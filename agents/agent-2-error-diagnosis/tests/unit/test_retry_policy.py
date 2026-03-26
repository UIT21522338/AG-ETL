import pytest
from agents.agent_2_error_diagnosis.src.retry_policy import should_retry

# Test cases từ spec.md
@pytest.mark.parametrize("env,category,message,expected_retry,expected_decision", [
    ("DEV",  "TRANSIENT_NETWORK", "connection timeout to db host=...",         True,  "RETRY_ONCE"),
    ("UAT",  "TRANSIENT_NETWORK", "too many connections for role etl_user",    True,  "RETRY_ONCE"),
    ("PROD", "TRANSIENT_NETWORK", "connection timeout to db host=...",          False, "NONE"),
    ("DEV",  "AUTH",              "permission denied for relation customers",   False, "NONE"),
    ("DEV",  "DATA_QUALITY",      "invalid input syntax for type integer",      False, "NONE"),
    ("DEV",  "UNKNOWN",           "unknown error occurred",                     False, "NONE"),
])
def test_retry_policy(env, category, message, expected_retry, expected_decision):
    result = should_retry(category, message, env)
    assert result["auto_retry_allowed"] == expected_retry
    assert result["retry_decision"] == expected_decision
