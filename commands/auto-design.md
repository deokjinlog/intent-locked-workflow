---
description: auto-flow 2단계 진입 — requirements.md 있는 상태에서 design 부터 chain 끝까지 자동. 인자 누락 시 latest <slug> 추론.
---

# /auto-design

`<slug>` 인자 optional. 누락 시 `docs/features/` 의 가장 최근 폴더 자동 선택. 이 커맨드는 `auto-designing-direction` skill 을 invoke 합니다.

산출물:
- `<slug>-tech-design.md` (RAW)

다음 단계 (자동): `/auto-write-plan` → `/auto-execute-plan`
