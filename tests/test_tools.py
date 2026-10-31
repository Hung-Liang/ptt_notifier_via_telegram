from lib.utils import tools


def test_remove_board_ignores_missing_board(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'USER_JSON_PATH', tmp_path / 'user.json')
    tools.initial_user(1, 'tester')
    tools.add_or_update_board(1, 'Test', '10')

    assert tools.remove_board(1, 'Test')
    assert not tools.remove_board(1, 'Test')

    assert tools.get_users()['1']['boards'] == {}


def test_add_board_respects_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'USER_JSON_PATH', tmp_path / 'user.json')
    tools.initial_user(1, 'tester')
    for i in range(tools.MAX_BOARDS):
        assert tools.add_or_update_board(1, f'Board{i}', '10')

    assert not tools.add_or_update_board(1, 'Extra', '10')
    # Updating the threshold of a subscribed board is still allowed
    assert tools.add_or_update_board(1, 'Board0', '50')

    boards = tools.get_users()['1']['boards']
    assert len(boards) == tools.MAX_BOARDS
    assert boards['Board0'] == '50'


def test_is_valid_board(monkeypatch, tmp_path):
    boards_json = tmp_path / 'boards.json'
    tools.save_json(boards_json, {'0': ['Gossiping'], '1': ['C_Chat']})
    monkeypatch.setattr(tools, 'BOARDS_JSON_PATH', boards_json)

    assert tools.is_valid_board('C_Chat')
    assert not tools.is_valid_board('../../etc')
    assert not tools.is_valid_board('')


def test_update_user_name(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'USER_JSON_PATH', tmp_path / 'user.json')
    tools.initial_user(1, 'old')
    tools.add_or_update_board(1, 'Test', '10')

    tools.update_user_name(1, 'new')
    tools.update_user_name(2, 'nobody')

    users = tools.get_users()
    assert users == {'1': {'name': 'new', 'boards': {'Test': '10'}}}
