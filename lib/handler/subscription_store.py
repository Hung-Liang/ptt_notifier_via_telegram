import threading
from enum import Enum, auto
from pathlib import Path

from lib.utils.config import MAX_BOARDS
from lib.utils.file_path import USER_JSON_PATH
from lib.utils.tools import load_json, save_json


class Outcome(Enum):
    DONE = auto()
    BOARD_LIMIT = auto()
    NOT_SUBSCRIBED = auto()
    NOT_REGISTERED = auto()


class SubscriptionStore:
    """Registered users, their names and Subscriptions (board -> threshold).

    Every operation handles an unregistered uid itself, so callers never
    check existence first; uids may be int or str.
    """

    def __init__(self, path=USER_JSON_PATH, max_boards=MAX_BOARDS):
        self._path = Path(path)
        self._max_boards = max_boards
        # Hold for a read-modify-write of user.json. The bot handlers and the
        # notifier thread both update it; atomic replace alone still lets one
        # overwrite the other's changes. Not reentrant. Per instance, so the
        # bot and notifier must share one store.
        self._lock = threading.Lock()

    def _load(self):
        # Caller holds the lock
        if not self._path.exists():
            save_json(self._path, {})
        return load_json(self._path)

    def register(self, uid, name):
        """Register the user; if already registered, refresh the name.

        Returns:
            `bool`: True if the user was newly registered.
        """
        with self._lock:
            users = self._load()
            user = users.get(str(uid))
            if user is not None:
                if user['name'] == name:
                    return False
                user['name'] = name
                save_json(self._path, users)
                return False
            users[str(uid)] = {'name': name, 'boards': {}}
            save_json(self._path, users)
        return True

    def refresh_name(self, uid, name):
        """Update the stored name if the user changed it on Telegram."""
        with self._lock:
            users = self._load()
            user = users.get(str(uid))
            if user is None or user['name'] == name:
                return
            user['name'] = name
            save_json(self._path, users)

    def boards_of(self, uid):
        """The user's board -> threshold mapping, or None if unregistered."""
        with self._lock:
            user = self._load().get(str(uid))
        return None if user is None else user['boards']

    def subscribe(self, uid, board, threshold):
        """Add the board, or update its threshold if already subscribed.

        A new board is refused with BOARD_LIMIT once `max_boards` is reached.
        """
        with self._lock:
            users = self._load()
            user = users.get(str(uid))
            if user is None:
                return Outcome.NOT_REGISTERED
            boards = user['boards']
            if board not in boards and len(boards) >= self._max_boards:
                return Outcome.BOARD_LIMIT
            boards[board] = threshold
            save_json(self._path, users)
        return Outcome.DONE

    def unsubscribe(self, uid, board):
        with self._lock:
            users = self._load()
            user = users.get(str(uid))
            if user is None:
                return Outcome.NOT_REGISTERED
            # The board may already be gone if an old delete keyboard is reused
            if board not in user['boards']:
                return Outcome.NOT_SUBSCRIBED
            del user['boards'][board]
            save_json(self._path, users)
        return Outcome.DONE

    def remove(self, uid):
        """Remove the user.

        Returns:
            `bool`: False if the user was not registered.
        """
        with self._lock:
            users = self._load()
            if users.pop(str(uid), None) is None:
                return False
            save_json(self._path, users)
        return True

    def users(self):
        """Snapshot of every user: uid -> {'name', 'boards'}."""
        with self._lock:
            return self._load()


STORE = SubscriptionStore()
