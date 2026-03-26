# Agent 2 — Error Diagnosis Specification

## 1. Phạm vi (Scope)
- Phân loại lỗi ETL từ NiFi / PostgreSQL
- Gợi ý root cause + recommended action
- Auto-retry transient error (DEV/UAT only)
- KHÔNG: thay đổi schema, DDL, config DB, NiFi flow

## 2. Level theo môi trường
| Env  | Level | Hành động cho phép |
|------|-------|--------------------|
| DEV  | L2–3  | Auto-retry transient errors |
| UAT  | L2–3  | Auto-retry transient errors |
| PROD | L1    | Classify + suggest only, không auto action |

## 3. Transient Error Allowlist (auto-retry)
- `connection timeout`
- `too many connections`

## 4. Input Schema
```json
{
  "error_id": "string",
  "timestamp": "ISO8601",
  "nifi_flow_name": "string",
  "processor_name": "string",
  "error_message_raw": "string",
  "stacktrace": "string (optional)",
  "environment": "DEV | UAT | PROD"
}
```

## 5. Output Schema
```json
{
  "error_category": "TRANSIENT_NETWORK | AUTH | DATA_QUALITY | CONFIG | UNKNOWN",
  "root_cause_summary": "string (1–3 câu)",
  "recommended_action": ["step1", "step2"],
  "auto_retry_allowed": true,
  "retry_decision": "NONE | RETRY_ONCE | RETRY_WITH_BACKOFF",
  "notify_channels": ["Teams", "Email"]
}
```

## 6. Pseudo Logic
```
1. Nhận event lỗi từ orchestrator/NiFi.
2. Chuẩn hóa error_message_raw + stacktrace.
3. LLM classifier: gán error_category, root_cause_summary, recommended_action.
4. Áp retry_policy:
   - Nếu env ∈ {DEV, UAT}
   - Và error_category = TRANSIENT_NETWORK
   - Và message chứa allowlist keywords
     => auto_retry_allowed = true, retry_decision = RETRY_ONCE
   - Ngược lại: auto_retry_allowed = false, retry_decision = NONE
5. Nếu auto_retry_allowed = true: gọi NiFi API rerun.
6. Luôn luôn: log vào PostgreSQL + alert Teams nếu severity cao.
```

## 7. Test Cases
| ID  | Env  | Error message | Expected category | Retry? |
|-----|------|--------------|-------------------|--------|
| T01 | DEV  | connection timeout to db host=... | TRANSIENT_NETWORK | RETRY_ONCE |
| T02 | UAT  | too many connections for role etl_user | TRANSIENT_NETWORK | RETRY_ONCE |
| T03 | PROD | connection timeout to db host=... | TRANSIENT_NETWORK | NONE |
| T04 | DEV  | permission denied for relation customers | AUTH | NONE |
| T05 | DEV  | invalid input syntax for type integer | DATA_QUALITY | NONE |
| T06 | DEV  | unknown error occurred | UNKNOWN | NONE |
