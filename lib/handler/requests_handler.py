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


def fetch(url: str):
    """Fetch the content of the url.

    Args:
        `url`: The url to fetch.

    Returns:
        The content of the url.
    """
    headers = {'User-Agent': "Googlebot/2.1 (+http://www.google.com/bot.html)"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    return res.text


def get_ptt_title_and_url(
    board: str, likes: int, page: int = 1, max_page: int = 5
):
    """Get the title and url of the PTT threads.

    Args:
        `board`: The name of the board.
        `likes`: The number of likes.
            Search for threads with more than this number of likes.
        `page`: Optional. The page number. Defaults to 1.
        `max_page`: The maximum page number. Defaults to 5. Used for recursion.

    Returns:
        list: The list of the title and url of the PTT threads.
    """
    url = 'https://www.ptt.cc/bbs/{}/search?page={}&q=recommend%3A{}'.format(
        board, page, likes
    )
    soup = BeautifulSoup(fetch(url), 'lxml')
    threads = find_thread_info(soup)

    if page < max_page:
        threads += get_ptt_title_and_url(board, likes, page + 1, max_page)

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
