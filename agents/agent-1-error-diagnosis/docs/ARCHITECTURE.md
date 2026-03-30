# ARCHITECTURE -- Agent 1: Error Diagnosis & Auto-Recovery
Version: 2.0 | Updated: 2026-03-27

## Tong quan
Agent tu dong phat hien loi ETL, dung LLM phan loai, retry neu can, alert Teams.
Chay theo polling interval (cron hoac loop), khong can trigger thu cong.

## Luong xu ly chinh

```
     [NiFi Bulletin Board]      [PostgreSQL etl_job_log]
            |                           |
     nifi_poller.py              pg_poller.py
     (lay bulletin moi)          (lay row status=failed moi)
            |                           |
            +----------+  +-------------+
                       v  v
               agent_1_main.py
               process_single_error(error)
                       |
              [Step 1+2] classifier.py
               classify_and_analyze(error)
               -> LLM tra ve 1 JSON:
                  retry_category: TRANSIENT|NON_TRANSIENT
                  sub_category, severity
                  root_cause, suggested_steps
                  confidence, is_retryable
                       |
              [Step 3] retry logic
              is_retryable AND source=pg_log AND retry enabled?
                  YES              NO
                   |               |
         retry_policy.py      [skip retry]
         should_retry()             |
              |                     |
         ELIGIBLE?                  |
           YES    NO                |
            |      |                |
  retry_executor  skip              |
  check_retry_state()               |
  (dedup retry)                     |
  trigger NiFi Luong 3              |
            |                       |
            +----------+------------+
                       v
              [Step 4] alert_dedup.py
              check_alert_state()
              SHOULD_ALERT?
                YES        NO
                 |          |
       teams_notifier  SKIP (dup)
       build_alert_card()
       send_teams_alert()
                 |
              [Step 5] diagnosis_logger.py
              log_to_diagnosis_log()
              -> agent_log.diagnosis_log
```

## Nguon du lieu input

### Nguon A: NiFi Bulletin Board
- API endpoint: GET /nifi-api/bulletin-board
- Polling interval: moi N giay (cau hinh NIFI_POLL_INTERVAL_SECONDS)
- Dedup key: bulletin_id
- Retry: KHONG (bulletin la canh bao NiFi, khong phai job ETL)

### Nguon B: PostgreSQL etl_job_log
- Bang: a_etl_monitor.etl_job_log
- Dieu kien lay: status = 'failed'
         AND end_time >= NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh' - INTERVAL 'N minutes'
- Timezone: tat ca timestamp trong DB la gio VN (UTC+7, naive, khong co tzinfo)
- Polling: moi N giay (cau hinh PG_POLL_INTERVAL_SECONDS)

## Schema bang etl_job_log (input)

  log_id, batch_id, tenant_code, project_version, job_id, job_name,
  start_time, end_time, status, rows_read, rows_written,
  error_message, job_group, layer, flow_version, from_date, to_date

## Schema bang diagnosis_log (output)

  diagnosis_id, source, alert_identifier, error_category, severity,
  job_id, job_name, batch_id, error_message, retry_eligible,
  retry_count, retry_status, last_retry_at, last_alert_at,
  teams_alert_sent, llm_solution, processed_at

## Modules va nhiem vu

| Module | Nhiem vu duy nhat |
|--------|-------------------|
| agent_1_main.py | Orchestration: goi tung buoc theo thu tu |
| classifier.py | Goi LLM, parse JSON, fallback an toan |
| pg_poller.py | Query DB, tra ve list error dict |
| nifi_poller.py | Goi NiFi API, tra ve list bulletin dict |
| alert_dedup.py | check_alert_state() -- tranh gui Teams trung |
| retry_executor.py | check_retry_state() + trigger NiFi Luong 3 |
| retry_policy.py | should_retry() -- kiem tra max, window |
| teams_notifier.py | build_alert_card() + send_teams_alert() |
| diagnosis_logger.py | log_to_diagnosis_log() -- ghi DB |
