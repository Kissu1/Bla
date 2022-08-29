#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# Built using python-telegram-bot v20.0a2 and its dependencies.
# Special thanks to python-telegram-bot v20.0a2 example scripts.

"""
Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import traceback
import json
import os
from typing import Optional, Tuple
from uuid import uuid4
from html import escape

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        "This bot is only compatible with python-telegram-bot v20.0a2 or higher."
    )


from telegram import (
    Chat,
    ChatMember,
    ChatMemberUpdated,
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    InlineQueryHandler,
    ConversationHandler,
)

from gpa_values import calculate_gpa, get_gpa

# Enable logging
logging.basicConfig(
    # filename="app.log",
    # filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# BOT INFO
BOT_VERSION: str = "0.1.0"
BOT_NAME: str = "TEMP BOT"
BOT_DESCRIPTION: str = """Born on: 2022.08.20 in Sri Lanka.\n
And, Hey, I'm an open-source bot written in Python.
So you can see inside me literally! - How I handle all your requests...\n
Btw If you want, you can copy my source code and make your own bot under MIT license.\n
Also, reporting bugs is always appreciated and pull requests are always welcome! 🤗\n"""


# Choices Data
USER_ID, USER_NIC = range(2)


def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[Tuple[bool, bool]]:
    """
    Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get(
        "is_member", (None, None)
    )

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            logger.info("%s started the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).discard(chat.id)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).discard(chat.id)
    else:
        if not was_member and is_member:
            logger.info("%s added the bot to the channel %s", cause_name, chat.title)
            context.bot_data.setdefault("channel_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info(
                "%s removed the bot from the channel %s", cause_name, chat.title
            )
            context.bot_data.setdefault("channel_ids", set()).discard(chat.id)


async def greet_chat_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Greets new users in chats and announces when someone leaves"""
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result
    cause_name = update.chat_member.from_user.mention_html()
    member_name = update.chat_member.new_chat_member.user.mention_html()

    if not was_member and is_member:
        await update.effective_chat.send_message(
            f"{member_name} was added by {cause_name}.\nWelcome {member_name}! 🤗 🎉\n\n"
            "I'm {BOT_NAME} btw. If you like to know what can I do, just type /help.",
            parse_mode=ParseMode.HTML,
        )
    elif was_member and not is_member:
        await update.effective_chat.send_message(
            f"{member_name} is no longer with us... See you soon {member_name}! 🙌",
            parse_mode=ParseMode.HTML,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show 'About' section for the bot when the command /help is issued."""
    await update.message.reply_text(
        "<b>Hello there! 👋 I'm TEMP BOT and I'm here for you <i>24x7</i> no matter what 😊</b>"
        "\n\n"
        "<b><u>Basic Commands</u></b>"
        "\n\n"
        "/whois - 😎 Get to know about someone"
        "\n"
        "/help - 👀 Show this message"
        "\n"
        "/about - ⭐ Read about me"
        "\n"
        "/version - 📝 Show the version of the bot"
        "\n\n"
        "<b><u>Academic Related</u></b>"
        "\n\n"
        "/gpa - 📊 Show your GPA data"
        "\n"
        "/uom - 🎓 About UoM"
        "\n"
        "/staff - 👥 Get Staff Info",
        parse_mode=ParseMode.HTML,
    )


async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show BOT_VERSION & info when the command /about is issued."""
    logger.info("BOT info requested")
    await update.message.reply_text(
        f"I'm {BOT_NAME} - Version {BOT_VERSION} 🤩"
        "\n"
        f"{BOT_DESCRIPTION}"
        "\n\n"
        "Made with ❤️ by <a href='https://github.com/dilshan-h'>@Dilshan-h</a>",
        parse_mode=ParseMode.HTML,
    )


async def about_uom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show BOT_VERSION & info when the command /about is issued."""
    logger.info("About UoM requested")
    await update.message.reply_text(
        "University of Moratuwa, a leading technological university in the region "
        "welcomes you to witness a truly unique experience!\n"
        "Read More <a href='https://uom.lk/about-the-university'>here.</a>\n\n"
        "<b>📞 General Numbers:</b> 0112640051, 0112650301\n\n"
        "<b>📠 General Fax:</b> +94112650622\n\n"
        "<b>📨 Email:</b> info@uom.lk\n\n"
        "<b>🏬 Address:</b> University of Moratuwa, Bandaranayake Mawatha, Moratuwa 10400\n",
        parse_mode=ParseMode.HTML,
    )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline query. This is run when you type: @botusername <query>"""
    query = update.inline_query.query

    if query == "":
        return

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Capitalize Text",
            input_message_content=InputTextMessageContent(query.upper()),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Bold Text",
            input_message_content=InputTextMessageContent(
                f"<b>{escape(query)}</b>", parse_mode=ParseMode.HTML
            ),
        ),
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Italic Text",
            input_message_content=InputTextMessageContent(
                f"<i>{escape(query)}</i>", parse_mode=ParseMode.HTML
            ),
        ),
    ]

    await update.inline_query.answer(results)


async def gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Stores the info about the user and ends the conversation."""
    # user = update.message.from_user
    await update.message.reply_text(
        "Okay... Let's see how much you have scored! 🔥\n"
        "Please enter your UoM admission number:\n\n"
        "If you want to cancel this conversation anytime, just type /cancel."
    )
    logger.info("/gpa - Getting user's ID")
    return USER_ID


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get the user's ID and run validation. Then request NIC info."""
    # user = update.message.from_user
    if get_gpa(update.message.text, 1) != []:
        await update.message.reply_text("Please enter your NIC number")
        logger.info("/gpa - Getting user's NIC")
        return USER_NIC

    await update.message.reply_text(
        "Invalid ID detected! - Terminating process...\n"
        "Check your ID and try again with command /gpa"
    )

    return ConversationHandler.END


async def get_nic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Get the user's NIC and call calculate_gpa function. Then return the GPA info
    and end the conversation.
    """
    user = update.message.from_user
    logger.info("Received NIC from %s: %s", user.first_name, update.message.text)

    await update.message.reply_text(
        calculate_gpa(update.message.text), parse_mode=ParseMode.HTML
    )

    return ConversationHandler.END


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text("✅ OK, Your request has been cancelled")

    return ConversationHandler.END


async def unknown_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to unknown commands."""
    logger.warning("Unknown command received: %s", update.message.text)
    await update.message.reply_text(
        "Sorry, I didn't understand that command 🤖\nTry /help to see what I can do."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update")

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__, 0
    )
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    message = (
        f"🔴 <b><u>{BOT_NAME} - Error Report</u></b>\n\n"
        "An exception was raised while handling an update\n\n"
        f"<pre>update = {escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {escape(str(context.user_data))}</pre>\n\n"
        f"⏩ <pre>{escape(tb_string)}</pre>"
    )

    await update.message.reply_text(
        "Oops! Something's wrong 🤖\n"
        "An error occurred while handling your request.\n"
        "The error has been reported to the developer and will be fixed soon.\n"
    )
    await context.bot.send_message(
        chat_id=os.environ["DEV_CHAT_ID"], text=message, parse_mode=ParseMode.HTML
    )


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    # Use environment variables to avoid hardcoding your bot's token.
    application = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()

    # Handle members joining/leaving chats.
    application.add_handler(
        ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER)
    )
    logger.info("Greeting handler added")

    # Handle '/help' command.
    application.add_handler(CommandHandler("help", help_command))
    logger.info("Help handler added")

    # Handle '/about' command.
    application.add_handler(CommandHandler("about", about_bot))
    logger.info("About handler added")

    # Handle '/uom' command.
    application.add_handler(CommandHandler("uom", about_uom))
    logger.info("About UOM handler added")

    # Handle conversation.
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gpa", gpa)],
        states={
            USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            USER_NIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nic)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(conv_handler)

    # Handle unknown commands.
    application.add_handler(MessageHandler(filters.COMMAND, unknown_commands))
    logger.info("Unknown Command handler added")

    # Handle inline queries.
    application.add_handler(InlineQueryHandler(inline_query))

    # Handle errors.
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    # Pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
