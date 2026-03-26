# Architecture Overview — ETL NiFi Multi-Agent System

## Mục tiêu
Hệ thống 7 AI Agent hỗ trợ vận hành ETL NiFi tự động hóa theo từng level từ L1 (alert only) đến L3 (full automation).

## Danh sách Agent
| Agent | Tên | Level Go-live | Level Target (6T) |
|-------|-----|--------------|-------------------|
| Agent 0 | ETL Jobs Map | L1–L2 | L1–L2 |
| Agent 1 | Monitoring | L1 | L1 |
| Agent 2 | Error Diagnosis | L1 | L2–3 (DEV/UAT) |
| Agent 3 | Data Quality | L1 | L2 |
| Agent 5 | Dependency | L1 | L1 |
| Agent 6 | ChatOps | L2 | L2 |
| Agent 7 | NiFi Config | L2 | L2 |

## Shared Components
- `shared/nifi/` — NiFi API client
- `shared/db/` — PostgreSQL client
- `shared/llm/` — AI Copilot wrapper
- `shared/logging/` — Logging + correlation ID

## Orchestrator
- `orchestrator/router/` — Route event đến agent phù hợp
- `orchestrator/api/` — Webhook từ NiFi, Teams, ChatOps
