from dataclasses import dataclass
import logging 
from typing import Dict, List, Tuple, Any 
import sqlite3
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

############
# DATABASE #
############

conn = sqlite3.connect(
    "payliaodb.db", 
    detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    check_same_thread = False
)

curr = conn.cursor()

# reset_cmd = """
# DROP TABLE IF EXISTS Orders;
# """
# curr.execute(reset_cmd)

# reset_cmd = """
# DROP TABLE IF EXISTS Options
# """
# curr.execute(reset_cmd)

create_checklists_cmd = """
CREATE TABLE IF NOT EXISTS Checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payer_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
    datetime_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    descr TEXT,
    closed BOOLEAN NOT NULL DEFAULT FALSE
);
"""
curr.execute(create_checklists_cmd)

create_requests_cmd = """
CREATE TABLE IF NOT EXISTS Requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    debtor_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
    descr FLOAT NOT NULL,
    cost TEXT NOT NULL,
    paid BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE
);
"""
curr.execute(create_requests_cmd)

create_users_cmd = """
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE
);
"""

conn.commit()

#############################
# CONSTANTS AND DEFINITIONS #
#############################

# TOP LEVEL CONSTANTS
SELECTING_ACTION, NAME_CHECKLIST, SELECT_CHECKLIST = map(str, range(3))

# CREATE CHECKLIST CONSTANTS
CONFIRM_NAME, ACCEPT_NAME = map(str, range(3, 5)) 

# MANAGE CHECKLIST CONSTANTS
ADD_REQUEST = map(str, range(5, 6))

# META STATES
STOPPING = map(str, range(6, 7))

# ConversationHandler.END
END = ConversationHandler.END

# CONSTANTS
(
    IS_NEW_USE,
    TEMP_STORE,
    CHECKLIST,
    NAME,
    USERNAME,
) = map(str, range(7, 12))

#########################
# GENERAL USE FUNCTIONS #
#########################

def get_username(update: Update) -> str:
    message = update.message
    if message == None:
        callback_query = update.callback_query
        if callback_query == None:
            return None
        return callback_query.from_user.username
    return message.from_user.username

def get_text(update: Update) -> str:
    message = update.message
    if message == None:
        return None
    if message[0] == "@":
        message = message[1:]
    return message.text

class Store:
    """this is a glorified tree with a dictionary instead of a list of children"""
    def __init__(self):
        self.data = None
        self.children = {}
    
    def set_data(self, data):
        self.data = data
        return 1
    
    def store_data(self, data, labels):
        if not labels:
            return self.set_data(data)
        label = labels.pop(0)
        if label not in self.children.keys():
            self.children[label] = Store()
        return self.children[label].store_data(data, labels)
    
    def retrieve_data(self, labels):
        if not labels:
            return self.data
        label = labels.pop(0)
        if label not in self.children.keys():
            return -1
        return self.children[label].retrieve_data(labels)
    
    def clear_data(self, labels):
        if not labels:
            return self.clear_all_data()
        label = labels.pop(0)
        if label not in self.children.keys():
            return -1
        return self.children[label].clear_data(labels)
    
    def clear_all_data(self):
        self.data = None
        for child in self.children.values():
            child.clear_all_data()
        self.children.clear()
        return 1

def store_temp_data(context: CallbackContext, data: Any, labels: Tuple[str, ...]) -> int:
    try:
        if TEMP_STORE not in context.user_data.keys():
            context.user_data[TEMP_STORE] = Store()
        temp_store = context.user_data[TEMP_STORE]
        return temp_store.store_data(data, labels)
    except Exception as e:
        print(f"store_temp_data()\n{e}")
        return -1

def get_temp_data(context: CallbackContext, labels: Tuple[str, ...]) -> Any:
    temp_store = context.user_data[TEMP_STORE]
    return temp_store.retrieve_data(labels)

def clear_temp_data(context: CallbackContext, labels: Tuple[str, ...] = ()) -> int:
    try:
        temp_store = context.user_data[TEMP_STORE]
        temp_store.clear_data(labels)
    except Exception as e:
        print(f"clear_temp_data()\n{e}")
        return -1

#######################
# TOP LEVEL FUNCTIONS #
#######################

def start(update: Update, context: CallbackContext) -> str:
    """Main Menu for the bot, gives access to all other functions"""
    welcome_text = "Hello, and thank you for using PayLiaoBot!" # TODO: ADD PRIVACY DECLARATIONS
    text = "Create a checklist by clicking the 'Create Checklist' below."
    buttons = [
        [
            InlineKeyboardButton(
                text = 'Create Checklist',
                callback_data = str(NAME_CHECKLIST)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    
    """Only print welcome_text if it is the first time in the main menu after starting the bot."""
    if not context.user_data.get(IS_NEW_USE):
        update.message.reply_text(welcome_text)
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )
    else:
        """using callback_query.answer() means that coming back to start menu must be from InlineKeyboardButton"""
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
    
    """START_OVER is shared """
    context.user_data[IS_NEW_USE] = False
    return SELECTING_ACTION

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f"/stop to end the bot, followed by /start to restart it!")

def stop(update: Update, context: CallbackContext) -> int:
    """End Conversation by command. Clears all user_data for a hard reset"""
    update.message.reply_text('Okay, bye.')
    clear_temp_data(context)

    return END

def end(update: Update, context: CallbackContext) -> int:
    """End conversation from InlineKeyboardButton. Clears all user_data for a hard reset"""
    update.callback_query.answer()
    clear_temp_data(context)

    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)

    return END

##############################
# CREATE CHECKLIST FUNCTIONS #
##############################

def name_checklist(update: Update, context: CallbackContext) -> str:
    """starts the process of creating a Checklist by asking user for a name for the Checklist"""

    buttons = [
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(SELECTING_ACTION)
            ),
            InlineKeyboardButton(
                text = "No name",
                callback_data = str(CONFIRM_NAME)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    """asks for a name from Payer"""
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = "Type and send the name of this checklist.\n\nButton Guide\nCancel: Return to start menu.\nNo name: Provide no name for the checklist.",
        reply_markup = keyboard
    )

    return NAME_CHECKLIST

def confirm_name_checklist(update: Update, context: CallbackContext) -> str:
    """asks for confirmation about Checklist name"""
    """get Checklist name and payer username"""
    checklist_name = get_text(update)
    payer_username = get_username(update)
    """store name in context.user_data"""
    store_temp_data(context, checklist_name, [CHECKLIST, NAME])
    store_temp_data(context, payer_username, [CHECKLIST, USERNAME])
    
    buttons = [
        [
            InlineKeyboardButton(
                text = "Yes",
                callback_data = str(ACCEPT_NAME)
            ),
            InlineKeyboardButton(
                text = 'No',
                callback_data = str(NAME_CHECKLIST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(SELECTING_ACTION)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if checklist_name == None:
        printable_name = ""
    else:
        printable_name = " " + checklist_name
    text = f"@{payer_username}, create Checklist{printable_name}?\n\nButton Guide\nYes: Create the Checklist.\nNo: Rename the Checklist.\nCancel: Return to start menu."
    
    if checklist_name == None:
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
    else:
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )

    return CONFIRM_NAME

def accept_name_checklist(update: Update, context: CallbackContext) -> str:
    """if name is accepted, store Checklist in database"""
    checklist_name = get_temp_data(context, [CHECKLIST, NAME])
    checklist_username = get_temp_data(context, [CHECKLIST, USERNAME])

    """Insert into database"""
    checklist_id = db_insert_checklist(checklist_username, checklist_name)
    store_temp_data(context, checklist_id, [CHECKLIST, ID])

    """Set up temp_storage for adding descr"""
    store_temp_data(context, DESCRIPTION, [REQUEST, INFOTYPE])

    buttons = [
        [
            InlineKeyboardButton(
                text = "Add Requests",
                callback_data = str(ADD_INFO_REQUEST)
            ),
            InlineKeyboardButton(
                text = 'Back to start',
                callback_data = str(SELECTING_ACTION)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    if checklist_name == None:
        printable_name = ""
    else:
        printable_name = " " + checklist_name
    text = f"Checklist{printable_name} created.\n\nButton Guide\nAdd Requests: Add payments owed to you to this checklist.\nBack to start: Return to start menu."
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    
    return ACCEPT_NAME

def db_insert_checklist(payer_username: str, descr: str) -> int:
    """Inserting checklist data into Checklists table in Database, returns the id of the checklist"""
    curr.execute(f"""
    INSERT INTO Checklists(payer_username, descr)
    VALUES ('{payer_username}', '{descr}');
    """)
    conn.commit()

##############################
# MANAGE CHECKLIST FUNCTIONS #
##############################

# TODO: Manage checklist menu
# def view_checklists(update: Update, context: CallbackContext) -> str:
#     """view all checklists created by you"""
#     payer_username = get_username(update)
#     payer_checklists = get_payer_checklists(payer_username)
#     buttons = []
#     pass

# def manage_checklist(update: Update, context: CallbackContext) -> str:
#     """Sub menu to manage checklist"""
#     buttons = [
#         [
#             InlineKeyboardButton(
#                 text = "Add",
#                 callback_data = str(ADD_REQUEST)
#             ),
#             InlineKeyboardButton(
#                 text = "Edit/Del",
#                 callback_data = str(EDIT_DEL_REQUESTS)
#             )
#         ]
#     ]
#     keyboard = InlineKeyboardMarkup(keyboard)
    
#     checklist_name = get_temp_data(context, [CHECKLIST, NAME])
#     text = f""
#     return MANAGE_CHECKLIST

def select_info_request(update: Update, context: CallbackContext) -> str:
    """Add requests to checklist one by one"""
    buttons = [
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = str(CONFIRM_REQUEST) # should also print checklist
            ),
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str()
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    checklist_id = get_temp_data(context, [CHECKLIST, ID])
    payer_username = get_temp_data(context, [CHECKLIST, USERNAME])
    checklist_name = get_temp_data(context, [CHECKLIST, NAME])
    if checklist_name == None:
        printable_name = ""
    else:
        printable_name = " " + checklist_name
    text = f"Adding a new payment request to Checklist{checklist_name}."
    text += request_to_string(context)
    text += "Select one of the following info to add.\n\nButton Guide\nDone: Review Request.\nCancel: Return to start menu"
    return SELECT_INFO_REQUEST

def add_info_request(update: Update, context: CallbackContext) -> str:
    checklist_id = get_temp_data(context, [CHECKLIST, ID])
    infotype = get_temp_data(context, [REQUEST, INFOTYPE])

    buttons = [
        [
            InlineKeyboardButton(
                text = "Back",
                callback_data = str(ADD_REQUEST)
            ),
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(SELECTING_ACTION)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    """Different texts for different infotype"""
    if infotype == str(DESCRIPTION):
        text = "Please type and send a description of what was bought."
    elif infotype == str(COST):
        text = "Please type and send the cost of what was bought."
    elif infotype == str(USERNAME):
        text = "Please type and send the username of the person who bought this."
    text += "\n\nButton Guide\nBack: Change type of info being added\nCancel: Cancel adding this payment, return to start menu." # TODO eventually should be return to manage checklist menu
    
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    
    return ADD_INFO_REQUEST

def save_info_request(update: Update, context: CallbackContext) -> str:
    """Takes user input and temporarily stores it"""
    info = get_text(update)
    infotype = get_temp_data(context, [REQUEST, INFOTYPE])
    store_temp_data(context, info, [REQUEST, infotype])
    
    """reset infotype"""
    clear_temp_data(context, [REQUEST, INFOTYPE])

    return select_info_request(update, context)

def confirm_request(update: Update, context: CallbackContext) -> str:
    """Prints the Request, and asks Payer to confirm or to edit it."""
    buttons = [
        [
            InlineKeyboardButton(
                text = "Edit",
                callback_data = str(SELECT_INFO_REQUEST)
            ),
            InlineKeyboardButton(
                text = "Confirm",
                callback_data = str(ACCEPT_REQUEST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_context = str(SELECTING_ACTION) # TODO: change to manage checklist menu
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    text = "Please review your request for payment.\n"
    text += request_to_string(context) + "\n\n"
    text += "Button Guide\nEdit: Return to selecting info to edit\nConfirm: Adds request to checklist if all details are filled up.\nCancel: Return to start menu"
    return CONFIRM_REQUEST

def accept_request(update: Update, context: CallbackContext) -> str:
    checklist_id = get_temp_data(context, [CHECKLIST, ID])
    debtor_username = get_temp_data(context, [REQUEST, USERNAME])
    descr = get_temp_data(context, [REQUEST, DESCRIPTION])
    cost = get_temp_data(context, [REQUEST, COST])

    if None in (debtor_username, descr, cost):
        update.message.reply(text = "You have not filled in all details!")
        return select_info_request
    return ACCEPT_REQUEST

def db_insert_request(checklist_id: int, debtor_username: str, descr: str, cost: float) -> int:
    """Store request into database"""
    curr.execute(f"""
    INSERT INTO Requests(order_id, debtro_username, descr, cost)
    VALUES('{checklist_id}', '{debtor_username}', '{descr}', '{cost}');
    """)

    return conn.commit()

def request_to_string(context: CallbackContext, *id: Tuple[int]) -> str:
    if id:
        id = id[0]
        request_tpl = db_get_request(id)
        debtor_username, descr, cost = request_tpl[2:5]
    else:
        debtor_username = get_temp_data(context, [REQUEST, USERNAME])
        descr = get_temp_data(context, [REQUEST, DESCRIPTION])
        cost = get_temp_data(context, [REQUEST, COST])
    return f"@{debtor_username} bought {descr} for ${cost}."

def db_get_request(id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE id = {id}
    """)
    return curr.fetchall()

def print_checklist(update: Update, context: CallbackContext) -> str:
    return PRINT_CHECKLIST

def checklist_to_string() -> str:
    return ""

###########################
# PROVIDE PROOF FUNCTIONS #
###########################

def select_unpaid(update: Update, context: CallbackContext) -> str:
    pass

#############################
# SHOW ALL ORDERS FUNCTIONS #
#############################



########################
# ADDITIONAL FUNCTIONS #
########################

def stop_nested(update: Update, context: CallbackContext) -> str:
    update.message.reply_text('Okay, bye.')
    return STOPPING

########
# MAIN #
########

def main():
    updater = Updater("5457184587:AAE5SOisTmph4cvKrYPw1k33Rpx-NwW6BLA") 
    dispatcher = updater.dispatcher

    
    
    # Create checklist handler
    # Supports input and buttons for naming checklist
    naming_checklist_handlers = [
        MessageHandler(Filters.text & ~Filters.command, confirm_name_checklist),
        CallbackQueryHandler(
            confirm_name_checklist,
            pattern = "^" + str(CONFIRM_NAME) + "$"
        )
    ]
    # Supports buttons for confirming checklist
    confirm_name_handlers = [
        CallbackQueryHandler(
            accept_name_checklist, 
            pattern = "^" + str(ACCEPT_NAME) + "$"
        ),
        CallbackQueryHandler(
            name_checklist,
            pattern = "^" + str(NAME_CHECKLIST) + "$"
        )
    ]
    # Supports buttons for accepting checklist
    accept_name_handlers = [
        CallbackQueryHandler(
            add_info_request,
            pattern = "^" + str(ADD_INFO_REQUEST) + "$"
        ),
        CallbackQueryHandler(
            start,
            pattern = "^" + str(SELECTING_ACTION) + "$"    
        )
    ]   
    create_checklist_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(
                name_checklist,
                pattern = "^" + str(NAME_CHECKLIST) + "$"
            )
        ],
        states = {
            NAME_CHECKLIST: naming_checklist_handlers,
            CONFIRM_NAME: confirm_name_handlers,
            ACCEPT_NAME: accept_name_handlers
        },
        fallbacks = [
            CommandHandler('stop', stop)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            SELECTING_ACTION: SELECTING_ACTION,
            STOPPING: END
        }
    )

    # Top level ConversationHandler (selecting action)
    # supports the buttons for start menu
    selection_handlers = [
        create_checklist_handler,
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
            SELECTING_ACTION: selection_handlers,
            NAME_CHECKLIST: selection_handlers,

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