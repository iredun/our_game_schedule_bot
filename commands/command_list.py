import logging
from copy import deepcopy
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from commands.common import check_access
from commands.consts import TZ


async def list_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access = await check_access(update, context)
    if not access:
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
