# Agent 2 User Guide

Huong dan nay giup ban cau hinh va test thuc te Agent 2 (Error Diagnosis) voi PostgreSQL, NiFi va Microsoft Teams.

## 1. Muc tieu

Ban se hoan tat:
- Cau hinh tham so ket noi PostgreSQL, NiFi, LLM, Teams.
- Xac nhan poller doc duoc loi tu PostgreSQL va NiFi.
- Xac nhan classify + LLM analysis + Teams alert hoat dong.
- Chay test end-to-end an toan tren DEV.

## 2. Dieu kien tien quyet

Can co san:
- Python 3.11+ va virtual environment da kich hoat.
- Quyen truy cap PostgreSQL (schema a_etl_monitor va agent_log).
- Quyen truy cap NiFi API (Bulletin Board).
- Teams Incoming Webhook URL hop le.
- LLM endpoint + API key hop le.

## 3. Cau hinh bien moi truong (.env)

Cap nhat file .env tai root project dua tren .env.example.

Gia tri can dien:
- PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
- NIFI_BASE_URL, NIFI_USERNAME, NIFI_PASSWORD
- LLM_API_URL, LLM_API_KEY, LLM_MODEL
- TEAMS_WEBHOOK_URL
- AGENT_ENVIRONMENT

Mau:

```env
PG_HOST=your_pg_host
PG_PORT=5432
PG_DATABASE=your_db
PG_USER=your_user
PG_PASSWORD=your_password

NIFI_BASE_URL=http://your-nifi-host:8080
NIFI_USERNAME=your_nifi_user
NIFI_PASSWORD=your_nifi_password

LLM_API_URL=https://your-llm-endpoint/v1/chat/completions
LLM_API_KEY=your_llm_api_key
LLM_MODEL=gpt-4o

TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
AGENT_ENVIRONMENT=DEV
```

Luu y:
- Khong commit file .env len git.
- Neu AGENT_ENVIRONMENT = DEV thi nen su dung database va NiFi cua DEV.

## 4. Cau hinh file YAML

### 4.1 Moi truong

File:
- config/environments/dev.yaml
- config/environments/uat.yaml
- config/environments/prod.yaml

Doi voi DEV, dam bao:
- environment: DEV
- agent_2.pg_schema_etl_log: a_etl_monitor
- agent_2.pg_table_job_log: etl_job_log
- agent_2.max_errors_per_run: gia tri phu hop (vd 50)

### 4.2 Agent 2

File:
- config/agents/agent-2-error-diagnosis.yaml

Dam bao:
- phase: PHASE_1
- notify.on_error = true
- notify.on_unknown = true
- log_table = agent_log.diagnosis_log

## 5. Chuan bi PostgreSQL

### 5.1 Tao bang log cho Agent 2

Chay script:
- agents/agent-2-error-diagnosis/sql/setup_guide.sql

Script nay tao:
- schema agent_log
- table agent_log.diagnosis_log
- cac index can thiet

### 5.2 Kiem tra bang log nguon ETL

PG poller doc tu:
- a_etl_monitor.etl_job_log

Can co cac cot (toi thieu) de query:
- log_id, batch_id, tenant_code, project_version, job_id, job_name
- start_time, end_time, status, rows_read, rows_written, error_message
- job_group, layer, flow_version, from_date, to_date

## 6. Chuan bi NiFi

### 6.1 Bat bulletin level can theo doi

Agent loc bulletin voi level:
- ERROR
- WARNING

Dam bao NiFi dang tao bulletin o 2 level nay khi flow gap su co.

### 6.2 Kiem tra API tu may chay agent

Can goi duoc endpoint:
- GET /nifi-api/flow/bulletin-board

Tu base URL da khai bao trong NIFI_BASE_URL.

## 7. Chuan bi Teams

- Tao Incoming Webhook trong channel Teams can nhan canh bao.
- Gan URL vao TEAMS_WEBHOOK_URL.
- Dam bao webhook cho phep post JSON payload.

## 8. Cai dependencies

Tu root project chay:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 9. Test thuc te tung thanh phan

## 9.1 Test ket noi PostgreSQL + PG poller

```python
from dotenv import load_dotenv
load_dotenv()

from shared.db.pg_client import PGClient
from agents.agent_2_error_diagnosis.src.pg_poller import poll_pg_errors

pg = PGClient()
pg.connect()
errors = poll_pg_errors(pg, {
    "pg_schema_etl_log": "a_etl_monitor",
    "pg_table_job_log": "etl_job_log",
    "max_errors_per_run": 10,
    "environment": "DEV"
})
print(f"PG errors found: {len(errors)}")
if errors:
    print(errors[0])
pg.close()
```

Ket qua mong doi:
- Khong exception.
- Tra ve list (co the rong neu khong co loi failed).

## 9.2 Test ket noi NiFi + NiFi poller

```python
from dotenv import load_dotenv
load_dotenv()

from shared.nifi.nifi_client import NiFiClient
from agents.agent_2_error_diagnosis.src.nifi_poller import poll_nifi_bulletins

nifi = NiFiClient()
errors = poll_nifi_bulletins(nifi, {"environment": "DEV"}, processed_ids=set())
print(f"NiFi bulletins found: {len(errors)}")
if errors:
    print(errors[0])
```

Ket qua mong doi:
- Khong exception.
- Tra ve list da normalize, source = nifi_bulletin.

## 9.3 Test classifier + LLM analyzer

```python
import json
from agents.agent_2_error_diagnosis.src.classifier import classify_error
from agents.agent_2_error_diagnosis.src.llm_analyzer import get_llm_solution

error = {
    "job_name": "bronze.OM_SalesOrd",
    "layer": "bronze",
    "environment": "DEV",
    "error_message": "null value in column 'customer_id' violates not-null constraint",
    "rows_read": 1234,
    "rows_written": 0,
    "end_time": "2025-09-08T00:10:05"
}
classification = classify_error(error["error_message"])
result = get_llm_solution({**error, **classification})
print(json.dumps(result, ensure_ascii=False, indent=2))
```

Checklist:
- Co dung 5 field: root_cause_summary, suggested_steps, severity, estimated_fix_time, escalate_to_de_lead
- suggested_steps la list
- severity nam trong LOW/MEDIUM/HIGH/CRITICAL

## 9.4 Test Teams card

```python
import os
from dotenv import load_dotenv
load_dotenv()

from agents.agent_2_error_diagnosis.src.teams_notifier import build_teams_message, send_teams_alert

error_info = {
    "tenant_code": "FES",
    "job_id": 101,
    "layer": "bronze",
    "environment": "DEV",
    "batch_id": "20250907123000",
    "end_time": "2025-09-08T00:10:05",
    "error_message": "null value in column 'customer_id' violates not-null constraint",
    "rows_read": 1234,
    "rows_written": 0,
    "job_name": "bronze.OM_SalesOrd"
}
classification = {
    "error_category": "DATA_QUALITY",
    "matched_keyword": "null value in column",
    "classification_method": "rule_based"
}
llm_solution = {
    "root_cause_summary": "Du lieu nguon bi NULL customer_id.",
    "suggested_steps": ["Kiem tra du lieu nguon", "Them bo loc NULL trong NiFi", "Thong bao team nguon"],
    "severity": "HIGH",
    "estimated_fix_time": "30-60 phut",
    "escalate_to_de_lead": False
}

msg = build_teams_message(error_info, classification, llm_solution)
sent = send_teams_alert(msg, os.getenv("TEAMS_WEBHOOK_URL"))
print(f"Teams sent: {sent}")
```

Ket qua mong doi:
- sent = True
- Teams channel nhan card day du thong tin.

## 10. Test end-to-end thuc te tren PostgreSQL va NiFi

Khuyen nghi test tren DEV theo thu tu:

1. Tao 1 ban ghi failed test trong a_etl_monitor.etl_job_log.
2. Tao 1 bulletin ERROR/WARNING trong NiFi (co the dung 1 processor co cau hinh sai tam thoi tren DEV).
3. Chay poller PG va NiFi de xac nhan lay duoc 2 loi mau.
4. Chay classify_error cho tung error_message.
5. Chay get_llm_solution voi du lieu da classify.
6. Build Teams card va gui webhook.
7. Kiem tra channel Teams.
8. (Neu co logger ghi diagnosis) xac nhan du lieu vao agent_log.diagnosis_log.

## 11. SQL mau de tao du lieu failed test tren PostgreSQL

Chi test tren DEV:

```sql
INSERT INTO a_etl_monitor.etl_job_log (
    log_id, batch_id, tenant_code, project_version, job_id, job_name,
    start_time, end_time, status, rows_read, rows_written, error_message,
    job_group, layer, flow_version, from_date, to_date
)
VALUES (
    999001, '20260325170000', 'FES', '1.0.0', 101, 'bronze.OM_SalesOrd',
    NOW() - INTERVAL '1 minute', NOW(), 'failed', 1234, 0,
    'connection timeout to PostgreSQL host=db-dev port=5432 after 30s',
    'daily', 'bronze', '1.0.0', NULL, NULL
);
```

Sau khi test xong co the xoa ban ghi test:

```sql
DELETE FROM a_etl_monitor.etl_job_log WHERE log_id = 999001;
```

## 12. Su co thuong gap va cach xu ly nhanh

- Loi ket noi PG (timeout/refused):
  - Kiem tra PG_HOST/PG_PORT/firewall/user/password.
- NiFi API 401/403:
  - Kiem tra NIFI_USERNAME/NIFI_PASSWORD va quyen user.
- LLM phan tich tra fallback:
  - Kiem tra LLM_API_URL, LLM_API_KEY, model va outbound network.
- Teams sent = False:
  - Kiem tra webhook URL, policy Teams va Internet egress.
- Poller tra ve rong:
  - Kiem tra du lieu co status = 'failed', dedup logic, va max_errors_per_run.

## 13. Danh sach file lien quan

- shared/db/pg_client.py
- shared/nifi/nifi_client.py
- shared/llm/copilot_client.py
- agents/agent-2-error-diagnosis/src/pg_poller.py
- agents/agent-2-error-diagnosis/src/nifi_poller.py
- agents/agent-2-error-diagnosis/src/classifier.py
- agents/agent-2-error-diagnosis/src/llm_analyzer.py
- agents/agent-2-error-diagnosis/src/teams_notifier.py
- agents/agent-2-error-diagnosis/prompts/system-prompt.md
- agents/agent-2-error-diagnosis/prompts/examples.md
- agents/agent-2-error-diagnosis/sql/setup_guide.sql
- config/environments/dev.yaml
- config/agents/agent-2-error-diagnosis.yaml
