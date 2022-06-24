from ast import Call
import logging 
from typing import Dict, List, Tuple, Any
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

# State definitions for top level
SELECTING_ACTION, CREATING_ORDER, SHOWING_ALL_ORDERS = map(str, range(3))

# State definitions for second level (showing orders)
SHOW_ORDERS_BOUGHT, SHOW_ORDERS_PAID = map(str, range(3, 5))

# Meta states
STOPPING, SHOWING = map(str, range(5, 7))

#Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,
    CURRENT_LEVEL,
) = map(chr, range(7, 9))


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
                text = 'View existing orders',
                callback_data = str(SHOWING_ALL_ORDERS)
            ),
            InlineKeyboardButton(
                text = 'Create new order',
                callback_data = str(CREATING_ORDER)
            )
        ],
        [
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

def show_all_orders(update: Update, context = CallbackContext) -> str:
    # chat_id = update.message.chat.id
    all_orders = list(database['Orders'].items())
    all_orders.sort(key = lambda x: x[0]) # should sort by chronological order, for now is sorted by id
    out = [order_to_string(order_id, order) for order_id, order in all_orders]
    
    buttons = [
        [
            InlineKeyboardButton(
                text = "Show orders you paid",
                callback_data = str(SHOW_ORDERS_PAID)
            ),
            InlineKeyboardButton(
                text = "Show orders you bought",
                callback_data = str(SHOW_ORDERS_BOUGHT)
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
    return SHOWING

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

##########################
# SECOND LEVEL FUNCTIONS #
##########################

def create_new_order(update: Update, context: CallbackContext) -> str:
    ## Answering the user
    text = "Name this order."
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    ## Create an empty order in the database
    new_order_id = database["Orders"].size()
    database["Orders"][new_order_id] = ()

    return TYPING

########
# MAIN #
########

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA")
    dispatcher = updater.dispatcher

    # Second level ConversationHandler (creating order)
    create_order_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(create_new_order, pattern = '^' + str(CREATING_ORDER) + '$')
        ],
        states = {
            TYPING: [MessageHandler(Filters.text & ~Filters.command, save_order)],

        },
        fallbacks = [

        ],
        map_to_parent = {
            SHOWING: SHOWING,
            STOPPING: END,
        }
    )

    # Top level ConversationHandler (selecting action)
    selection_handlers = [
        # _handler,
        CallbackQueryHandler(
            show_all_orders, 
            pattern = "^" + str(SHOWING_ALL_ORDERS) + "$"
        ),
        CallbackQueryHandler(
            create_new_order,
            pattern = "^" + str(CREATING_ORDER) + "$"
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
            SHOWING: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: selection_handlers,
            CREATING_ORDER: selection_handlers,
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