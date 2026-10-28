import pytest

from lib import notifier as notifier_module
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)

THREAD = ['10', 'title', '/bbs/Test/M.1.A.html']


@pytest.fixture
def env(monkeypatch, tmp_path):
    state = {
        'users': {
            '1': {'name': 'a', 'boards': {'Test': '10'}},
            '2': {'name': 'b', 'boards': {'Test': '10'}},
            '3': {'name': 'c', 'boards': {'Other': '10'}},
        },
        'send': {},
        'sent_to': [],
        'marked': [],
        'removed': [],
        'subscribed': None,
    }

    class FakeHandler:
        def send_multiple_messages(self, uid, messages):
            state['sent_to'].append(uid)
            outcome = state['send'].get(uid)
            if outcome is not None:
                raise outcome
            return True

    monkeypatch.setattr(notifier_module, 'get_users', lambda: state['users'])
    monkeypatch.setattr(
        notifier_module, 'get_new_threads', lambda board, like: [THREAD]
    )
    monkeypatch.setattr(notifier_module, 'TelegramHandler', FakeHandler)
    monkeypatch.setattr(
        notifier_module,
        'mark_threads_seen',
        lambda board, like, threads: state['marked'].append(board),
    )
    monkeypatch.setattr(
        notifier_module, 'remove_user', state['removed'].append
    )
    monkeypatch.setattr(
        notifier_module,
        'remove_unsubscribed_records',
        lambda subscriptions: state.update(subscribed=set(subscriptions)),
    )
    monkeypatch.setattr(
        notifier_module, 'HEARTBEAT_PATH', tmp_path / '.heartbeat'
    )
    return state


def test_all_sent_marks_every_board(env):
    notifier_module.notifier()

    assert env['sent_to'] == ['1', '2', '3']
    assert sorted(env['marked']) == ['Other', 'Test']
    assert env['subscribed'] == {('Test', '10'), ('Other', '10')}


def test_send_failure_continues_and_keeps_board_unseen(env):
    env['send']['1'] = TelegramSendError('timeout')

    notifier_module.notifier()

    assert env['sent_to'] == ['1', '2', '3']
    assert env['marked'] == ['Other']
    assert notifier_module.HEARTBEAT_PATH.exists()


def test_blocked_user_is_removed_and_board_marked(env):
    env['send']['1'] = TelegramBlockedError('blocked')

    notifier_module.notifier()

    assert env['removed'] == ['1']
    assert sorted(env['marked']) == ['Other', 'Test']
