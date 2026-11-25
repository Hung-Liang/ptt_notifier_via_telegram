import pytest

from lib.handler.subscription_store import Outcome, SubscriptionStore
from lib.utils.tools import save_json


@pytest.fixture
def store(tmp_path):
    return SubscriptionStore(tmp_path / 'user.json', max_boards=3)


def test_missing_file_is_bootstrapped(tmp_path, store):
    assert store.users() == {}
    assert (tmp_path / 'user.json').exists()


def test_register_new_and_existing(store):
    assert store.register(1, 'old')
    assert not store.register(1, 'new')

    assert store.users() == {'1': {'name': 'new', 'boards': {}}}


def test_refresh_name(store):
    store.register(1, 'old')

    store.refresh_name(1, 'new')
    store.refresh_name(2, 'nobody')

    assert store.users() == {'1': {'name': 'new', 'boards': {}}}


def test_subscribe_and_update(store):
    store.register(1, 'tester')

    assert store.subscribe(1, 'Test', '10') is Outcome.DONE
    assert store.subscribe(1, 'Test', '50') is Outcome.DONE

    assert store.boards_of(1) == {'Test': '50'}


def test_subscribe_respects_limit(store):
    store.register(1, 'tester')
    for i in range(3):
        assert store.subscribe(1, f'Board{i}', '10') is Outcome.DONE

    assert store.subscribe(1, 'Extra', '10') is Outcome.BOARD_LIMIT
    # Updating the threshold of a subscribed board is still allowed
    assert store.subscribe(1, 'Board0', '50') is Outcome.DONE

    assert store.boards_of(1) == {
        'Board0': '50',
        'Board1': '10',
        'Board2': '10',
    }


def test_unsubscribe(store):
    store.register(1, 'tester')
    store.subscribe(1, 'Test', '10')

    assert store.unsubscribe(1, 'Test') is Outcome.DONE
    assert store.unsubscribe(1, 'Test') is Outcome.NOT_SUBSCRIBED
    assert store.boards_of(1) == {}


def test_unregistered_user(store):
    assert store.boards_of(1) is None
    assert store.subscribe(1, 'Test', '10') is Outcome.NOT_REGISTERED
    assert store.unsubscribe(1, 'Test') is Outcome.NOT_REGISTERED
    assert not store.remove(1)
    assert store.users() == {}


def test_remove_is_idempotent(store):
    store.register(1, 'tester')

    assert store.remove(1)
    assert not store.remove(1)
    assert store.boards_of(1) is None


def test_int_and_str_uids_are_the_same_user(store):
    store.register(1, 'tester')

    assert not store.register('1', 'tester')
    assert store.subscribe('1', 'Test', '10') is Outcome.DONE
    assert store.boards_of(1) == {'Test': '10'}


def test_reads_existing_file(tmp_path):
    path = tmp_path / 'user.json'
    save_json(path, {'7': {'name': 'a', 'boards': {'Test': '10'}}})

    assert SubscriptionStore(path).boards_of(7) == {'Test': '10'}
