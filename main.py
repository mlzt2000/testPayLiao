import logging 
from telegram import Update
from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters


all_cmds: str = [
    "/createorder --> Clears current order and starts allowing options to be added",
    "/add Name Purchase Cost --> Adds a purchase where Name buys Purchase for Cost dollars",
    "/vieworder --> Views all options in the current order",
    "/completeorder --> Sends the current order as a poll into the chat and resets the order"    
]
orders: str = []

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"Thank you for using PayLiaoBot!\nCreate a new order with /createorder, or view all commands with /help!")

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(str.join(all_cmds, "\n"))

def create_order(update: Update, context: CallbackContext) -> None:
    ## give a warning here about clearing order? potentially need to provide the means of creating multiple orders
    orders.clear()
    update.message.reply_text(f"/add Name Purchase Cost: Adds an option where Name buys Purchase for Cost dollars")

def add_option(update: Update, context: CallbackContext) -> None:
    text = update.message.text.split(" ")[1:]
    name, purchase, cost = text[0], text[1], text[2]
    msg = f"Order added! {name} buys {purchase} for ${cost}"
    update.message.reply_text(f"{msg}\n\n/vieworder --> Views all options in the current order\n\n/completeorder --> Sends the current order as a poll into the chat and resets the order")

def view_order(update: Update, context: CallbackContext) -> None:
    msg = str.join(orders, "\n")
    update.message.reply_text(f"{msg}")

def complete_order(update: Update, context: CallbackContext) -> None:
    update_chat_id = update.message.chat.id
    context.bot.send_poll(
        chat_id = update_chat_id,
        question = f"Who order what",
        options = orders,
        is_anonymous = False,
        allows_multiple_answers = True
    )
    
def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA")
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("createorder", create_order))
    dispatcher.add_handler(CommandHandler("add", add_option))
    dispatcher.add_handler(CommandHandler("vieworder", view_order))
    dispatcher.add_handler(CommandHandler("completeorder", complete_order))

    dispatcher.add_handler(MessageHandler(Filters.text, unknown_cmd))

    updater.start_polling()

    updater.idle()

if __name__ == "main":
    main()