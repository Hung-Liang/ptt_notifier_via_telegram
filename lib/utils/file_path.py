import os
from pathlib import Path

PROGRAM_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

ASSET_PATH = Path(PROGRAM_PATH, 'assets')
BOARDS_PATH = Path(ASSET_PATH, 'boards')
LOG_PATH = Path(PROGRAM_PATH, 'logs')

USER_JSON_PATH = Path(ASSET_PATH, 'user.json')
BOARDS_JSON_PATH = Path(ASSET_PATH, 'boards.json')
USERS_FOLDER_PATH = Path(ASSET_PATH, 'users')

ASSET_PATH.mkdir(exist_ok=True)
BOARDS_PATH.mkdir(exist_ok=True)
LOG_PATH.mkdir(exist_ok=True)
