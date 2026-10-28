import pytest
import requests

from lib.handler import requests_handler


def search_page(page):
    return (
        '<div class="r-ent"><div class="nrec">10</div>'
        f'<div class="title"><a href="/bbs/Test/M.{page}.A.html">t{page}</a>'
        '</div></div>'
    )


def http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


def test_fetches_max_page_pages(monkeypatch):
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return search_page(len(fetched_urls))

    monkeypatch.setattr(requests_handler, 'fetch', fake_fetch)

    threads = requests_handler.get_ptt_title_and_url('Test', 10)

    assert len(fetched_urls) == 5
    assert len(threads) == 5
    assert fetched_urls[-1].endswith('page=5&q=recommend%3A10')


def test_missing_page_keeps_fetched_threads(monkeypatch):
    def fake_fetch(url):
        if 'page=3&' in url:
            raise http_error(404)
        return search_page(url.split('page=')[1].split('&')[0])

    monkeypatch.setattr(requests_handler, 'fetch', fake_fetch)

    threads = requests_handler.get_ptt_title_and_url('Test', 10)

    assert [thread[2] for thread in threads] == [
        '/bbs/Test/M.1.A.html',
        '/bbs/Test/M.2.A.html',
    ]


def test_empty_page_stops_paging(monkeypatch):
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return search_page(1) if len(fetched_urls) == 1 else '<html></html>'

    monkeypatch.setattr(requests_handler, 'fetch', fake_fetch)

    threads = requests_handler.get_ptt_title_and_url('Test', 10)

    assert len(fetched_urls) == 2
    assert len(threads) == 1


@pytest.mark.parametrize('page, status_code', [(1, 404), (2, 500)])
def test_other_http_errors_raise(monkeypatch, page, status_code):
    def fake_fetch(url):
        if f'page={page}&' in url:
            raise http_error(status_code)
        return search_page(1)

    monkeypatch.setattr(requests_handler, 'fetch', fake_fetch)

    with pytest.raises(requests.HTTPError):
        requests_handler.get_ptt_title_and_url('Test', 10)


def test_first_run_records_baseline_only(monkeypatch, tmp_path):
    first = ['10', 'old', '/bbs/Test/M.1.A.html']
    second = ['10', 'new', '/bbs/Test/M.2.A.html']
    fetched = [[first]]

    monkeypatch.setattr(requests_handler, 'BOARDS_PATH', tmp_path)
    monkeypatch.setattr(
        requests_handler,
        'get_ptt_title_and_url',
        lambda board, like: fetched[-1],
    )

    assert requests_handler.get_new_threads('Test', '10') == []

    fetched.append([second, first])
    assert requests_handler.get_new_threads('Test', '10') == [second]
    # Not marked yet, so it is returned again until sent
    assert requests_handler.get_new_threads('Test', '10') == [second]

    requests_handler.mark_threads_seen('Test', '10', [second])
    assert requests_handler.get_new_threads('Test', '10') == []
