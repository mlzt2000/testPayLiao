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

"""
- Start menu for the bot, buttons lead to various sub-menus and other functions.
- Entering this menu updates the user's username in the Users table in the database
- Returns SELECTING_ACTION state
"""
def selecting_action(update: Update, context: CallbackContext) -> str:
    # Updating username in database
    username = get_username(update)
    user_id = get_user_id(update)
    db.insert_user(user_id, username)

    # Text
    welcome_text = "Hello, and thank you for using PayLiaoBot!\n"
    welcome_text += "For this bot to work, please make sure that your friends are have started the bot, and take note that this bot will collect your username."
    welcome_text += "\n\nThis bot allows users to request payments from other users."
    welcome_text += "\nAfter payement has been made, requests can be marked as paid, which will appear for the sender to check."
    welcome_text += "\nThe sender can then acknowledge the payment to mark the transaction as complete."
    text = "Button Guide:"
    text += "\nCreate request: Ask another user to make a payment to you."
    text += "\nView all requests: See all completed and pending transactions involving you in chronological order."
    text += "\nPay: See all outstanding payments that you owe others, and mark them as paid."
    text += "\nAcknowledge: See all payments that have been made to you, and mark them as complete."
    text += "\nDone: Stops the bot."
    
    # Buttons and relevant data
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
            InlineKeyboardButton(text = "Done", callback_data = str(END))
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    
    # Only print welcome_text if it is the first time in the main menu after starting the bot.
    if not temp.get_temp_data(context, [SELECTING_ACTION, START_OVER]):
        update.message.reply_text(welcome_text)
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )
        # Stores a label to indicate that the next visit to the start menu will not be the first one.
        temp.store_temp_data(context, True, [SELECTING_ACTION, START_OVER])
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
    return SELECTING_ACTION

"""
- Displays a simple message with the two main commands that users can use to restart the bot if they are stuck. 
"""
def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"/stop to end the bot, followed by /start to restart it!")

"""
- Function to stop the bot when in the start menu
- Clears all temporary data (stored in context.user_data)
- Returns END state
"""
def stop(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Okay, bye.')
    temp.clear_temp_data(context)
    return END

"""
- Function to stop the bot from an InlineKeyboardButton.
- Clears all temporary data (stores in context.user_data)
- Returns END state
"""
def end(update: Update, context: CallbackContext) -> int:
    """End conversation from InlineKeyboardButton. Clears all user_data for a hard reset"""
    update.callback_query.answer()
    temp.clear_temp_data(context)
    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)
    return END

########
# MAIN #
########

"""
The main function that runs the bot. Creates the top level ConversationHandler
"""
def main():
    updater = Updater("5376242962:AAGxLOy-Yd8MMYvoxBft_7wULmL-GB2eFcM") 
    dispatcher = updater.dispatcher
    
    db.create_all_tables()

    # Supports the buttons for the start menu
    selection_handlers = [
        create_request.create_request_handler,
        view_requests.view_requests_handler,
        pay.pay_handler,
        acknowledge.acknowledge_handler,
        CallbackQueryHandler(end, pattern = f"^{END}$"),
    ]

    start_handler = ConversationHandler(
        # start menu is only accessed when /start is sent by user
        entry_points = [
            CommandHandler("start", selecting_action)
        ],
        states = {
            SELECTING_ACTION: selection_handlers,
            STOPPING: [CommandHandler("start", selecting_action)]
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ]
    )

    dispatcher.add_handler(start_handler)
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()