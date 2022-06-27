from ast import Call
from asyncio.log import logger
import logging 
from typing import Dict, List, Tuple, Any
import datetime
import sqlite3
from telegram import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO

)

############
# DATABASE #
############

conn = sqlite3.connect(
    "payliaodb.db", 
    detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread = False
)

curr = conn.cursor()

reset_cmd = """
DROP TABLE IF EXISTS Orders;
"""
curr.execute(reset_cmd)

reset_cmd = """
DROP TABLE IF EXISTS Options
"""
curr.execute(reset_cmd)

create_cmd = """
CREATE TABLE IF NOT EXISTS Orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    datetime_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descr TEXT,
    closed BOOLEAN NOT NULL DEFAULT FALSE
);
"""
curr.execute(create_cmd)

create_cmd = """
CREATE TABLE IF NOT EXISTS Options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    payee_username TEXT NOT NULL,
    descr FLOAT NOT NULL,
    cost TEXT NOT NULL,
    paid BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);
"""
curr.execute(create_cmd)

conn.commit()

#############################
# CONSTANTS AND DEFINITIONS #
#############################

# State definitions for top level
SELECTING_ACTION, NAME_ORDER, SHOW_OPEN_SELF_PAYER, SHOW_OPEN, SHOW_UNPAID_SELF_PAYER, SHOW_UNPAID_SELF_PAYEE, SHOW_ALL = map(str, range(7))

# State definitions for creating new order (NAME_ORDER)
CONFIRM_NAME, ACCEPT_NAME, REJECT_NAME = map(str, range(7, 10))

# State definitions for closing order (SHOW_OPEN_SELF_PAYER)
CONFIRM_CLOSURE, ACCEPT_CLOSURE = map(str, range(10, 12))

# State definitions for adding options (SHOW_OPEN)
SELECT_INFO, ADD_INFO, CURR_INFO, CONFIRM_OPTION, ACCEPT_OPTION, REJECT_OPTION = map(str, range(12, 18))

# State definitions for acknowledging payments (SHOW_UNPAID_SELF_PAYER)
SELECT_PAYMENT, CONFIRM_PAYMENT, ACCEPT_PAYMENT, REJECT_PAYMENT = map(str, range(18,22))

# State definitions for paying (SHOW_UNPAID_SELF_PAYEE)
SELECT_UNPAID_OPTION, PROVIDE_PROOF, CONFIRM_PROOF = map(str, range(22, 25))

# State definitions for showing
SHOW_PAYEE, SHOW_PAYEE_UNPAID, SHOW_ALL_UNPAID, SHOW_PAYER, SHOW_PAYER_UNPAID = map(str, range(25, 30))

# Meta states
STOPPING, TYPING = map(str, range(30, 32))

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,
    CURRENT_LEVEL,
    DESCRIPTION,
    COST,
    OPTION_INFO,
    ORDER,
    OPTION,
) = map(chr, range(32, 39))


#######################
# TOP LEVEL FUNCTIONS #
#######################

def start(update: Update, context: CallbackContext) -> str:
    """Select an action: View existing orders or start new order"""
    text = (
        "You can view existing orders or start a new order. To stop, type /stop"
    )
    
    buttons = [
        [
            InlineKeyboardButton(
                text = 'Create new order',
                callback_data = str(NAME_ORDER)
            ),
            InlineKeyboardButton(
                text = "Close Order",
                callback_data = str(SHOW_OPEN_SELF_PAYER)
            ),
        ],
        [
            InlineKeyboardButton(
                text = "Add to order",
                callback_data = str(SHOW_OPEN)
            ),
            InlineKeyboardButton(
                text = "Provide proof",
                callback_data = str(SHOW_UNPAID_SELF_PAYEE)
            )
        ],
        [
            InlineKeyboardButton(
                text = 'View existing orders',
                callback_data = str(SHOW_ALL)
            ),
            InlineKeyboardButton(
                text = 'Done',
                callback_data = str(END)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if context.user_data.get(START_OVER):
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
    else:
        update.message.reply_text(
            "Thank you for using PayLahBot! I can help you collect orders and payments."
        )
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )
    
    context.user_data[START_OVER] = False
    return SELECTING_ACTION

##########################
# CREATE ORDER FUNCTIONS #
##########################

def ask_for_new_order_name(update: Update, context: CallbackContext) -> str:
    ## Answering the user
    text = "Name this order."
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return NAME_ORDER

def confirm_name(update: Update, context: CallbackContext) -> str:
    msg = update.message.text
    logger.info(msg)
    username = update.message.from_user.username
    user_data = context.user_data
    user_data[ORDER] = (username, msg)
    text = f"@{username}, create order {msg}?"

    buttons = [
        [
            InlineKeyboardButton(
                text = "Yes",
                callback_data = str(ACCEPT_NAME)
            ),
            InlineKeyboardButton(
                text = "Change name",
                callback_data = str(NAME_ORDER)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel, return to start",
                callback_data = str(SELECTING_ACTION)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
        text = text,
        reply_markup = keyboard
    )

    return CONFIRM_NAME

def accept_name(update: Update, context: CallbackContext) -> str:
    # logger.info(update.message.text)
    new_order = context.user_data[ORDER]
    order_name = new_order[1]
    text = f"Order {order_name} created."
    
    ## Create an empty order in the database
    insert_new_order_cmd = f"""
    INSERT INTO Orders(username, descr)
    VALUES ('{new_order[0]}', '{new_order[1]}')
    """
    curr.execute(insert_new_order_cmd)
    conn.commit()

    buttons = [
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = SELECTING_ACTION
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )

    return ACCEPT_NAME

def end_create_order(update: Update, context: CallbackContext) -> str:
    context.user_data[START_OVER] = True
    start(update, context)
    return SELECTING_ACTION


#########################
# CLOSE ORDER FUNCTIONS #
#########################

def select_closable(update: Update, context: CallbackContext) -> str:
    return SHOW_OPEN_SELF_PAYER

def confirm_close(update: Update, context: CallbackContext) -> str:
    return CONFIRM_CLOSURE

def accept_close(update: Update,    context: CallbackContext) -> str:
    return ACCEPT_CLOSURE

##########################
# ADD TO ORDER FUNCTIONS #
##########################

def select_open(update: Update, context: CallbackContext) -> str:
    text = "Which order do you want to add to?\n"

    fetch_open_orders_cmd = """
    SELECT * FROM Orders o
    WHERE o.closed = false
    """
    curr.execute(fetch_open_orders_cmd)
    orders = curr.fetchall()

    for order in orders:
        text += "Order:\n" + str(order) + "\n\n"

    update.callback_query.answer()
    update.callback_query.edit_message_text(text = text)

    return SHOW_OPEN

def ask_for_option(update: Update, context: CallbackContext) -> str:
    ## TODO check for appropriate order!
    order = int(update.message.text)
    print(order)
    context.user_data[ORDER] = order
    buttons = [
        [
            InlineKeyboardButton(
                text = "Description",
                callback_data = str(DESCRIPTION)
            ),
            InlineKeyboardButton(
                text = "Cost",
                callback_data = str(COST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(SHOW_OPEN)
            ),
            InlineKeyboardButton(
                text = "Done",
                callback_data = str(CONFIRM_OPTION)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    text = "Please add info to your new option."
    if not context.user_data.get(START_OVER):
        context.user_data[DESCRIPTION] = "Please update description."
        context.user_data[COST] = "Please update cost."
    descr = context.user_data.get(DESCRIPTION)
    cost = context.user_data.get(COST)
    text = f"{text}\nDescription: {descr}\nCost: {cost}"

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )

    return SELECT_INFO

def ask_for_option_info(update: Update, context: CallbackContext) -> str:
    context.user_data[CURR_INFO] = update.callback_query.data
    text = "Okay, tell me."

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return ADD_INFO

def save_option_info(update: Update, context: CallbackContext) -> str:
    user_data = context.user_data
    user_data[OPTION_INFO][user_data[CURR_INFO]] = update.message.text

    user_data[START_OVER] = True
    return ask_for_option(update, context)

def confirm_option(update:Update, context:CallbackContext) -> str:
    msg = update.message.text
    logger.info(msg)
    username = update.message.from_user.username
    user_data = context.user_data
    user_data[OPTION_INFO] = (user_data[DESCRIPTION], user_data[COST])
    order = user_data[ORDER]
    text = f"@{username}, add option {msg} to order {order}?"

    buttons = [
        [
            InlineKeyboardButton(
                text = "Yes",
                callback_data = str(ACCEPT_OPTION)
            ),
            InlineKeyboardButton(
                text = "Edit option",
                callback_data = str(ADD_INFO)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel, return to start",
                callback_data = str(SELECTING_ACTION)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
        text = text,
        reply_markup = keyboard
    )

    return CONFIRM_OPTION

def accept_option(update: Update, context: CallbackContext) -> str:
    order_id = context.user_data[ORDER]
    opt_desc = context.user_data[DESCRIPTION]
    opt_cost = context.user_data[COST]
    
    ## Create an empty order in the database
    insert_new_option_cmd = f"""
    INSERT INTO Options(order_id, )
    VALUES ('{new_order[0]}', '{new_order[1]}')
    """
    curr.execute(insert_new_order_cmd)
    conn.commit()

    buttons = [
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = SELECTING_ACTION
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )

    return ACCEPT_NAME

###########################
# PROVIDE PROOF FUNCTIONS #
###########################

def select_unpaid(update: Update, context: CallbackContext) -> str:
    return SHOW_UNPAID_SELF_PAYEE

#############################
# SHOW ALL ORDERS FUNCTIONS #
#############################

def show_all_orders(update: Update, context = CallbackContext) -> str:
    text = "All orders:\n"
    
    fetch_orders_cmd = """
    SELECT * FROM Orders
    ORDER BY id
    ;
    """
    curr.execute(fetch_orders_cmd)
    orders = curr.fetchall()

    for order in orders:
        order_id = order[0]
        fetch_options_cmd = f"""
        SELECT * FROM Options opt
        WHERE opt.order_id = {order_id}
        ORDER BY opt.id
        ;
        """
        curr.execute(fetch_options_cmd)
        options = curr.fetchall()
        text += "Order: " + str(order) + "\n"
        for option in options:
            text += str(option) + "\n"
        text += "\n"
    
    buttons = [
        [
            InlineKeyboardButton(
                text = "Show orders you paid",
                callback_data = str(SHOW_PAYER)
            ),
            InlineKeyboardButton(
                text = "Show orders you bought",
                callback_data = str(SHOW_PAYEE)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Show all outstanding payments",
                callback_data = str(SHOW_ALL_UNPAID)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Back",
                callback_data = str(END)
            ),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    context.user_data[START_OVER] = True
    return SHOW_ALL


def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"/start to start the bot")

def stop(update: Update, context: CallbackContext) -> int:
    """End Conversation by command."""
    update.message.reply_text('Okay, bye.')

    return END

def end(update: Update, context: CallbackContext) -> int:
    """End conversation from InlineKeyboardButton."""
    update.callback_query.answer()

    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)

    return END

########################
# ADDITIONAL FUNCTIONS #
########################

def stop_nested(update: Update, context: CallbackContext) -> str:
    update.message.reply_text('Okay, bye.')
    return STOPPING

########
# MAIN #
########

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA") 
    dispatcher = updater.dispatcher

    # Second level ConversationHandler (add option)
    confirm_option_handlers = [
        CallbackQueryHandler(accept_option, pattern = '^' + str(ACCEPT_OPTION) + '$'),
        CallbackQueryHandler(ask_for_option_info, pattern = '^' + str(ADD_INFO))
    ]
    
    add_option_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(select_open, pattern = '^' + str(SHOW_OPEN) + '$')
        ],
        states = {
            SHOW_OPEN: [MessageHandler(Filters.text & ~Filters.command, ask_for_option)],
            CONFIRM_OPTION: confirm_option_handlers
        },
        fallbacks = [
            CallbackQueryHandler(end_create_order, pattern = '^' + str(SELECTING_ACTION) + '$'),
            CommandHandler('stop', stop_nested)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            SELECTING_ACTION: SELECTING_ACTION,
            STOPPING: STOPPING
        }
    )

    # Second level ConversationHandler (creating order)
    confirm_name_handlers = [
        CallbackQueryHandler(accept_name, pattern = '^' + str(ACCEPT_NAME) + '$'),
        CallbackQueryHandler(ask_for_new_order_name, pattern = '^' + str(NAME_ORDER) + '$'),
    ]

    create_order_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(ask_for_new_order_name, pattern = '^' + str(NAME_ORDER) + '$')
        ],
        states = {
            NAME_ORDER: [MessageHandler(Filters.text & ~Filters.command, confirm_name)],
            CONFIRM_NAME: confirm_name_handlers
        },
        fallbacks = [
            CallbackQueryHandler(end_create_order, pattern = '^' + str(SELECTING_ACTION) + '$'),
            CommandHandler('stop', stop)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            SELECTING_ACTION: SELECTING_ACTION,
            STOPPING: END,
        }
    )

    # Top level ConversationHandler (selecting action)

    selection_handlers = [
        create_order_handler,
        CallbackQueryHandler(
            select_closable,
            pattern = "^" + str(SHOW_OPEN_SELF_PAYER)
        ),
        CallbackQueryHandler(
            select_open,
            pattern = "^" + str(SHOW_OPEN)
        ),
        CallbackQueryHandler(
            select_unpaid,
            pattern = "^" + str(SHOW_UNPAID_SELF_PAYEE)
        ),
        CallbackQueryHandler(
            show_all_orders, 
            pattern = "^" + str(SHOW_ALL) + "$"
        ),
        CallbackQueryHandler(
            end,
            pattern = "^" + str(END) + "$"
        )
    ]

    conv_handler = ConversationHandler(
        entry_points = [
            CommandHandler("start", start)
        ],
        states = {
            SHOW_ALL: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: selection_handlers,
            NAME_ORDER: selection_handlers,
            STOPPING: [CommandHandler('start', start)]
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()

if __name__ == "__main__":
    main()