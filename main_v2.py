import telebot
import logging 

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
bot = telebot.TeleBot("5376242962:AAGxLOy-Yd8MMYvoxBft_7wULmL-GB2eFcM", parse_mode = None)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"Thank you for using PayLiaoBot!\nCreate a new order with /createorder, or view all commands with /help!")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, f"/createorder: start a new order")

curr_order_options = []
curr_order = []

@bot.message_handler(commands=["createorder"])
def create_order(message):
    bot.reply_to(message, f"new order! /add order, /completeorder when done")
    global curr_order_options
    curr_order_options = []

@bot.message_handler(commands=["add"])
def add_option(message):
    global curr_order_options
    option = message.text[5:]
    if option in curr_order_options:
        bot.reply_to(message, f"{option} already exists!")
        return
    curr_order_options.append(option)
    bot.reply_to(message, f"{option} added!")

@bot.message_handler(commands=["completeorder"])
def complete_order(message):
    global curr_order, curr_order_options
    if curr_order and not curr_order[0].is_closed:
        bot.reply_to(message, f"one order at a time!")
        return
    options = curr_order_options
    order = bot.send_poll(
        message.chat.id, 
        "Who order What?", 
        options,
        allows_multiple_answers=True
    )
    curr_order = [order]

@bot.message_handler(func = lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()