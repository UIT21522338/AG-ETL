"""
Agent 2 - Diagnosis Logging Module
Handles persistence of error analysis results to PostgreSQL audit log.

Purpose:
  - Insert diagnosis records to agent_log.diagnosis_log for audit trail
  - Enable deduplication (check if error already analyzed)
  - Track Teams alert status and processing metrics
  - Support operational dashboards and root cause trending

Database table: agent_log.diagnosis_log
  Required fields:
    - source (pg/nifi)
    - source_log_id (job_log_id or bulletin_id)
    - correlation_id (uuid for request tracing)
    - tenant_code, job_id, job_name, batch_id, layer, environment
    - error_message_raw (full error text)
    - error_category (TRANSIENT/DATA_QUALITY/CONFIGURATION/SOURCE_UNAVAILABLE/RESOURCE)
    - classification_method (rule/llm/default)
    - llm_root_cause, llm_suggested_steps (JSON), llm_severity, llm_escalate
    - teams_alert_sent (boolean)
    - teams_alert_ts (timestamp if sent)
    - processing_duration_ms (pipeline latency)
"""

import json
from datetime import datetime
from shared.db.pg_client import PGClient
from shared.logging.logger import get_logger

logger = get_logger('agent-2.diagnosis_logger')


def log_to_diagnosis_log(pg_client: PGClient, record: dict) -> int:
    """
    Insert one error diagnosis record to agent_log.diagnosis_log.
    
    Args:
        pg_client (PGClient): Database connection
        record (dict): Complete error analysis with all required fields:
            source, source_log_id, correlation_id, tenant_code, job_id, job_name,
            batch_id, layer, environment, error_message_raw, error_category,
            classification_method,
            llm_root_cause, llm_suggested_steps, llm_severity, llm_escalate,
            teams_alert_sent, teams_alert_ts, processing_duration_ms
    
    Returns:
        int: diagnosis_id (auto-generated ID) if successful, -1 on error
    
    Note:
        - llm_suggested_steps is normalized to JSON string for JSONB column
        - Does NOT raise exceptions; returns -1 on error for graceful degradation
        - Logs errors for operational monitoring
    """
    try:
        # Normalize llm_suggested_steps to JSON string so PostgreSQL JSONB always accepts it.
        llm_steps = record.get('llm_suggested_steps')
        if llm_steps is None:
            llm_steps_json = json.dumps([], ensure_ascii=False)
        elif isinstance(llm_steps, (list, dict)):
            llm_steps_json = json.dumps(llm_steps, ensure_ascii=False)
        elif isinstance(llm_steps, str):
            stripped = llm_steps.strip()
            if not stripped:
                llm_steps_json = json.dumps([], ensure_ascii=False)
            else:
                try:
                    json.loads(stripped)
                    llm_steps_json = stripped
                except Exception:
                    llm_steps_json = json.dumps([stripped], ensure_ascii=False)
        else:
            llm_steps_json = json.dumps([str(llm_steps)], ensure_ascii=False)
        
        # Build INSERT statement
        sql = """
            INSERT INTO agent_log.diagnosis_log (
                source,
                source_log_id,
                alert_identifier,
                correlation_id,
                tenant_code,
                job_id,
                job_name,
                batch_id,
                layer,
                environment,
                error_message_raw,
                error_category,
                classification_method,
                llm_root_cause,
                llm_suggested_steps,
                llm_severity,
                severity,
                llm_escalate,
                teams_alert_sent,
                teams_alert_ts,
                last_alert_at,
                processing_duration_ms,
                retry_eligible,
                retry_count,
                retry_status,
                last_retry_at,
                retry_triggered_by,
                processed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING diagnosis_id
        """
        
        params = (
            record.get('source'),
            record.get('source_log_id'),
            record.get('alert_identifier'),
            record.get('correlation_id'),
            record.get('tenant_code'),
            record.get('job_id'),
            record.get('job_name'),
            record.get('batch_id'),
            record.get('layer'),
            record.get('environment'),
            record.get('error_message_raw'),
            record.get('error_category'),
            record.get('classification_method'),
            record.get('llm_root_cause'),
            llm_steps_json,
            record.get('llm_severity'),
            record.get('severity', record.get('llm_severity')),
            record.get('llm_escalate'),
            record.get('teams_alert_sent'),
            record.get('teams_alert_ts'),
            record.get('last_alert_at'),
            record.get('processing_duration_ms'),
            record.get('retry_eligible', False),
            record.get('retry_count', 0),
            record.get('retry_status', None),
            record.get('last_retry_at', None),
            record.get('retry_triggered_by', None),
            datetime.now(),
        )
        
        # Execute INSERT and retrieve RETURNING diagnosis_id
        diagnosis_id = pg_client.execute_returning(sql, params)

        if diagnosis_id is not None:
            logger.info(
                f'Logged diagnosis {diagnosis_id} | '
                f'{record.get("error_category")} | '
                f'{record.get("job_name")} | '
                f'corr_id={record.get("correlation_id")[:8]}'
            )
            return diagnosis_id
        else:
            logger.error('INSERT returned no RETURNING value — DB issue?')
            return -1
            
    except Exception as e:
        logger.error(
            f'Failed to log diagnosis for {record.get("job_name")}: {str(e)}',
            exc_info=True
        )
        return -1
