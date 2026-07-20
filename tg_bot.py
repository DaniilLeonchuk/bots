import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")

EVENTS = [
    {
        "title": "Старый митап (прошёл)",
        "date": datetime(2026, 1, 10, 18, 0),
        "location": "Москва",
        "description": "Этого не должно быть видно.",
    },
    {
        "title": "Митап по Python",
        "date": datetime.now() + timedelta(hours=5),
        "location": "Москва, Лубянский проезд, 27",
        "description": "Пицца и разговоры про асинхронность.",
    },
    {
        "title": "Ивент для разработчиков",
        "date": datetime(2026, 7, 15, 19, 0),
        "location": "Москва, улица Большая Дмитровка, 5/6с5",
        "description": "Доклады про микросервисы.",
    },
    {
        "title": "IT HR Конфиренция",
        "date": datetime(2026, 7, 22, 11, 0),
        "location": "Онлайн (Zoom)",
        "description": "Как искать работу.",
    },
    {
        "title": "Хакатон по машинному обучению",
        "date": datetime(2026, 8, 2, 10, 0),
        "location": "Санкт-Петербург, улица Глинки, 11",
        "description": "24 часа, призовой фонд 500 000 ₽.",
    },
    {
        "title": "Конференция по кибербезапасности",
        "date": datetime(2026, 10, 8, 12, 0),
        "location": "Казань, улица Пушкина, 52",
        "description": "Доклады про защиту инфраструктуры.",
    },
]

# --- Тестовые события для проверки разницы между периодами ---
# Несколько штук в ближайшую неделю (чтобы "Неделя" отличалась от "Дня")
# и много штук в пределах месяца (чтобы у "Месяца" появлялось "Показать ещё").
_TEST_TITLES = [
    "Митап Java-разработчиков",
    "Воркшоп по Docker",
    "Лекция про базы данных",
    "Встреча Data Science клуба",
    "Открытая лекция по алгоритмам",
    "Демо-день стартапов",
    "Курс по системному дизайну",
    "Вебинар по тестированию",
    "Митап Frontend-разработчиков",
    "Хакатон для студентов",
    "Конференция по DevOps",
    "Встреча по Go-разработке",
]

for i, title in enumerate(_TEST_TITLES):
    EVENTS.append({
        "title": title,
        # первые несколько — в течение недели, остальные — в течение месяца
        "date": datetime.now() + timedelta(days=2 + i * 2, hours=i),
        "location": "Онлайн" if i % 2 == 0 else "Москва",
        "description": f"Тестовое событие №{i + 1} для проверки пагинации.",
    })

EVENTS.sort(key=lambda e: e["date"])

# у каждого события — стабильный id (позиция после сортировки),
# по нему храним избранное и раздаём кнопки конкретному событию
for _idx, _e in enumerate(EVENTS):
    _e["id"] = _idx

EVENTS_BY_ID = {e["id"]: e for e in EVENTS}

# user_id -> множество id избранных событий (в памяти, без БД)
FAVORITES: dict[int, set[int]] = {}

BATCH_SIZE = 10  # сколько событий отправлять за раз одним "куском"

PERIODS = {
    "day": ("за день", 1),
    "week": ("за неделю", 7),
    "month": ("за месяц", 30),
    "all": ("все события", None),
}

# текст кнопки -> ключ периода
PERIOD_BUTTONS = {
    "За день": "day",
    "За неделю": "week",
    "За месяц": "month",
    "Все события": "all",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 События")],
        [KeyboardButton(text="⭐ Избранное")],
        [KeyboardButton(text="ℹ️ О боте")],
    ],
    resize_keyboard=True,
)

events_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="За день"),
            KeyboardButton(text="За неделю"),
            KeyboardButton(text="За месяц"),
        ],
        [KeyboardButton(text="Все события")],
        [KeyboardButton(text="🏠 Главное меню")],
    ],
    resize_keyboard=True,
)


def filter_events(period: str):
    now = datetime.now()
    days = PERIODS[period][1]

    if days is None:
        return [e for e in EVENTS if e["date"] >= now]

    end = now + timedelta(days=days)
    return [e for e in EVENTS if now <= e["date"] <= end]


def get_events_for(period: str, user_id: int):
    """period может быть ключом из PERIODS или спец-значением "fav" (избранное)."""
    if period == "fav":
        ids = FAVORITES.get(user_id, set())
        favs = [EVENTS_BY_ID[i] for i in ids if i in EVENTS_BY_ID]
        favs.sort(key=lambda e: e["date"])
        return favs
    return filter_events(period)


def label_for(period: str) -> str:
    if period == "fav":
        return "Избранное"
    return PERIODS[period][0]


def event_text(e: dict) -> str:
    """Текст карточки одного события — теперь это отдельное сообщение, без 'X из Y'."""
    return (
        f"<b>{e['title']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>Дата:</b> {e['date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Место:</b> {e['location']}\n"
        f"{e['description']}"
    )


def is_favorite(user_id: int, event_id: int) -> bool:
    return event_id in FAVORITES.get(user_id, set())


def event_keyboard(event_id: int, favorite: bool) -> InlineKeyboardMarkup:
    """У каждого события — своя клавиатура. Сейчас в ней одна кнопка (избранное),
    но раз сообщение своё для каждого события, сюда легко добавить и другие
    кнопки (например 'Поделиться', 'Подробнее' и т.д.)."""
    text = "✅ В избранном (нажми, чтобы убрать)" if favorite else "⭐ В избранное"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, callback_data=f"fav_{event_id}"),
    ]])


def more_keyboard(period: str, next_offset: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="▶️ Показать ещё", callback_data=f"more_{period}_{next_offset}"),
    ]])


async def send_events_batch(answerable, events, period: str, offset: int, user_id: int):
    """Отправляет события отдельными сообщениями (каждое — со своими кнопками).
    Если событий больше BATCH_SIZE, показывает только часть + кнопку 'Показать ещё'."""
    if not events:
        await answerable.answer(
            f"<b>{label_for(period)}</b>\n\nНичего не найдено 😕",
            parse_mode="HTML",
        )
        return

    batch = events[offset:offset + BATCH_SIZE]
    for e in batch:
        await answerable.answer(
            event_text(e),
            reply_markup=event_keyboard(e["id"], is_favorite(user_id, e["id"])),
            parse_mode="HTML",
        )

    shown = offset + len(batch)
    remaining = len(events) - shown
    if remaining > 0:
        await answerable.answer(
            f"Показано {shown} из {len(events)} ({label_for(period)}).",
            reply_markup=more_keyboard(period, shown),
        )


@dp.message(CommandStart())
async def start(message: Message):
    if not message.from_user:
        return
    await message.answer(
        f"👋 Добро пожаловать, <b>{message.from_user.first_name}</b>!\n\n"
        "Я бот для поиска интересных событий.\n"
        "Выбери раздел в меню ниже",
        reply_markup=main_menu,
        parse_mode="HTML",
    )


@dp.message(F.text == "📅 События")
async def show_events(message: Message):
    await message.answer(
        "Раздел событий. Выбери период внизу 👇",
        reply_markup=events_menu,
    )
    events = filter_events("all")
    await send_events_batch(message, events, "all", 0, message.from_user.id)


@dp.message(F.text.in_(PERIOD_BUTTONS))
async def show_by_period(message: Message):
    period = PERIOD_BUTTONS[message.text]
    events = filter_events(period)
    await send_events_batch(message, events, period, 0, message.from_user.id)


@dp.message(F.text == "⭐ Избранное")
async def show_favorites(message: Message):
    events = get_events_for("fav", message.from_user.id)
    await send_events_batch(message, events, "fav", 0, message.from_user.id)


@dp.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message):
    await message.answer(
        "Главное меню 👇",
        reply_markup=main_menu,
    )


@dp.callback_query(F.data.startswith("fav_"))
async def toggle_favorite(callback: CallbackQuery):
    if not callback.data or not callback.message or not callback.from_user:
        return

    event_id = int(callback.data.split("_", 1)[1])
    user_id = callback.from_user.id
    favs = FAVORITES.setdefault(user_id, set())

    if event_id in favs:
        favs.discard(event_id)
        added = False
    else:
        favs.add(event_id)
        added = True

    await callback.message.edit_reply_markup(reply_markup=event_keyboard(event_id, added))
    await callback.answer("Добавлено в избранное ⭐" if added else "Убрано из избранного")


@dp.callback_query(F.data.startswith("more_"))
async def show_more(callback: CallbackQuery):
    if not callback.data or not callback.message or not callback.from_user:
        return

    _, period, offset_str = callback.data.split("_", 2)
    offset = int(offset_str)
    user_id = callback.from_user.id
    events = get_events_for(period, user_id)

    # убираем старую кнопку "Показать ещё", чтобы на неё нельзя было нажать повторно
    await callback.message.delete()
    await send_events_batch(callback.message, events, period, offset, user_id)
    await callback.answer()


@dp.message(F.text == "ℹ️ О боте")
async def about(message: Message):
    await message.answer(
        "<b>О боте</b>\n\n"
        "Этот бот показывает список актуальных событий "
        "и помогает быть в курсе интересных мероприятий.\n\n"
        "<b>Разработчик:</b> Леончук Даниил",
        parse_mode="HTML",
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())