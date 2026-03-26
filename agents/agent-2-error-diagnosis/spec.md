# Agent 2 — Error Diagnosis — Detailed Spec

> Đây là tài liệu chính để kiểm soát chất lượng agent.
> DE review + approve trước khi bắt đầu code.

## Status: DRAFT — chờ review

## 1. Scope
[Xem docs/agent-2-error-diagnosis-spec.md]

## 2. Checklist trước khi code
- [ ] Scope được approve bởi DE Lead
- [ ] Input/Output schema được confirm
- [ ] Pseudo logic được review
- [ ] Test cases >= 10 case đã được sign-off
- [ ] Prompt template được duyệt

## 3. Next Step
Sau khi checklist trên hoàn tất:
1. Gửi spec này cho AI Copilot với lệnh: "Implement Agent 2 theo spec này"
2. Run test cases trong tests/unit/
3. Deploy DEV -> UAT -> PROD
