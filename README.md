# AG-ETL — AI Agent Platform for ETL Pipelines

> Repo: https://github.com/UIT21522338/AG-ETL

He thong 6 AI Agent tu dong hoa vận hành ETL Pipeline tren Apache NiFi + PostgreSQL.

## Danh sach Agent

| # | Agent | Trang thai | Mo ta ngan |
|---|-------|-----------|------------|
| **1** | [Error Diagnosis & Auto-Recovery](agents/agent-1-error-diagnosis/) | ✅ Done | Phat hien loi, LLM phan loai, retry TRANSIENT, alert Teams |
| **2** | [Superset RBAC](agents/agent-2-superset-rbac/) | 🔲 Todo | Phan quyen Superset tu dong theo role + scope |
| **3** | [NiFi Controller Config Bot](agents/agent-3-nifi-controller/) | 🔲 Todo | Tu dong cau hinh NiFi Controller Service |
| **4** | [Monitoring & Anomaly Detection](agents/agent-4-monitoring/) | 🔲 Todo | Rule/Statistical baseline, canh bao bat thuong |
| **5** | [Data Quality Validation](agents/agent-5-data-quality/) | 🔲 Todo | Kiem tra chat luong du lieu theo quy tac |
| **6** | [Transfer Data to Insight](agents/agent-6-transfer-insight/) | 🔲 Todo | Chuyen du lieu len tang Insight |

## Cau truc repo

```
AG-ETL/
|-- agents/
|   |-- agent-1-error-diagnosis/   # Done — xem docs/ ben trong
|   |-- agent-2-superset-rbac/
|   |-- agent-3-nifi-controller/
|   |-- agent-4-monitoring/
|   |-- agent-5-data-quality/
|   |-- agent-6-transfer-insight/
|-- config/
|   |-- agents/                    # YAML config cho tung agent
|   |-- dev.yaml / uat.yaml / prod.yaml
|-- shared/                        # Client dung chung: NiFi, PG, LLM, Logger
|-- orchestrator/                  # Event router, webhook endpoint
|-- ops/                           # Runbook, deploy scripts, metrics
|-- requirements.txt
|-- .env.example
```

## Chay Agent 1 (san sang su dung)

```bash
cd agents/agent-1-error-diagnosis
cp .env.example .env        # dien bien thuc te
python src/agent_1_main.py --health-check  # kiem tra ket noi
python src/agent_1_main.py --dry-run       # test khong gui that
python src/agent_1_main.py                 # chay production
```

## Tai lieu Agent 1

- [Architecture](agents/agent-1-error-diagnosis/docs/ARCHITECTURE.md)
- [Rules & Config](agents/agent-1-error-diagnosis/docs/RULES.md)
- [Runbook](agents/agent-1-error-diagnosis/docs/RUNBOOK.md)
- [Test Cases](agents/agent-1-error-diagnosis/docs/TEST_CASES.md)
- [User Guide](agents/agent-1-error-diagnosis/docs/USER_GUIDE.md)
- [Production Checklist](agents/agent-1-error-diagnosis/docs/PRODUCTION_CHECKLIST.md)
