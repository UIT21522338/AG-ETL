# Test Strategy & QA Process

## Triết lý: Spec trước, Code sau
1. Viết spec.md (scope, IO, pseudo logic) → DE review + approve
2. Thiết kế test cases trong spec → DE sign-off
3. Viết prompt template → review
4. Copilot generate code
5. Run test cases → pass 100% mới merge
6. Deploy DEV → UAT → PROD

## Test Pyramid
- 70% Unit tests (classifier, retry_policy)
- 20% Integration tests (NiFi API, PostgreSQL)
- 10% E2E tests (full flow)

## Inspection Checklist (không cần đọc code)
- [ ] spec.md đã được approve chưa?
- [ ] Test cases trong spec.md đã đủ chưa? (tối thiểu 10)
- [ ] Pseudo logic có khớp test cases không?
- [ ] Log vào PostgreSQL có đủ field không?
- [ ] Alert Teams có trigger đúng condition không?
- [ ] Auto-action có nằm trong allowlist không?
