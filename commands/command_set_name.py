from telegram import Update
from telegram.ext import ContextTypes

from commands.common import check_access


async def mynameis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запомнить имя пользователя которое он введет после команды /mynameis"""
    access = await check_access(update, context)
    if not access:
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
