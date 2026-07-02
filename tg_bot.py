import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import CommandStart
import os



BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

DEVELOPER = "@event_leon_bot"


EVENTS = [
    {
        "title": "Ивент для разработчиков",
        "date": "15 июля 2026, 19:00",
        "location": "Москва, улица Большая Дмитровка, 5/6с5",
        "description": "Доклады про микросервисы.",
    },
    {
        "title": "IT HR Конфиренция",
        "date": "22 июля 2026, 11:00",
        "location": "Онлайн (Zoom)",
        "description": "Как искать работу.",
    },
    {
        "title": "Хакатон по машинному обучению",
        "date": "2 августа 2026, начало в 10:00",
        "location": "Санкт-Петербург, улица Глинки, 11",
        "description": "24 часа, призовой фонд 500 000 ₽.",
    },
]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 События")],
        [KeyboardButton(text="ℹ️ О боте")],
    ],
    resize_keyboard=True,
)


def event_card(index: int) -> str:
    e = EVENTS[index]
    return (
        f"<b>{e['title']}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"<b>Дата:</b> {e['date']}\n"
        f"<b>Место:</b> {e['location']}\n"
        f"{e['description']}\n\n"
        f"<i>Событие {index + 1} из {len(EVENTS)}</i>"
    )


def event_keyboard(index: int) -> InlineKeyboardMarkup:
    prev_index = (index - 1) % len(EVENTS)
    next_index = (index + 1) % len(EVENTS)
    row = [
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"event_{prev_index}"),
        InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"event_{next_index}"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


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
        event_card(0),
        reply_markup=event_keyboard(0),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("event_"))
async def paginate_events(callback: CallbackQuery):
    if not callback.data or not callback.message:
        return
    index = int(callback.data.split("_")[1])
    await callback.message.edit_text(
        event_card(index),
        reply_markup=event_keyboard(index),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(F.text == "ℹ️ О боте")
async def about(message: Message):
    await message.answer(
        "<b>О боте</b>\n\n"
        "Этот бот показывает список актуальных событий "
        "и помогает быть в курсе интересных мероприятий.\n\n"
        f"<b>Разработчик:</b> Леончук Даниил",
        parse_mode="HTML",
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())