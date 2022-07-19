from dataclasses import dataclass
import logging 
from typing import Dict, List, Tuple, Any
import sqlite3
from telegram import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Update, Bot
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

reset_cmd = """
DROP TABLE IF EXISTS Checklists;
"""
curr.execute(reset_cmd)

reset_cmd = """
DROP TABLE IF EXISTS Requests;
"""
curr.execute(reset_cmd)

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
    checklist_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    debtor_username TEXT NOT NULL REFERENCES Users(username) ON UPDATE CASCADE,
    descr TEXT NOT NULL,
    cost FLOAT NOT NULL,
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
SELECTING_ACTION, NAME_CHECKLIST, VIEW_CHECKLISTS = map(str, range(3))

# CREATE CHECKLIST CONSTANTS
CONFIRM_NAME_CHECKLIST, ACCEPT_NAME_CHECKLIST = map(str, range(3, 5)) 

# MANAGE CHECKLIST CONSTANTS
MANAGE_CHECKLIST, SELECT_INFO_REQUEST, ASK_FOR_INFO_REQUEST, CONFIRM_REQUEST, ACCEPT_REQUEST, EDIT_DEL_REQUESTS = map(str, range(5, 11))

# REMINDER CONSTANTS
SEND_REMINDERS, SEND_REMINDER, PAID = map(str, range(11, 13))

# META STATES
STOPPING = map(str, range(13, 14))

# ConversationHandler.END
END = ConversationHandler.END

# CONSTANTS
(
    START_OVER,
    TEMP_STORE,
    CHECKLIST,
    REQUEST,
    INFOTYPE,
    ID,
    NAME,
    USERNAME,
    DESCRIPTION,
    COST,
) = map(str, range(14, 24))

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
    text = message.text
    if text[0] == "@":
        text = text[1:]
    return text

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
            return None
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
    if TEMP_STORE not in context.user_data.keys():
        context.user_data[TEMP_STORE] = Store()
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

def selecting_action(update: Update, context: CallbackContext) -> str:
    """Main Menu for the bot, gives access to all other functions"""
    welcome_text = "Hello, and thank you for using PayLiaoBot!" # TODO: ADD PRIVACY DECLARATIONS
    text = "Button Guide:\nCreate Checklist: Make a list of money that people owe you.\nManage Checlists: View all Checklists that you have created, and edit them."
    buttons = [
        [
            InlineKeyboardButton(
                text = 'Create Checklist',
                callback_data = str(NAME_CHECKLIST)
            ),
            InlineKeyboardButton(
                text = "Manage Checklists",
                callback_data = str(VIEW_CHECKLISTS)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = str(END)
            )
        ]
    ]

    keyboard = InlineKeyboardMarkup(buttons)
    
    """Only print welcome_text if it is the first time in the main menu after starting the bot."""
    if not get_temp_data(context, [SELECTING_ACTION, START_OVER]):
        update.message.reply_text(welcome_text)
        update.message.reply_text(
            text = text,
            reply_markup = keyboard
        )
        store_temp_data(context, True, [SELECTING_ACTION, START_OVER])
    else:
        """using callback_query.answer() means that coming back to start menu must be from InlineKeyboardButton"""
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text = text,
            reply_markup = keyboard
        )
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

def stop_nested(update: Update, context: CallbackContext) -> str:
    update.message.reply_text("Okay, bye.")
    return STOPPING

##############################
# CREATE CHECKLIST FUNCTIONS #
##############################

def name_checklist(update: Update, context: CallbackContext) -> str:
    """starts the process of creating a Checklist by asking user for a name for the Checklist"""
    buttons = [
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
            ),
            InlineKeyboardButton(
                text = "No name",
                callback_data = str(CONFIRM_NAME_CHECKLIST)
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
                callback_data = str(ACCEPT_NAME_CHECKLIST)
            ),
            InlineKeyboardButton(
                text = 'No',
                callback_data = str(NAME_CHECKLIST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
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

    return CONFIRM_NAME_CHECKLIST

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
                text = "Add requests",
                callback_data = str(ASK_FOR_INFO_REQUEST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Create new",
                callback_data = str(NAME_CHECKLIST)
            ),
            InlineKeyboardButton(
                text = 'Back to start',
                callback_data = str(END)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    if checklist_name == None:
        printable_name = ""
    else:
        printable_name = " " + checklist_name
    text = f"Checklist{printable_name} created."
    text += "\n\nButton Guide"
    text += "\nAdd Requests: Add payments owed to you to this checklist."
    text += "\nCreate new: Make a new checklist."
    text += "\nBack to start: Return to start menu."
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    
    return ACCEPT_NAME_CHECKLIST

def db_insert_checklist(payer_username: str, descr: str) -> int:
    """Inserting checklist data into Checklists table in Database, returns the id of the checklist"""
    curr.execute(f"""
    INSERT INTO Checklists(payer_username, descr)
    VALUES ('{payer_username}', '{descr}');
    """)
    conn.commit()

def end_create_checklist(update: Update, context: CallbackContext) -> str:
    clear_temp_data(context, [CHECKLIST])
    selecting_action(update, context)
    return END

##############################
# MANAGE CHECKLIST FUNCTIONS #
##############################

def view_checklists(update: Update, context: CallbackContext) -> str:
    """view all checklists created by username"""
    payer_username = get_username(update)
    payer_checklists = db_get_open_payer_checklists(payer_username)

    if not payer_checklists:
        buttons = [
            [
                InlineKeyboardButton(
                    text = "Create one",
                    callback_data = str(NAME_CHECKLIST)
                ),
                InlineKeyboardButton(
                    text = "Back",
                    callback_data = str(END)
                )
            ]
        ]
        text = "You have not created any checklists!"
        text += "\n\nButton Guide:"
        text += "\nCreate one: Start creating a checklist."
        text += "\nBack: Return to start menu."
    
    else:
        text = "All the checklists created by you.\n"
        num_to_id_dct = {}
        for i in range(len(payer_checklists)):
            checklist = payer_checklists[i]
            num_to_id_dct[i + 1] = checklist[0]
            checklist_str = checklist_to_string(checklist)
            text += f"Checklist {i + 1}: {checklist_str}\n\n"
        text += "Press the button with the number that corresponds to the Checklist number."
        buttons = []
        for i in range(len(payer_checklists)):
            button_text = str(i + 1)
            checklist_id = num_to_id_dct[i + 1]
            buttons.append([
                InlineKeyboardButton(
                    text = button_text, 
                    callback_data = int(checklist_id)
                )])
        buttons.append([\
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
            )    
        ])
    keyboard = InlineKeyboardMarkup(buttons)
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    return VIEW_CHECKLISTS

def manage_checklist(update: Update, context: CallbackContext) -> str:
    """Sub menu to manage checklist"""
    buttons = [
        [
            InlineKeyboardButton(
                text = "Add",
                callback_data = str(SELECT_INFO_REQUEST)
            ),
            InlineKeyboardButton(
                text = "Edit/Del",
                callback_data = str(EDIT_DEL_REQUESTS)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Remind",
                callback_data = str(SEND_REMINDERS)
            )
        ]
        [
            InlineKeyboardButton(
                text = "Back",
                callback_data = str(VIEW_CHECKLISTS)
            ),
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    
    checklist_id = update.callback_query.data
    store_temp_data(context, checklist_id, [CHECKLIST, ID])
    checklist = db_get_checklist(checklist_id)
    checklist_str = checklist_to_string(checklist)
    text = f"{checklist_str}"

    update.callback_query.answer()
    update.callback_query.edit_message_reply_markup(
        text = text,
        reply_markup = keyboard
    )
    return MANAGE_CHECKLIST

def select_info_request(update: Update, context: CallbackContext) -> str:
    infotype = update.callback_query.data
    store_temp_data(context, infotype, [REQUEST, INFOTYPE])
    """Add requests to checklist one by one"""
    buttons = [
        [
            InlineKeyboardButton(
                text = "Username",
                callback_data = str(USERNAME)
            ),
            InlineKeyboardButton(
                text = "Description",
                callback_data = str(DESCRIPTION)
            ),
            InlineKeyboardButton(
                text = "Cost",
                callback_data = str(COST)
            )
        ],
        [
            InlineKeyboardButton(
                text = "Done",
                callback_data = str(CONFIRM_REQUEST) # should also print checklist
            ),
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    checklist_name = get_temp_data(context, [CHECKLIST, NAME])
    if checklist_name == None:
        printable_name = ""
    else:
        printable_name = " " + checklist_name
    text = f"Adding a new payment request to Checklist{printable_name}."
    text += request_to_string(context)
    text += "Select one of the following info to add.\n\nButton Guide\nDone: Review Request.\nCancel: Return to start menu"
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    return SELECT_INFO_REQUEST

def ask_for_info_request(update: Update, context: CallbackContext) -> str:
    """ask user for the information of the type specified in previous menu"""
    infotype = get_temp_data(context, [REQUEST, INFOTYPE])
    if infotype == None:
        infotype = str(USERNAME)

    buttons = [
        [
            InlineKeyboardButton(
                text = "Back",
                callback_data = str(SELECT_INFO_REQUEST)
            ),
            InlineKeyboardButton(
                text = "Cancel",
                callback_data = str(END)
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    """Different texts for different infotype"""
    text = ""
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
    
    return ASK_FOR_INFO_REQUEST

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
                callback_context = str(MANAGE_CHECKLIST) # TODO: change to manage checklist menu
            )
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    text = "Please review your request for payment.\n"
    text += request_to_string(context) + "\n\n"
    text += "Button Guide\nEdit: Return to selecting info to edit\nConfirm: Adds request to checklist if all details are filled up.\nCancel: Return to start menu"
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = text,
        reply_markup = keyboard
    )
    
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
    INSERT INTO Requests(order_id, debtor_username, descr, cost)
    VALUES('{checklist_id}', '{debtor_username}', '{descr}', '{cost}');
    """)

    return conn.commit()

def request_to_string(context: CallbackContext, *request_id: Tuple[int]) -> str:
    if request_id:
        request_id = request_id[0]
        request_tpl = db_get_request(request_id)
        debtor_username, descr, cost = request_tpl[2:5]
    else:
        debtor_username = get_temp_data(context, [REQUEST, USERNAME])
        descr = get_temp_data(context, [REQUEST, DESCRIPTION])
        cost = get_temp_data(context, [REQUEST, COST])
    return f"@{debtor_username} bought {descr} for ${cost}."

def db_get_request(request_id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE id = {request_id}
    """)
    return curr.fetchall()

def db_get_open_checklists_of_payer_username(username: str) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT * FROM Checklists
    WHERE payer_username = '{username}'
    AND closed = FALSE;
    """)
    return curr.fetchall()

def db_get_checklist(checklist_id: int) -> Tuple:
    curr.execute(f"""
    SELECT * FROM Checklists
    WHERE id = {checklist_id};
    """)
    return curr.fetchall()

def checklist_to_string(checklist: Tuple) -> str:
    checklist_id = checklist[0]
    descr = checklist[3]
    datetime = checklist[2]
    requests = db_get_requests_of_checklist(checklist_id)
    requests_str = ""
    for request in requests:
        request_id = request[0]
        requests_str += f"{request_to_string(request_id)}"
    return f"{descr}, created on {datetime}"

def db_get_requests_of_checklist(checklist_id: int) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT id FROM REQUESTS
    WHERE checklist_id = {checklist_id};
    """)
    return curr.fetchall()

def db_get_unpaid_requests_of_checklist(checklist_id: int) -> Tuple[Tuple, ...]:
    curr.execute(f"""
    SELECT * FROM Requests
    WHERE checklist_id = {checklist_id}
    AND paid = FALSE
    """)
    return curr.fetchall()

def end_manage_checklist(update: Update, context: CallbackContext) -> str:
    clear_temp_data(context, [REQUEST])
    clear_temp_data(context, [CHECKLIST])
    selecting_action(update, context)
    return END

###########################
# SEND REMINDER FUNCTIONS #
###########################

def send_reminders(update: Update, context: CallbackContext) -> str:
    payer_username = get_username(update)
    checklist_id = get_temp_data(context, [CHECKLIST, ID])
    
    # """Coming from start menu, send reminder for all unpaid requests"""
    if not checklist_id == None:
        checklists = db_get_open_checklists_of_payer_username(payer_username)
        for checklist in checklists:
            send_reminder(update, checklist)
    
    # """Coming from manage checklist, send reminder for unpaid requests in chosen checklist"""
    else:
        checklist = db_get_checklist(checklist_id)
        send_reminder(update, checklist)

    return SEND_REMINDERS

def send_reminder(update: Update, checklist: Tuple):
    checklist_id = checklist[0]
    payer_username = checklist[1]
    requests = db_get_unpaid_requests_of_checklist(checklist_id)
    for request in requests:
        req_descr = request[3]
        req_cost = request[4]
        msg_str = f"Reminder to pay @{payer_username} ${req_cost} for {req_descr}."
        debtor_username = request[2]
        buttons = [InlineKeyboardButton(
            text = "Paid",
            callback_data = str(PAID)
        )]
        keyboard = InlineKeyboardMarkup(buttons)
        is_sent = Bot.send_message(
            chat_id = f"@{debtor_username}",
            text = msg_str,
            reply_markup = keyboard
        )
        """Inform payer of status of sending each reminder"""
        text = ""
        if is_sent:
            text = f"@{debtor_username} reminded to pay {req_cost} for {req_descr}"
        else:
            text = f"Could not remind @{debtor_username} to pay {req_cost} for {req_descr}"
        update.message.reply_text(text = text)

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

    ############################
    # Manage checklist handler #
    ############################

    # Initialise create_checklist_handler, defined below
    create_checklist_handler = ConversationHandler(
        entry_points = [],
        states = {},
        fallbacks = [],
        map_to_parent = {}
    )

    # Support buttons for selecting info request
    select_info_request_handler = [
        CallbackQueryHandler(
            ask_for_info_request,
            pattern = f'^{DESCRIPTION}$|^{USERNAME}$|^{COST}$'
        ),
        CallbackQueryHandler(
            confirm_request,
            pattern = f"^{CONFIRM_REQUEST}&"
        ),
    ]

    # Supports buttons for asking for info
    ask_for_info_request_handler = [
        CallbackQueryHandler(
            select_info_request,
            pattern = "^" + str(SELECT_INFO_REQUEST) + "$"
        ),
    ]

    # Menu
    manage_checklist_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(
                view_checklists,
                pattern = "^" + str(VIEW_CHECKLISTS) + "$"
            ),
            CallbackQueryHandler(
                ask_for_info_request,
                pattern = "^" + str(ASK_FOR_INFO_REQUEST) + "$"
            )
        ],
        states = {
            ACCEPT_NAME_CHECKLIST: ask_for_info_request_handler,
            VIEW_CHECKLISTS: [create_checklist_handler],
            SELECT_INFO_REQUEST: select_info_request_handler,
            ASK_FOR_INFO_REQUEST: ask_for_info_request_handler,
        },
        fallbacks = [
            CallbackQueryHandler(
                end_manage_checklist,
                pattern = f"^{END}$"
            ),
            CommandHandler('stop', stop_nested)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            STOPPING: STOPPING
        }
    )

    ############################
    # Create checklist handler #
    ############################

    # Supports input and buttons for naming checklist
    naming_checklist_handlers = [
        MessageHandler(Filters.text & ~Filters.command, confirm_name_checklist),
        CallbackQueryHandler(
            selecting_action,
            pattern = "^" + str(SELECTING_ACTION) + "$"
        ),
        CallbackQueryHandler(
            confirm_name_checklist,
            pattern = "^" + str(CONFIRM_NAME_CHECKLIST) + "$"
        )
    ]
    # Supports buttons for confirming checklist
    confirm_name_checklist_handlers = [
        CallbackQueryHandler(
            accept_name_checklist,
            pattern = "^" + str(ACCEPT_NAME_CHECKLIST) + "$"
        ),
        CallbackQueryHandler(
            name_checklist,
            pattern = "^" + str(NAME_CHECKLIST) + "$"
        )
    ]

    # Menu
    create_checklist_handler = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(
                name_checklist,
                pattern = "^" + str(NAME_CHECKLIST) + "$"
            )
        ],
        states = {
            NAME_CHECKLIST: naming_checklist_handlers,
            CONFIRM_NAME_CHECKLIST: confirm_name_checklist_handlers,
            ACCEPT_NAME_CHECKLIST: [manage_checklist_handler],
        },
        fallbacks = [
            CallbackQueryHandler(
                end_create_checklist,
                pattern = f"^{END}$" 
            ),
            CommandHandler('stop', stop_nested)
        ],
        map_to_parent = {
            END: SELECTING_ACTION,
            STOPPING: END
        }
    )

    ####################################################
    # Top level ConversationHandler (selecting action) #
    ####################################################
    # supports the buttons for start menu
    selection_handlers = [
        create_checklist_handler,
        manage_checklist_handler,
        CallbackQueryHandler(
            end,
            pattern = "^" + str(END) + "$"
        )
    ]

    # Menu
    conv_handler = ConversationHandler(
        entry_points = [
            CommandHandler("start", selecting_action)
        ],
        states = {
            SELECTING_ACTION: selection_handlers,     
            STOPPING: [CommandHandler('start', selecting_action)]
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