# Runbook — Agent 2: Error Diagnosis & Alert

## Mô tả
Agent tự động poll lỗi từ NiFi Bulletin Board và PostgreSQL ETL log,
phân loại vào 5 nhóm, dùng LLM phân tích nguyên nhân, gửi alert Teams với solution.
Phase 1: Alert only. Phase 2 (tương lai): Auto-retry TRANSIENT errors.

## Chạy thủ công
```bash
cd etl-nifi-agents
python agents/agent-1-error-diagnosis/run.py
```

## Chạy vòng lặp liên tục
```bash
cd etl-nifi-agents
python agents/agent-1-error-diagnosis/run.py --loop
```

## Override poll interval
```bash
# Linux/macOS
AGENT_POLL_INTERVAL=60 python agents/agent-1-error-diagnosis/run.py --loop

# Windows PowerShell
$env:AGENT_POLL_INTERVAL=60
python agents/agent-1-error-diagnosis/run.py --loop
```

## Chạy theo lịch (Linux cron mỗi 1 phút)
```bash
* * * * * cd /path/to/etl-nifi-agents && /path/to/venv/bin/python agents/agent-1-error-diagnosis/run.py >> /var/log/agent2.log 2>&1
```

## Chạy theo lịch (Windows Task Scheduler)
- Program/script: `C:\path\to\venv\Scripts\python.exe`
- Add arguments: `agents/agent-1-error-diagnosis/run.py`
- Start in: `C:\path\to\etl-nifi-agents`

## Khi Teams không nhận được alert
1. Kiểm tra `.env` — `TEAMS_WEBHOOK_URL` có đúng không.
2. Kiểm tra DB:
	`SELECT * FROM agent_log.diagnosis_log WHERE teams_alert_sent = false ORDER BY processed_at DESC LIMIT 5;`
3. Chạy lại thủ công:
	`python agents/agent-1-error-diagnosis/run.py`

## Khi agent lỗi
1. Xem log file: `tail -100 /var/log/agent2.log` (Linux) hoặc transcript log trên Task Scheduler (Windows).
2. Kiểm tra kết nối PG:
	`psql -h $PG_HOST -U $PG_USER -d $PG_DATABASE -c "SELECT 1"`
3. Kiểm tra NiFi API:
	`curl -u $NIFI_USERNAME:$NIFI_PASSWORD $NIFI_BASE_URL/nifi-api/flow/bulletin-board`

## Escalation
- DE Team: de-team@company.com
- Teams channel: #etl-alerts
- Khi `llm_escalate = true` trong `agent_log.diagnosis_log` -> DE Lead phải xem ngay.

## Query hữu ích
```sql
-- Xem 10 records mới nhất
SELECT diagnosis_id, source, job_name, error_category,
		 matched_keyword, llm_severity, teams_alert_sent, processed_at
FROM agent_log.diagnosis_log
ORDER BY processed_at DESC LIMIT 10;

-- Lỗi chưa có solution rõ ràng (cần escalate)
SELECT *
FROM agent_log.diagnosis_log
WHERE llm_escalate = true
ORDER BY processed_at DESC;

-- Lỗi nhiều nhất trong 24h
SELECT job_name, error_category, COUNT(*)
FROM agent_log.diagnosis_log
WHERE processed_at > NOW() - INTERVAL '24 hours'
GROUP BY job_name, error_category
ORDER BY 3 DESC;

-- Thống kê theo nhóm lỗi
SELECT error_category,
		 COUNT(*) AS total,
		 SUM(CASE WHEN teams_alert_sent THEN 1 ELSE 0 END) AS alerted,
		 SUM(CASE WHEN llm_escalate THEN 1 ELSE 0 END) AS escalated
FROM agent_log.diagnosis_log
GROUP BY error_category
ORDER BY total DESC;
```

## Retry Mechanism

Agent tu dong retry loi TRANSIENT toi da 3 lan.

### Kiem tra trang thai retry trong DB:
```sql
-- Xem cac job dang duoc retry
SELECT job_name, batch_id, retry_count, retry_status, last_retry_at, error_category
FROM agent_log.diagnosis_log
WHERE retry_eligible = true
ORDER BY processed_at DESC LIMIT 20;

-- Job bi het retry (can DE xu ly thu cong):
SELECT job_name, batch_id, error_message_raw, llm_root_cause, llm_suggested_steps
FROM agent_log.diagnosis_log
WHERE retry_status = 'MAX_REACHED'
ORDER BY processed_at DESC;

-- Ti le retry thanh cong:
SELECT
	COUNT(*) FILTER (WHERE retry_status = 'TRIGGERED') as triggered,
	COUNT(*) FILTER (WHERE retry_status = 'SUCCESS')   as success,
	COUNT(*) FILTER (WHERE retry_status = 'MAX_REACHED') as max_reached
FROM agent_log.diagnosis_log
WHERE retry_eligible = true
	AND processed_at > NOW() - INTERVAL '7 days';
```

### Khi can disable retry khan cap:
```bash
# Windows PowerShell
$env:RETRY_ENABLED="false"
python agents/agent-1-error-diagnosis/run.py --loop

# Linux/macOS
RETRY_ENABLED=false python agents/agent-1-error-diagnosis/run.py --loop
```

### Khi NiFi Luong 3 processor ID thay doi:
1. NiFi UI -> click GenerateFlowFile Luong 3 -> Copy ID
2. Cap nhat NIFI_LUONG3_PROCESSOR_ID trong .env
3. Khoi dong lai agent
