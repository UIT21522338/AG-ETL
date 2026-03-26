# Agent Governance Model

## Allowlist Level Definition
| Level | Mô tả | Ví dụ hành động |
|-------|-------|----------------|
| L1 | Alert only — không action | Gửi Teams alert, ghi log |
| L2 | Action sau human confirm | Rerun job sau khi DE bấm confirm |
| L3 | Auto action trong phạm vi whitelist | Auto-retry transient error DEV/UAT |

## Nguyên tắc
- PROD mặc định tối đa L2 (cần confirm)
- DEV/UAT có thể cho L3 với lỗi transient đã được allowlist
- Mọi action đều phải log đầy đủ vào PostgreSQL
- Escalate lên DE team nếu agent không tự xử lý được
