# application/usecases/user_groups.py

from dataclasses import dataclass
from typing import Optional

from domain.models.groups import Group, UserGroupLink
from domain.repositories import IGroupRepository, IUserGroupRepository, IUserRepository

@dataclass
class UserGroupsService:
    """
    Сервис (use-case слой) для работы с группами пользователя.

    Здесь нет ничего про Google Sheets — только вызовы репозиториев.
    """

    group_repo: IGroupRepository
    user_group_repo: IUserGroupRepository
    user_repo: IUserRepository

    def ensure_user_exists(self, user_id: str, name: str) -> None:
        """
        Если пользователя ещё нет в листе users, добавить его.
        """
        self.user_repo.create_if_not_exists(user_id, name)

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

    def create_group_and_assign(
        self,
        user_id: str,
        group_id: str,
        user_name: str,
    ) -> Group:
        """
        Создать новую группу с заданным идентификатором и
        привязать пользователя к этой группе.

        Дополнительно:
        - если пользователя ещё нет в листе users, добавить его
        с указанным именем.
        """

        # Сначала убедимся, что пользователь есть в листе users.
        # Если записи нет, репозиторий создаст строку (userId, userName).
        self.ensure_user_exists(user_id, user_name)

        # Создаём группу в таблице Groups.
        # Репозиторий добавит новую строку с group_id в лист Groups.
        group = self.group_repo.create(group_id)

        # Обновляем или создаём запись userId -> groupId
        # в таблице userGroups.
        # Если строка с таким userId уже была, её groupId заменится.
        # Если не было — добавится новая строка.
        self.user_group_repo.upsert(user_id, group_id)

        # Возвращаем объект Group, чтобы хэндлер мог показать id пользователю.
        return group


    def join_group(
        self,
        user_id: str,
        group_id: str,
        user_name: str,
    ) -> bool:
        """
        Присоединить пользователя к существующей группе.

        Параметры:
        - user_id: идентификатор пользователя (telegram user id).
        - group_id: введённый пользователем идентификатор группы
        (может быть в любом регистре).
        - user_name: имя пользователя (для записи в таблицу users,
        если его там ещё нет).

        Возвращает:
        - True, если группа существует и привязка создана/обновлена.
        - False, если группы с таким id не существует.
        """

        # Убедимся, что пользователь есть в листе users.
        # Если записи нет, добавим (userId, userName).
        self.ensure_user_exists(user_id, user_name)

        # Нормализуем идентификатор группы:
        # - убираем пробелы по краям;
        # - приводим к верхнему регистру.
        # Так поиск и хранение group_id становятся регистронезависимыми.
        group_id_norm = group_id.strip().upper()

        # Проверяем, существует ли такая группа в таблице Groups.
        # Если нет — нельзя присоединить пользователя, возвращаем False.
        if not self.group_repo.exists(group_id_norm):
            return False

        # Группа существует — обновляем/создаём связь userId -> groupId
        # в таблице userGroups.
        self.user_group_repo.upsert(user_id, group_id_norm)

        # Сообщаем вызывающему коду, что операция прошла успешно.
        return True

    
    def leave_group(self, user_id: str) -> bool:
        """
        Удалить привязку пользователя к текущей группе.

        Возвращает:
        - True, если привязка была и мы её удалили;
        - False, если пользователь и так не был ни к какой группе привязан.
        """
        link: Optional[UserGroupLink] = self.user_group_repo.get_by_user_id(user_id)
        if link is None:
            return False

        self.user_group_repo.delete_by_user_id(user_id)
        return True
