# test_expense.py
"""
Тест создания затраты 'за всех в группе' без Telegram.

Что делает скрипт:
1. Создаёт репозитории Google Sheets.
2. Создаёт сервис расходов ExpenseService.
3. Вызывает create_expense_for_all для заданного пользователя и группы.
4. Печатает ID операции, чтобы можно было проверить строки в Google Sheets.
"""

from infrastructure.google_sheets.group_repository import GroupSheetRepository
from infrastructure.google_sheets.user_group_repository import UserGroupSheetRepository
from infrastructure.google_sheets.operation_repository import OperationSheetRepository
from infrastructure.google_sheets.operation_row_repository import OperationRowSheetRepository

from application.usecases.expenses import ExpenseService


def main():
    # 1. Инициализация репозиториев
    #
    # Они внутри themselves создают клиента Google Sheets (get_sheets_service),
    # поэтому важно, чтобы:
    # - были корректно настроены GOOGLE_SPREADSHEET_ID и диапазоны в config/settings.py;
    # - существовал credentials.json (или другой путь в client.py).
    group_repo = GroupSheetRepository()
    user_group_repo = UserGroupSheetRepository()
    op_repo = OperationSheetRepository()
    op_row_repo = OperationRowSheetRepository()

    # 2. Сервис расходов
    #
    # ExpenseService использует:
    # - op_repo       для записи в лист Operations;
    # - op_row_repo   для записи в лист OperationRows;
    # - user_group_repo для получения участников группы (по листу userGroups).
    expense_service = ExpenseService(
        operation_repo=op_repo,
        operation_row_repo=op_row_repo,
        user_group_repo=user_group_repo,
    )

    # 3. Тестовые данные
    #
    # user_id  – id пользователя, от имени которого создаём затрату.
    # group_id – id группы, в которой уже есть участники в листе userGroups.
    # category – одна из допустимых категорий.
    # comment  – произвольный текст описания.
    # amount   – сумма затраты.
    user_id = "405145783"           # ЗАМЕНИ на реальный userId из userGroups
    group_id = "F857LW"          # ЗАМЕНИ на реально существующий group_id
    category = "Реклама"
    comment = "Тестовая затрата за всех"
    amount = 1000.0

    # 4. Вызов use-case
    #
    # Метод:
    # - создаст запись в Operations;
    # - создаст строки в OperationRows (debit для user_id и credit для всех участников группы).
    op_id = expense_service.create_expense_for_all(
        user_id=user_id,
        group_id=group_id,
        category=category,
        comment=comment,
        amount=amount,
    )

    print("Операция создана.")
    print(f"ID операции: {op_id}")
    print("Проверь листы 'Operations' и 'OperationRows' в Google Sheets.")


if __name__ == "__main__":
    main()
