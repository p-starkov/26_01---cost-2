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
from application.usecases.reports import ReportService
from common.id_generator import generate_group_id  # если потребуется


LOG_CHANNEL_ID = -1002907150912

# ----- ТЕКСТЫ КНОПОК -----


# Кнопки верхнего меню выбора типа операции
EXPENSE_BTN = "Затрата"
TRANSFER_BTN = "Передача"  # пока только заглушка

# Кнопки выбора режима учета затраты
EXPENSE_FOR_ALL_BTN = "За всех в группе"
EXPENSE_SELECTIVE_BTN = "Выборочно"  # пока не реализуем

# Кнопки выбора отчета
REPORT_BALANCE_BTN = "Баланс"

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

     # пользователь выбирает получателя для передачи
    TRANSFER_TARGET = State()


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


def _report_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура с перечнем доступных отчётов.
    Пока доступен один отчёт — 'Баланс'.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=REPORT_BALANCE_BTN,
                    callback_data="report:balance",
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

def _transfer_target_keyboard(
    group_member_ids: list[str],
    current_user_id: str,
    user_groups_svc: UserGroupsService,
) -> InlineKeyboardMarkup:
    """
    Строит inline-клавиатуру для выбора получателя передачи.

    В подписи кнопки используем имя пользователя из листа users,
    если оно есть, иначе показываем его id.
    """
    buttons: list[list[InlineKeyboardButton]] = []

    for uid in group_member_ids:
        if uid == current_user_id:
            # Себя не показываем как возможного получателя
            continue

        # Пытаемся получить информацию о пользователе из репозитория users
        # user_repo реализует интерфейс IUserRepository
        user_info = user_groups_svc.user_repo.get_by_id(uid)
        if user_info is not None and getattr(user_info, "name", None):
            display_name = user_info.name
        else:
            # Fallback: если имени нет, показываем id
            display_name = f"Пользователь {uid}"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=display_name,
                    callback_data=f"trg:{uid}",
                )
            ]
        )

    # На случай, если в группе один человек (нет других получателей)
    if not buttons:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="В группе нет других участников",
                    callback_data="trg:none",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def register_expense_handlers(
    dp: Dispatcher,
    user_groups_svc: UserGroupsService,
    expense_svc: ExpenseService,
    report_svc: ReportService,
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
            # Помечаем в FSM, что сейчас сценарий передачи
            await state.update_data(mode="transfer")

            # Достаём group_id и список участников группы
            data_state = await state.get_data()
            group_id = data_state.get("group_id")
            current_user_id = str(callback.from_user.id)

            # Используем тот же способ, что и в ExpenseService.create_expense_for_all:
            # читаем все строки userGroups и фильтруем по group_id.
            links, _ = user_groups_svc.user_group_repo._read_all_rows()  # временное решение
            member_ids: list[str] = []
            if links:
                for row in links:
                    if not row:
                        continue
                    row_user_id = row[0].strip()
                    row_group_id = row[1].strip().upper() if len(row) > 1 else ""
                    if row_group_id == str(group_id).strip().upper():
                        member_ids.append(row_user_id)

            # Переводим FSM в состояние выбора получателя
            await state.set_state(ExpenseStates.TRANSFER_TARGET)

            # Показываем inline-клавиатуру со списком участников
            await callback.message.answer(
                "Выберите, кому передаёте деньги:",
                reply_markup=_transfer_target_keyboard(
                    group_member_ids=member_ids,
                    current_user_id=current_user_id,
                    user_groups_svc=user_groups_svc,
                ),
            )

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

    # ---------- ШАГ 3a. Выбор получателя для передачи ----------

    @dp.callback_query(
        ExpenseStates.TRANSFER_TARGET,
        F.data.startswith("trg:"),
    )
    async def process_transfer_target_callback(
        callback: CallbackQuery,
        state: FSMContext,
    ):
        """
        Обработка выбора получателя передачи.

        callback_data имеет вид 'trg:<user_id>'.
        """
        raw = callback.data  # например 'trg:123456'
        _, target_user_id = raw.split(":", 1)

        if target_user_id == "none":
            # Нет других участников — прерываем сценарий
            await state.clear()
            await callback.message.answer(
                "В группе нет других участников, передача невозможна.",
            )
            await callback.answer()
            return

        # Сохраняем id получателя в FSM
        await state.update_data(transfer_target_id=target_user_id)

        # Переходим к вводу описания
        await state.set_state(ExpenseStates.EXPENSE_COMMENT)
        await callback.message.answer(
            "Введите описание передачи (комментарий):",
        )
        await callback.answer()


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
        mode = data.get("mode", "expense")
        transfer_target_id = data.get("transfer_target_id")

        user_id = str(message.from_user.id)
        user_name = message.from_user.full_name  # пригодится, если будем записывать в users

        # Вызываем бизнес-логику:
        # создаём операцию типа 'expense' или 'transfer' в зависимости от mode.

        if mode == "transfer":
            if not group_id or not transfer_target_id:
                await state.clear()
                await message.answer(
                    "Не удалось определить данные передачи. Не указана группа пользователя или получатель."
                    "Попробуйте начать заново командой /operation.",
                )
                return

            op_id = expense_svc.create_transfer(
                group_id=group_id, 
                from_user_id=user_id,
                to_user_id=transfer_target_id,
                comment=comment,
                amount=amount,
            )
        else:
            if not group_id or not category:
                await state.clear()
                await message.answer(
                    "Что-то пошло не так с данными операции. Не указана группа пользователя или категория."
                    "Попробуйте начать заново командой /operation.",
                )
                return

            op_id = expense_svc.create_expense_for_all(
                user_id=user_id,
                group_id=group_id,
                category=category,
                comment=comment,
                amount=amount,
            )



        # ---------- ЛОГИРОВАНИЕ В КАНАЛ ----------  #
        # Формируем человекочитаемый текст операции со всеми атрибутами.
        operation_type = "transfer" if mode == "transfer" else "expense"

        log_category = category if mode != "transfer" else "transfer"
        log_text = (
            "Новая операция зарегистрирована:\n"
            f"Тип: {operation_type}\n"
            f"ID операции: {op_id}\n"
            f"Пользователь: {user_name} (id={user_id})\n"
            f"Группа: {group_id}\n"
            f"Категория: {log_category}\n"
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

        result_text = (
            "Передача успешно зарегистрирована.\n"
            if mode == "transfer"
            else "Затрата успешно зарегистрирована.\n"
        )

        await message.answer(
            result_text + f"ID операции: <code>{op_id}</code>",
            reply_markup=ReplyKeyboardRemove(),
        )
    
    @dp.message(Command("report"))
    async def cmd_report(message: Message, state: FSMContext):
            await state.clear()
            await message.answer(
                "Выберите отчёт:",
                reply_markup=_report_menu_keyboard(),
            )

    @dp.callback_query(F.data == "report:balance")
    async def process_report_balance(callback: CallbackQuery, state: FSMContext):
        """
        Обработчик выбора отчёта 'Баланс'.

        1. Определяем текущую группу пользователя.
        2. Запрашиваем отчёт у ReportService.
        3. Отправляем текст пользователю.
        """
        user_id = str(callback.from_user.id)

        # Текущая группа по userGroups
        link = user_groups_svc.user_group_repo.get_by_user_id(user_id)
        if link is None:
            await state.clear()
            await callback.message.answer(
                "Вы ещё не выбрали группу.\n"
                "Сначала используйте команду /start и выберите или создайте группу.",
            )
            await callback.answer()
            return

        group_id = link.group_id

        # Получаем уже отформатированный текст отчёта
        report_text = report_svc.format_balance_report(group_id)

        await callback.message.answer(report_text)
        await callback.answer()
