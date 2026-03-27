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

## Agent 2 Retry Timing (Phase 2)

Agent 2 su dung 2 bien retry rieng biet de tranh nham lan:

- `CONFIRMED_NEW_FAILURE_MINUTES`:
	nguong xac nhan loi moi that su sau retry, so sanh `error_end_time` voi
	`last_retry_at + N phut`.
- `FALLBACK_DELAY_MINUTES`:
	nguong du phong chi dung khi timestamp bi null/parse loi, so sanh
	`now - last_retry_at`.

Gia tri mac dinh:

- `CONFIRMED_NEW_FAILURE_MINUTES=2`
- `FALLBACK_DELAY_MINUTES=5`

Khuyen nghi dat gia tri theo toc do Bronze:

1. Do `min` thoi gian Bronze trong 30 ngay.
2. Dat `CONFIRMED_NEW_FAILURE_MINUTES = min + 1`.
3. Dat `FALLBACK_DELAY_MINUTES = confirmed + 1`.
