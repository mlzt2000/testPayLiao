import telebot

bot = telebot.TeleBot("5376242962:AAGxLOy-Yd8MMYvoxBft_7wULmL-GB2eFcM", parse_mode = None)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"Thank you for using PayLiaoBot!\nCreate a new order with /createorder, or view all commands with /help!")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, f"/createorder: start a new order")

all_orders = {}

@bot.message_handler(commands=["createorder"])
def create_order(message):
    bot.reply_to(message, f"/add order, /completeorder when done")
    curr_poll_id = len(all_orders) + 1
    message = bot.send_poll(
        message.chat.id, 
        "Who order What?", 
        options,
        allows_multiple_answers=True
    )
    all_orders[len(all_orders) + 1] = message

@bot.message_handler(func = lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()