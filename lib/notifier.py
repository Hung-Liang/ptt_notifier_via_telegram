import traceback

from lib.handler.output_handler import create_board_message
from lib.handler.requests_handler import get_new_threads
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.file_path import HEARTBEAT_PATH
from lib.utils.logger import log
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
                try:
                    threads = get_new_threads(board, like)
                except Exception:
                    # Skip this board so one failure doesn't block others;
                    # cache the empty result to avoid refetching this run
                    log('[notifier]', board_and_like, traceback.format_exc())
                    threads = []
                update_threads[board_and_like] = threads

            current_threads[board] = threads

        messages = create_board_message(current_threads)

        if len(messages) == 0:
            continue

        TelegramHandler().send_multiple_messages(uid, messages)

    HEARTBEAT_PATH.touch()
