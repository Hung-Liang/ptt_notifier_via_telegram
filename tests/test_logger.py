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
