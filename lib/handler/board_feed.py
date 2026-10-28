from pathlib import Path
from typing import NamedTuple

import requests
from bs4 import BeautifulSoup

from lib.utils.config import MAX_PAGE
from lib.utils.file_path import BOARDS_PATH
from lib.utils.tools import load_json, save_json

SEARCH_URL = 'https://www.ptt.cc/bbs/{}/search?page={}&q=recommend%3A{}'

# PTT search lists 20 threads per page
THREADS_PER_FETCH = MAX_PAGE * 20


class Thread(NamedTuple):
    """A PTT thread; `url` is its identity.

    Serialises to the same JSON list as the `[like, title, url]` records
    written before it existed.
    """

    like: str
    title: str
    url: str


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


def parse_threads(text: str):
    """Parse the threads listed on a PTT search page."""
    threads = []

    for element in BeautifulSoup(text, 'lxml').find_all('div', 'r-ent'):
        div_title = element.find('div', 'title')
        if div_title.a is not None:
            like = element.find('div', 'nrec').text.replace('\n', '')
            title = div_title.text.replace('\n', '')
            threads.append(Thread(like, title, div_title.a.get('href')))

    return threads


class BoardFeed:
    """New threads of each Subscription, a (board, threshold) pair.

    Searches PTT for threads with at least `threshold` likes and keeps a
    Seen-thread record per Subscription under `records_path`.
    """

    def __init__(self, records_path=BOARDS_PATH, fetch=fetch):
        self.records_path = Path(records_path)
        self.fetch = fetch

    def new_threads(self, subscription):
        """Threads of `subscription` not in its Seen-thread record.

        The threads are not recorded as seen; call `mark_seen` after they
        are sent. The first run for a Subscription only records a baseline
        and returns nothing, so subscribers aren't flooded with old
        threads.

        Raises:
            Fetch errors, e.g. `requests.HTTPError` when the board is
            wrong, so the caller can skip this Subscription.
        """
        path = self._record_path(subscription)
        threads = self._search(subscription)

        if not path.exists():
            self._save(path, threads)
            return []

        seen_urls = {thread.url for thread in self._load(path)}
        return [thread for thread in threads if thread.url not in seen_urls]

    def mark_seen(self, subscription, threads):
        """Record threads as seen so they are not returned again."""
        path = self._record_path(subscription)
        seen = self._load(path) + list(threads)

        # Keep well above one fetch (`MAX_PAGE` pages x 20 threads) so
        # threads still visible in search results are not trimmed and
        # re-sent
        if len(seen) > THREADS_PER_FETCH * 3:
            seen = seen[-THREADS_PER_FETCH * 2 :]

        self._save(path, seen)

    def prune(self, subscriptions_to_keep):
        """Remove Seen-thread records no user subscribes to anymore.

        A record is not updated while nobody subscribes to it, so a later
        subscriber would get every thread posted in between; removing it
        makes the next subscription start from a fresh baseline instead.
        """
        keep = {self._record_path(s) for s in subscriptions_to_keep}

        for path in self.records_path.glob('*/*.json'):
            if path not in keep:
                path.unlink()

        for folder in self.records_path.iterdir():
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()

    def _search(self, subscription):
        """Threads in the first `MAX_PAGE` search pages, newest first.

        Stops early when a page is missing or empty, keeping the threads
        already fetched.
        """
        board, like = subscription
        threads = []

        for page in range(1, MAX_PAGE + 1):
            url = SEARCH_URL.format(board, page, like)
            try:
                text = self.fetch(url)
            except requests.HTTPError as e:
                # Pages past the last search result may return 404; a 404
                # on the first page means the board itself is wrong, so
                # raise
                status_code = getattr(e.response, 'status_code', None)
                if page > 1 and status_code == 404:
                    break
                raise

            page_threads = parse_threads(text)
            if not page_threads:
                break
            threads += page_threads

        return threads

    def _record_path(self, subscription):
        board, like = subscription
        return Path(self.records_path, board, '{}_{}.json'.format(board, like))

    def _load(self, path):
        return [Thread(*thread) for thread in load_json(path)]

    def _save(self, path, threads):
        path.parent.mkdir(parents=True, exist_ok=True)
        save_json(path, threads)
