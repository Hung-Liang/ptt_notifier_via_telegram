import json
import platform
import subprocess
from pathlib import Path

from lib.utils.file_path import USER_JSON_PATH


def get_users():
    """Get users and boards from user.json file.

    Returns:
        `users` : users from user.json file.
        `boards` : boards from user.json file.
    """

    if not Path(USER_JSON_PATH).exists():
        save_json(USER_JSON_PATH, {})

    users = load_json(USER_JSON_PATH)

    return users


def save_json(path, data):
    """Save data to json file.

    Args:
        `path` : path to save the json file.
        `data` : data to save.
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


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


def run_listen_bot():
    """Run listen_bot.py as a subprocess."""
    system = platform.system()
    python = 'python3' if system == 'Linux' else 'python'
    subprocess.Popen([python, 'listen_bot.py'])


def check_if_user_exist(uid):
    """Check if the user exist in the user.json file.

    Args:
        `uid` : user id.

    Returns:
        `bool` : True if the user exist, False if not.
    """
    users = get_users()
    if str(uid) in users:
        return True
    return False


def initial_user(uid, name):
    """Initial the user in the user.json file.

    Args:
        `uid` : user id.
        `name` : user name.
    """
    users = get_users()
    users[str(uid)] = {'name': name, 'boards': {}}
    save_json(USER_JSON_PATH, users)


def add_or_update_board(uid, board, threshold):
    """Add or update the board to the user.json file.

    Args:
        `uid` : user id.
        `board` : board to add or update.
        `threshold` : threshold to add or update.
    """
    users = get_users()
    users[str(uid)]['boards'][board] = threshold
    save_json(USER_JSON_PATH, users)


def remove_board(uid, board):
    """Remove the board from the user.json file.

    Args:
        `uid` : user id.
        `board` : board to remove.
    """
    users = get_users()
    users[str(uid)]['boards'].pop(board)
    save_json(USER_JSON_PATH, users)


def check_thread_file(thread_path: Path):
    """Check if the thread file exist.

    Args:
        `thread_path` : path to the thread file.
    """

    if not thread_path.exists():
        thread_path.touch()
        save_json(thread_path, [])
