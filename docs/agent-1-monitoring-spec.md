# Agent 1 — Monitoring Specification

## Scope
- Poll NiFi metrics (CPU, memory, flow status, queue depth)
- Gửi alert Teams khi vượt ngưỡng
- KHÔNG auto action

## Level: L1 (Go-live & Target)

## Input
- NiFi API metrics (polling interval: configurable)
- Thresholds từ config/agents/agent-1-monitoring.yaml

## Output
- Teams alert message
- Log entry vào PostgreSQL

## Alert Conditions
- Processor STOPPED unexpectedly
- Queue depth > threshold
- Bulletin ERROR tồn tại
- Flow file backpressure triggered
