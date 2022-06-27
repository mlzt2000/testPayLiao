from ast import Call
import logging 
from typing import Dict, List, Tuple, Any
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

# initialise database
conn = sqlite3.connect("payliaodb.db")

curr = conn.cursor()

db_cmds = """ 
CREATE TABLE Orders (
    id INTEGER PRIMARY KEY,
    payer_id INTEGER NOT NULL,
    chat_id INTEGER,
    datetime_created DATETIME NOT NULL,
    descr TEXT,
    closed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE Options (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    payee_id INTEGER NOT NULL,
    cost FLOAT NOT NULL,
    descr TEXT NOT NULL,
    paid BOOLEAN DEFAULT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);
"""

# stand-in for a SQL database in the form of Dict[table_name: str, table: Table]
# see database.sql file for actual sql tables
database = {
    "Orders": {
        1: (1, "eg_chat_id", "eg_datetime", "eg_order"),
        2: (2, "eg_chat_id_2", "eg_datetime_2", "eg_order_2")
    },
    "Items": {
        1: (1, 2, 5.00, "eg_item_1"),
        2: (1, 3, 10.00, "eg_item_2"),
        3: (2, 3, 3.00, "eg_item_3"),
        4: (2, 1, 4.00, "eg_item_4")
    }
}

class Order:

    def __init__(self, name, date, time, payer):
        self.name = name
        self.date = date
        self.time = time
        self.payer = payer
        self.open = True
        self.options = []
    
    def add_options(self, option):
        self.options.append(option)
    
    def remove_option(self, id):
        self.options.remove(id)
    
    def get_title(self):
        return "{} created on {} {} by {}".format(self.name, self.date, self.time, self.payer)

    def printer(self, title, options):
        option_str = "\n".join(options)
        return title + "\n" + option_str

    def print_all(self):
        option_lst = []
        for option in self.options:
            option_lst.append(option.to_string())
        return self.printer(self.get_title(), option_lst)
    
    def print_unpaid(self):
        option_lst = []
        for option in self.options:
            if not option.is_paid():
                option_lst.append(option.to_string())
        title = self.get_title() + " unpaid"
        return self.printer(title, option_lst)

# State definitions for top level
SELECTING_ACTION, NAME_ORDER, SHOW_OPEN_SELF_PAYER, SHOW_OPEN, SHOW_UNPAID_SELF_PAYER, SHOW_UNPAID_SELF_PAYEE, SHOW_ALL = map(str, range(7))

# State definitions for creating new order (NAME_ORDER)
CONFIRM_NAME, ACCEPT_NAME, REJECT_NAME = map(str, range(7, 10))

# State definitions for closing order (SHOW_OPEN_SELF_PAYER)
CONFIRM_CLOSURE, ACCEPT_CLOSURE = map(str, range(10, 12))

# State definitions for adding options (SHOW_OPEN)
ADD_DESC, ADD_COST, CONFIRM_OPTION, ACCEPT_OPTION, REJECT_OPTION = map(str, range(12, 17))

# State definitions for acknowledging payments (SHOW_UNPAID_SELF_PAYER)
SELECT_PAYMENT, CONFIRM_PAYMENT, ACCEPT_PAYMENT, REJECT_PAYMENT = map(str, range(17,21))

# State definitions for paying (SHOW_UNPAID_SELF_PAYEE)
SELECT_UNPAID_OPTION, PROVIDE_PROOF, CONFIRM_PROOF = map(str, range(21, 24))

# State definitions for showing
SHOW_PAYEE, SHOW_PAYEE_UNPAID, SHOW_ALL_UNPAID, SHOW_PAYER, SHOW_PAYER_UNPAID = map(str, range(25, 30))

# Meta states
STOPPING = str(30)

#Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,
    CURRENT_LEVEL,
    DESCRIPTION,
    COST,
) = map(chr, range(31, 33))


#######################
# TOP LEVEL FUNCTIONS #
#######################

def start(update: Update, context: CallbackContext) -> str:
    """Select an action: View existing orders or start new order"""
    desc = (
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
            text = desc,
            reply_markup = keyboard
        )
    else:
        update.message.reply_text(
            "Thank you for using PayLahBot! I can help you collect orders and payments."
        )
        update.message.reply_text(
            text = desc,
            reply_markup = keyboard
        )
    
    context.user_data[START_OVER] = False
    return SELECTING_ACTION

##########################
# CREATE ORDER FUNCTIONS #
##########################

def create_new_order(update: Update, context: CallbackContext) -> str:
    ## Answering the user
    text = "Name this order."
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    ## Create an empty order in the database
    new_order_id = database["Orders"].size()
    database["Orders"][new_order_id] = ()

    return NAME_ORDER

def confirm_name(update: Update, context: CallbackContext) -> str:
    return CONFIRM_NAME

#########################
# CLOSE ORDER FUNCTIONS #
#########################

def select_closable(update: Update, context: CallbackContext) -> str:
    return SHOW_OPEN_SELF_PAYER

def confirm_close(update: Update, context: CallbackContext) -> str:
    return CONFIRM_CLOSURE

def accept_close(update: Update, context: CallbackContext) -> str:
    return ACCEPT_CLOSURE

##########################
# ADD TO ORDER FUNCTIONS #
##########################

def select_open(update: Update, context: CallbackContext) -> str:
    return SHOW_OPEN

###########################
# PROVIDE PROOF FUNCTIONS #
###########################

def select_unpaid(update: Update, context: CallbackContext) -> str:
    return SHOW_UNPAID_SELF_PAYEE

#############################
# SHOW ALL ORDERS FUNCTIONS #
#############################

def show_all_orders(update: Update, context = CallbackContext) -> str:
    all_orders = list(database['Orders'].items())
    all_orders.sort(key = lambda x: x[0]) # should sort by chronological order, for now is sorted by id
    out = [order_to_string(order_id, order) for order_id, order in all_orders]
    
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
        text = "\n\n".join(out),
        reply_markup = keyboard
    )
    context.user_data[START_OVER] = True
    return SHOW_ALL

def order_to_string(order_id: int, order: Tuple[Any]) -> str:
    all_items = database["Items"]
    items_in_order_id = list(filter(lambda x: x[0] == order_id, all_items.values()))
    out = [item_to_string(item) for item in items_in_order_id]
    out.insert(0, f"Order {order_id}, created at {order[2]}, paid by {order[0]}")
    return "\n".join(out)

def item_to_string(item: Tuple[Any]) -> str:
    out = f"{item[1]} bought {item[3]} for ${item[2]:.2f}"
    return out

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


########
# MAIN #
########

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA")
    dispatcher = updater.dispatcher

    # Second level ConversationHandler (creating order)
    create_order_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(create_new_order, pattern = '^' + str(NAME_ORDER) + '$')
        ],
        states = {
            NAME_ORDER: [MessageHandler(Filters.text & ~Filters.command, confirm_name)],
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ],
        map_to_parent = {
            SHOW_ALL: SHOW_ALL,
            STOPPING: STOPPING,
        }
    )

    # Top level ConversationHandler (selecting action)
    selection_handlers = [
        # _handler,
        CallbackQueryHandler(
            create_new_order,
            pattern = "^" + str(NAME_ORDER) + "$"
        ),
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