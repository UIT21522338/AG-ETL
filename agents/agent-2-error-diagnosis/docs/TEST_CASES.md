# TEST CASES -- Agent 2: Tat ca truong hop co the xay ra

## Nhom A: Classifier (test_classifier.py)

| ID | Input error_message | Expected retry_category | Expected sub_category |
|----|--------------------|--------------------------|-----------------------|
| C01 | connection timeout to PostgreSQL | TRANSIENT | CONNECTION_TIMEOUT |
| C02 | connection reset by peer broken pipe | TRANSIENT | NETWORK_RESET |
| C03 | too many connections PostgreSQL max_connections | TRANSIENT | TOO_MANY_CONNECTIONS |
| C04 | deadlock detected on relation etl_staging | TRANSIENT | DEADLOCK |
| C05 | query timeout statement_timeout | TRANSIENT | QUERY_TIMEOUT |
| C06 | database system is starting up / recovery | TRANSIENT | DB_STARTING |
| C07 | null value in column id violates not-null | NON_TRANSIENT | DATA_QUALITY |
| C08 | numeric field overflow precision 10 scale 2 | NON_TRANSIENT | DATA_QUALITY |
| C09 | duplicate key value violates unique constraint bk_hash | NON_TRANSIENT | DATA_QUALITY |
| C10 | relation bronze.NewTable does not exist | NON_TRANSIENT | CONFIGURATION |
| C11 | column updated_at does not exist | NON_TRANSIENT | CONFIGURATION |
| C12 | function etl_transform() does not exist | NON_TRANSIENT | CONFIGURATION |
| C13 | syntax error at or near SELECT | NON_TRANSIENT | CONFIGURATION |
| C14 | password authentication failed for user etl_user | NON_TRANSIENT | SOURCE_UNAVAILABLE |
| C15 | database etl_source does not exist | NON_TRANSIENT | SOURCE_UNAVAILABLE |
| C16 | java.lang.OutOfMemoryError Java heap space | NON_TRANSIENT | RESOURCE |
| C17 | no space left on device disk full | NON_TRANSIENT | RESOURCE |
| C18 | ERROR unexpected internal state XYZ-9999 | NON_TRANSIENT | UNKNOWN |
| C19 | (empty string) | NON_TRANSIENT | UNKNOWN |
| C20 | LLM timeout (simulate LLM fail) | NON_TRANSIENT | UNKNOWN (fallback) |

## Nhom B: Alert Dedup (test_alert_dedup.py)

| ID | Tinh huong | Expected should_alert | Path |
|----|-----------|----------------------|------|
| D01 | Chua co record nao cho identifier nay | True | first_time |
| D02 | Da gui 5p truoc, loi moi 3p truoc (>CONFIRMED=2) | True | timestamp_based |
| D03 | Da gui 5p truoc, loi 1p truoc (<=CONFIRMED=2) | False | timestamp_based |
| D04 | Da gui 3p truoc, timestamp=None, elapsed<FALLBACK=5 | False | fallback_elapsed |
| D05 | Da gui 6p truoc, timestamp=None, elapsed>=FALLBACK=5 | True | fallback_elapsed |
| D06 | DB throw exception khi query | True | error (safe default) |

## Nhom C: Retry Policy (test_retry_policy.py)

| ID | Tinh huong | Expected eligible |
|----|-----------|-------------------|
| R01 | TRANSIENT, count=0, max=3, trong window | True |
| R02 | NON_TRANSIENT (DATA_QUALITY) | False |
| R03 | TRANSIENT, count=3, max=3 (da het) | False |
| R04 | TRANSIENT, count=1, max=3, ngoai window 50p | False |
| R05 | TRANSIENT, count=2, max=3, trong window | True |
| R06 | is_retryable=False (LLM quyet dinh) | False |

## Nhom D: Teams Card (test_teams_notifier.py)

| ID | Tinh huong | Kiem tra |
|----|-----------|----------|
| T01 | pg_log TRANSIENT co retry | Job ID la dong dau tien |
| T02 | pg_log NON_TRANSIENT khong retry | Retry str = 'Khong...' |
| T03 | bulletin board | Processor ID la dong dau tien |
| T04 | LLM steps = None | Steps dung DEFAULT_STEPS khong trong |
| T05 | LLM steps = [] | Steps dung DEFAULT_STEPS khong trong |
| T06 | retry MAX_REACHED | Retry str chua MAX_REACHED |
| T07 | error_message dai 2000 ky tu | Error Detail bi cat o 1000 |

## Nhom E: End-to-End (test_end_to_end.py)

| ID | Tinh huong | Teams cards | NiFi FlowFile | diagnosis_log rows |
|----|-----------|-------------|---------------|-------------------|
| E01 | TRANSIENT lan 1 | 1 card | +1 | 1 row TRIGGERED |
| E02 | Cung job lan 2 (sau CONFIRMED p) | 1 card moi | +1 | 1 row moi |
| E03 | TRANSIENT qua MAX_RETRIES | 1 card MAX_REACHED | 0 | 1 row MAX_REACHED |
| E04 | 3 row dup cung job+batch | 1 card | +1 | 3 rows, 1 alert |
| E05 | NON_TRANSIENT DATA_QUALITY | 1 card | 0 | 1 row no retry |
| E06 | Bulletin Board RESOURCE | 1 card | 0 | 1 row bulletin |
| E07 | UNKNOWN error ngoai 5 nhom | 1 card + LLM steps | 0 | 1 row UNKNOWN |
| E08 | 4 job fail cung batch | 4 cards | +2 (TRANSIENT jobs) | 4 rows |
