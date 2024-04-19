import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from datetime import datetime

from commands.common import check_access
from commands.consts import REPLY_MARKUP, GAME_HOUR, GAME_PRICE, ALLOWED_CHAT_IDS, TZ, MAX_PLAYERS_COUNT


async def new_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access = await check_access(update, context)
    if not access:
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
            except Exception:
                price = GAME_PRICE

            if price < 0:
                price = GAME_PRICE

        if arg.startswith("ч."):
            try:
                hour = int(arg[2:])
            except Exception:
                hour = GAME_HOUR

            if hour < 0:
                hour = GAME_HOUR

    context.args = list(
        filter(
            lambda arg: not arg.startswith("₽") or not arg.startswith("ч."),
            context.args,
        )
    )

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
        "max_players_count": MAX_PLAYERS_COUNT,
    }
