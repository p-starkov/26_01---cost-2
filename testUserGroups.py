# test_user_groups.py

from infrastructure.google_sheets.group_repository import GroupSheetRepository
from infrastructure.google_sheets.user_group_repository import UserGroupSheetRepository
from application.usecases.user_groups import UserGroupsService


def main():
    # 1. Создаём реализации репозиториев
    group_repo = GroupSheetRepository()
    user_group_repo = UserGroupSheetRepository()

    # 2. Создаём сервис use-case
    service = UserGroupsService(
        group_repo=group_repo,
        user_group_repo=user_group_repo,
    )

    # Зададим test user_id (в реальности это будет telegram user id)
    user_id = "123456"

    print("=== Проверка текущей группы (до изменений) ===")
    current_group = service.get_current_user_group(user_id)
    if current_group is None:
        print("Пользователь пока не привязан ни к одной группе.")
    else:
        print(f"Текущая группа пользователя: {current_group.id}")

    # 3. Создадим новую группу и привяжем пользователя
    new_group_id = "TESTGRP1"  # для начала можно задать руками
    print(f"\n=== Создание группы {new_group_id} и привязка пользователя ===")
    group = service.create_group_and_assign(user_id, new_group_id)
    print(f"Создана группа с id: {group.id}")

    # 4. Ещё раз проверим текущую группу
    print("\n=== Проверка текущей группы (после создания) ===")
    current_group = service.get_current_user_group(user_id)
    if current_group is None:
        print("Что-то пошло не так: группа не найдена.")
    else:
        print(f"Теперь текущая группа пользователя: {current_group.id}")

    # 5. Проверим присоединение к другой группе
    another_group_id = "TESTGRP2"
    print(f"\n=== Попытка присоединиться к группе {another_group_id} ===")
    # Сначала создадим её напрямую через репозиторий
    group_repo.create(another_group_id)

    joined = service.join_group(user_id, another_group_id)
    if joined:
        print(f"Пользователь присоединён к группе {another_group_id}.")
    else:
        print(f"Группа {another_group_id} не существует.")

    print("\n=== Финальная проверка текущей группы ===")
    current_group = service.get_current_user_group(user_id)
    if current_group:
        print(f"Текущая группа пользователя: {current_group.id}")
    else:
        print("Группа не найдена.")


if __name__ == "__main__":
    main()
