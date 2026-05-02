---
description: 직전에 만든 <slug>-requirements.md를 받아 기술 설계 대화를 진행하고 <slug>-tech-design.md를 작성합니다.
---

# /design

이 커맨드는 `designing-direction` skill을 invoke 합니다.

전제: 동일한 피처 폴더에 `<slug>-requirements.md`가 이미 존재해야 합니다 (없으면 `/brainstorm` 먼저).

산출물:
- `docs/features/<날짜>-<slug>/<slug>-tech-design.md`
- 메인 에이전트 검증 보고서 (대화로 출력, Phase 2 이후 활성)

다음 단계: `/write-plan`
