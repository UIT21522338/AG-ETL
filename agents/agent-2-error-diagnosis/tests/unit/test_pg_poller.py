"""
Test suite for pg_poller.py - PostgreSQL error polling with time filter.

Tests cover:
- Time filter logic (present when lookback > 0, absent when <= -1)
- Database deduplication always active
- Exception handling (returns [])
- Output schema validation
- NULL handling in error messages
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import sys
from pathlib import Path
import os

# Setup path for imports
current_file = Path(__file__).resolve()
# test file at: agents/agent-2-error-diagnosis/tests/unit/test_pg_poller.py
# parents[0] = unit, parents[1] = tests, parents[2] = agent-2-error-diagnosis
# parents[3] = agents, parents[4] = project_root
project_root = current_file.parents[4]
src_path = project_root / "agents" / "agent-2-error-diagnosis" / "src"

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

# Mock pg_client module before importing agent_2 modules
sys.modules['shared'] = MagicMock()
sys.modules['shared.db'] = MagicMock()
sys.modules['shared.db.pg_client'] = MagicMock()
sys.modules['shared.logging'] = MagicMock()
sys.modules['shared.logging.logger'] = MagicMock()

# Now we can safely import pg_poller
import importlib.util
pg_poller_path = src_path / "pg_poller.py"
spec = importlib.util.spec_from_file_location("pg_poller", str(pg_poller_path))
pg_poller = importlib.util.module_from_spec(spec)

# Define mock get_logger before loading the module
def mock_get_logger(name):
    return MagicMock()

sys.modules['shared.logging.logger'].get_logger = mock_get_logger

# Now load the module
spec.loader.exec_module(pg_poller)
poll_pg_errors = pg_poller.poll_pg_errors


class TestPgPollerTimeFilter:
    """Test time filter logic in pg_poller"""
    
    def test_time_filter_included_when_lookback_positive(self):
        """Verify SQL includes time filter when lookback_minutes > 0"""
        config = {
            "lookback_minutes": 5,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = []
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        # Verify fetchall was called
        assert mock_pg_client.fetchall.called
        sql = mock_pg_client.fetchall.call_args[0][0]
        
        # Verify time filter is in SQL (5 minute lookback)
        assert "NOW() - INTERVAL '5 minutes'" in sql
        assert "AND end_time >=" in sql
    
    def test_time_filter_excluded_when_lookback_negative(self):
        """Verify SQL excludes time filter when lookback_minutes = -1"""
        config = {
            "lookback_minutes": -1,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = []
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        # Verify fetchall was called
        assert mock_pg_client.fetchall.called
        sql = mock_pg_client.fetchall.call_args[0][0]
        
        # Verify time filter is NOT in SQL (backfill mode)
        assert "NOW() - INTERVAL" not in sql
    
    def test_dedup_clause_always_present(self):
        """Verify deduplication logic always included regardless of lookback"""
        for lookback in [5, -1, 0]:
            config = {
                "lookback_minutes": lookback,
                "pg_schema_etl_log": "a_etl_monitor",
                "pg_table_job_log": "etl_job_log",
                "max_errors_per_run": 50
            }
            
            mock_pg_client = MagicMock()
            mock_pg_client.fetchall.return_value = []
            
            with patch('pg_poller.logger'):
                result = poll_pg_errors(mock_pg_client, config)
            
            sql = mock_pg_client.fetchall.call_args[0][0]
            
            # Dedup check should always be present
            assert "agent_log.diagnosis_log" in sql
            assert "NOT IN" in sql


class TestPgPollerExceptionHandling:
    """Test exception handling and edge cases"""
    
    def test_db_connection_error_returns_empty_list(self):
        """Verify function returns [] when database connection fails"""
        config = {
            "lookback_minutes": 5,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.side_effect = Exception("Connection refused")
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_missing_config_keys_uses_defaults(self):
        """Verify function handles missing optional config keys"""
        config = {
            "lookback_minutes": 5,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log"
            # Missing: max_errors_per_run
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = []
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        assert isinstance(result, list)


class TestPgPollerOutputSchema:
    """Test output data structure validation"""
    
    def test_output_matches_expected_schema(self):
        """Verify poll_pg_errors returns properly formatted error records"""
        config = {
            "lookback_minutes": 5,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        # Mock database response with realistic error record
        mock_row = {
            "log_id": 1,
            "batch_id": "batch_123",
            "tenant_code": "tenant_1",
            "project_version": "1.0",
            "job_id": 1,
            "job_name": "failed_etl_job",
            "status": "failed",
            "start_time": datetime(2024, 1, 15, 10, 30, 0),
            "end_time": datetime(2024, 1, 15, 10, 35, 0),
            "rows_read": 1000,
            "rows_written": 500,
            "error_message": "Connection timeout",
            "job_group": "group_1",
            "layer": "bronze",
            "flow_version": "1.0",
            "from_date": None,
            "to_date": None
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = [mock_row]
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        assert len(result) == 1
        record = result[0]
        
        # Verify record contains expected fields
        assert "job_id" in record
        assert "job_name" in record
        assert "status" in record
        assert record["status"] == "failed"
        assert record["job_name"] == "failed_etl_job"
    
    def test_null_error_message_handled(self):
        """Verify NULL error_message values are handled gracefully"""
        config = {
            "lookback_minutes": 5,
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        # Mock database response with NULL error_message
        mock_row = {
            "log_id": 2,
            "batch_id": "batch_456",
            "tenant_code": "tenant_1",
            "project_version": "1.0",
            "job_id": 2,
            "job_name": "another_job",
            "status": "failed",
            "start_time": datetime(2024, 1, 15, 11, 0, 0),
            "end_time": datetime(2024, 1, 15, 11, 5, 0),
            "rows_read": 500,
            "rows_written": 250,
            "error_message": None,
            "job_group": "group_2",
            "layer": "silver",
            "flow_version": "1.0",
            "from_date": None,
            "to_date": None
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = [mock_row]
        
        with patch('pg_poller.logger'):
            result = poll_pg_errors(mock_pg_client, config)
        
        # Should not crash; result should contain the record
        assert len(result) == 1
        # NULL error_message should be converted to empty string
        assert result[0]["error_message"] == ""


class TestPgPollerDefaultLookback:
    """Test default lookback_minutes behavior"""
    
    def test_default_lookback_when_not_specified(self):
        """Verify default lookback_minutes=10 used when config key missing"""
        config = {
            # lookback_minutes not specified
            "pg_schema_etl_log": "a_etl_monitor",
            "pg_table_job_log": "etl_job_log",
            "max_errors_per_run": 50
        }
        
        mock_pg_client = MagicMock()
        mock_pg_client.fetchall.return_value = []
        
        with patch('pg_poller.logger'):
            poll_pg_errors(mock_pg_client, config)
        
        # Verify fetchall was called
        assert mock_pg_client.fetchall.called
        sql = mock_pg_client.fetchall.call_args[0][0]
        
        # Should use default 10-minute filter when not specified
        assert "NOW() - INTERVAL '10 minutes'" in sql
        assert isinstance(sql, str)
