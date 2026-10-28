import json

import pytest
import requests

from lib.handler.board_feed import MAX_PAGE, BoardFeed, Subscription, Thread

SUBSCRIPTION = Subscription('Test', '10')


def thread(i):
    return Thread('10', f't{i}', f'/bbs/Test/M.{i}.A.html')


def search_page(threads):
    return ''.join(
        '<div class="r-ent"><div class="nrec">{}</div>'
        '<div class="title"><a href="{}">{}</a></div></div>'.format(
            t.like, t.url, t.title
        )
        for t in threads
    )


class FakePtt:
    """Serves `pages` as PTT search pages; missing pages are empty."""

    def __init__(self, *pages):
        self.pages = list(pages)
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        page = int(url.split('page=')[1].split('&')[0])
        if page > len(self.pages):
            return '<html></html>'
        result = self.pages[page - 1]
        if isinstance(result, Exception):
            raise result
        return search_page(result)


def http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


def make_feed(tmp_path, ptt):
    return BoardFeed(records_path=tmp_path, fetch=ptt)


def test_first_run_records_baseline_only(tmp_path):
    ptt = FakePtt([thread(1)])
    feed = make_feed(tmp_path, ptt)

    assert feed.new_threads(SUBSCRIPTION) == []

    ptt.pages = [[thread(2), thread(1)]]
    assert feed.new_threads(SUBSCRIPTION) == [thread(2)]


def test_threads_are_returned_until_marked_seen(tmp_path):
    ptt = FakePtt([thread(1)])
    feed = make_feed(tmp_path, ptt)
    feed.new_threads(SUBSCRIPTION)

    ptt.pages = [[thread(3), thread(2), thread(1)]]
    assert feed.new_threads(SUBSCRIPTION) == [thread(3), thread(2)]

    feed.mark_seen(SUBSCRIPTION, [thread(2)])
    assert feed.new_threads(SUBSCRIPTION) == [thread(3)]


def test_trim_keeps_threads_from_latest_fetch(tmp_path):
    old = [thread(i) for i in range(1000, 1000 + MAX_PAGE * 20 * 3)]
    latest = [thread(i) for i in range(MAX_PAGE * 20)]
    ptt = FakePtt(old)
    feed = make_feed(tmp_path, ptt)
    feed.new_threads(SUBSCRIPTION)

    ptt.pages = [latest]
    assert feed.new_threads(SUBSCRIPTION) == latest
    feed.mark_seen(SUBSCRIPTION, latest)

    assert feed.new_threads(SUBSCRIPTION) == []
    # The oldest threads were trimmed from the record
    ptt.pages = [old[:1]]
    assert feed.new_threads(SUBSCRIPTION) == old[:1]


def test_fetches_up_to_max_page_pages(tmp_path):
    ptt = FakePtt(*[[thread(i)] for i in range(1, MAX_PAGE + 2)])
    feed = make_feed(tmp_path, ptt)
    feed.new_threads(SUBSCRIPTION)

    ptt.pages[0] = [thread(0)]
    ptt.urls.clear()
    assert feed.new_threads(SUBSCRIPTION) == [thread(0)]
    assert len(ptt.urls) == MAX_PAGE
    assert ptt.urls[-1].endswith(f'page={MAX_PAGE}&q=recommend%3A10')


def test_empty_page_stops_paging(tmp_path):
    ptt = FakePtt([thread(1)], [], [thread(3)])
    make_feed(tmp_path, ptt).new_threads(SUBSCRIPTION)

    assert len(ptt.urls) == 2


def test_missing_page_keeps_fetched_threads(tmp_path):
    ptt = FakePtt([], [], http_error(404))
    feed = make_feed(tmp_path, ptt)
    feed.new_threads(SUBSCRIPTION)

    ptt.pages[:2] = [[thread(1)], [thread(2)]]
    assert feed.new_threads(SUBSCRIPTION) == [thread(1), thread(2)]


@pytest.mark.parametrize('page, status_code', [(1, 404), (2, 500)])
def test_other_http_errors_raise(tmp_path, page, status_code):
    pages = [[thread(1)], [thread(2)]]
    pages[page - 1] = http_error(status_code)
    feed = make_feed(tmp_path, FakePtt(*pages))

    with pytest.raises(requests.HTTPError):
        feed.new_threads(SUBSCRIPTION)


def test_prune_removes_unsubscribed_records(tmp_path):
    ptt = FakePtt([thread(1)])
    feed = make_feed(tmp_path, ptt)
    for board, threshold in [('Test', '10'), ('Test', '50'), ('Gone', '10')]:
        feed.new_threads(Subscription(board, threshold))

    feed.prune({SUBSCRIPTION})

    assert sorted(p.name for p in tmp_path.rglob('*.json')) == [
        'Test_10.json'
    ]
    assert not (tmp_path / 'Gone').exists()


def test_resubscribe_after_prune_starts_from_baseline(tmp_path):
    ptt = FakePtt([thread(1)])
    feed = make_feed(tmp_path, ptt)
    feed.new_threads(SUBSCRIPTION)
    feed.prune(set())

    ptt.pages = [[thread(2), thread(1)]]
    assert feed.new_threads(SUBSCRIPTION) == []


def test_reads_record_written_as_lists(tmp_path):
    record = tmp_path / 'Test' / 'Test_10.json'
    record.parent.mkdir()
    record.write_text(json.dumps([['10', 't1', '/bbs/Test/M.1.A.html']]))
    feed = make_feed(tmp_path, FakePtt([thread(2), thread(1)]))

    new = feed.new_threads(SUBSCRIPTION)

    assert new == [thread(2)]
    assert new[0].url == '/bbs/Test/M.2.A.html'
