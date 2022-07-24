from typing import Tuple, Any
import time
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

"""
- Function that displays the list of all Requests that are marked as unpaid by the Debtor.
- If there are such Requests, provide a button for User to continue to acknowledge the Requests.
- Provide a button for User to return to start menu
- Returns VIEW_OWNED state
"""
def view_owed(update: Update, context: CallbackContext) -> str:
    debtor_username = get_username(update)
    text = "View what your friends have requested you to return.\n"
    requests = db.get_unpaid_requests_from_debtor_username(debtor_username)
    buttons=[]
    if not requests:
        text += "\nGood job! You do not owe anyone any money."
        text += "\n\nNavigational Buttons Guide:"
        text += "\nBack: Return to start menu."
        buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    else:
        count = 1
        for request in requests:
            text += f"\n{count}: {request_to_string(request)}"
            count += 1
        text += "\n\nNavigational Buttons Guide:"
        text += "\nPay: Click to select an option from above to mark it as paid."
        text += "\nBack: Return to start menu."
        buttons = [
            [
                InlineKeyboardButton(text="Pay", callback_data=str(SELECT_REQUEST)),
                InlineKeyboardButton(text="Back", callback_data=str(END))
            ]
        ]
    keyboard = InlineKeyboardMarkup(buttons)
    if not update.callback_query or temp.get_temp_data(context, [PAY, START_OVER]):
        update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        temp.store_temp_data(context, True, [PAY, START_OVER])
    return VIEW_OWED

"""
- Function that displays the same list as view_owed, and provides buttons for the User to mark the requests as complete, or reject it.
- If there are no more requests, provide a button for User to return to start menu.
- Returns SELECT_UPDATE state
"""
def select_request(update: Update, context: CallbackContext) -> str:
    text = "View what your friends have requested you to return.\n"
    debtor_username = get_username(update)
    requests = db.get_unpaid_requests_from_debtor_username(debtor_username)
    buttons = []
    if not requests:
        text = "Good job! You do not owe anyone any money."
        text += "\n\nNavigational Buttons Guide:"
        text += "\nBack: Return to start menu."
        buttons = [[InlineKeyboardButton(text="Back", callback_data=str(END))]]
    else:
        count = 1
        for request in requests:
            text += f"\n{count}: {request_to_string(request)}"
            button_str = get_button_string_from_request(request, count)
            count += 1
            callback_data = get_callback_data_from_request(request)
            buttons.append([InlineKeyboardButton(text=button_str, callback_data=str(callback_data + 999))])
        text += "\n\nButton Guide:"
        text += "\nClick on the button with the matching username and cost after you have paid that person."
        text += "\n\nNavigational Buttons Guide:"
        text += "\nCancel: Return to start menu."
        buttons.append([InlineKeyboardButton(text="Cancel", callback_data=str(END))])
    keyboard = InlineKeyboardMarkup(buttons)
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECT_REQUEST

"""
- Function that marks the request as paid.
- Resets the temporarily stored data.
- Automatically returns to select_request to choose another request.
"""
def mark_as_paid(update: Update, context: CallbackContext) -> str:
    request_id = int(update.callback_query.data) - 999
    db.mark_request_as_paid_from_id(request_id)
    request = db.get_request_from_id(request_id)
    text = request_to_string(request)
    update.callback_query.answer()
    update.callback_query.edit_message_text(text)
    time.sleep(2.5)
    return select_request(update, context)

"""
- Stops the bot from within this sub-menu with the /stop command
- Clears all temporary data to prepare for /start
- Returns STOPPING state
"""
def stop_pay(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context)
    update.message.reply_text("Okay, bye!")
    return STOPPING

"""
- Returns the user to the start menu.
- Clears all temporary data used in this sub-menu
- Returns END state
"""
def end_pay(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context, [PAY])
    main.selecting_action(update, context)
    return END

"""
Sub-menu ConversationHandler
"""
pay_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(view_owed, pattern=f"^{VIEW_OWED}")
    ],
    states={
        VIEW_OWED: [CallbackQueryHandler(select_request, pattern=f"^{SELECT_REQUEST}$")],
        SELECT_REQUEST: [CallbackQueryHandler(mark_as_paid, pattern=f"^[0-9]+$")]
    },
    fallbacks=[
        CallbackQueryHandler(end_pay, pattern=f"^{END}$"),
        CommandHandler('stop', stop_pay)
    ],
    map_to_parent={
        # END state maps to SELECTING_ACTION in start menu
        END: SELECTING_ACTION,
        # STOPPING state maps to END in start menu
        STOPPING: END
    }
)

def request_to_string(request: Tuple[Any, ...]) -> str:
    payer_username, debtor_username, description, cost, datetime_created, paid, acknowledged = request[1:]
    paid_str = "owe"
    datetime_str = f"on {datetime_created}"
    if paid:
        paid_str = "have paid"
        datetime_str = ""
    return f"You {paid_str} {payer_username} {cost} for {description} {datetime_str}."

def get_button_string_from_request(request: Tuple[Any, ...], serial_no: int) -> str:
    payer_username = request[1]
    cost = request[4]
    return f"{serial_no}: Pay {payer_username} ${cost}"

def get_callback_data_from_request(request: Tuple[Any, ...]) -> int:
    id = request[0]
    return int(id)
