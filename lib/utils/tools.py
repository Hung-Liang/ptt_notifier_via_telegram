import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from lib.utils.file_path import BOARDS_JSON_PATH, USER_JSON_PATH
from lib.utils.logger import log

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

THRESHOLDS = ('10', '20', '30', '50', '70', '100')
MAX_BOARDS = 10


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


@contextmanager
def users_lock():
    """Hold an exclusive lock for a read-modify-write of user.json.

    The bot and notifier processes both update user.json; atomic replace
    alone still lets one overwrite the other's changes. Not reentrant.
    """
    lock_path = Path(USER_JSON_PATH).with_suffix('.lock')
    with open(lock_path, 'a+b') as f:
        if os.name == 'nt':
            # Locks the first byte; retries for ~10s then raises OSError
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def is_valid_board(board):
    """Check if the board is listed in boards.json.

    Callback data can be forged by modified clients, so a board taken
    from it must be checked before it is used in paths, URLs or messages.
    """
    boards = load_json(BOARDS_JSON_PATH)
    return any(board in page for page in boards.values())


def run_listen_bot():
    """Run listen_bot.py as a subprocess.

    Returns:
        `subprocess.Popen` : the listen_bot process.
    """
    return subprocess.Popen([sys.executable, 'listen_bot.py'])


def keep_listen_bot_alive(process):
    """Restart listen_bot.py if it has exited.

    Args:
        `process` : the listen_bot process.

    Returns:
        `subprocess.Popen` : the running listen_bot process.
    """
    if process.poll() is None:
        return process

    log('[listen_bot]', f'exited with {process.returncode}, restarting')
    return run_listen_bot()


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
    with users_lock():
        users = get_users()
        users[str(uid)] = {'name': name, 'boards': {}}
        save_json(USER_JSON_PATH, users)


def update_user_name(uid, name):
    """Update the stored name if the user changed it on Telegram.

    Args:
        `uid` : user id.
        `name` : current user name.
    """
    with users_lock():
        users = get_users()
        user = users.get(str(uid))
        if user is None or user['name'] == name:
            return
        user['name'] = name
        save_json(USER_JSON_PATH, users)


def add_or_update_board(uid, board, threshold):
    """Add or update the board to the user.json file.

    Args:
        `uid` : user id.
        `board` : board to add or update.
        `threshold` : threshold to add or update.

    Returns:
        `bool` : False if adding a new board would exceed `MAX_BOARDS`.
    """
    with users_lock():
        users = get_users()
        boards = users[str(uid)]['boards']
        if board not in boards and len(boards) >= MAX_BOARDS:
            return False
        boards[board] = threshold
        save_json(USER_JSON_PATH, users)
    return True


def remove_board(uid, board):
    """Remove the board from the user.json file.

    Args:
        `uid` : user id.
        `board` : board to remove.
    """
    with users_lock():
        users = get_users()
        # The board may already be gone if an old delete keyboard is reused
        users[str(uid)]['boards'].pop(board, None)
        save_json(USER_JSON_PATH, users)


def remove_user(uid):
    """Remove the user from the user.json file.

    Args:
        `uid` : user id.
    """
    with users_lock():
        users = get_users()
        users.pop(str(uid), None)
        save_json(USER_JSON_PATH, users)
