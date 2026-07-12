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

pythonEVENTS = [
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
]

PERIODS = {
    "day": ("за день", 1),
    "week": ("за неделю", 7),
    "month": ("за месяц", 30),
    "all": ("все события", None),
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
    rows = []

    # навигация по событиям (только если есть что листать)
    if len(events) > 1:
        prev_index = (index - 1) % len(events)
        next_index = (index + 1) % len(events)
        rows.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"event_{period}_{prev_index}"),
            InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"event_{period}_{next_index}"),
        ])

    # выбор периода
    rows.append([
        InlineKeyboardButton(text="За день", callback_data="event_day_0"),
        InlineKeyboardButton(text="За неделю", callback_data="event_week_0"),
        InlineKeyboardButton(text="За месяц", callback_data="event_month_0"),
    ])
    rows.append([
        InlineKeyboardButton(text="Все события", callback_data="event_all_0"),
    ])
    rows.append([
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    events = filter_events("all")
    await message.answer(
        event_card(events, 0, "all"),
        reply_markup=event_keyboard(events, 0, "all"),
        parse_mode="HTML",
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

    # чтобы телеграм не ругался, если текст не поменялся
    if callback.message.html_text != text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@dp.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery):
    if not callback.message:
        return
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню 👇",
        reply_markup=main_menu,
    )
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