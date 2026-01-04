# domain/repositories.py

from typing import Protocol, Optional
from domain.models.groups import Group, UserGroupLink


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

        Логика:
        - если в таблице userGroups уже есть строка с этим userId,
          то заменить в ней groupId на новое значение;
        - если строки нет, добавить новую (userId, groupId).

        Возвращает:
        - актуальный объект UserGroupLink после изменения.
        """
        ...
