"""
/start : create or update the table
/anykey: say hello, and update the keyboard
/location item: queryback the question about:

    #1: save the location as target location (will pinned the location data on the chat room)
    #2: search the stops and eta time
    #3: point2point matching service (if the pinned message is available)
"""

from ast import parse
from telegram.ext import (
    Updater,
    MessageHandler,
    Filters,
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram import Update, Chat, replymarkup
import logging
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from time import sleep
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
import Bus

CO_DICT = {"NWFB": "新", "KMB": "九", "CTB": "城"}


class Chat_CheckPoints:
    WELCOME: str = "welcome"
    PIN_LOCATION: str = "pin"
    SEARCH: str = "search"
    MATCH: str = "match"
    HELP: str = "help"
    EXAMPLE: str = "example"
    SHOW_ROUTE: str = "showroute"


class Users:
    """this is the user that will remember the user data"""

    id: str
    location: str
    name: str

    def __init__(self, id: str) -> None:
        """input the update data, get id and check location"""
        self.id = id
        self.chatroom = BOT.get_chat(self.id)
        pass

    def get_location(self) -> None:
        """get the pinned message from chatroom and saved as a target location"""
        self.location = self.chatroom.pinned_message
        if not self.location:
            self.chatroom.send_message("text")
        pass

    def update_location(self, update: Update) -> None:
        self.chatroom.unpin_all_messages()
        self.chatroom.pin_message(update.message.message_id)
        pass

    def visualize_location(self) -> None:
        self.chatroom.send_location(self.location[0], self.location[1])

    def set_target_location(self, update) -> None:
        location = update.message.location
        self.target_location = (location.latitude, location.longitude)


class User_System:
    """this is the system impletements the telegram and access the User"""

    database: dict = {}

    def login(self, update: Update):
        return self._get_user_info(update.message.chat.id)

    def _create_user(self, id: str):
        self.database[id] = Users(id)

    def _is_new_user(self, id):
        if id not in self.database:
            self._create_user(id)

    def _get_user_info(self, id: str):
        self._is_new_user(id)
        user = self.database.get(id)
        return user

    def _save_temp_location(self, user: Users, update: Update):
        pass


class TG_Clients:
    """this is the operation of TG"""

    def enter_conversation(update: Update, context: CallbackContext):
        message = update.message
        keyboard = [
            [
                InlineKeyboardButton(
                    "儲存為目的地(用作點對點搜尋)", callback_data=Chat_CheckPoints.PIN_LOCATION
                )
            ],
            [InlineKeyboardButton("搜尋此目的地附近巴士", callback_data=Chat_CheckPoints.SEARCH)]
        ]

        if BOT.get_chat(update.message.chat.id).pinned_message:
            keyboard.append(
                [InlineKeyboardButton("點對點搜尋", callback_data=Chat_CheckPoints.MATCH)]
            )

        update.message.reply_location(
            latitude=message.location.latitude,
            longitude=message.location.longitude,
            reply_markup=InlineKeyboardMarkup(keyboard),
            reply_to_message_id=message.message_id,
        )

        return Chat_CheckPoints.WELCOME

    def _hear_response(update: Update, context: CallbackContext):
        response = update.callback_query.data
        print(response.split("_")[0])
        if response == Chat_CheckPoints.PIN_LOCATION:
            TG_Clients._pin_location_message(update)
        elif response == Chat_CheckPoints.SEARCH:
            TG_Clients._stop_search(update)
        elif response == Chat_CheckPoints.MATCH:
            TG_Clients._point2point_matching(update)
        elif response[0] == "S":
            TG_Clients._show_search_info(update)
        elif response[0] == "M":
            TG_Clients._show_match_info(update)
        elif response.split("_")[0] == "BACK":
            TG_Clients._leave_chat(update)

    def _pin_location_message(update: Update):
        chatroom = BOT.get_chat(update.callback_query.message.chat.id)
        reply_message_id = update.callback_query.message.reply_to_message.message_id
        if chatroom.pinned_message: chatroom.pinned_message.delete()
        chatroom.pin_message(reply_message_id)
        update.callback_query.answer("已經順利記錄，3秒後退出對話")
        sleep(3)
        update.callback_query.delete_message()

    def _point2point_matching(update: Update):
        chatroom = BOT.get_chat(update.callback_query.message.chat.id)
        update.callback_query.message.reply_to_message.delete()
        target_location = chatroom.pinned_message.location
        current_location = update.callback_query.message.location
        update.callback_query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("載入中", callback_data="load")]])
        )
        output = MASTER.point2point_match(
            (current_location.latitude, current_location.longitude),
            (target_location.latitude, target_location.longitude),
            True,
        )
        update.callback_query.message.delete()
        output.sort_values(by=["route", "co"], inplace=True)
        columns_num = 4
        row_button, keyboard = [], []
        for row in output.itertuples():
            data = "M" + "_".join(
                [row.route, row.dest, row.name, row.name_target, str(row._8)]
            )
            row_button.append(
                InlineKeyboardButton(
                    f"{CO_DICT.get(row.co)}-{row.route}", callback_data=data
                )
            )
            if len(row_button) == columns_num:
                keyboard.append(row_button)
                row_button = []
        if len(row_button) > 0:
            keyboard.append(row_button)
        keyboard.append(
            [
                InlineKeyboardButton(
                    "離開",
                    callback_data=f"BACK_{current_location.latitude}_{current_location.longitude}",
                )
            ]
        )
        chatroom.send_message("請選擇路線", reply_markup=InlineKeyboardMarkup(keyboard))
        return Chat_CheckPoints.WELCOME

    def _stop_search(update: Update):
        chatroom = BOT.get_chat(update.callback_query.message.chat.id)
        location_data = update.callback_query.message.location
        update.callback_query.message.reply_to_message.delete()
        update.callback_query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("載入中", callback_data="load")]])
        )
        output = MASTER.stops_search(
            (location_data.latitude, location_data.longitude), eta=True
        )
        update.callback_query.message.delete()

        output.sort_values(by=["route", "co"], inplace=True)
        columns_num = 4
        row_button, keyboard = [], []
        for row in output.itertuples():
            data = "S" + "_".join(
                [row.route, row.dest, row.name, str(row._8), str(row._9)]
            )
            row_button.append(
                InlineKeyboardButton(
                    f"{CO_DICT.get(row.co)}-{row.route}", callback_data=data
                )
            )
            if len(row_button) == columns_num:
                keyboard.append(row_button)
                row_button = []
        if len(row_button) > 0:
            keyboard.append(row_button)
        keyboard.append(
            [
                InlineKeyboardButton(
                    "離開",
                    callback_data=f"BACK_{location_data.latitude}_{location_data.longitude}",
                )
            ]
        )

        chatroom.send_message("請選擇路線", reply_markup=InlineKeyboardMarkup(keyboard))
        return Chat_CheckPoints.WELCOME

    def _show_search_info(update: Update):
        route, dest, name, eta_1, eta_2 = update.callback_query.data[1:].split("_")
        template = f"""
路線： <code>{route}</code>
目的地： <code>{dest}</code>
附近的站： <code>{name}</code>
{f'<code>1st: {eta_1}</code>' if eta_1 else ''}
{f'<code>2nd: {eta_2}</code>' if eta_2 else ''}
"""
        update.callback_query.answer(f"{route} :  {eta_1}")
        update.callback_query.edit_message_text(
            template,
            parse_mode="HTML",
            reply_markup=update.callback_query.message.reply_markup,
        )
        return Chat_CheckPoints.WELCOME

    def _show_match_info(update: Update):
        route, dest, name, name_target, eta_1 = update.callback_query.data[1:].split(
            "_"
        )
        template = f"""
路線： <code>{route}</code>
往： <code>{dest}</code>
附近的站： <code>{name}</code>
目的地： <code>{name_target}</code>
{f'<code>{eta_1}</code>' if eta_1 else ''}
"""
        update.callback_query.answer(f"{route} :  {eta_1}")
        update.callback_query.edit_message_text(
            template,
            parse_mode="HTML",
            reply_markup=update.callback_query.message.reply_markup,
        )
        return Chat_CheckPoints.WELCOME

    def _leave_chat(update: Update):
        update.callback_query.message.delete()
        return ConversationHandler.END


def echo(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    user = MAIN_SYSTEM.login(update)
    user.chatroom.send_message()


def main():
    CONVERSATION = ConversationHandler(
        entry_points=[MessageHandler(Filters.location, TG_Clients.enter_conversation)],
        states={
            Chat_CheckPoints.WELCOME: [CallbackQueryHandler(TG_Clients._hear_response)]
        },
        fallbacks=[CommandHandler("cancel", echo)],
        allow_reentry=True,
        conversation_timeout=None,
    )
    DISPATCHER.add_handler(CommandHandler("start", echo))
    DISPATCHER.add_handler(CONVERSATION)
    UPDATER.start_polling()
    UPDATER.idle()



API_KEY = "2058616638:AAGOp7JqhzalJga69mP_7-vuOGvnJ9dOVZE"
MASTER = Bus.Data(True)
logger = logging.getLogger(__name__)
UPDATER = Updater(API_KEY, workers=1)
DISPATCHER = UPDATER.dispatcher
BOT = UPDATER.bot
MAIN_SYSTEM = User_System()
main()
