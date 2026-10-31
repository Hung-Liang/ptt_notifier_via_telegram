import logging
from datetime import datetime, timedelta

from lib.utils import logger


def test_remove_old_logs_keeps_files_within_retention(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, 'LOG_PATH', tmp_path)

    def day(days_ago):
        return (datetime.now() - timedelta(days=days_ago)).strftime(
            '%Y-%m-%d'
        )

    for days_ago in (0, 30, 31, 400):
        (tmp_path / f'{day(days_ago)}.log').touch()
    (tmp_path / '.heartbeat').touch()

    logger.remove_old_logs(30)

    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        ['.heartbeat', f'{day(0)}.log', f'{day(30)}.log']
    )


def test_log_error_includes_level_and_traceback(monkeypatch):
    records = []
    handler = logging.Handler()
    handler.emit = records.append
    handler.setFormatter(logger._formatter)
    monkeypatch.setattr(logger._logger, 'handlers', [handler])

    try:
        raise ValueError('boom')
    except ValueError as e:
        logger.log_error('failed', 1, exc_info=e)

    output = handler.format(records[0])
    assert records[0].levelno == logging.ERROR
    assert 'ERROR failed 1' in output
    assert 'Traceback' in output and 'boom' in output
