import traceback
from concurrent.futures import ThreadPoolExecutor

from lib.handler.output_handler import create_board_message
from lib.handler.requests_handler import (
    get_new_threads,
    mark_threads_seen,
    remove_unsubscribed_records,
)
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramHandler,
    TelegramSendError,
)
from lib.utils.file_path import HEARTBEAT_PATH
from lib.utils.logger import log
from lib.utils.tools import get_users, remove_user


# Kept low so a run does not flood PTT with requests
FETCH_WORKERS = 4


def fetch_new_threads(board_and_like):
    try:
        return get_new_threads(*board_and_like)
    except Exception:
        # Skip this board so one failure doesn't block others
        log('[notifier]', board_and_like, traceback.format_exc())
        return []


def notifier():
    users = get_users()

    # Each board and threshold is fetched once, shared by its subscribers
    subscriptions = list(
        dict.fromkeys(
            (board, like)
            for user in users.values()
            for board, like in user["boards"].items()
        )
    )
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        results = executor.map(fetch_new_threads, subscriptions)
        update_threads = dict(zip(subscriptions, results, strict=True))

    # Threads are shared by every user with the same board and threshold,
    # so a retryable failure for any of them keeps the threads unseen and
    # all of them get it again next run; duplicates beat missed threads
    failed_keys = set()

    for uid in users:

        current_threads = {
            board: update_threads[(board, like)]
            for board, like in users[uid]["boards"].items()
        }

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

    remove_unsubscribed_records(update_threads.keys())

    HEARTBEAT_PATH.touch()
