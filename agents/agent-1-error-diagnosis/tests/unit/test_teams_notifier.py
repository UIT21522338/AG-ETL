import importlib.util
from pathlib import Path


_module_path = Path('agents/agent-1-error-diagnosis/src/teams_notifier.py').resolve()
_spec = importlib.util.spec_from_file_location('teams_notifier', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_alert_card = _mod.build_alert_card


def _facts(card):
    return card['attachments'][0]['content']['body'][1]['facts']


def test_t01_pg_transient_retry_has_id_first(sample_pg_error):
    card = build_alert_card(
        {**sample_pg_error, 'retry_eligible': True, 'retry_count': 1, 'max_retries': 3, 'retry_status': 'TRIGGERED'},
        {'error_category': 'TRANSIENT', 'severity': 'HIGH'},
        {'severity': 'HIGH', 'root_cause': 'Network issue', 'suggested_steps': ['step1', 'step2', 'step3']},
    )
    facts = _facts(card)
    assert facts[0]['title'] == 'ID'
    assert facts[0]['value'] == '999'


def test_t02_pg_non_transient_retry_text(sample_pg_error):
    card = build_alert_card(
        {**sample_pg_error, 'retry_eligible': False},
        {'error_category': 'DATA_QUALITY', 'severity': 'MEDIUM'},
        {'severity': 'MEDIUM', 'root_cause': 'Bad data', 'suggested_steps': ['step1', 'step2', 'step3']},
    )
    facts = _facts(card)
    retry = [f for f in facts if f['title'] == 'Retry'][0]
    assert 'Khong' in retry['value']


def test_t03_bulletin_has_processor_id_first(sample_bulletin):
    card = build_alert_card(
        sample_bulletin,
        {'error_category': 'RESOURCE', 'severity': 'HIGH'},
        {'severity': 'HIGH', 'root_cause': 'OOM', 'suggested_steps': ['step1', 'step2', 'step3']},
    )
    facts = _facts(card)
    assert facts[0]['title'] == 'ID'
    assert facts[0]['value'] == 'aaaa-bbbb-cccc-dddd'


def test_t04_steps_none_uses_default(sample_pg_error):
    card = build_alert_card(
        sample_pg_error,
        {'error_category': 'UNKNOWN', 'severity': 'MEDIUM'},
        {'severity': 'MEDIUM', 'root_cause': 'unknown', 'suggested_steps': None},
    )
    steps = [f for f in _facts(card) if f['title'] == 'LLM Steps'][0]
    assert '1.' in steps['value']


def test_t05_steps_empty_uses_default(sample_pg_error):
    card = build_alert_card(
        sample_pg_error,
        {'error_category': 'UNKNOWN', 'severity': 'MEDIUM'},
        {'severity': 'MEDIUM', 'root_cause': 'unknown', 'suggested_steps': []},
    )
    steps = [f for f in _facts(card) if f['title'] == 'LLM Steps'][0]
    assert '1.' in steps['value']


def test_t06_retry_max_reached_text(sample_pg_error):
    card = build_alert_card(
        {**sample_pg_error, 'retry_status': 'MAX_REACHED', 'retry_eligible': True},
        {'error_category': 'TRANSIENT', 'severity': 'HIGH'},
        {'severity': 'HIGH', 'root_cause': 'network', 'suggested_steps': ['step1', 'step2', 'step3']},
    )
    retry = [f for f in _facts(card) if f['title'] == 'Retry'][0]
    assert 'MAX_REACHED' in retry['value']


def test_t07_error_detail_truncated_1000(sample_pg_error):
    long_error = 'x' * 2000
    card = build_alert_card(
        {**sample_pg_error, 'error_message': long_error},
        {'error_category': 'DATA_QUALITY', 'severity': 'MEDIUM'},
        {'severity': 'MEDIUM', 'root_cause': 'data issue', 'suggested_steps': ['step1', 'step2', 'step3']},
    )
    detail = [f for f in _facts(card) if f['title'] == 'Error Detail'][0]
    assert len(detail['value']) == 1000
