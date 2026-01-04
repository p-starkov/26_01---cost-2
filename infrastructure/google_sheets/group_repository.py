# infrastructure/google_sheets/group_repository.py

from typing import List
from googleapiclient.discovery import Resource
from domain.models.groups import Group
from domain.repositories import IGroupRepository
from infrastructure.google_sheets.client import get_sheets_service, SPREADSHEET_ID
from config.settings import SHEET_GROUPS_RANGE


class GroupSheetRepository(IGroupRepository):
    """
    Реализация репозитория групп поверх листа Groups.

    Лист Groups:
    - одна колонка id, начиная со строки 2 (A2:A).
    """

    def __init__(self) -> None:
        self.service: Resource = get_sheets_service()

    def _read_all_group_ids(self) -> List[str]:
        """
        Считывает все значения из диапазона SHEET_GROUPS_RANGE и
        возвращает список строковых id.
        """
        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_GROUPS_RANGE,
            )
            .execute()
        )
        values = result.get("values", [])
        # values — список списков, каждая внутренняя ячейка — одна строка
        group_ids = [row[0] for row in values if row]  # row[0] — значение в колонке A
        return group_ids

    def exists(self, group_id: str) -> bool:
        """
        Проверяет, есть ли в листе Groups строка с таким group_id.
        """
        group_ids = self._read_all_group_ids()
        return group_id in group_ids

    def create(self, group_id: str) -> Group:
        """
        Добавляет новую строку в лист Groups с указанным group_id.
        """
        body = {"values": [[group_id]]}  # одна строка, одна колонка

        (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range=SHEET_GROUPS_RANGE,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        return Group(id=group_id)
