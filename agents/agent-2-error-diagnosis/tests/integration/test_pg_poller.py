from unittest.mock import MagicMock
import importlib.util
from pathlib import Path


_module_path = Path('agents/agent-2-error-diagnosis/src/pg_poller.py').resolve()
_spec = importlib.util.spec_from_file_location('pg_poller', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
poll_pg_errors = _mod.poll_pg_errors


def test_pg_poller_normalizes_rows():
    pg = MagicMock()
    pg.fetchall.return_value = [
        {
            'log_id': 1, 'batch_id': 20260327210000, 'tenant_code': 'FES', 'project_version': '1.0.0',
            'job_id': 3001, 'job_name': 'demo.llm_transient', 'start_time': '2026-03-27 21:00:00',
            'end_time': '2026-03-27 21:01:00', 'status': 'failed', 'rows_read': 100, 'rows_written': 0,
            'error_message': 'connection timeout', 'job_group': 'daily', 'layer': 'bronze',
            'flow_version': '1.0.0', 'from_date': None, 'to_date': None,
        }
    ]

    cfg = {
        'pg_schema_etl_log': 'a_etl_monitor',
        'pg_table_job_log': 'etl_job_log',
        'max_errors_per_run': 50,
        'lookback_minutes': 5,
        'environment': 'DEV',
    }

    rows = poll_pg_errors(pg, cfg)
    assert len(rows) == 1
    assert rows[0]['source'] == 'pg_log'
    assert rows[0]['source_log_id'] == '1'
    assert rows[0]['job_id'] == 3001
