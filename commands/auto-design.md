---
description: 자동 흐름의 2단계 진입 — requirements.md 가 있는 상태에서 design 부터 끝까지 자동으로 이어갑니다. 인자 누락 시 가장 최근 <slug> 자동 선택.
---

# /auto-design

`<slug>` 인자는 선택입니다. 누락 시 `docs/features/` 의 가장 최근 폴더를 자동으로 선택합니다. 이 슬래시는 `auto-designing-direction` skill 을 호출합니다.

산출물은 `<slug>-tech-design.md` 입니다 (RAW 본문).

다음 단계는 자동으로 이어집니다 — `/auto-write-plan` → `/auto-execute-plan`.
