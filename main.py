import logging
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

token = "5376242962:AAGxLOy-Yd8MMYvoxBft_7wULmL-GB2eFcM"

def echo(update: Update, _: CallbackContext) -> None:
    """Echo the user message."""
    update.message.reply_text(f"you said {update.message.text}")


def start(update: Update, _: CallbackContext):
    update.message.reply_text(f"Thank you for using PayLiaoBot!\nCreate a new order with /ordernow, or view all commands with /help!")

def help(update: Update, _: CallbackContext):
    update.message.reply_text(f"/ordernow: start a new order")

def order_now(update: Update, _: CallbackContext):
    update.message.poll("Who order what?")

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("ordernow", order_now))
    
    # on non command i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()