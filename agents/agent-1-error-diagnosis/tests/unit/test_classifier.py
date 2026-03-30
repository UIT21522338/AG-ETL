import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


_module_path = Path('agents/agent-1-error-diagnosis/src/classifier.py').resolve()
_spec = importlib.util.spec_from_file_location('classifier', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
classify_and_analyze = _mod.classify_and_analyze


@pytest.mark.parametrize('case_id,error_message,expected_retry,expected_sub', [
    ('C01', 'connection timeout to PostgreSQL', 'TRANSIENT', 'CONNECTION_TIMEOUT'),
    ('C02', 'connection reset by peer broken pipe', 'TRANSIENT', 'NETWORK_RESET'),
    ('C03', 'too many connections PostgreSQL max_connections', 'TRANSIENT', 'TOO_MANY_CONNECTIONS'),
    ('C04', 'deadlock detected on relation etl_staging', 'TRANSIENT', 'DEADLOCK'),
    ('C05', 'query timeout statement_timeout', 'TRANSIENT', 'QUERY_TIMEOUT'),
    ('C06', 'database system is starting up / recovery', 'TRANSIENT', 'DB_STARTING'),
    ('C07', 'null value in column id violates not-null', 'NON_TRANSIENT', 'DATA_QUALITY'),
    ('C08', 'numeric field overflow precision 10 scale 2', 'NON_TRANSIENT', 'DATA_QUALITY'),
    ('C09', 'duplicate key value violates unique constraint bk_hash', 'NON_TRANSIENT', 'DATA_QUALITY'),
    ('C10', 'relation bronze.NewTable does not exist', 'NON_TRANSIENT', 'CONFIGURATION'),
    ('C11', 'column updated_at does not exist', 'NON_TRANSIENT', 'CONFIGURATION'),
    ('C12', 'function etl_transform() does not exist', 'NON_TRANSIENT', 'CONFIGURATION'),
    ('C13', 'syntax error at or near SELECT', 'NON_TRANSIENT', 'CONFIGURATION'),
    ('C14', 'password authentication failed for user etl_user', 'NON_TRANSIENT', 'SOURCE_UNAVAILABLE'),
    ('C15', 'database etl_source does not exist', 'NON_TRANSIENT', 'SOURCE_UNAVAILABLE'),
    ('C16', 'java.lang.OutOfMemoryError Java heap space', 'NON_TRANSIENT', 'RESOURCE'),
    ('C17', 'no space left on device disk full', 'NON_TRANSIENT', 'RESOURCE'),
    ('C18', 'ERROR unexpected internal state XYZ-9999', 'NON_TRANSIENT', 'UNKNOWN'),
])
def test_classifier_cases_c01_to_c18(case_id, error_message, expected_retry, expected_sub):
    payload = {
        'retry_category': expected_retry,
        'sub_category': expected_sub,
        'severity': 'HIGH',
        'root_cause': f'{case_id} root cause',
        'suggested_steps': ['step1', 'step2', 'step3'],
        'confidence': 'HIGH',
    }
    mocked = MagicMock()
    mocked.chat.return_value = str(payload).replace("'", '"')

    with patch.object(_mod, '_get_llm', return_value=mocked):
        r = classify_and_analyze({'error_message': error_message, 'job_name': 'job'})

    assert r['retry_category'] == expected_retry
    assert r['sub_category'] == expected_sub


def test_c19_empty_message_fallback_without_llm_call():
    with patch.object(_mod, '_get_llm') as mocked:
        r = classify_and_analyze({'error_message': ''})
        mocked.assert_not_called()
    assert r['retry_category'] == 'NON_TRANSIENT'
    assert r['sub_category'] == 'UNKNOWN'


def test_c20_llm_fail_should_fallback():
    mocked = MagicMock()
    mocked.chat.side_effect = Exception('LLM timeout')
    with patch.object(_mod, '_get_llm', return_value=mocked):
        r = classify_and_analyze({'error_message': 'some error', 'job_name': 'test'})
    assert r['retry_category'] == 'NON_TRANSIENT'
    assert r['sub_category'] == 'UNKNOWN'
    assert r['confidence'] == 'LOW'
