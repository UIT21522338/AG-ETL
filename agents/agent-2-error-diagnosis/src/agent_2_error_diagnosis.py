# Agent 2 — Error Diagnosis — Main entrypoint
# TODO: Wire up classifier + retry_policy + nifi_client + pg_client

import uuid
from agents.agent_2_error_diagnosis.src.retry_policy import should_retry
from shared.logging.logger import get_logger
from shared.logging.correlation_id import set_correlation_id

logger = get_logger("agent-2-error-diagnosis")

def handle_error_event(event: dict) -> dict:
    """
    Main handler cho error event.
    Input: event dict (xem Input Schema trong spec.md)
    Output: action result dict
    """
    cid = str(uuid.uuid4())
    set_correlation_id(cid)
    logger.info(f"[{cid}] Handling error event: {event.get('error_id')}")

    # TODO: Step 1 — Classify error
    # TODO: Step 2 — Apply retry policy
    # TODO: Step 3 — Execute retry if allowed
    # TODO: Step 4 — Log to PostgreSQL
    # TODO: Step 5 — Notify Teams if needed

    raise NotImplementedError("Implement sau khi spec được approve và test cases đã sign-off")
