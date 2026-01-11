# main.py

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN
from application.usecases.reports import ReportService
from infrastructure.google_sheets.group_repository import GroupSheetRepository
from infrastructure.google_sheets.user_group_repository import UserGroupSheetRepository
from infrastructure.google_sheets.user_repository import UserSheetRepository

from application.usecases.user_groups import UserGroupsService
from transport.telegram.registration_handlers import register_registration_handlers

from infrastructure.google_sheets.operation_repository import OperationSheetRepository
from infrastructure.google_sheets.operation_row_repository import OperationRowSheetRepository
from transport.telegram.expense_handlers import register_expense_handlers
from application.usecases.expenses import ExpenseService



async def main():
    # 1. Создаём Bot и Dispatcher
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # Регистрируем команды, которые будут видны по кнопке справа от поля ввода
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Начать работу / выбрать группу"),
            BotCommand(command="operation", description="Учесть затрату или передачу"),
            BotCommand(command="report", description="Показать отчёты"),
            # можно добавить и другие команды
        ]
    )

    dp = Dispatcher(storage=MemoryStorage())


    # 2. Инициализируем репозитории и сервис работы с группами
    group_repo = GroupSheetRepository()
    user_group_repo = UserGroupSheetRepository()
    user_repo = UserSheetRepository()
    user_groups_service = UserGroupsService(
        group_repo=group_repo,
        user_group_repo=user_group_repo,
        user_repo=user_repo,
    )

    operation_repo = OperationSheetRepository()
    operation_row_repo = OperationRowSheetRepository()
    expense_service = ExpenseService(
        operation_repo=operation_repo,
        operation_row_repo=operation_row_repo,
        user_group_repo=user_group_repo,
    )

    report_service = ReportService(
        user_groups_svc=user_groups_service,
        user_repo=user_repo,
        group_repo=group_repo,
        operations_repo=operation_repo,
    )

    # 3. Регистрируем хэндлеры, передавая внутрь сервис
    register_registration_handlers(dp, user_groups_service)
    register_expense_handlers(dp, user_groups_service, expense_service, report_service)

    # 4. Запускаем бота в режиме long polling
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
