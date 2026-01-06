# transport/telegram/expense_handlers.py

from enum import IntEnum  # (в этом примере IntEnum не обязателен, но можно использовать)
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from application.usecases.expenses import ExpenseService
from application.usecases.user_groups import UserGroupsService
from common.id_generator import generate_group_id  # если потребуется

LOG_CHANNEL_ID = -1002907150912

# ----- ТЕКСТЫ КНОПОК -----


# Кнопки верхнего меню выбора типа операции
EXPENSE_BTN = "Затрата"
TRANSFER_BTN = "Передача"  # пока только заглушка

# Кнопки выбора режима учета затраты
EXPENSE_FOR_ALL_BTN = "За всех в группе"
EXPENSE_SELECTIVE_BTN = "Выборочно"  # пока не реализуем

# Список категорий затрат
CATEGORIES = ["Реклама", "Релизы", "Контент", "Концерты", "Прочее"]


# ----- СОСТОЯНИЯ FSM (диалога) -----


class ExpenseStates(StatesGroup):
    """
    Набор шагов (состояний) диалога учета операций.

    FSM — конечный автомат: бот всегда находится в каком-то одном
    состоянии и реагирует на сообщения по-разному в зависимости от него.
    """

    # Пользователь выбирает: что он хочет сделать — затрата или передача
    MAIN_MENU = State()

    # Пользователь выбирает режим затраты: за всех / выборочно
    EXPENSE_MODE = State()

    # Пользователь выбирает категорию
    EXPENSE_CATEGORY = State()

    # Пользователь вводит текст описания (комментарий)
    EXPENSE_COMMENT = State()

    # Пользователь вводит сумму
    EXPENSE_AMOUNT = State()


# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КЛАВИАТУР -----


def _main_operation_keyboard() -> InlineKeyboardMarkup:
    """
    Формирует inline-клавиатуру для выбора типа операции.
    Эти кнопки появляются прямо под сообщением.

    callback_data:
    - "op_expense"  – пользователь выбрал "Затрата"
    - "op_transfer" – пользователь выбрал "Передача"
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=EXPENSE_BTN,          # Текст на кнопке
                    callback_data="op_expense"  # Идентификатор, который придёт в обработчик
                )
            ],
            [
                InlineKeyboardButton(
                    text=TRANSFER_BTN,
                    callback_data="op_transfer"
                )
            ],
        ]
    )


# >>> ИЗМЕНЕНО: режим расхода теперь тоже inline-клавиатура,
# >>> чтобы кнопки были под сообщением, а не снизу экрана.
def _expense_mode_keyboard() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора режима затраты: за всех или выборочно.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=EXPENSE_FOR_ALL_BTN,
                    callback_data="mode_all",       # режим "за всех"
                )
            ],
            [
                InlineKeyboardButton(
                    text=EXPENSE_SELECTIVE_BTN,
                    callback_data="mode_selective",  # режим "выборочно"
                )
            ],
        ]
    )


# >>> ИЗМЕНЕНО: категории тоже как inline-кнопки.
def _category_keyboard() -> InlineKeyboardMarkup:
    """
    Inline-клавиатура для выбора категории затрат.
    Каждая категория — отдельная кнопка в отдельной строке.

    callback_data имеет вид 'cat:<Название категории>'.
    """
    keyboard_rows = []

    for cat in CATEGORIES:
        button = InlineKeyboardButton(
            text=cat,
            callback_data=f"cat:{cat}",
        )
        # Каждую кнопку кладём в отдельную строку
        keyboard_rows.append([button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def register_expense_handlers(
    dp: Dispatcher,
    user_groups_svc: UserGroupsService,
    expense_svc: ExpenseService,
) -> None:
    """
    Функция, которую вызываем из main.py,
    чтобы зарегистрировать хэндлеры, относящиеся к учёту затрат.

    Параметры:
    - dp: Dispatcher aiogram (центр маршрутизации апдейтов).
    - user_groups_svc: сервис, который знает, к какой группе привязан пользователь.
    - expense_svc: сервис, который создаёт записи об операциях в Google Sheets.
    """

    # ---------- ШАГ 1. Команда /operation ----------

    @dp.message(Command("operation"))
    async def cmd_operation(message: Message, state: FSMContext):
        """
        Старт диалога выбора операции (Затрата / Передача).

        1. Проверяем, привязан ли пользователь к какой-то группе.
        2. Если нет — просим сначала пройти /start.
        3. Если да — сохраняем group_id в состояние и показываем меню.
        """
        user_id = str(message.from_user.id)

        # Пытаемся получить текущую группу по user_id
        group = user_groups_svc.get_current_user_group(user_id)
        if group is None:
            # Группы нет — очищаем состояние и просим пользователя
            # сначала выбрать/создать группу
            await state.clear()
            await message.answer(
                "Вы ещё не выбрали группу.\n"
                "Сначала используйте команду /start и выберите или создайте группу.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        # Сохраняем group_id в памяти FSM, чтобы не искать его каждый раз
        await state.update_data(group_id=group.id)

        # Переводим FSM в состояние выбора типа операции
        await state.set_state(ExpenseStates.MAIN_MENU)

        # Показываем inline-клавиатуру с кнопками 'Затрата' и 'Передача'
        await message.answer(
            "Выберите тип операции:",
            reply_markup=_main_operation_keyboard(),
        )

    # ---------- ШАГ 2. Обработка выбора Затрата / Передача ----------

    # >>> ИЗМЕНЕНО: вместо обработки text-сообщений
    # >>> добавляем обработчик callback-кнопок.
    @dp.callback_query(
        ExpenseStates.MAIN_MENU,
        F.data.in_({"op_expense", "op_transfer"}),
    )
    async def process_main_menu_callback(callback: CallbackQuery, state: FSMContext):
        """
        Реакция на выбор пользователя в главном меню по inline-кнопке.

        Если выбрана 'Затрата' — идём дальше по сценарию.
        Если 'Передача' — пока выводим заглушку.
        """
        data = callback.data

        if data == "op_expense":
            # Переводим FSM в состояние выбора режима расхода
            await state.set_state(ExpenseStates.EXPENSE_MODE)

            # Меняем текст сообщения и показываем следующее меню (режим затраты)
            await callback.message.answer(
                "Выберите, как учитывать затрату:",
                reply_markup=_expense_mode_keyboard(),
            )
            await callback.answer()
            return

        if data == "op_transfer":
            # Логику передач пока не реализуем,
            # поэтому просто сообщаем об этом.
            await callback.message.answer(
                "Учёт передачи денег пока не реализован.",
            )
            await state.clear()
            await callback.answer()
            return

    # >>> СТАРЫЙ обработчик по тексту для MAIN_MENU можно удалить.
    # >>> Оставим только "страховку" на случай произвольного текста.
    @dp.message(ExpenseStates.MAIN_MENU)
    async def process_main_menu_invalid(message: Message):
        """
        Если в состоянии MAIN_MENU пользователь ввёл что-то руками
        (не нажал кнопку), повторно показываем inline-клавиатуру.
        """
        await message.answer(
            "Пожалуйста, выберите один из вариантов на кнопках под сообщением.",
            reply_markup=_main_operation_keyboard(),
        )

    # ---------- ШАГ 3. Выбор режима расхода: За всех / Выборочно ----------

    # >>> ИЗМЕНЕНО: теперь режим выбираем через inline-кнопки,
    # >>> поэтому нужен callback_query-хэндлер.
    @dp.callback_query(
        ExpenseStates.EXPENSE_MODE,
        F.data.in_({"mode_all", "mode_selective"}),
    )
    async def process_expense_mode_callback(callback: CallbackQuery, state: FSMContext):
        """
        Обработка выбора режима затраты.

        Сейчас реализуем только 'За всех в группе',
        режим 'Выборочно' выводит заглушку.
        """
        data = callback.data

        if data == "mode_all":
            # Переходим к следующему шагу — выбор категории
            await state.set_state(ExpenseStates.EXPENSE_CATEGORY)
            await callback.message.answer(
                "Выберите категорию затраты:",
                reply_markup=_category_keyboard(),
            )
            await callback.answer()
            return

        if data == "mode_selective":
            await callback.message.answer(
                "Режим 'Выборочно' пока не реализован.",
            )
            await state.clear()
            await callback.answer()
            return

    # >>> "Страховка" на случай произвольного текста в этом состоянии.
    @dp.message(ExpenseStates.EXPENSE_MODE)
    async def process_expense_mode_invalid(message: Message):
        """
        Пользователь что-то ввёл руками в состоянии EXPENSE_MODE —
        просим выбрать одну из кнопок под сообщением.
        """
        await message.answer(
            "Пожалуйста, выберите один из вариантов на кнопках под сообщением.",
            reply_markup=_expense_mode_keyboard(),
        )

    # ---------- ШАГ 4. Выбор категории ----------

    # >>> ИЗМЕНЕНО: категории теперь выбираются по callback_data "cat:<категория>".
    @dp.callback_query(
        ExpenseStates.EXPENSE_CATEGORY,
        F.data.startswith("cat:"),
    )
    async def process_category_callback(callback: CallbackQuery, state: FSMContext):
        """
        Сохраняем выбранную категорию (из callback_data) и переходим к вводу описания.
        """
        # callback.data имеет вид 'cat:Реклама'
        category = callback.data.removeprefix("cat:")

        # Запоминаем выбранную категорию в FSM
        await state.update_data(category=category)

        # Следующее состояние — ввод комментария
        await state.set_state(ExpenseStates.EXPENSE_COMMENT)
        await callback.message.answer(
            f"Категория: {category}\n\nВведите описание затраты (комментарий):",
        )
        await callback.answer()

    # >>> Если вдруг пользователь напишет текст вместо нажатия кнопки.
    @dp.message(ExpenseStates.EXPENSE_CATEGORY)
    async def process_category_invalid(message: Message):
        """
        Если введён текст, не совпадающий с ожидаемыми callback-кнопками —
        повторно показываем inline-клавиатуру с категориями.
        """
        await message.answer(
            "Пожалуйста, выберите категорию с помощью кнопок под сообщением.",
            reply_markup=_category_keyboard(),
        )

    # ---------- ШАГ 5. Ввод описания ----------

    @dp.message(ExpenseStates.EXPENSE_COMMENT)
    async def process_comment(message: Message, state: FSMContext):
        """
        Получаем текст описания и сохраняем его в FSM,
        затем просим ввести сумму.
        """
        comment = (message.text or "").strip()
        await state.update_data(comment=comment)

        # Переходим к следующему состоянию — ввод суммы
        await state.set_state(ExpenseStates.EXPENSE_AMOUNT)
        await message.answer(
            "Введите сумму затраты (число, например 123.45):",
            reply_markup=ReplyKeyboardRemove(),
        )

    # ---------- ШАГ 6. Ввод суммы и создание операции ----------

    @dp.message(ExpenseStates.EXPENSE_AMOUNT)
    async def process_amount(message: Message, state: FSMContext):
        """
        Здесь пользователь вводит сумму.

        1. Проверяем, что это число > 0.
        2. Берём из FSM сохранённые group_id, category, comment.
        3. Вызываем ExpenseService.create_expense_for_all.
        4. Очищаем состояние и пишем пользователю результат.
        """
        # Заменяем запятую на точку, чтобы поддержать формат "123,45"
        text_amount = (message.text or "").replace(",", ".").strip()

        try:
            amount = float(text_amount)
        except ValueError:
            # Не удалось преобразовать строку к числу
            await message.answer(
                "Не удалось понять сумму. Введите число, например 123.45:",
            )
            return

        if amount <= 0:
            await message.answer(
                "Сумма должна быть больше нуля. Введите ещё раз:",
            )
            return

        # Достаём всё, что накопили ранее: group_id, category, comment
        data = await state.get_data()
        group_id = data.get("group_id")
        category = data.get("category")
        comment = data.get("comment", "")

        user_id = str(message.from_user.id)
        user_name = message.from_user.full_name  # пригодится, если будем записывать в users

        if not group_id or not category:
            # Если чего-то важного не хватает — сбрасываем диалог
            await state.clear()
            await message.answer(
                "Что-то пошло не так с данными операции. "
                "Попробуйте начать заново командой /operation.",
            )
            return

        # Вызываем бизнес-логику:
        # создаём затрату типа 'expense' для всех участников группы.
        op_id = expense_svc.create_expense_for_all(
            user_id=user_id,
            group_id=group_id,
            category=category,
            comment=comment,
            amount=amount,
        )

        # ---------- ЛОГИРОВАНИЕ В КАНАЛ ----------  #
        # Формируем человекочитаемый текст операции со всеми атрибутами.
        log_text = (
            "Новая операция зарегистрирована:\n"
            f"ID операции: {op_id}\n"
            f"Пользователь: {user_name} (id={user_id})\n"
            f"Группа: {group_id}\n"
            f"Тип: Затрата за всех в группе\n"
            f"Категория: {category}\n"
            f"Комментарий: {comment or '—'}\n"
            f"Сумма: {amount}\n"
        )

        # Отправляем сообщение в канал логов.
        # message.bot — это экземпляр Bot, через который работает хендлер.
        await message.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_text,
        )
        # ---------- КОНЕЦ БЛОКА ЛОГИРОВАНИЯ ----------

        # Очищаем состояние FSM и сообщаем пользователю результат
        await state.clear()
        await message.answer(
            f"Затрата успешно зарегистрирована.\n"
            f"ID операции: <code>{op_id}</code>",
            reply_markup=ReplyKeyboardRemove(),
        )
