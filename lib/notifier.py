import os
from concurrent.futures import ThreadPoolExecutor
from itertools import starmap

from dotenv import load_dotenv

from lib.handler.board_feed import BoardFeed, Subscription
from lib.handler.delivery import Delivery
from lib.handler.telegram_handler import TelegramHandler
from lib.utils.file_path import HEARTBEAT_PATH
from lib.utils.logger import log, log_error
from lib.utils.tools import get_users, remove_user

load_dotenv()

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


def notifier(board_feed=BOARD_FEED, delivery=None):
    if delivery is None:
        delivery = Delivery(TelegramHandler(os.environ.get('telegram_token')))

    users = get_users()

    # Each board and threshold is fetched once, shared by its subscribers
    subscriptions = list(
        dict.fromkeys(
            Subscription(board, like)
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
            subscription: update_threads[subscription]
            for subscription in starmap(
                Subscription, users[uid]["boards"].items()
            )
        }

        result = delivery.deliver(uid, current_threads)

        if result.blocked:
            log('[notifier]', f'{uid} blocked the bot, removing user')
            remove_user(uid)

        failed_threads.update(
            (subscription, thread.url)
            for subscription, thread in result.undelivered
        )

    for subscription, threads in update_threads.items():
        sent_threads = [
            thread
            for thread in threads
            if (subscription, thread.url) not in failed_threads
        ]
        if sent_threads:
            board_feed.mark_seen(subscription, sent_threads)

    board_feed.prune(update_threads.keys())

    HEARTBEAT_PATH.touch()
