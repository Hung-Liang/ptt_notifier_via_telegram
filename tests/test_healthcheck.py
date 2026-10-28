import os
import time

import pytest

import healthcheck


@pytest.fixture
def heartbeat(monkeypatch, tmp_path):
    path = tmp_path / '.heartbeat'
    monkeypatch.setattr(healthcheck, 'HEARTBEAT_PATH', path)
    monkeypatch.setattr(healthcheck, 'is_listen_bot_running', lambda: True)
    return path


def test_healthy(heartbeat):
    heartbeat.touch()

    assert healthcheck.main() == 0


def test_missing_heartbeat(heartbeat):
    assert healthcheck.main() == 1


def test_stale_heartbeat(heartbeat):
    heartbeat.touch()
    old = time.time() - healthcheck.MAX_HEARTBEAT_AGE - 60
    os.utime(heartbeat, (old, old))

    assert healthcheck.main() == 1


def test_listen_bot_not_running(monkeypatch, heartbeat):
    heartbeat.touch()
    monkeypatch.setattr(healthcheck, 'is_listen_bot_running', lambda: False)

    assert healthcheck.main() == 1
