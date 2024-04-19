import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    PicklePersistence,
    CallbackQueryHandler,
)
from dotenv import load_dotenv

from commands.command_delete import delete_schedule
from commands.command_list import list_schedule
from commands.command_new import new_schedule
from commands.command_set_hour import set_hour
from commands.command_set_max_players_count import set_max_players_count
from commands.command_set_name import mynameis
from commands.command_set_price import set_price
from commands.common import buttons
from commands.consts import ALLOWED_CHAT_IDS, BOT_TOKEN

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

PERSISTENCE = PicklePersistence(filepath="chats_data.dat", update_interval=10)

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
    application.add_handler(CommandHandler("max_players_count", set_max_players_count))

    application.run_polling()
