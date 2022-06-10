from ast import Call
import logging 
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
# --> Table is the form Dict[primary_key: id, data: List[Any]]
database = {
    "Orders": {},
    "Chats": {},
    "Users": {},
}

# State definitions 
SELECTING_ACTION, CREATE_ORDER, SHOW_ALL_ORDERS = map(str, range(3))

#Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,

) = map(chr, range(3, 4))



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