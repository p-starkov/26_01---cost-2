# domain/repositories.py

from typing import Protocol, Optional
from domain.models.groups import Group, UserGroupLink
from domain.models.users import UserInfo
from domain.models.expenses import Operation, OperationRow

class IUserRepository(Protocol):
    def get_by_id(self, user_id: str) -> Optional[UserInfo]:
        ...

    def create_if_not_exists(self, user_id: str, name: str) -> UserInfo:
        ...

class IGroupRepository(Protocol):
    """
    Интерфейс (контракт) для работы с таблицей Groups.

    В реальной реализации (в infrastructure/google_sheets/group_repository.py)
    эти методы будут:
    - читать строки из листа Groups;
    - добавлять новые строки в лист Groups.
    """

    def exists(self, group_id: str) -> bool:
        """
        Проверить, существует ли группа с таким идентификатором.

        Возвращает:
        - True, если в листе Groups есть строка с этим group_id.
        - False, если такой группы нет.
        """
        ...

    def create(self, group_id: str) -> Group:
        """
        Создать новую группу с указанным идентификатором.

        В реальной реализации:
        - добавить строку в лист Groups;
        - вернуть объект Group.

        Параметры:
        - group_id: строковый идентификатор новой группы.
        """
        ...


class IUserGroupRepository(Protocol):
    """
    Интерфейс (контракт) для работы с таблицей userGroups.

    Таблица userGroups хранит связь:
    - userId -> groupId
    """

    def get_by_user_id(self, user_id: str) -> Optional[UserGroupLink]:
        """
        Найти текущую группу пользователя по его user_id.

        Возвращает:
        - UserGroupLink, если запись найдена;
        - None, если пользователь ещё не привязан ни к какой группе.
        """
        ...

    def upsert(self, user_id: str, group_id: str) -> UserGroupLink:
        """
        Обновить или создать запись для пользователя.
        """
        ...

    def delete_by_user_id(self, user_id: str) -> None:
        """
        Удалить строку с указанным user_id из таблицы userGroups,
        если она есть.
        """
        ...


class IOperationRepository(Protocol):
    """
    Контракт для работы с листом operations (таблица Operations).
    Сейчас нужен только метод create (добавить одну операцию).
    """

    def create(self, op: Operation) -> None:
        """
        Сохранить операцию в хранилище.

        Параметры:
        - op: объект Operation с заполненными полями.
        """
        ...


class IOperationRowRepository(Protocol):
    """
    Контракт для работы с листом operationsRows (таблица OperationRows).
    """

    def create_many(self, rows: list[OperationRow]) -> None:
        """
        Сохранить сразу несколько строк операций.

        Параметры:
        - rows: список объектов OperationRow.
        """
        ...
