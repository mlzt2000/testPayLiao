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
        2: (2, "eg_chat_id_2", )
    },
    "Items": {
        1: (1, 2, 5.00, "eg_item_1"),
        2: (1, 3, 10.00, "eg_item_2")
    }
}

# State definitions 
SELECTING_ACTION, CREATE_ORDER, SHOW_ALL_ORDERS = map(str, range(3))

# Meta states
STOPPING, SHOWING = map(str, range(3, 5))

#Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,

) = map(chr, range(5, 6))



def start(update: Update, context: CallbackContext) -> str:
    """Select an action: View existing orders or start new order"""
    desc = (
        "You can view existing orders or start a new order. To stop, type /stop"
    )
    
    buttons = [
        [
            InlineKeyboardButton(
                text = 'View existing orders',
                callback_data = str(SHOW_ALL_ORDERS)
            ),
            InlineKeyboardButton(
                text = 'Create new order',
                callback_data = str(CREATE_ORDER)
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
    chat_id = update.message.chat.id
    all_orders: Dict[int, Tuple[Any]] = database['Orders']
    out = [to_string(order_id, order) for order_id, order in all_orders.values() if order['chat_id'] == chat_id]
    
    buttons = [
        [InlineKeyboardButton(
            text = "Back",
            callbakc_data = str(END)
        )]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = out,
        reply_markup = keyboard
    )
    context.user_data[START_OVER] = True
    return SHOWING

def to_string(order_id: int, order: Tuple[Any]) -> str:
    all_items = database["Items"]
    items_in_order = list(filter(lambda x: x[0] == order_id, all_items.values()))
    out = [str(item) for item in items_in_order]
    return out

        

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"/start to start the bot")

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA")
    dispatcher = updater.dispatcher

    # _handler = ConversationHandler(
    #     entry_points = [
    #         CallbackQueryHandler(lvl_two, pattern = '^' + str(LVLTWO) + '$')
    #     ],
    #     states = {
            
    #     },
    #     fallbacks = [

    #     ],
    #     map_to_parent = {
    #         SHOWING: SHOWING,
    #         STOPPING: END,
    #     }
    # )

    # Top level ConversationHandler (selecting action)
    selection_handlers = [
        # _handler,
        CallbackQueryHandler(
            show_all_orders, 
            pattern = '^' + str(SHOW_ALL_ORDERS)
        ),
        CallbackQueryHandler(

        )
    ]

    conv_handler = ConversationHandler(
        entry_points = [
            CommandHandler("start", start)
        ],
        states = {
            SHOWING: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: selection_handlers,
            STOPPING: [CommandHandler('start', start)]
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()

if __name__ == "main":
    main()