from shared.db.pg_client import PGClient
from shared.logging.logger import get_logger

logger = get_logger('agent-2.pg_poller')


def poll_pg_errors(pg_client: PGClient, config: dict) -> list:
    """
    Poll PostgreSQL for failed jobs with time-based lookback filter.
    
    Retrieves errors that satisfy ALL 3 conditions (AND):
    1. status = 'failed'
    2. end_time within lookback window (chi loi MOI - only NEW errors)
    3. log_id NOT in agent_log.diagnosis_log (dedup - avoid re-processing)
    
    Config keys:
      pg_schema_etl_log  : str  (default: 'a_etl_monitor')
      pg_table_job_log   : str  (default: 'etl_job_log')
      max_errors_per_run : int  (default: 50)
      environment        : str  (DEV | UAT | PROD)
      lookback_minutes   : int  retrieve errors from last N minutes
                                (default: 10, use -1 to disable time filter for backfill)
    
    Returns:
      list[dict] - Normalized error records ready for classification
      
    Exception handling:
      On any DB error, logs error and returns [] — does NOT raise exception
    """
    schema   = config.get('pg_schema_etl_log',  'a_etl_monitor')
    table    = config.get('pg_table_job_log',   'etl_job_log')
    limit    = config.get('max_errors_per_run', 50)
    env      = config.get('environment',        'DEV')
    lookback = int(config.get('lookback_minutes', 10))

    try:
        # Build time filter: only include if lookback > 0
        # If lookback <= -1, filter is disabled (for manual backfill scenarios)
        time_filter = (
            f"AND end_time >= NOW() - INTERVAL '{lookback} minutes'"
            if lookback > 0 else ''
        )

        query = f'''
            SELECT log_id, batch_id, tenant_code, project_version,
                   job_id, job_name, start_time, end_time, status,
                   rows_read, rows_written, error_message,
                   job_group, layer, flow_version, from_date, to_date
            FROM {schema}.{table}
            WHERE status = 'failed'
              {time_filter}
              AND CAST(log_id AS VARCHAR) NOT IN (
                  SELECT source_log_id FROM agent_log.diagnosis_log
                  WHERE source = 'pg_log'
              )
            ORDER BY end_time DESC NULLS LAST
            LIMIT {limit}
        '''

        rows = pg_client.fetchall(query)
        logger.info(f'PG poll: {len(rows)} new errors (lookback={lookback}min, env={env})')

        result = []
        for row in rows:
            result.append({
                'source':          'pg_log',
                'source_log_id':   str(row['log_id']),
                'log_id':          row['log_id'],
                'batch_id':        str(row['batch_id']) if row.get('batch_id') else None,
                'tenant_code':     row.get('tenant_code'),
                'project_version': row.get('project_version'),
                'job_id':          row.get('job_id'),
                'job_name':        row.get('job_name') or 'unknown',
                'start_time':      str(row['start_time']) if row.get('start_time') else None,
                'end_time':        str(row['end_time']) if row.get('end_time') else None,
                'status':          'failed',
                'rows_read':       row.get('rows_read'),
                'rows_written':    row.get('rows_written'),
                'error_message':   row.get('error_message') or '',
                'job_group':       row.get('job_group'),
                'layer':           row.get('layer'),
                'flow_version':    row.get('flow_version'),
                'from_date':       str(row['from_date']) if row.get('from_date') else None,
                'to_date':         str(row['to_date']) if row.get('to_date') else None,
                'environment':     env,
            })
        return result

    except Exception as e:
        logger.error(f'poll_pg_errors failed: {e}')
        return []
