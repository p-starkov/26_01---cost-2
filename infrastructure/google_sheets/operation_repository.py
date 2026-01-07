from datetime import datetime
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
