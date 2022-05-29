import telebot
import logging 
from telebot import types

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
bot = telebot.TeleBot("5376242962:AAGxLOy-Yd8MMYvoxBft_7wULmL-GB2eFcM", parse_mode = None)

payees = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"Thank you for using PayLiaoBot!\nCreate a new order with /createorder, or view all commands with /help!")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, f"/createorder: start a new order")

@bot.message_handler(commands=["createorder"])
def create_order(message):
    bot.reply_to(message, f"/add Followed by your order \n/completeorder When done")

@bot.message_handler(commands=["add"])
def add_option(message):
    option = message.text[5:]
    markup = types.ForceReply(selective=True)
    bot.send_message(message, "Who made this order?", reply_markup=markup)
    payee = message.text
    if payee in payees:
        payees[payee].append(option)
    else: 
        payees[payee] = [option]
    bot.reply_to(message, f"{option} added!")

@bot.message_handler(commands=["completeorder"])
def complete_order(message):
    pass

@bot.message_handler(func = lambda m: True)
def echo_all(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()