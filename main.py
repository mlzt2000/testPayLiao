from constants import *
import database as db
import temp_store as temp
import create_request
import view_requests
import pay
import acknowledge
from others import *
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
)

#######################
# TOP LEVEL FUNCTIONS #
#######################

def selecting_action(update: Update, context: CallbackContext) -> str:

    username = get_username(update)
    user_id = get_user_id(update)
    db.insert_user(user_id, username)

    """Main Menu for the bot, gives access to all other functions"""
    welcome_text = "Hello, and thank you for using PayLiaoBot!\n"
    welcome_text += "For this bot to work, please make sure that your friends are have started the bot, and " # TODO: ADD PRIVACY DECLARATIONS
    text = "Button Guide:"
    text += "\nCreate Checklist: Make a list of money that people owe you."
    text += "\nManage Checklists: View all Checklists that you have created, and edit them."
    buttons = [
        [
            InlineKeyboardButton(text = 'Create request', callback_data = str(SELECTING_REQUEST_INFO)),
            InlineKeyboardButton(text = "View all requests", callback_data = str(VIEW_REQUESTS))
        ],
        [
            InlineKeyboardButton(text = "Pay", callback_data = str(VIEW_OWED)),
            InlineKeyboardButton(text = "Acknowledge", callback_data = str(VIEW_UPDATES))
        ],
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = str(END)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    
    """Only print welcome_text if it is the first time in the main menu after starting the bot."""
    if not temp.get_temp_data(context, [SELECTING_ACTION, START_OVER]):
        update.message.reply_text(welcome_text)
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )
        temp.store_temp_data(context, True, [SELECTING_ACTION, START_OVER])
    else:
        """using callback_query.answer() means that coming back to start menu must be from InlineKeyboardButton"""
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
    return SELECTING_ACTION

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"/stop to end the bot, followed by /start to restart it!")

def stop(update: Update, context: CallbackContext) -> int:
    """End Conversation by command. Clears all user_data for a hard reset"""
    update.message.reply_text('Okay, bye.')
    temp.clear_temp_data(context)
    return END

def end(update: Update, context: CallbackContext) -> int:
    """End conversation from InlineKeyboardButton. Clears all user_data for a hard reset"""
    update.callback_query.answer()
    temp.clear_temp_data(context)
    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)
    return END

def stop_nested(update: Update, context: CallbackContext) -> str:
    update.message.reply_text("Okay, bye.")
    temp.clear_temp_data(context)
    return STOPPING

########
# MAIN #
########

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA") 
    dispatcher = updater.dispatcher

    # db.drop_all_tables()
    db.create_all_tables()

    selection_handlers = [
        create_request.create_request_handler,
        view_requests.view_requests_handler,
        pay.pay_handler,
        acknowledge.acknowledge_handler,
        CallbackQueryHandler(end, pattern = f"^{END}$"),
    ]

    start_handler = ConversationHandler(
        entry_points = [
            CommandHandler("start", selecting_action)
        ],
        states = {
            SELECTING_ACTION: selection_handlers,
            STOPPING: [CommandHandler("start", selecting_action)]
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ],
        allow_reentry=True
    )

    dispatcher.add_handler(start_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()