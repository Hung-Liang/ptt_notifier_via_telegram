import asyncio
from types import SimpleNamespace

import pytest

import listen_bot


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

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)


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
