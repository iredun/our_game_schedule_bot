import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from commands.common import generate_message, check_access
from commands.consts import REPLY_MARKUP


async def set_max_players_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить максимальное количество игроков"""

    access = await check_access(update, context)
    if not access:
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Не указана цена игры!",
        )
        return

    try:
        count = int(context.args[0])
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат кол-ва! Введите число.",
        )
        return

    if count <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Неверный формат кол-ва! Введите число больше 0.",
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
        context.chat_data[message_id]["max_players_count"] = count
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Кол-во игроков обновлено!",
        )

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=generate_message(context.chat_data[message_id]),
            reply_markup=REPLY_MARKUP,
            parse_mode=ParseMode.MARKDOWN,
        )

