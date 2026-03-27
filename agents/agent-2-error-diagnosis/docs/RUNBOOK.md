# RUNBOOK -- Agent 2: Cach chay va xu ly su co

## 1. Cac che do chay

### 1.1 Chay binh thuong (production mode)
  python agents/agent-2-error-diagnosis/src/agent_2_main.py

  Hieu qua: Bat dau polling loop, cu N giay quet 1 lan,
  phat hien loi moi, phan loai, retry/alert tu dong, ghi log.
  Chay mai mai cho den khi Ctrl+C.

### 1.2 Chay 1 lan duy nhat (manual trigger)
  python agents/agent-2-error-diagnosis/src/agent_2_main.py --once

  Hieu qua: Quet 1 lan roi thoat. Dung de test hoac chay theo cron.

### 1.3 Dry run (kiem tra logic, khong gui Teams, khong trigger NiFi)
  python agents/agent-2-error-diagnosis/src/agent_2_main.py --dry-run

  Hieu qua: Phan loai loi, hien thi ket qua ra log,
  KHONG gui Teams, KHONG trigger NiFi Luong 3, KHONG ghi diagnosis_log.
  Dung de verify logic truoc khi deploy len moi truong moi.

### 1.4 Test ket noi (khong xu ly loi, chi kiem tra kha nang ket noi)
  python agents/agent-2-error-diagnosis/src/agent_2_main.py --health-check

  Kiem tra: PostgreSQL ping, NiFi API ping, Teams webhook ping.
  Exit 0 neu tat ca OK, exit 1 neu bat ky thu nao fail.

## 2. Bien moi truong bat buoc

  # PostgreSQL
  PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD

  # NiFi
  NIFI_BASE_URL            : https://nifi-host:8443
  NIFI_USERNAME, NIFI_PASSWORD
  NIFI_LUONG3_PROCESSOR_ID : ID processor GenerateFlowFile cua Luong 3

  # Teams
  TEAMS_WEBHOOK_URL        : Incoming Webhook URL cua channel ETL Alert

  # LLM
  OPENAI_API_KEY hoac LLM_ENDPOINT + LLM_API_KEY

  # Retry
  RETRY_ENABLED=true
  MAX_RETRIES=3
  CONFIRMED_NEW_FAILURE_MINUTES=2
  FALLBACK_DELAY_MINUTES=5
  MAX_RETRY_WINDOW_MINUTES=50

## 3. Xem log

  # Log terminal real-time
  python agents/agent-2-error-diagnosis/src/agent_2_main.py 2>&1 | tee agent2.log

  # Query DB xem ket qua gan nhat
  SELECT diagnosis_id, TO_CHAR(processed_at,'HH24:MI:SS') as time,
    job_name, error_category, retry_count, retry_status, teams_alert_sent
  FROM agent_log.diagnosis_log
  ORDER BY diagnosis_id DESC LIMIT 20;

## 4. Thay doi MAX_RETRIES khi dang chay

  # Khong can restart agent (neu agent doc .env moi poll cycle)
  # Sua .env:
  MAX_RETRIES=5

  # Hoac set environment variable ngay:
  export MAX_RETRIES=5
  # Agent se doc gia tri moi o poll cycle tiep theo

## 5. Troubleshoot nhanh

  Van de: Teams khong nhan duoc card
    -> Kiem tra TEAMS_WEBHOOK_URL con hieu luc: curl -X POST $TEAMS_WEBHOOK_URL -H 'Content-Type: application/json' -d '{"text":"test"}'
    -> Kiem tra log: grep 'Teams alert' agent2.log | tail -20
    -> Kiem tra dedup: co the bi ALERT SKIP do chay truoc do roi

  Van de: NiFi khong co FlowFile sau retry
    -> Kiem tra NIFI_LUONG3_PROCESSOR_ID dung chua: grep NIFI_LUONG3 .env
    -> Kiem tra log: grep 'Luong3' agent2.log | tail -20
    -> Thu manual: python -c "from shared.nifi.nifi_client import NiFiClient; ..."

  Van de: LLM classify sai hoac tra ve LOW confidence
    -> Xem raw_response trong diagnosis_log:
       SELECT llm_solution FROM agent_log.diagnosis_log ORDER BY diagnosis_id DESC LIMIT 5;
    -> Neu LLM hay fail: kiem tra API key va endpoint

  Van de: Log cu bi lay lai (timestamp lech)
    -> Kiem tra: SELECT NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh', end_time FROM a_etl_monitor.etl_job_log ORDER BY log_id DESC LIMIT 3;
    -> Hai gia tri phai gan nhau (khong lech 7h)
    -> Neu lech: NiFi dang insert bang NOW() khong co AT TIME ZONE
