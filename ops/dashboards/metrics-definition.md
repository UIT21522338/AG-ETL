# Agent Metrics Definition

| Metric | Agent | Mô tả |
|--------|-------|-------|
| errors_classified_total | Agent 2 | Tổng lỗi đã phân loại |
| retries_attempted_total | Agent 2 | Tổng số lần retry |
| retries_success_total | Agent 2 | Retry thành công |
| alerts_sent_total | Agent 1 | Tổng alert Teams đã gửi |
| dq_checks_total | Agent 3 | Tổng data quality checks |
| dq_blocks_total | Agent 3 | Số lần block pipeline |

## Agent 2 — Error Diagnosis Metrics

| Metric | Query | Y nghia |
|--------|-------|---------|
| Total errors processed | `SELECT COUNT(*) FROM agent_log.diagnosis_log;` | Tong loi da xu ly |
| By category | `SELECT error_category, COUNT(*) FROM agent_log.diagnosis_log GROUP BY error_category;` | Phan bo nhom loi |
| Alert rate | `SELECT COALESCE(SUM(CASE WHEN teams_alert_sent THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) FROM agent_log.diagnosis_log;` | Ty le alert gui thanh cong |
| Escalate rate | `SELECT COALESCE(SUM(CASE WHEN llm_escalate THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) FROM agent_log.diagnosis_log;` | Ty le can DE Lead xem |
| Avg processing time | `SELECT AVG(processing_duration_ms) FROM agent_log.diagnosis_log;` | Thoi gian xu ly trung binh |
| CRITICAL/HIGH ratio | `SELECT COALESCE(SUM(CASE WHEN llm_severity IN ('CRITICAL','HIGH') THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0), 0) FROM agent_log.diagnosis_log;` | Ty le loi nghiem trong |
