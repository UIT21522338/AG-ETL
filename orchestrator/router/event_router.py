from shared.logging.logger import get_logger

logger = get_logger("event_router")

ROUTING_RULES = {
    "nifi_error": "agent-1-error-diagnosis",
    "nifi_alert": "agent-4-monitoring",
    "data_quality_fail": "agent-3-data-quality",
    "dependency_check": "agent-5-dependency",
    "chatops_command": "agent-6-chatops",
    "config_update": "agent-7-nifi-config",
}

def route_event(event_type: str, payload: dict) -> str:
    agent = ROUTING_RULES.get(event_type)
    if not agent:
        logger.warning(f"No route found for event_type={event_type}")
        return "unhandled"
    logger.info(f"Routing {event_type} -> {agent}")
    return agent
