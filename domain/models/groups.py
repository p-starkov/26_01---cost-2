from dataclasses import dataclass
from typing import Optional


@dataclass
class Group:
    """
    Модель группы.

    Поля:
    - id: строковый идентификатор группы.
      В твоём случае это будет «короткий» id, который бот показывает пользователю.
    """

    id: str


@dataclass
class UserGroupLink:
    """
    Связка пользователя с его текущей группой.

    Поля:
    - user_id: идентификатор пользователя (обычно telegram user id).
    - group_id: идентификатор группы, к которой сейчас «привязан» пользователь.
    """

    user_id: str
    group_id: str
