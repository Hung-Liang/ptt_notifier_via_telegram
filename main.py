from lib.notifier import notifier
from lib.utils.logger import remove_old_logs
from lib.utils.tools import keep_listen_bot_alive, run_listen_bot


import pytz
from apscheduler.schedulers.blocking import BlockingScheduler


def get_interval_str(interval):
    return '0-59/{}'.format(interval)


timezone = pytz.timezone('Asia/Taipei')

scheduler = BlockingScheduler(timezone=timezone)

interval = 30
scheduler.add_job(
    notifier,
    'cron',
    minute=get_interval_str(interval),
)

scheduler.add_job(remove_old_logs, 'cron', hour=0, minute=5)


def check_listen_bot():
    global listen_bot
    listen_bot = keep_listen_bot_alive(listen_bot)


# Wall-clock adjustments (e.g. NTP steps on WSL2) can delay a run past the
# default 1s grace time, which silently skips it
scheduler.add_job(
    check_listen_bot, 'interval', minutes=1, misfire_grace_time=30
)

remove_old_logs()
listen_bot = run_listen_bot()
scheduler.start()
