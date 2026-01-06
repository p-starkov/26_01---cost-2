# transport/telegram/registration_handlers.py

from enum import IntEnum

from aiogram import Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from application.usecases.user_groups import UserGroupsService
from common.id_generator import generate_group_id


# Тексты кнопок меню
CREATE_GROUP_BTN = "Создать группу"
JOIN_GROUP_BTN = "Присоединиться к группе"


class RegistrationStates(StatesGroup):
    """
    Набор состояний конечного автомата (FSM)
    для сценария выбора / ввода группы.
    """

    MENU_CHOICE = State()        # пользователь выбирает: создать / присоединиться
    WAITING_FOR_GROUP_ID = State()  # пользователь вводит ID группы для присоединения


def _main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура с двумя кнопками для выбора действия.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CREATE_GROUP_BTN),
             KeyboardButton(text=JOIN_GROUP_BTN)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def register_registration_handlers(dp: Dispatcher, svc: UserGroupsService) -> None:
    """
    Регистрация всех хэндлеров, связанных с регистрацией
    и сменой группы.

    Параметры:
    - dp: Dispatcher aiogram.
    - svc: сервис работы с группами пользователя.
    """

    # /start
    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        """
        /start:
        - если у пользователя уже есть группа -> показать её id;
        - иначе -> показать меню с выбором.
        """
        user_id = str(message.from_user.id)

        current_group = svc.get_current_user_group(user_id)

        if current_group is not None:
            await state.clear()
            await message.answer(
                f"Текущая группа: <b>{current_group.id}</b>\n"
                "Чтобы сменить группу, используйте команду /change_group.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        # Группы нет — показываем меню
        await state.set_state(RegistrationStates.MENU_CHOICE)
        await message.answer(
            "Вы пока не привязаны ни к одной группе.\n"
            "Выберите действие:",
            reply_markup=_main_menu_keyboard(),
        )

    # /change_group
    @dp.message(Command("change_group"))
    async def cmd_change_group(message: Message, state: FSMContext):
        """
        Команда смены группы:
        сразу показываем меню 'Создать группу' / 'Присоединиться к группе'.
        """
        await state.set_state(RegistrationStates.MENU_CHOICE)
        await message.answer(
            "Выберите действие:",
            reply_markup=_main_menu_keyboard(),
        )

    # Обработка выбора в меню (создать / присоединиться)
    @dp.message(
        RegistrationStates.MENU_CHOICE,
        F.text.in_({CREATE_GROUP_BTN, JOIN_GROUP_BTN}),
    )
    async def process_menu_choice(message: Message, state: FSMContext):
        user_id = str(message.from_user.id)
        text = message.text

        if text == CREATE_GROUP_BTN:
            if text == CREATE_GROUP_BTN:
                # Генерируем, пока не найдём свободный id
                while True:
                    group_id = generate_group_id(6)
                    if not svc.group_repo.exists(group_id):
                        break

                group = svc.create_group_and_assign(user_id, group_id)

            await state.clear()
            await message.answer(
                f"Группа создана.\n"
                f"ID вашей группы: <b>{group.id}</b>\n"
                "Этим ID можно делиться, чтобы другие присоединились.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if text == JOIN_GROUP_BTN:
            await state.set_state(RegistrationStates.WAITING_FOR_GROUP_ID)
            await message.answer(
                "Введите ID группы, к которой хотите присоединиться:",
                reply_markup=ReplyKeyboardRemove(),
            )

    # Обработка любого другого текста в состоянии MENU_CHOICE
    @dp.message(RegistrationStates.MENU_CHOICE)
    async def process_menu_invalid(message: Message):
        """
        Пользователь ввёл что-то руками вместо выбора кнопки.
        """
        await message.answer(
            "Пожалуйста, выберите один из вариантов на клавиатуре.",
            reply_markup=_main_menu_keyboard(),
        )

    # Пользователь вводит ID группы
    @dp.message(RegistrationStates.WAITING_FOR_GROUP_ID)
    async def process_group_id(message: Message, state: FSMContext):
        user_id = str(message.from_user.id)
        group_id = (message.text or "").strip()

        if not group_id:
            await message.answer("ID группы не может быть пустым. Введите ID ещё раз.")
            return

        joined = svc.join_group(user_id, group_id)
        if not joined:
            await message.answer(
                "Группа с таким ID не найдена. "
                "Проверьте ID и попробуйте ещё раз.",
            )
            return

        await state.clear()
        await message.answer(
            f"Вы успешно присоединились к группе <b>{group_id}</b>.",
            reply_markup=ReplyKeyboardRemove(),
        )
