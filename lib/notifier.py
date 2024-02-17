from lib.handler.output_handler import create_board_message
from lib.handler.requests_handler import get_new_threads
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.tools import get_users


def notifier():
    users = get_users()

    update_threads = {}

    for uid in users:

        current_threads = {}

        for board in users[uid]["boards"]:
            like = users[uid]["boards"][board]

            board_and_like = "{}_{}".format(board, like)

            if board_and_like in update_threads:
                threads = update_threads[board_and_like]
            else:
                threads = get_new_threads(board, like)
                update_threads[board_and_like] = threads

            current_threads[board] = threads

        messages = create_board_message(current_threads)

        if len(messages) == 0:
            continue

        TelegramHandler().send_multiple_messages(uid, messages)
