---
name: auto-brainstorming
description: auto-flow 진입점 — Socratic clarifying Q (1~5개 적응) + AI 자동 approach 선택 + 자동 section 작성 + change-history 자동 + auto-designing-direction 자동 invoke. 사용자 입력은 clarifying Q 답변에만. AskUserQuestion / Visual Companion / docs-pretty 호출 X.
---

# Auto Brainstorming → <slug>-requirements.md (Socratic auto)

js-super:auto-brainstorming 은 명시적 사용자 invoke (`/auto-brainstorm <피처명>`) 시에만 작동. PRD `auto-flow-requirements.md` D1~D12 (D9 amend) + tech-design D-T1~D-T12 의 자동 흐름 본문.

**Announce at start:** "I'm using the auto-brainstorming skill — Socratic clarifying Q + 자동 진행."

## Process

### Step 1 — Slug 추론 + 폴더 생성

`/auto-brainstorm <피처명>` 인자 → slug (공백 → 하이픈). 인자 누락 시 메인이 한 줄 묻고 진행.

```bash
mkdir -p docs/features/$(date +%Y-%m-%d)-<slug>/
```

### Step 2 — Socratic clarifying questions (1~5개 적응)

메인 에이전트가 사용자 첫 입력 + slug 으로 첫 질문 던짐. 한 번에 1개. 답변 충분히 명확하면 1개로 끝, 모호하면 최대 5개 (D-T2).

질문 패턴:
- 핵심 user story 한 줄?
- 가장 중요한 acceptance criterion?
- (필요 시) 명시적 범위 밖?
- (필요 시) 외부 의존성?
- (필요 시) 사용자가 우려하는 위험?

→ 사용자 답변 = 본 흐름의 유일한 사용자 입력 지점.

### Step 3 — AI 자동 approach 선택

메인이 2-3 approach + tradeoffs 자체 추론, recommendation 1개 자동 선택. 사용자에게 노출 X. 선택 reasoning 은 산출물 §핵심 결정 에 logged.

### Step 4 — 산출물 자동 작성

`<slug>-requirements.md` 작성 (Socratic free-form):
- H1 + Mode line + 배경 + 핵심 결정 + 우려/해결 + 다음 단계 + 변경이력 footer
- docs-pretty 호출 X (D-T12). RAW 본문 그대로.

### Step 5 — change-history 자동

`change-history` skill invoke → 첫 `[요구사항-수정]` entry append. CH-id 자동 생성.

### Step 6 — Transition notice + auto-designing-direction invoke

```
ℹ️ Auto-proceeding to /design. Type "stop" to abort.
```

다음 사용자 turn 의 입력에 `parse_interrupt` (scripts/auto_flow.py) 매치 시 cleanly exit + `ℹ️ OK. /design 나중에 직접 실행.` 안내. 매치 X 시 즉시 `js-super:auto-designing-direction` skill invoke.

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 호출 | NEVER. auto-flow 의 사용자 입력은 clarifying Q 답변에만. |
| docs-pretty 호출 | NEVER. PRD D9 amend — auto-flow 는 review 없으므로 prettify 의미 없음. |
| Visual Companion offer | NEVER. D-T11. |
| 일반 brainstorming skill body 호출 | NEVER. self-contained mirror (D-T1). |
| transition notice 후 사용자 응답 wait sleep | NEVER. harness 모델은 자동 다음 turn — sleep X. |

## Related Skills

- `auto-designing-direction` — 다음 단계
- `change-history` — 첫 entry append
- `scripts/auto_flow.parse_interrupt` — interrupt 키워드 catch
