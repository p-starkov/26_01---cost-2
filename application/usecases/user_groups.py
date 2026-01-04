# application/usecases/user_groups.py

from dataclasses import dataclass
from typing import Optional

from domain.models.groups import Group, UserGroupLink
from domain.repositories import IGroupRepository, IUserGroupRepository


@dataclass
class UserGroupsService:
    """
    Сервис (use-case слой) для работы с группами пользователя.

    Здесь нет ничего про Google Sheets — только вызовы репозиториев.
    """

    group_repo: IGroupRepository
    user_group_repo: IUserGroupRepository

    def get_current_user_group(self, user_id: str) -> Optional[Group]:
        """
        Получить текущую группу пользователя.

        Если пользователь ещё не привязан к группе, вернёт None.
        """
        link: Optional[UserGroupLink] = self.user_group_repo.get_by_user_id(user_id)
        if link is None:
            return None

        # Можно не проверять exists, если верим данным userGroups,
        # но для надёжности можно дополнительно проверить:
        if not self.group_repo.exists(link.group_id):
            # Странная ситуация: связка есть, а группы нет.
            # В простой версии просто вернём None.
            return None

        return Group(id=link.group_id)

    def create_group_and_assign(self, user_id: str, group_id: str) -> Group:
        """
        Создать новую группу с заданным идентификатором и
        привязать пользователя к этой группе.

        В проде group_id обычно генерируется автоматически (короткий код).
        """
        # Создаём группу в таблице Groups
        group = self.group_repo.create(group_id)

        # Обновляем или создаём запись userId -> groupId
        self.user_group_repo.upsert(user_id, group_id)

        return group

    def join_group(self, user_id: str, group_id: str) -> bool:
        """
        Присоединить пользователя к существующей группе.

        Возвращает:
        - True, если группа существует и присоединение выполнено;
        - False, если группы с таким id нет.
        """
        if not self.group_repo.exists(group_id):
            return False

        self.user_group_repo.upsert(user_id, group_id)
        return True
