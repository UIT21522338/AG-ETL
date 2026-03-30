from datetime import datetime, timedelta
from shared.db.pg_client import PGClient
from shared.logging.logger import get_logger

logger = get_logger('agent-2.alert_dedup')


def _parse_ts(val):
    """Parse DB timestamp (naive, VN time) without adding timezone info.
    
    DB stores naive datetime in VN timezone.
    This function parses to naive datetime without modifying.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)  # Remove any tzinfo, keep naive
    try:
        s = str(val)[:19].replace('T', ' ')
        return datetime.fromisoformat(s)
    except Exception:
        return None


def check_alert_state(
    pg_client: PGClient,
    source: str,
    identifier: str,
    error_end_time: str,
    confirmed_new_failure_minutes: int = 2,
    fallback_delay_minutes: int = 5,
    window_minutes: int = 50,
    cfm: int = None,
    fbdm: int = None,
) -> dict:
    '''
    Kiem tra xem co nen gui Teams alert cho loi nay khong.

    source     : 'bulletin' | 'pg_log'
    identifier : bulletin_id (bulletin) hoac '{job_id}_{batch_id}' (pg_log)
    error_end_time: end_time hoac bulletin_ts cua loi hien tai

    confirmed_new_failure_minutes:
      Nguong so sanh: end_time > last_alert_at + N -> loi MOI -> gui alert
      Dat bang thoi gian job chay nhanh nhat + 1 buffer.

    fallback_delay_minutes:
      Dung khi timestamp NULL/parse loi.
      elapsed >= N -> cho phep gui alert.

    Return:
      should_alert : bool
      reason       : str
      path         : timestamp_based | fallback_elapsed | first_time | status_based
    '''
    if cfm is not None:
        confirmed_new_failure_minutes = cfm
    if fbdm is not None:
        fallback_delay_minutes = fbdm

    try:
        rows = pg_client.fetchall(
            f'''
            SELECT teams_alert_sent, last_alert_at, processed_at
            FROM agent_log.diagnosis_log
            WHERE alert_identifier = %s
              AND source           = %s
              AND teams_alert_sent = TRUE
              AND processed_at    >= NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh' - INTERVAL '{window_minutes} minutes'
            ORDER BY diagnosis_id DESC LIMIT 1
            ''',
            (str(identifier), source)
        )
        if not rows:
            return {'should_alert': True, 'reason': 'first alert for this identifier', 'path': 'first_time'}

        row = rows[0]
        last_alert_at = _parse_ts(row.get('last_alert_at') or row.get('processed_at'))
        current_ts = _parse_ts(error_end_time)

        if last_alert_at and current_ts:
            threshold = last_alert_at + timedelta(minutes=confirmed_new_failure_minutes)
            if current_ts > threshold:
                return {
                    'should_alert': True,
                    'reason': f'[timestamp] new failure: error_end={current_ts.strftime("%H:%M:%S")} > last_alert({last_alert_at.strftime("%H:%M:%S")})+{confirmed_new_failure_minutes}min',
                    'path': 'timestamp_based',
                }
            return {
                'should_alert': False,
                'reason': f'[timestamp] duplicate: error_end={current_ts.strftime("%H:%M:%S")} <= last_alert({last_alert_at.strftime("%H:%M:%S")})+{confirmed_new_failure_minutes}min',
                'path': 'timestamp_based',
            }

        if last_alert_at:
            elapsed = (datetime.now() - last_alert_at).total_seconds() / 60
            if elapsed >= fallback_delay_minutes:
                return {
                    'should_alert': True,
                    'reason': f'[fallback] elapsed={elapsed:.1f}min >= fallback_delay={fallback_delay_minutes}min',
                    'path': 'fallback_elapsed',
                }
            return {
                'should_alert': False,
                'reason': f'[fallback] elapsed={elapsed:.1f}min < fallback_delay={fallback_delay_minutes}min - duplicate',
                'path': 'fallback_elapsed',
            }

        return {'should_alert': True, 'reason': 'no parseable timestamps - allow alert', 'path': 'fallback_elapsed'}

    except Exception as e:
        logger.warning(f'check_alert_state failed: {e} - allow alert by default')
        return {'should_alert': True, 'reason': f'DB check error: {e}', 'path': 'error'}
