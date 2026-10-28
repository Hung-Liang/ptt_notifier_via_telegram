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
