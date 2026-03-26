from shared.nifi.nifi_client import NiFiClient
from shared.db.pg_client import PGClient
from shared.logging.logger import get_logger

logger = get_logger('agent-2.nifi_poller')


def _get_processed_bulletin_ids(pg_client: PGClient) -> set:
  # Query agent_log.diagnosis_log lay tat ca bulletin_id da xu ly
  # Dam bao dedup qua DB — khong mat khi agent restart
  try:
    rows = pg_client.fetchall(
      "SELECT source_log_id FROM agent_log.diagnosis_log"
      " WHERE source = 'nifi_bulletin'"
    )
    ids = {r['source_log_id'] for r in rows}
    logger.debug(f'Loaded {len(ids)} processed bulletin ids from diagnosis_log')
    return ids
  except Exception as e:
    logger.warning(f'Could not fetch processed bulletin ids from DB: {e} — fallback to empty set')
    return set()


def poll_nifi_bulletins(
  nifi_client: NiFiClient,
  config: dict,
  pg_client: PGClient = None,
  processed_ids: set = None,
) -> list:
  # Lay NiFi bulletins muc ERROR hoac WARNING chua duoc xu ly.
  #
  # Dedup theo thu tu uu tien:
  #   1. pg_client truyen vao -> query agent_log.diagnosis_log (CHINH)
  #   2. processed_ids truyen vao -> in-memory fallback (chi dung khi khong co pg_client)
  #   3. Khong co gi -> khong dedup (tranh dung che do nay trong prod)
  env = config.get('environment', 'DEV')
  try:
    bulletins = nifi_client.get_bulletins(limit=200)

    # Xac dinh tap bulletin_id da xu ly
    if pg_client is not None:
      # Uu tien: dedup qua DB -> an toan khi agent restart
      done_ids = _get_processed_bulletin_ids(pg_client)
    elif processed_ids is not None:
      # Fallback: in-memory (chi dung khi test, khong dung trong prod)
      done_ids = processed_ids
      logger.warning('NiFi poller dang dung in-memory dedup — neu agent restart se bao lai loi cu')
    else:
      done_ids = set()
      logger.warning('NiFi poller khong co dedup — moi bulletin deu duoc xu ly lai')

    result = []
    for b in bulletins:
      # NiFi API tra ve {'bulletin': {...}} hoac truc tiep {...}
      bulletin = b.get('bulletin', b)
      level = bulletin.get('level', '')
      if level not in ('ERROR', 'WARNING'):
        continue
      bid = str(bulletin.get('id', ''))
      if bid in done_ids:
        continue
      result.append({
        'source':          'nifi_bulletin',
        'source_log_id':   bid,
        'log_id':          None,
        'batch_id':        None,
        'tenant_code':     None,
        'project_version': None,
        'job_id':          None,
        'job_name':        bulletin.get('sourceName') or bulletin.get('sourceId', 'NiFi'),
        'start_time':      None,
        'end_time':        bulletin.get('timestamp'),
        'status':          'failed',
        'rows_read':       None,
        'rows_written':    None,
        'error_message':   bulletin.get('message', ''),
        'job_group':       None,
        'layer':           None,
        'flow_version':    None,
        'from_date':       None,
        'to_date':         None,
        'environment':     env,
      })

    logger.info(f'NiFi poll: {len(result)} new bulletins (dedup={"DB" if pg_client else "memory"})')
    return result

  except Exception as e:
    logger.error(f'poll_nifi_bulletins failed: {e}')
    return []
