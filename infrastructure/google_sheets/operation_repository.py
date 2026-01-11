from datetime import datetime
from datetime import date
from googleapiclient.discovery import Resource

from domain.models.expenses import Operation
from domain.repositories import IOperationRepository
from infrastructure.google_sheets.client import get_sheets_service, SPREADSHEET_ID
from config.settings import SHEET_OPERATIONS_RANGE


class OperationSheetRepository(IOperationRepository):
    def __init__(self) -> None:
        self.service: Resource = get_sheets_service()

    def create(self, op: Operation) -> None:
        body = {
            "values": [[
                op.group_id,            # Group
                op.date.isoformat(),    # Date
                op.id,                  # Id
                op.operation_type,      # OperationType
                op.person_id,           # Person
                "TRUE" if op.is_expense else "FALSE",    # IsExpense
                op.category,            # Category
                op.comment,             # Comment
                op.amount,              # Amount
                "TRUE" if op.active else "FALSE",  # Active
            ]]
        }

        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_OPERATIONS_RANGE,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

    def get_operations_for_group(
        self,
        group_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Operation]:
        """
        Читает операции группы из Google Sheets и фильтрует по периоду.
        
        Параметры:
        - group_id: идентификатор группы
        - start_date: начало периода (включительно), если None — не фильтруем
        - end_date: конец периода (включительно), если None — не фильтруем
        
        Возвращает:
        - список объектов Operation, подходящих под фильтр
        """
        # 1. Читаем все строки из листа operations
        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_OPERATIONS_RANGE,
            )
            .execute()
        )
        
        # values — это список списков, каждый внутренний список — одна строка таблицы
        rows = result.get("values", [])
        
        operations: list[Operation] = []
        
        for row in rows:
            # Если строка пустая или слишком короткая — пропускаем
            if len(row) < 10:
                continue
            
            # Распаковываем колонки (порядок тот же, что при записи в create)
            row_group_id = row[0]      # Group
            row_date_str = row[1]      # Date (ISO формат, например "2026-01-10")
            row_id = row[2]            # Id
            row_op_type = row[3]       # OperationType
            row_person_id = row[4]     # Person
            row_is_expense_str = row[5]  # IsExpense ("TRUE" или "FALSE")
            row_category = row[6]      # Category
            row_comment = row[7]       # Comment
            row_amount_str = row[8]    # Amount (строка, нужно преобразовать)
            row_active_str = row[9]    # Active ("TRUE" или "FALSE")
            
            # 2. Фильтруем по group_id
            if row_group_id != group_id:
                continue
            
            # 3. Парсим дату
            try:
                # Ожидаем формат ISO: "YYYY-MM-DD"
                row_date = datetime.fromisoformat(row_date_str).date()
            except (ValueError, AttributeError):
                # Если дата невалидная — пропускаем строку
                continue
            
            # 4. Фильтруем по периоду
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            
            # 5. Парсим is_expense
            is_expense = row_is_expense_str.upper() == "TRUE"
            
            # 6. Парсим amount (сумму)
            try:
                amount = float(row_amount_str)
            except (ValueError, TypeError):
                amount = 0.0
            
            # 7. Парсим active
            active = row_active_str.upper() == "TRUE"
            
            # 8. Собираем объект Operation
            op = Operation(
                group_id=row_group_id,
                date=datetime.combine(row_date, datetime.min.time()),  # преобразуем date -> datetime
                id=row_id,
                operation_type=row_op_type,
                person_id=row_person_id,
                is_expense=is_expense,
                category=row_category,
                comment=row_comment,
                amount=amount,
                active=active,
            )
            
            operations.append(op)
        
        return operations