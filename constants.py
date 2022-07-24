from telegram.ext import ConversationHandler

#############################
# CONSTANTS AND DEFINITIONS #
#############################

# START MENU
SELECTING_ACTION, SELECTING_REQUEST_INFO, VIEW_REQUESTS, VIEW_OWED, VIEW_UPDATES, REMIND, = map(str, range(6))

# CREATE REQUEST (SELECTING_REQUEST_INFO)
ASK_FOR_REQUEST_INFO, CONFIRM_REQUEST, SAVE_REQUEST = map(str, range(6, 9))

# PAY (VIEW_OWED)
SELECT_REQUEST = map(str, range(9,10))

# ACKNOWLEDGE (VIEW_UPDATES)
SELECT_UPDATE, ACKNOWLEDGE_OR_REJECT = map(str, range(10,12))

# META STATE
STOPPING, TEMP_STORE, END_INNER = map(str, range(12, 15))

# ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,
    REQUEST,
    ID,
    INFOTYPE,
    USERNAME,
    DESCRIPTION,
    COST,
    PAY,
    ACKNOWLEDGE,
    REJECT
) = map(str, range(15, 25))