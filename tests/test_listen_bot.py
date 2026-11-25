import asyncio
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import listen_bot
from lib.handler import callback_data
from lib.handler.subscription_store import SubscriptionStore
from lib.utils import tools
from lib.utils.message import MESSAGE_LIMIT


def keyboard_texts(markup):
    return [[button.text for button in row] for row in markup.inline_keyboard]


@pytest.mark.parametrize('count', range(1, 6))
def test_delete_board_maker_keeps_every_board(count):
    boards = {f'Board{i}': '10' for i in range(count)}

    rows = keyboard_texts(listen_bot.delete_board_maker(boards))

    assert [text for row in rows for text in row] == list(boards)
    assert all(1 <= len(row) <= 2 for row in rows)


class FakeMessage:
    def __init__(self):
        self.edits = []
        self.markups = []

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)
        self.markups.append(kwargs.get('reply_markup'))


def make_callback_update(data, uid=1):
    async def answer():
        pass

    query = SimpleNamespace(
        data=data,
        answer=answer,
        from_user=SimpleNamespace(id=uid, name='tester'),
        message=FakeMessage(),
    )
    return SimpleNamespace(callback_query=query)


@pytest.fixture
def store(monkeypatch, tmp_path):
    store = SubscriptionStore(tmp_path / 'user.json')
    monkeypatch.setattr(listen_bot, 'STORE', store)
    return store


@pytest.fixture
def registered(store):
    store.register(1, 'tester')
    return store


def test_delete_board_ignores_invalid_callback(monkeypatch, registered):
    monkeypatch.setattr(callback_data, 'log_warning', lambda *args: None)
    registered.subscribe(1, 'Gossiping', '10')
    update = make_callback_update('Delete,Gossiping,10')

    asyncio.run(listen_bot.delete_board(update, None))

    assert registered.boards_of(1) == {'Gossiping': '10'}
    assert update.callback_query.message.edits == []


def test_delete_board_removes_board(registered):
    registered.subscribe(1, 'Gossiping', '10')
    update = make_callback_update('Delete,Gossiping')

    asyncio.run(listen_bot.delete_board(update, None))

    assert registered.boards_of(1) == {}
    assert update.callback_query.message.edits == [
        listen_bot.delete_confirm_message('tester', 'Gossiping')
    ]


def test_delete_board_reports_missing_board(registered):
    update = make_callback_update('Delete,Gossiping')

    asyncio.run(listen_bot.delete_board(update, None))

    assert update.callback_query.message.edits == [
        listen_bot.board_not_subscribed_message('Gossiping')
    ]


def test_delete_board_requires_registration(store):
    update = make_callback_update('Delete,Gossiping')

    asyncio.run(listen_bot.delete_board(update, None))

    assert update.callback_query.message.edits == [
        listen_bot.not_registered_message()
    ]


def test_error_logs_traceback_without_update_details(monkeypatch):
    logged = []
    monkeypatch.setattr(
        listen_bot,
        'log_error',
        lambda *args, exc_info: logged.append((' '.join(args), exc_info)),
    )

    try:
        raise ValueError('boom')
    except ValueError as e:
        context = SimpleNamespace(error=e)

    update = SimpleNamespace(update_id=7, message='secret text')
    asyncio.run(listen_bot.error(update, context))

    message, exc_info = logged[0]
    assert 'Update 7' in message
    assert exc_info is context.error
    assert 'secret text' not in message


def test_users_messages_joins_users_under_limit():
    users = {
        str(i): {'name': f'user{i}', 'boards': {'Gossiping': '10'}}
        for i in range(300)
    }

    messages = listen_bot.users_messages(users)

    assert 1 < len(messages) < len(users)
    assert all(len(m) <= MESSAGE_LIMIT for m in messages)
    joined = ''.join(messages)
    assert all(f'user{i}\nGossiping 10\n' in joined for i in range(300))


def use_boards(monkeypatch, tmp_path, boards):
    boards_json = tmp_path / 'boards.json'
    tools.save_json(boards_json, boards)
    monkeypatch.setattr(listen_bot, 'BOARDS_JSON_PATH', boards_json)
    monkeypatch.setattr(tools, 'BOARDS_JSON_PATH', boards_json)


@pytest.fixture
def boards(monkeypatch, tmp_path):
    use_boards(
        monkeypatch,
        tmp_path,
        {'1': ['A', 'B', 'C'], '2': ['D'], '3': ['E']},
    )


def test_confirm_and_write_ignores_invalid_callback(
    monkeypatch, boards, registered
):
    monkeypatch.setattr(callback_data, 'log_warning', lambda *args: None)
    update = make_callback_update('Confirm,A,15')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert registered.boards_of(1) == {}
    assert update.callback_query.message.edits == []


def test_confirm_and_write_requires_registration(boards, store):
    update = make_callback_update('Confirm,A,10')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert store.users() == {}
    assert update.callback_query.message.edits == [
        listen_bot.not_registered_message()
    ]


def test_confirm_and_write_reports_board_limit(monkeypatch, tmp_path, boards):
    store = SubscriptionStore(tmp_path / 'user.json', max_boards=0)
    monkeypatch.setattr(listen_bot, 'STORE', store)
    store.register(1, 'tester')
    update = make_callback_update('Confirm,A,10')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert store.boards_of(1) == {}
    assert update.callback_query.message.edits == [
        listen_bot.error_message()
    ]


def test_confirm_and_write_saves_board(boards, registered):
    update = make_callback_update('Confirm,E,100')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert registered.boards_of(1) == {'E': '100'}
    assert update.callback_query.message.edits == [
        listen_bot.confirm_message('tester', 'E', '100')
    ]


def test_page_turner_ignores_invalid_callback(monkeypatch, boards):
    monkeypatch.setattr(callback_data, 'log_warning', lambda *args: None)
    update = make_callback_update('Page,4')

    asyncio.run(listen_bot.page_turner(update, None))

    assert update.callback_query.message.edits == []


@pytest.mark.parametrize('first_page', [0, 1])
def test_page_turner_shows_one_based_page(monkeypatch, tmp_path, first_page):
    use_boards(
        monkeypatch,
        tmp_path,
        {str(first_page): ['A'], str(first_page + 1): ['B']},
    )
    update = make_callback_update(f'Page,{first_page + 1}')

    asyncio.run(listen_bot.page_turner(update, None))

    message = update.callback_query.message
    assert message.edits == [listen_bot.add_message(2)]
    assert keyboard_texts(message.markups[0]) == [['B'], ['<< 上一頁']]


@pytest.mark.parametrize(
    'page, nav',
    [
        (1, ['下一頁 >>']),
        (2, ['<< 上一頁', '下一頁 >>']),
        (3, ['<< 上一頁']),
    ],
)
def test_page_keyboard_maker_navigation(boards, page, nav):
    rows = keyboard_texts(listen_bot.page_keyboard_maker(page))

    assert rows[-1] == nav


def test_page_keyboard_maker_board_buttons(boards):
    markup = listen_bot.page_keyboard_maker(1)

    assert keyboard_texts(markup)[:-1] == [['A', 'B'], ['C']]
    callbacks = [
        button.callback_data
        for row in markup.inline_keyboard[:-1]
        for button in row
    ]
    assert callbacks == ['Board,A', 'Board,B', 'Board,C']


def test_build_application_has_job_queue(monkeypatch):
    monkeypatch.setenv('telegram_token', '123:test')
    timezone = ZoneInfo('Asia/Taipei')

    application = listen_bot.build_application(timezone)

    # The notifier is scheduled on this queue, which needs APScheduler
    assert application.job_queue is not None
    assert application.job_queue.scheduler.timezone == timezone


@pytest.mark.parametrize('user', [None, SimpleNamespace(id=2)])
def test_admin_only_drops_other_users(monkeypatch, user):
    monkeypatch.setenv('admin_id', '1')
    update = SimpleNamespace(effective_user=user)

    with pytest.raises(listen_bot.ApplicationHandlerStop):
        asyncio.run(listen_bot.admin_only(update, None))


def test_admin_only_passes_admin(monkeypatch):
    monkeypatch.setenv('admin_id', '1')
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1))

    asyncio.run(listen_bot.admin_only(update, None))


@pytest.mark.parametrize('admin_mode', [True, False])
def test_build_application_admin_filter(monkeypatch, admin_mode):
    monkeypatch.setenv('telegram_token', '123:test')
    monkeypatch.setattr(listen_bot, 'ADMIN_MODE', admin_mode)

    application = listen_bot.build_application(ZoneInfo('Asia/Taipei'))

    assert (-1 in application.handlers) == admin_mode
