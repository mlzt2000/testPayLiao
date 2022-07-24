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

def view_updates(update: Update, context: CallbackContext) -> str:
    payer_username = get_username(update)
    text = "Check if your friends have paid what they owe you.\n"
    requests = db.get_unacknowledged_requests_from_payer_username(payer_username)
    buttons=[]
    if not requests:
        text += "\nYou do not have any payments to acknowledge."
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
                InlineKeyboardButton(text="Acknowledge", callback_data=str(SELECT_UPDATE)),
                InlineKeyboardButton(text="Back", callback_data=str(END))
            ]
        ]
    keyboard = InlineKeyboardMarkup(buttons)
    if not update.callback_query or temp.get_temp_data(context, [ACKNOWLEDGE, START_OVER]):
        update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        temp.store_temp_data(context, True, [ACKNOWLEDGE, START_OVER])
    return VIEW_UPDATES

def select_update(update: Update, context: CallbackContext) -> str:
    text = "Check if your friends have paid what they owe you.\n"
    debtor_username = get_username(update)
    requests = db.get_unacknowledged_requests_from_payer_username(debtor_username)
    buttons = []
    if not requests:
        text = "\nYou do not have any payments to acknowledge."
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
        text += "\nClick on the button with the matching username and cost. You can then confirm that the transaction has occured, or revert it to being unpaid."
        text += "\n\nNavigational Buttons Guide:"
        text += "\nCancel: Return to start menu."
        buttons.append([InlineKeyboardButton(text="Cancel", callback_data=str(END))])
    keyboard = InlineKeyboardMarkup(buttons)
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return SELECT_UPDATE

def acknowledge_or_reject(update: Update, context: CallbackContext) -> str:
    request_id = int(update.callback_query.data) - 999
    temp.store_temp_data(context, request_id, [ACKNOWLEDGE, ID])
    request = db.get_request_from_id(request_id)
    text = "Confirm that the payment has indeed been made."
    text += f"\n\n{request_to_string(request)}"
    text += "\n\nButton Guide:"
    text += "\nAcknowledge: Click to confirm that the payment has been made."
    text += "\nReject: Click if the payment has not been made."
    text += "\n\nNavigational Button Guide:"
    text += "\nBack: Choose a different option."
    text += "\nCancel: Return to the start menu."

    buttons = [
        [
            InlineKeyboardButton(text="Acknowledge", callback_data=str(ACKNOWLEDGE)),
            InlineKeyboardButton(text="Reject", callback_data=str(REJECT))
        ],
        [
            InlineKeyboardButton(text="Back", callback_data=str(SELECT_UPDATE)),
            InlineKeyboardButton(text="Cancel", callback_data=str(END))
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return ACKNOWLEDGE_OR_REJECT

def mark_as_acknowledged(update: Update, context: CallbackContext) -> str:
    request_id = temp.get_temp_data(context, [ACKNOWLEDGE, ID])
    db.mark_request_as_acknowledged_from_id(request_id)
    text = "You have acknowledged the payment."
    update.callback_query.answer()
    update.callback_query.edit_message_text(text)
    temp.clear_temp_data(context, [ACKNOWLEDGE])
    return select_update(update, context)

def mark_as_rejected(update: Update, context: CallbackContext) -> str:
    request_id = temp.get_temp_data(context, [ACKNOWLEDGE, ID])
    db.mark_request_as_unpaid_from_id(request_id)
    text = "You have marked the payment as unpaid."
    update.callback_query.answer()
    update.callback_query.edit_message_text(text)
    temp.clear_temp_data(context, [ACKNOWLEDGE])
    return select_update(update, context)

def stop_acknowledge(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context)
    update.message.reply_text("Okay, bye!")
    return STOPPING

def end_acknowledge(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context, [ACKNOWLEDGE])
    main.selecting_action(update, context)
    return END

acknowledge_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(view_updates, pattern=f"^{VIEW_UPDATES}$")
    ],
    states={
        VIEW_UPDATES: [CallbackQueryHandler(select_update, pattern=f"^{SELECT_UPDATE}")],
        SELECT_UPDATE: [CallbackQueryHandler(acknowledge_or_reject, pattern=f"^[0-9]+$")],
        ACKNOWLEDGE_OR_REJECT: [
            CallbackQueryHandler(mark_as_acknowledged, pattern=f"^{ACKNOWLEDGE}$"),
            CallbackQueryHandler(mark_as_rejected, pattern=f"^{REJECT}$"),
            CallbackQueryHandler(select_update, pattern=f"^{SELECT_UPDATE}$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(end_acknowledge, pattern=f"^{END}$"),
        CommandHandler('stop', stop_acknowledge)
    ],
    map_to_parent={
        END: SELECTING_ACTION,
        STOPPING: END
    }
)

def request_to_string(request: Tuple[Any, ...]) -> str:
    payer_username, debtor_username, description, cost, datetime_created, paid, acknowledged = request[1:]
    return f"{debtor_username} has paid you {cost} for {description}."

def get_button_string_from_request(request: Tuple[Any, ...], serial_no: int) -> str:
    payer_username = request[1]
    cost = request[4]
    return f"{serial_no}: {payer_username} paid you ${cost}"

def get_callback_data_from_request(request: Tuple[Any, ...]) -> int:
    id = request[0]
    return int(id)