# RULES -- Agent 1: Toan bo logic va bien cau hinh

## 1. Phan loai loi (classifier.py)

### 1.1 Phuong phap: LLM (khong dung keyword)
LLM nhan: job_name, layer, source, rows_read, rows_written, error_message
LLM tra ve JSON 1 lan duy nhat, gom ca phan loai lan giai phap.

### 1.2 Hai loai chinh
| retry_category | Dieu kien LLM ket luan | Hanh dong |
|----------------|------------------------|-----------|
| TRANSIENT | Loi tam thoi, co the tu phuc hoi | Retry + Alert |
| NON_TRANSIENT | Can can thiep thu cong | Chi Alert |

### 1.3 Sub-category
TRANSIENT    : CONNECTION_TIMEOUT, TOO_MANY_CONNECTIONS, DEADLOCK,
               QUERY_TIMEOUT, DB_STARTING, NETWORK_RESET
NON_TRANSIENT: DATA_QUALITY, CONFIGURATION, SOURCE_UNAVAILABLE,
               RESOURCE, UNKNOWN

### 1.4 Fallback khi LLM fail
- retry_category = NON_TRANSIENT (an toan, khong retry)
- sub_category   = UNKNOWN
- confidence     = LOW
- suggested_steps = 3 buoc mac dinh
- Pipeline van chay, chi alert Teams

### 1.5 Confidence
- LOW + is_retryable = True: neu LOW_CONFIDENCE_RETRY=false -> khong retry
- Cau hinh qua bien LOW_CONFIDENCE_RETRY trong .env

## 2. Retry logic

### 2.1 Dieu kien de retry (phai thoa man TAT CA):
  [1] LLM phan loai TRANSIENT (is_retryable = True)
  [2] source = 'pg_log'  (Bulletin Board khong bao gio retry)
  [3] RETRY_ENABLED = true trong .env
  [4] retry_count < MAX_RETRIES
  [5] end_time cua loi con trong MAX_RETRY_WINDOW_MINUTES
  [6] check_retry_state() xac nhan day la loi MOI (khong phai dup)

### 2.2 Bien cau hinh retry (doc tu .env truoc, YAML la fallback)

| Bien .env | YAML key | Mac dinh | Giai thich |
|-----------|----------|----------|------------|
| RETRY_ENABLED | retry.enabled | true | Bat/tat retry toan cuc |
| MAX_RETRIES | retry.max_retries | 3 | So lan retry toi da, thay .env khong can deploy |
| CONFIRMED_NEW_FAILURE_MINUTES | retry.confirmed_new_failure_minutes | 2 | Nguong xac nhan loi moi (luong chinh) |
| FALLBACK_DELAY_MINUTES | retry.fallback_delay_minutes | 5 | Nguong fallback khi timestamp loi |
| MAX_RETRY_WINDOW_MINUTES | retry.max_retry_window_minutes | 50 | Tong thoi gian retry window |
| LOW_CONFIDENCE_RETRY | classifier.low_confidence_retry | false | Retry khi LLM confidence=LOW |

### 2.3 Cay quyet dinh dedup retry (check_retry_state)

  Chua co record trong window      -> RETRY (loi moi)
  Co record, co timestamp:
    end_time > last_retry + CONFIRMED_NEW_FAILURE_MINUTES  -> RETRY (loi moi)
    end_time <= last_retry + CONFIRMED_NEW_FAILURE_MINUTES -> SKIP  (dup)
  Co record, khong co timestamp (fallback):
    elapsed >= FALLBACK_DELAY_MINUTES  -> RETRY
    elapsed <  FALLBACK_DELAY_MINUTES  -> SKIP  (dup)

## 3. Alert / Dedup Teams (alert_dedup.py)

### 3.1 Nguon va dedup key
| Nguon | Dedup key | Retry |
|-------|-----------|-------|
| NiFi Bulletin Board | bulletin_id | Khong |
| PostgreSQL Job Log | {job_id}_{batch_id} | Co (neu TRANSIENT) |

### 3.2 Cay quyet dinh dedup alert (check_alert_state)
Tuong tu check_retry_state nhung doc lap -- dedup alert != dedup retry.

### 3.3 Quy tac gui 1 lan
- Loi dup (cung job+batch, end_time gan): SKIP, khong gui Teams
- Loi co retry: cap nhat so lan retry tren cung 1 identifier,
  chi gui card moi khi la failure_round moi (qua CONFIRMED_NEW_FAILURE_MINUTES)

## 4. Teams card -- noi dung bat buoc

CHUNG (ca 2 nguon):
  Dong 1: [ID] Job ID / Processor ID (noi bat, dong dau tien)
  Dong 2: Job Name / Processor Name
  Dong 3: Nguon, Nhom loi, Muc do, Thoi gian, Retry status
  Dong cuoi: Root Cause (LLM), LLM Steps (3 buoc), Error Detail (nguyen ven)

BULLETIN BOARD them: Processor ID, Processor Name, Node
PG LOG them: Batch ID, Tenant, Layer, Rows Read, Rows Written

LLM Steps KHONG BAO GIO TRONG:
  - Neu LLM tra ve steps -> dung steps cua LLM
  - Neu LLM fail -> dung DEFAULT_STEPS[category] (3 buoc mac dinh theo nhom)

## 5. Timezone
- DB luu timestamp gio VN (UTC+7, naive, khong co tzinfo)
- NiFi insert dung: NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh'
- Python so sanh dung: datetime.now()  (khong co timezone.utc)
- SQL so sanh dung: NOW() AT TIME ZONE 'Asia/Ho_Chi_Minh' - INTERVAL 'N minutes'
- KHONG dung datetime.now(timezone.utc) o bat ky dau trong agent nay
