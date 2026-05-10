---
name: auto-writing-plans
description: auto-flow 3단계 — requirements + tech-design 읽기 + AI 자동 task 분해 (TDD bite-sized + Model hint 자동) + RISK 코드 지점 §2 자동 + verifying-spec 자동 + code-pretty 호출 X (D-T12 와 일관) + change-history 자동 + auto-executing-plans 자동 invoke. AskUserQuestion / docs-pretty 호출 X.
---

# Auto Writing Plans → <slug>-implementation-plan.md (auto)

## Process

### Step 1 — 입력 확인 + slug 추론

`<slug>-requirements.md` + `<slug>-tech-design.md` 모두 존재 확인. 누락 시 `ℹ️ 입력 누락 (<누락 파일>). /auto-brainstorm 또는 /auto-design 부터 시작하세요.` 안내 후 종료.

### Step 2 — AI 자동 task 분해

tech-design §1~§7 + R1~R10 분석. TDD bite-sized task 자동 생성:
- 각 task 의 Files / Model hint / TDD steps / RISK 자동 결정
- Model 힌트 자동: 1-2 파일 mechanical → haiku / 다중 파일 + 통합 → sonnet / 설계 + 광범위 → opus / Korean prose 조작 → sonnet (Haiku rephrasing 위험)
- Before/After 코드블록 (`**원본**` / `**수정 후**`) 컨벤션

### Step 3 — §2 위험 코드 지점 자동

tech-design §6 R-N → file:line + mitigation 매핑. 모든 R-N 이 §2 에 entry 갖도록 보장 (writing-plans Self-Review 룰).

### Step 4 — 산출물 자동 작성

`<slug>-implementation-plan.md` schema 따라 작성. frontmatter `commit_policy: per-task`. RAW 본문, code-pretty / docs-pretty 호출 X (D-T12 일관).

### Step 4.5 — plan_byte_check 자동 (v2.0.0+)

Plan 본문 자동 작성 직후, 메인이 helper 자동 호출:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.plan_byte_check import verify_plan_block_byte_equal
mismatches = verify_plan_block_byte_equal(
    Path('<PLAN_PATH>'),
    Path('.'),
)
if mismatches:
    for m in mismatches:
        print(f'MISMATCH #{m.block_index} — {m.reason}')
    sys.exit(1)
sys.exit(0)
"
```

미스매치 발견 시 메인이 즉시 plan 의 `**원본**` 블록 수정 후 재시도 (auto 모드 — 사용자 응답 wait X). 3회 재시도 후에도 실패 시 `ℹ️ plan_byte_check 3회 실패. 사용자 개입 필요.` 안내 후 종료. byte-copy 정밀도 강제는 v2.0.0 구현계획서의 핵심 precondition.

### Step 5 — verifying-spec 자동 실행

`verifying-spec` invoke. 4축 보고서 생성. 결과는 transition notice 직전 노출.

### Step 6 — change-history 자동

`change-history` invoke → 첫 `[구현계획서-수정]` entry. CH-id 자동.

### Step 7 — Transition notice + auto-executing-plans invoke

```
🔍 verifying-spec 결과: ...
ℹ️ Auto-proceeding to /execute-plan (subagent wave-parallel, Gate #14 override). Type "stop" to abort.
```

`parse_interrupt` 매치 시 exit. 매치 X → `js-super:auto-executing-plans` invoke.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. |
| docs-pretty 호출 | NEVER. |
| code-pretty 호출 | NEVER. D-T12 일관. |
| 일반 writing-plans skill body 호출 | NEVER. self-contained mirror (D-T1). |

## Related Skills

- `auto-executing-plans` — 다음 단계 (wave-parallel subagent 강제)
- `verifying-spec` / `change-history`
- `scripts/auto_flow.parse_interrupt`, `find_latest_slug`
