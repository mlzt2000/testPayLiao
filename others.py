from typing import Tuple, Any
from telegram import Update

def get_username(update: Update) -> str:
    message = update.message
    if message == None:
        callback_query = update.callback_query
        if callback_query == None:
            return None
        return "@" + callback_query.from_user.username
    return "@" + message.from_user.username

def get_text(update: Update) -> str:
    message = update.message
    if message == None:
        return None
    text = message.text
    if text[0] == "@":
        text = text[1:]
    return text

def get_user_id(update: Update) -> str:
    message = update.message
    if message == None:
        callback_query = update.callback_query
        if callback_query == None:
            return None
        return callback_query.from_user.id
    return message.from_user.id