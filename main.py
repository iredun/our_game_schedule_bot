import logging
import math
import os
from copy import deepcopy
from datetime import datetime, timedelta

from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    PicklePersistence,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode
from dotenv import load_dotenv
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_IDS = set(map(int, os.getenv("ALLOWED_CHAT_IDS", "").split(",")))
PERSISTENCE = PicklePersistence(filepath="chats_data.dat", update_interval=10)
TZ = timezone("Europe/Moscow")
GAME_PRICE = 2500
GAME_HOUR = 3

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
    ]
)


def pretty_user_name(user: User, custom_name: str = "") -> str:
    if custom_name:
        return f"[{custom_name}](tg://user?id={user.id})"

    user_full_name = " ".join(
        map(
            lambda s: s.strip() if s else "",
            [user.first_name, user.last_name],
        )
    ).strip()

    if not user_full_name:
        user_full_name = "@" + user.username

    return f"[{user_full_name}](tg://user?id={user.id})"


def generate_message(game):
    price = game.get("price", GAME_PRICE)
    hour = game.get("hour", GAME_HOUR)
    total_price = price * hour
    price_per_user = math.ceil(total_price / len(game["users"]))
    users_numeric_list = [
        f"{i}. {user['username']}{user['type_text']}"
        for i, user in enumerate(game["users"], 1)
    ]
    users_text = "\n".join(users_numeric_list)
    return (
        f"{game['date_text']} {game['user_message']}\n"
        f"Список участников:\n"
        f"{users_text}"
        f"\n------\n"
        f"Цена за час: `{price}₽`\n"
        f"Продолжительность игры: `{hour}ч.`\n"
        f"Стоимость игры: `{total_price}₽`\n"
        f"С одного игрока: `{price_per_user}₽`"
    )


async def new_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"New not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return

    try:
        date_time = parse(context.args.pop(0))
        date_time = date_time.replace(tzinfo=TZ)
        if date_time < datetime.now(tz=TZ):
            date_time = date_time + relativedelta(months=1)
    except Exception as e:
        logging.warning(f"Error while parsing date - {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            parse_mode=ParseMode.MARKDOWN,
            text="Неверный формат сообщения!\n"
            "Формат: /new ДАТА ТЕКСТ\n"
            "Пример: `/new 10 #игра` (Дата текущего месяца)\n"
            "Пример: `/new 10.10.2023 #игра` (Конкретная дата)\n"
            "Если хотим установить цену (за час) или продолжительность игры, то пишем так:\n"
            "`/new 10.10.2023 #игра ₽1000 ч.2`",
        )
        return

    price = GAME_PRICE
    hour = GAME_HOUR

    logging.info(f"New game - {date_time} {context.args}")

    for arg in context.args:
        if arg.startswith("₽"):
            try:
                price = int(arg[1:])
            except Exception as e:
                price = GAME_PRICE

            if price < 0:
                price = GAME_PRICE

        if arg.startswith("ч."):
            try:
                hour = int(arg[2:])
            except Exception as e:
                hour = GAME_HOUR

            if hour < 0:
                hour = GAME_HOUR

    context.args = list(filter(lambda arg: not arg.startswith("₽") or not arg.startswith("ч."), context.args))

    user_message = " ".join(context.args)

    date_text = date_time.strftime("%d.%m.%Y")
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=REPLY_MARKUP,
        text=f"{date_text} {user_message}\n" f"Список участников:\n\n",
    )

    context.chat_data[message.message_id] = {
        "date": date_time,
        "date_text": date_text,
        "user_message": user_message,
        "author": update.effective_user.id,
        "users": [],
        "price": price,
        "hour": hour,
    }


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    message_id = query.message.message_id
    user_id = query.from_user.id

    if_change = False

    if query.data in TYPE_TEXT_ADD:
        for user in context.chat_data[message_id]["users"]:
            if (
                user["id"] == user_id
                and user["type"] in ["i", "not_sure"]
                and query.data in ["i", "not_sure"]
            ):
                return

        username = pretty_user_name(query.from_user, context.chat_data.get("custom_names", {}).get(user_id, ""))

        context.chat_data[message_id]["users"].append(
            {
                "id": user_id,
                "username": username,
                "type": query.data,
                "type_text": TYPE_TEXT_ADD.get(query.data, ""),
            }
        )
        if_change = True
    elif query.data == "not_play":
        for user in context.chat_data[message_id]["users"]:
            if user["id"] == user_id and user["type"] in ["i", "not_sure"]:
                context.chat_data[message_id]["users"].remove(user)
                if_change = True
                break
    elif query.data == "i-1":
        for user in context.chat_data[message_id]["users"]:
            if user["id"] == user_id and user["type"] == "i+1":
                context.chat_data[message_id]["users"].remove(user)
                if_change = True
                break

    if if_change:
        await query.edit_message_text(
            text=generate_message(context.chat_data[message_id]),
            reply_markup=REPLY_MARKUP,
            parse_mode=ParseMode.MARKDOWN,
        )


async def delete_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = update.message.reply_to_message.message_id
    if message_id in context.chat_data:
        if update.effective_user.id != context.chat_data[message_id]["author"]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Удалять может только автор!",
            )
            return
        del context.chat_data[message_id]
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=message_id,
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Игра удалена!",
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Игра не найдена!",
        )


async def list_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"List not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return

    if not context.chat_data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Список игр пуст!",
        )
        return

    now_date_without_time = datetime.now(tz=TZ).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    for message_id, game in deepcopy(context.chat_data).items():
        if message_id == "custom_names":
            continue
        if now_date_without_time > game["date"]:
            del context.chat_data[message_id]
            continue
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=message_id,
            text=f"{game['date_text']} {game['user_message']}",
        )


async def mynameis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запомнить имя пользователя которое он введет после команды /mynameis"""
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"List not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return

    if "custom_names" not in context.chat_data:
        context.chat_data["custom_names"] = {}

    if context.args:
        new_name = " ".join(context.args)
        context.chat_data["custom_names"][update.effective_user.id] = new_name
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text=f"Теперь ты - {new_name}",
        )
    elif update.effective_user.id in context.chat_data["custom_names"]:
        del context.chat_data["custom_names"][update.effective_user.id]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text=f"Вернул твое настоящее имя!",
        )


async def set_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить время игры"""
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"List not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Не указано время игры!",
        )
        return

    try:
        hour = int(context.args[0])
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат времени! Введите число.",
        )
        return

    if hour <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат времени! Введите число больше 0.",
        )
        return

    message_id = update.message.reply_to_message.message_id
    if message_id in context.chat_data:
        if update.effective_user.id != context.chat_data[message_id]["author"]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Редактировать может только автор!",
            )
            return
        context.chat_data[message_id]["hour"] = hour
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Время игры обновлено!",
        )

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=generate_message(context.chat_data[message_id]),
            reply_markup=REPLY_MARKUP,
            parse_mode=ParseMode.MARKDOWN,
        )

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить цену игры"""
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"List not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Не указана цена игры!",
        )
        return

    try:
        price = int(context.args[0])
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат цены! Введите число.",
        )
        return

    if price <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат цены! Введите число больше 0.",
        )
        return

    message_id = update.message.reply_to_message.message_id
    if message_id in context.chat_data:
        if update.effective_user.id != context.chat_data[message_id]["author"]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Редактировать может только автор!",
            )
            return
        context.chat_data[message_id]["price"] = price
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Цена игры обновлена!",
        )

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=generate_message(context.chat_data[message_id]),
            reply_markup=REPLY_MARKUP,
            parse_mode=ParseMode.MARKDOWN,
        )


if __name__ == "__main__":
    logging.info(f"Allowed chats: {ALLOWED_CHAT_IDS}")

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .persistence(persistence=PERSISTENCE)
        .build()
    )

    application.add_handler(CallbackQueryHandler(buttons))
    application.add_handler(CommandHandler("new", new_schedule))
    application.add_handler(CommandHandler("delete", delete_schedule))
    application.add_handler(CommandHandler("list", list_schedule))
    application.add_handler(CommandHandler("mynameis", mynameis))
    application.add_handler(CommandHandler("price", set_price))
    application.add_handler(CommandHandler("hour", set_hour))

    application.run_polling()
