from concurrent.futures import ThreadPoolExecutor

from lib.handler.board_feed import BoardFeed
from lib.handler.output_handler import create_board_message_with_threads
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramHandler,
    TelegramSendError,
)
from lib.utils.file_path import HEARTBEAT_PATH
from lib.utils.logger import log, log_error, log_warning
from lib.utils.tools import get_users, remove_user


# Kept low so a run does not flood PTT with requests
FETCH_WORKERS = 4

BOARD_FEED = BoardFeed()


def fetch_new_threads(board_feed, subscription):
    try:
        return board_feed.new_threads(subscription)
    except Exception:
        # Skip this board so one failure doesn't block others
        log_error('[notifier]', subscription, exc_info=True)
        return []


def notifier(board_feed=BOARD_FEED):
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
        results = executor.map(
            lambda subscription: fetch_new_threads(board_feed, subscription),
            subscriptions,
        )
        update_threads = dict(zip(subscriptions, results, strict=True))

    # Threads are shared by every user with the same board and threshold,
    # so a retryable failure for any of them keeps the threads unseen and
    # all of them get it again next run; duplicates beat missed threads.
    # Only threads in messages not yet sent are kept unseen
    failed_threads = set()

    for uid in users:

        current_threads = {
            board: update_threads[(board, like)]
            for board, like in users[uid]["boards"].items()
        }

        messages = create_board_message_with_threads(current_threads)

        if len(messages) == 0:
            continue

        try:
            if not TelegramHandler().send_multiple_messages(
                uid, [message for message, _ in messages]
            ):
                log_warning('[notifier]', f'{uid} rejected some messages')
        except TelegramBlockedError:
            log('[notifier]', f'{uid} blocked the bot, removing user')
            remove_user(uid)
        except TelegramSendError as e:
            log_error('[notifier]', f'{uid} send failed, retry next run: {e}')
            failed_threads.update(
                (board, users[uid]["boards"][board], thread.url)
                for _, message_threads in messages[e.sent :]
                for board, thread in message_threads
            )

    for (board, like), threads in update_threads.items():
        sent_threads = [
            thread
            for thread in threads
            if (board, like, thread.url) not in failed_threads
        ]
        if sent_threads:
            board_feed.mark_seen((board, like), sent_threads)

    board_feed.prune(update_threads.keys())

    HEARTBEAT_PATH.touch()
