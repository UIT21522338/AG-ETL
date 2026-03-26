import json
import os

from shared.llm.copilot_client import CopilotClient
from shared.logging.logger import get_logger

logger = get_logger("agent-2.llm_analyzer")

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "../prompts")
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

_FALLBACK = {
    "root_cause_summary": "Không thể phân tích tự động. Cần DE team xem xét.",
    "suggested_steps": ["Kiểm tra NiFi Bulletin Board", "Escalate lên DE Lead"],
    "severity": "HIGH",
    "estimated_fix_time": "Cần điều tra",
    "escalate_to_de_lead": True,
}


def _load_prompt(filename: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("Empty LLM response")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.find("\n")
        last_fence = cleaned.rfind("```")
        if first_nl != -1 and last_fence > first_nl:
            cleaned = cleaned[first_nl + 1:last_fence].strip()

    return json.loads(cleaned)


def _normalize_output(data: dict) -> dict:
    result = dict(_FALLBACK)

    if isinstance(data.get("root_cause_summary"), str) and data.get("root_cause_summary").strip():
        result["root_cause_summary"] = data["root_cause_summary"].strip()

    steps = data.get("suggested_steps")
    if isinstance(steps, list):
        normalized_steps = [str(item).strip() for item in steps if str(item).strip()]
        if normalized_steps:
            result["suggested_steps"] = normalized_steps[:3]

    severity = str(data.get("severity", "")).upper().strip()
    if severity in _VALID_SEVERITIES:
        result["severity"] = severity

    if isinstance(data.get("estimated_fix_time"), str) and data.get("estimated_fix_time").strip():
        result["estimated_fix_time"] = data["estimated_fix_time"].strip()

    if isinstance(data.get("escalate_to_de_lead"), bool):
        result["escalate_to_de_lead"] = data["escalate_to_de_lead"]

    return {
        "root_cause_summary": result["root_cause_summary"],
        "suggested_steps": result["suggested_steps"],
        "severity": result["severity"],
        "estimated_fix_time": result["estimated_fix_time"],
        "escalate_to_de_lead": result["escalate_to_de_lead"],
    }


def get_llm_solution(error_info: dict) -> dict:
    try:
        system_prompt = _load_prompt("system-prompt.md") + "\n\n" + _load_prompt("examples.md")
        user_message = (
            "Phan tich loi ETL sau va tra ve JSON:\n"
            f"- Job: {error_info.get('job_name')}\n"
            f"- Layer: {error_info.get('layer')}\n"
            f"- Moi truong: {error_info.get('environment')}\n"
            f"- Error category: {error_info.get('error_category')}\n"
            f"- Matched keyword: {error_info.get('matched_keyword')}\n"
            f"- Error message: {error_info.get('error_message')}\n"
            f"- Rows doc / ghi: {error_info.get('rows_read')} / {error_info.get('rows_written')}\n"
            f"- Thoi gian loi: {error_info.get('end_time')}\n\n"
            "Tra ve JSON voi dung 5 field:\n"
            "root_cause_summary, suggested_steps (list), severity, estimated_fix_time, escalate_to_de_lead"
        )

        raw_response = CopilotClient().chat(system_prompt, user_message)
        parsed = _extract_json(raw_response)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be JSON object")

        return _normalize_output(parsed)
    except Exception as exc:
        logger.error(f"LLM analysis failed, using fallback: {exc}")
        return dict(_FALLBACK)
