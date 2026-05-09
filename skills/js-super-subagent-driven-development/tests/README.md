# js-super-subagent-driven-development tests (v1.1.7)

| Fixture | 검증 대상 | 연결 AC | 자동? |
|---|---|---|---|
| F1-basic-batch | 2-task → consolidated entry 1개 (slim schema) | AC-1, AC-4 | ✅ pytest |
| F2-zero-code-task | 코드 0건 task → [검증] entry | AC-3 | (수동 비교) |
| F3-mode-schema-divergence | per-task vs single 모드 schema 분기 | AC-4 | (수동 비교) |
| F4-interrupt-recovery | 세션 끊긴 후 buffer 잔존 detection | R2 mitigation | ✅ pytest |
| F5-cleanup | consolidator 성공 후 buffer 디렉토리 cleanup | R4 mitigation | (수동 dogfood) |

자동 (pytest) 항목은 `scripts/tests/test_changelog_buffer.py` 의 `test_F1_basic_batch_fixture` 등으로 호출됨. 나머지는 dogfood (I1~I4) 에서 사용자가 직접 비교 검증.
