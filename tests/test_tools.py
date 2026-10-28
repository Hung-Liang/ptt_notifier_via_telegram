from lib.utils import tools


def test_remove_board_ignores_missing_board(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'USER_JSON_PATH', tmp_path / 'user.json')
    tools.initial_user(1, 'tester')
    tools.add_or_update_board(1, 'Test', '10')

    tools.remove_board(1, 'Test')
    tools.remove_board(1, 'Test')

    assert tools.get_users()['1']['boards'] == {}
