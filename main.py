import telebot
import logging 
from telebot import types

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
bot = telebot.TeleBot("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA", parse_mode = None)

orders = []

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"Thank you for using PayLiaoBot!\nCreate a new order with /createorder, or view all commands with /help!")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, f"/createorder: start a new order")

@bot.message_handler(commands=["createorder"])
def create_order(message):
    bot.reply_to(message, f"/add Followed by your order in this format: OrderName NameOfPerson Cost \n/vieworder When done")

@bot.message_handler(commands=["add"])
def add_option(message):
    msg = message.text[5:].split(" ")
    option = msg[0]
    payee = msg[1]
    cost = msg[2]
    msg = f"{payee} owes {cost} for {option}"
    orders.append(msg)
    bot.reply_to(message, f"Order added!")
    bot.reply_to(message, msg)
    bot.reply_to(message, f"/add Followed by your order in this format: OrderName NameOfPerson Cost \n/vieworder When done")

@bot.message_handler(commands=["vieworder"])
def view_order(message):
    final = ""
    for order in orders:
        final += f"{order}\n"
    bot.reply_to(message, final)
    bot.reply_to(message, f"/completeorder to send the poll!")

@bot.message_handler(commands=["completeorder"])
def complete_order(message):
    bot.send_poll(
        chat_id = message.chat.id,
        question = "Have you paid?",
        options = orders,
        allows_multiple_answers=False,
        is_anonymous=False,
    )
    orders.clear()
    

# @bot.message_handler(func = lambda m: True)
# def echo_all(message):
#     bot.reply_to(message, message.text)

bot.infinity_polling()