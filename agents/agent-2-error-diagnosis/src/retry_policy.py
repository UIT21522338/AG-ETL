# retry_policy.py — Quyết định retry
# Rule-based (không dùng LLM) để đảm bảo predictable

TRANSIENT_KEYWORDS = [
    "connection timeout",
    "too many connections",
]

RETRY_ALLOWED_ENVS = {"DEV", "UAT"}

def should_retry(error_category: str, error_message: str, environment: str) -> dict:
    """
    Quyết định có retry không dựa trên rule.
    Returns: {"auto_retry_allowed": bool, "retry_decision": str}
    """
    if environment.upper() not in RETRY_ALLOWED_ENVS:
        return {"auto_retry_allowed": False, "retry_decision": "NONE"}

    if error_category != "TRANSIENT_NETWORK":
        return {"auto_retry_allowed": False, "retry_decision": "NONE"}

    msg_lower = error_message.lower()
    for keyword in TRANSIENT_KEYWORDS:
        if keyword in msg_lower:
            return {"auto_retry_allowed": True, "retry_decision": "RETRY_ONCE"}

    return {"auto_retry_allowed": False, "retry_decision": "NONE"}
