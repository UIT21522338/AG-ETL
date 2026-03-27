import importlib.util
from datetime import datetime, timedelta
from pathlib import Path


_module_path = Path('agents/agent-2-error-diagnosis/src/retry_policy.py').resolve()
_spec = importlib.util.spec_from_file_location('retry_policy', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
should_retry = _mod.should_retry


def _ts(minutes_ago: int) -> str:
    return (datetime.now() - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d %H:%M:%S')


def test_r01_transient_eligible():
    r = should_retry({'is_retryable': True, 'retry_count': 0, 'end_time': _ts(3)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is True


def test_r02_non_transient_not_eligible():
    r = should_retry({'is_retryable': False, 'retry_count': 0, 'end_time': _ts(3)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is False


def test_r03_reach_max_retries_not_eligible():
    r = should_retry({'is_retryable': True, 'retry_count': 3, 'end_time': _ts(3)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is False


def test_r04_outside_window_not_eligible():
    r = should_retry({'is_retryable': True, 'retry_count': 1, 'end_time': _ts(51)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is False


def test_r05_transient_count_2_still_eligible():
    r = should_retry({'is_retryable': True, 'retry_count': 2, 'end_time': _ts(10)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is True


def test_r06_is_retryable_false_not_eligible():
    r = should_retry({'is_retryable': False, 'retry_count': 0, 'end_time': _ts(2)}, {'max_retries': 3, 'max_retry_window_minutes': 50})
    assert r['eligible'] is False
