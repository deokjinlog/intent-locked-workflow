---
description: 구현된 API에 대해 자동 테스트를 진행합니다. 메인이 SQL을 안내하고, 사용자가 결과를 paste 하면 pytest 시나리오를 생성·실행합니다.
---

# /api-test

이 슬래시는 `api-auto-testing` skill 을 호출합니다.

전제: 동일 피처 폴더에 `<slug>-implementation-plan.md` 가 있고, 코드 구현이 완료되어 있어야 합니다 (즉 `/executing-plans` 이 끝난 상태).

흐름:
1. API 인벤토리를 추출합니다.
2. 메인이 테스트 데이터 SQL 을 제시하면 사용자가 결과를 paste 합니다.
3. 시나리오 코드를 자동으로 생성합니다 (auth 패턴 자동 감지).
4. pytest 를 실행하고 JSON 결과를 받습니다.
5. `<slug>-implementation-plan.md` 의 변경이력에 `[API테스트]` entry 를 누적합니다.
6. 실패 시 재실행을 제안합니다.

산출물:
- `docs/features/<날짜>-<slug>/api-tests/scenario-*.py`
- `docs/features/<날짜>-<slug>/api-tests/conftest.py`
- `docs/features/<날짜>-<slug>/api-tests/results/<timestamp>.json`
- <slug>-implementation-plan.md 변경이력 [API테스트] entry
