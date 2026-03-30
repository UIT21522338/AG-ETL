import json

from shared.llm.copilot_client import CopilotClient
from shared.logging.logger import get_logger

logger = get_logger("agent-2.classifier")
_llm = None


def _get_llm() -> CopilotClient:
    global _llm
    if _llm is None:
        _llm = CopilotClient()
    return _llm


SYSTEM_PROMPT = """
Ban la chuyen gia phan tich loi ETL/Data Pipeline.
Phan loai loi theo 2 nhom chinh dua tren nguyen tac:

TRANSIENT -- loi tam thoi, he thong co the tu phuc hoi neu thu lai:
  - Connection timeout, connection refused, connection reset
  - Too many connections, max connections exceeded
  - Deadlock detected
  - Query/statement timeout
  - Database dang khoi dong / recovery mode
  - Broken pipe, network reset

NON_TRANSIENT -- loi can can thiep thu cong, thu lai vo ich:
  - NULL violation, type mismatch, overflow, string too long
  - Duplicate key, foreign key violation
  - Schema/table/column/function khong ton tai
  - Syntax error trong SQL
  - Authentication failed, permission denied
  - Instance/DB khong ton tai
  - OutOfMemory, disk full
  - Bat ky loi khong ro rang -> NON_TRANSIENT (an toan hon)

SUB_CATEGORY:
  TRANSIENT    : CONNECTION_TIMEOUT | TOO_MANY_CONNECTIONS | DEADLOCK |
                 QUERY_TIMEOUT | DB_STARTING | NETWORK_RESET
  NON_TRANSIENT: DATA_QUALITY | CONFIGURATION | SOURCE_UNAVAILABLE |
                 RESOURCE | UNKNOWN

SEVERITY: CRITICAL | HIGH | MEDIUM | LOW

Tra loi DUNG DINH DANG JSON, khong them gi khac:
{
  "retry_category" : "TRANSIENT" or "NON_TRANSIENT",
  "sub_category"   : "<sub category>",
  "severity"       : "CRITICAL" or "HIGH" or "MEDIUM" or "LOW",
  "root_cause"     : "<1 cau tieng Viet>",
  "suggested_steps": ["<buoc 1>", "<buoc 2>", "<buoc 3>"],
  "confidence"     : "HIGH" or "MEDIUM" or "LOW"
}
"""


USER_PROMPT_TEMPLATE = """
Phan tich loi ETL:
  Job Name : {job_name}
  Layer    : {layer}
  Source   : {source}
  Rows Read: {rows_read} | Rows Written: {rows_written}

ERROR MESSAGE:
{error_message}

Tra loi JSON theo dung format.
"""


DEFAULT_FALLBACK = {
    "retry_category": "NON_TRANSIENT",
    "sub_category": "UNKNOWN",
    "severity": "MEDIUM",
    "root_cause": "Khong the phan tich tu dong -- xem Error Detail",
    "suggested_steps": [
        "Doc error message day du trong thong bao",
        "Kiem tra NiFi bulletin board va log file",
        "Lien he DE Lead voi full error log de dieu tra",
    ],
    "confidence": "LOW",
}


def classify_and_analyze(error: dict) -> dict:
    error_message = str(error.get("error_message") or "").strip()
    if not error_message:
        logger.warning("classify_and_analyze: empty error_message -- fallback")
        return _make_fallback("")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_name=error.get("job_name") or error.get("processor_name") or "N/A",
        layer=error.get("layer", "N/A"),
        source=error.get("source", "pg_log"),
        rows_read=error.get("rows_read", 0),
        rows_written=error.get("rows_written", 0),
        error_message=error_message,
    )

    try:
        raw = _get_llm().chat(SYSTEM_PROMPT, user_prompt)
        raw_str = str(raw).strip()
        start = raw_str.find("{")
        end = raw_str.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON in LLM response: {raw_str[:200]}")

        parsed = json.loads(raw_str[start:end])

        retry_category = str(parsed.get("retry_category", "NON_TRANSIENT")).upper()
        if retry_category not in ("TRANSIENT", "NON_TRANSIENT"):
            retry_category = "NON_TRANSIENT"

        sub_category = str(parsed.get("sub_category", "UNKNOWN")).upper()
        severity = str(parsed.get("severity", "MEDIUM")).upper()
        if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            severity = "MEDIUM"

        confidence = str(parsed.get("confidence", "MEDIUM")).upper()
        if confidence not in ("HIGH", "MEDIUM", "LOW"):
            confidence = "MEDIUM"

        steps = parsed.get("suggested_steps") or []
        if not isinstance(steps, list) or not any(str(s).strip() for s in steps):
            steps = DEFAULT_FALLBACK["suggested_steps"]

        result = {
            "retry_category": retry_category,
            "sub_category": sub_category,
            "severity": severity,
            "root_cause": parsed.get("root_cause") or DEFAULT_FALLBACK["root_cause"],
            "suggested_steps": [str(s).strip() for s in steps[:3]],
            "confidence": confidence,
            "error_category": sub_category,
            "is_retryable": retry_category == "TRANSIENT",
            "raw_response": raw_str,
        }
        logger.info(
            f"LLM classify: {retry_category}/{sub_category} "
            f"severity={severity} confidence={confidence}"
        )
        return result

    except Exception as exc:
        logger.error(f"classify_and_analyze LLM failed: {exc} -- fallback")
        return _make_fallback(str(exc))


def _make_fallback(raw: str) -> dict:
    result = dict(DEFAULT_FALLBACK)
    result["error_category"] = result["sub_category"]
    result["is_retryable"] = False
    result["raw_response"] = raw
    return result


def classify_error(error_message: str) -> dict:
    return classify_and_analyze({"error_message": error_message})
