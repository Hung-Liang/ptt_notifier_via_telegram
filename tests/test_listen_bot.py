import asyncio
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import listen_bot
from lib.utils import tools


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


@pytest.mark.parametrize('data', ['Delete', 'Delete,A,B'])
def test_delete_board_rejects_invalid_callback(monkeypatch, data):
    removed = []
    monkeypatch.setattr(listen_bot, 'log', lambda *args: None)
    monkeypatch.setattr(
        listen_bot, 'remove_board', lambda *args: removed.append(args)
    )
    update = make_callback_update(data)

    asyncio.run(listen_bot.delete_board(update, None))

    assert removed == []
    assert update.callback_query.message.edits == []


def test_delete_board_removes_board(monkeypatch):
    removed = []
    monkeypatch.setattr(listen_bot, 'check_if_user_exist', lambda uid: True)
    monkeypatch.setattr(
        listen_bot, 'remove_board', lambda *args: removed.append(args)
    )
    update = make_callback_update('Delete,Gossiping')

    asyncio.run(listen_bot.delete_board(update, None))

    assert removed == [(1, 'Gossiping')]
    assert len(update.callback_query.message.edits) == 1


def test_error_logs_traceback_without_update_details(monkeypatch):
    logged = []
    monkeypatch.setattr(
        listen_bot, 'log', lambda *args: logged.append(' '.join(args))
    )

    try:
        raise ValueError('boom')
    except ValueError as e:
        context = SimpleNamespace(error=e)

    update = SimpleNamespace(update_id=7, message='secret text')
    asyncio.run(listen_bot.error(update, context))

    assert 'Update 7' in logged[0]
    assert 'Traceback' in logged[0] and 'boom' in logged[0]
    assert 'secret text' not in logged[0]


def test_users_messages_joins_users_under_limit():
    users = {
        str(i): {'name': f'user{i}', 'boards': {'Gossiping': '10'}}
        for i in range(300)
    }

    messages = listen_bot.users_messages(users)

    assert 1 < len(messages) < len(users)
    assert all(len(m) <= listen_bot.MESSAGE_LIMIT for m in messages)
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


@pytest.fixture
def added(monkeypatch):
    added = []

    def add_or_update_board(*args):
        added.append(args)
        return True

    monkeypatch.setattr(listen_bot, 'log', lambda *args: None)
    monkeypatch.setattr(listen_bot, 'check_if_user_exist', lambda uid: True)
    monkeypatch.setattr(listen_bot, 'add_or_update_board', add_or_update_board)
    return added


@pytest.mark.parametrize(
    'data',
    [
        'Confirm,A',
        'Confirm,A,10,20',
        'Confirm,Unknown,10',
        'Confirm,../../etc,10',
        'Confirm,A,15',
        'Confirm,A,',
    ],
)
def test_confirm_and_write_rejects_invalid_callback(boards, added, data):
    update = make_callback_update(data)

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert added == []
    assert update.callback_query.message.edits == []


def test_confirm_and_write_requires_registration(
    monkeypatch, boards, added
):
    monkeypatch.setattr(listen_bot, 'check_if_user_exist', lambda uid: False)
    update = make_callback_update('Confirm,A,10')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert added == []
    assert update.callback_query.message.edits == [
        listen_bot.not_registered_message()
    ]


def test_confirm_and_write_reports_board_limit(monkeypatch, boards, added):
    monkeypatch.setattr(
        listen_bot, 'add_or_update_board', lambda *args: False
    )
    update = make_callback_update('Confirm,A,10')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert update.callback_query.message.edits == [
        listen_bot.error_message()
    ]


def test_confirm_and_write_saves_board(boards, added):
    update = make_callback_update('Confirm,E,100')

    asyncio.run(listen_bot.confirm_and_write(update, None))

    assert added == [(1, 'E', '100')]
    assert update.callback_query.message.edits == [
        listen_bot.confirm_message('tester', 'E', '100')
    ]


@pytest.mark.parametrize(
    'data', ['Page', 'Page,1,2', 'Page,x', 'Page,-1', 'Page,0', 'Page,4']
)
def test_page_turner_rejects_invalid_callback(monkeypatch, boards, data):
    monkeypatch.setattr(listen_bot, 'log', lambda *args: None)
    update = make_callback_update(data)

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
