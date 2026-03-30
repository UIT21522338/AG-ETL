import os, json, requests
from datetime import datetime, timedelta
from shared.db.pg_client import PGClient
from shared.nifi.nifi_client import NiFiClient
from shared.logging.logger import get_logger

logger = get_logger('agent-2.retry_executor')


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


def check_retry_state(
    pg_client: PGClient,
    job_id: str,
    batch_id: str,
    error_end_time: str,
    confirmed_new_failure_minutes: int = 2,
    fallback_delay_minutes: int = 5,
    window_minutes: int = 50,
) -> dict:
    '''
    Xac dinh hanh dong retry cho 1 loi TRANSIENT.

    HAI BIEN CO THE TUY CHINH QUA YAML / .env:

    confirmed_new_failure_minutes (YAML: retry.confirmed_new_failure_minutes)
      Dung cho LUONG CHINH (co timestamp).
      So sanh end_time(loi moi) voi last_retry_at + N phut:
        > N phut  => loi xay ra SAU khi NiFi da chay xong => RETRY
        <= N phut => loi xay ra TRUOC/TRONG KHI NiFi dang chay => SKIP
      Dat bang: thoi gian Bronze job chay nhanh nhat + 1 phut buffer.
      Vi du: Bronze min=3min -> dat 4.

    fallback_delay_minutes (YAML: retry.fallback_delay_minutes)
      Chi dung khi timestamp NULL hoac khong parse duoc (LUONG DU PHONG).
      Tinh elapsed = now - last_retry_at:
        elapsed < N phut  => SKIP (con trong thoi gian cho NiFi)
        elapsed >= N phut => RETRY (da du thoi gian, cho phep thu lai)
      Nen dat >= confirmed_new_failure_minutes de an toan.
      Vi du: confirmed=4 -> fallback=5.

    Return dict:
      action      : FIRST_TIME | RETRY | SKIP
      reason      : giai thich ro nguon (timestamp / fallback / status)
      retry_count : so lan da retry truoc do
      path        : timestamp_based | fallback_elapsed | status_based
    '''
    try:
        rows = pg_client.fetchall(
            f'''
            SELECT retry_status, retry_count, last_retry_at
            FROM agent_log.diagnosis_log
            WHERE CAST(job_id AS VARCHAR) = %s
              AND batch_id       = %s
              AND retry_eligible = TRUE
              AND processed_at  >= NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh' - INTERVAL '{window_minutes} minutes'
            ORDER BY diagnosis_id DESC
            LIMIT 1
            ''',
            (str(job_id), str(batch_id))
        )

        if not rows:
            return {
                'action': 'FIRST_TIME',
                'reason': 'no previous retry record in window',
                'retry_count': 0,
                'path': 'status_based',
            }

        row    = rows[0]
        status = row.get('retry_status')
        count  = int(row.get('retry_count') or 0)

        if status == 'SUCCESS':
            return {'action': 'SKIP', 'reason': 'already SUCCESS', 'retry_count': count, 'path': 'status_based'}

        if status == 'MAX_REACHED':
            return {'action': 'SKIP', 'reason': 'MAX_REACHED - escalate DE Lead', 'retry_count': count, 'path': 'status_based'}

        if status == 'TRIGGERED':
            last_retry_at  = _parse_ts(row.get('last_retry_at'))
            current_err_ts = _parse_ts(error_end_time)

            # LUONG CHINH: co du timestamp de so sanh
            if last_retry_at and current_err_ts:
                threshold = last_retry_at + timedelta(minutes=confirmed_new_failure_minutes)
                if current_err_ts <= threshold:
                    return {
                        'action': 'SKIP',
                        'reason': (
                            f'[timestamp] error_end={current_err_ts.strftime("%H:%M:%S")} '
                            f'<= last_retry({last_retry_at.strftime("%H:%M:%S")}) '
                            f'+ {confirmed_new_failure_minutes}min '
                            f'- NiFi still executing'
                        ),
                        'retry_count': count,
                        'path': 'timestamp_based',
                    }
                return {
                    'action': 'RETRY',
                    'reason': (
                        f'[timestamp] error_end={current_err_ts.strftime("%H:%M:%S")} '
                        f'> last_retry({last_retry_at.strftime("%H:%M:%S")}) '
                        f'+ {confirmed_new_failure_minutes}min '
                        f'- confirmed new failure after retry'
                    ),
                    'retry_count': count,
                    'path': 'timestamp_based',
                }

            # LUONG DU PHONG: timestamp NULL hoac parse loi
            if last_retry_at:
                elapsed = (datetime.now() - last_retry_at).total_seconds() / 60
                if elapsed < fallback_delay_minutes:
                    return {
                        'action': 'SKIP',
                        'reason': (
                            f'[fallback] elapsed={elapsed:.1f}min '
                            f'< fallback_delay={fallback_delay_minutes}min '
                            f'- waiting for NiFi result'
                        ),
                        'retry_count': count,
                        'path': 'fallback_elapsed',
                    }
                return {
                    'action': 'RETRY',
                    'reason': (
                        f'[fallback] elapsed={elapsed:.1f}min '
                        f'>= fallback_delay={fallback_delay_minutes}min '
                        f'- allow retry (error_end_time not parseable)'
                    ),
                    'retry_count': count,
                    'path': 'fallback_elapsed',
                }

            # Khong co bat ky timestamp nao -> cho retry
            return {
                'action': 'RETRY',
                'reason': 'no timestamps available - fallback allow retry',
                'retry_count': count,
                'path': 'fallback_elapsed',
            }

        # FAILED hoac NULL -> cho retry lan tiep
        return {
            'action': 'RETRY',
            'reason': f'previous status={status} - eligible for next attempt',
            'retry_count': count,
            'path': 'status_based',
        }

    except Exception as e:
        logger.warning(f'check_retry_state failed: {e} - assume FIRST_TIME')
        return {'action': 'FIRST_TIME', 'reason': f'DB check error: {e}', 'retry_count': 0, 'path': 'error'}


def get_processor_revision(nifi_client: NiFiClient, processor_id: str) -> dict:
    resp = requests.get(
        f'{nifi_client.base_url}/nifi-api/processors/{processor_id}',
        headers={'Authorization': f'Bearer {nifi_client.token}'},
        verify=False,
        timeout=nifi_client.timeout,
    )
    resp.raise_for_status()
    return resp.json().get('revision', {'version': 0})


def trigger_nifi_luong3(
    nifi_client: NiFiClient,
    processor_id: str,
    batch_id: str,
    job_group: str,
    job_id: str,
) -> dict:
    if not processor_id or processor_id == 'REPLACE_WITH_ACTUAL_PROCESSOR_ID':
        return {'success': False, 'message': 'nifi_luong3_processor_id chua duoc cau hinh', 'nifi_response': None}
    try:
        payload  = {'v_batch_id': batch_id or '', 'v_job_group': job_group or '', 'v_job_ids': str(job_id) if job_id else ''}
        revision = get_processor_revision(nifi_client, processor_id)
        headers  = {'Authorization': f'Bearer {nifi_client.token}', 'Content-Type': 'application/json'}
        patch_resp = requests.put(
            f'{nifi_client.base_url}/nifi-api/processors/{processor_id}',
            headers=headers,
            json={'revision': revision, 'component': {'id': processor_id, 'config': {'properties': {'custom-text': json.dumps(payload)}}}},
            verify=False, timeout=nifi_client.timeout,
        )
        patch_resp.raise_for_status()
        logger.info(f'Luong3 variables set: {payload}')
        revision2 = patch_resp.json().get('revision', revision)
        run_resp  = requests.put(
            f'{nifi_client.base_url}/nifi-api/processors/{processor_id}/run-status',
            headers=headers,
            json={'revision': revision2, 'state': 'RUN_ONCE'},
            verify=False, timeout=nifi_client.timeout,
        )
        run_resp.raise_for_status()
        logger.info(f'Luong3 triggered RUN_ONCE | job_id={job_id} batch={batch_id}')
        return {'success': True, 'message': f'Triggered: job_id={job_id} batch={batch_id}', 'nifi_response': run_resp.json()}

    except Exception as e:
        logger.error(f'trigger_nifi_luong3 failed: {e}')
        return {'success': False, 'message': str(e), 'nifi_response': None}


def update_retry_state(
    pg_client: PGClient,
    diagnosis_id: int,
    retry_count: int,
    retry_status: str,
    triggered_by: str = 'agent_auto',
) -> bool:
    try:
        pg_client.execute(
            '''
            UPDATE agent_log.diagnosis_log
            SET retry_count        = %s,
                retry_status       = %s,
                last_retry_at      = %s,
                retry_triggered_by = %s
            WHERE diagnosis_id = %s
            ''',
            (retry_count, retry_status, datetime.now(), triggered_by, diagnosis_id)
        )
        logger.info(f'diagnosis_id={diagnosis_id} updated: count={retry_count} status={retry_status}')
        return True
    except Exception as e:
        logger.error(f'update_retry_state failed: {e}')
        return False
