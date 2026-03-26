"""
Agent 2 - Error Diagnosis with Automatic Polling Loop
Main orchestrator for capturing, analyzing, and alerting on ETL pipeline errors

Entry points:
  Run once: python agents/agent-2-error-diagnosis/src/agent_2_main.py
  Loop mode: python agents/agent-2-error-diagnosis/src/agent_2_main.py --loop
  Dry-run: python agents/agent-2-error-diagnosis/src/agent_2_main.py --dry-run
  Interval override: set AGENT_POLL_INTERVAL=60 then run with --loop

Configuration:
  - Loads from: config/environments/{AGENT_ENVIRONMENT}.yaml (DEV/UAT/PROD)
  - Env overrides: AGENT_LOOKBACK_MINUTES, AGENT_POLL_INTERVAL, TEAMS_WEBHOOK_URL
  
Time-based filtering:
  - Lookback window prevents re-processing old errors
  - DEV: 5-10 min window (for testing)
  - UAT/PROD: 10+ min window (for production safety)
  - Set AGENT_LOOKBACK_MINUTES=-1 to disable (backfill mode)

Database deduplication:
  - PRIMARY: agent_log.diagnosis_log table (persists across restarts)
  - Prevents duplicate Teams alerts and redundant LLM analysis
  
Graceful shutdown:
  - Loop mode responds to SIGINT (Ctrl+C) and SIGTERM
  - Completes current cycle before exiting
"""

import os
import sys
import uuid
import time
import signal
import logging
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add project root to sys.path to enable imports
_project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_project_root))

from shared.db.pg_client import PGClient
from shared.nifi.nifi_client import NiFiClient
from shared.utils.config_loader import load_env, load_yaml

# Import agent-2 modules using importlib (avoids hyphen issue)
_src_dir = Path(__file__).resolve().parent
for _module_name in ["classifier", "llm_analyzer", "teams_notifier", "diagnosis_logger", "pg_poller", "nifi_poller"]:
    _module_path = _src_dir / f"{_module_name}.py"
    _spec = importlib.util.spec_from_file_location(_module_name, _module_path)
    globals()[_module_name] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(globals()[_module_name])

# Import functions from loaded modules
classify_error = classifier.classify_error
get_llm_solution = llm_analyzer.get_llm_solution
build_teams_message = teams_notifier.build_teams_message
send_teams_alert = teams_notifier.send_teams_alert
log_to_diagnosis_log = diagnosis_logger.log_to_diagnosis_log
poll_pg_errors = pg_poller.poll_pg_errors
poll_nifi_bulletins = nifi_poller.poll_nifi_bulletins

logger = logging.getLogger('agent-2')


def _load_config() -> dict:
    """
    Load configuration from YAML + environment overrides.
    
    Priority hierarchy:
      1. Environment variables (highest priority)
      2. config/environments/{AGENT_ENVIRONMENT}.yaml
      3. Hardcoded defaults (lowest priority)
    
    Key config values:
      - lookback_minutes: Time window for polling (default 10 min)
        * Use -1 to disable time filter (manual backfill mode)
      - poll_interval: Seconds between polling cycles (default 60s)
        * Rule: lookback_minutes >= 2 * (poll_interval / 60)
        * Example: poll_interval=60s -> lookback >= 2 min (recommend 10 min)
    """
    load_env()
    
    # Calculate path from src/agent_2_main.py -> project root
    # src/agent_2_main.py -> agent-2-error-diagnosis/ -> agents/ -> project root
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[3]  # Go up to project root
    
    env_name    = os.getenv('AGENT_ENVIRONMENT', 'DEV').lower()
    config_path = project_root / 'config' / 'environments' / f'{env_name}.yaml'
    
    agent2_cfg  = load_yaml(str(config_path)).get('agent_2', {})
    
    return {
        'environment':        os.getenv('AGENT_ENVIRONMENT', 'DEV'),
        'teams_webhook_url':  os.getenv('TEAMS_WEBHOOK_URL'),
        'pg_schema_etl_log':  agent2_cfg.get('pg_schema_etl_log',  'a_etl_monitor'),
        'pg_table_job_log':   agent2_cfg.get('pg_table_job_log',   'etl_job_log'),
        'max_errors_per_run': agent2_cfg.get('max_errors_per_run', 50),
        # Lookback window: Priority env var > yaml config > default 10 min
        # Rule: lookback_minutes >= POLL_INTERVAL_seconds/60 x 2
        # Example: Poll every 60s = min 2 min window, recommend 10 min for safety
        'lookback_minutes':   int(os.getenv('AGENT_LOOKBACK_MINUTES',
                                  agent2_cfg.get('lookback_minutes', 10))),
        'poll_interval':      int(os.getenv('AGENT_POLL_INTERVAL', 60)),
    }


def process_single_error(error: dict, config: dict, pg_client: PGClient) -> dict:
    """
    End-to-end pipeline for a single error: classify → analyze → alert → log.
    
    Steps:
      1. Classify error using keyword matching (fast, deterministic)
      2. Send to LLM for root cause analysis (DeepSeek)
      3. Build Teams message with classification+LLM diagnostics
      4. Send Teams alert (if webhook configured)
      5. Log diagnosis result to agent_log.diagnosis_log (for dedup+audit)
    
    Returns:
      dict with correlation_id, diagnosis_id, error_category, teams_sent status
    """
    correlation_id = str(uuid.uuid4())
    start_ts = datetime.now(timezone.utc)
    
    classification = classify_error(error['error_message'])
    llm_solution   = get_llm_solution({**error, **classification})
    msg            = build_teams_message(error, classification, llm_solution)
    teams_sent     = send_teams_alert(msg, config['teams_webhook_url'])
    
    duration_ms    = int((datetime.now(timezone.utc) - start_ts).total_seconds() * 1000)
    
    diagnosis_id   = log_to_diagnosis_log(pg_client, {
        'source':                 error['source'],
        'source_log_id':          str(error['source_log_id']),
        'correlation_id':         correlation_id,
        'tenant_code':            error.get('tenant_code'),
        'job_id':                 error.get('job_id'),
        'job_name':               error.get('job_name', 'unknown'),
        'batch_id':               str(error['batch_id']) if error.get('batch_id') else None,
        'layer':                  error.get('layer'),
        'environment':            error['environment'],
        'error_message_raw':      error['error_message'],
        'error_category':         classification['error_category'],
        'matched_keyword':        classification['matched_keyword'],
        'classification_method':  classification['classification_method'],
        'llm_root_cause':         llm_solution.get('root_cause_summary'),
        'llm_suggested_steps':    llm_solution.get('suggested_steps'),
        'llm_severity':           llm_solution.get('severity'),
        'llm_escalate':           llm_solution.get('escalate_to_de_lead', False),
        'teams_alert_sent':       teams_sent,
        'teams_alert_ts':         datetime.now(timezone.utc) if teams_sent else None,
        'processing_duration_ms': duration_ms,
    })
    
    logger.info(
        f'[{correlation_id[:8]}] {classification["error_category"]} | '
        f'{error.get("job_name")} | severity={llm_solution.get("severity")} | '
        f'teams={teams_sent} | diag_id={diagnosis_id}'
    )
    
    return {
        'correlation_id': correlation_id,
        'diagnosis_id': diagnosis_id,
        'error_category': classification['error_category'],
        'teams_sent': teams_sent
    }


def run_agent_once(dry_run: bool = False):
    """
    Execute one complete polling cycle:
      1. Poll PostgreSQL for failed jobs (with lookback filter)
      2. Poll NiFi for error/warning bulletins (with DB dedup)
      3. Process each error: classify → analyze → alert
    
    Args:
      dry_run (bool): If True, log actions without writing to Teams or DB
    """
    config     = _load_config()
    pg_client  = PGClient()
    pg_client.connect()
    
    nifi_client = NiFiClient()
    
    try:
        # Poll errors from both PostgreSQL and NiFi
        pg_errors   = poll_pg_errors(pg_client, config)
        
        # NiFi poller uses DB-based dedup (pg_client) instead of in-memory
        nifi_errors = poll_nifi_bulletins(nifi_client, config, pg_client=pg_client)
        
        all_errors  = pg_errors + nifi_errors
        logger.info(f'Errors to process: {len(all_errors)} (PG={len(pg_errors)}, NiFi={len(nifi_errors)})')
        
        if not all_errors:
            return
        
        for error in all_errors:
            try:
                if dry_run:
                    logger.info(f'DRY RUN — skip: {error["job_name"]} | {error["error_message"][:80]}')
                else:
                    process_single_error(error, config, pg_client)
            except Exception as e:
                logger.error(f'Error processing {error.get("source_log_id")}: {e}')
    finally:
        pg_client.close()


def run_agent_loop(dry_run: bool = False):
    """
    Start infinite polling loop with configurable interval.
    
    Behavior:
      - Polls at intervals specified by config['poll_interval'] seconds
      - Responds to SIGINT (Ctrl+C) and SIGTERM for graceful shutdown
      - Completes current cycle before exiting on signal
      - Logs lifecycle events (start/stop)
    
    Args:
      dry_run (bool): If True, simulate alert processing without side effects
    """
    config = _load_config()
    interval = config['poll_interval']
    
    keep_running = {'value': True}
    
    def _stop(sig, frame):
        logger.info('Shutdown signal — stopping after current cycle...')
        keep_running['value'] = False
    
    signal.signal(signal.SIGINT,  _stop)
    signal.signal(signal.SIGTERM, _stop)
    
    logger.info(f'Agent 2 loop started — interval={interval}s, lookback={config["lookback_minutes"]}min')
    
    while keep_running['value']:
        t0 = time.time()
        try:
            run_agent_once(dry_run=dry_run)
        except Exception as e:
            logger.error(f'Cycle exception: {e}')
        
        sleep_time = max(0, interval - (time.time() - t0))
        time.sleep(sleep_time)
    
    logger.info('Agent 2 stopped.')


if __name__ == '__main__':
    import sys
    dry_run = '--dry-run' in sys.argv
    if '--loop' in sys.argv:
        run_agent_loop(dry_run=dry_run)
    else:
        run_agent_once(dry_run=dry_run)
