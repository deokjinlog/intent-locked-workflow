---
description: <slug>-requirements.md + <slug>-tech-design.md를 기반으로 <slug>-implementation-plan.md(단계별 TDD plan)를 작성합니다.
---

# /write-plan

이 커맨드는 `writing-plans` skill을 invoke 합니다.

전제: 동일한 피처 폴더에 `<slug>-requirements.md` AND `<slug>-tech-design.md`가 모두 존재.

산출물:
- `docs/features/<날짜>-<slug>/<slug>-implementation-plan.md`
- 메인 에이전트 검증 보고서 (대화로 출력, Phase 2 이후 활성)

다음 단계: `/execute-plan`
