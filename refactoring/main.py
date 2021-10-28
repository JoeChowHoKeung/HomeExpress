

from telegram.callbackquery import CallbackQuery
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
import server
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardButton, replykeyboardmarkup
from time import sleep
import logging

from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
api_id = 8487685
api_hash = 'b0e81650a39f65fc038b8a182581d428'
# 2058616638:AAGOp7JqhzalJga69mP_7-vuOGvnJ9dOVZE


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# The API Key we received for our bot
API_KEY = "2058616638:AAGOp7JqhzalJga69mP_7-vuOGvnJ9dOVZE"
# Create an updater object with our API Key
updater = Updater(API_KEY)
# Retrieve the dispatcher, which will be used to add handlers
dispatcher = updater.dispatcher
AGREE, REG_LOCATION = range(2)

class registration:

    def start(update: Update, context: CallbackContext) -> int:
        """
        recieve the start command,
            check the existing user_id,
                if yes, 
                    end this conversation
                    start to ask him need to change the location setting? 
                if no,
                    continue -> private_policy
                    with the keyboard button or inline keyboard
                    to send the location or cancel registration
        """
        user_id = update.message.from_user['id']
        
        for i in [registration.introduction(), registration.private_policy()]:
            update.message.reply_text(i)
            # sleep(10)
        update.message.reply_text(registration.continue_process(), reply_markup = InlineKeyboardMarkup(registration.continue_button()))
        return AGREE

    def continue_button():
        return [[
            InlineKeyboardButton("Continue", callback_data='continue',),
            InlineKeyboardButton("Terminate", callback_data='cancel')
            ]]
        
    def continue_process():
        return 'you may continue the registration process if you agree to provide the location data and user_id and fully understand the operation of Home Express'

    def private_policy():
        # print the private policy
        return "Home express is a telegram bot which is able to receive and store users' GPS location data to the local hosted SQL Database. \nThe whole project, including SQL server component, is designed and developed in Python by Joe, Chow Ho Keung. All of the data will be stored in Joe's Microsoft Surface GO harddisk. \nHome Express would only stored the location data and user_id_number of user. So... No Worries. "
        pass

    def introduction():
        # print the introduction
        return "Hi, I am Home Express Bot. I am created by Joe, Chow Ho Keung, a student from City University of Hong Kong. \nPlease read through the following instruction of Home Express to understand the operation and data pravicy management."

    def location_confirmation(update: Update, context: CallbackContext):
        # database = server.user_database(update.message.chat_id)
        # database.registration((update.message.location.latitute, update.message.location.longitude))
        update.message.reply_text('completed, please press the send my current location button to start your first time in Home Express')
        pass

    def completion(update: Update, context: CallbackContext):
        print('good')
        
        query = update.callback_query
        query.answer()
        print(query.data)
        if (a:=query.data) == 'cancel': ConversationHandler.END
        elif a == 'continue': 
            print('Thank you for trusting me. Now, plz send me your home location through share location features with swiping the map for setting home location.')
        return REG_LOCATION

    def cancel(update: Update, context: CallbackContext) -> int:
        """cancels and ends the conversation"""
        user = update.message.from_user
        logging.info(f'user {user.first_name} canceleed the conversation.')
        update.message.reply_text(
            'the registration is cancelled', reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def conversation_flow():
        """
        this is conversation handler,
            timeout = 3mins
            fallback by 'cancel'
        """
        return ConversationHandler(
            entry_points=[CommandHandler('start', registration.start)],
            states={
                AGREE : [CallbackQueryHandler(registration.completion, pass_update_queue=True)],
                REG_LOCATION : [MessageHandler(Filters.location, registration.location_confirmation)]
            },
            fallbacks=[CommandHandler('cancel', registration.cancel)],
            allow_reentry=False
        )


class user_setting:
    def start() -> int:
        pass

    def confirmation() -> int:
        pass

    def conversation_flow():
        """
        this is conversation handler,
            timeout = 1min
            fallback by 'cancel'
        """
        return ConversationHandler(
            endtry_points=[CommandHandler('setting', user_setting.start)],
            states={
                'confirmation': [MessageHandler(
                    Filters.location, user_setting.confirmation)]
            },
            fallbacks=[CommandHandler('cancel', user_setting.cancel)],
            allow_reentry=False
        )


def match():
    pass


def locaiton():
    pass


def route_genertion():
    pass


dispatcher.add_handler(registration.conversation_flow())
updater.start_polling()
updater.idle()
