from lib.utils import tools


def test_is_valid_board(monkeypatch, tmp_path):
    boards_json = tmp_path / 'boards.json'
    tools.save_json(boards_json, {'0': ['Gossiping'], '1': ['C_Chat']})
    monkeypatch.setattr(tools, 'BOARDS_JSON_PATH', boards_json)

    assert tools.is_valid_board('C_Chat')
    assert not tools.is_valid_board('../../etc')
    assert not tools.is_valid_board('')
