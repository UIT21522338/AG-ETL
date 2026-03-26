# ETL NiFi Multi-Agent System

## Tổng quan
Hệ thống 7 AI Agent hỗ trợ vận hành ETL NiFi với PostgreSQL.

## Cấu trúc
- `docs/` — Tài liệu spec toàn bộ agent
- `config/` — Config theo môi trường (DEV/UAT/PROD)
- `shared/` — Shared clients (NiFi, PostgreSQL, LLM, Logging)
- `orchestrator/` — Event router + API webhook
- `agents/` — Implementation từng agent
- `ops/` — Runbooks, dashboards, deploy scripts

## Quick Start
```bash
cp .env.example .env
# Điền giá trị thực vào .env
pip install -r requirements.txt
# Run tests
pytest agents/agent-2-error-diagnosis/tests/ -v
# Run orchestrator
uvicorn orchestrator.api.http_endpoint:app --reload
```

## Agent Status
| Agent | Status |
|-------|--------|
| Agent 0 — ETL Jobs Map | PLACEHOLDER |
| Agent 1 — Monitoring | PLACEHOLDER |
| Agent 2 — Error Diagnosis | IN PROGRESS |
| Agent 3 — Data Quality | PLACEHOLDER |
| Agent 5 — Dependency | PLACEHOLDER |
| Agent 6 — ChatOps | PLACEHOLDER |
| Agent 7 — NiFi Config | PLACEHOLDER |

## Quy trình phát triển
Xem: `docs/test-strategy-and-qa-process.md`
