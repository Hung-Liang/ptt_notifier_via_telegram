import traceback

from lib.handler.output_handler import create_board_message
from lib.handler.requests_handler import get_new_threads, mark_threads_seen
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramHandler,
    TelegramSendError,
)
from lib.utils.file_path import HEARTBEAT_PATH
from lib.utils.logger import log
from lib.utils.tools import get_users, remove_user


def notifier():
    users = get_users()

    update_threads = {}
    # Threads are shared by every user with the same board and threshold,
    # so a retryable failure for any of them keeps the threads unseen and
    # all of them get it again next run; duplicates beat missed threads
    failed_keys = set()

    for uid in users:

        current_threads = {}

        for board in users[uid]["boards"]:
            like = users[uid]["boards"][board]

            board_and_like = (board, like)

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

        try:
            if not TelegramHandler().send_multiple_messages(uid, messages):
                log('[notifier]', f'{uid} rejected some messages')
        except TelegramBlockedError:
            log('[notifier]', f'{uid} blocked the bot, removing user')
            remove_user(uid)
        except TelegramSendError as e:
            log('[notifier]', f'{uid} send failed, retry next run: {e}')
            failed_keys.update(
                (board, users[uid]["boards"][board])
                for board in current_threads
            )

    for (board, like), threads in update_threads.items():
        if threads and (board, like) not in failed_keys:
            mark_threads_seen(board, like, threads)

    HEARTBEAT_PATH.touch()
