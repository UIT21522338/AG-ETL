# Agent 1 -- Error Diagnosis & Auto-Recovery

Tu dong phat hien loi ETL, phan loai bang LLM, retry neu TRANSIENT, alert Teams.

## Chay nhanh
  cp .env.example .env  # dien day du bien
  python src/agent_1_main.py --health-check  # kiem tra ket noi
  python src/agent_1_main.py --dry-run       # test khong gui that
  python src/agent_1_main.py                 # chay that su

## Tai lieu
  docs/ARCHITECTURE.md       -- Kien truc, flow, schema
  docs/RULES.md              -- Toan bo rule logic, bien env
  docs/RUNBOOK.md            -- Cach chay, lenh, troubleshoot
  docs/TEST_CASES.md         -- Tat ca test case
  docs/USER_GUIDE.md         -- Huong dan doc card, xu ly thu cong
  docs/PRODUCTION_CHECKLIST.md -- Checklist truoc khi go-live

## Chay test
  pytest tests/unit/ -v                # unit test (khong can DB that)
  pytest tests/integration/ -v --env=dev  # integration test (can DB)

## Hai quyet dinh chinh
  TRANSIENT     -> Retry tu dong (NiFi Luong 3) + Alert Teams
  NON_TRANSIENT -> Chi Alert Teams, can xu ly thu cong
