import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from lib.utils.file_path import LOG_PATH

LOG_RETENTION_DAYS = 30


class DailyFileHandler(logging.Handler):
    """Append each record to `LOG_PATH/YYYY-MM-DD.log`.

    Files are named by date only, unlike TimedRotatingFileHandler, so
    `remove_old_logs` can tell their age from the name.
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
        '%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S'
    )
    for _handler in (DailyFileHandler(), logging.StreamHandler(sys.stdout)):
        _handler.setFormatter(_formatter)
        _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def _join(messages):
    return ' '.join(str(message) for message in messages)


def log(*messages, return_filename: bool = False):
    """Basic Log to Record Progress.

    Args:
        `messages`: Logging message.
    """

    _logger.info(_join(messages))

    if return_filename:
        return DailyFileHandler.get_filename(datetime.now().timestamp())


def log_warning(*messages):
    """Log something unexpected that the program recovered from."""
    _logger.warning(_join(messages))


def log_error(*messages, exc_info=None):
    """Log a failure.

    Args:
        `messages`: Logging message.
        `exc_info`: Exception to attach the traceback of, or True for the
            one being handled.
    """
    _logger.error(_join(messages), exc_info=exc_info)


def remove_old_logs(days: int = LOG_RETENTION_DAYS):
    """Remove daily log files older than `days` days."""

    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Log files are named by date, so string comparison orders them by age
    for path in LOG_PATH.glob('*.log'):
        if path.stem < cutoff:
            path.unlink()
