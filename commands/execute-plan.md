---
description: <slug>-implementation-plan.md를 task-by-task로 실행합니다. 매 코드 변경마다 위험 주석 자동 부착 + 변경 전·후 코드를 변경이력에 보존합니다.
---

# /execute-plan

이 커맨드는 `executing-plans` skill을 invoke 합니다.

전제: 동일 피처 폴더에 `<slug>-implementation-plan.md` 존재.

자동 동작:
- 각 코드 변경 전 before snapshot 캡처
- risk-annotation 6-체크리스트 → 필요 시 `# ⚠️ RISK(...)` 주석 자동 부착
- 매 task 완료 후 <slug>-implementation-plan.md 변경이력에 [코드-수정] entry 추가 (변경 전·후 코드 풀 블록)
- frequent commits (git 미초기화 시 commit step skip)

다음 단계 (선택): `/api-test`
