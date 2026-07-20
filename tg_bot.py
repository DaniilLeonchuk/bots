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
    {
        "title": "Митап Java-разработчиков",
        "date": datetime(2026, 7, 24, 19, 0),
        "location": "Онлайн (Zoom)",
        "description": "Обсуждение новых фич Java 22 и производительности JVM.",
    },
    {
        "title": "Воркшоп по Docker",
        "date": datetime(2026, 7, 26, 18, 30),
        "location": "Москва, ул. Тверская, 12",
        "description": "Практика: контейнеризация приложения с нуля до продакшена.",
    },
    {
        "title": "Лекция про базы данных",
        "date": datetime(2026, 7, 28, 17, 0),
        "location": "Онлайн (Zoom)",
        "description": "Индексы, транзакции и оптимизация запросов в PostgreSQL.",
    },
    {
        "title": "Встреча Data Science клуба",
        "date": datetime(2026, 7, 30, 19, 0),
        "location": "Санкт-Петербург, Невский проспект, 100",
        "description": "Разбор реальных кейсов применения ML в бизнесе.",
    },
    {
        "title": "Открытая лекция по алгоритмам",
        "date": datetime(2026, 8, 1, 18, 0),
        "location": "Москва, Ленинский проспект, 4",
        "description": "Разбор задач на графы и динамическое программирование.",
    },
    {
        "title": "Демо-день стартапов",
        "date": datetime(2026, 8, 4, 12, 0),
        "location": "Москва, Сколково",
        "description": "Питчи молодых команд перед инвесторами.",
    },
    {
        "title": "Курс по системному дизайну",
        "date": datetime(2026, 8, 6, 19, 0),
        "location": "Онлайн (Zoom)",
        "description": "Проектирование высоконагруженных систем на практике.",
    },
    {
        "title": "Вебинар по тестированию",
        "date": datetime(2026, 8, 8, 18, 0),
        "location": "Онлайн (Zoom)",
        "description": "Автоматизация тестирования: с чего начать и как не бросить.",
    },
    {
        "title": "Митап Frontend-разработчиков",
        "date": datetime(2026, 8, 10, 19, 0),
        "location": "Москва, Проспект Мира, 33",
        "description": "React, производительность и новые подходы к вёрстке.",
    },
    {
        "title": "Хакатон для студентов",
        "date": datetime(2026, 8, 14, 10, 0),
        "location": "Казань, ул. Кремлёвская, 18",
        "description": "48 часов на разработку прототипа, менторы и призы.",
    },
    {
        "title": "Конференция по DevOps",
        "date": datetime(2026, 8, 18, 11, 0),
        "location": "Санкт-Петербург, Пироговская наб., 5/2",
        "description": "CI/CD, Kubernetes и автоматизация инфраструктуры.",
    },
    {
        "title": "Встреча по Go-разработке",
        "date": datetime(2026, 8, 20, 19, 0),
        "location": "Онлайн (Zoom)",
        "description": "Конкурентность в Go: горутины, каналы и лучшие практики.",
    },
]
EVENTS.sort(key=lambda e: e["date"])

# у каждого события — стабильный id (позиция после сортировки),
# по нему храним избранное и раздаём кнопки конкретному событию
for _idx, _e in enumerate(EVENTS):
    _e["id"] = _idx

EVENTS_BY_ID = {e["id"]: e for e in EVENTS}

# user_id -> множество id избранных событий (в памяти, без БД)
FAVORITES: dict[int, set[int]] = {}

# Если событий в выборке <= этого числа — шлём их отдельными сообщениями
# (у каждого своя кнопка избранного). Если больше — используем один
# переключаемый "карточный" вид с кнопками "Назад"/"Вперёд" + избранное.
SWITCH_THRESHOLD = 5

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


def is_favorite(user_id: int, event_id: int) -> bool:
    return event_id in FAVORITES.get(user_id, set())


def fav_button_text(favorite: bool) -> str:
    return "✅ В избранном (нажми, чтобы убрать)" if favorite else "⭐ В избранное"


# ---------- Режим "отдельные сообщения" (когда событий <= SWITCH_THRESHOLD) ----------

def single_event_text(e: dict) -> str:
    return (
        f"<b>{e['title']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>Дата:</b> {e['date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Место:</b> {e['location']}\n"
        f"{e['description']}"
    )


def single_event_keyboard(event_id: int, favorite: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=fav_button_text(favorite), callback_data=f"fav_{event_id}"),
    ]])


# ---------- Режим "переключаемая карточка" (когда событий > SWITCH_THRESHOLD) ----------

def card_text(events, index, period) -> str:
    period_name = label_for(period)
    e = events[index]
    return (
        f"<b>{e['title']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>Дата:</b> {e['date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Место:</b> {e['location']}\n"
        f"{e['description']}\n\n"
        f"<i>Событие {index + 1} из {len(events)} ({period_name})</i>"
    )


def card_keyboard(events, index, period, user_id) -> InlineKeyboardMarkup:
    e = events[index]
    prev_index = (index - 1) % len(events)
    next_index = (index + 1) % len(events)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"nav_{period}_{prev_index}"),
            InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"nav_{period}_{next_index}"),
        ],
        [
            InlineKeyboardButton(
                text=fav_button_text(is_favorite(user_id, e["id"])),
                callback_data=f"navfav_{period}_{index}",
            ),
        ],
    ])


# ---------- Общая точка входа: показать события за период/избранное ----------

async def send_events(answerable, events, period: str, user_id: int):
    if not events:
        await answerable.answer(
            f"<b>{label_for(period)}</b>\n\nНичего не найдено 😕",
            parse_mode="HTML",
        )
        return

    if len(events) <= SWITCH_THRESHOLD:
        # событий немного — просто шлём каждое отдельным сообщением со своей кнопкой
        for e in events:
            await answerable.answer(
                single_event_text(e),
                reply_markup=single_event_keyboard(e["id"], is_favorite(user_id, e["id"])),
                parse_mode="HTML",
            )
    else:
        # событий много — одна переключаемая карточка вместо простыни сообщений
        await answerable.answer(
            card_text(events, 0, period),
            reply_markup=card_keyboard(events, 0, period, user_id),
            parse_mode="HTML",
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
    await send_events(message, events, "all", message.from_user.id)


@dp.message(F.text.in_(PERIOD_BUTTONS))
async def show_by_period(message: Message):
    period = PERIOD_BUTTONS[message.text]
    events = filter_events(period)
    await send_events(message, events, period, message.from_user.id)


@dp.message(F.text == "⭐ Избранное")
async def show_favorites(message: Message):
    events = get_events_for("fav", message.from_user.id)
    await send_events(message, events, "fav", message.from_user.id)


@dp.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message):
    await message.answer(
        "Главное меню 👇",
        reply_markup=main_menu,
    )


@dp.callback_query(F.data.startswith("nav_"))
async def navigate_card(callback: CallbackQuery):
    """Переключение карточек кнопками 'Назад'/'Вперёд' (режим > SWITCH_THRESHOLD)."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    _, period, index_str = callback.data.split("_", 2)
    index = int(index_str)
    user_id = callback.from_user.id
    events = get_events_for(period, user_id)

    if not events:
        await callback.message.edit_text(
            f"<b>{label_for(period)}</b>\n\nНичего не найдено 😕", parse_mode="HTML"
        )
        await callback.answer()
        return

    index = index % len(events)
    await callback.message.edit_text(
        card_text(events, index, period),
        reply_markup=card_keyboard(events, index, period, user_id),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("navfav_"))
async def toggle_favorite_in_card(callback: CallbackQuery):
    """Кнопка избранного внутри переключаемой карточки."""
    if not callback.data or not callback.message or not callback.from_user:
        return

    _, period, index_str = callback.data.split("_", 2)
    index = int(index_str)
    user_id = callback.from_user.id

    # список на момент нажатия (до переключения избранного)
    events_before = get_events_for(period, user_id)
    if not events_before or index >= len(events_before):
        await callback.answer()
        return

    event_id = events_before[index]["id"]
    favs = FAVORITES.setdefault(user_id, set())
    if event_id in favs:
        favs.discard(event_id)
        added = False
    else:
        favs.add(event_id)
        added = True

    # пересчитываем список (для "избранного" он мог измениться в размере)
    events_after = get_events_for(period, user_id)
    if not events_after:
        await callback.message.edit_text(
            f"<b>{label_for(period)}</b>\n\nНичего не найдено 😕", parse_mode="HTML"
        )
        await callback.answer("Убрано из избранного")
        return

    new_index = min(index, len(events_after) - 1)
    await callback.message.edit_text(
        card_text(events_after, new_index, period),
        reply_markup=card_keyboard(events_after, new_index, period, user_id),
        parse_mode="HTML",
    )
    await callback.answer("Добавлено в избранное ⭐" if added else "Убрано из избранного")


@dp.callback_query(F.data.startswith("fav_"))
async def toggle_favorite_single(callback: CallbackQuery):
    """Кнопка избранного у отдельного сообщения (режим <= SWITCH_THRESHOLD)."""
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

    await callback.message.edit_reply_markup(reply_markup=single_event_keyboard(event_id, added))
    await callback.answer("Добавлено в избранное ⭐" if added else "Убрано из избранного")


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