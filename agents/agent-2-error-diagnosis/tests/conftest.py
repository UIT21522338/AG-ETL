import pytest
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').resolve()))


@pytest.fixture
def sample_pg_error():
    return {
        'source': 'pg_log', 'log_id': 1, 'batch_id': '20260327210000',
        'tenant_code': 'FES', 'job_id': 999, 'job_name': 'test.bronze_sales',
        'start_time': datetime(2026, 3, 27, 21, 0, 0),
        'end_time': datetime(2026, 3, 27, 21, 5, 0),
        'status': 'failed', 'rows_read': 1000, 'rows_written': 0,
        'error_message': 'connection timeout to PostgreSQL port=5432',
        'layer': 'bronze', 'job_group': 'daily',
    }


@pytest.fixture
def sample_bulletin():
    return {
        'source': 'bulletin', 'bulletin_id': 'bull-001',
        'processor_name': 'ExecuteScript_Bronze',
        'processor_id': 'aaaa-bbbb-cccc-dddd',
        'node_address': 'nifi-node1:8443',
        'bulletin_ts': datetime(2026, 3, 27, 21, 0, 0),
        'error_message': 'java.lang.OutOfMemoryError: Java heap space',
    }
