import requests
from datetime import datetime
from shared.logging.logger import get_logger

logger = get_logger('agent-2.teams_notifier')

SEVERITY_EMOJI = {
    'CRITICAL': '🔴',
    'HIGH'    : '🟠',
    'MEDIUM'  : '🟡',
    'LOW'     : '🟢',
}
CATEGORY_EMOJI = {
    'TRANSIENT'        : '⚡',
    'DATA_QUALITY'     : '📊',
    'CONFIGURATION'    : '⚙',
    'SOURCE_UNAVAILABLE': '📵',
    'RESOURCE'         : '💾',
    'UNKNOWN'          : '❓',
}


def _ts_str(ts) -> str:
    if ts is None:
        return 'N/A'
    try:
        if isinstance(ts, datetime):
            return ts.strftime('%Y-%m-%d %H:%M:%S')
        return str(ts)[:19].replace('T', ' ')
    except Exception:
        return str(ts)


def build_alert_card(error: dict, classification: dict, llm_solution: dict) -> dict:
    source = error.get('source', 'pg_log')
    category = classification.get('error_category', 'UNKNOWN')
    severity = llm_solution.get('severity') or classification.get('severity', 'MEDIUM')
    sev_emoji = SEVERITY_EMOJI.get(severity, '🟡')
    cat_emoji = CATEGORY_EMOJI.get(category, '❓')

    if source in ('bulletin', 'nifi_bulletin'):
        entity_name = error.get('processor_name') or error.get('job_name') or 'Unknown Processor'
        entity_id = error.get('processor_id') or error.get('source_log_id') or 'N/A'
        ts_str = _ts_str(error.get('bulletin_ts') or error.get('end_time'))
        retry_str = 'Khong (Bulletin Board khong retry)'
        source_label = 'NiFi Bulletin Board'
        specific_facts = [
            {'title': 'ID', 'value': entity_id},
            {'title': 'Processor Name', 'value': entity_name},
            {'title': 'Node', 'value': error.get('node_address', 'N/A')},
        ]
    else:
        entity_name = error.get('job_name', 'Unknown Job')
        entity_id = str(error.get('job_id', 'N/A'))
        ts_str = _ts_str(error.get('end_time'))
        source_label = 'PostgreSQL Job Log'
        rc = int(error.get('retry_count') or 0)
        rm = int(error.get('max_retries') or 3)
        if error.get('retry_eligible'):
            rs = error.get('retry_status') or 'PENDING'
            retry_str = f'Co - lan {rc}/{rm} | Status: {rs}'
        else:
            retry_str = f'Khong (category {category} khong retry)'
        if (error.get('retry_status') or '').upper() == 'MAX_REACHED':
            retry_str = 'MAX_REACHED - can DE Lead xu ly thu cong'
        specific_facts = [
            {'title': 'ID', 'value': entity_id},
            {'title': 'Job Name', 'value': entity_name},
            {'title': 'Batch ID', 'value': str(error.get('batch_id', 'N/A'))},
            {'title': 'Tenant', 'value': error.get('tenant_code', 'N/A')},
            {'title': 'Layer', 'value': error.get('layer', 'N/A')},
            {'title': 'Rows Read', 'value': str(error.get('rows_read', 0))},
            {'title': 'Rows Written', 'value': str(error.get('rows_written', 0))},
        ]

    title = f'{sev_emoji} {cat_emoji} {category} | {entity_name}'
    steps = llm_solution.get('suggested_steps')
    if not isinstance(steps, list) or not any(str(s).strip() for s in steps):
        steps = [
            'Doc error message day du trong thong bao',
            'Kiem tra NiFi bulletin board va log file',
            'Lien he DE Lead voi full error log de dieu tra',
        ]
    root_cause = llm_solution.get('root_cause') or llm_solution.get('root_cause_summary', 'Chua xac dinh')
    err_msg = str(error.get('error_message', 'N/A'))

    facts = [
        {'title': specific_facts[0]['title'], 'value': specific_facts[0]['value']},
        {'title': 'Nguon', 'value': source_label},
        {'title': 'Nhom loi', 'value': category},
        {'title': 'Muc do', 'value': f'{sev_emoji} {severity}'},
        {'title': 'Thoi gian', 'value': ts_str},
        {'title': 'Retry', 'value': retry_str},
    ] + specific_facts[1:] + [
        {'title': 'Root Cause', 'value': root_cause},
        {'title': 'Error Detail', 'value': err_msg[:1000]},
        {'title': 'LLM Steps', 'value': ' | '.join([f'{i + 1}. {s}' for i, s in enumerate(steps[:3])])},
    ]

    return {
        'type': 'message',
        'attachments': [{
            'contentType': 'application/vnd.microsoft.card.adaptive',
            'content': {
                '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                'type': 'AdaptiveCard',
                'version': '1.4',
                'body': [
                    {'type': 'TextBlock', 'text': title, 'weight': 'Bolder', 'size': 'Medium', 'wrap': True},
                    {'type': 'FactSet', 'facts': facts},
                ],
            },
        }],
    }


def send_teams_alert(card: dict, webhook_url: str) -> bool:
    if not webhook_url:
        logger.warning('TEAMS_WEBHOOK_URL not configured - skip alert')
        return False
    try:
        resp = requests.post(webhook_url, json=card, timeout=10)
        resp.raise_for_status()
        logger.info('Teams alert sent OK')
        return True
    except Exception as e:
        logger.error(f'Teams alert failed: {e}')
        return False
