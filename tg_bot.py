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
EVENTS.sort(key=lambda e: e["date"])

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
    days = PERIODS[period][1]
    if days is None:
        return EVENTS
    now = datetime.now()
    end = now + timedelta(days=days)
    return [e for e in EVENTS if now <= e["date"] <= end]


def event_card(events, index, period):
    period_name = PERIODS[period][0]
    if not events:
        return f"<b>События {period_name}</b>\n\nНичего не найдено 😕"

    e = events[index]
    return (
        f"<b>{e['title']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>Дата:</b> {e['date'].strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Место:</b> {e['location']}\n"
        f"{e['description']}\n\n"
        f"<i>Событие {index + 1} из {len(events)} ({period_name})</i>"
    )


def event_keyboard(events, index, period):
    # листалка нужна, только если событий больше одного
    if len(events) <= 1:
        return None

    prev_index = (index - 1) % len(events)
    next_index = (index + 1) % len(events)
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"event_{period}_{prev_index}"),
        InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"event_{period}_{next_index}"),
    ]])


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
    await message.answer(
        event_card(filter_events("all"), 0, "all"),
        reply_markup=event_keyboard(filter_events("all"), 0, "all"),
        parse_mode="HTML",
    )


@dp.message(F.text.in_(PERIOD_BUTTONS))
async def show_by_period(message: Message):
    period = PERIOD_BUTTONS[message.text]
    events = filter_events(period)
    await message.answer(
        event_card(events, 0, period),
        reply_markup=event_keyboard(events, 0, period),
        parse_mode="HTML",
    )


@dp.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message):
    await message.answer(
        "Главное меню 👇",
        reply_markup=main_menu,
    )


@dp.callback_query(F.data.startswith("event_"))
async def paginate_events(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return

    _, period, index = callback.data.split("_")
    index = int(index)
    events = filter_events(period)

    text = event_card(events, index, period)
    keyboard = event_keyboard(events, index, period)

    if callback.message.html_text != text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

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