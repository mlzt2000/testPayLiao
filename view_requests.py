from typing import Tuple, Any
from constants import *
import database as db
import temp_store as temp
from others import *
import main
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    CommandHandler,
)

def view_requests(update: Update, context: CallbackContext) -> str:
    text = "View all requests you have created from oldest at the top to newest at the bottom.\n"
    username = get_username(update)
    all_requests = db.get_all_requests_involving_username(username)
    if not all_requests:
        text = "You have not made any requests, and have not owed anyone either.\n"
        text += "To create a request, return to the start menu and click on the 'Create Request' button."
    else:
        count = 1
        for request in all_requests:
            text += f"\n{count}: {request_to_string(request, username)}"
            count += 1
    text += "\n\nNavigational Buttons Guide:"
    text += "\nBack: Return to start menu."

    buttons = [
        [InlineKeyboardButton(text="Back", callback_data=str(END))]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return VIEW_REQUESTS

def stop_view_requests(update: Update, context: CallbackContext) -> str:
    update.message.reply_text(text = "Okay, bye!")
    temp.clear_temp_data(context)
    return STOPPING

def end_view_requests(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context, [REQUEST])
    main.selecting_action(update, context)
    return END

view_requests_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(view_requests, pattern=f"^{VIEW_REQUESTS}$")
    ],
    states={
        VIEW_REQUESTS: [CallbackQueryHandler(end_view_requests, pattern=f"^{END}$")]
    },
    fallbacks=[
        CallbackQueryHandler(end_view_requests, pattern=f"^{END}$"),
        CommandHandler('stop', stop_view_requests)
    ],
    map_to_parent={
        END: SELECTING_ACTION,
        STOPPING: END
    }
)

def request_to_string(request: Tuple[Any,...], username: str) -> str:
    payer_username, debtor_username, description, cost, datetime_created, paid, acknowledged = request[1:]
    if str(payer_username) == username:
        payer_username = "you"
    if str(debtor_username) == username:
        debtor_username = "You"
    
    paid_str = ""
    if debtor_username == "You":   
        paid_str = "owe"
        if paid:
            paid_str = "have paid"
    else:
        paid_str = "owes"
        if paid:
            paid_str = "has paid"
    out = f"{debtor_username} {paid_str} {payer_username} ${cost} for {description}. "

    if paid:
        ack_str = ""
        if payer_username == "you":
            payer_username = "You"
            ack_str = "have not"
            if acknowledged:
                ack_str = "have"
        else:
            ack_str = "has not"
            if acknowledged:
                ack_str = "has"
        out += f"{payer_username} {ack_str} acknowledged."
    
    return out

