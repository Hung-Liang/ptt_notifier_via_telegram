from pathlib import Path

import requests
from bs4 import BeautifulSoup

from lib.handler.output_handler import (
    compare_with_old,
    find_thread_info,
    update_old_threads,
)
from lib.utils.file_path import BOARDS_PATH
from lib.utils.tools import load_json, save_json

SEARCH_URL = 'https://www.ptt.cc/bbs/{}/search?page={}&q=recommend%3A{}'


def fetch(url: str):
    """Fetch the content of the url.

    Args:
        `url`: The url to fetch.

    Returns:
        The content of the url.
    """
    headers = {'User-Agent': "Googlebot/2.1 (+http://www.google.com/bot.html)"}
    # PTT's own "I am over 18" consent cookie for adult-only boards
    cookies = {'over18': '1'}
    res = requests.get(url, headers=headers, cookies=cookies, timeout=10)
    res.raise_for_status()
    return res.text


def get_ptt_title_and_url(board: str, likes: int, max_page: int = 5):
    """Get the title and url of the PTT threads.

    Stops early when a page is missing or empty, keeping the threads
    already fetched.

    Args:
        `board`: The name of the board.
        `likes`: The number of likes.
            Search for threads with more than this number of likes.
        `max_page`: The maximum number of pages to fetch. Defaults to 5.

    Returns:
        list: The list of the title and url of the PTT threads.
    """
    threads = []

    for page in range(1, max_page + 1):
        url = SEARCH_URL.format(board, page, likes)
        try:
            text = fetch(url)
        except requests.HTTPError as e:
            # Pages past the last search result may return 404; a 404 on
            # the first page means the board itself is wrong, so raise
            status_code = getattr(e.response, 'status_code', None)
            if page > 1 and status_code == 404:
                break
            raise

        page_threads = find_thread_info(BeautifulSoup(text, 'lxml'))
        if not page_threads:
            break
        threads += page_threads

    return threads


def get_old_threads_path(board, like):
    """Get the path of the threads already seen for a board and threshold.

    Args:
        `board`: The name of the board.
        `like`: The number of likes.

    Returns:
        The path to the old threads json file.
    """
    board_folder = Path(BOARDS_PATH, board)
    board_folder.mkdir(parents=True, exist_ok=True)

    return Path(board_folder, "{}_{}.json".format(board, like))


def get_new_threads(board, like):
    """Get the new threads.

    The threads are not recorded as seen; call `mark_threads_seen` after
    they are sent. The first run for a board and threshold only records a
    baseline and returns nothing, so subscribers aren't flooded with old
    threads.

    Args:
        `board`: The name of the board.
        `like`: The number of likes.

    Returns:
        The new threads.
    """
    old_threads_path = get_old_threads_path(board, like)

    threads = get_ptt_title_and_url(board, like)

    if not old_threads_path.exists():
        save_json(old_threads_path, threads)
        return []

    old_threads = load_json(old_threads_path)

    return compare_with_old(threads, old_threads)


def mark_threads_seen(board, like, threads):
    """Record threads as seen so they are not sent again.

    Args:
        `board`: The name of the board.
        `like`: The number of likes.
        `threads`: The threads that were sent.
    """
    update_old_threads(get_old_threads_path(board, like), threads)


def remove_unsubscribed_records(subscriptions):
    """Remove seen-thread records that no user subscribes to anymore.

    A record is not updated while nobody subscribes to it, so a later
    subscriber would get every thread posted in between; removing it makes
    the next subscription start from a fresh baseline instead.

    Args:
        `subscriptions`: The (board, like) pairs still subscribed.
    """
    keep = {
        Path(BOARDS_PATH, board, '{}_{}.json'.format(board, like))
        for board, like in subscriptions
    }

    for path in Path(BOARDS_PATH).glob('*/*.json'):
        if path not in keep:
            path.unlink()

    for folder in Path(BOARDS_PATH).iterdir():
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
