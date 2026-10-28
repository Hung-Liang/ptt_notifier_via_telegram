import pytest
import requests

from lib.handler import telegram_handler
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramHandler,
    TelegramSendError,
)


class FakeResponse:
    def __init__(self, status_code=200, text='{"ok":true}'):
        self.status_code = status_code
        self.text = text


def make_handler():
    handler = TelegramHandler()
    handler.token = '123:secret'
    return handler


def test_send_message_posts_json(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append((url, json, timeout))
        return FakeResponse()

    monkeypatch.setattr(telegram_handler.requests, 'post', fake_post)

    message = '<b>[10] A&B #1 +2</b>'
    assert make_handler().send_message(42, message) is True

    url, payload, timeout = calls[0]
    assert url == 'https://api.telegram.org/bot123:secret/sendMessage'
    assert payload == {'chat_id': 42, 'parse_mode': 'HTML', 'text': message}
    assert timeout is not None


def test_send_message_error_hides_token(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.ConnectionError(f'Max retries exceeded with url: {url}')

    monkeypatch.setattr(telegram_handler.requests, 'post', fake_post)

    with pytest.raises(TelegramSendError) as exc_info:
        make_handler().send_message(42, 'hi')

    assert 'secret' not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


@pytest.mark.parametrize(
    'status_code, text, expected',
    [
        (429, 'Too Many Requests', TelegramSendError),
        (502, 'Bad Gateway', TelegramSendError),
        (403, 'Forbidden: bot was blocked by the user', TelegramBlockedError),
        (403, 'Forbidden: user is deactivated', TelegramBlockedError),
    ],
)
def test_send_message_error_types(monkeypatch, status_code, text, expected):
    monkeypatch.setattr(
        telegram_handler.requests,
        'post',
        lambda url, json, timeout: FakeResponse(status_code, text),
    )

    with pytest.raises(expected):
        make_handler().send_message(42, 'hi')


def test_send_message_rejected_returns_false(monkeypatch):
    monkeypatch.setattr(
        telegram_handler.requests,
        'post',
        lambda url, json, timeout: FakeResponse(400, "can't parse entities"),
    )

    assert make_handler().send_message(42, 'hi') is False


def test_other_forbidden_errors_are_not_treated_as_blocked(monkeypatch):
    monkeypatch.setattr(
        telegram_handler.requests,
        'post',
        lambda url, json, timeout: FakeResponse(
            403, 'Forbidden: bot was kicked from the group chat'
        ),
    )

    assert make_handler().send_message(42, 'hi') is False
