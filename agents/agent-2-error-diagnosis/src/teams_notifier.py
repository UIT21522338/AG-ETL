import requests

from shared.logging.logger import get_logger

logger = get_logger("agent-2.teams_notifier")


def _severity_color(severity: str) -> str:
    sev = str(severity or "").upper()
    if sev in {"CRITICAL", "HIGH"}:
        return "Attention"
    if sev == "MEDIUM":
        return "Warning"
    return "Good"


def _extract_processor_info(job_name: str) -> tuple:
    """
    Parse processor name and ID from job_name.
    
    Format: "ProcessorName[id=uuid]" -> ("ProcessorName", "uuid")
    Example: "PutDatabaseRecord[id=b6b57519-019c-1000-74c7]" 
             -> ("PutDatabaseRecord", "b6b57519-019c-1000-74c7")
    
    If format is unexpected, returns (job_name, "")
    """
    if not job_name:
        return ("Unknown", "")
    
    job_str = str(job_name).strip()
    
    # Try to parse format: "ProcessorName[id=uuid]"
    if "[id=" in job_str:
        bracket_pos = job_str.find("[id=")
        if bracket_pos > 0:
            processor_name = job_str[:bracket_pos]
            id_part = job_str[bracket_pos + 4:]  # Skip "[id="
            
            # Remove closing bracket if present
            if id_part.endswith("]"):
                id_part = id_part[:-1]
            
            return (processor_name, id_part)
    
    # Fallback: return job_name as-is if format doesn't match
    return (job_str, "")


def _format_header(error_category: str, job_name: str) -> str:
    """
    Format header as: [CATEGORY] | ProcessorName (processor_id)
    
    Example: [SOURCE_UNAVAILABLE] | PutDatabaseRecord (b6b57519-019c-1000-74c7-0a28c1d71aa8)
    """
    processor_name, processor_id = _extract_processor_info(job_name)
    
    if processor_id:
        return f"[{error_category}] | {processor_name} ({processor_id})"
    else:
        return f"[{error_category}] | {processor_name}"


def _truncate_text(text: str, max_len: int = 300) -> str:
    value = str(text or "")
    return value if len(value) <= max_len else value[:max_len] + "..."


def _numbered_steps(steps) -> str:
    if not isinstance(steps, list):
        return "1. Khong co de xuat cu the."
    cleaned = [str(s).strip() for s in steps if str(s).strip()]
    if not cleaned:
        return "1. Khong co de xuat cu the."
    return "\n".join([f"{idx}. {step}" for idx, step in enumerate(cleaned[:3], start=1)])


def build_teams_message(error_info: dict, classification: dict, llm_solution: dict) -> dict:
    """
    Build Microsoft Teams Adaptive Card message.
    
    Header format: [ERROR_CATEGORY] | ProcessorName (processor_id)
    Example: [SOURCE_UNAVAILABLE] | PutDatabaseRecord (b6b57519-019c-1000-74c7-0a28c1d71aa8)
    """
    error_category = classification.get("error_category") or error_info.get("error_category") or "UNKNOWN"
    matched_keyword = classification.get("matched_keyword") or error_info.get("matched_keyword")
    job_name = error_info.get("job_name") or "Unknown"

    severity = str(llm_solution.get("severity", "HIGH")).upper()
    card_color = _severity_color(severity)
    
    # Format header with processor name and ID
    header_text = _format_header(error_category, job_name)

    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "color": card_color,
            "text": header_text,
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Tenant: {error_info.get('tenant_code')} | Job ID: {error_info.get('job_id')} | Layer: {error_info.get('layer')}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Moi truong: {error_info.get('environment')} | Batch: {error_info.get('batch_id')}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Thoi gian loi: {error_info.get('end_time')}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Error message: {_truncate_text(error_info.get('error_message', ''))}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Nhom loi: {error_category} | Keyword: {matched_keyword}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Data flow: {error_info.get('rows_read')} rows doc -> {error_info.get('rows_written')} rows ghi",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Root cause: {llm_solution.get('root_cause_summary', '')}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"De xuat xu ly:\n{_numbered_steps(llm_solution.get('suggested_steps'))}",
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": f"Severity: {severity} | Est. fix: {llm_solution.get('estimated_fix_time')}",
            "wrap": True,
        },
    ]

    if bool(llm_solution.get("escalate_to_de_lead")):
        body.append(
            {
                "type": "Container",
                "style": "Attention",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "ESCALATE TO DE LEAD",
                        "weight": "Bolder",
                        "color": "Light",
                        "wrap": True,
                    }
                ],
            }
        )

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }
        ],
    }


def send_teams_alert(message: dict, webhook_url: str) -> bool:
    try:
        if not webhook_url:
            logger.error("Teams webhook URL is empty")
            return False
        response = requests.post(webhook_url, json=message, timeout=10)
        return 200 <= response.status_code < 300
    except Exception as exc:
        logger.error(f"Failed to send Teams alert: {exc}")
        return False
