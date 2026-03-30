# PRODUCTION CHECKLIST -- Agent 1: Truoc khi go-live

## Phan 1: Moi truong (Infrastructure)

  [ ] PostgreSQL: user ETL co quyen SELECT a_etl_monitor.etl_job_log
  [ ] PostgreSQL: user ETL co quyen INSERT/SELECT agent_log.diagnosis_log
  [ ] PostgreSQL: bang diagnosis_log da co 4 cot moi:
      source, alert_identifier, last_alert_at, severity
      (Chay ALTER TABLE trong ARCHITECTURE.md neu chua co)
  [ ] NiFi: Luong 3 processor ID da duoc xac nhan chinh xac
  [ ] NiFi: NIFI_LUONG3_PROCESSOR_ID trong .env khop voi NiFi UI
  [ ] Teams: Webhook URL con hieu luc (test bang curl)
  [ ] LLM: API key hop le, endpoint kha dung, test goi thu thanh cong

## Phan 2: Cau hinh (Configuration)

  [ ] .env day du 12 bien bat buoc (xem RUNBOOK.md muc 2)
  [ ] MAX_RETRIES duoc set theo nhu cau thuc te (khong phai gia tri test)
  [ ] CONFIRMED_NEW_FAILURE_MINUTES >= thoi gian chay nhanh nhat cua job + 1p buffer
  [ ] FALLBACK_DELAY_MINUTES > CONFIRMED_NEW_FAILURE_MINUTES
  [ ] PG_POLL_INTERVAL_SECONDS phu hop voi tan suat job (de nghi: 60-300s)

## Phan 3: Kiem tra ket noi (Health Check)

  [ ] Chay: python agent_1_main.py --health-check
      Ket qua: PostgreSQL OK | NiFi OK | Teams OK
  [ ] Query DB xac nhan timezone dung:
      SELECT NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh';
      Ket qua phai khop voi gio VN hien tai

## Phan 4: Dry run cuoi cung

  [ ] Insert 1 loi TRANSIENT test vao etl_job_log
  [ ] Chay: python agent_1_main.py --dry-run
  [ ] Log hien thi: classify TRANSIENT, would retry, would alert
  [ ] Xoa row test: DELETE FROM a_etl_monitor.etl_job_log WHERE job_name='verify.%'

## Phan 5: Go-live

  [ ] Chay production: python agent_1_main.py (hoac setup systemd/docker)
  [ ] Mo Teams channel, xac nhan nhan duoc card test dau tien
  [ ] Theo doi log 30 phut dau: khong co ERROR-level log bat thuong
  [ ] Confirm NiFi Luong 3 co FlowFile khi TRANSIENT job fail
  [ ] Thong bao cho team: agent da hoat dong, mo ta cach doc card

## Phan 6: Rollback plan

  Neu co van de nghiem trong:
  1. Tat agent: Ctrl+C hoac systemctl stop agent2
  2. Tat retry: RETRY_ENABLED=false trong .env
  3. Giu alert chay: agent van poll va gui Teams, chi tat retry
  4. Debug: xem diagnosis_log + agent2.log
  5. Fix xong: bat lai RETRY_ENABLED=true, restart agent
