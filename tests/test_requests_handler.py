from lib.handler import requests_handler


def test_fetches_max_page_pages(monkeypatch):
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return '<html></html>'

    monkeypatch.setattr(requests_handler, 'fetch', fake_fetch)

    requests_handler.get_ptt_title_and_url('Test', 10)

    assert len(fetched_urls) == 5
    assert fetched_urls[-1].endswith('page=5&q=recommend%3A10')


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
