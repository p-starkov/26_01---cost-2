# infrastructure/google_sheets/user_group_repository.py

from typing import Optional, List, Tuple

from googleapiclient.discovery import Resource

from domain.models.groups import UserGroupLink
from domain.repositories import IUserGroupRepository
from infrastructure.google_sheets.client import get_sheets_service, SPREADSHEET_ID
from config.settings import SHEET_USER_GROUPS_RANGE, SHEET_ID_USER_GROUPS


class UserGroupSheetRepository(IUserGroupRepository):
    """
    Репозиторий связки пользователь -> группа
    поверх листа userGroups.

    Лист userGroups:
    - колонка A: userId
    - колонка B: groupId
    начиная со строки 2 (диапазон A2:B).
    """

    def __init__(self) -> None:
        self.service: Resource = get_sheets_service()

    def _read_all_rows(self) -> Tuple[List[List[str]], int]:
        """
        Считывает все строки из диапазона SHEET_USER_GROUPS_RANGE.

        Возвращает:
        - values: список строк (каждая строка — список значений ячеек)
        - start_row_index: номер первой строки диапазона (например, 2),
          нужен, чтобы вычислять абсолютный номер строки для обновления/удаления.
        """
        # Пример: "userGroups!A2:B"
        range_str = SHEET_USER_GROUPS_RANGE
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
                range=SHEET_USER_GROUPS_RANGE,
            )
            .execute()
        )
        values = result.get("values", [])
        return values, start_row_index

    def get_by_user_id(self, user_id: str) -> Optional[UserGroupLink]:
        """
        Ищет запись по userId в листе userGroups.
        """
        values, _ = self._read_all_rows()

        for row in values:
            if not row:
                continue
            row_user_id = row[0].strip()
            if not row_user_id:
                continue
            if row_user_id == str(user_id):
                group_id = row[1].strip() if len(row) > 1 else ""
                return UserGroupLink(user_id=str(user_id), group_id=group_id)

        return None

    def upsert(self, user_id: str, group_id: str) -> UserGroupLink:
        """
        Обновляет запись для userId, если она есть,
        иначе добавляет новую строку.
        """
        values, start_row_index = self._read_all_rows()

        row_index = None
        current_row_offset = 0

        for row in values:
            current_row_offset += 1
            if not row:
                continue
            row_user_id = row[0].strip()
            if not row_user_id:
                continue
            if row_user_id == str(user_id):
                row_index = start_row_index + current_row_offset - 1
                break

        norm_group_id = group_id.strip().upper()

        if row_index is None:
            body = {"values": [[str(user_id), norm_group_id]]}

            (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=SPREADSHEET_ID,
                    range=SHEET_USER_GROUPS_RANGE,
                    valueInputOption="RAW",
                    body=body,
                )
                .execute()
            )
        else:
            update_range = f"userGroups!A{row_index}:B{row_index}"
            body = {"values": [[str(user_id), norm_group_id]]}

            (
                self.service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=update_range,
                    valueInputOption="RAW",
                    body=body,
                )
                .execute()
            )

        return UserGroupLink(user_id=str(user_id), group_id=norm_group_id)

    def delete_by_user_id(self, user_id: str) -> None:
        """
        Удаляет строку с userId из листа userGroups, если она есть,
        удаляя строку со сдвигом вверх.
        """
        values, start_row_index = self._read_all_rows()

        row_index = None
        current_row_offset = 0

        for row in values:
            current_row_offset += 1
            if not row:
                continue
            row_user_id = row[0].strip()
            if not row_user_id:
                continue
            if row_user_id == str(user_id):
                row_index = start_row_index + current_row_offset - 1
                break

        if row_index is None:
            return

        requests = [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": SHEET_ID_USER_GROUPS,
                        "dimension": "ROWS",
                        "startIndex": row_index - 1,
                        "endIndex": row_index,
                    }
                }
            }
        ]

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests},
        ).execute()
