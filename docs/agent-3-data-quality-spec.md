# Agent 3 — Data Quality Specification

## Scope
- Kiểm tra data quality sau mỗi ETL job
- L1: warn + report
- L2 (Target): block pipeline với confirm từ DE

## Level
- Go-live: L1
- Target 6T: L2

## Out of scope
- Không L3 trong giai đoạn này

## Checks
- Null/blank fields trong critical columns
- Duplicate primary keys
- Row count deviation > threshold
- Data type mismatch
