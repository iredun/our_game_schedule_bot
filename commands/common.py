import logging
import math

from telegram import User, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from commands.consts import GAME_PRICE, GAME_HOUR, MAX_PLAYERS_COUNT, REPLY_MARKUP, TYPE_TEXT_ADD, ALLOWED_CHAT_IDS


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
    max_players = game.get("max_players_count", MAX_PLAYERS_COUNT)
    total_price = price * hour
    total_users = len(game["users"])
    try:
        if total_users > max_players:
            users_count = max_players
        else:
            users_count = total_users
        price_per_user = math.ceil(total_price / users_count)
    except Exception:
        price_per_user = 0
    users_numeric_list = []
    for i, user in enumerate(game["users"], 1):
        users_numeric_list.append(f"{i}. {user['username']}{user['type_text']}")
        if i == max_players and total_users > max_players:
            users_numeric_list.append("--- Запасной список ---")

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


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    message_id = query.message.message_id
    user_id = query.from_user.id

    if_change = False

    if query.data in TYPE_TEXT_ADD:
        username = pretty_user_name(
            query.from_user, context.chat_data.get("custom_names", {}).get(user_id, "")
        )

        for user in context.chat_data[message_id]["users"]:
            if (
                user["id"] == user_id
                and user["type"] in ["i", "not_sure"]
                and query.data in ["i", "not_sure"]
                and user["type"] != query.data
            ):
                user["type"] = query.data
                user["type_text"] = TYPE_TEXT_ADD.get(query.data, "")
                if_change = True
                break
            elif user["id"] == user_id and user["type"] == query.data and user["type"] == "i":
                await query.answer()
                return

        if not if_change:
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
    elif query.data == "check_not_sure":
        if user_id != context.chat_data[message_id]["author"]:
            await query.answer(
                text="Только автор игры может выполнять это действие",
                show_alert=True
            )
            return

        not_sure_users = []
        for user in context.chat_data[message_id]["users"]:
            if user["type"] == "not_sure":
                not_sure_users.append(user["username"])

        not_sure_users = "\n".join(not_sure_users)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=message_id,
            parse_mode=ParseMode.MARKDOWN,
            text=f"Решите свои вопросы!\n{not_sure_users}",
        )

    if if_change:
        await query.edit_message_text(
            text=generate_message(context.chat_data[message_id]),
            reply_markup=REPLY_MARKUP,
            parse_mode=ParseMode.MARKDOWN,
        )

    await query.answer()


async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        logging.warning(f"Command not allowed try from - {update.effective_chat}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text="Доступ запрещен!",
        )
        return False
    return True
