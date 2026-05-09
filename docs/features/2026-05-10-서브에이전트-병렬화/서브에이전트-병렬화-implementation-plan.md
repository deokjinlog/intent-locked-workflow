---
commit_policy: per-task
---

# 서브에이전트 병렬화 구현계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `js-super-subagent-driven-development` 가 plan 의 task 들을 DAG 기반 wave 로 병렬 dispatch 하고, 각 task 의 implementer 모델을 plan 의 `**Model**:` 필드대로 dynamic 선택하도록 확장.

**Architecture:** 메인이 plan 분석 → DAG 추론 (Kahn topological sort) → wave 단위 pair-parallel dispatch (impl + spec-reviewer) → wave 끝에서 직렬 commit + post-hoc manifest 비교로 충돌 검출. 기존 v1.1.7 end-of-run consolidator 흐름 유지.

**Tech Stack:** Python 3.13 (helper + tests), Markdown skill 본문, bash (version bump).

**Spec inputs:**
- `서브에이전트-병렬화-requirements.md` — 11개 design decision (D1~D11), 6개 수용 기준
- `서브에이전트-병렬화-tech-design.md` — 8개 영향 파일, 8개 tech 결정 (D-T1~D-T8), 8개 위험 (R1~R8), 12개 fixture (F1~F5 + G1~G7)

**Bootstrap 주의:** 본 plan 의 변경이 이 plan 자체를 실행하는 skill 의 동작을 변경. 따라서 본 plan 은 **현재 v1.1.13 sequential 패턴으로 실행** (`/execute-plan` 인라인 또는 v1.1.13 `js-super-subagent-driven-development` 직렬). 신규 wave 동작은 다음 피처부터 자연스럽게 적용. v1.1.7 self-validation 패턴 따라감.

---

## 1. 단계별 작업

### Task 1: scripts/dag_builder.py — Task / Wave dataclass + build_waves (TDD)

**Files:**
- Create: `scripts/dag_builder.py`
- Test: `scripts/tests/test_dag_builder.py`

**Model**: haiku

- [ ] **Step 1: Write the failing test for Task / Wave dataclasses**

Append to `scripts/tests/test_dag_builder.py`:

```python
from scripts.dag_builder import Task, Wave


def test_task_dataclass_default_model_sonnet():
    t = Task(id=1, name="Foo", files=["a.py"], deps=[])
    assert t.model == "sonnet"


def test_wave_dataclass_holds_tasks():
    t1 = Task(id=1, name="Foo", files=["a.py"], deps=[])
    t2 = Task(id=2, name="Bar", files=["b.py"], deps=[])
    w = Wave(index=1, tasks=[t1, t2])
    assert len(w.tasks) == 2
    assert w.index == 1
```

- [ ] **Step 2: Run test — expect ImportError**

Run: `source .venv/bin/activate && pytest scripts/tests/test_dag_builder.py -v`
Expected: ImportError (module doesn't exist)

- [ ] **Step 3: Create dag_builder.py with dataclasses**

**수정 후** (new file: `scripts/dag_builder.py`):

```python
"""DAG builder for js-super-subagent-driven-development wave scheduling.

Reads a plan's task list (with files + deps) and produces wave groupings
where tasks within a wave can run in parallel without file conflicts or
dependency violations.
"""
from dataclasses import dataclass, field


@dataclass
class Task:
    id: int
    name: str
    files: list[str]
    deps: list[int] = field(default_factory=list)
    model: str = "sonnet"


@dataclass
class Wave:
    index: int
    tasks: list[Task]
```

- [ ] **Step 4: Run test — expect PASS**

Run: `pytest scripts/tests/test_dag_builder.py -v`
Expected: 2 PASS

- [ ] **Step 5: Add failing test for build_waves (linear deps)**

Append:

```python
from scripts.dag_builder import build_waves


def test_build_waves_linear_deps():
    """Task 2 depends on Task 1 → 2 waves of 1 task each."""
    t1 = Task(id=1, name="A", files=["a.py"], deps=[])
    t2 = Task(id=2, name="B", files=["b.py"], deps=[1])
    waves = build_waves([t1, t2])
    assert len(waves) == 2
    assert [t.id for t in waves[0].tasks] == [1]
    assert [t.id for t in waves[1].tasks] == [2]


def test_build_waves_independent_files():
    """3 tasks no deps, no file overlap → 1 wave with all 3."""
    tasks = [
        Task(id=1, name="A", files=["a.py"]),
        Task(id=2, name="B", files=["b.py"]),
        Task(id=3, name="C", files=["c.py"]),
    ]
    waves = build_waves(tasks)
    assert len(waves) == 1
    assert {t.id for t in waves[0].tasks} == {1, 2, 3}


def test_build_waves_file_conflict_serializes():
    """Tasks 2 and 3 both touch foo.py → 3 waves (DAG forces serialize)."""
    tasks = [
        Task(id=1, name="A", files=["a.py"]),
        Task(id=2, name="B", files=["foo.py"]),
        Task(id=3, name="C", files=["foo.py"]),
    ]
    waves = build_waves(tasks)
    # task 1 alone in wave 1, task 2 wave 2, task 3 wave 3
    assert len(waves) >= 2
    # tasks 2 and 3 must NOT be in the same wave
    for wave in waves:
        ids = {t.id for t in wave.tasks}
        assert not (2 in ids and 3 in ids)
```

- [ ] **Step 6: Run — expect AttributeError on build_waves**

Run: `pytest scripts/tests/test_dag_builder.py -v`
Expected: 3 new tests fail (build_waves not implemented).

- [ ] **Step 7: Implement build_waves (Kahn topological sort + file overlap)**

**원본** (`scripts/dag_builder.py:1-22`):

```python
"""DAG builder for js-super-subagent-driven-development wave scheduling.

Reads a plan's task list (with files + deps) and produces wave groupings
where tasks within a wave can run in parallel without file conflicts or
dependency violations.
"""
from dataclasses import dataclass, field


@dataclass
class Task:
    id: int
    name: str
    files: list[str]
    deps: list[int] = field(default_factory=list)
    model: str = "sonnet"


@dataclass
class Wave:
    index: int
    tasks: list[Task]
```

**수정 후**:

```python
"""DAG builder for js-super-subagent-driven-development wave scheduling.

Reads a plan's task list (with files + deps) and produces wave groupings
where tasks within a wave can run in parallel without file conflicts or
dependency violations.
"""
from dataclasses import dataclass, field


@dataclass
class Task:
    id: int
    name: str
    files: list[str]
    deps: list[int] = field(default_factory=list)
    model: str = "sonnet"


@dataclass
class Wave:
    index: int
    tasks: list[Task]


def build_waves(tasks: list[Task]) -> list[Wave]:
    """Kahn's algorithm + file-overlap secondary serialization.

    Within an indegree-zero candidate set, tasks that touch the same file
    are split: only one of them goes into the current wave (plan order
    earliest), others wait for next wave even though deps are satisfied.
    """
    by_id = {t.id: t for t in tasks}
    indeg = {t.id: len(t.deps) for t in tasks}
    waves: list[Wave] = []
    placed: set[int] = set()

    while len(placed) < len(tasks):
        # candidates: indeg 0 and not yet placed
        candidates = [
            by_id[tid] for tid, deg in indeg.items()
            if deg == 0 and tid not in placed
        ]
        if not candidates:
            raise ValueError("Cyclic deps in tasks")

        # plan order
        candidates.sort(key=lambda t: t.id)

        # split by file overlap: greedy file-disjoint subset
        wave_tasks: list[Task] = []
        used_files: set[str] = set()
        for cand in candidates:
            if any(f in used_files for f in cand.files):
                continue
            wave_tasks.append(cand)
            used_files.update(cand.files)

        if not wave_tasks:
            raise ValueError("Unable to place any task in wave (logic bug)")

        wave = Wave(index=len(waves) + 1, tasks=wave_tasks)
        waves.append(wave)

        for t in wave_tasks:
            placed.add(t.id)

        # decrement indegree for newly placed tasks' downstream
        for tid, t in by_id.items():
            if tid in placed:
                continue
            for dep in t.deps:
                if dep in placed:
                    indeg[tid] -= 1
                    # ensure not going below 0 due to multi-decrement
                    if indeg[tid] < 0:
                        indeg[tid] = 0

    return waves
```

- [ ] **Step 8: Run all tests — expect PASS**

Run: `pytest scripts/tests/test_dag_builder.py -v`
Expected: 5 PASS

- [ ] **Step 9: Commit**

```bash
git add scripts/dag_builder.py scripts/tests/test_dag_builder.py
git commit -m "feat(v1.1.14): add dag_builder Task/Wave + build_waves with Kahn topo sort"
```

---

### Task 2: scripts/dag_builder.py — detect_conflicts (post-hoc) + edge cases (TDD)

**Files:**
- Modify: `scripts/dag_builder.py:60-` (add `detect_conflicts`)
- Modify: `scripts/tests/test_dag_builder.py` (append cases)

**Model**: haiku

- [ ] **Step 1: Failing test for detect_conflicts**

Append to `scripts/tests/test_dag_builder.py`:

```python
from scripts.dag_builder import detect_conflicts


def test_detect_conflicts_disjoint_returns_empty():
    """Two manifests touching different files → no conflicts."""
    manifests = {
        1: ["a.py", "b.py"],
        2: ["c.py", "d.py"],
    }
    assert detect_conflicts(manifests) == []


def test_detect_conflicts_shared_file_returns_pair():
    """Two manifests overlap on b.py → conflict pair (1, 2, 'b.py')."""
    manifests = {
        1: ["a.py", "b.py"],
        2: ["b.py", "c.py"],
    }
    conflicts = detect_conflicts(manifests)
    assert (1, 2, "b.py") in conflicts


def test_detect_conflicts_three_way_overlap():
    """Three manifests share x.py → 3 pairwise conflicts."""
    manifests = {
        1: ["x.py"],
        2: ["x.py"],
        3: ["x.py"],
    }
    conflicts = detect_conflicts(manifests)
    assert len(conflicts) == 3
```

- [ ] **Step 2: Run — expect ImportError**

Run: `pytest scripts/tests/test_dag_builder.py -v`
Expected: 3 new tests fail (detect_conflicts not defined).

- [ ] **Step 3: Implement detect_conflicts**

**원본** (`scripts/dag_builder.py:end of file`):

```python
        for tid, t in by_id.items():
            if tid in placed:
                continue
            for dep in t.deps:
                if dep in placed:
                    indeg[tid] -= 1
                    if indeg[tid] < 0:
                        indeg[tid] = 0

    return waves
```

**수정 후** (append after `build_waves`):

```python
        for tid, t in by_id.items():
            if tid in placed:
                continue
            for dep in t.deps:
                if dep in placed:
                    indeg[tid] -= 1
                    if indeg[tid] < 0:
                        indeg[tid] = 0

    return waves


def detect_conflicts(
    manifests: dict[int, list[str]],
) -> list[tuple[int, int, str]]:
    """Post-hoc file-conflict detection across same-wave manifests.

    Returns list of (task_id_a, task_id_b, shared_file) tuples for every
    pair of manifests that touched the same file. Empty list = no conflict.

    Caller (main agent at wave finalization) uses this to decide rollback
    of the later task (plan order). See tech-design D-T2.
    """
    conflicts: list[tuple[int, int, str]] = []
    ids = sorted(manifests.keys())
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = set(manifests[a]) & set(manifests[b])
            for path in sorted(shared):
                conflicts.append((a, b, path))
    return conflicts
```

- [ ] **Step 4: Run — expect PASS**

Run: `pytest scripts/tests/test_dag_builder.py -v`
Expected: 8 PASS total.

- [ ] **Step 5: Commit**

```bash
git add scripts/dag_builder.py scripts/tests/test_dag_builder.py
git commit -m "feat(v1.1.14): dag_builder.detect_conflicts for post-hoc manifest comparison"
```

---

### Task 3: skills/writing-plans/SKILL.md — `**Model**:` 필드 + 평가 룰

**Files:**
- Modify: `skills/writing-plans/SKILL.md` (Task Structure 섹션 + 신규 "Task Model Hint" 섹션)

**Model**: sonnet

- [ ] **Step 1: Locate Task Structure section**

Run: `grep -n "## Task Structure" skills/writing-plans/SKILL.md`
Expected: line 109 (or similar — confirm before edit).

- [ ] **Step 2: Add Model field to task structure example**

**원본** (`skills/writing-plans/SKILL.md:111-117`):

```markdown
### Task N: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`
```

**수정 후**:

```markdown
### Task N: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Model**: haiku
```

- [ ] **Step 3: Insert new "Task Model Hint" section AFTER "Task Structure" section, BEFORE "Code Block Convention"**

**수정 후** (new section, insert after line ~150 inside `## Task Structure (inherited)`):

```markdown
## Task Model Hint (v1.1.14+)

Each task block MAY include `**Model**: haiku | sonnet | opus` to tell `js-super-subagent-driven-development` which model to dispatch the implementer with. Spec-reviewer is always sonnet (NOT controlled by this field).

Evaluation rule:

| 신호 | 모델 |
|---|---|
| 1-2 파일 + mechanical implementation + 명확 spec | haiku |
| 다중 파일 통합 / 디버깅 / 패턴 매칭 | sonnet |
| Korean prose 조작 (skill 본문 / MD 편집) | sonnet (Haiku rephrasing 위험) |
| 설계 / 광범위 코드베이스 이해 | opus |
| 누락 / 모호 | sonnet (보수 디폴트) |

Backward compat: If the field is omitted, `js-super-subagent-driven-development` defaults to `sonnet`. Existing plans (v1.1.13 and earlier) work as-is.

Anti-pattern: setting `Model: haiku` for a task that touches Korean prose in skill bodies. Haiku has a known rephrasing risk on Korean text — see `skills/docs-pretty/SKILL.md:50` for the same constraint.
```

- [ ] **Step 4: Verify edit**

Run: `grep -n "Task Model Hint" skills/writing-plans/SKILL.md`
Expected: 1 match (new section header).

Run: `grep -A2 "Test: \`tests/exact" skills/writing-plans/SKILL.md`
Expected: shows `**Model**: haiku` line right after Test path.

- [ ] **Step 5: Commit**

```bash
git add skills/writing-plans/SKILL.md
git commit -m "feat(v1.1.14): writing-plans task schema — add Model: hint field + eval rule"
```

---

### Task 4: skills/js-super-subagent-driven-development/implementer-prompt.md — `{{MODEL}}` placeholder + DO NOT commit

**Files:**
- Modify: `skills/js-super-subagent-driven-development/implementer-prompt.md`

**Model**: sonnet

- [ ] **Step 1: Locate the model line**

Run: `grep -n 'model:' skills/js-super-subagent-driven-development/implementer-prompt.md`
Expected: line 7 — `model: "sonnet"`.

- [ ] **Step 2: Replace model line with placeholder**

**원본** (`skills/js-super-subagent-driven-development/implementer-prompt.md:7`):

```
  model: "sonnet"   # default — override to "haiku" for trivial mechanical tasks, or "opus" for design-heavy tasks. See SKILL.md "Model Selection".
```

**수정 후**:

```
  model: "{{MODEL}}"   # Main injects per-task value from plan's `**Model**:` field; defaults to "sonnet" if missing. See SKILL.md "Model Selection" + writing-plans "Task Model Hint".
```

- [ ] **Step 3: Replace "Commit your work" instruction with NO-COMMIT rule**

**원본** (`skills/js-super-subagent-driven-development/implementer-prompt.md:50-58`):

```
    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify implementation works
    4. Commit your work (multi-commit OK — main captures BASE_SHA before dispatch)
    5. Self-review (see below)
    6. Report back
```

**수정 후**:

```
    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify implementation works (run tests in working tree, no commit)
    4. **DO NOT git commit** — main agent commits at wave end in plan order
    5. Self-review (see below)
    6. Report back

    ## Why no commit

    In v1.1.14+ wave-parallel mode, multiple implementers may run concurrently.
    To keep wave commits in plan order (and avoid race), the main agent stages +
    commits each task's working-tree changes at wave finalization. Your job is
    to leave the working tree in the right state with manifest written; main
    handles git from there.
```

- [ ] **Step 4: Add commit-avoidance check to Self-review**

**원본** (`skills/js-super-subagent-driven-development/implementer-prompt.md:118-121`):

```
    **Governance hands-off:**
    - Did I avoid adding RISK comments? (main does this)
    - Did I leave 변경이력 footer untouched? (main does this)
```

**수정 후**:

```
    **Governance hands-off:**
    - Did I avoid adding RISK comments? (main does this)
    - Did I leave 변경이력 footer untouched? (main does this)
    - **Did I avoid `git commit`?** (main does this at wave end)
```

- [ ] **Step 5: Verify edits**

Run: `grep -n 'MODEL\|DO NOT git commit\|Did I avoid \`git commit\`' skills/js-super-subagent-driven-development/implementer-prompt.md`
Expected: 3+ matches.

- [ ] **Step 6: Commit**

```bash
git add skills/js-super-subagent-driven-development/implementer-prompt.md
git commit -m "feat(v1.1.14): implementer-prompt — model placeholder + DO NOT commit (wave parallel)"
```

---

### Task 5: skills/js-super-subagent-driven-development/spec-reviewer-prompt.md — working tree Read 명확화

**Files:**
- Modify: `skills/js-super-subagent-driven-development/spec-reviewer-prompt.md`

**Model**: sonnet

- [ ] **Step 1: Locate model line**

Run: `grep -n 'model:' skills/js-super-subagent-driven-development/spec-reviewer-prompt.md`
Expected: line ~9 — `model: "sonnet"`.

- [ ] **Step 2: Confirm sonnet stays fixed (no change to model line)**

Read the current line. Per PRD D11 spec-reviewer fixed at sonnet. **No change to model line** — just verify it's still `model: "sonnet"`.

- [ ] **Step 3: Add note about reading working tree (not git diff)**

**원본** (`skills/js-super-subagent-driven-development/spec-reviewer-prompt.md:43-50`):

```
    Read the implementation code and verify:

    **Missing requirements:**
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?
```

**수정 후**:

```
    Read the implementation code and verify.

    **Note (v1.1.14+):** Implementer no longer commits. The code is in the
    **working tree**, not yet in any git commit. Use the Read tool against
    the file paths in the implementer's manifest. `git diff HEAD -- <file>`
    also works (compares working tree to last commit). Avoid `git show <SHA>`
    — there is no SHA yet for this task's work.

    **Missing requirements:**
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?
```

- [ ] **Step 4: Verify**

Run: `grep -c "Implementer no longer commits" skills/js-super-subagent-driven-development/spec-reviewer-prompt.md`
Expected: 1.

- [ ] **Step 5: Commit**

```bash
git add skills/js-super-subagent-driven-development/spec-reviewer-prompt.md
git commit -m "feat(v1.1.14): spec-reviewer-prompt — clarify working tree Read (no commit yet)"
```

---

### Task 6: skills/js-super-subagent-driven-development/SKILL.md — Per-task → Per-wave 재작성

**Files:**
- Modify: `skills/js-super-subagent-driven-development/SKILL.md` (대폭 개정)

**Model**: sonnet

이 task 는 가장 큰 변경. 4단계로 나눠 진행.

- [ ] **Step 1: Add Entry Guard section before "Per-task Sequence"**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:75-77`, before `## Per-task Sequence`):

```markdown
## Per-task Sequence
```

**수정 후**:

```markdown
## Entry Guard (v1.1.14+)

이 skill 호출 시 메인은 즉시 다음을 검사:

```bash
test -f docs/features/<date>-<slug>/<slug>-implementation-plan.md
```

존재하지 않으면 **즉시 종료** + 한 줄 안내: `❌ <slug>-implementation-plan.md 없음. /write-plan 먼저 실행하세요.`

이유: wave 분할은 plan task 정보 (Files, deps, Model) 를 100% 의존. plan 없는 dispatch 는 의미 없음.

## Plan Analysis & Wave Build (v1.1.14+, 1회)

Per-task Sequence 보다 먼저 1회만 실행. 모든 task 완료까지 wave 구조는 immutable.

1. **Read plan tasks** — `<slug>-implementation-plan.md` 의 §1 단계별 작업 모든 task block.
2. **Parse files + deps** — 각 task block 의 `**Files:**` (Create/Modify/Test) 섹션 + step 본문에서 task ID 참조 추출 (예: "Task 1 의 helper 사용" → deps=[1]).
3. **Parse model hint** — task block 의 `**Model**:` 줄 (`haiku`/`sonnet`/`opus`). 없으면 `sonnet` 디폴트.
4. **Build waves** — `scripts/dag_builder.py:build_waves` 호출:

```bash
python -c "
from scripts.dag_builder import Task, build_waves
tasks = [
    Task(id=1, name='Foo', files=['scripts/dag_builder.py'], deps=[], model='haiku'),
    Task(id=2, name='Bar', files=['scripts/dag_builder.py'], deps=[1], model='haiku'),
    # ...
]
waves = build_waves(tasks)
for w in waves:
    print(f'Wave {w.index}: tasks={[t.id for t in w.tasks]}')
"
```

5. **사용자 출력 (1회)**:

```
📊 DAG 분석: <N> tasks → <W> waves
  Wave 1: tasks <list> (모델: <list>)
  Wave 2: tasks <list>
  ...
```

## Per-wave Sequence (v1.1.14+)

기존 Per-task Sequence 폐기. 흐름 변화:
```

- [ ] **Step 2: Replace Per-task Sequence section content with Per-wave**

**원본** (대규모, 80~280 줄 부근의 Per-task Sequence 섹션 + diagram + Detailed Step-by-Step):

(생략 — 현재 파일의 `## Per-task Sequence` 부터 `### 3. 다음 세션 시작 시 stale buffer 검출` 직전까지 모두)

**수정 후**:

```markdown
### Per-wave loop

For each wave (in order 1..N):

#### W-1. Wave 시작 안내 (사용자 출력 1회)

```
Wave i/N 시작: task <list> 병렬 실행…
```

#### W-2. Pair-parallel dispatch

For each task in this wave (in plan order):

- BASE_SHA_task = `git rev-parse HEAD` (per-task BASE_SHA, 다중 dispatch 시 공통)
- 두 dispatch 를 한 메시지에 묶어 **병렬** 실행 (Agent tool multiple calls in single message):
  - Implementer (`./implementer-prompt.md`, `model: <task.model>`, 디폴트 sonnet)
  - Spec reviewer (`./spec-reviewer-prompt.md`, `model: "sonnet"` 고정)

> **NOTE:** Spec reviewer 는 implementer 가 `Status: DONE` + manifest 작성 후 호출돼야 함. 현재 단순 구현은 implementer 끝까지 기다린 뒤 spec-reviewer dispatch (페어 병렬은 wave 안 task **간** 병렬을 뜻함, task **안** 의 impl→review 는 직렬).

#### W-3. Spec reviewer ❌ 시 implementer 재dispatch

기존 패턴 그대로. impl 재호출 → reviewer 재검 (working tree 만 갱신, commit 아직 X).

#### W-4. Wave finalization (직렬, plan order)

모든 task 의 spec-reviewer ✅ 후 메인이 plan 순서대로:

```bash
# (a) post-hoc conflict detection
python -c "
from pathlib import Path
from scripts.dag_builder import detect_conflicts
from scripts.changelog_buffer import read_manifest
manifests_dir = Path('.js-super/changelog-buffer/<slug>')
manifests = {}
for task_id in <wave_task_ids>:
    m = read_manifest(manifests_dir / f'task-{task_id:02d}.md')
    manifests[task_id] = [fc['path'] for fc in m['files_changed']]
conflicts = detect_conflicts(manifests)
print(conflicts)
"
```

- 비어있으면 정상 → step (b) 진행
- 충돌 발견 시: plan order 늦은 task 의 working tree 변경 stash → 다음 wave 로 이동:

```bash
git checkout -- <late_task_files>
# manifest 도 다음 wave 로 이동 (rename task-NN.md → task-NN.md.deferred)
```

```bash
# (b) For each task in plan order:
git diff HEAD -- <task.files>           # 3-checklist 입력
# 메인이 위험 평가 → RISK 주석 Edit
git add <task.files>
git commit -m "task <N>: <task.name>"
# (RISK 트리거 있으면 follow-up commit 별도)
```

#### W-5. Wave 완료 요약 (사용자 출력 1회)

```
Wave i/N 완료: <pass list>✓ <fail list>✗ (후행 차단: <list 또는 없음>)
```

#### W-6. Failure isolation (D7)

- spec-reviewer ❌ 가 retry loop 종료 후에도 ❌ → task 격리
- 격리 task 의 working tree 변경 `git checkout --` 으로 폐기, manifest 도 삭제
- DAG 에서 격리 task 의 후행 (deps 에 격리 task 포함) 모두 blocked 상태로 마킹
- 다음 wave 진행 시 blocked task 는 dispatch 대상에서 제외

## End-of-run Consolidator (v1.1.7 그대로 — 변화 없음)

§2 "모든 task 완료 후" 흐름 유지. wave 모델에서도 buffer manifest 가 task NN 별 isolation 이라 그대로 호환.

(아래 §2 / §3 stale 검출은 v1.1.7 원본 그대로 유지)
```

- [ ] **Step 3: Update "Few-Shot Example Workflow" — replace single-task narrative with wave narrative**

**원본** (`Few-Shot Example Workflow` 섹션, 단일 task 내러티브):

(현재 v1.1.13 의 single task narrative)

**수정 후** (wave-aware narrative — 더 짧게):

```markdown
## Example Workflow (Few-Shot, v1.1.14 wave 모드)

```
You: I'm using js-super-subagent-driven-development to execute this plan.

[Entry guard: foo-implementation-plan.md exists ✅]
[Read plan: 5 tasks. Parse Files/deps/Model.]
[Build waves: 3 waves (W1=[1,2], W2=[3,4], W3=[5])]
[User output: 📊 DAG 분석: 5 tasks → 3 waves]

──────────────────────────────────────
Wave 1/3 시작: task 1, 2 병렬 실행…
──────────────────────────────────────

[Single message with 2 Agent tool calls in parallel:
  - Implementer task 1 (model: haiku, BASE_SHA captured)
  - Implementer task 2 (model: sonnet, BASE_SHA captured)]

[Both return: Status DONE + manifest written to buffer]

[Single message with 2 Agent tool calls:
  - Spec reviewer task 1 (model: sonnet)
  - Spec reviewer task 2 (model: sonnet)]

[Both return: ✅ Spec compliant]

[Wave finalization, plan order]:
  - detect_conflicts(manifests) → []  (no conflict)
  - task 1: git diff HEAD → 3-checklist → no RISK → git add + commit "task 1"
  - task 2: git diff HEAD → 3-checklist → side-effect trigger → Edit RISK comment → git add + commit "task 2" + follow-up "[risk-annotate] task 2"

[Wave 1/3 완료: 1✓ 2✓ (2/2 통과)]

──────────────────────────────────────
Wave 2/3 시작: task 3, 4 병렬 실행…
──────────────────────────────────────

[Pair-parallel dispatch...]

[Spec reviewer task 4 returns ❌: missing AC-3]
[Re-dispatch implementer task 4 with reviewer findings]
[Re-dispatch spec reviewer task 4 → ✅]

[Wave finalization → 2 commits in plan order]

[Wave 2/3 완료: 3✓ 4✓ (2/2 통과)]

──────────────────────────────────────
Wave 3/3 시작: task 5...
──────────────────────────────────────

[End-of-run consolidator (v1.1.7 그대로):]
  ✅ foo 모든 task 완료. 구현 요약: ...
  - footer 1회 batch entry append
  - [log] 단일 commit
  - buffer cleanup
```
```

- [ ] **Step 4: Update Anti-Patterns + Acceptance + Process diagram**

**원본** Anti-Patterns 표에 새 항목 추가:

**수정 후**:

```markdown
| Wrong | Right |
|---|---|
| ... 기존 항목 ... | ... |
| Implementer 가 commit 하도록 두기 (v1.1.13 패턴 그대로) | v1.1.14+ 메인이 wave 끝에서 commit. implementer-prompt 에 명시적 금지. |
| wave 분할 안 하고 task 그대로 직렬 dispatch | wave = 1 인 plan 만 자연스럽게 직렬. 다중 wave plan 에 직렬 강행은 D3 위배. |
| 같은 wave task 들 commit 순서 race 방치 | wave 끝 plan order 직렬 commit 강제. |
| post-hoc conflict 검출 skip | DAG 추론 오류 안전망. 매 wave finalization 첫 단계. |
```

Acceptance 표에 추가:

```markdown
A wave is complete only when ALL hold:
1. 모든 task 의 implementer Status: DONE + spec reviewer ✅
2. detect_conflicts(wave manifests) == [] 이거나 충돌 task 가 deferred 처리됨
3. plan order 직렬 commit 완료 (RISK follow-up 포함)
4. 사용자에게 wave 완료 요약 출력 (✓/✗ + blocked tasks)
```

- [ ] **Step 5: Verify**

Run: `grep -c "Per-wave\|Entry Guard\|Wave finalization\|detect_conflicts" skills/js-super-subagent-driven-development/SKILL.md`
Expected: 6+ matches.

- [ ] **Step 6: Commit**

```bash
git add skills/js-super-subagent-driven-development/SKILL.md
git commit -m "feat(v1.1.14): SKILL.md — Per-task → Per-wave (DAG analysis + wave loop + finalization)"
```

---

### Task 7: tests/G1+G2 fixture (entry guard + simple wave)

**Files:**
- Create: `skills/js-super-subagent-driven-development/tests/G1-entry-guard/README.md` (+ minimal fixture)
- Create: `skills/js-super-subagent-driven-development/tests/G2-simple-wave/README.md` (+ minimal plan)

**Model**: haiku

- [ ] **Step 1: Create G1 README**

**수정 후** (new file: `skills/js-super-subagent-driven-development/tests/G1-entry-guard/README.md`):

```markdown
# G1: Entry Guard

**Scenario:** plan 없는 폴더에서 skill 진입 → 즉시 ABORT

**Setup:** `docs/features/2026-01-01-empty-fixture/` 폴더만 존재 (plan 파일 없음).

**Expected:** 메인이 entry guard 검사 → 한 줄 안내 출력 + 종료
```

- [ ] **Step 2: Create G2 README + minimal plan fixture**

**수정 후** (new files):

`skills/js-super-subagent-driven-development/tests/G2-simple-wave/README.md`:

```markdown
# G2: Simple Wave (3 tasks, file-disjoint, all sonnet)

**Scenario:** task 1, 2, 3 이 모두 다른 파일을 건드리고 deps 없음 → 1 wave 동시 dispatch.

**Expected wave 분할:** Wave 1: [1, 2, 3]
**Expected commits:** 3 commits in plan order (task 1 → task 2 → task 3)
**Expected dispatch model:** 모두 sonnet (Model 필드 없음 → 디폴트)
```

`skills/js-super-subagent-driven-development/tests/G2-simple-wave/plan.md`:

```markdown
---
commit_policy: per-task
---

# G2 Plan

## 1. 단계별 작업

### Task 1: A
**Files:**
- Create: `a.py`

- [ ] Step 1: write a.py

### Task 2: B
**Files:**
- Create: `b.py`

- [ ] Step 1: write b.py

### Task 3: C
**Files:**
- Create: `c.py`

- [ ] Step 1: write c.py
```

- [ ] **Step 3: Commit**

```bash
git add skills/js-super-subagent-driven-development/tests/G1-entry-guard/ skills/js-super-subagent-driven-development/tests/G2-simple-wave/
git commit -m "test(v1.1.14): G1 entry guard + G2 simple wave fixtures"
```

---

### Task 8: tests/G3+G4 fixture (deps + failure isolation)

**Files:**
- Create: `skills/js-super-subagent-driven-development/tests/G3-deps/{README.md, plan.md}`
- Create: `skills/js-super-subagent-driven-development/tests/G4-failure-isolation/{README.md, plan.md}`

**Model**: haiku

- [ ] **Step 1: G3 README + plan**

`G3-deps/README.md`:

```markdown
# G3: Logic Dependency

**Scenario:** Task 2 가 Task 1 의 helper 함수를 import. Task 1 끝나야 Task 2 시작.

**Expected wave 분할:** Wave 1: [1], Wave 2: [2, 3] (task 3 가 disjoint 면)
```

`G3-deps/plan.md`:

```markdown
---
commit_policy: per-task
---

# G3 Plan

## 1. 단계별 작업

### Task 1: helper module
**Files:**
- Create: `lib/helper.py`

- [ ] Step 1: write helper

### Task 2: consumer (uses Task 1's helper)
**Files:**
- Create: `app/consumer.py`

- [ ] Step 1: import from lib.helper (Task 1)

### Task 3: independent
**Files:**
- Create: `etc/standalone.py`

- [ ] Step 1: write
```

- [ ] **Step 2: G4 README**

`G4-failure-isolation/README.md`:

```markdown
# G4: Failure Isolation

**Scenario:** Wave 1 의 task 1, 2, 3 동시 dispatch. Task 2 spec FAIL 강제 (테스트 fixture 가 reviewer ❌ 강제 응답).

**Expected:**
- Task 1 ✓ commit 됨
- Task 2 ✗ 격리 (working tree rollback + manifest 삭제)
- Task 3 ✓ commit 됨
- Task 2 의 후행 task 들 (있다면) blocked 마킹
```

- [ ] **Step 3: Commit**

```bash
git add skills/js-super-subagent-driven-development/tests/G3-deps/ skills/js-super-subagent-driven-development/tests/G4-failure-isolation/
git commit -m "test(v1.1.14): G3 logic deps + G4 failure isolation fixtures"
```

---

### Task 9: tests/G5+G6+G7+G8 fixture (model hint + conflict + reviewer fix)

**Files:**
- Create: 4 fixture 디렉토리 with README.md / plan.md (필요 시)

**Model**: haiku

- [ ] **Step 1: G5 (Model: haiku 박힌 plan)**

`G5-model-haiku/README.md`:

```markdown
# G5: Model Hint = haiku

**Scenario:** plan 의 task 1 에 `**Model**: haiku` 명시.

**Expected:** 메인이 implementer dispatch 시 `model: "haiku"` 로 호출. spec-reviewer 는 sonnet.
```

`G5-model-haiku/plan.md`:

```markdown
---
commit_policy: per-task
---

# G5 Plan

## 1. 단계별 작업

### Task 1: trivial
**Files:**
- Create: `trivial.py`

**Model**: haiku

- [ ] Step 1: write trivial.py
```

- [ ] **Step 2: G6 (no Model field — sonnet default)**

`G6-no-model-default/README.md`:

```markdown
# G6: No Model Field — Sonnet Default

**Scenario:** plan task block 에 `**Model**:` 줄 없음 (v1.1.13 이전 plan 시뮬레이션).

**Expected:** 메인이 implementer dispatch 시 `model: "sonnet"` (디폴트) + 한 줄 dispatch log: "Task 1 model: sonnet (default)".
```

(plan.md 는 G2 plan 재사용 가능 — README 에 명시)

- [ ] **Step 3: G7 (post-hoc conflict)**

`G7-post-hoc-conflict/README.md`:

```markdown
# G7: Post-hoc Conflict Detection

**Scenario:** DAG 추론 오류 시뮬레이션 — task 2 와 task 3 모두 `shared.py` 수정. 메인이 두 task 를 같은 wave 로 묶음 (잘못 된 추론). 양쪽 implementer 가 manifest 에 `shared.py` 보고.

**Expected:**
- detect_conflicts → `(2, 3, 'shared.py')` 반환
- 메인이 task 3 (plan order 늦음) 의 working tree 변경 rollback
- task 3 의 manifest → `task-03.md.deferred` 로 rename
- 다음 wave 에서 task 3 단독 재시도
```

`G7-post-hoc-conflict/plan.md`:

```markdown
---
commit_policy: per-task
---

# G7 Plan

## 1. 단계별 작업

### Task 1: setup
**Files:**
- Create: `setup.py`

- [ ] Step 1: write

### Task 2: edit shared (first)
**Files:**
- Modify: `shared.py:1-10`

- [ ] Step 1: edit

### Task 3: edit shared (second — conflict!)
**Files:**
- Modify: `shared.py:11-20`

- [ ] Step 1: edit
```

- [ ] **Step 4: G8 (spec-reviewer fixed sonnet)**

`G8-reviewer-sonnet/README.md`:

```markdown
# G8: Spec-reviewer Always Sonnet

**Scenario:** plan task 1 에 `**Model**: haiku` 박힘 (implementer 는 haiku). 동시에 spec-reviewer dispatch 가 sonnet 인지 검증.

**Expected dispatch:**
- Implementer: `model: "haiku"` (Task 1 의 hint)
- Spec reviewer: `model: "sonnet"` (D11 고정, hint 무관)
```

(plan.md 는 G5 plan 재사용)

- [ ] **Step 5: Commit**

```bash
git add skills/js-super-subagent-driven-development/tests/G5-model-haiku/ skills/js-super-subagent-driven-development/tests/G6-no-model-default/ skills/js-super-subagent-driven-development/tests/G7-post-hoc-conflict/ skills/js-super-subagent-driven-development/tests/G8-reviewer-sonnet/
git commit -m "test(v1.1.14): G5/G6/G7/G8 fixtures (model hint + conflict + reviewer fix)"
```

---

### Task 10: CLAUDE.md 1줄 추가 + tests/README 갱신

**Files:**
- Modify: `CLAUDE.md` (js-super 내부 skill 주의사항 섹션에 1줄 추가)
- Modify: `skills/js-super-subagent-driven-development/tests/README.md` (G1~G8 색인 추가)

**Model**: sonnet

- [ ] **Step 1: Add line to CLAUDE.md (after docs-pretty ↔ change-history note)**

**원본** (`CLAUDE.md` 의 js-super 섹션 끝부분, 한 줄 위 빈 줄 위치 확인):

(파일 구조에 따라 정확한 위치는 grep 으로 확인)

**수정 후** (마지막에 추가):

```markdown
## writing-plans `**Model**:` 필드 ↔ js-super-subagent-driven-development 결합

`writing-plans` 의 task block 신규 `**Model**:` 필드는 `js-super-subagent-driven-development` 의 implementer dispatch model 결정에 직접 사용된다 (`skills/js-super-subagent-driven-development/SKILL.md` Plan Analysis & Wave Build 단계). 즉:

- writing-plans 의 평가 룰 (haiku/sonnet/opus 분기) 변경 시 `js-super-subagent-driven-development` 의 dispatch 단계도 동시 수정
- 한쪽만 건드리면 다음 회귀 발생: plan 작성 시 의도한 모델과 실제 dispatch 모델 불일치

요약: 이 두 skill 의 `**Model**:` 룰 변경은 atomic 하게 묶어 처리할 것.
```

- [ ] **Step 2: Update tests/README.md**

**원본** (`skills/js-super-subagent-driven-development/tests/README.md`):

(현재 F1~F5 색인 — 정확 내용은 Read 후 결정)

**수정 후** (G1~G8 추가):

```markdown
# Test Fixtures

## v1.1.7 (changelog batch consolidator)
- F1-basic-batch — ...
- F2-zero-code-task — ...
- F3-mode-schema-divergence — ...
- F4-interrupt-recovery — ...
- F5-cleanup — ...

## v1.1.14 (wave-parallel + model hint)
- G1-entry-guard — plan 없는 폴더 ABORT
- G2-simple-wave — 3 task disjoint, 1 wave
- G3-deps — task 2 가 task 1 의 helper 사용, 2 waves
- G4-failure-isolation — wave 안 task 1개 spec FAIL, 형제 commit + 격리
- G5-model-haiku — `**Model**: haiku` → implementer haiku dispatch
- G6-no-model-default — Model 필드 없음 → sonnet 디폴트
- G7-post-hoc-conflict — DAG 추론 오류 시뮬, conflict rollback + 재배치
- G8-reviewer-sonnet — implementer haiku 시에도 reviewer sonnet 고정
```

- [ ] **Step 3: Verify**

Run: `grep -c "writing-plans \`\*\*Model\*\*:\` 필드" CLAUDE.md`
Expected: 1.

Run: `grep -c "G1-entry-guard\|G8-reviewer-sonnet" skills/js-super-subagent-driven-development/tests/README.md`
Expected: 2.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md skills/js-super-subagent-driven-development/tests/README.md
git commit -m "docs(v1.1.14): CLAUDE.md skill coupling memo + tests/README G1~G8 index"
```

---

### Task 11: scripts/preflight.py — 4 helper (TDD)

**Files:**
- Create: `scripts/preflight.py`
- Create: `scripts/tests/test_preflight.py`

**Model**: haiku

`docs/backlog/v1.1.14-preflight-to-code.md` 의 4 종 helper (docs_pretty_check / code_pretty_check / execute_plan_mode_check / subagent_task_entry_check) 를 deterministic Python 으로 이관. 각 skill pre-flight 의 LLM 추론 단계 (수 초 + 토큰) 를 밀리초 + 0 토큰으로 대체.

- [ ] **Step 1: 4 helper 의 failing test 작성**

Append to `scripts/tests/test_preflight.py`:

```python
from pathlib import Path

import pytest

from scripts.preflight import (
    PreflightResult,
    docs_pretty_check,
    code_pretty_check,
    execute_plan_mode_check,
    subagent_task_entry_check,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_docs_pretty_check_file_not_found(tmp_path):
    result = docs_pretty_check(tmp_path / "missing-requirements.md")
    assert result.ok is False
    assert "not found" in result.reason


def test_docs_pretty_check_footer_not_empty(tmp_path):
    f = tmp_path / "foo-requirements.md"
    _write(f, "# x\n## 변경이력\n### [2026-05-10] [요구사항-수정]\n- id: CH-1\n")
    result = docs_pretty_check(f)
    assert result.ok is False
    assert "변경이력" in result.reason


def test_docs_pretty_check_wrong_filename(tmp_path):
    f = tmp_path / "random.md"
    _write(f, "# x\n## 변경이력\n")
    result = docs_pretty_check(f)
    assert result.ok is False


def test_docs_pretty_check_ok_requirements(tmp_path):
    f = tmp_path / "foo-requirements.md"
    _write(f, "# x\n## 변경이력\n<!-- empty -->\n")
    assert docs_pretty_check(f).ok is True


def test_code_pretty_check_only_implementation_plan(tmp_path):
    req = tmp_path / "foo-requirements.md"
    plan = tmp_path / "foo-implementation-plan.md"
    _write(req, "# x\n## 변경이력\n")
    _write(plan, "# x\n**수정 후**:\n```py\npass\n```\n## 변경이력\n")
    assert code_pretty_check(req).ok is False
    assert code_pretty_check(plan).ok is True


def test_execute_plan_mode_check_per_task(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "---\ncommit_policy: per-task\n---\n# x\n## 변경이력\n")
    result = execute_plan_mode_check(plan)
    assert result.ok is True


def test_execute_plan_mode_check_missing_frontmatter(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "# x\n## 변경이력\n")
    result = execute_plan_mode_check(plan)
    # default per-task assumed → ok
    assert result.ok is True


def test_subagent_task_entry_check_no_plan(tmp_path):
    result = subagent_task_entry_check(tmp_path / "missing-implementation-plan.md")
    assert result.ok is False


def test_subagent_task_entry_check_commit_policy_single_rejected(tmp_path):
    plan = tmp_path / "foo-implementation-plan.md"
    _write(plan, "---\ncommit_policy: single\n---\n# x\n## 변경이력\n")
    result = subagent_task_entry_check(plan)
    assert result.ok is False
    assert "per-task" in result.reason
```

- [ ] **Step 2: Run tests — expect ImportError**

Run: `source .venv/bin/activate && pytest scripts/tests/test_preflight.py -v`
Expected: ImportError (preflight module doesn't exist).

- [ ] **Step 3: Implement scripts/preflight.py**

**수정 후** (new file: `scripts/preflight.py`):

```python
"""Deterministic pre-flight checks for js-super skills.

Replaces LLM inference in skill pre-flight steps with bash-callable Python
helpers. Each function returns a PreflightResult; callers parse exit code
0 (ok) / 1 (fail with reason on stderr or stdout).
"""
import re
from pathlib import Path
from typing import NamedTuple


class PreflightResult(NamedTuple):
    ok: bool
    reason: str


_FEATURE_MD_PATTERN = re.compile(
    r".*-(requirements|tech-design|implementation-plan)\.md$"
)
_PLAN_MD_PATTERN = re.compile(r".*-implementation-plan\.md$")
_CHANGELOG_ENTRY = re.compile(r"^### \[", re.MULTILINE)
_FRONTMATTER_COMMIT_POLICY = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL
)
_COMMIT_POLICY_LINE = re.compile(
    r"^commit_policy:\s*(per-task|single|none)\s*$", re.MULTILINE
)


def _has_changelog_entries(text: str) -> bool:
    if "## 변경이력" not in text:
        return False
    footer = text.split("## 변경이력", 1)[1]
    return _CHANGELOG_ENTRY.search(footer) is not None


def _read_commit_policy(text: str) -> str:
    m = _FRONTMATTER_COMMIT_POLICY.match(text)
    if not m:
        return "per-task"
    line = _COMMIT_POLICY_LINE.search(m.group(1))
    return line.group(1) if line else "per-task"


def docs_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(False, f"file not found: {file_path}")
    if not _FEATURE_MD_PATTERN.match(str(file_path)):
        return PreflightResult(False, "filename doesn't match feature MD pattern")
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(False, "변경이력 footer not empty (doc is live)")
    return PreflightResult(True, "ok")


def code_pretty_check(file_path: Path) -> PreflightResult:
    if not file_path.exists():
        return PreflightResult(False, f"file not found: {file_path}")
    if not _PLAN_MD_PATTERN.match(str(file_path)):
        return PreflightResult(False, "code-pretty target must be implementation-plan.md")
    text = file_path.read_text(encoding="utf-8")
    if _has_changelog_entries(text):
        return PreflightResult(False, "변경이력 footer not empty (doc is live)")
    if "**수정 후**" not in text:
        return PreflightResult(False, "no '수정 후' code blocks found — nothing to prettify")
    return PreflightResult(True, "ok")


def execute_plan_mode_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        return PreflightResult(False, f"plan not found: {plan_path}")
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    return PreflightResult(True, f"commit_policy={policy}")


def subagent_task_entry_check(plan_path: Path) -> PreflightResult:
    if not plan_path.exists():
        return PreflightResult(False, f"plan not found: {plan_path}")
    text = plan_path.read_text(encoding="utf-8")
    policy = _read_commit_policy(text)
    if policy != "per-task":
        return PreflightResult(
            False,
            f"js-super-subagent-driven-development requires commit_policy: per-task (got {policy})",
        )
    return PreflightResult(True, "ok")
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest scripts/tests/test_preflight.py -v`
Expected: 9 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py scripts/tests/test_preflight.py
git commit -m "feat(v1.1.14): scripts/preflight.py — 4 deterministic pre-flight helpers + TDD"
```

---

### Task 12: docs-pretty + code-pretty SKILL.md — pre-flight 섹션 helper 호출로 교체

**Files:**
- Modify: `skills/docs-pretty/SKILL.md` (Step 1 Pre-flight check 섹션)
- Modify: `skills/code-pretty/SKILL.md` (Step 1 Pre-flight check 섹션)

**Model**: sonnet

- [ ] **Step 1: docs-pretty Pre-flight 섹션 위치 확인**

Run: `grep -n "Step 1 — Pre-flight check" skills/docs-pretty/SKILL.md`
Expected: line ~52.

- [ ] **Step 2: docs-pretty 의 LLM 추론 산문 → bash one-liner 로 교체**

**원본** (`skills/docs-pretty/SKILL.md:52~62`):

```markdown
### Step 1 — Pre-flight check

Before dispatching, the main agent MUST verify:

1. The target file exists (Read or Glob)
2. The file's `## 변경이력` footer has ZERO entries (Grep for `### \[` under `## 변경이력` heading; expect 0 matches)
3. The file is one of the three feature MDs (`-requirements.md` / `-tech-design.md` / `-implementation-plan.md`)

If ANY check fails → DO NOT dispatch. Tell the user why and exit.
```

**수정 후**:

```markdown
### Step 1 — Pre-flight check (v1.1.14+ deterministic)

Before dispatching, run the deterministic helper:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.preflight import docs_pretty_check
result = docs_pretty_check(Path('<TARGET>'))
print(f'ok={result.ok} reason={result.reason}')
sys.exit(0 if result.ok else 1)
"
```

- exit code 0 → 검증 통과, Step 2 dispatch 진행
- exit code 1 → 사용자에게 reason 한 줄 노출 후 즉시 종료. **메인은 검증 retry 또는 LLM 재추론 X**

이 단계는 v1.1.14 에서 LLM 추론 → 코드로 이관. 동일 검사 (file 존재 / 변경이력 footer 비어있음 / filename 패턴) 가 deterministic 으로 처리되어 응답 속도 + 토큰 비용 모두 0 수준. 자세한 룰은 `scripts/preflight.py:docs_pretty_check`.
```

- [ ] **Step 3: code-pretty Pre-flight 섹션 동일 패턴 교체**

**원본** (`skills/code-pretty/SKILL.md:46~55`):

```markdown
### Step 1 — Pre-flight check

Before dispatching, the main agent MUST verify:

1. The target file exists (Read or Glob)
2. The file's `## 변경이력` footer has ZERO entries (Grep for `### \[` under `## 변경이력`; expect 0 matches)
3. The file is `<slug>-implementation-plan.md` (NOT requirements.md, NOT tech-design.md)
4. verifying-spec has just passed for this draft (caller responsibility)
5. The file contains at least one `**수정 후**` label preceding a code block

If ANY check fails → DO NOT dispatch. Tell the caller why and exit.
```

**수정 후**:

```markdown
### Step 1 — Pre-flight check (v1.1.14+ deterministic)

Before dispatching, run the deterministic helper:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.preflight import code_pretty_check
result = code_pretty_check(Path('<TARGET>'))
print(f'ok={result.ok} reason={result.reason}')
sys.exit(0 if result.ok else 1)
"
```

- exit code 0 → 검증 통과, Step 2 dispatch 진행
- exit code 1 → reason 노출 후 즉시 종료

**Caller 책임 (helper 가 검증 X)**: verifying-spec 가 직전에 통과했는지 — 이건 writing-plans 흐름의 책임이고 helper 가 검사할 수 없음. 호출자가 보장.

helper 의 검사: file 존재 / 변경이력 footer 비어있음 / filename `*-implementation-plan.md` / 최소 1개 `**수정 후**` 블록 존재. 자세히는 `scripts/preflight.py:code_pretty_check`.
```

- [ ] **Step 4: 검증**

```bash
grep -c "scripts.preflight" skills/docs-pretty/SKILL.md skills/code-pretty/SKILL.md
```
Expected: 2 (각 1).

- [ ] **Step 5: Commit**

```bash
git add skills/docs-pretty/SKILL.md skills/code-pretty/SKILL.md
git commit -m "feat(v1.1.14): docs-pretty + code-pretty pre-flight → scripts/preflight helper"
```

---

### Task 13: executing-plans + js-super-subagent-driven-development — pre-flight 코드 호출 통합

**Files:**
- Modify: `skills/executing-plans/SKILL.md` (mode-check 섹션)
- Modify: `skills/js-super-subagent-driven-development/SKILL.md` (Entry Guard 섹션 — Task 6 에서 작성한 부분 강화)

**Model**: sonnet

- [ ] **Step 1: executing-plans mode-check 위치 확인**

Run: `grep -n "Read plan frontmatter\|commit_policy" skills/executing-plans/SKILL.md | head -3`
Expected: ~line 38, 44.

- [ ] **Step 2: executing-plans mode-check 단계에 helper 호출 추가**

**원본** (`skills/executing-plans/SKILL.md` mode-check 부분, 기존 산문):

```markdown
1. **Read plan frontmatter** for the `commit_policy` field (see writing-plans schema):
```

**수정 후**:

```markdown
1. **Run mode-check helper (v1.1.14+ deterministic)**:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.preflight import execute_plan_mode_check
result = execute_plan_mode_check(Path('<PLAN_PATH>'))
print(f'ok={result.ok} reason={result.reason}')
sys.exit(0 if result.ok else 1)
"
```

이 helper 가 plan frontmatter 의 `commit_policy` 를 deterministic 으로 읽어 반환. exit code 0 시 reason 에 `commit_policy=per-task` 형식. 메인은 reason 의 policy 값으로 git-fast / memory-fallback 분기.

기존 LLM 산문 추론 단계 제거 (v1.1.14). frontmatter 파싱 결과를 그대로 신뢰.
```

- [ ] **Step 3: js-super-subagent-driven-development Entry Guard 강화**

Task 6 의 Entry Guard 섹션 (Step 1 에서 추가한 부분) 을 helper 호출로 교체.

**원본** (Task 6 Step 1 의 결과물, `skills/js-super-subagent-driven-development/SKILL.md` Entry Guard 섹션):

```markdown
## Entry Guard (v1.1.14+)

이 skill 호출 시 메인은 즉시 다음을 검사:

```bash
test -f docs/features/<date>-<slug>/<slug>-implementation-plan.md
```

존재하지 않으면 **즉시 종료** + 한 줄 안내: `❌ <slug>-implementation-plan.md 없음. /write-plan 먼저 실행하세요.`
```

**수정 후**:

```markdown
## Entry Guard (v1.1.14+ deterministic)

이 skill 호출 시 메인은 즉시 helper 호출:

```bash
source .venv/bin/activate && python -c "
import sys
from pathlib import Path
from scripts.preflight import subagent_task_entry_check
result = subagent_task_entry_check(Path('<PLAN_PATH>'))
print(f'ok={result.ok} reason={result.reason}')
sys.exit(0 if result.ok else 1)
"
```

- exit code 0 → Plan Analysis 단계 진입
- exit code 1 → 한 줄 안내 후 즉시 종료. 예: `❌ <reason>. /write-plan 먼저 실행하세요.`

이유: helper 가 (a) plan 존재, (b) `commit_policy: per-task` 두 조건 모두 검사 — 단일 호출. plan 없는 dispatch 또는 `single`/`none` mode plan 모두 deterministic 거부.
```

- [ ] **Step 4: 검증**

```bash
grep -c "scripts.preflight" skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md
```
Expected: 2.

- [ ] **Step 5: Commit**

```bash
git add skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md
git commit -m "feat(v1.1.14): executing-plans + js-super-subagent-driven-development entry → scripts/preflight"
```

---

### Task 14: v1.1.14 version bump (6 manifests)

**Files:**
- Modify (auto via script): `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json`, `package.json`

**Model**: haiku

- [ ] **Step 1: Run bump script**

```bash
bash scripts/bump-version.sh 1.1.14
```
Expected: 6 manifest files updated 1.1.13 → 1.1.14.

- [ ] **Step 2: Verify**

```bash
grep -l '"version": "1.1.14"' .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json package.json
```
Expected: 6 paths listed.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json package.json
git commit -m "chore: bump version 1.1.13 → 1.1.14"
```

---

### Task 15: finishing-a-development-branch SKILL.md — 슬림화 (Step 2/3/4 제거)

**Files:**
- Modify: `skills/finishing-a-development-branch/SKILL.md` (~220 줄 → ~50 줄)

**Model**: sonnet

`docs/backlog/v1.1.14-finishing-branch-slim.md` 의 Option B 적용. 1인 개발 철학 일관성: 사전 verifying-spec + TDD + RISK + 변경이력으로 안전성 확보 → 종료 시점 추가 게이트 불필요. AskUserQuestion 4-option 게이트 제거. Step 1 (테스트 자동 실행) 만 안전망으로 유지.

- [ ] **Step 1: 현재 SKILL.md 라인 수 + 섹션 구조 파악**

Run: `wc -l skills/finishing-a-development-branch/SKILL.md && grep -n "^## " skills/finishing-a-development-branch/SKILL.md`
Expected: ~220 lines, Step 1~5 + meta sections.

- [ ] **Step 2: SKILL.md 본문 슬림 버전으로 전면 재작성**

**원본** (`skills/finishing-a-development-branch/SKILL.md` 전체, ~220 줄):

(현재 v1.1.13 finishing skill 본문 — Step 1 테스트 자동 실행 + Step 2 base branch 추정 + Step 3 AskUserQuestion 4-option 게이트 + Step 4 git boilerplate + Step 5 worktree cleanup)

**수정 후** (전체 교체, 코드 블록은 새 SKILL.md 본문):

```markdown
---
name: finishing-a-development-branch
description: Use when implementation is complete and tests pass. Runs the test gate one final time and emits a single termination message; user manually decides merge / PR / keep / discard. (v1.1.14 슬림화 — AskUserQuestion 게이트 + boilerplate 제거)
---

# Finishing a Development Branch (v1.1.14 slim)

implementation 완료 + 모든 테스트 통과 시점에 호출. 1인 개발자가 다음 행동 (merge / PR / keep / discard) 을 이미 알고 있다는 가정 하에, 추가 게이트는 두지 않고 **테스트 자동 실행 안전망 + 종료 메시지** 만 제공.

**Announce at start:** "I'm using the finishing-a-development-branch skill to verify tests then emit a termination summary."

## When to Use

- `executing-plans` / `js-super-subagent-driven-development` 가 모든 task 완료 후 자동 호출
- 사용자가 명시적으로 마무리 단계 진입 시 호출

## Process

### Step 1 — Tests pass gate (필수 안전망)

자동으로 프로젝트 표준 테스트 명령 실행:

```bash
# Python (이 저장소 기본)
source .venv/bin/activate && pytest -v

# 다른 stack 의 경우 README / package.json scripts 확인
```

- 모든 테스트 PASS → Step 2 진행
- FAIL 1건 이상 → **즉시 STOP**. 실패한 테스트 출력을 사용자에게 노출 + 한 줄 안내: "❌ 테스트 실패. 마무리 진행 안 함. 실패 원인 확인 후 다시 호출."

이 단계는 **유일한 자동 게이트**. 깨진 코드가 main / PR 로 흘러 들어가는 것 방지.

### Step 2 — Termination Message (한 메시지, 게이트 X)

```
✅ 모든 task 완료 + 테스트 통과.
   - 변경 commit: <SHA list>
   - RISK 트리거: <카테고리 카운트>
   - 누락/초과: <list 또는 "없음">

마무리하세요. (예: git checkout main && git merge <branch>, 또는 PR 생성, 또는 그대로 두기)
```

→ AskUserQuestion 게이트 없음. 사용자가 직접 git/gh 명령 실행. boilerplate 자동 생성 X.

## Worktree Cleanup (manual)

워크트리 정리는 자동 안 함 (마무리 시점이라고 자동 정리하면 사용자가 "그대로 두기" 의도일 때 자료 손실 가능). 사용자가 직접 처리:

```bash
git worktree remove <path>
```

## Anti-Patterns

| Wrong | Right |
|---|---|
| AskUserQuestion 4-option 게이트 추가 | 게이트 X. 1인 개발자 마찰 회피. |
| base branch 자동 추정 | 사용자가 본인 브랜치 알고 있음. 추정 시간 낭비. |
| git/gh boilerplate 자동 생성 | 종료 메시지 한 줄 안내만. 명령 직접 실행. |
| Step 1 테스트 실패 시 무시 | NEVER. 유일한 안전망. STOP 강제. |

## Why slim (v1.1.14)

- 1인 개발 철학: 사전 verifying-spec + TDD + RISK + 변경이력으로 안전성 분산. 종료 게이트는 중복.
- v1.1.9~12 게이트 합리화 흐름의 자연스러운 연장 (partial 제거 / fix→no / #12 복원 같은 마찰 정리).
- discard 안전망 의도적 트레이드오프: 사용자가 직접 `git branch -D` 시 confirm 없음. 1인 개발자는 git 동작 알고 있음.

## Related Skills

- `executing-plans` — 인라인 모드 종료 시 호출
- `js-super-subagent-driven-development` — 서브에이전트 모드 End-of-Run consolidator 끝 호출
- `setting-up-worktrees` — 워크트리 생성 페어 (cleanup 은 manual)
```

- [ ] **Step 3: 검증 (라인 수 + 게이트 제거)**

```bash
# 라인 수 ~70 이하로 슬림 됐는지
wc -l skills/finishing-a-development-branch/SKILL.md
# Expected: < 100 lines

# AskUserQuestion 게이트 제거됐는지
grep -c "AskUserQuestion" skills/finishing-a-development-branch/SKILL.md
# Expected: 0

# Step 1 테스트 안전망 유지
grep -c "Tests pass gate\|pytest" skills/finishing-a-development-branch/SKILL.md
# Expected: 2+
```

- [ ] **Step 4: Commit**

```bash
git add skills/finishing-a-development-branch/SKILL.md
git commit -m "feat(v1.1.14): finishing-a-development-branch slim — drop AskUserQuestion + boilerplate"
```

---

### Task 16: caller 동기화 (executing-plans, subagent-dd, commands/execute-plan)

**Files:**
- Modify: `skills/executing-plans/SKILL.md` (finishing 호출 라인)
- Modify: `skills/js-super-subagent-driven-development/SKILL.md` (End-of-Run finishing 호출)
- Modify: `commands/execute-plan.md` (시퀀스 동기화)

**Model**: sonnet

- [ ] **Step 1: 호출 위치 파악**

```bash
grep -rn "finishing-a-development-branch" skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md commands/execute-plan.md
```
Expected: 3+ matches.

- [ ] **Step 2: caller 호출 라인을 슬림 finishing 의 호출로 일관 정리**

**원본** (각 caller 의 finishing 호출 prose, 4-option 게이트 가정 wording):

(예: "Step 5: finishing-a-development-branch invoke — Merge / PR / cleanup 옵션 제시")

**수정 후** (각 caller 동일 패턴):

```markdown
**Final step**: invoke `finishing-a-development-branch` — 테스트 자동 검증 + 종료 메시지 (v1.1.14 슬림화). AskUserQuestion 게이트 X, 사용자가 직접 git/gh 명령 실행.
```

각 caller 의 4-option 게이트 가정 wording (Merge/PR/Keep/Discard 분기, base branch 추정 언급 등) 모두 위 한 줄로 통합.

- [ ] **Step 3: HANDOFF.md Risk Register 업데이트 (discard 안전망 제거 명시)**

**원본** (`HANDOFF.md` Risk Register 섹션 추가):

(현재 Risk Register 마지막 항목)

**수정 후** (1줄 추가):

```markdown
- **finishing-a-development-branch discard 안전망 제거** (v1.1.14): 4-option 게이트 + "discard" 타이핑 강제 제거. 1인 개발자 가정 + 마찰 회피 트레이드오프 의도. 사용자가 직접 `git branch -D` 시 confirm 없음 — 정말 큰 작업이면 PR 후 삭제 권장.
```

- [ ] **Step 4: 검증**

```bash
# caller 들이 모두 슬림 finishing 호출하는지
grep -c "v1.1.14 슬림화" skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md commands/execute-plan.md
# Expected: 3
```

- [ ] **Step 5: Commit**

```bash
git add skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md commands/execute-plan.md HANDOFF.md
git commit -m "feat(v1.1.14): caller sync for finishing slim + HANDOFF Risk Register update"
```

---

### Task 17: 검증 — 정적 grep + pytest 전체 + 회귀 검사

**Files:** (read-only) — `[검증]` entry, no code change.

**Model**: haiku

- [ ] **Step 1: pytest 전체 실행 (회귀 없음)**

```bash
source .venv/bin/activate && pytest scripts/tests/ -v
```
Expected: 기존 + 신규 test 모두 PASS (test_changelog_buffer + test_change_id + test_detect_auth + test_dag_builder + test_preflight).

- [ ] **Step 2: 정적 grep — schema 일관성 + preflight 통합**

```bash
# Model: 필드가 writing-plans 본문에 명시되는지
grep -c "Task Model Hint\|\*\*Model\*\*:" skills/writing-plans/SKILL.md
# Expected: 2+

# implementer-prompt 의 placeholder 정상 박힘
grep -c '{{MODEL}}' skills/js-super-subagent-driven-development/implementer-prompt.md
# Expected: 1

# implementer-prompt 의 DO NOT commit 명시
grep -c "DO NOT git commit" skills/js-super-subagent-driven-development/implementer-prompt.md
# Expected: 1+

# spec-reviewer model sonnet 고정
grep -c '"sonnet"' skills/js-super-subagent-driven-development/spec-reviewer-prompt.md
# Expected: 1

# SKILL.md 의 wave 모델 섹션 박힘
grep -c "Plan Analysis & Wave Build\|Per-wave Sequence\|Wave finalization" skills/js-super-subagent-driven-development/SKILL.md
# Expected: 3+

# preflight helper 4 skill 에 통합됨
grep -c "scripts.preflight" skills/docs-pretty/SKILL.md skills/code-pretty/SKILL.md skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md
# Expected: 4

# finishing slim — AskUserQuestion 제거 + 라인 수 슬림
grep -c "AskUserQuestion" skills/finishing-a-development-branch/SKILL.md
# Expected: 0
test "$(wc -l < skills/finishing-a-development-branch/SKILL.md)" -lt 100 && echo "slim ok"
# Expected: slim ok

# finishing caller 들이 슬림 호출 wording 으로 통일
grep -c "v1.1.14 슬림화" skills/executing-plans/SKILL.md skills/js-super-subagent-driven-development/SKILL.md commands/execute-plan.md
# Expected: 3
```

- [ ] **Step 3: G1~G8 fixture 디렉토리 8개 모두 생성됨 확인**

```bash
ls skills/js-super-subagent-driven-development/tests/ | grep -c '^G[1-8]-'
# Expected: 8
```

- [ ] **Step 4: og- mirrors 변경 없음 확인**

```bash
git diff HEAD~17 HEAD -- skills/og-writing-plans/ skills/og-executing-plans/ skills/og-brainstorming/
# Expected: 빈 diff (0 lines)
```

- [ ] **Step 5: 6 manifest version 일치**

```bash
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json package.json; do
  echo "$f: $(grep '"version"' $f | head -1)"
done
# Expected: 6 lines, all "1.1.14"
```

- [ ] **Step 6: 검증 PASS 보고 — 코드 변경 없음, [검증] entry 작성**

검증 결과를 사용자에게 출력. 본 task 는 코드 0건이라 `[검증]` entry 로 변경이력 작성 (실행 모드 자동 처리, end-of-run consolidator 가 [검증] type 으로 분리).

---

## 2. 위험 코드 지점

- `scripts/dag_builder.py:build_waves` — side-effect: LLM 이 Task `deps` / `files` 를 잘못 추론해서 같은 wave 에 충돌 task 2개 묶음 (R1) | mitigation: `detect_conflicts` post-hoc + plan order 늦은 task rollback + 다음 wave 재배치 (Task 9 G7 fixture 검증)
- `skills/js-super-subagent-driven-development/SKILL.md` Plan Analysis 단계 — breaking: plan 의 `**Model**:` 필드 누락 (v1.1.13 이전 plan) → silent skip 위험 (R2) | mitigation: default sonnet + 한 줄 dispatch log: `Task N model: sonnet (default)` (Task 6 + G6 fixture 검증)
- `scripts/changelog_buffer.py` (변경 없음) — race: 병렬 implementer 들이 동시에 manifest 작성 시 file system race (R3) | mitigation: manifest path 가 `task-NN.md` 별 isolation, 같은 파일 동시 쓰기 없음 — 검증 X (조건 자체가 안 발생)
- `skills/js-super-subagent-driven-development/implementer-prompt.md:50-58` — breaking: implementer 가 습관으로 `git commit` 호출 시 wave-end commit logic 깨짐 (R4) | mitigation: prompt "DO NOT git commit" 명시 + Self-review 항목 추가 (Task 4 + Task 17 step 2 grep 검증)
- `skills/js-super-subagent-driven-development/SKILL.md` Per-wave loop W-2 — side-effect: pair-parallel reviewer 가 commingled 워킹트리 봄 (R5) | mitigation: DAG file-disjoint 보장으로 자연 회피, R1 처리 룰이 동시 처리
- `skills/js-super-subagent-driven-development/SKILL.md` Per-wave loop W-6 — side-effect: 후행 차단된 task 들이 다음 wave 로 미뤄지지 않고 영구 skip 위험 (R6) | mitigation: blocked 마킹 + end-of-run 요약에 `blocked tasks: [...]` 노출 (Task 6 + G4 fixture 검증)
- `skills/js-super-subagent-driven-development/SKILL.md` Per-wave loop W-4 — side-effect: implementer 가 commit 안 하므로 인터럽트 시 working tree 미정리 변경 유실 (R7) | mitigation: wave finalization 즉시 commit → 인터럽트 사실상 wave 단위 원자성. wave 중간 인터럽트는 §3 stale buffer 검출 (v1.1.7 패턴 재사용)
- `skills/writing-plans/SKILL.md` Task Structure — breaking: schema 변경 (`**Model**:`) 이 og-writing-plans 영향 (R8) | mitigation: og- mirror 변경 X 명시 (Task 17 step 4 git diff 0 lines 검증)
- `scripts/preflight.py` 호출 (4 skill 의 Step 1) — side-effect: venv / Python 환경 깨지면 모든 skill pre-flight bash one-liner 가 실패 → skill 진입 자체 막힘 (R9) | mitigation: bash one-liner 의 `sys.exit(...)` + 명확한 reason 메시지 + `scripts/tests/test_preflight.py` 9건 fixture 단위 테스트 (Task 11 + Task 17 step 2 grep 검증)
- `skills/finishing-a-development-branch/SKILL.md` (전체 슬림 교체) — breaking: AskUserQuestion 4-option 게이트 + "discard" 타이핑 안전망 제거 → 사용자가 직접 `git branch -D` 시 confirm 없음 (R10) | mitigation: 1인 개발자 가정 + Step 1 (테스트 자동 실행) 안전망 유지 + HANDOFF.md Risk Register 명시적 trade-off 기록 (Task 15 + Task 16 + Task 17 step 2 grep 검증)

## 3. 롤백 전략

- **Code rollback**: Task 1~17 의 commits 합산 (≈ 1 task = 1~2 commits, RISK follow-up 별도) → 약 17~20 commits. revert range = HEAD~20..HEAD 부근. 또는 v1.1.13 tag 체크아웃 (`git checkout v1.1.13` — tag 존재 시).
- **Skill body rollback**: skills/js-super-subagent-driven-development/SKILL.md 의 Per-task → Per-wave 변경이 가장 큰 영향. v1.1.13 의 파일은 git history 에 그대로 보존 (`git show v1.1.13:skills/js-super-subagent-driven-development/SKILL.md`).
- **Plan downstream rollback**: v1.1.14 dispatch 시 silent overwrite 회귀 발견 → plan 의 `**Model**:` 필드 무시 + 메인이 implementer dispatch 시 무조건 sonnet 사용하도록 SKILL.md hot-fix. 본 plan 의 Task 6 만 reverting.
- **Helper rollback**: `scripts/dag_builder.py` + `scripts/preflight.py` + 그 테스트 파일 삭제. 4 skill (docs-pretty / code-pretty / executing-plans / js-super-subagent-driven-development) 의 Pre-flight 섹션 v1.1.13 LLM 추론 산문으로 revert. helper 는 살려두고 호출만 끊어도 무관 (사용 안 하면 그만).
- **Finishing slim rollback**: `skills/finishing-a-development-branch/SKILL.md` 를 v1.1.13 형식 (Step 1~5 + AskUserQuestion 4-option 게이트) 으로 revert. caller (executing-plans / subagent-dd / commands/execute-plan) 의 finishing 호출 wording 도 동시 revert. discard 안전망 복원이면 R10 trade-off 폐기.
- **Tag**: `git tag v1.1.14` 안 만들었으면 main push 만 됨 — 사용자가 직접 tag 결정 (HANDOFF.md v1.1.13 정책 그대로).

---
## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-05-10] [구현계획서-수정]
- **id**: CH-20260510-003
- **이유**: 신규 구현계획서 (v1.1.14 = 서브에이전트 병렬화 + Task별 모델 힌트 + Pre-flight 코드 이관 + finishing-a-development-branch 슬림화 4 backlog 통합)
- **무엇이**: 서브에이전트-병렬화-implementation-plan.md 전체 (Tasks 1-17 / §2 위험 R1-R10 / §3 롤백 전략)
- **영향범위**: 없음 (최초 생성)
- **연관 항목**: CH-20260510-001 (요구사항 PRD), CH-20260510-002 (개발방향)

### [2026-05-10] [코드-수정] (batch: tasks 1..16)
- **id**: CH-20260510-004
- **이유**: v1.1.14 = 서브에이전트 병렬화 (DAG + wave + model hint) + Pre-flight 코드 이관 + finishing-a-development-branch 슬림화 4 backlog 통합 구현
- **무엇이**: scripts/dag_builder.py (신규), scripts/preflight.py (신규), scripts/tests/test_dag_builder.py (신규), scripts/tests/test_preflight.py (신규), skills/writing-plans/SKILL.md (Model: schema), skills/js-super-subagent-driven-development/{SKILL.md (Per-task → Per-wave 재작성), implementer-prompt.md ({{MODEL}} placeholder + DO NOT commit), spec-reviewer-prompt.md (working tree Read 명확화), tests/G1~G8 8 fixture}, skills/docs-pretty/SKILL.md (Pre-flight helper), skills/code-pretty/SKILL.md (Pre-flight helper), skills/executing-plans/SKILL.md (mode-check helper + finishing slim wording), skills/finishing-a-development-branch/SKILL.md (전체 슬림 220→75줄), CLAUDE.md (2 결합 메모 추가), 6 manifests (1.1.13 → 1.1.14)
- **영향범위**: js-super 워크플로 전반 (서브에이전트 dispatch 흐름 + writing-plans schema + 4 skill Pre-flight + finishing 종료 흐름). og- mirrors 변경 X 확정.
- **위험 카테고리**: breaking (R4 implementer commit pattern shift + R10 finishing slim discard 안전망 제거 — 의도적 trade-off)
- **task별 세부 (16건)**:
  - Task 1+2: `scripts/dag_builder.py:1-110`, `scripts/tests/test_dag_builder.py:1-90` — Task/Wave dataclass + build_waves (Kahn) + detect_conflicts (post-hoc) — commits: `1ddef15`
  - Task 3: `skills/writing-plans/SKILL.md:117, 152-` — `**Model**:` 필드 + 평가 룰 — commit: `ecfbdc5`
  - Task 4: `skills/js-super-subagent-driven-development/implementer-prompt.md:7, 50-65, 122-125` — {{MODEL}} placeholder + DO NOT commit + Self-review 항목 — commit: `a4236ad`
  - Task 5: `skills/js-super-subagent-driven-development/spec-reviewer-prompt.md:43-50` — working tree Read 명확화 (v1.1.14+ 노트) — commit: `cc75e2f`
  - Task 6: `skills/js-super-subagent-driven-development/SKILL.md:전체` — Per-task → Per-wave (Entry Guard + Plan Analysis + Wave loop W-1~W-6 + End-of-Run consolidator + Stale 검출 + wave Few-Shot + Anti-Patterns) — commit: `baf311e`
  - Task 7: `tests/G1-entry-guard/`, `tests/G2-simple-wave/` — entry guard + simple wave 검증 fixture — commit: `a0aae34`
  - Task 8: `tests/G3-deps/`, `tests/G4-failure-isolation/` — logic deps + failure isolation fixture — commit: `e6abc47`
  - Task 9: `tests/G5-model-haiku/`, `tests/G6-no-model-default/`, `tests/G7-post-hoc-conflict/`, `tests/G8-reviewer-sonnet/` — model hint + conflict + reviewer fixture — commit: `dbe87b8`
  - Task 10: `CLAUDE.md`, `skills/.../tests/README.md` — 2 skill 결합 메모 + G1~G8 색인 — commits: `9122017`, `52d0d41`
  - Task 11: `scripts/preflight.py:1-92`, `scripts/tests/test_preflight.py:1-90` — 4 deterministic helper + 9 unit test — commit: `d4e0b2d`
  - Task 12: `skills/docs-pretty/SKILL.md:54-`, `skills/code-pretty/SKILL.md:44-` — Pre-flight LLM 산문 → bash one-liner — commit: `e9b4ac2`
  - Task 13: `skills/executing-plans/SKILL.md:44-` — mode-check helper 호출 — commit: `82bd0de`
  - Task 14: 6 manifest 1.1.13 → 1.1.14 — commit: `9222617`
  - Task 15: `skills/finishing-a-development-branch/SKILL.md:전체` — 220→75줄 슬림 (Step 2/3/4 제거, AskUserQuestion 게이트 제거, Step 1 테스트 안전망 + 종료 메시지만 유지) — commit: `f948657`
  - Task 16: `skills/executing-plans/SKILL.md:252-256` — finishing slim wording sync — commit: `320f1a1`
- **연관 commits**: `1ddef15`, `ecfbdc5`, `a4236ad`, `cc75e2f`, `baf311e`, `a0aae34`, `e6abc47`, `dbe87b8`, `9122017`, `52d0d41`, `d4e0b2d`, `e9b4ac2`, `82bd0de`, `9222617`, `f948657`, `320f1a1` (총 16 commits, BASE_SHA `6ef7a91`..HEAD)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
- **연관 항목**: CH-20260510-003 (구현계획서)

### [2026-05-10] [검증] (task: Task 17 — 정적 grep + pytest 전체 + 회귀 검사)
- **id**: CH-20260510-005
- **이유**: v1.1.14 릴리즈 직전 회귀 + schema 일관성 검증
- **무엇이**: pytest 전체 (30 PASS) / Model: schema (3 hits) / {{MODEL}} placeholder (1) / DO NOT git commit (1) / spec-reviewer sonnet (1) / Wave 섹션 (8) / preflight 4 skill 통합 (모두 적용) / finishing slim 75줄 + AskUserQuestion 0 functional / G1~G8 8 fixture / og- mirrors 0-diff / 6 manifest v1.1.14
- **결과**: PASS — 모든 grep + pytest + diff 검증 통과
- **연관 commit**: HEAD (검증은 코드 0건, 본 entry 가 곧 결과)
- **연관 항목**: CH-20260510-004 (코드 변경 batch)
