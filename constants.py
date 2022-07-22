from telegram.ext import ConversationHandler

#############################
# CONSTANTS AND DEFINITIONS #
#############################

# START MENU
SELECTING_ACTION, SELECTING_REQUEST_INFO, VIEW_REQUESTS, PAY, ACKNOWLEDGE, REMIND, = map(str, range(6))

# CREATE REQUEST (SELECTING_REQUEST_INFO)
ASK_FOR_REQUEST_INFO, CONFIRM_REQUEST, SAVE_REQUEST = map(str, range(6, 9))

# META STATE
STOPPING, TEMP_STORE, END_INNER = map(str, range(9, 12))

# ConversationHandler.END
END = ConversationHandler.END

# Constants
(
    START_OVER,
    REQUEST,
    INFOTYPE,
    USERNAME,
    DESCRIPTION,
    COST,
) = map(str, range(12, 18))