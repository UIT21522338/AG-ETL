from datetime import datetime, timedelta
from unittest.mock import MagicMock
import importlib.util
from pathlib import Path


_module_path = Path('agents/agent-2-error-diagnosis/src/alert_dedup.py').resolve()
_spec = importlib.util.spec_from_file_location('alert_dedup', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_alert_state = _mod.check_alert_state


def _fmt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def test_d01_first_time_should_alert():
    pg = MagicMock()
    pg.fetchall.return_value = []
    r = check_alert_state(pg, 'pg_log', '101_20260327210000', _fmt(datetime.now()))
    assert r['should_alert'] is True
    assert r['path'] == 'first_time'


def test_d02_timestamp_new_failure_should_alert():
    now = datetime.now()
    pg = MagicMock()
    pg.fetchall.return_value = [{'last_alert_at': _fmt(now - timedelta(minutes=5)), 'processed_at': None}]
    r = check_alert_state(
        pg, 'pg_log', '101_20260327210000', _fmt(now - timedelta(minutes=2)),
        confirmed_new_failure_minutes=2,
    )
    assert r['should_alert'] is True
    assert r['path'] == 'timestamp_based'


def test_d03_timestamp_duplicate_should_skip():
    now = datetime.now()
    pg = MagicMock()
    pg.fetchall.return_value = [{'last_alert_at': _fmt(now - timedelta(minutes=5)), 'processed_at': None}]
    r = check_alert_state(
        pg, 'pg_log', '101_20260327210000', _fmt(now - timedelta(minutes=4)),
        confirmed_new_failure_minutes=2,
    )
    assert r['should_alert'] is False
    assert r['path'] == 'timestamp_based'


def test_d04_fallback_elapsed_lt_delay_skip():
    now = datetime.now()
    pg = MagicMock()
    pg.fetchall.return_value = [{'last_alert_at': _fmt(now - timedelta(minutes=3)), 'processed_at': None}]
    r = check_alert_state(
        pg, 'pg_log', '101_20260327210000', None,
        fallback_delay_minutes=5,
    )
    assert r['should_alert'] is False
    assert r['path'] == 'fallback_elapsed'


def test_d05_fallback_elapsed_gte_delay_alert():
    now = datetime.now()
    pg = MagicMock()
    pg.fetchall.return_value = [{'last_alert_at': _fmt(now - timedelta(minutes=6)), 'processed_at': None}]
    r = check_alert_state(
        pg, 'pg_log', '101_20260327210000', None,
        fallback_delay_minutes=5,
    )
    assert r['should_alert'] is True
    assert r['path'] == 'fallback_elapsed'


def test_d06_db_exception_safe_default_alert():
    pg = MagicMock()
    pg.fetchall.side_effect = Exception('db broken')
    r = check_alert_state(pg, 'pg_log', '101_20260327210000', _fmt(datetime.now()))
    assert r['should_alert'] is True
    assert r['path'] == 'error'
