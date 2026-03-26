import os
from functools import lru_cache

import yaml

from shared.logging.logger import get_logger

logger = get_logger("agent-2.classifier")

PRIORITY_ORDER = ["TRANSIENT", "DATA_QUALITY", "CONFIGURATION", "SOURCE_UNAVAILABLE", "RESOURCE"]


@lru_cache(maxsize=1)
def _load_keywords() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "../config/error_keywords.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def classify_error(error_message: str) -> dict:
    if not error_message:
        return {
            "error_category": "UNKNOWN",
            "matched_keyword": None,
            "classification_method": "rule_based",
        }

    message_lower = str(error_message).lower()
    keywords = _load_keywords()

    for category in PRIORITY_ORDER:
        for keyword in keywords.get(category, []):
            if keyword.lower() in message_lower:
                return {
                    "error_category": category,
                    "matched_keyword": keyword,
                    "classification_method": "rule_based",
                }

    return {
        "error_category": "UNKNOWN",
        "matched_keyword": None,
        "classification_method": "rule_based",
    }
