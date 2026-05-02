# js-superpowers v0.1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** superpowers v5.0.7 베이스 위에 한국형 3-MD spec-driven 워크플로우(요구사항 → 개발방향 → 구현계획서) + 메인 검증 게이트 + 변경이력 자동 누적 + 위험 주석 규약 + API 자동 테스트 파이프라인을 얹은 v0.1.0 플러그인을 구현한다.

**Architecture:** vendored superpowers 코드 위에 6개 신규 skill, 3개 기존 skill 수정, 2개 신규 슬래시 커맨드, 2개 helper Python 스크립트를 추가한다. 모든 신규 skill은 superpowers 프롬프트 스타일(YAML frontmatter, HARD-GATE, dot-graph, Red Flags, 체크리스트)을 따른다.

**Tech Stack:** Markdown(skill/command/spec), Python 3.10+(helper script + pytest), pytest + requests + pytest-json-report(API 테스트), Bash(end-to-end 스모크).

**Spec 참조:** `docs/superpowers/specs/2026-05-02-js-superpowers-design.md`

**Git 가정:** 본 plan의 각 task 끝에 `git add` / `git commit` step이 포함되어 있다. 사용자가 본격 구현 전에 `git init` 을 한 다음 Phase 0부터 진행하는 것을 권장한다. git이 초기화되지 않은 상태로 진행할 경우 모든 commit step은 건너뛰고, Phase별 acceptance는 파일 존재/형식 검증으로만 통과 판정한다.

---

## File Structure (변경/신규분)

```
js-superpowers/
├── .claude-plugin/plugin.json          # 이미 갱신됨
├── README.md                            # 이미 작성됨
├── skills/
│   ├── brainstorming/SKILL.md           # 수정 (요구사항.md 산출)
│   ├── designing-direction/SKILL.md     # 신규 (개발방향.md 산출)
│   ├── writing-plans/SKILL.md           # 수정 (구현계획서.md 산출)
│   ├── executing-plans/SKILL.md         # 수정 (위험 주석 + 변경이력)
│   ├── verifying-spec/SKILL.md          # 신규 (메인 검증 게이트)
│   ├── change-history/SKILL.md          # 신규 (이력 누적 규약)
│   ├── change-propagation/SKILL.md      # 신규 (cascading 전파)
│   ├── risk-annotation/SKILL.md         # 신규 (위험 주석 형식 + 체크리스트)
│   └── api-auto-testing/SKILL.md        # 신규 (API 테스트 파이프라인)
├── commands/
│   ├── brainstorm.md                    # 수정
│   ├── design.md                        # 신규
│   ├── write-plan.md                    # 수정
│   ├── execute-plan.md                  # 수정 (텍스트 갱신만)
│   └── api-test.md                      # 신규
├── scripts/
│   ├── change_id.py                     # 신규 (CH-id 자동 생성)
│   ├── detect_auth.py                   # 신규 (auth 패턴 탐색)
│   └── tests/
│       ├── test_change_id.py
│       └── test_detect_auth.py
└── templates/
    └── api-tests/
        └── conftest.py.template         # 신규 (시나리오 공통 fixture)
```

각 파일은 단일 책임을 갖고 분리되어 있다. skill 본문과 command 본문이 함께 변하니 같은 파일 묶음 안에서 작업한다.

---

## 진행 원칙

1. **각 Phase 끝에 acceptance task** 가 있고, 거기 통과해야 다음 Phase 진입
2. **모든 skill 작성/수정**은 `superpowers:writing-skills` skill을 사전 invoke하여 컨벤션 준수
3. **모든 코드 변경 후** `git add` + `git commit` (사용자가 git init 한 후부터)
4. **에이전트가 막히면**: spec(`docs/superpowers/specs/2026-05-02-js-superpowers-design.md`) 다시 읽기 → spec과 plan 모순 발견 시 사용자에 보고 후 결정
5. **TDD가 부적합한 경우**(prose skill 본문) — "구조 outline → 작성 → 동료 리뷰 시뮬레이션(자기 체크리스트) → 사용자 acceptance" 패턴 사용

---

## Phase 0 — Bootstrap

### Task 0.1: scripts/ 디렉터리 + pytest 환경 준비

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/tests/__init__.py`
- Create: `requirements-dev.txt`

- [ ] **Step 1: 디렉터리/파일 골격 생성**

```bash
mkdir -p scripts/tests templates/api-tests
touch scripts/__init__.py scripts/tests/__init__.py
```

- [ ] **Step 2: requirements-dev.txt 작성**

```
pytest>=7.4
requests>=2.31
pytest-json-report>=1.5
pytest-httpserver>=1.0
```

`pytest-httpserver`는 Phase 5/6 acceptance에서 모의 백엔드 서버 fixture로 사용 (실제 백엔드 없이 시나리오 실행 검증).

파일: `requirements-dev.txt`

- [ ] **Step 3: 가상환경 + 설치 확인**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --version
```

Expected: `pytest 7.x.x` 출력

- [ ] **Step 4: .gitignore에 .venv 추가** (이미 git init 후에는)

`.gitignore`에 다음 라인 append:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: 커밋 (git init 이후)**

```bash
git add scripts/ templates/ requirements-dev.txt .gitignore
git commit -m "chore: bootstrap dev environment (pytest + scaffolding)"
```

---

### Task 0.2: 플러그인 dev install (심볼릭 링크)

**책임:** 모든 Phase의 acceptance 시뮬레이션이 실제 슬래시 커맨드를 트리거하려면 플러그인이 Claude Code에 install 되어 있어야 한다. 개발 중에는 심볼릭 링크로 라이브 install (수정 즉시 반영).

**Files:** (none — 외부 디렉터리 조작)

- [ ] **Step 1: 기존 install 충돌 확인**

```bash
ls -la ~/.claude/plugins/ 2>&1 | grep -E "js-superpowers|^l" || echo "no conflict"
```

기존 동명 plugin 디렉터리가 있다면 사용자에 확인 후 백업/제거.

- [ ] **Step 2: 심볼릭 링크 생성**

```bash
mkdir -p ~/.claude/plugins
ln -sfn "$JS_SUPERPOWERS_PATH" ~/.claude/plugins/js-superpowers
ls -la ~/.claude/plugins/js-superpowers
```
Expected: `js-superpowers -> <repo absolute path>`

- [ ] **Step 3: Claude Code 재시작 안내**

사용자에 "터미널에서 Claude Code 세션 종료 후 재시작 → 플러그인 인식되는지 `/help` 또는 슬래시 자동완성으로 확인" 안내.

- [ ] **Step 4: install 검증**

신규 세션에서:
- `/brainstorm` 슬래시가 자동완성에 보이는지
- 플러그인 manifest가 `js-superpowers` v0.1.0 으로 인식되는지

- [ ] **Step 5: (git init 후) 커밋**

(이 task는 외부 디렉터리만 건드리므로 커밋할 파일 없음. 다음 task에서 함께.)

> **주의**: 이후 Phase 1~6의 모든 acceptance 시뮬레이션은 이 dev install 이 활성화된 상태를 전제로 한다. 새 skill 파일을 추가/수정한 뒤 Claude Code를 재시작하지 않으면 변경이 반영되지 않을 수 있다 — 각 Phase acceptance 직전에 세션 재시작 권장.

---

## Phase 1 — 3-MD Workflow + Change History

> **Phase 1 한정 정책 — verify-gate stub 모드**
>
> Phase 1의 designing-direction(Task 1.5) 과 writing-plans 수정(Task 1.7)에서 `verifying-spec` skill 호출 site를 SKILL.md에 명시한다. 그러나 verifying-spec skill 자체는 Phase 2.1에서 비로소 작성된다. Phase 1 acceptance 동안에는 다음 정책 적용:
>
> 1. 두 skill의 "After Save" 섹션에 **tolerance 절** 명시 — `verifying-spec` skill 미존재 시 호출을 skip 하고 사용자에 1줄 notice ("verify-gate 미설치, Phase 2 이후 활성화") 출력 후 진행
> 2. Phase 1.9 acceptance는 verify gate 출력을 검증하지 않음 (3-MD 산출 + 변경이력 entry 만 검증)
> 3. Phase 2.4 acceptance에서 verify gate 가 active 상태로 동작하는지 별도 검증

### Task 1.1: change_id.py 헬퍼 스크립트 (TDD)

**책임:** 주어진 피처 폴더에서 다음 CH-id를 생성. 형식 `CH-YYYYMMDD-NNN`. NNN은 같은 날 안의 일련번호.

**Files:**
- Create: `scripts/change_id.py`
- Test: `scripts/tests/test_change_id.py`

- [ ] **Step 1: 실패 테스트 작성**

`scripts/tests/test_change_id.py`:
```python
from pathlib import Path
import tempfile
from datetime import date

from scripts.change_id import next_change_id


def test_first_id_when_no_history(tmp_path: Path):
    feature_dir = tmp_path
    (feature_dir / "요구사항.md").write_text("# 요구사항\n\n## 변경이력\n", encoding="utf-8")
    today = date(2026, 5, 2)
    assert next_change_id(feature_dir, today) == "CH-20260502-001"


def test_increment_within_same_day(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "# 요구사항\n\n## 변경이력\n\n### [2026-05-02 10:00] [요구사항-수정]\n- **id**: CH-20260502-001\n",
        encoding="utf-8",
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-002"


def test_reset_for_new_day(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "## 변경이력\n\n### [2026-05-01 10:00] [요구사항-수정]\n- **id**: CH-20260501-007\n",
        encoding="utf-8",
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-001"


def test_scans_all_md_files(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "## 변경이력\n### [2026-05-02 10:00]\n- **id**: CH-20260502-001\n", encoding="utf-8"
    )
    (tmp_path / "구현계획서.md").write_text(
        "## 변경이력\n### [2026-05-02 11:00]\n- **id**: CH-20260502-005\n", encoding="utf-8"
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-006"
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

```bash
pytest scripts/tests/test_change_id.py -v
```
Expected: 4 FAILED with `ModuleNotFoundError: No module named 'scripts.change_id'`

- [ ] **Step 3: 최소 구현**

`scripts/change_id.py`:
```python
"""Generate next CH-id (CH-YYYYMMDD-NNN) by scanning feature folder MDs."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

CH_PATTERN = re.compile(r"CH-(\d{8})-(\d{3})")


def next_change_id(feature_dir: Path, today: date) -> str:
    today_str = today.strftime("%Y%m%d")
    max_seq = 0
    for md_file in feature_dir.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for match in CH_PATTERN.finditer(text):
            day, seq = match.group(1), int(match.group(2))
            if day == today_str:
                max_seq = max(max_seq, seq)
    return f"CH-{today_str}-{max_seq + 1:03d}"


if __name__ == "__main__":
    import sys
    from datetime import date as _date

    if len(sys.argv) != 2:
        print("usage: python -m scripts.change_id <feature-dir>", file=sys.stderr)
        sys.exit(2)
    print(next_change_id(Path(sys.argv[1]), _date.today()))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest scripts/tests/test_change_id.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: 커밋**

```bash
git add scripts/change_id.py scripts/tests/test_change_id.py
git commit -m "feat(scripts): add change_id.py to generate CH-YYYYMMDD-NNN ids"
```

---

### Task 1.2: change-history skill 작성

**책임:** 3-MD 변경이력 항목 기록 규약을 정의하고, 모든 다른 skill이 이 규약을 호출/참조하도록 한다.

**Files:**
- Create: `skills/change-history/SKILL.md`

- [ ] **Step 1: writing-skills 사전 invoke로 컨벤션 재확인**

세션 안에서:
```
Skill: superpowers:writing-skills
```
출력의 frontmatter/구조 가이드 따른다.

- [ ] **Step 2: SKILL.md 작성** — 다음 구조 그대로

```markdown
---
name: change-history
description: Use when ANY MD or code is added/modified/deleted in a feature folder under docs/features/<date>-<slug>/, before commits — appends a structured change-log entry to the relevant MD's "변경이력" footer with auto-generated CH-id, reason, scope, before/after code (for code edits), and impact links.
---

# Change History (변경이력 자동 누적)

<HARD-GATE>
You MUST append a 변경이력 entry to the affected MD whenever you:
- Edit/Create/Delete any of 요구사항.md, 개발방향.md, 구현계획서.md
- Modify code as part of /execute-plan
NEVER skip this. The history is the only audit trail outside git.
</HARD-GATE>

## When to Use

- 요구사항.md edited → append to 요구사항.md "## 변경이력"
- 개발방향.md edited → append to 개발방향.md "## 변경이력"
- 구현계획서.md edited → append to 구현계획서.md "## 변경이력"
- Code edited via /execute-plan → append [코드-수정] entry to 구현계획서.md "## 변경이력" with before/after code
- API test executed via /api-test → append [API테스트] entry to 구현계획서.md

## Entry Schema (Common — all 3 MDs)

\`\`\`markdown
### [YYYY-MM-DD HH:MM] [요구사항-수정 | 개발방향-수정 | 구현계획서-수정 | 코드-수정 | API테스트]
- **id**: CH-YYYYMMDD-NNN
- **이유**: <왜 바꿨나>
- **무엇이**: <어느 섹션/필드/파일>
- **영향범위**: <하위 MD 또는 코드 어느 부분이 같이 갱신됐는지>
- **연관 항목**: CH-... (선행/관련, 없으면 생략)
\`\`\`

## Code-Change Entry (구현계획서.md only)

추가 필드:

\`\`\`markdown
- **위험 카테고리**: side-effect | race | breaking | perf
- **변경 전 코드** (file:line)
  \`\`\`<lang>
  <원본 코드 그대로>
  \`\`\`
- **변경 후 코드**
  \`\`\`<lang>
  <새 코드 — 위험 주석 포함>
  \`\`\`
\`\`\`

## API-Test Entry (구현계획서.md only)

\`\`\`markdown
- **시나리오 파일**: api-tests/scenario-NNN-<name>.py (N tests)
- **결과**: PASS x / FAIL y / ERROR z
- **실패 상세**: <요약>
- **결과 파일**: api-tests/results/<timestamp>.json
- **다음 액션**: <필요 시 코드 수정 제안>
\`\`\`

## CH-id Generation

Use the helper script. Never hand-author CH-id:

\`\`\`bash
python -m scripts.change_id docs/features/<date>-<slug>
# 출력 예: CH-20260502-003
\`\`\`

## Process Flow

\`\`\`dot
digraph change_history {
    "Edit detected" [shape=box];
    "Generate CH-id\n(scripts/change_id.py)" [shape=box];
    "Build entry per schema" [shape=box];
    "Append to '## 변경이력' footer" [shape=box];
    "Cross-link if cascading\n(연관 항목)" [shape=diamond];
    "Done" [shape=doublecircle];

    "Edit detected" -> "Generate CH-id\n(scripts/change_id.py)";
    "Generate CH-id\n(scripts/change_id.py)" -> "Build entry per schema";
    "Build entry per schema" -> "Append to '## 변경이력' footer";
    "Append to '## 변경이력' footer" -> "Cross-link if cascading\n(연관 항목)";
    "Cross-link if cascading\n(연관 항목)" -> "Done";
}
\`\`\`

## Anti-Patterns

| Thought | Reality |
|---|---|
| "이 작은 수정은 이력 안 남겨도 돼" | 사소해 보여도 시간 지나면 컨텍스트 휘발. 모든 수정 기록. |
| "CH-id는 적당히 만들어 쓰자" | 중복/순서 깨짐. 반드시 helper script 사용. |
| "코드 변경 후 before 코드는 git이 알지" | git log는 의도/영향범위/위험 카테고리를 모름. 구현계획서.md에 풀스키마. |

## Red Flags

| 신호 | 무시 금지 |
|---|---|
| "이번엔 변경이력 생략" | 멈춰. 누적이 깨지면 추적 단서 사라진다. |
| "위험 카테고리 모르겠다" | risk-annotation skill 6-체크리스트로 분류. 그래도 모호하면 side-effect default. |

## Acceptance

새 entry가 추가되면:
1. CH-id가 형식에 맞고 유일함 (`grep -c "CH-20260502-003" <file>` == 1 in entry)
2. "## 변경이력" 섹션 끝에 들어가 있음 (다른 본문 안에 끼어들지 않음)
3. 코드 수정 entry는 변경 전·후 코드 풀 블록 포함

## Related Skills

- risk-annotation: 위험 카테고리 분류 기준
- change-propagation: 상위 변경 시 하위 자동 갱신
```

- [ ] **Step 3: skill 자기 체크리스트**

다음 모두 만족하는지 본인 점검:
- frontmatter `name` + `description` (트리거 조건 명시)
- HARD-GATE 블록
- "When to Use" 섹션
- Process Flow with `digraph`
- Anti-Patterns 표
- Red Flags 표
- Acceptance 기준
- Related Skills 링크

- [ ] **Step 4: Skill 도구로 로딩 시뮬레이션**

세션 안에서 `Skill: change-history` 호출 → 본문이 정상 표시되는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add skills/change-history/SKILL.md
git commit -m "feat(skill): add change-history skill (3-MD entry schema + CH-id rule)"
```

---

### Task 1.3: brainstorming skill 수정 (요구사항.md 산출)

**책임:** 기존 brainstorming 흐름은 유지하되, 산출물을 spec.md → 요구사항.md (PRD 형식)로 바꾸고 위치도 `docs/features/YYYY-MM-DD-<slug>/요구사항.md`로 변경.

**Files:**
- Modify: `skills/brainstorming/SKILL.md` (전체 갈아엎기, superpowers 베이스 위에 PRD 산출 로직 추가)

- [ ] **Step 1: 원본 백업 (참고용)**

```bash
cp skills/brainstorming/SKILL.md skills/brainstorming/SKILL.md.upstream
```
이 백업 파일은 `.gitignore`에 추가하거나 커밋하지 않는다.

- [ ] **Step 2: 신규 SKILL.md 작성** — 핵심 변경점

`skills/brainstorming/SKILL.md` (요지):

```markdown
---
name: brainstorming
description: You MUST use this before creating any feature, component, or behavior change. Conducts a structured PRD-style dialogue (purpose → user stories → FRs → NFRs → out-of-scope → acceptance criteria) and writes 요구사항.md to docs/features/YYYY-MM-DD-<slug>/. Does NOT cover technical design — that belongs to designing-direction.
---

# Brainstorming → 요구사항.md (PRD)

(상속: superpowers:brainstorming의 핵심 패턴 — one question at a time, multiple choice preferred, 2-3 approaches with tradeoffs, design sections with approval. 이 skill은 그 위에 PRD 산출에 특화한 변형판이다.)

## Output

저장 경로: `docs/features/YYYY-MM-DD-<slug>/요구사항.md`
- 날짜 = 첫 brainstorming 세션이 시작된 날(불변 ID)
- slug = 사용자가 첫 질문에서 명시한 피처명(공백→하이픈)

## Document Schema (요구사항.md)

\`\`\`markdown
# 요구사항: <피처명>

## 1. 배경/목적
## 2. 사용자 스토리 / 시나리오
## 3. 기능 요구사항 (FR)
   - FR-1: …
   - FR-2: …
## 4. 비기능 요구사항 (NFR)
## 5. 범위 밖 (Out of Scope)
## 6. 수용 기준 (Acceptance Criteria)

---
## 변경이력
<!-- change-history skill이 자동 추가, 최신이 아래로 누적 -->
\`\`\`

## Process Flow (PRD 전용)

\`\`\`dot
digraph prd_flow {
    "Explore project context" [shape=box];
    "Confirm feature name + slug" [shape=box];
    "Q: 배경/목적은?" [shape=box];
    "Q: 사용자 스토리는?" [shape=box];
    "Q: 기능 요구사항(FR)?" [shape=box];
    "Q: NFR(성능/보안/접근성)?" [shape=box];
    "Q: 범위 밖?" [shape=box];
    "Q: 수용 기준?" [shape=box];
    "Spec self-review" [shape=box];
    "User reviews 요구사항.md" [shape=diamond];
    "Invoke change-history\n(첫 entry: 요구사항-생성)" [shape=box];
    "Hand off to /design" [shape=doublecircle];

    "Explore project context" -> "Confirm feature name + slug";
    "Confirm feature name + slug" -> "Q: 배경/목적은?";
    "Q: 배경/목적은?" -> "Q: 사용자 스토리는?";
    "Q: 사용자 스토리는?" -> "Q: 기능 요구사항(FR)?";
    "Q: 기능 요구사항(FR)?" -> "Q: NFR(성능/보안/접근성)?";
    "Q: NFR(성능/보안/접근성)?" -> "Q: 범위 밖?";
    "Q: 범위 밖?" -> "Q: 수용 기준?";
    "Q: 수용 기준?" -> "Spec self-review";
    "Spec self-review" -> "User reviews 요구사항.md";
    "User reviews 요구사항.md" -> "Spec self-review" [label="changes"];
    "User reviews 요구사항.md" -> "Invoke change-history\n(첫 entry: 요구사항-생성)" [label="approve"];
    "Invoke change-history\n(첫 entry: 요구사항-생성)" -> "Hand off to /design";
}
\`\`\`

## HARD-GATE (terminal)

The terminal state of this skill is **inviting user to run /design** — NOT writing 개발방향.md, NOT touching code. The brainstorming skill in this plugin is for PRD only.

## Self-Review

PRD 문서 작성 후 다음 검사:
1. 모든 FR이 unique id (FR-1, FR-2, …) 보유
2. 수용 기준이 측정 가능 (Yes/No로 답할 수 있는 형태)
3. Out-of-scope 명시 (없으면 "없음" 명시)
4. 기술/구현 디테일이 본문에 안 들어감 (그건 개발방향.md 영역)

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| 본문에 "Postgres 사용", "REST API"같은 기술 결정 박기 | 그건 개발방향.md로. 요구사항은 기술 무관. |
| FR 없이 "사용자가 ~할 수 있다"만 적기 | FR-N: <행동> + acceptance criteria 함께 |
| 1번 세션에 개발방향까지 끝내기 | 분리. 끝나면 사용자가 /design 직접 호출 |

## After Save — Invoke change-history

요구사항.md 첫 저장 시 [요구사항-수정] entry로 "최초 생성" 기록:
- 이유: 신규 피처 brainstorming 결과
- 무엇이: 요구사항.md 전체 (FR-1..N)
- 영향범위: 없음 (최초 생성)
```

전체 길이 ~120줄. superpowers brainstorming의 visual companion 등 부수 기능은 유지(상속 표현으로 명시).

- [ ] **Step 3: 자기 체크리스트**

- frontmatter description이 트리거 조건을 명시 ("before creating any feature...")
- HARD-GATE이 "PRD only, no design"을 강제
- 산출물 위치/형식이 spec §3.1과 일치
- change-history 호출이 명시
- Anti-Patterns에 "기술 결정 섞지 마" 명시

- [ ] **Step 4: 통합 테스트 (수동, Phase 1 acceptance에서 자동화)**

세션에서 `/brainstorm 데모피처` 실행 → 단계별 질문 진행 → `docs/features/2026-05-02-데모피처/요구사항.md` 생성 확인 → 변경이력 첫 entry 존재 확인.

- [ ] **Step 5: 커밋**

```bash
git add skills/brainstorming/SKILL.md
git commit -m "feat(skill): brainstorming → produce 요구사항.md (PRD-only, separate from design)"
```

---

### Task 1.4: commands/brainstorm.md 수정

**Files:**
- Modify: `commands/brainstorm.md`

- [ ] **Step 1: 새 본문 작성**

```markdown
---
description: 새 피처의 요구사항.md(PRD)를 작성합니다. 기획 레벨 합의 후 /design으로 넘어갑니다.
---

# /brainstorm

피처명을 인수로 주거나 (`/brainstorm 사용자 잔액 출금`) 인수 없이 호출하면 피처명을 묻습니다.

이 커맨드는 `brainstorming` skill을 invoke 합니다.

산출물:
- `docs/features/<오늘날짜>-<slug>/요구사항.md`

다음 단계: `/design`
```

- [ ] **Step 2: 커밋**

```bash
git add commands/brainstorm.md
git commit -m "feat(cmd): /brainstorm produces 요구사항.md only"
```

---

### Task 1.5: designing-direction skill 작성

**책임:** 요구사항.md를 입력으로 받아 기술 설계 대화 → 개발방향.md 산출 + 메인 검증 게이트 호출.

**Files:**
- Create: `skills/designing-direction/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

`skills/designing-direction/SKILL.md`:

```markdown
---
name: designing-direction
description: Use after brainstorming has produced 요구사항.md, before writing-plans. Conducts a technical-design dialogue (architecture → impacted components → data model → external interfaces → key decisions w/ alternatives → preliminary risks → testing strategy) and writes 개발방향.md. Ends with the main agent's spec verification gate (verifying-spec) before handing off to /write-plan.
---

# Designing Direction → 개발방향.md (Technical Spec)

<HARD-GATE>
You MUST have an existing 요구사항.md in the current feature folder before invoking this skill. If none exists, instruct the user to run /brainstorm first.
</HARD-GATE>

## Input

`docs/features/YYYY-MM-DD-<slug>/요구사항.md`

## Output

`docs/features/YYYY-MM-DD-<slug>/개발방향.md`

## Schema (개발방향.md)

\`\`\`markdown
# 개발방향: <피처명>

## 1. 아키텍처 개요 (다이어그램/설명)
## 2. 영향 받는 컴포넌트/파일
## 3. 데이터 모델/스키마 변경
## 4. 외부 인터페이스 (API, 이벤트)
## 5. 핵심 결정 + 대안 비교 (왜 이 길을)
## 6. 위험/사이드이펙트 (preliminary)
## 7. 테스트 전략

---
## 변경이력
\`\`\`

## Process Flow

\`\`\`dot
digraph design_flow {
    "Read 요구사항.md" [shape=box];
    "Survey existing code\n(impacted files via Grep)" [shape=box];
    "Q: 아키텍처 후보 2-3개?" [shape=box];
    "Q: 영향 컴포넌트 매핑?" [shape=box];
    "Q: 데이터 모델 변경?" [shape=box];
    "Q: 외부 인터페이스?" [shape=box];
    "Q: 핵심 결정 + 대안?" [shape=box];
    "Q: 위험 후보?" [shape=box];
    "Q: 테스트 전략?" [shape=box];
    "Self-review" [shape=box];
    "User reviews 개발방향.md" [shape=diamond];
    "Invoke verifying-spec\n(요구사항 ↔ 개발방향)" [shape=box];
    "Verifier 보고서 → 사용자 결정" [shape=diamond];
    "Invoke change-history" [shape=box];
    "Hand off to /write-plan" [shape=doublecircle];

    "Read 요구사항.md" -> "Survey existing code\n(impacted files via Grep)";
    "Survey existing code\n(impacted files via Grep)" -> "Q: 아키텍처 후보 2-3개?";
    "Q: 아키텍처 후보 2-3개?" -> "Q: 영향 컴포넌트 매핑?";
    "Q: 영향 컴포넌트 매핑?" -> "Q: 데이터 모델 변경?";
    "Q: 데이터 모델 변경?" -> "Q: 외부 인터페이스?";
    "Q: 외부 인터페이스?" -> "Q: 핵심 결정 + 대안?";
    "Q: 핵심 결정 + 대안?" -> "Q: 위험 후보?";
    "Q: 위험 후보?" -> "Q: 테스트 전략?";
    "Q: 테스트 전략?" -> "Self-review";
    "Self-review" -> "User reviews 개발방향.md";
    "User reviews 개발방향.md" -> "Self-review" [label="changes"];
    "User reviews 개발방향.md" -> "Invoke verifying-spec\n(요구사항 ↔ 개발방향)" [label="approve"];
    "Invoke verifying-spec\n(요구사항 ↔ 개발방향)" -> "Verifier 보고서 → 사용자 결정";
    "Verifier 보고서 → 사용자 결정" -> "Self-review" [label="fix needed"];
    "Verifier 보고서 → 사용자 결정" -> "Invoke change-history" [label="proceed"];
    "Invoke change-history" -> "Hand off to /write-plan";
}
\`\`\`

## Self-Review

- 요구사항.md의 모든 FR이 §2(영향 컴포넌트) 또는 §4(외부 IF)에 매핑되어야 함
- §5 핵심 결정마다 최소 1개 대안 + 채택 이유 명시
- §6 위험 후보는 risk-annotation 카테고리(side-effect|race|breaking|perf) 기준으로 사전 분류

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| 단계별 task 적기 | 그건 구현계획서.md에. 개발방향은 "어떻게 설계되었나"까지 |
| FR 매핑 빠뜨리기 | 모든 FR이 §2 또는 §4에 등장해야 함 |
| 한 결정만 적기 | 항상 대안 1개 이상 + 비교 |

## After Save

1. verifying-spec skill invoke (메인이 직접) → 요구사항.md ↔ 개발방향.md 정합성 + 코드 임팩트 분석
   - **Tolerance**: 만약 verifying-spec skill 이 아직 install 되지 않았다면 ("Skill not found" 등) 호출을 skip 하고 사용자에 1줄 notice 출력 후 진행: "ℹ️ verify-gate 미설치 (Phase 2 이후 활성화) — 검증 없이 진행"
2. 보고서 사용자에 표시 → 사용자가 "수정"/"진행" 결정 (verify skip 모드일 땐 이 단계도 skip)
3. 진행이면 change-history skill로 [개발방향-수정] entry 추가 (최초 생성)
4. 사용자에 `/write-plan` 호출 안내
```

- [ ] **Step 2: 자기 체크리스트**

- 입력/출력 명시
- HARD-GATE으로 요구사항.md 부재 시 차단
- Tolerance 절: verifying-spec 미설치 시 graceful skip
- Process flow에 verifying-spec 호출 노드
- After Save에 change-history 호출 명시

- [ ] **Step 3: 커밋**

```bash
git add skills/designing-direction/SKILL.md
git commit -m "feat(skill): add designing-direction (요구사항 → 개발방향.md, with verify gate)"
```

---

### Task 1.6: commands/design.md 작성

**Files:**
- Create: `commands/design.md`

- [ ] **Step 1: 본문 작성**

```markdown
---
description: 직전에 만든 요구사항.md를 받아 기술 설계 대화를 진행하고 개발방향.md를 작성합니다.
---

# /design

이 커맨드는 `designing-direction` skill을 invoke 합니다.

전제: 동일한 피처 폴더에 `요구사항.md`가 이미 존재해야 합니다 (없으면 `/brainstorm` 먼저).

산출물:
- `docs/features/<날짜>-<slug>/개발방향.md`
- 메인 에이전트 검증 보고서 (대화로 출력)

다음 단계: `/write-plan`
```

- [ ] **Step 2: 커밋**

```bash
git add commands/design.md
git commit -m "feat(cmd): add /design command (technical spec phase)"
```

---

### Task 1.7: writing-plans skill 수정 (구현계획서.md 산출)

**책임:** 기존 writing-plans는 spec.md를 기반으로 plan.md를 만들었음. 이제 요구사항.md + 개발방향.md를 함께 읽어 구현계획서.md를 산출하고, 끝에 verifying-spec 게이트를 호출.

**Files:**
- Modify: `skills/writing-plans/SKILL.md`

- [ ] **Step 1: 원본 백업**

```bash
cp skills/writing-plans/SKILL.md skills/writing-plans/SKILL.md.upstream
```
백업은 커밋 안 함. `.gitignore`에 `*.upstream` 추가.

- [ ] **Step 2: 새 본문 작성** — 핵심 변경점

upstream의 플랜 작성 패턴(bite-sized 단계, exact paths, 코드 블록, TDD)은 그대로 유지하되:

```markdown
---
name: writing-plans
description: Use when 요구사항.md and 개발방향.md exist for a feature, before touching code. Reads both, produces 구현계획서.md (단계별 plan with bite-sized TDD tasks). Ends with the main agent's spec verification gate (verifying-spec) — covers 요구사항 + 개발방향 ↔ 구현계획서 consistency + code impact.
---

# Writing Plans → 구현계획서.md

<HARD-GATE>
Both 요구사항.md and 개발방향.md must exist in the current feature folder. If either is missing, instruct the user to run /brainstorm or /design first.
</HARD-GATE>

## Inputs

- `docs/features/<date>-<slug>/요구사항.md`
- `docs/features/<date>-<slug>/개발방향.md`

## Output

`docs/features/<date>-<slug>/구현계획서.md`

## Schema (구현계획서.md)

\`\`\`markdown
# 구현계획서: <피처명>

## 1. 단계별 작업
   ### Task 1: <Component>
   **Files:** Create/Modify/Test
   - [ ] Step 1: <action>
   - [ ] Step 2: <action>
   ...
## 2. 위험 코드 지점
   - <file:line>: <카테고리> | <대응>
## 3. 롤백 전략

---
## 변경이력
\`\`\`

## Bite-Sized Task Granularity (상속 from upstream)

(upstream의 2-5분 단위 step 패턴 그대로 — TDD 사이클: 실패 테스트 → 실행 확인 → 최소 구현 → 통과 확인 → 커밋)

## Process Flow

\`\`\`dot
digraph plan_flow {
    "Read 요구사항.md + 개발방향.md" [shape=box];
    "File structure outline" [shape=box];
    "Decompose into bite-sized tasks" [shape=box];
    "Self-review (spec coverage,\n placeholder, type consistency)" [shape=box];
    "User reviews 구현계획서.md" [shape=diamond];
    "Invoke verifying-spec" [shape=box];
    "Verifier 보고서 → 사용자 결정" [shape=diamond];
    "Invoke change-history" [shape=box];
    "Hand off to /execute-plan" [shape=doublecircle];

    "Read 요구사항.md + 개발방향.md" -> "File structure outline";
    "File structure outline" -> "Decompose into bite-sized tasks";
    "Decompose into bite-sized tasks" -> "Self-review (spec coverage,\n placeholder, type consistency)";
    "Self-review (spec coverage,\n placeholder, type consistency)" -> "User reviews 구현계획서.md";
    "User reviews 구현계획서.md" -> "Self-review (spec coverage,\n placeholder, type consistency)" [label="changes"];
    "User reviews 구현계획서.md" -> "Invoke verifying-spec" [label="approve"];
    "Invoke verifying-spec" -> "Verifier 보고서 → 사용자 결정";
    "Verifier 보고서 → 사용자 결정" -> "Self-review (spec coverage,\n placeholder, type consistency)" [label="fix"];
    "Verifier 보고서 → 사용자 결정" -> "Invoke change-history" [label="proceed"];
    "Invoke change-history" -> "Hand off to /execute-plan";
}
\`\`\`

## No Placeholders (상속 from upstream)

"TBD", "TODO", "implement later", "add appropriate error handling" 절대 금지. 모든 step은 실제 코드/명령/예상 출력 명시.

## Self-Review

upstream 그대로:
1. 스펙 커버리지 — 요구사항.md FR + 개발방향.md 결정마다 task 매핑
2. 플레이스홀더 스캔
3. 타입/시그니처 일관성

## After Save

1. verifying-spec invoke → 요구사항+개발방향 ↔ 구현계획서 정합성 + 코드 임팩트
   - **Tolerance**: verifying-spec skill 미설치 시 호출 skip + 사용자에 notice ("ℹ️ verify-gate 미설치, Phase 2 이후 활성화")
2. 보고서 → 사용자 결정 (verify skip 시 이 단계도 skip)
3. change-history [구현계획서-수정] entry 추가
4. /execute-plan 호출 안내
```

- [ ] **Step 3: 자기 체크리스트**

- HARD-GATE으로 두 입력 MD 부재 시 차단
- 위험 코드 지점 §2 섹션이 risk-annotation 카테고리와 정렬됨
- TDD 패턴 + bite-sized step + no placeholders는 upstream 그대로 상속
- After Save에 verifying-spec + change-history 호출 명시

- [ ] **Step 4: 커밋**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "feat(skill): writing-plans → 구현계획서.md (reads 요구사항+개발방향, with verify gate)"
```

---

### Task 1.8: commands/write-plan.md 수정

- [ ] **Step 1: 본문 갱신**

```markdown
---
description: 요구사항.md + 개발방향.md를 기반으로 구현계획서.md(단계별 TDD plan)를 작성합니다.
---

# /write-plan

이 커맨드는 `writing-plans` skill을 invoke 합니다.

전제: 동일한 피처 폴더에 `요구사항.md` AND `개발방향.md`가 모두 존재.

산출물:
- `docs/features/<날짜>-<slug>/구현계획서.md`
- 메인 에이전트 검증 보고서 (대화로 출력)

다음 단계: `/execute-plan`
```

- [ ] **Step 2: 커밋**

```bash
git add commands/write-plan.md
git commit -m "feat(cmd): /write-plan reads 요구사항+개발방향 → 구현계획서.md"
```

---

### Task 1.9: Phase 1 Acceptance — End-to-End Smoke

**책임:** Phase 1만으로 완전한 3-MD 산출 가능한지 검증.

**Files:**
- Create (temp): `docs/features/2026-05-02-acceptance-smoke/`

- [ ] **Step 1: 가짜 피처로 전체 플로우 시뮬레이션**

세션에서 다음 순서 실행하고 각 결과 확인:

1. `/brainstorm 가입 보너스 지급`
   - 단계별 질문 → answer를 dummy로 진행
   - 결과: `docs/features/2026-05-02-가입-보너스-지급/요구사항.md` 존재
   - 결과: 그 파일 끝에 `## 변경이력` + 첫 entry (`CH-20260502-001`) 존재

2. `/design`
   - 결과: 같은 폴더에 `개발방향.md` 존재
   - 결과: ℹ️ "verify-gate 미설치, Phase 2 이후 활성화" notice 출력 (verify gate는 아직 검증 안 함)
   - 결과: 개발방향.md 끝에 `## 변경이력` + 첫 entry

3. `/write-plan`
   - 결과: 같은 폴더에 `구현계획서.md` 존재
   - 결과: ℹ️ verify-gate skip notice 출력
   - 결과: 구현계획서.md 끝에 `## 변경이력` + 첫 entry

> **Phase 1 한정**: verify gate 출력은 검증 대상이 아님. Phase 2.4 acceptance에서 별도 검증.

- [ ] **Step 2: 산출물 grep 검증**

```bash
ls docs/features/2026-05-02-가입-보너스-지급/
# Expected: 요구사항.md  개발방향.md  구현계획서.md

grep -l "## 변경이력" docs/features/2026-05-02-가입-보너스-지급/*.md
# Expected: 3 files matched

grep -E "CH-20260502-[0-9]{3}" docs/features/2026-05-02-가입-보너스-지급/*.md | wc -l
# Expected: ≥ 3 (각 MD에 최소 1 entry)
```

- [ ] **Step 3: 정리 및 커밋**

```bash
rm -rf docs/features/2026-05-02-가입-보너스-지급
# (실제 acceptance 폴더는 삭제, plan에는 결과 보고만)
git add -A
git commit -m "test(phase-1): acceptance smoke passed (3-MD flow + change history)"
```

**Phase 1 완료 기준:** 위 grep 3개 모두 expected 매치. 하나라도 실패 시 어느 task로 돌아갈지 결정 후 재진행.

---

## Phase 2 — Verification Gate (verifying-spec)

### Task 2.1: verifying-spec skill 작성

**책임:** 메인 에이전트가 직접 수행하는 정합성 + 코드 임팩트 분석 절차 명세.

**Files:**
- Create: `skills/verifying-spec/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
---
name: verifying-spec
description: Use immediately after writing 개발방향.md (via designing-direction) or 구현계획서.md (via writing-plans), before final user handoff. Performs main-agent self-verification — A) 정합성 cross-check between target MD and all upstream MDs, plus C) code impact analysis (file existence, callers, side-effect candidates) — and produces a structured report for user decision.
---

# Verifying Spec (메인 검증 게이트)

<HARD-GATE>
You (main agent) execute this directly. NEVER dispatch a code-reviewer subagent for this skill — the user explicitly requires main-agent verification for context preservation.
EXCEPTION: If code impact analysis requires extensive grep across many files (≥10), you MAY dispatch ONE Explore subagent for read-only impact survey, then synthesize the report yourself.
</HARD-GATE>

## When to Invoke

- After 개발방향.md is written (designing-direction skill)
  - Targets: 요구사항.md ↔ 개발방향.md
- After 구현계획서.md is written (writing-plans skill)
  - Targets: 요구사항.md + 개발방향.md ↔ 구현계획서.md

요구사항.md는 source of truth라 검증 대상 아님.

## Procedure

\`\`\`dot
digraph verify_flow {
    "Read target MD + all upstream MDs" [shape=box];
    "A. 정합성 체크" [shape=box];
    "C. 코드 임팩트 분석" [shape=box];
    "Compose report" [shape=box];
    "Present to user" [shape=diamond];
    "User decides:\nfix / ignore / partial" [shape=diamond];
    "Re-enter previous skill\n(designing-direction or writing-plans)" [shape=box];
    "Proceed" [shape=doublecircle];

    "Read target MD + all upstream MDs" -> "A. 정합성 체크";
    "Read target MD + all upstream MDs" -> "C. 코드 임팩트 분석";
    "A. 정합성 체크" -> "Compose report";
    "C. 코드 임팩트 분석" -> "Compose report";
    "Compose report" -> "Present to user";
    "Present to user" -> "User decides:\nfix / ignore / partial";
    "User decides:\nfix / ignore / partial" -> "Re-enter previous skill\n(designing-direction or writing-plans)" [label="fix"];
    "User decides:\nfix / ignore / partial" -> "Proceed" [label="ignore/partial"];
}
\`\`\`

## A. 정합성 체크 (Consistency)

상위 MD의 모든 FR / 결정 / 위험 항목이 하위에 반영됐는지:

- 요구사항.md FR-N — 개발방향.md §2(영향 컴포넌트) 또는 §4(외부 IF)에 매핑됐나?
- 요구사항.md NFR — 개발방향.md §6(위험) 또는 §7(테스트 전략)에 다뤄졌나?
- 개발방향.md 핵심 결정 §5 — 구현계획서.md task로 매핑됐나?
- 개발방향.md 위험 §6 — 구현계획서.md §2(위험 코드 지점)에 등재됐나?

**누락**: 상위 항목이 하위에서 사라졌으면 보고
**모순**: 상위와 하위의 결정/제약이 충돌하면 보고

## C. 코드 임팩트 분석 (Impact)

대상 MD가 명시한 파일/함수/엔드포인트에 대해:

1. **파일 존재 여부** — Read/Glob로 실재 확인
2. **호출처 매핑** — Grep으로 함수/심볼 사용처 수집
3. **사이드이펙트 후보** — risk-annotation 6-체크리스트 적용
4. **테스트 커버리지** — 해당 파일에 대한 기존 테스트 존재 여부

## Report Format

대화 출력:

\`\`\`
🔍 verifying-spec 보고서 — 대상: 개발방향.md (CH base: 요구사항.md)

## A. 정합성
✅ 매핑 완료 (FR-1, FR-2, FR-3 → §2/§4)
⚠️ 누락 1건
   - 요구사항.md FR-4 "관리자 회수 기능" → 개발방향.md에 등장 없음
❌ 모순 0건

## C. 코드 임팩트
- 영향 파일: src/wallet/service.py, src/api/wallet_routes.py (2)
- 호출처: withdraw() 호출 3곳 (src/admin/, src/cron/, src/api/)
- 위험 후보: side-effect(잔액 -로 가능), race(동시 요청), perf(낙관적 락 미사용)
- 테스트 커버리지: tests/wallet/test_service.py 존재, withdraw 케이스 미커버

## 권장
- FR-4 누락은 개발방향.md §2 추가 또는 요구사항.md에서 명시 제외
- 위험 후보 3건은 개발방향.md §6 보강 권장

진행 / 수정 / 부분 수정 중 선택해주세요.
\`\`\`

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| 보고서 없이 "OK 진행" | 항상 구조화된 보고서 출력 |
| 누락만 보고 | 누락 + 모순 + 임팩트 + 테스트 4축 모두 |
| 서브에이전트로 위임 | NO. 메인이 직접. (광범위 grep만 예외적으로 Explore 1회) |

## Acceptance

- 보고서가 4축(정합성-누락/모순, 임팩트-파일/호출처/위험/테스트) 모두 포함
- 사용자 선택지(진행/수정/부분 수정) 명시
```

- [ ] **Step 2: 자기 체크리스트**

- HARD-GATE에 "메인 직접" 명시
- 4축 검증 절차 모두 기재
- 보고서 포맷 예시 포함
- Exception(광범위 grep만 Explore 허용) 명시

- [ ] **Step 3: 커밋**

```bash
git add skills/verifying-spec/SKILL.md
git commit -m "feat(skill): add verifying-spec (main-agent A+C verification gate)"
```

---

### Task 2.2: designing-direction에서 verifying-spec 호출 강화

이미 1.5의 SKILL.md에 호출 노드가 있지만, 실제 호출 호출 호출 명령부를 명시적 텍스트로 보강.

**Files:**
- Modify: `skills/designing-direction/SKILL.md`

- [ ] **Step 1: "After Save" 섹션에 정확한 호출 절차**

```markdown
## After Save — 메인 검증 게이트 자동 발동

1. 즉시 다음 명령으로 verifying-spec 호출:
   - 입력: target = `docs/features/<...>/개발방향.md`, upstream = `[요구사항.md]`
   - Skill 호출: `verifying-spec`
2. 보고서 출력 후 사용자 응답 대기
3. 사용자 결정:
   - "수정" → 본 skill 재진입(특정 섹션 재대화)
   - "진행" → change-history 호출 → /write-plan 안내
   - "부분 수정" → 어느 항목 수정할지 좁혀 묻고 본 skill 재진입
```

- [ ] **Step 2: 커밋**

```bash
git add skills/designing-direction/SKILL.md
git commit -m "feat(skill): designing-direction explicitly invokes verifying-spec on save"
```

---

### Task 2.3: writing-plans에서 verifying-spec 호출 강화

대칭적 작업.

**Files:**
- Modify: `skills/writing-plans/SKILL.md`

- [ ] **Step 1: "After Save" 섹션 강화**

```markdown
## After Save — 메인 검증 게이트 자동 발동

1. verifying-spec 호출:
   - target = `구현계획서.md`, upstream = `[요구사항.md, 개발방향.md]`
2. 보고서 출력 → 사용자 결정
3. 진행 시 change-history → /execute-plan 안내
```

- [ ] **Step 2: 커밋**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "feat(skill): writing-plans explicitly invokes verifying-spec on save"
```

---

### Task 2.4: Phase 2 Acceptance

- [ ] **Step 1: 시뮬레이션** — Phase 1 acceptance와 같은 더미 피처로 `/design` 마지막에 verifier 보고서가 4축 모두 포함되는지 확인.

- [ ] **Step 2: 결과 기록 + 커밋**

```bash
git commit --allow-empty -m "test(phase-2): verification gate produces 4-axis report"
```

---

## Phase 3 — Change Propagation (cascading)

### Task 3.1: change-propagation skill 작성

**책임:** 자연어 변경 요청 감지 → 변경 레벨 식별 → 영향 매트릭스 적용 → 사용자 승인 → 갱신.

**Files:**
- Create: `skills/change-propagation/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
---
name: change-propagation
description: Use whenever the user expresses a change to existing 요구사항/개발방향/구현계획서/code in a feature folder (natural language like "X 바꿔/추가해/빼" or explicit edit-skill invocation). Identifies the change level, applies the impact matrix to surface affected downstream artifacts, gates user approval, then performs cascading updates and writes change-history entries.
---

# Change Propagation (cascading update)

<HARD-GATE>
NEVER silently update downstream MDs or code without showing the impact list to the user first. Cascading without consent is a data-integrity bug.
</HARD-GATE>

## Trigger Detection

- 자연어: "요구사항 X를 추가/수정/삭제", "개발방향에서 Y 바꿔", "구현계획서 step N 다시"
- 명시 override: "요구사항만, 하위는 건드리지 마" → 메인이 그 지시를 우선

## Change Level Identification

| 사용자 발화 단서 | 변경 레벨 |
|---|---|
| FR / NFR / 사용자 시나리오 / 수용 기준 | 요구사항 |
| 아키텍처 / 컴포넌트 / 데이터 모델 / 결정 / 외부 IF / 위험 / 테스트 전략 | 개발방향 |
| Task 추가/순서/단계 코드/롤백 | 구현계획서 |
| 함수 본문 / 버그 수정 | 코드 |

모호하면 사용자에 한 번 묻기 ("이건 요구사항 변경인가요, 개발방향 변경인가요?")

## Impact Matrix

| 변경 위치 | 자동 영향 검토 대상 |
|---|---|
| 요구사항.md | 개발방향.md + 구현계획서.md + 코드 (구현됐다면) |
| 개발방향.md | 구현계획서.md + 코드 |
| 구현계획서.md | 코드 |
| 코드 | 구현계획서.md 변경이력만 (역방향) |

## Process Flow

\`\`\`dot
digraph propagation {
    "Detect change request" [shape=box];
    "Identify change level" [shape=diamond];
    "Apply impact matrix" [shape=box];
    "Compose impact list\n(어느 MD/코드가 함께 갱신되나)" [shape=box];
    "User approves scope?" [shape=diamond];
    "Apply edits to all approved targets" [shape=box];
    "Cross-link CH-ids\n(연관 항목)" [shape=box];
    "Done" [shape=doublecircle];

    "Detect change request" -> "Identify change level";
    "Identify change level" -> "Apply impact matrix";
    "Apply impact matrix" -> "Compose impact list\n(어느 MD/코드가 함께 갱신되나)";
    "Compose impact list\n(어느 MD/코드가 함께 갱신되나)" -> "User approves scope?";
    "User approves scope?" -> "Apply edits to all approved targets" [label="approved"];
    "User approves scope?" -> "Apply edits to all approved targets" [label="partial → narrowed"];
    "Apply edits to all approved targets" -> "Cross-link CH-ids\n(연관 항목)";
    "Cross-link CH-ids\n(연관 항목)" -> "Done";
}
\`\`\`

## User Approval Format

\`\`\`
변경 요청 감지: 요구사항 변경 ("FR-3 한도 5만원 → 10만원")

영향 매트릭스 적용 결과 — 함께 갱신될 항목:
1. 요구사항.md §3 FR-3 (직접 변경)
2. 개발방향.md §6 위험 (한도 증가에 따른 잔액 검증 강도 재평가)
3. 구현계획서.md Task 4 (한도 검증 로직)
4. 코드 src/wallet/service.py:withdraw() (한도 상수)

진행 / 부분 진행(번호 선택) / 취소 중 선택해주세요.
\`\`\`

## After Approval

각 갱신 대상에 대해:
1. 해당 skill 또는 직접 Edit 적용
2. change-history skill로 entry 추가 (모두 같은 batch CH-id 시리즈에 `연관 항목` 으로 cross-link)

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| "그냥 요구사항만 고치자" 식 cascading 무시 | 영향 매트릭스 적용 → 사용자가 명시 override한 경우만 부분 적용 |
| 모호한 발화에 추측으로 적용 | 한 번은 사용자에 변경 레벨 확인 |
| 코드 직접 수정인데 구현계획서.md 미갱신 | 코드 변경은 항상 구현계획서.md에 [코드-수정] entry 누적 |
```

- [ ] **Step 2: 커밋**

```bash
git add skills/change-propagation/SKILL.md
git commit -m "feat(skill): add change-propagation (cascading edit with user gate)"
```

---

### Task 3.2: Phase 3 Acceptance

- [ ] **Step 1: 시뮬레이션** — Phase 2 더미 피처에서 "FR-3 한도 변경해줘" 자연어로 요청 → 메인이 영향 매트릭스 보고서 출력 → 사용자 승인 시뮬레이션 → 모든 영향 MD에 entry 추가 + 연관 항목 cross-link 확인.

- [ ] **Step 2: 커밋**

```bash
git commit --allow-empty -m "test(phase-3): cascading update gate works for natural-language change request"
```

---

## Phase 4 — Risk Annotation + executing-plans

### Task 4.1: risk-annotation skill 작성

**Files:**
- Create: `skills/risk-annotation/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
---
name: risk-annotation
description: Use during /execute-plan whenever code is created or modified, and during verifying-spec when surveying existing code. Applies a 6-item self-checklist to detect side-effect/race/breaking/perf risks, then attaches standardized "# ⚠️ RISK(category): reason — by context" comments to risky lines and records the placement in change-history.
---

# Risk Annotation (위험 주석 자동 부착)

<HARD-GATE>
Before committing any code edit, you MUST run the 6-item self-checklist below on the changed lines AND the surrounding control flow. If any item triggers, attach a standardized RISK comment to the relevant line BEFORE the commit.
</HARD-GATE>

## Comment Format

\`\`\`python
# ⚠️ RISK(<category>): <reason> — by <context>
\`\`\`

- 카테고리(고정 4종): `side-effect` | `race` | `breaking` | `perf`
- `<reason>`: 자유 한국어
- `<context>`: 권장 default = 현재 피처 슬러그 (예: `by 가입-보너스-지급`). 사용자 override 가능.
- grep 패턴: `RISK\(`

## 6-Item Self-Checklist

각 항목별 트리거 조건과 카테고리:

1. **복잡 분기 / 순서 종속** [side-effect]
   - 트리거: 다중 if/else, switch, early-return, 호출 순서에 의존하는 흐름에 신규/수정 코드 삽입
   - 예: 기존 `process_order()` 함수의 5번째 분기 안에 새 로직 추가 → side-effect 위험
2. **외부 시스템 변경** [side-effect]
   - 트리거: DB write, 파일 I/O, 네트워크 호출, 캐시 invalidate 추가/수정
3. **전역/공유 상태 변경** [race]
   - 트리거: module-level 변수, 싱글턴, 클래스 변수 변경, lock 없는 동시 접근
4. **public 함수 시그니처 / 응답 스키마 변경** [breaking]
   - 트리거: 인자/반환/예외 타입 변경, REST 응답 필드 추가/제거/이름 변경
5. **루프 안에서 쿼리/네트워크 호출** [perf]
   - 트리거: `for/while` 안에서 DB 쿼리 호출, 외부 HTTP, 큰 컬렉션 순회
6. **재귀 / 가변 깊이 순회** [perf]
   - 트리거: 재귀 함수, 입력 깊이가 가변인 트리/그래프 탐색

체크리스트는 **자기 점검(stdin 출력 안 함)** 으로 진행. 사용자에 "위험인지 확인해주세요"라고 묻지 않음 — 메인이 직접 결정.

## Process Flow

\`\`\`dot
digraph risk_flow {
    "Code edit imminent\n(executing-plans context)" [shape=box];
    "Self-checklist (6 items)" [shape=box];
    "Any trigger?" [shape=diamond];
    "Determine category" [shape=box];
    "Compose RISK comment\n(category + reason + context)" [shape=box];
    "Insert comment above the risky line" [shape=box];
    "Set 위험 카테고리 in change-history entry" [shape=box];
    "No annotation" [shape=oval];
    "Done" [shape=doublecircle];

    "Code edit imminent\n(executing-plans context)" -> "Self-checklist (6 items)";
    "Self-checklist (6 items)" -> "Any trigger?";
    "Any trigger?" -> "Determine category" [label="yes"];
    "Any trigger?" -> "No annotation" [label="no"];
    "Determine category" -> "Compose RISK comment\n(category + reason + context)";
    "Compose RISK comment\n(category + reason + context)" -> "Insert comment above the risky line";
    "Insert comment above the risky line" -> "Set 위험 카테고리 in change-history entry";
    "Set 위험 카테고리 in change-history entry" -> "Done";
    "No annotation" -> "Done";
}
\`\`\`

## Existing Code Survey (verifying-spec context)

verifying-spec의 §C 임팩트 분석 단계에서 영향 받는 기존 코드에도 위험 주석 부착 제안 가능:
1. Grep으로 영향 함수/엔드포인트의 호출처 수집
2. 각 호출처에 6-checklist 적용
3. 위험 발견 시 사용자 승인 후 주석 추가 + change-history entry

## Examples

\`\`\`python
# 1. 복잡 분기 + 외부 시스템
def process_order(order):
    if order.status == "pending":
        if order.amount > 100000:
            # ⚠️ RISK(side-effect): 큰 주문 처리 중 결제 게이트웨이 호출 — by 결제-v2
            charge_via_gateway(order)
        ...

# 2. 루프 내 쿼리
def get_summaries(user_ids):
    summaries = []
    for uid in user_ids:
        # ⚠️ RISK(perf): N+1 쿼리 가능 — by 알림-리스트-개선
        summaries.append(db.query("SELECT ... WHERE id=?", uid))
    return summaries

# 3. 응답 스키마 변경
def get_user(user_id):
    user = ...
    # ⚠️ RISK(breaking): 응답에 phone 필드 추가, 클라이언트 호환성 확인 — by 회원-정보-확장
    return {"id": user.id, "name": user.name, "phone": user.phone}
\`\`\`

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| "이건 작은 수정이라 위험 아닐 듯" | 6-checklist 무조건 적용. 0/6이면 부착 안 함, 결정 후. |
| 카테고리 모호 시 회피 | side-effect default. 정확한 분류는 시간 지나며 학습. |
| 주석에 doc 링크 박기 | 구현계획서.md는 사용자 본인용이라 코드 주석에는 빼고, context tag만. |

## Acceptance

- 모든 코드 변경 직전 6-checklist 적용 (실제 부착은 trigger된 경우만)
- 부착된 주석은 grep `RISK\\(` 으로 1개 이상 매치
- 부착된 주석마다 구현계획서.md 변경이력의 [코드-수정] entry에 `위험 카테고리` 필드 채워짐
```

- [ ] **Step 2: 커밋**

```bash
git add skills/risk-annotation/SKILL.md
git commit -m "feat(skill): add risk-annotation (6-item self-checklist + RISK comment format)"
```

---

### Task 4.2: executing-plans skill 수정

**책임:** upstream의 task-by-task 실행 패턴은 유지하되, 코드 변경 직전·후에 risk-annotation + change-history(코드-수정 entry with before/after) 자동 호출.

**Files:**
- Modify: `skills/executing-plans/SKILL.md`

- [ ] **Step 1: 원본 백업**

```bash
cp skills/executing-plans/SKILL.md skills/executing-plans/SKILL.md.upstream
```

- [ ] **Step 2: 추가/수정 핵심 부분**

기존 본문 위에 다음 섹션 삽입(또는 해당 위치에 통합):

```markdown
## Code Edit Discipline (js-superpowers 추가)

<HARD-GATE>
Every code Edit/Write you make during /execute-plan MUST follow this 5-step discipline:
1. Read the target file → capture the **before** snapshot for the affected range
2. Run risk-annotation 6-checklist on the planned change
3. Apply the Edit (insert RISK comment above risky lines as needed)
4. Re-Read or Grep to confirm RISK comments are in place
5. Invoke change-history → append [코드-수정] entry to 구현계획서.md with id/이유/무엇이/영향범위/위험 카테고리/변경 전 코드/변경 후 코드 (full schema per spec §4.1)
NEVER commit code without completing all 5 steps.
</HARD-GATE>

## Process Flow (extension)

\`\`\`dot
digraph exec_extension {
    "Pick next [ ] task" [shape=box];
    "Read target file (before snapshot)" [shape=box];
    "risk-annotation 6-checklist" [shape=box];
    "Apply Edit (with RISK comments)" [shape=box];
    "Verify RISK comments in place" [shape=box];
    "Run tests for this task" [shape=box];
    "All pass?" [shape=diamond];
    "change-history [코드-수정] entry" [shape=box];
    "Commit (frequent, small)" [shape=box];
    "Mark task [x]" [shape=doublecircle];
    "Fix and retry" [shape=box];

    "Pick next [ ] task" -> "Read target file (before snapshot)";
    "Read target file (before snapshot)" -> "risk-annotation 6-checklist";
    "risk-annotation 6-checklist" -> "Apply Edit (with RISK comments)";
    "Apply Edit (with RISK comments)" -> "Verify RISK comments in place";
    "Verify RISK comments in place" -> "Run tests for this task";
    "Run tests for this task" -> "All pass?";
    "All pass?" -> "change-history [코드-수정] entry" [label="yes"];
    "All pass?" -> "Fix and retry" [label="no"];
    "Fix and retry" -> "Apply Edit (with RISK comments)";
    "change-history [코드-수정] entry" -> "Commit (frequent, small)";
    "Commit (frequent, small)" -> "Mark task [x]";
}
\`\`\`

## Anti-Patterns (보강)

| 잘못 | 올바름 |
|---|---|
| Edit 먼저, before snapshot 나중 | 반드시 Edit 전에 Read로 before 캡처. 그래야 history에 정확한 원본 보존 |
| 변경이력 entry는 batch로 모아서 작성 | 매 task 끝마다 즉시 작성. 누락/혼동 방지 |
| 위험 주석 누락하고 commit | HARD-GATE 위반. revert + re-edit |
```

upstream의 plan-loading, task-picking, TDD 등 핵심 메커니즘은 유지.

- [ ] **Step 3: 자기 체크리스트**

- HARD-GATE 5단계 명시
- before snapshot이 history entry 생성 전에 확보됨
- risk-annotation 호출이 명시
- frequent commits 패턴 유지

- [ ] **Step 4: 커밋**

```bash
git add skills/executing-plans/SKILL.md
git commit -m "feat(skill): executing-plans enforces risk-annotation + before/after history per code edit"
```

---

### Task 4.3: commands/execute-plan.md 보강

- [ ] **Step 1: 본문 갱신**

```markdown
---
description: 구현계획서.md를 task-by-task로 실행합니다. 매 코드 변경마다 위험 주석 자동 부착 + 변경 전·후 코드를 변경이력에 보존합니다.
---

# /execute-plan

이 커맨드는 `executing-plans` skill을 invoke 합니다.

전제: 동일 피처 폴더에 `구현계획서.md` 존재.

자동 동작:
- 각 코드 변경 전 before snapshot
- risk-annotation 6-체크리스트 → 필요 시 `# ⚠️ RISK(...)` 주석 자동 부착
- 매 task 완료 후 구현계획서.md 변경이력에 [코드-수정] entry 추가 (변경 전·후 코드 풀 블록)
- frequent commits

다음 단계 (선택): `/api-test`
```

- [ ] **Step 2: 커밋**

```bash
git add commands/execute-plan.md
git commit -m "feat(cmd): /execute-plan documents discipline (risk + history)"
```

---

### Task 4.4: Phase 4 Acceptance

- [ ] **Step 1: 시뮬레이션** — 더미 구현계획서.md(2~3 task)로 `/execute-plan` 실행 → 코드 파일에 RISK 주석 부착 확인 + 구현계획서.md 변경이력에 [코드-수정] entry + 변경 전·후 풀 블록 확인.

```bash
grep -E "# ⚠️ RISK\(" <대상 코드 파일> | wc -l
# Expected: ≥ 1 (위험 후보가 있는 경우)

grep -A 30 "\[코드-수정\]" docs/features/<...>/구현계획서.md | grep -c "변경 전 코드"
# Expected: ≥ 1
```

- [ ] **Step 2: 커밋**

```bash
git commit --allow-empty -m "test(phase-4): risk annotation + before/after history validated"
```

---

## Phase 5 — API Auto-Testing

### Task 5.1: detect_auth.py (TDD)

**책임:** 프로젝트 코드를 Grep으로 스캔해 auth 패턴(JWT 로그인 엔드포인트 / 정적 토큰 / OAuth) 감지. 모호하면 "unknown" 반환.

**Files:**
- Create: `scripts/detect_auth.py`
- Test: `scripts/tests/test_detect_auth.py`

- [ ] **Step 1: 실패 테스트**

```python
from pathlib import Path
from scripts.detect_auth import detect_auth_pattern


def test_detect_jwt_login(tmp_path: Path):
    (tmp_path / "auth.py").write_text(
        "@router.post('/auth/login')\ndef login(...): return {'access_token': ...}\n",
        encoding="utf-8",
    )
    assert detect_auth_pattern(tmp_path).pattern == "jwt-login"


def test_detect_static_env_token(tmp_path: Path):
    (tmp_path / "client.py").write_text(
        "API_TOKEN = os.environ['API_TOKEN']\nheaders={'Authorization': f'Bearer {API_TOKEN}'}\n",
        encoding="utf-8",
    )
    assert detect_auth_pattern(tmp_path).pattern == "static-env-token"


def test_unknown_when_no_signal(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    assert detect_auth_pattern(tmp_path).pattern == "unknown"
```

- [ ] **Step 2: 실행 → FAIL**

```bash
pytest scripts/tests/test_detect_auth.py -v
```
Expected: 3 FAILED

- [ ] **Step 3: 구현**

```python
"""Detect backend auth pattern by scanning project files."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

JWT_LOGIN_RE = re.compile(r"['\"](/auth/login|/login|/sessions|/token)['\"]")
STATIC_TOKEN_RE = re.compile(r"os\.environ\[['\"][A-Z_]*TOKEN[A-Z_]*['\"]\]|os\.getenv\(['\"][A-Z_]*TOKEN[A-Z_]*['\"]")


@dataclass
class AuthDetection:
    pattern: str       # jwt-login | static-env-token | oauth | unknown
    evidence: list[str]


def detect_auth_pattern(project_root: Path) -> AuthDetection:
    evidence: list[str] = []
    for py_file in project_root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if JWT_LOGIN_RE.search(text):
            evidence.append(f"{py_file}: login route")
            return AuthDetection("jwt-login", evidence)
        if STATIC_TOKEN_RE.search(text):
            evidence.append(f"{py_file}: env-var token")
            return AuthDetection("static-env-token", evidence)
    return AuthDetection("unknown", evidence)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest scripts/tests/test_detect_auth.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: 커밋**

```bash
git add scripts/detect_auth.py scripts/tests/test_detect_auth.py
git commit -m "feat(scripts): detect_auth.py — scan project for JWT/static/OAuth auth patterns"
```

---

### Task 5.2: conftest.py.template 작성

**Files:**
- Create: `templates/api-tests/conftest.py.template`

- [ ] **Step 1: 템플릿 작성**

```python
"""
conftest.py — js-superpowers api-tests 공통 fixture.

자동 생성 시 detect_auth.py 결과에 따라 두 블록 중 하나를 선택해 활성화한다.
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest
import requests


BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


# === Block A: jwt-login ===
# (detect_auth가 jwt-login 패턴을 발견했을 때 활성화)
@pytest.fixture(scope="session")
def auth_token() -> str:
    """Login once per session and reuse the token."""
    creds = {
        "email": os.environ.get("TEST_USER_EMAIL"),
        "password": os.environ.get("TEST_USER_PASSWORD"),
    }
    if not creds["email"] or not creds["password"]:
        pytest.skip("TEST_USER_EMAIL / TEST_USER_PASSWORD env vars required")
    r = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


# === Block B: static-env-token ===
# (detect_auth가 static-env-token일 때 활성화)
# @pytest.fixture(scope="session")
# def auth_token() -> str:
#     token = os.environ.get("API_TOKEN")
#     if not token:
#         pytest.skip("API_TOKEN env var required")
#     return token


@pytest.fixture
def api_client(auth_token: str) -> Iterator[requests.Session]:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {auth_token}"})
    yield s
    s.close()


# === Test data fixtures ===
# api-auto-testing skill이 사용자가 paste한 SQL 결과를 여기에 채워준다.
# 예시:
# @pytest.fixture
# def test_user() -> dict:
#     return {"id": 12345, "email": "test@example.com"}
```

- [ ] **Step 2: 커밋**

```bash
git add templates/api-tests/conftest.py.template
git commit -m "feat(template): conftest.py with jwt-login / static-token toggleable blocks"
```

---

### Task 5.3: api-auto-testing skill 작성

**Files:**
- Create: `skills/api-auto-testing/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
---
name: api-auto-testing
description: Use when /api-test is invoked after /execute-plan has implemented APIs. Drives the 6-step pipeline — API inventory from 구현계획서.md and code → SQL guides for test data acquisition (user pastes results) → pytest scenario code generation (with conftest.py auth fixture auto-selected via detect_auth.py) → execution → result recording in 구현계획서.md change-history → fail-handling proposal.
---

# API Auto-Testing Pipeline

<HARD-GATE>
Triggered ONLY by explicit /api-test (no auto-run). DB access is via SQL-paste only — NEVER use MCP DB connectors or run SQL through the user's DB credentials directly. The user pastes SQL results into the conversation.
</HARD-GATE>

## When to Invoke

- 사용자가 `/api-test` 슬래시 호출
- 직전 `/execute-plan`으로 구현계획서.md에 적힌 API가 구현됨

## Pipeline

\`\`\`dot
digraph api_test {
    "1. API inventory" [shape=box];
    "2. SQL guide for test data" [shape=box];
    "3. User pastes SQL results" [shape=box];
    "4. Generate scenario code\n(conftest + scenario-NNN.py)" [shape=box];
    "5. Execute pytest" [shape=box];
    "6. Record results in change-history" [shape=box];
    "Any failures?" [shape=diamond];
    "Propose code-fix re-execute-plan" [shape=box];
    "Done" [shape=doublecircle];

    "1. API inventory" -> "2. SQL guide for test data";
    "2. SQL guide for test data" -> "3. User pastes SQL results";
    "3. User pastes SQL results" -> "4. Generate scenario code\n(conftest + scenario-NNN.py)";
    "4. Generate scenario code\n(conftest + scenario-NNN.py)" -> "5. Execute pytest";
    "5. Execute pytest" -> "6. Record results in change-history";
    "6. Record results in change-history" -> "Any failures?";
    "Any failures?" -> "Propose code-fix re-execute-plan" [label="yes"];
    "Any failures?" -> "Done" [label="no"];
}
\`\`\`

## Step 1 — API Inventory

- 구현계획서.md `## 1. 단계별 작업` task에서 새로 만든/수정된 endpoint 식별
- 코드(`src/**/*.py` 등) Grep으로 라우터 데코레이터 매핑(`@router.post`, `@app.get` 등)
- 각 endpoint별로: method, path, path/query/body params, 인증 필요 여부 정리

## Step 2 — SQL Guide for Test Data

각 endpoint에 필요한 데이터(예: user_id, product_id, order_id) 식별 후 사용자에 SQL 제시:

\`\`\`
필요한 테스트 데이터를 백엔드 DB에서 조회 후 결과를 paste 해주세요:

-- active 사용자 1명 (정상 케이스)
SELECT id, email FROM users WHERE status='active' AND deleted_at IS NULL LIMIT 1;

-- 재고 있는 상품 1개
SELECT id, name, stock FROM products WHERE stock > 0 LIMIT 1;
\`\`\`

사용자 paste → 메인이 변수로 보존.

## Step 3 — Auto-Detect Auth

```bash
python -m scripts.detect_auth .
```

결과에 따라 conftest.py.template의 적절한 블록 활성화:
- `jwt-login` → Block A (login fixture)
- `static-env-token` → Block B (env var fixture)
- `unknown` → 사용자에 질문 ("어떻게 인증하나요? 로그인 엔드포인트 있나요?")

## Step 4 — Scenario Code Generation

생성 위치: `docs/features/<...>/api-tests/`

- `conftest.py` ← template + 사용자 paste 데이터 fixture 자동 추가
- `scenario-001-<endpoint>.py` ← happy path 1개
- `scenario-002-<endpoint>-edge.py` ← edge case 2~3 (잘못된 입력/권한/존재하지 않는 ID)

예시 시나리오:

\`\`\`python
# scenario-001-withdraw.py
def test_withdraw_success(api_client, test_user, test_product):
    r = api_client.post(
        "/api/wallet/withdraw",
        json={"user_id": test_user["id"], "amount": 1000},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["balance"] >= 0
    assert "transaction_id" in body
\`\`\`

## Step 5 — Execute

```bash
pytest docs/features/<...>/api-tests/scenario-*.py \
       -v --tb=short \
       --json-report \
       --json-report-file=docs/features/<...>/api-tests/results/$(date +%Y-%m-%d-%H%M).json
```

의존성 미설치 시 `pip install pytest requests pytest-json-report` 안내 후 재실행.

## Step 6 — Record Results

change-history skill로 [API테스트] entry를 구현계획서.md에 추가 (spec §4.2 풀 스키마):

\`\`\`markdown
### [2026-05-02 15:30] [API테스트]
- **id**: CH-20260502-009
- **시나리오 파일**: api-tests/scenario-001-withdraw.py (4 tests)
- **결과**: PASS 3 / FAIL 1 / ERROR 0
- **실패 상세**: test_withdraw_negative_amount → 422 기대, 200 응답
- **결과 파일**: api-tests/results/2026-05-02-1530.json
- **다음 액션**: 음수 amount 검증 누락 → /execute-plan 재진입 권장
\`\`\`

## Failure Handling

실패 시 메인이 사용자에 제안:

\`\`\`
1건 실패 — test_withdraw_negative_amount 가 음수 amount에 대해 422를 기대했으나 200을 받았습니다.
원인: src/wallet/service.py의 withdraw에 음수 검증 누락으로 보입니다.

선택:
A) /execute-plan 재진입 → 수정 후 재테스트
B) 시나리오 자체가 잘못 → 시나리오 코드 수정
C) 무시하고 마무리
\`\`\`

## Anti-Patterns

| 잘못 | 올바름 |
|---|---|
| MCP로 DB 직접 쿼리 | NO. SQL paste 방식만 (보안) |
| 시크릿을 시나리오 파일에 박기 | env var 또는 .env.test (.gitignore 등록) |
| FAIL 무시하고 PASS만 보고 | 모든 실패 상세 보고 + 다음 액션 제안 |

## Acceptance

- 시나리오 파일 ≥ 1개 생성
- pytest 실행 → JSON 리포트 생성
- 구현계획서.md 변경이력에 [API테스트] entry 추가됨
```

- [ ] **Step 2: 커밋**

```bash
git add skills/api-auto-testing/SKILL.md
git commit -m "feat(skill): add api-auto-testing (SQL-paste → pytest scenario → execute → record)"
```

---

### Task 5.4: commands/api-test.md 작성

- [ ] **Step 1: 본문 작성**

```markdown
---
description: 구현된 API에 대해 자동 테스트를 진행합니다. 메인이 SQL을 안내하고, 사용자가 결과를 paste 하면 pytest 시나리오를 생성·실행합니다.
---

# /api-test

이 커맨드는 `api-auto-testing` skill을 invoke 합니다.

전제: 동일 피처 폴더에 `구현계획서.md` 존재 + 코드 구현 완료 (`/execute-plan` 끝).

흐름:
1. API 인벤토리 추출
2. 메인이 테스트 데이터 SQL 제시 → 사용자가 paste
3. 시나리오 코드 자동 생성
4. pytest 실행 → JSON 결과
5. 구현계획서.md 변경이력에 결과 누적
6. 실패 시 재실행 제안

산출물:
- `docs/features/<날짜>-<slug>/api-tests/scenario-*.py`
- `docs/features/<날짜>-<slug>/api-tests/results/*.json`
- 구현계획서.md 변경이력 [API테스트] entry
```

- [ ] **Step 2: 커밋**

```bash
git add commands/api-test.md
git commit -m "feat(cmd): add /api-test command"
```

---

### Task 5.5: Phase 5 Acceptance — pytest-httpserver mock 백엔드 사용

**전제:** 실 백엔드가 없는 dev env에서 시나리오를 실제로 실행하려면 mock 백엔드가 필요. `pytest-httpserver` 픽스처로 in-process 서버 띄움.

- [ ] **Step 1: acceptance 전용 conftest 보강 — mock 서버 fixture**

`docs/features/2026-05-02-acceptance-smoke/api-tests/conftest.py` (acceptance 한정 오버라이드, 정상 사용 시엔 templates의 conftest 그대로):

```python
import pytest
from pytest_httpserver import HTTPServer

@pytest.fixture(scope="session")
def mock_backend(httpserver: HTTPServer):
    # 가짜 GET /api/users/<id>
    httpserver.expect_request("/api/users/12345").respond_with_json(
        {"id": 12345, "email": "test@example.com"}
    )
    return httpserver

@pytest.fixture
def base_url(mock_backend) -> str:
    return mock_backend.url_for("")

@pytest.fixture(scope="session")
def auth_token() -> str:
    return "mock-token-acceptance"
```

원본 conftest의 `BASE_URL` env var 의존을 acceptance 한정으로 base_url fixture 로 override.

- [ ] **Step 2: 더미 API 시나리오 생성**

`/api-test` 호출로 메인이 시나리오 생성. 가상의 endpoint = `GET /api/users/<id>`, 사용자 paste = `{"id": 12345, "email": "test@example.com"}`.

생성될 `scenario-001-get-user.py` 예시:
```python
def test_get_user_success(api_client, base_url, test_user):
    r = api_client.get(f"{base_url}/api/users/{test_user['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == test_user["id"]
```

- [ ] **Step 3: pytest 실행 (mock 백엔드 위에서)**

```bash
cd docs/features/2026-05-02-acceptance-smoke
pytest api-tests/ -v --json-report --json-report-file=api-tests/results/acceptance.json
```
Expected: 1 passed, JSON 결과 파일 생성

- [ ] **Step 4: grep 검증**

```bash
ls docs/features/2026-05-02-acceptance-smoke/api-tests/scenario-*.py | wc -l
# Expected: ≥ 1

ls docs/features/2026-05-02-acceptance-smoke/api-tests/results/*.json | wc -l
# Expected: ≥ 1

grep -c "\[API테스트\]" docs/features/2026-05-02-acceptance-smoke/구현계획서.md
# Expected: ≥ 1
```

- [ ] **Step 3: 커밋**

```bash
git commit --allow-empty -m "test(phase-5): api-auto-testing pipeline validated"
```

---

## Phase 6 — End-to-End + Polish

### Task 6.1: 전체 플로우 스모크 (한 피처 통째로)

- [ ] **Step 1: 가상의 피처 "출금 한도 알림" 으로 처음부터 끝까지**

세션에서 다음 순서:

1. `/brainstorm 출금 한도 알림`
2. `/design`
3. `/write-plan`
4. `/execute-plan` (간단한 더미 함수 추가, 위험 주석 부착, 변경이력 누적 확인)
5. `/api-test` (Task 5.5와 동일하게 `pytest-httpserver` mock 백엔드 사용 — 출금 알림 API mock으로 등록)

각 단계 끝마다:
- 산출물 파일 존재 확인
- 변경이력 entry 누적 확인 (CH-id 시퀀스 끊김 없는지)

- [ ] **Step 2: 변경 전파 시나리오 검증**

`/brainstorm` 후 "FR-2 한도 변경해줘" 자연어 입력 → cascading 영향 매트릭스 출력 → 부분 승인 → 영향 받은 MD에 entry 추가 + `연관 항목` cross-link 검증.

- [ ] **Step 3: 결과 보고서 작성**

`docs/superpowers/specs/2026-05-02-js-superpowers-acceptance-report.md` 생성 — 각 Phase별 acceptance 결과 + 발견된 결함 + fix 커밋 리스트.

- [ ] **Step 4: 커밋**

```bash
git add docs/superpowers/specs/2026-05-02-js-superpowers-acceptance-report.md
git commit -m "test(e2e): full pipeline smoke (5 commands + cascading propagation)"
```

---

### Task 6.2: README 갱신 — 실제 예시 추가

- [ ] **Step 1: README의 "첫 사용 빠른 시작" 섹션을 Task 6.1 실제 결과로 갱신**

각 단계의 실제 출력 예시(요구사항.md 일부, 변경이력 entry 예시 등) 인라인.

- [ ] **Step 2: 커밋**

```bash
git add README.md
git commit -m "docs(readme): add real-world quickstart from acceptance smoke"
```

---

### Task 6.3: 최종 plugin.json + version bump

- [ ] **Step 1: version bump 0.1.0 → 0.1.0 (확정 release tag)**

`.claude-plugin/plugin.json` 의 `version` 그대로 0.1.0 유지 (이미 작성). 단, 최종 변경분이 있으면 커밋.

- [ ] **Step 2: README에 최종 install + acceptance 통과 명시**

- [ ] **Step 3: 커밋 + 태그**

```bash
git add -A
git commit -m "chore: js-superpowers v0.1.0 release"
git tag v0.1.0
```

---

## 진행 추적 체크리스트

- [ ] Phase 0 — Bootstrap + Dev Install (2 tasks)
- [ ] Phase 1 — 3-MD Workflow + Change History (9 tasks, verify-gate stub 모드)
- [ ] Phase 2 — Verification Gate 활성화 (4 tasks)
- [ ] Phase 3 — Change Propagation (2 tasks)
- [ ] Phase 4 — Risk Annotation + executing-plans (4 tasks)
- [ ] Phase 5 — API Auto-Testing (5 tasks, mock 백엔드 사용)
- [ ] Phase 6 — End-to-End + Polish (3 tasks)

**총 29 tasks. 예상 소요: 10~15 세션 (한 세션에 한 Phase 정도가 안전).**

---

## Risk Register (이 plan 자체의 위험)

- ⚠️ **upstream brainstorming/writing-plans/executing-plans skill 본문 수정 시 의도치 않은 동작 변화** — 백업 파일(`*.upstream`) 보유로 비교 가능, 각 수정 후 acceptance 시뮬레이션 필수
- ⚠️ **change-history와 git history 중복** — 의도된 중복(스키마와 의도 정보 보존). 로직 충돌 없음
- ⚠️ **api-auto-testing이 실제 백엔드에 영향** — local/staging 환경에서만 실행, prod URL은 명시적 차단(detect_auth.py 또는 conftest 수준에서 환경 체크 권장)
- ⚠️ **`detect_auth.py` regex가 단순함** — `/auth/login`·`/login`만 매치, `os.environ['*TOKEN*']` 패턴만 식별. 실제 다수 프로젝트는 `/api/v1/auth/login`, `/users/sessions`, GraphQL `login` mutation, `API_KEY`·`BEARER_*`·`SECRET_*` 등 false negative 다수. **v0.1.0 한계로 수용** — `unknown` 반환 시 사용자에 직접 묻는 흐름이 fallback. v0.2.0에서 패턴 확장 예정.
- ⚠️ **구현계획서.md bloat** — 매 코드 변경마다 변경 전·후 풀 코드 블록 누적 (spec §4.1 사용자 결정). 50회 변경 시 수천 줄. 운영 중 "큰 변경(>50줄)은 외부 patch 파일 링크" 같은 압축 장치 필요해질 수 있음 — v0.2.0 이후 §11에 검토 항목 추가 권장.
- ⚠️ **change-history 강제는 soft enforcement** — HARD-GATE 문구로 "반드시 entry 추가"라고 적었지만, skill 시스템은 모델의 자율 호출 기반이라 결정적 강제 X. 메인이 invoke 안 하면 entry 누락 가능. 보강책: `/execute-plan` 등 wrapper 커맨드 본문에 명시적 호출 절차 굵게 강조 + 각 acceptance에서 entry 누락 여부를 grep으로 검증 (이 plan에 이미 포함).
- ⚠️ **세션 추정(7~10) 낙관적** — 각 skill 본문이 한국어 prose 100~200줄. 작성·자기 리뷰·로드 검증 시간 고려 시 실제 **10~15 세션** 가능성. 계획 시 여유 두기.

---

## 후속 spec

이 plan으로 v0.1.0 출시 후 §11/§12 항목(사용자 정의 위험 카테고리 / MCP DB 옵션)은 별도 spec → plan으로 진행.
