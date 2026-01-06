# main.py

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN
from infrastructure.google_sheets.group_repository import GroupSheetRepository
from infrastructure.google_sheets.user_group_repository import UserGroupSheetRepository
from application.usecases.user_groups import UserGroupsService
from transport.telegram.registration_handlers import register_registration_handlers


async def main():
    # 1. Создаём Bot и Dispatcher
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 2. Инициализируем репозитории и сервис работы с группами
    group_repo = GroupSheetRepository()
    user_group_repo = UserGroupSheetRepository()
    user_groups_service = UserGroupsService(group_repo, user_group_repo)

    # 3. Регистрируем хэндлеры, передавая внутрь сервис
    register_registration_handlers(dp, user_groups_service)

    # 4. Запускаем бота в режиме long polling
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
