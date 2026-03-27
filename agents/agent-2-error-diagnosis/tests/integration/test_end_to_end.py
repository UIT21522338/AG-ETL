from unittest.mock import MagicMock
import importlib.util
from pathlib import Path


_module_path = Path('agents/agent-2-error-diagnosis/src/agent_2_main.py').resolve()
_spec = importlib.util.spec_from_file_location('agent_2_main', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_e01_transient_should_trigger_retry_and_alert(monkeypatch):
    error = {
        'source': 'pg_log', 'source_log_id': '1', 'job_id': 3001, 'job_name': 'demo.llm_transient',
        'batch_id': '20260327210000', 'error_message': 'connection timeout', 'environment': 'DEV'
    }
    cfg = {
        'teams_webhook_url': 'https://example.invalid',
        'retry': {
            'enabled': True, 'max_retries': 3,
            'confirmed_new_failure_minutes': 2, 'fallback_delay_minutes': 5,
            'max_retry_window_minutes': 50, 'nifi_luong3_processor_id': 'pid',
        },
    }

    monkeypatch.setattr(_mod, 'classify_and_analyze', lambda _: {
        'retry_category': 'TRANSIENT', 'sub_category': 'CONNECTION_TIMEOUT', 'severity': 'HIGH',
        'root_cause': 'network issue', 'suggested_steps': ['1', '2', '3'], 'is_retryable': True,
    })
    monkeypatch.setattr(_mod, 'should_retry', lambda *_: {'eligible': True, 'reason': 'ok'})
    monkeypatch.setattr(_mod, 'check_retry_state', lambda *a, **k: {'action': 'RETRY', 'retry_count': 0, 'path': 'timestamp_based', 'reason': 'new'})
    monkeypatch.setattr(_mod, 'trigger_nifi_luong3', lambda *a, **k: {'success': True})
    monkeypatch.setattr(_mod, 'check_alert_state', lambda *a, **k: {'should_alert': True, 'reason': 'first'})
    monkeypatch.setattr(_mod, 'build_alert_card', lambda *a, **k: {'type': 'message'})
    monkeypatch.setattr(_mod, 'send_teams_alert', lambda *a, **k: True)
    monkeypatch.setattr(_mod, 'log_to_diagnosis_log', lambda *a, **k: 101)

    result = _mod.process_single_error(error, cfg, MagicMock(), MagicMock(), dry_run=False)
    assert result['diagnosis_id'] == 101
    assert result['retry_eligible'] is True


def test_e05_non_transient_should_not_retry(monkeypatch):
    error = {
        'source': 'pg_log', 'source_log_id': '2', 'job_id': 3002, 'job_name': 'demo.llm_nontransient',
        'batch_id': '20260327210001', 'error_message': 'null value violates not-null', 'environment': 'DEV'
    }
    cfg = {
        'teams_webhook_url': 'https://example.invalid',
        'retry': {
            'enabled': True, 'max_retries': 3,
            'confirmed_new_failure_minutes': 2, 'fallback_delay_minutes': 5,
            'max_retry_window_minutes': 50, 'nifi_luong3_processor_id': 'pid',
        },
    }

    monkeypatch.setattr(_mod, 'classify_and_analyze', lambda _: {
        'retry_category': 'NON_TRANSIENT', 'sub_category': 'DATA_QUALITY', 'severity': 'MEDIUM',
        'root_cause': 'bad data', 'suggested_steps': ['1', '2', '3'], 'is_retryable': False,
    })
    monkeypatch.setattr(_mod, 'check_alert_state', lambda *a, **k: {'should_alert': True, 'reason': 'first'})
    monkeypatch.setattr(_mod, 'build_alert_card', lambda *a, **k: {'type': 'message'})
    monkeypatch.setattr(_mod, 'send_teams_alert', lambda *a, **k: True)
    monkeypatch.setattr(_mod, 'log_to_diagnosis_log', lambda *a, **k: 102)

    result = _mod.process_single_error(error, cfg, MagicMock(), MagicMock(), dry_run=False)
    assert result['diagnosis_id'] == 102
    assert result['retry_eligible'] is False
