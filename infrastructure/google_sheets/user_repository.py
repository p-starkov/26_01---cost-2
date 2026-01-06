from typing import List, Tuple, Optional
from googleapiclient.discovery import Resource

from domain.models.users import UserInfo
from domain.repositories import IUserRepository
from infrastructure.google_sheets.client import get_sheets_service, SPREADSHEET_ID
from config.settings import SHEET_USERS_RANGE


class UserSheetRepository(IUserRepository):
    """
    Репозиторий для листа users.

    Лист users:
    - колонка A: userId
    - колонка B: userName
    начиная со строки 2 (диапазон A2:B).
    """

    def __init__(self) -> None:
        self.service: Resource = get_sheets_service()

    def _read_all_rows(self) -> Tuple[List[List[str]], int]:
        range_str = SHEET_USERS_RANGE  # "users!A2:B"
        _, cells_part = range_str.split("!")
        start_row_str = ""
        for ch in cells_part.split(":")[0]:
            if ch.isdigit():
                start_row_str += ch
        start_row_index = int(start_row_str) if start_row_str else 1

        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_USERS_RANGE,
            )
            .execute()
        )
        values = result.get("values", [])
        return values, start_row_index

    def get_by_id(self, user_id: str) -> Optional[UserInfo]:
        values, _ = self._read_all_rows()

        for row in values:
            if not row:
                continue
            row_user_id = row[0].strip()
            if not row_user_id:
                continue
            if row_user_id == str(user_id):
                name = row[1].strip() if len(row) > 1 else ""
                return UserInfo(user_id=str(user_id), name=name)

        return None

    def create_if_not_exists(self, user_id: str, name: str) -> UserInfo:
        existing = self.get_by_id(user_id)
        if existing is not None:
            return existing

        body = {
            "values": [
                [str(user_id), name]
            ]
        }

        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_USERS_RANGE,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        return UserInfo(user_id=str(user_id), name=name)
