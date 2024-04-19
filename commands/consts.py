import os

from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_IDS = set(map(int, os.getenv("ALLOWED_CHAT_IDS", "").split(",")))
TZ = timezone("Europe/Moscow")
GAME_PRICE = 2500
GAME_HOUR = 3
MAX_PLAYERS_COUNT = 14

TYPE_TEXT_ADD = {
    "i": "",
    "i+1": " от меня +1",
    "not_sure": " (под вопросом)",
}

REPLY_MARKUP = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Я играю", callback_data="i"),
            InlineKeyboardButton("+1 от меня", callback_data="i+1"),
            InlineKeyboardButton("-1 от меня", callback_data="i-1"),
        ],
        [
            InlineKeyboardButton("Я под вопросом", callback_data="not_sure"),
            InlineKeyboardButton("Я не играю", callback_data="not_play"),
        ],
        [
            InlineKeyboardButton("Решить вопросы 😎", callback_data="check_not_sure"),
        ]
    ]
)