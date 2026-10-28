import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from lib.utils.file_path import LOG_PATH

LOG_RETENTION_DAYS = 30


class DailyFileHandler(logging.Handler):
    """Append each record to `LOG_PATH/YYYY-MM-DD.log`.

    The scheduler and listen_bot run as separate processes writing to the
    same files, so files are opened per record in append mode instead of
    using TimedRotatingFileHandler, whose rotation is not multi-process safe.
    """

    def emit(self, record):
        try:
            filename = self.get_filename(record.created)
            with open(Path(LOG_PATH, filename), 'a', encoding='utf-8') as f:
                f.write(self.format(record) + '\n')
        except Exception:
            self.handleError(record)

    @staticmethod
    def get_filename(timestamp):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d') + '.log'


_logger = logging.getLogger('ptt_notifier')

if not _logger.handlers:
    _formatter = logging.Formatter(
        '%(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S'
    )
    for _handler in (DailyFileHandler(), logging.StreamHandler(sys.stdout)):
        _handler.setFormatter(_formatter)
        _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log(*messages, return_filename: bool = False):
    """Basic Log to Record Progress.

    Args:
        `messages`: Logging message.
    """

    _logger.info(' '.join(str(message) for message in messages))

    if return_filename:
        return DailyFileHandler.get_filename(datetime.now().timestamp())


def remove_old_logs(days: int = LOG_RETENTION_DAYS):
    """Remove daily log files older than `days` days."""

    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Log files are named by date, so string comparison orders them by age
    for path in LOG_PATH.glob('*.log'):
        if path.stem < cutoff:
            path.unlink()
