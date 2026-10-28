import threading

import pytest

from lib import notifier as notifier_module
from lib.handler.board_feed import Thread
from lib.handler.telegram_handler import (
    TelegramBlockedError,
    TelegramSendError,
)

THREAD = Thread('10', 'title', '/bbs/Test/M.1.A.html')


class FakeBoardFeed:
    def __init__(self, state):
        self.state = state
        self.new_threads = lambda subscription: [THREAD]

    def mark_seen(self, subscription, threads):
        self.state['marked'].append(subscription[0])

    def prune(self, subscriptions_to_keep):
        self.state['subscribed'] = set(subscriptions_to_keep)


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
    monkeypatch.setattr(notifier_module, 'TelegramHandler', FakeHandler)
    monkeypatch.setattr(
        notifier_module, 'remove_user', state['removed'].append
    )
    monkeypatch.setattr(
        notifier_module, 'HEARTBEAT_PATH', tmp_path / '.heartbeat'
    )
    state['feed'] = FakeBoardFeed(state)
    return state


def run(env):
    notifier_module.notifier(board_feed=env['feed'])


def test_all_sent_marks_every_board(env):
    run(env)

    assert env['sent_to'] == ['1', '2', '3']
    assert sorted(env['marked']) == ['Other', 'Test']
    assert env['subscribed'] == {('Test', '10'), ('Other', '10')}


def test_send_failure_continues_and_keeps_board_unseen(env):
    env['send']['1'] = TelegramSendError('timeout')

    run(env)

    assert env['sent_to'] == ['1', '2', '3']
    assert env['marked'] == ['Other']
    assert notifier_module.HEARTBEAT_PATH.exists()


def test_blocked_user_is_removed_and_board_marked(env):
    env['send']['1'] = TelegramBlockedError('blocked')

    run(env)

    assert env['removed'] == ['1']
    assert sorted(env['marked']) == ['Other', 'Test']


def test_each_subscription_fetched_once(env):
    fetched = []

    def fake_new_threads(subscription):
        fetched.append(subscription)
        return [THREAD]

    env['feed'].new_threads = fake_new_threads

    run(env)

    assert sorted(fetched) == [('Other', '10'), ('Test', '10')]


def test_fetch_failure_skips_only_that_board(env, monkeypatch):
    def fake_new_threads(subscription):
        if subscription[0] == 'Test':
            raise ConnectionError('ptt down')
        return [THREAD]

    env['feed'].new_threads = fake_new_threads
    monkeypatch.setattr(
        notifier_module, 'log_error', lambda *args, **kwargs: None
    )

    run(env)

    assert env['sent_to'] == ['3']
    assert env['marked'] == ['Other']


def test_subscriptions_are_fetched_concurrently(env):
    # Both fetches must be in flight at once to pass the barrier
    barrier = threading.Barrier(2, timeout=5)

    def fake_new_threads(subscription):
        barrier.wait()
        return [THREAD]

    env['feed'].new_threads = fake_new_threads

    run(env)

    assert sorted(env['marked']) == ['Other', 'Test']


def test_partial_send_keeps_only_unsent_threads_unseen(env, monkeypatch):
    env['users'] = {
        '1': {'name': 'a', 'boards': {'Test': '10', 'Other': '10'}}
    }
    error = TelegramSendError('timeout')
    error.sent = 1
    env['send']['1'] = error
    # Each board lands in its own message; only the first one was sent
    monkeypatch.setattr(
        notifier_module,
        'create_board_message_with_threads',
        lambda threads: [
            (board, [(board, thread) for thread in threads[board]])
            for board in threads
        ],
    )

    run(env)

    assert env['marked'] == ['Test']
