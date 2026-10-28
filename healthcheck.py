"""Container healthcheck: notifier ran recently and listen_bot is alive."""

import sys
import time
from pathlib import Path

from lib.utils.file_path import HEARTBEAT_PATH

# Notifier runs every 30 minutes; allow some slack for slow runs
MAX_HEARTBEAT_AGE = 35 * 60


def is_listen_bot_running():
    for cmdline in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = cmdline.read_bytes().split(b'\0')
        except OSError:
            # Process exited between glob and read
            continue
        if b'listen_bot.py' in args:
            return True
    return False


def main():
    if not HEARTBEAT_PATH.exists():
        print('notifier heartbeat not found')
        return 1

    if time.time() - HEARTBEAT_PATH.stat().st_mtime > MAX_HEARTBEAT_AGE:
        print('notifier heartbeat is stale')
        return 1

    if not is_listen_bot_running():
        print('listen_bot is not running')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
