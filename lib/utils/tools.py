import json
import os
from pathlib import Path

from lib.utils.file_path import BOARDS_JSON_PATH


def save_json(path, data):
    """Save data to json file.

    Args:
        `path` : path to save the json file.
        `data` : data to save.
    """
    # Write to a temp file then replace, so concurrent readers
    # (bot and notifier processes) never see a partially written file
    tmp_path = Path(path).with_suffix('.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp_path, path)


def load_json(path):
    """Load data from json file.

    Args:
        `path` : path to load the json file.

    Returns:
        `data` : data from the json file.
    """
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data


def is_valid_board(board):
    """Check if the board is listed in boards.json.

    Callback data can be forged by modified clients, so a board taken
    from it must be checked before it is used in paths, URLs or messages.
    """
    boards = load_json(BOARDS_JSON_PATH)
    return any(board in page for page in boards.values())


def get_page_numbers():
    """Page numbers in boards.json, sorted; they may start at 0 or 1."""
    return sorted(int(page) for page in load_json(BOARDS_JSON_PATH))
