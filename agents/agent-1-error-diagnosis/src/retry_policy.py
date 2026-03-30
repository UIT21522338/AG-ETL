from datetime import datetime


def should_retry(error: dict, retry_cfg: dict) -> dict:
    is_retryable = error.get("is_retryable")
    if is_retryable is None:
        is_retryable = error.get("retry_category") == "TRANSIENT"
    if not is_retryable:
        return {"eligible": False, "reason": "LLM classified NON_TRANSIENT -- no retry"}

    retry_count = int(error.get("retry_count") or 0)
    max_retries = int(retry_cfg.get("max_retries", 3))
    if retry_count >= max_retries:
        return {"eligible": False, "reason": f"retry_count={retry_count} >= max={max_retries}"}

    ts = error.get("end_time")
    if ts:
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts[:19].replace("T", " "))
            age = (datetime.now() - ts).total_seconds() / 60
            window_minutes = int(retry_cfg.get("max_retry_window_minutes", 50))
            if age > window_minutes:
                return {
                    "eligible": False,
                    "reason": f"error too old ({age:.0f}min > {window_minutes}min)",
                }
        except Exception:
            pass

    return {
        "eligible": True,
        "reason": f"TRANSIENT -- retry {retry_count + 1}/{max_retries}",
    }
