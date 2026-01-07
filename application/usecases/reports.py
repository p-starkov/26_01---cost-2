# application/usecases/reports.py

from dataclasses import dataclass
from typing import Dict, List, Tuple

from infrastructure.google_sheets.client import get_sheets_service
from config.settings import GOOGLE_SPREADSHEET_ID, SHEET_OPERATION_ROWS_RANGE

from application.usecases.user_groups import UserGroupsService
from infrastructure.google_sheets.user_repository import UserSheetRepository
from infrastructure.google_sheets.group_repository import GroupSheetRepository


@dataclass
class ReportService:
    """
    Сервис построения отчётов по данным Google Sheets.

    Сейчас реализует один отчёт:
    - баланс по группе на основе листа operationsRows.
    """

    user_groups_svc: UserGroupsService
    user_repo: UserSheetRepository
    group_repo: GroupSheetRepository

    def _get_group_members(self, group_id: str) -> List[str]:
        """
        Возвращает список user_id участников заданной группы
        по данным листа userGroups.
        """
        # Используем уже существующий вспомогательный метод репозитория
        values, _ = self.user_groups_svc.user_group_repo._read_all_rows()

        member_ids: List[str] = []
        for row in values:
            if not row:
                continue
            row_user_id = row[0].strip()
            row_group_id = row[1].strip().upper() if len(row) > 1 else ""
            if row_group_id == group_id.strip().upper():
                member_ids.append(row_user_id)
        return member_ids

    def get_group_balance(self, group_id: str) -> Tuple[str, Dict[str, float]]:
        """
        Рассчитать баланс по всем пользователям группы.

        Баланс пользователя считается по листу operationsRows:
        - debit-строки дают +amount;
        - credit-строки дают -amount.

        Возвращает:
        - group_name: строка с названием группы (если есть в Groups, иначе group_id);
        - balances: словарь {user_id -> сумма}.
        """
        # 1. Участники группы
        member_ids = self._get_group_members(group_id)
        balances: Dict[str, float] = {uid: 0.0 for uid in member_ids}

        if not member_ids:
            # Пустая группа — вернём пустой баланс
            group_name = group_id
            return group_name, balances

        # 2. Читаем все строки из operationsRows
        service = get_sheets_service()
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=GOOGLE_SPREADSHEET_ID,
                range=SHEET_OPERATION_ROWS_RANGE,
            )
            .execute()
        )
        values = result.get("values", [])

        # Порядок колонок operationsRows:
        # A: Group
        # B: Date
        # C: Operation
        # D: Person
        # E: Category
        # F: Type (debit/credit)
        # G: Amount
        # H: Active

        for row in values:
            if len(row) < 7:
                continue

            row_group_id = row[0].strip().upper()
            if row_group_id != group_id.strip().upper():
                # Строка относится к другой группе
                continue

            person_id = row[3].strip()
            if person_id not in balances:
                # Пользователь не в текущей группе
                continue

            row_type = row[5].strip().lower()  # "debit" или "credit"
            amount_str = row[6].replace(",", ".").strip()

            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if row_type == "debit":
                balances[person_id] += amount
            elif row_type == "credit":
                balances[person_id] -= amount

        # 3. Имя группы из Groups (если есть)
        group_name = group_id
        try:
            group_info = self.group_repo.get_by_id(group_id)
            if group_info is not None and getattr(group_info, "name", None):
                group_name = group_info.name
        except AttributeError:
            # Если метода get_by_id нет — оставим group_id
            pass

        return group_name, balances

    def format_balance_report(self, group_id: str) -> str:
        """
        Построить текст отчёта по группе с использованием имён пользователей.

        Формат:
        Группа: <имя группы>
        Имя 1: сумма
        Имя 2: сумма
        ...
        """
        group_name, balances = self.get_group_balance(group_id)

        lines: List[str] = [f"Группа: {group_name}"]

        for user_id, balance in balances.items():
            user_info = self.user_repo.get_by_id(user_id)
            if user_info is not None and getattr(user_info, "name", None):
                display_name = user_info.name
            else:
                display_name = f"Пользователь {user_id}"

            lines.append(f"{display_name}: {balance:.2f}")

        # Если в группе нет участников или нет строк, balances будет пустым
        if len(lines) == 1:
            lines.append("В этой группе пока нет данных по операциям.")

        return "\n".join(lines)
