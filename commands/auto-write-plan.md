---
description: 자동 흐름의 3단계 진입 — tech-design.md 가 있는 상태에서 write-plan + execute-plan 까지 자동으로 이어갑니다.
---

# /auto-write-plan

`<slug>` 인자는 선택입니다. 누락 시 가장 최근 <slug> 자동 선택. 이 슬래시는 `auto-writing-plans` skill 을 호출합니다.

산출물은 `<slug>-implementation-plan.md` 입니다 (RAW 본문, frontmatter 의 `commit_policy: per-task`).

다음 단계는 자동으로 이어집니다 — `/auto-execute-plan`.
