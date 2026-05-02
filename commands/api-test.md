---
description: 구현된 API에 대해 자동 테스트를 진행합니다. 메인이 SQL을 안내하고, 사용자가 결과를 paste 하면 pytest 시나리오를 생성·실행합니다.
---

# /api-test

이 커맨드는 `api-auto-testing` skill을 invoke 합니다.

전제: 동일 피처 폴더에 `<slug>-implementation-plan.md` 존재 + 코드 구현 완료 (`/execute-plan` 끝).

흐름:
1. API 인벤토리 추출
2. 메인이 테스트 데이터 SQL 제시 → 사용자가 paste
3. 시나리오 코드 자동 생성 (auth 패턴 자동 감지)
4. pytest 실행 → JSON 결과
5. <slug>-implementation-plan.md 변경이력에 [API테스트] entry 누적
6. 실패 시 재실행 제안

산출물:
- `docs/features/<날짜>-<slug>/api-tests/scenario-*.py`
- `docs/features/<날짜>-<slug>/api-tests/conftest.py`
- `docs/features/<날짜>-<slug>/api-tests/results/<timestamp>.json`
- <slug>-implementation-plan.md 변경이력 [API테스트] entry
