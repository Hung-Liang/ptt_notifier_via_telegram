from datetime import datetime
from pathlib import Path

from lib.utils.file_path import LOG_PATH


def log(*messages, console: bool = False, return_filename: bool = False):
    """Basic Log to Record Progress.

    Args:
        `messages`: Logging message.
    """

    today = datetime.now().strftime('%Y-%m-%d')

    filename = today + '.log'

    file_path = Path(LOG_PATH, filename)

    with open(file_path, 'a', encoding='utf-8') as f:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), *messages, file=f)

    if console:
        print(messages)

    if return_filename:
        return filename
