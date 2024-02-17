from lib.handler.output_handler import create_board_message, trim_messages
from lib.handler.requests_handler import get_new_threads
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.tools import get_users


def notifier():
    users = get_users()

    update_thread_messages = {}

    for uid in users:

        current_messages = []
        for board in users[uid]["boards"]:
            like = users[uid]["boards"][board]
            threads = get_new_threads(board, like)

            board_and_like = "{}_{}".format(board, like)

            if board_and_like in update_thread_messages:
                messages = update_thread_messages[board_and_like]
            else:
                messages = create_board_message(board, threads)
                update_thread_messages[board_and_like] = messages

            current_messages += messages

        current_messages = trim_messages(current_messages)

        TelegramHandler().send_multiple_messages(uid, current_messages)
