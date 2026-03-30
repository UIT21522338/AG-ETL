import os
import uuid
import time
import signal
import logging
import importlib.util
import sys
from pathlib import Path
from datetime import datetime

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
  sys.path.insert(0, str(_project_root))

from shared.db.pg_client import PGClient
from shared.nifi.nifi_client import NiFiClient
from shared.utils.config_loader import load_env, load_yaml

_src_dir = Path(__file__).resolve().parent
for _module_name in [
  "classifier",
  "teams_notifier",
  "alert_dedup",
  "diagnosis_logger",
  "pg_poller",
  "nifi_poller",
  "retry_policy",
  "retry_executor",
]:
  _module_path = _src_dir / f"{_module_name}.py"
  _spec = importlib.util.spec_from_file_location(_module_name, _module_path)
  globals()[_module_name] = importlib.util.module_from_spec(_spec)
  _spec.loader.exec_module(globals()[_module_name])

classify_and_analyze = globals()['classifier'].classify_and_analyze
build_alert_card = globals()['teams_notifier'].build_alert_card
send_teams_alert = globals()['teams_notifier'].send_teams_alert
check_alert_state = globals()['alert_dedup'].check_alert_state
log_to_diagnosis_log = globals()['diagnosis_logger'].log_to_diagnosis_log
poll_pg_errors = globals()['pg_poller'].poll_pg_errors
poll_nifi_bulletins = globals()['nifi_poller'].poll_nifi_bulletins
should_retry = globals()['retry_policy'].should_retry
check_retry_state = globals()['retry_executor'].check_retry_state
trigger_nifi_luong3 = globals()['retry_executor'].trigger_nifi_luong3

logger = logging.getLogger('agent-2')


def _load_config() -> dict:
  load_env()
  env_name = os.getenv('AGENT_ENVIRONMENT', 'DEV').lower()
  config_path = _project_root / 'config' / 'environments' / f'{env_name}.yaml'
  agent2_cfg = load_yaml(str(config_path)).get('agent_2', {})
  retry_cfg = agent2_cfg.get('retry', {})
  return {
    'environment': os.getenv('AGENT_ENVIRONMENT', 'DEV'),
    'teams_webhook_url': os.getenv('TEAMS_WEBHOOK_URL'),
    'pg_schema_etl_log': agent2_cfg.get('pg_schema_etl_log', 'a_etl_monitor'),
    'pg_table_job_log': agent2_cfg.get('pg_table_job_log', 'etl_job_log'),
    'max_errors_per_run': agent2_cfg.get('max_errors_per_run', 50),
    'lookback_minutes': int(os.getenv('AGENT_LOOKBACK_MINUTES', agent2_cfg.get('lookback_minutes', 5))),
    'poll_interval': int(os.getenv('AGENT_POLL_INTERVAL', 60)),
    'retry': {
      'enabled': os.getenv('RETRY_ENABLED', str(retry_cfg.get('enabled', False))).lower() == 'true',
      'max_retries': int(os.getenv('MAX_RETRIES', retry_cfg.get('max_retries', 3))),
      'confirmed_new_failure_minutes': int(os.getenv(
        'CONFIRMED_NEW_FAILURE_MINUTES',
        retry_cfg.get('confirmed_new_failure_minutes', 2),
      )),
      'fallback_delay_minutes': int(os.getenv(
        'FALLBACK_DELAY_MINUTES',
        retry_cfg.get('fallback_delay_minutes', 5),
      )),
      'max_retry_window_minutes': int(os.getenv(
        'MAX_RETRY_WINDOW_MINUTES',
        retry_cfg.get('max_retry_window_minutes', 50),
      )),
      'nifi_luong3_processor_id': os.getenv(
        'NIFI_LUONG3_PROCESSOR_ID',
        retry_cfg.get('nifi_luong3_processor_id', ''),
      ),
    }
  }


def process_single_error(
  error: dict,
  config: dict,
  pg_client: PGClient,
  nifi_client: NiFiClient,
  dry_run: bool = False,
) -> dict:
  correlation_id = str(uuid.uuid4())
  start_ts = datetime.now()
  retry_cfg = config['retry']
  cfm = retry_cfg['confirmed_new_failure_minutes']
  fbdm = retry_cfg['fallback_delay_minutes']
  win = retry_cfg['max_retry_window_minutes']

  source_raw = error.get('source', 'pg_log')
  source = 'bulletin' if source_raw in ('bulletin', 'nifi_bulletin') else 'pg_log'
  end_time = error.get('end_time') or error.get('bulletin_ts')

  analysis = classify_and_analyze(error)
  category = analysis['sub_category']
  retry_category = analysis['retry_category']
  severity = analysis['severity']

  classification = {
    'error_category': category,
    'severity': severity,
    'classification_method': 'llm',
  }
  llm_solution = {
    'severity': severity,
    'root_cause': analysis['root_cause'],
    'suggested_steps': analysis['suggested_steps'],
  }

  retry_eligible = (
    analysis['is_retryable']
    and source == 'pg_log'
    and retry_cfg['enabled']
  )
  retry_count = 0
  retry_status = None
  trigger_result = None

  if retry_eligible and not dry_run:
    retry_check = should_retry(
      {
        'is_retryable': analysis.get('is_retryable'),
        'retry_category': retry_category,
        'retry_count': int(error.get('retry_count') or 0),
        'end_time': end_time,
      },
      retry_cfg,
    )

    if retry_check['eligible']:
      state = check_retry_state(
        pg_client,
        job_id=error.get('job_id'),
        batch_id=str(error.get('batch_id') or ''),
        error_end_time=end_time,
        confirmed_new_failure_minutes=cfm,
        fallback_delay_minutes=fbdm,
        window_minutes=win,
      )
      logger.debug(f'check_retry_state path={state["path"]} action={state["action"]} | {state["reason"]}')
      if state['action'] == 'SKIP':
        logger.info(f'RETRY SKIP | {error.get("job_name")} | {state["reason"]}')
        return {
          'correlation_id': correlation_id,
          'diagnosis_id': None,
          'error_category': category,
          'teams_sent': False,
          'retry_eligible': True,
          'retry_status': 'TRIGGERED',
        }

      trigger_result = trigger_nifi_luong3(
        nifi_client,
        processor_id=retry_cfg['nifi_luong3_processor_id'],
        batch_id=str(error.get('batch_id') or ''),
        job_group=str(error.get('job_group') or ''),
        job_id=str(error.get('job_id') or ''),
      )
      retry_count = state['retry_count'] + 1
      retry_status = 'TRIGGERED' if trigger_result['success'] else 'FAILED'
      logger.info(f'RETRY {retry_status} attempt={retry_count}/{retry_cfg["max_retries"]} | {error.get("job_name")}')
    else:
      retry_eligible = False
      retry_status = 'MAX_REACHED' if int(error.get('retry_count') or 0) >= retry_cfg['max_retries'] else None

  if source == 'bulletin':
    identifier = str(error.get('bulletin_id') or error.get('source_log_id') or '')
  else:
    identifier = f"{error.get('job_id')}_{error.get('batch_id')}"

  alert_check = check_alert_state(
    pg_client,
    source=source,
    identifier=identifier,
    error_end_time=end_time,
    confirmed_new_failure_minutes=cfm,
    fallback_delay_minutes=fbdm,
    window_minutes=win,
  )

  teams_sent = False
  if alert_check['should_alert'] and not dry_run:
    error['retry_eligible'] = retry_eligible
    error['retry_count'] = retry_count
    error['retry_status'] = retry_status
    error['max_retries'] = retry_cfg['max_retries']
    card = build_alert_card(error, classification, llm_solution)
    teams_sent = send_teams_alert(card, config['teams_webhook_url'])
    logger.info(
      f'Teams alert sent={teams_sent} | {source} | {category} | '
      f'{error.get("job_name") or error.get("processor_name")}'
    )
  elif not alert_check['should_alert']:
    logger.info(f'ALERT SKIP (dedup) | {identifier} | {alert_check["reason"]}')
    return {
      'correlation_id': correlation_id,
      'diagnosis_id': None,
      'error_category': category,
      'teams_sent': False,
      'retry_eligible': retry_eligible,
      'retry_status': retry_status,
    }
  else:
    logger.info(f'DRY RUN - would alert: {identifier} | category={category} | retry={retry_eligible}')

  if dry_run:
    return {
      'correlation_id': correlation_id,
      'diagnosis_id': None,
      'error_category': category,
      'teams_sent': False,
      'retry_eligible': retry_eligible,
      'retry_status': retry_status,
    }

  duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
  diagnosis_id = log_to_diagnosis_log(pg_client, {
    'source': source,
    'source_log_id': str(error.get('source_log_id') or identifier),
    'alert_identifier': identifier,
    'correlation_id': correlation_id,
    'tenant_code': error.get('tenant_code'),
    'job_id': error.get('job_id'),
    'job_name': error.get('job_name') or error.get('processor_name') or 'unknown',
    'batch_id': str(error['batch_id']) if error.get('batch_id') else None,
    'layer': error.get('layer'),
    'environment': error['environment'],
    'error_message_raw': error.get('error_message', ''),
    'error_category': category,
    'classification_method': classification.get('classification_method'),
    'llm_root_cause': llm_solution.get('root_cause') or llm_solution.get('root_cause_summary'),
    'llm_suggested_steps': llm_solution.get('suggested_steps'),
    'llm_severity': llm_solution.get('severity', 'MEDIUM'),
    'severity': llm_solution.get('severity', 'MEDIUM'),
    'llm_escalate': llm_solution.get('escalate_to_de_lead', False),
    'teams_alert_sent': teams_sent,
    'teams_alert_ts': datetime.now() if teams_sent else None,
    'last_alert_at': datetime.now() if teams_sent else None,
    'processing_duration_ms': duration_ms,
    'retry_eligible': retry_eligible,
    'retry_count': retry_count,
    'retry_status': retry_status,
    'last_retry_at': datetime.now() if trigger_result and trigger_result.get('success') else None,
    'retry_triggered_by': 'agent_auto' if retry_count > 0 else None,
    'parent_diagnosis_id': None,
  })

  return {
    'correlation_id': correlation_id,
    'diagnosis_id': diagnosis_id,
    'error_category': category,
    'teams_sent': teams_sent,
    'retry_eligible': retry_eligible,
    'retry_status': retry_status,
  }


def run_agent_once(dry_run: bool = False):
  config = _load_config()
  pg_client = PGClient()
  pg_client.connect()
  nifi_client = NiFiClient()
  try:
    pg_errors = poll_pg_errors(pg_client, config)
    nifi_errors = poll_nifi_bulletins(nifi_client, config, pg_client=pg_client)
    all_errors = pg_errors + nifi_errors
    logger.info(f'Errors to process: {len(all_errors)} (PG={len(pg_errors)}, NiFi={len(nifi_errors)})')
    if not all_errors:
      return
    for error in all_errors:
      try:
        process_single_error(error, config, pg_client, nifi_client, dry_run=dry_run)
      except Exception as e:
        logger.error(f'Error processing {error.get("source_log_id")}: {e}')
  finally:
    pg_client.close()


def run_health_check() -> int:
  try:
    config = _load_config()
    pg_client = PGClient()
    pg_client.connect()
    pg_client.fetchall('SELECT 1')
    pg_client.close()
    logger.info('Health check: PostgreSQL OK')

    nifi_client = NiFiClient()
    nifi_client.get_bulletins(limit=1)
    logger.info('Health check: NiFi OK')

    teams_ok = send_teams_alert({'text': 'Agent 2 health-check'}, config.get('teams_webhook_url'))
    if teams_ok:
      logger.info('Health check: Teams OK')
    else:
      logger.error('Health check: Teams FAILED')
      return 1
    return 0
  except Exception as e:
    logger.error(f'Health check FAILED: {e}')
    return 1


def run_agent_loop(dry_run: bool = False):
  config = _load_config()
  interval = config['poll_interval']
  max_rt = int(os.getenv('AGENT_MAX_RUNTIME_MINUTES', 0))
  start_wall = time.time()
  keep_running = {'value': True}

  def _stop(sig, frame):
    logger.info('Shutdown - stopping after current cycle...')
    keep_running['value'] = False

  signal.signal(signal.SIGINT, _stop)
  signal.signal(signal.SIGTERM, _stop)
  logger.info(f'Agent 2 loop started | interval={interval}s | retry={config["retry"]["enabled"]}')
  while keep_running['value']:
    if max_rt > 0 and (time.time() - start_wall) > max_rt * 60:
      logger.info(f'Max runtime {max_rt}min reached - stopping.')
      break
    t0 = time.time()
    try:
      run_agent_once(dry_run=dry_run)
    except Exception as e:
      logger.error(f'Cycle exception: {e}')
    time.sleep(max(0, interval - (time.time() - t0)))
  logger.info('Agent 2 stopped.')


if __name__ == '__main__':
  dry_run = '--dry-run' in sys.argv
  if '--health-check' in sys.argv:
    raise SystemExit(run_health_check())
  elif '--once' in sys.argv:
    run_agent_once(dry_run=dry_run)
  elif '--loop' in sys.argv:
    run_agent_loop(dry_run=dry_run)
  else:
    run_agent_once(dry_run=dry_run)
