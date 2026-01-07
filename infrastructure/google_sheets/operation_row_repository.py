from googleapiclient.discovery import Resource

from domain.models.expenses import OperationRow
from domain.repositories import IOperationRowRepository
from infrastructure.google_sheets.client import get_sheets_service, SPREADSHEET_ID
from config.settings import SHEET_OPERATION_ROWS_RANGE


class OperationRowSheetRepository(IOperationRowRepository):
    def __init__(self) -> None:
        self.service: Resource = get_sheets_service()

    def create_many(self, rows: list[OperationRow]) -> None:
        if not rows:
            return

        values = []
        for r in rows:
            values.append([
                r.group_id,                        # Group 
                r.date.isoformat(),                 # Date
                r.operation_id,                     # Operation
                r.person_id,                        # Person
                r.category,                         # Category
                r.row_type,                         # type: debit/credit
                r.amount,                           # Amount
                "TRUE" if r.active else "FALSE",    # Active
            ])

        body = {"values": values}

        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_OPERATION_ROWS_RANGE,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )
