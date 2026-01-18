# application/usecases/reports.py

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import StrEnum
from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal, ROUND_HALF_UP

from infrastructure.google_sheets.client import get_sheets_service
from config.settings import GOOGLE_SPREADSHEET_ID, SHEET_OPERATION_ROWS_RANGE

from application.usecases.user_groups import UserGroupsService
from infrastructure.google_sheets.user_repository import UserSheetRepository
from infrastructure.google_sheets.group_repository import GroupSheetRepository
from infrastructure.google_sheets.operation_repository import OperationSheetRepository


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
    operations_repo: OperationSheetRepository

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
    
    def format_category_expense_report(self, group_id: str, period_code: str) -> str:
        """
        Отчёт "Затраты по категориям" за выбранный период.

        - Берём все операции группы за период;
        - фильтруем только расходы (isExpense == True);
        - группируем по категории;
        - считаем сумму и долю (%) по каждой категории;
        - форматируем текст.
        """
        start_date, end_date = _get_period_bounds(period_code)

        # 1. Получаем операции из репозитория.
        #    Здесь нужно использовать уже существующий репозиторий/метод, который
        #    читает строки листа operations.
        operations = self.operations_repo.get_operations_for_group(
            group_id=group_id,
            start_date=start_date,
            end_date=end_date,
        )
        # Предполагаем, что каждая операция — объект/датакласс с полями:
        # - date (datetime.date)
        # - is_expense (bool)
        # - category (str)
        # - amount (Decimal или float)

        # 2. Фильтруем только расходы.
        expense_ops = [
            op for op in operations
            if op.is_expense
        ]
        
        # ОТЛАДКА: вывести количество расходов
        print(f"Expense operations: {len(expense_ops)}")
        print("===============================")

        if not expense_ops:
            return "За выбранный период не найдено расходов."

        # 3. Группируем по категориям и считаем сумму.
        from collections import defaultdict
        from decimal import Decimal, ROUND_HALF_UP

        sum_by_category: dict[str, Decimal] = defaultdict(Decimal)

        for op in expense_ops:
            # Нормализуем категорию (пустое -> "Без категории")
            category = op.category or "Без категории"
            sum_by_category[category] += Decimal(op.amount)

        total_amount = sum(sum_by_category.values())

        # 4. Готовим текст в зависимости от типа периода.
        is_month_level = period_code in {
            ReportPeriod.CURRENT_MONTH,
            ReportPeriod.PREV_MONTH,
        }

        lines: list[str] = []

        if is_month_level:
            # Отчёт за один месяц
            lines.append(f"Отчёт по категориям за период {start_date:%d.%m.%Y}–{end_date:%d.%m.%Y}:")
            lines.extend(
                _format_category_lines(sum_by_category, total_amount)
            )
        else:
            # Квартал или год: делаем разрез по месяцам + раздел ИТОГО
            lines.append(f"Отчёт по категориям за период {start_date:%d.%m.%Y}–{end_date:%d.%m.%Y}:")

            # Группируем операции по месяцам
            ops_by_month: dict[tuple[int, int], list] = defaultdict(list)
            for op in expense_ops:
                key = (op.date.year, op.date.month)
                ops_by_month[key].append(op)

            # Перебираем месяцы в хронологическом порядке
            for (y, m) in sorted(ops_by_month.keys()):
                month_ops = ops_by_month[(y, m)]
                month_sum_by_cat: dict[str, Decimal] = defaultdict(Decimal)
                for op in month_ops:
                    category = op.category or "Без категории"
                    month_sum_by_cat[category] += Decimal(op.amount)

                month_total = sum(month_sum_by_cat.values())
                lines.append("")  # пустая строка между месяцами
                lines.append(f"За {m:02d}.{y}:")
                lines.extend(
                    _format_category_lines(month_sum_by_cat, month_total)
                )

            # Раздел ИТОГО по всему периоду
            lines.append("")
            lines.append("ИТОГО за период:")
            lines.extend(
                _format_category_lines(sum_by_category, total_amount)
            )

        return "\n".join(lines)
    
class ReportPeriod(StrEnum):
    CURRENT_MONTH = "period:current_month"
    PREV_MONTH = "period:prev_month"
    CURRENT_QUARTER = "period:current_quarter"
    PREV_QUARTER = "period:prev_quarter"
    CURRENT_YEAR = "period:current_year"
    PREV_YEAR = "period:prev_year"

def _get_period_bounds(period_code: str, today: date | None = None) -> tuple[date, date]:
    """
    По коду периода возвращает даты начала и конца (включительно).

    Это чистая функция без обращения к БД:
    - удобно тестировать;
    - её можно переиспользовать.
    """
    if today is None:
        today = date.today()

    year = today.year
    month = today.month

    def month_start_end(y: int, m: int) -> tuple[date, date]:
        last_day = monthrange(y, m)[1]
        return date(y, m, 1), date(y, m, last_day)

    if period_code == ReportPeriod.CURRENT_MONTH:
        return month_start_end(year, month)

    if period_code == ReportPeriod.PREV_MONTH:
        if month == 1:
            return month_start_end(year - 1, 12)
        return month_start_end(year, month - 1)

    # Кварталы: 1–3, 4–6, 7–9, 10–12
    quarter = (month - 1) // 3 + 1

    if period_code == ReportPeriod.CURRENT_QUARTER:
        q_start_month = (quarter - 1) * 3 + 1
        q_end_month = q_start_month + 2
        start = date(year, q_start_month, 1)
        end = date(year, q_end_month, monthrange(year, q_end_month)[1])
        return start, end

    if period_code == ReportPeriod.PREV_QUARTER:
        if quarter == 1:
            prev_year = year - 1
            prev_q = 4
        else:
            prev_year = year
            prev_q = quarter - 1

        q_start_month = (prev_q - 1) * 3 + 1
        q_end_month = q_start_month + 2
        start = date(prev_year, q_start_month, 1)
        end = date(prev_year, q_end_month, monthrange(prev_year, q_end_month)[1])
        return start, end

    if period_code == ReportPeriod.CURRENT_YEAR:
        return date(year, 1, 1), date(year, 12, 31)

    if period_code == ReportPeriod.PREV_YEAR:
        return date(year - 1, 1, 1), date(year - 1, 12, 31)

    # На случай неизвестного кода — по умолчанию текущий месяц
    return month_start_end(year, month)

def _format_category_lines(sum_by_category: dict[str, "Decimal"], total_amount: "Decimal") -> list[str]:
    """
    Форматирует строки вида:
    <КАТЕГОРИЯ>: СУММА (XX.XX%)
    Сортировка по убыванию суммы.
    """
    from decimal import Decimal, ROUND_HALF_UP

    # Сортируем категории по сумме по убыванию
    sorted_items = sorted(sum_by_category.items(), key=lambda kv: kv[1], reverse=True)

    lines: list[str] = []
    for category, amount in sorted_items:
        if total_amount == 0:
            percent = Decimal("0")
        else:
            percent = (amount / total_amount * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        lines.append(f"{category}: {amount:.2f} ({percent}%)")

    return lines