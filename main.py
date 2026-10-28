from lib.notifier import notifier
from lib.utils.tools import run_listen_bot


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

run_listen_bot()
scheduler.start()
