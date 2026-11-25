import re

import pytest

from lib.handler import callback_data
from lib.handler.callback_data import BOARD, CONFIRM, DELETE, PAGE
from lib.utils import tools


@pytest.fixture(autouse=True)
def boards(monkeypatch, tmp_path):
    boards_json = tmp_path / 'boards.json'
    tools.save_json(boards_json, {'1': ['A', 'B'], '2': ['C']})
    monkeypatch.setattr(tools, 'BOARDS_JSON_PATH', boards_json)


@pytest.fixture
def warnings(monkeypatch):
    warnings = []
    monkeypatch.setattr(callback_data, 'log_warning', warnings.append)
    return warnings


@pytest.mark.parametrize(
    'action, values, data',
    [
        (PAGE, (2,), 'Page,2'),
        (BOARD, ('A',), 'Board,A'),
        (CONFIRM, ('C', '100'), 'Confirm,C,100'),
        (DELETE, ('Removed',), 'Delete,Removed'),
    ],
)
def test_round_trip_keeps_wire_format(action, values, data):
    assert action.encode(*values) == data
    assert action.decode(data) == values
    assert re.match(action.pattern, data)


@pytest.mark.parametrize(
    'action, data',
    [
        (PAGE, 'Page'),
        (PAGE, 'Page,1,2'),
        (PAGE, 'Page,x'),
        (PAGE, 'Page,-1'),
        (PAGE, 'Page,3'),
        (PAGE, 'Page,'),
        (BOARD, 'Board'),
        (BOARD, 'Board,A,B'),
        (BOARD, 'Board,Unknown'),
        (BOARD, 'Board,../../etc'),
        (CONFIRM, 'Confirm,A'),
        (CONFIRM, 'Confirm,A,10,20'),
        (CONFIRM, 'Confirm,Unknown,10'),
        (CONFIRM, 'Confirm,A,15'),
        (CONFIRM, 'Confirm,A,'),
        (DELETE, 'Delete'),
        (DELETE, 'Delete,A,B'),
        (DELETE, 'Board,A'),
    ],
)
def test_forged_data_is_rejected_and_logged(warnings, action, data):
    assert action.decode(data) is None
    assert warnings == [f'Invalid callback data: {data!r}']


def test_patterns_do_not_overlap():
    actions = [PAGE, BOARD, CONFIRM, DELETE]
    samples = ['Page,1', 'Board,A', 'Confirm,A,10', 'Delete,A']

    for action in actions:
        matched = [s for s in samples if re.match(action.pattern, s)]
        assert matched == [action.encode(*action.decode(matched[0]))]
        assert not re.match(action.pattern, 'x' + matched[0])


def test_encode_rejects_data_over_telegram_limit():
    with pytest.raises(AssertionError):
        DELETE.encode('A' * 64)
