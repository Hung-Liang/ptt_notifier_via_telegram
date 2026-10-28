import asyncio
from datetime import time
from zoneinfo import ZoneInfo

from lib.notifier import notifier
from lib.utils.logger import remove_old_logs
from listen_bot import build_application


def get_interval_str(interval):
    return '0-59/{}'.format(interval)


timezone = ZoneInfo('Asia/Taipei')

interval = 30


async def notifier_job(context):
    # notifier blocks on network I/O; run it off the event loop so the
    # bot keeps answering commands meanwhile
    await asyncio.to_thread(notifier)


async def remove_old_logs_job(context):
    remove_old_logs()


def main():
    application = build_application(timezone)
    job_queue = application.job_queue

    # Wall-clock adjustments (e.g. NTP steps on WSL2) can delay a run past
    # the default 1s grace time, which silently skips it
    job_queue.run_custom(
        notifier_job,
        job_kwargs={
            'trigger': 'cron',
            'minute': get_interval_str(interval),
            'misfire_grace_time': 30,
        },
    )
    job_queue.run_daily(
        remove_old_logs_job, time(hour=0, minute=5, tzinfo=timezone)
    )

    remove_old_logs()
    application.run_polling()


if __name__ == '__main__':
    main()
