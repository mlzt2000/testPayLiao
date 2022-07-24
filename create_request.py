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
    Filters,
    MessageHandler
)

"""
- Function that creates a menu for Users to choose either Username, Description, or Cost for the request they are creating.
- Provide a button to confirm the request after all details are filled in.
- Also provides button to return to start menu.
- Returns SELECTING_REQUEST_INFO state
"""
def selecting_request_info(update: Update, context: CallbackContext) -> str:
    text = "Create a request by filling up the following information! You can also edit information you have already entered."
    text += f"\n\n{request_to_string(context)}"
    text += "\n\nButton Guide:"
    text += "\nUsername: Click this button to fill up the telegram username of the person who owes you payment."
    text += "\nDescription: Click this button to fill up the description of the item you paid for."
    text += "\nCost: Click this button to fill up the cost of the item you paid for."
    text += "\n\nNavigational Button Guide"
    text += "\nDone: Click to complete the request only after filling in all three sets of information"
    text += "\nCancel: Cancel the creation of the reqeust and return to the start menu."

    buttons = [
        [
            InlineKeyboardButton(text="Username", callback_data=str(USERNAME)),
            InlineKeyboardButton(text="Description", callback_data=str(DESCRIPTION)),
            InlineKeyboardButton(text="Cost", callback_data=str(COST))
        ],
        [
            InlineKeyboardButton(text="Done", callback_data=str(CONFIRM_REQUEST)), 
            InlineKeyboardButton(text="Cancel", callback_data=str(END))
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if not update.callback_query:
        update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    temp.store_temp_data(context, True, [REQUEST, START_OVER])
    return SELECTING_REQUEST_INFO

"""
- Function that asks Users to key in information based on the button they pressed in selecting_request_info
- Returns ASK_FOR_REQUEST_INFO state 
"""
def ask_for_request_info(update: Update, context: CallbackContext) -> str:
    infotype = temp.get_temp_data(context, [REQUEST, INFOTYPE])
    if not infotype:
        infotype = update.callback_query.data
        temp.store_temp_data(context, infotype, [REQUEST, INFOTYPE])

    filler = ""
    guide = ""
    if infotype == str(DESCRIPTION):
        filler = "description"
    elif infotype == str(COST):
        filler = "cost"
        guide = "Cost should be a decimal number with up to 2 decimal places only. Do not include '$'. It should not be less than or equals to 0"
    elif infotype == str(USERNAME):
        filler = "username"
        guide = "Username should have an '@', followed by the username. Please also ensure that this user has started the bot."
    text = f"Type out the {filler}, and send it. {guide}"
    text += "\n\nNavigational Button Guide:"
    text += "\nBack: Choose a different information to fill in."
    text += "\nCancel: Cancel creation of this request and return to the start menu."

    buttons = [
        [
            InlineKeyboardButton(text="Back", callback_data=str(SELECTING_REQUEST_INFO)),
            InlineKeyboardButton(text="Cancel", callback_data=str(END))
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    if not update.callback_query:
        update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    return ASK_FOR_REQUEST_INFO

"""
- Function that checks for validity of data, and if valid, saves it to the temporary storage before allowing user to select other info to fill in.
- If invalid, shows error message and instructs user on appropriate use.
- If invalid, asks user to resend the info.
- Provide buttons for user to choose a different info to fill in, or to cancel the creation of the request.
"""
def save_request_info(update: Update, context: CallbackContext) -> str:
    infotype = temp.get_temp_data(context, [REQUEST, INFOTYPE])
    info = update.message.text
    appropriate = is_appropriate(infotype, info)
    
    if not appropriate:
        error_text = "Inappropriate info! Please try again! "
        if infotype == str(USERNAME):
            error_text += "Username should have an '@', followed by the username. Please also ensure that this user has started the bot."
        elif infotype == str(DESCRIPTION):
            error_text += "Description does not have any particular restrictions."
        elif infotype == str(COST):
            error_text += "Cost should be a decimal number with up to 2 decimal places only. Do not include '$'. It should not be less than or equals to 0"
        error_text += "\n\nNavigational Button Guide:"
        error_text += "\nBack: Choose a different information to fill in."
        error_text += "\nCancel: Cancel creation of this request and return to the start menu."

        buttons = [
            [
                InlineKeyboardButton(text="Back", callback_data=str(SELECTING_REQUEST_INFO)),
                InlineKeyboardButton(text="Cancel", callback_data=str(END))
            ]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        update.message.reply_text(text=error_text, reply_markup=keyboard)
        return ASK_FOR_REQUEST_INFO
    else:
        temp.store_temp_data(context, info, [REQUEST, infotype])
        temp.clear_temp_data(context, [REQUEST, INFOTYPE])
        return selecting_request_info(update, context)   

def is_appropriate(infotype: str, info: str) -> bool:
    info = info.strip()
    if infotype == str(USERNAME):
        return is_appropriate_username(info)
    elif infotype == str(DESCRIPTION):
        return info
    elif infotype == str(COST):
        return is_appropriate_cost(info)
    return False

def is_appropriate_username(username: str) -> bool:
    if not username or username[0] != '@':
        return False
    if not db.get_user_from_username(username):
        return False
    return True

def is_appropriate_cost(cost: str) -> bool:
    try:
        cost = float(cost)
        if cost > 0 and round(cost, 2) == cost:
            return True
        return False
    except ValueError:
        return False

"""
- Function that checks if all info has been filled up, and asks if the User is sure that the info is correct.
- Provides a button for User to go back to edit information.
- If not all the info has been filled up, show an error message.
- Returns CONFIRM_REQUEST state
"""
def confirm_request(update: Update, context: CallbackContext) -> str:
    debtor_username = temp.get_temp_data(context, [REQUEST, USERNAME])
    description = temp.get_temp_data(context, [REQUEST, DESCRIPTION])
    cost = temp.get_temp_data(context, [REQUEST, COST])

    text = ""
    buttons = []
    if not (debtor_username and description and cost):
        text = "You have not filled up all the information!"
        text += f"\n\n{request_to_string(context)}"
        text += "\n\nNavigational Button Guide:"
        text += "\nEdit: Back to previous menu to change details about the request."
        text += "\nCancel: Cancel the creation of the reqeust and return to the start menu."
        buttons = [
            [
                InlineKeyboardButton(text="Edit", callback_data=str(SELECTING_REQUEST_INFO)),
                InlineKeyboardButton(text="Cancel", callback_data=str(END))
            ]
        ]
    else:
        text = "Please check if all the information is correct!"
        text += f"\n\n{request_to_string(context)}"
        text += "\n\nNavigational Button Guide:"
        text += "\nDone: Complete the creation of this request."
        text += "\nEdit: Back to previous menu to change details about the request."
        text += "\nCancel: Cancel the creation of the reqeust and return to the start menu."
        buttons = [
            [InlineKeyboardButton(text="Done", callback_data=str(SAVE_REQUEST))],
            [
                InlineKeyboardButton(text="Edit", callback_data=str(SELECTING_REQUEST_INFO)),
                InlineKeyboardButton(text="Cancel", callback_data=str(END))
            ]
        ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    
    return CONFIRM_REQUEST

"""
- Function that saves the request created into database.
- Provides buttons for user to create a new request, or to return to the start menu
- Clears temp data regarding existing request.
- Returns SAVE_REQUEST state
"""
def save_request(update: Update, context: CallbackContext) -> str:
    debtor_username = temp.get_temp_data(context, [REQUEST, USERNAME])
    description = temp.get_temp_data(context, [REQUEST, DESCRIPTION])
    cost = temp.get_temp_data(context, [REQUEST, COST])
    payer_username = get_username(update)

    db.insert_request(payer_username, debtor_username, description, cost)

    text = "Request added!"
    buttons = [
        [
            InlineKeyboardButton(text="New Request", callback_data=str(SELECTING_REQUEST_INFO)),
            InlineKeyboardButton(text="Done", callback_data=str(END))
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    temp.clear_temp_data(context, [REQUEST])

    return SAVE_REQUEST

"""
- Stops the bot from within this sub-menu with the /stop command
- Clears all temporary data to prepare for /start
- Returns STOPPING state
"""
def stop_create_request(update: Update, context: CallbackContext) -> str:
    update.message.reply_text(text = "Okay, bye!")

    # clear temp data
    temp.clear_temp_data(context)

    return STOPPING

"""
- Returns the user to the start menu.
- Clears all temporary data used in this sub-menu
- Returns END state
"""
def end_create_request(update: Update, context: CallbackContext) -> str:
    temp.clear_temp_data(context, [REQUEST])
    main.selecting_action(update, context)
    return END

"""
Sub-menu ConversationHandler
"""
create_request_handler = ConversationHandler(
        entry_points = [CallbackQueryHandler(selecting_request_info,pattern = f"^{SELECTING_REQUEST_INFO}$")],
        states = {
            SELECTING_REQUEST_INFO: [
                CallbackQueryHandler(ask_for_request_info,pattern=f'^{DESCRIPTION}$|^{USERNAME}$|^{COST}$'),
                CallbackQueryHandler(confirm_request, pattern=f"^{CONFIRM_REQUEST}$")
            ],
            ASK_FOR_REQUEST_INFO: [
                CallbackQueryHandler(selecting_request_info, pattern=f"^{SELECTING_REQUEST_INFO}$"),
                MessageHandler(Filters.text & ~Filters.command, save_request_info)
            ],
            CONFIRM_REQUEST: [
                CallbackQueryHandler(selecting_request_info, pattern=f"^{SELECTING_REQUEST_INFO}$"),
                CallbackQueryHandler(save_request, pattern=f"^{SAVE_REQUEST}$")
            ],
            SAVE_REQUEST: [
                CallbackQueryHandler(selecting_request_info, pattern=f"^{SELECTING_REQUEST_INFO}$"),
            ]
        },
        fallbacks = [
            CallbackQueryHandler(end_create_request, pattern=f"^{END}$"),
            CommandHandler('stop', stop_create_request)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            STOPPING: END
        }
    )

def request_to_string(context: CallbackContext) -> str:
    text = ""
    debtor_username = temp.get_temp_data(context, [REQUEST, USERNAME])
    description = temp.get_temp_data(context, [REQUEST, DESCRIPTION])
    cost = temp.get_temp_data(context, [REQUEST, COST])
    text += f"Username: {debtor_username if debtor_username else 'Yet to fill up'}."
    text += f"\nDescription: {description if description else 'Yet to fill up'}."
    text += f"\nCost: {'$' + cost if cost else 'Yet to fill up'}."
    return text