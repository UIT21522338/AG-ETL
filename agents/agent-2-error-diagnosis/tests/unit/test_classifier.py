import pytest
from agents.agent_2_error_diagnosis.src.classifier import classify_error


@pytest.mark.parametrize(
    "msg,expected_cat,expected_kw_contains",
    [
        # TRANSIENT
        ("connection timeout to PostgreSQL host=db port=5432", "TRANSIENT", "connection timeout"),
        ("too many connections for role etl_user", "TRANSIENT", "too many connections"),
        ("connection reset by peer", "TRANSIENT", "connection reset"),
        ("broken pipe while sending query", "TRANSIENT", "broken pipe"),
        ("deadlock detected on transaction", "TRANSIENT", "deadlock detected"),
        ("the database system is starting up", "TRANSIENT", "the database system is starting up"),
        # DATA_QUALITY
        ('invalid input syntax for type integer: "abc"', "DATA_QUALITY", "invalid input syntax for type integer"),
        ('null value in column "status" violates not-null constraint', "DATA_QUALITY", "null value in column"),
        ("duplicate key value violates unique constraint bk_hash_key", "DATA_QUALITY", "bk_hash_key"),
        ("value too long for type character varying(100)", "DATA_QUALITY", "value too long for type character"),
        # CONFIGURATION
        ('relation "bronze.sales_order" does not exist', "CONFIGURATION", "does not exist"),
        ('column "created_at" of relation does not exist', "CONFIGURATION", "does not exist"),
        ('syntax error at or near "FORM"', "CONFIGURATION", "syntax error at"),
        # SOURCE_UNAVAILABLE
        ('password authentication failed for user "etl_user"', "SOURCE_UNAVAILABLE", "password authentication failed"),
        ("login failed for user 'sa'", "SOURCE_UNAVAILABLE", "login failed for user"),
        # RESOURCE
        ("java.lang.OutOfMemoryError: Java heap space", "RESOURCE", "java.lang.outofmemoryerror"),
        ("no space left on device", "RESOURCE", "no space left on device"),
        ("FlowFile is empty, no content available", "RESOURCE", "flowfile is empty"),
        # UNKNOWN
        ("some completely unknown error xyz123", "UNKNOWN", None),
        ("", "UNKNOWN", None),
    ],
)
def test_classify_error(msg, expected_cat, expected_kw_contains):
    result = classify_error(msg)
    assert result["error_category"] == expected_cat
    assert result["classification_method"] == "rule_based"
    if expected_kw_contains:
        assert expected_kw_contains in (result["matched_keyword"] or "")
    else:
        assert result["matched_keyword"] is None
