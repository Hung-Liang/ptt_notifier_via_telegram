"""Settings read from environment variables, with defaults."""

import os

from dotenv import load_dotenv

load_dotenv()


def get_int(name, default, minimum=1, maximum=None):
    value = os.environ.get(name, '').strip()
    if not value:
        return default

    number = int(value)
    if number < minimum:
        raise ValueError(f'{name} must be at least {minimum}, got {number}')
    if maximum is not None and number > maximum:
        raise ValueError(f'{name} must be at most {maximum}, got {number}')
    return number


def get_list(name, default):
    value = os.environ.get(name, '').strip()
    if not value:
        return default
    return tuple(item.strip() for item in value.split(',') if item.strip())


def get_bool(name, default):
    value = os.environ.get(name, '').strip().lower()
    if not value:
        return default
    if value in ('1', 'true', 'yes', 'on'):
        return True
    if value in ('0', 'false', 'no', 'off'):
        return False
    raise ValueError(f'{name} must be true or false, got {value!r}')


# Minutes between notifier runs; used as a cron minute step, so values
# that don't divide 60 give uneven gaps no longer than this
NOTIFY_INTERVAL = get_int('notify_interval', 30, maximum=60)
# Search result pages fetched per board and threshold on each run
MAX_PAGE = get_int('max_page', 5)
MAX_BOARDS = get_int('max_boards', 10)
THRESHOLDS = get_list('thresholds', ('10', '20', '30', '50', '70', '100'))

# Thresholds go into PTT search URLs and callback data
if not THRESHOLDS or not all(t.isdigit() for t in THRESHOLDS):
    raise ValueError(
        f'thresholds must be comma separated numbers, got {THRESHOLDS}'
    )

# Only admin_id may use the bot; updates from anyone else are dropped
ADMIN_MODE = get_bool('admin_mode', False)

if ADMIN_MODE and not os.environ.get('admin_id', '').strip():
    raise ValueError('admin_mode requires admin_id to be set')
