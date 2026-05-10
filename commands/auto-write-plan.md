---
description: auto-flow 3단계 진입 — tech-design.md 있는 상태에서 write-plan + execute-plan 자동.
---

# /auto-write-plan

`<slug>` 인자 optional. 인자 누락 시 latest <slug> 자동. 이 커맨드는 `auto-writing-plans` skill 을 invoke 합니다.

산출물:
- `<slug>-implementation-plan.md` (RAW, frontmatter `commit_policy: per-task`)

다음 단계 (자동): `/auto-execute-plan`
