"""Container healthcheck: notifier ran recently.

The bot and the notifier share one event loop, so a fresh heartbeat also
means the bot process is alive.
"""

import sys
import time

from lib.utils.file_path import HEARTBEAT_PATH

# Notifier runs every 30 minutes; allow some slack for slow runs
MAX_HEARTBEAT_AGE = 35 * 60


def main():
    if not HEARTBEAT_PATH.exists():
        print('notifier heartbeat not found')
        return 1

    if time.time() - HEARTBEAT_PATH.stat().st_mtime > MAX_HEARTBEAT_AGE:
        print('notifier heartbeat is stale')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
