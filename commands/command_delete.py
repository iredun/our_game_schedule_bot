from telegram import Update
from telegram.ext import ContextTypes

from commands.common import check_access


async def delete_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access = await check_access(update, context)
    if not access:
        return

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
