import pytest

from lib.utils import config


def test_get_int_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv('test_value', raising=False)

    assert config.get_int('test_value', 30) == 30


def test_get_int_reads_env(monkeypatch):
    monkeypatch.setenv('test_value', ' 15 ')

    assert config.get_int('test_value', 30, maximum=60) == 15


@pytest.mark.parametrize('value', ['0', '61', 'abc'])
def test_get_int_rejects_invalid(monkeypatch, value):
    monkeypatch.setenv('test_value', value)

    with pytest.raises(ValueError):
        config.get_int('test_value', 30, maximum=60)


def test_get_list_splits_and_strips(monkeypatch):
    monkeypatch.setenv('test_value', '10, 20,,30 ')

    assert config.get_list('test_value', ()) == ('10', '20', '30')


def test_get_list_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv('test_value', raising=False)

    assert config.get_list('test_value', ('1',)) == ('1',)


@pytest.mark.parametrize(
    'value, expected', [('true', True), (' ON ', True), ('0', False)]
)
def test_get_bool_reads_env(monkeypatch, value, expected):
    monkeypatch.setenv('test_value', value)

    assert config.get_bool('test_value', not expected) is expected


def test_get_bool_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv('test_value', raising=False)

    assert config.get_bool('test_value', True) is True


def test_get_bool_rejects_invalid(monkeypatch):
    monkeypatch.setenv('test_value', 'maybe')

    with pytest.raises(ValueError):
        config.get_bool('test_value', False)
