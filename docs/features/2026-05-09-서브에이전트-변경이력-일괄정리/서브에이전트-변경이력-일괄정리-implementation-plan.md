---
commit_policy: per-task
---

# 서브에이전트 변경이력 일괄정리 구현계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use `js-super-subagent-driven-development` (recommended for 13+ tasks) or `executing-plans` (recommended for ≤12 tasks) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 서브에이전트 모드에서 task별 즉시 [코드-수정] entry append 패턴을 end-of-run 일괄 정리 패턴으로 재설계 + 비-코드 entry type([검증]/[릴리즈]) 추가 + git-fast 모드 슬림 schema 도입.

**Architecture:** implementer 서브에이전트는 종료 시 `Changes Manifest` (YAML) 를 보고 + `.js-super/changelog-buffer/<slug>/task-NN.md` 에도 기록 (A+B 하이브리드). 메인은 task별 후처리에서 footer 안 건드리고 in-memory accumulator + buffer 무결성만 확인. 모든 task 완료 후 1회 종합 → "구현 요약" 메시지 + consolidated [코드-수정] entry 1개 + 비-코드 task 별도 [검증] entry → 단일 `[log] all tasks` commit → buffer cleanup. 인라인 모드(`executing-plans`)도 동일 패턴 (buffer 없이 in-memory).

**Tech Stack:** Markdown skill 본문 + Python helper (`scripts/changelog_buffer.py`) + pytest fixtures + bash bump-version.

**Spec inputs:**
- 서브에이전트-변경이력-일괄정리-requirements.md — AC-1 (batch append) / AC-2 (구현 요약 메시지) / AC-3 ([검증] entry) / AC-4 (per-task 슬림) / AC-5 (구조화 보고)
- 서브에이전트-변경이력-일괄정리-tech-design.md — D1~D6 결정, R1~R7 위험, F1~F5 + G1~G3 + I1~I4 + R-1~R-2 테스트

---

## 1. 단계별 작업

### Task 1: `.gitignore` 추가 + helper 스크립트 skeleton

**Files:**
- Modify: `.gitignore`
- Create: `scripts/changelog_buffer.py`
- Test: `scripts/tests/test_changelog_buffer.py`

- [ ] **Step 1: `.gitignore` 에 buffer 경로 추가**

**원본** (`.gitignore`)
```
# js-superpowers dev env
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.upstream
```

**수정 후**
```
# js-superpowers dev env
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.upstream

# v1.1.7 — subagent changelog buffer (interrupt recovery)
.js-super/
```

- [ ] **Step 2: failing test 작성 — 빈 manifest 작성·읽기**

**수정 후** (`scripts/tests/test_changelog_buffer.py`, 신규)
```python
from pathlib import Path
import pytest
from scripts.changelog_buffer import write_manifest, read_manifest

def test_write_and_read_minimal_manifest(tmp_path: Path):
    target = tmp_path / "task-01.md"
    manifest = {
        "task_id": 1,
        "task_name": "Hello",
        "status": "DONE",
        "base_sha": "deadbee",
        "commits": [],
        "files_changed": [],
        "concerns": [],
    }
    write_manifest(target, manifest)
    assert target.exists()
    loaded = read_manifest(target)
    assert loaded["task_id"] == 1
    assert loaded["task_name"] == "Hello"
    assert loaded["status"] == "DONE"
```

- [ ] **Step 3: test 실행해서 fail 확인**

```bash
source .venv/bin/activate
pytest scripts/tests/test_changelog_buffer.py::test_write_and_read_minimal_manifest -v
```
Expected: FAIL — `ModuleNotFoundError: scripts.changelog_buffer`

- [ ] **Step 4: helper 최소 구현 — `write_manifest` + `read_manifest`**

**수정 후** (`scripts/changelog_buffer.py`, 신규)
```python
"""Subagent changelog buffer helpers (v1.1.7).

Implementer subagents write Changes Manifest as YAML frontmatter to
.js-super/changelog-buffer/<slug>/task-NN.md. The main agent reads
these at end-of-run to consolidate into a single 변경이력 entry.
"""
from pathlib import Path
import yaml


def write_manifest(target: Path, manifest: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    target.write_text(f"---\n{body}---\n", encoding="utf-8")


def read_manifest(target: Path) -> dict:
    text = target.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {target}")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"malformed manifest: {target}")
    return yaml.safe_load(parts[1])
```

- [ ] **Step 5: test 통과 확인**

```bash
pytest scripts/tests/test_changelog_buffer.py::test_write_and_read_minimal_manifest -v
```
Expected: PASS

- [ ] **Step 6: commit**

```bash
git add .gitignore scripts/changelog_buffer.py scripts/tests/test_changelog_buffer.py
git commit -m "feat(v1.1.7): changelog buffer helpers + .gitignore — Task 1/11"
```

---

### Task 2: `list_buffer_files` + `detect_stale_buffer` (interrupt recovery)

**Files:**
- Modify: `scripts/changelog_buffer.py`
- Modify: `scripts/tests/test_changelog_buffer.py`

- [ ] **Step 1: failing tests 작성 — list + stale detection**

**수정 후** (`scripts/tests/test_changelog_buffer.py` append)
```python
from scripts.changelog_buffer import list_buffer_files, detect_stale_buffer


def _write(p: Path, manifest: dict):
    write_manifest(p, manifest)


def test_list_buffer_files_sorted_by_task_id(tmp_path: Path):
    base = tmp_path / "feature-a"
    _write(base / "task-02.md", {"task_id": 2, "task_name": "B", "status": "DONE"})
    _write(base / "task-10.md", {"task_id": 10, "task_name": "J", "status": "DONE"})
    _write(base / "task-01.md", {"task_id": 1, "task_name": "A", "status": "DONE"})
    files = list_buffer_files(base)
    assert [f.name for f in files] == ["task-01.md", "task-02.md", "task-10.md"]


def test_detect_stale_buffer_returns_path_when_present(tmp_path: Path):
    base = tmp_path / ".js-super" / "changelog-buffer" / "feature-a"
    _write(base / "task-01.md", {"task_id": 1, "task_name": "A", "status": "DONE"})
    stale = detect_stale_buffer(tmp_path / ".js-super" / "changelog-buffer", "feature-a")
    assert stale is not None
    assert stale.name == "feature-a"


def test_detect_stale_buffer_returns_none_when_absent(tmp_path: Path):
    stale = detect_stale_buffer(tmp_path / ".js-super" / "changelog-buffer", "feature-a")
    assert stale is None
```

- [ ] **Step 2: tests 실행해서 fail 확인**

```bash
pytest scripts/tests/test_changelog_buffer.py -v
```
Expected: FAIL on 3 new tests with `ImportError: cannot import name 'list_buffer_files'`

- [ ] **Step 3: 두 함수 추가**

**원본** (`scripts/changelog_buffer.py:end-of-file`)
```python
def read_manifest(target: Path) -> dict:
    text = target.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {target}")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"malformed manifest: {target}")
    return yaml.safe_load(parts[1])
```

**수정 후**
```python
def read_manifest(target: Path) -> dict:
    text = target.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {target}")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"malformed manifest: {target}")
    return yaml.safe_load(parts[1])


def list_buffer_files(buffer_dir: Path) -> list[Path]:
    """Return task-*.md files sorted by numeric task id."""
    if not buffer_dir.exists():
        return []
    files = list(buffer_dir.glob("task-*.md"))
    return sorted(files, key=lambda p: int(p.stem.split("-")[1]))


def detect_stale_buffer(root: Path, slug: str) -> Path | None:
    """Return the slug subdir under root if it exists with manifests, else None."""
    candidate = root / slug
    if not candidate.exists():
        return None
    if not list_buffer_files(candidate):
        return None
    return candidate
```

- [ ] **Step 4: tests 통과 확인**

```bash
pytest scripts/tests/test_changelog_buffer.py -v
```
Expected: 4 passed

- [ ] **Step 5: commit**

```bash
git add scripts/changelog_buffer.py scripts/tests/test_changelog_buffer.py
git commit -m "feat(v1.1.7): list + stale detection helpers — Task 2/11"
```

---

### Task 3: `consolidate_to_entry` (manifest list → markdown entry)

**Files:**
- Modify: `scripts/changelog_buffer.py`
- Modify: `scripts/tests/test_changelog_buffer.py`

- [ ] **Step 1: failing test 작성 — consolidator 출력 검증**

**수정 후** (`scripts/tests/test_changelog_buffer.py` append)
```python
from scripts.changelog_buffer import consolidate_to_entry


def test_consolidate_two_tasks_into_single_entry(tmp_path: Path):
    base = tmp_path / "feat"
    _write(base / "task-01.md", {
        "task_id": 1, "task_name": "Init", "status": "DONE",
        "base_sha": "aaa", "commits": [{"sha": "aaa1", "message": "feat: init"}],
        "files_changed": [{"path": "src/a.py", "line_range": "1-10",
                            "summary": "create A", "risk_hints": []}],
        "concerns": [],
    })
    _write(base / "task-02.md", {
        "task_id": 2, "task_name": "Wire", "status": "DONE",
        "base_sha": "aaa1", "commits": [{"sha": "bbb2", "message": "feat: wire"}],
        "files_changed": [{"path": "src/b.py", "line_range": "5-20",
                            "summary": "wire B", "risk_hints": ["side-effect"]}],
        "concerns": [],
    })
    out = consolidate_to_entry(
        manifests_dir=base,
        ch_id="CH-FIXTURE-100",
        timestamp="2026-05-09 18:00",
    )
    assert "[코드-수정] (batch: tasks 1..2)" in out
    assert "CH-FIXTURE-100" in out
    assert "src/a.py" in out and "src/b.py" in out
    assert "side-effect" in out
    assert "변경 전/후 코드: 생략" in out
    assert "aaa1" in out and "bbb2" in out
```

- [ ] **Step 2: test 실행해서 fail**

```bash
pytest scripts/tests/test_changelog_buffer.py::test_consolidate_two_tasks_into_single_entry -v
```
Expected: FAIL — `ImportError: cannot import name 'consolidate_to_entry'`

- [ ] **Step 3: consolidator 구현**

**수정 후** (`scripts/changelog_buffer.py` append)
```python
def consolidate_to_entry(
    manifests_dir: Path,
    ch_id: str,
    timestamp: str,
) -> str:
    """Build a single git-fast slim [코드-수정] entry from buffer manifests.

    Code blocks are intentionally omitted — git show <SHA> is the source
    of truth in per-task commit_policy mode (AC-4).
    """
    manifests = [read_manifest(p) for p in list_buffer_files(manifests_dir)]
    if not manifests:
        raise ValueError("no manifests to consolidate")

    task_ids = [m["task_id"] for m in manifests]
    files = sorted({fc["path"] for m in manifests for fc in m.get("files_changed", [])})
    risks = sorted({r for m in manifests for fc in m.get("files_changed", [])
                     for r in fc.get("risk_hints", [])})
    all_shas = [c["sha"] for m in manifests for c in m.get("commits", [])]

    lines = [
        f"### [{timestamp}] [코드-수정] (batch: tasks {min(task_ids)}..{max(task_ids)})",
        f"- **id**: {ch_id}",
        "- **이유**: 서브에이전트 모드 task batch 종합 (end-of-run consolidation)",
        f"- **무엇이**: {', '.join(files)}",
        "- **영향범위**: 누적 (task별 세부 참조)",
        f"- **위험 카테고리**: {', '.join(risks) if risks else 'none'}",
        f"- **task별 세부 ({len(manifests)}건)**:",
    ]
    for m in manifests:
        for fc in m.get("files_changed", []):
            shas = ", ".join(f"`{c['sha']}`" for c in m.get("commits", []))
            lines.append(
                f"  - Task {m['task_id']}: `{fc['path']}:{fc['line_range']}`"
                f" — {fc['summary']} (`{','.join(fc.get('risk_hints', [])) or 'none'}`)"
                f" — commits: {shas}"
            )
    lines.append(f"- **연관 commits**: {', '.join(all_shas)}")
    lines.append("- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: test 통과 확인**

```bash
pytest scripts/tests/test_changelog_buffer.py::test_consolidate_two_tasks_into_single_entry -v
```
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add scripts/changelog_buffer.py scripts/tests/test_changelog_buffer.py
git commit -m "feat(v1.1.7): consolidate_to_entry helper — Task 3/11"
```

---

### Task 4: `change-history` 스킬 — 신규 entry types + 슬림 schema + batch entry section

**Files:**
- Modify: `skills/change-history/SKILL.md`

- [ ] **Step 1: 사전 grep 베이스라인 — 현재 entry type 5종 확인**

```bash
grep -nE '\[요구사항-수정 \| 개발방향-수정' skills/change-history/SKILL.md
```
Expected: 1 매치 (line 31, common entry schema)

- [ ] **Step 2: When-to-Use 표 + Common Entry Schema 에 [검증]/[릴리즈] 추가**

**원본** (`skills/change-history/SKILL.md:18-37`)
```markdown
## When to Use

| Trigger | Append to |
|---|---|
| <slug>-requirements.md edited | <slug>-requirements.md `## 변경이력` |
| <slug>-tech-design.md edited | <slug>-tech-design.md `## 변경이력` |
| <slug>-implementation-plan.md edited | <slug>-implementation-plan.md `## 변경이력` |
| Code edited via /execute-plan | <slug>-implementation-plan.md `## 변경이력` (with [코드-수정] tag, before/after code blocks) |
| API test executed via /api-test | <slug>-implementation-plan.md `## 변경이력` (with [API테스트] tag) |

## Common Entry Schema (all 3 MDs)

```markdown
### [YYYY-MM-DD HH:MM] [요구사항-수정 | 개발방향-수정 | 구현계획서-수정 | 코드-수정 | API테스트]
- **id**: CH-YYYYMMDD-NNN
- **이유**: <why the change>
- **무엇이**: <which section/field/file>
- **영향범위**: <which downstream MDs or code areas were also touched>
- **연관 항목**: CH-... (related entries; omit if none)
```
```

**수정 후**
```markdown
## When to Use

| Trigger | Append to |
|---|---|
| <slug>-requirements.md edited | <slug>-requirements.md `## 변경이력` |
| <slug>-tech-design.md edited | <slug>-tech-design.md `## 변경이력` |
| <slug>-implementation-plan.md edited | <slug>-implementation-plan.md `## 변경이력` |
| Code edited via /execute-plan | <slug>-implementation-plan.md `## 변경이력` (with [코드-수정] tag) |
| Verification-only task (no code change) | <slug>-implementation-plan.md `## 변경이력` (with `[검증]` tag) |
| Release / version bump / git tag | <slug>-implementation-plan.md `## 변경이력` (with `[릴리즈]` tag) |
| API test executed via /api-test | <slug>-implementation-plan.md `## 변경이력` (with [API테스트] tag) |

## Common Entry Schema (all 3 MDs)

```markdown
### [YYYY-MM-DD HH:MM] [요구사항-수정 | 개발방향-수정 | 구현계획서-수정 | 코드-수정 | 검증 | 릴리즈 | API테스트]
- **id**: CH-YYYYMMDD-NNN
- **이유**: <why the change>
- **무엇이**: <which section/field/file>
- **영향범위**: <which downstream MDs or code areas were also touched>
- **연관 항목**: CH-... (related entries; omit if none)
```
```

- [ ] **Step 3: Code-Change Entry 직후에 신규 entry type 섹션 추가 (`[검증]` `[릴리즈]` + git-fast slim batch)**

**원본** (`skills/change-history/SKILL.md:100-103`)
```markdown
No 영향범위, no 위험 카테고리, no before/after code blocks. The `(trivial)` tag makes filtering / spotting these in 변경이력 easy.

If any of the trivial criteria fails, fall back to the full Code-Change Entry above.

## API-Test Entry (only in <slug>-implementation-plan.md)
```

**수정 후**
```markdown
No 영향범위, no 위험 카테고리, no before/after code blocks. The `(trivial)` tag makes filtering / spotting these in 변경이력 easy.

If any of the trivial criteria fails, fall back to the full Code-Change Entry above.

## Verification Entry — `[검증]` (v1.1.7+)

For tasks that did NOT change code (static grep, fixture run, release sanity, git tag-only). Use this instead of `[코드-수정]` when 변경 전/후 코드 blocks would be empty.

```markdown
### [YYYY-MM-DD HH:MM] [검증] (task: Task N — <task name>)
- **id**: CH-YYYYMMDD-NNN
- **이유**: <검증 목적 — e.g., 정적 grep 통과 / 릴리즈 전 sanity>
- **무엇이**: <검증한 항목들 — e.g., AC-1 grep / G1 fixture run>
- **결과**: PASS | FAIL | PARTIAL — <상세>
- **연관 commit**: <SHA, 해당 시>
- **연관 항목**: CH-... (omit if none)
```

No 위험 카테고리, no 변경 전/후 code (the task didn't change code).

## Release Entry — `[릴리즈]` (v1.1.7+)

For version bumps, manifest sync, git tag operations.

```markdown
### [YYYY-MM-DD HH:MM] [릴리즈]
- **id**: CH-YYYYMMDD-NNN
- **이유**: <버전 bump 이유>
- **무엇이**: vX.Y.Z 태그 + N개 manifest 동기화
- **연관 commit**: <SHA>, <tag SHA>
```

## End-of-Run Consolidated Batch Entry (v1.1.7+, git-fast mode only)

When `executing-plans` or `js-super-subagent-driven-development` finishes ALL tasks under `commit_policy: per-task` (git-fast mode), the main agent appends ONE consolidated entry covering every task's code edits — instead of N per-task entries. Code blocks are omitted because `git show <commit-SHA>` is the audit trail; the entry references SHAs only.

```markdown
### [YYYY-MM-DD HH:MM] [코드-수정] (batch: tasks N..M)
- **id**: CH-YYYYMMDD-NNN
- **이유**: <feature-level 종합 요약>
- **무엇이**: <comma-separated file list (전체 task 합쳐서)>
- **영향범위**: <combined>
- **위험 카테고리**: <union of all task hits — e.g., "side-effect, breaking" or "none">
- **task별 세부 (M건)**:
  - Task N: `<file:lines>` — <요약> (`<risk-or-none>`) — commits: `<SHA1>`, `<SHA2>`
  - Task N+1: ...
- **연관 commits**: <전체 SHA 리스트, 또는 BASE_SHA..HEAD>
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
```

`commit_policy: single` / `none` (memory-fallback) modes keep the legacy fat schema (변경 전/후 코드 blocks preserved) — git can't audit those modes, so the entry must.

## API-Test Entry (only in <slug>-implementation-plan.md)
```

- [ ] **Step 4: Anti-Patterns 표 행 4 ("Batch entries at end of session") 와 Acceptance §3 갱신 — v1.1.7과 모순 제거**

**원본** (`skills/change-history/SKILL.md:154-157`)
```markdown
| Wrong | Right |
|---|---|
| "This change is too small to log" | Even tiny edits decay context over time. Log everything. |
| "I'll invent a CH-id manually" | Duplicates and gaps will appear. Always use the helper script. |
| "git log already has the diff" | git log lacks intent, scope, risk category. Full schema in <slug>-implementation-plan.md. |
| "Batch entries at end of session" | Context evaporates. Append immediately after each edit. |
```

**수정 후**
```markdown
| Wrong | Right |
|---|---|
| "This change is too small to log" | Even tiny edits decay context over time. Log everything. |
| "I'll invent a CH-id manually" | Duplicates and gaps will appear. Always use the helper script. |
| "git log already has the diff (per-task mode)" | git log lacks intent, scope, risk category. Use slim entry + commit SHA in per-task mode. |
| "Batch entries at end of session" | Applies to manual editing only. Subagent / `/execute-plan` runs MUST batch (end-of-run consolidator) — see "End-of-Run Consolidated Batch Entry" section. |
```

**원본** (`skills/change-history/SKILL.md:170-174`)
```markdown
1. CH-id matches `CH-YYYYMMDD-NNN` and is unique within the feature folder
2. Entry sits at the end of the `## 변경이력` footer (not inserted into the body)
3. [코드-수정] entries include both before/after code blocks AND a 위험 카테고리 value, **unless tagged `(trivial)`** — trivial entries skip those fields by design
4. [API테스트] entries include scenario file, pass/fail counts, failure details
5. `(trivial)` is used ONLY when executing-plans Trivial-Edit Exception criteria are all met (≤3 lines + no logic change + 0/3 risk triggers); otherwise full entry is required
```

**수정 후**
```markdown
1. CH-id matches `CH-YYYYMMDD-NNN` and is unique within the feature folder
2. Entry sits at the end of the `## 변경이력` footer (not inserted into the body)
3. [코드-수정] entries: in `commit_policy: per-task` mode use slim batch form (코드 블록 생략 + commit SHA 참조 + 위험 카테고리); in `single` / `none` mode keep before/after code blocks AND a 위험 카테고리 value. `(trivial)` and `(batch: tasks N..M)` are recognised tag suffixes.
4. `[검증]` entries include 결과 (PASS/FAIL/PARTIAL); they have NO 위험 카테고리 / 코드 블록 by design.
5. `[릴리즈]` entries reference at minimum a 연관 commit (the bump commit) and the tag SHA when applicable.
6. [API테스트] entries include scenario file, pass/fail counts, failure details
7. `(trivial)` is used ONLY when executing-plans Trivial-Edit Exception criteria are all met (≤3 lines + no logic change + 0/3 risk triggers); otherwise full entry is required
```

- [ ] **Step 5: 사후 grep 검증 — 신규 type 명시됨**

```bash
grep -nE '\| Verification-only|\| Release / version|\[검증\] \(v1\.1\.7|\[릴리즈\] \(v1\.1\.7|End-of-Run Consolidated' skills/change-history/SKILL.md
```
Expected: 5 매치 (각 신규 섹션/표 행)

- [ ] **Step 6: commit**

```bash
git add skills/change-history/SKILL.md
git commit -m "feat(v1.1.7): change-history schema — [검증]/[릴리즈] + slim batch entry — Task 4/11"
```

---

### Task 5: `implementer-prompt.md` — Changes Manifest section + buffer write step

**Files:**
- Modify: `skills/js-super-subagent-driven-development/implementer-prompt.md`

- [ ] **Step 1: 사전 grep 베이스라인 — 현재 Report Format 섹션 위치**

```bash
grep -n '## Report Format' skills/js-super-subagent-driven-development/implementer-prompt.md
```
Expected: 1 매치 (line 126 부근)

- [ ] **Step 2: Report Format 섹션 직후 Changes Manifest 섹션 삽입**

**원본** (`skills/js-super-subagent-driven-development/implementer-prompt.md:126-138`)
```
    ## Report Format

    When done, report:
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - What you implemented (or what you attempted, if blocked)
    - What you tested and test results
    - Files changed (this list helps the main agent scope `git diff`)
    - Self-review findings (if any)
    - Any issues or concerns

    Use DONE_WITH_CONCERNS if you completed the work but have doubts about correctness.
    Use BLOCKED if you cannot complete the task. Use NEEDS_CONTEXT if you need
    information that wasn't provided. Never silently produce work you're unsure about.
```
```

**수정 후**
```
    ## Report Format

    When done, report:
    - **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
    - What you implemented (or what you attempted, if blocked)
    - What you tested and test results
    - Files changed (this list helps the main agent scope `git diff`)
    - Self-review findings (if any)
    - Any issues or concerns

    Use DONE_WITH_CONCERNS if you completed the work but have doubts about correctness.
    Use BLOCKED if you cannot complete the task. Use NEEDS_CONTEXT if you need
    information that wasn't provided. Never silently produce work you're unsure about.

    ## Changes Manifest (REQUIRED on DONE / DONE_WITH_CONCERNS) — v1.1.7+

    Before reporting back, write the manifest file. The main agent reads it
    at end-of-run to consolidate ALL tasks into a single 변경이력 entry — your
    per-task append step is gone (the controller no longer touches the footer
    until everything is finished).

    Path: `.js-super/changelog-buffer/<slug>/task-NN.md`
    (replace `<slug>` with the feature folder slug from the plan path; NN is your
    zero-padded task id, e.g. `task-05.md`).

    Use Python to write it (atomic + YAML-safe):

    ```bash
    python -c "
    from pathlib import Path
    from scripts.changelog_buffer import write_manifest
    write_manifest(Path('.js-super/changelog-buffer/<slug>/task-NN.md'), {
        'task_id': N,
        'task_name': '<task title>',
        'status': 'DONE',
        'base_sha': '<BASE_SHA from controller>',
        'commits': [
            {'sha': '<SHA1>', 'message': '<msg1>'},
            {'sha': '<SHA2>', 'message': '<msg2>'},
        ],
        'files_changed': [
            {'path': 'src/foo.py', 'line_range': '42-58',
             'summary': 'Add X validation', 'risk_hints': ['side-effect']},
        ],
        'concerns': [],
    })
    "
    ```

    Field rules:
    - `risk_hints` is your **best guess** only (taxonomy: side-effect | breaking | race | empty list).
      The main agent re-runs the official 3-checklist and overrides if needed.
    - `files_changed[].line_range` is the post-edit range, e.g. `"42-58"`.
    - If the directory creation fails (permission, disk full), report status BLOCKED.
      Do NOT silently skip the manifest — the controller depends on it.

    Why YAML manifest + buffer file (not just a return-value report):
    - The buffer file survives if the main session is interrupted mid-run.
    - The next session reads the buffer and resumes consolidation instead of losing
      the per-task summary.
```

- [ ] **Step 3: 사후 grep 검증**

```bash
grep -nE 'Changes Manifest \(REQUIRED|\.js-super/changelog-buffer|write_manifest' skills/js-super-subagent-driven-development/implementer-prompt.md
```
Expected: ≥3 매치

- [ ] **Step 4: commit**

```bash
git add skills/js-super-subagent-driven-development/implementer-prompt.md
git commit -m "feat(v1.1.7): implementer-prompt — Changes Manifest + buffer write — Task 5/11"
```

---

### Task 6: `js-super-subagent-driven-development/SKILL.md` — Per-task Sequence rewrite + End-of-run consolidator

**Files:**
- Modify: `skills/js-super-subagent-driven-development/SKILL.md`

- [ ] **Step 1: 사전 grep — 현재 Per-task Sequence diagram + Detailed §1-4 위치**

```bash
grep -nE 'Per-task Sequence|메인 후처리|## 2\. 모든 task 완료 후' skills/js-super-subagent-driven-development/SKILL.md
```
Expected: 3 매치

- [ ] **Step 2: §1-4-(d) "변경이력 기록" 단계를 in-memory accumulator + buffer 무결성 확인으로 교체**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:160-167`)
```
```
# (d) 변경이력 기록
Read <slug>-implementation-plan.md  (1회)
Edit <slug>-implementation-plan.md  (변경이력 [코드-수정] entry 1개 append)

git add <slug>-implementation-plan.md
git commit -m "[log] task N: <요약>"
```
```

**수정 후**
```
```
# (d) Buffer 무결성 + accumulator (v1.1.7 — footer 안 건드림)
Read .js-super/changelog-buffer/<slug>/task-NN.md
- validate manifest schema (task_id, status, files_changed, commits, ...)
- if validation fails → ask implementer to re-emit OR raise STOP
- merge into in-memory accumulator (kept until "모든 task 완료 후")

(NOTE) per-task append + [log] commit은 v1.1.7 에서 제거됨.
실제 footer 갱신과 단일 [log] commit은 §2 "모든 task 완료 후" 에서 1회 발화.
```
```

- [ ] **Step 3: §2 "모든 task 완료 후" 를 end-of-run consolidator 흐름으로 확장**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:171-173`)
```markdown
### 2. 모든 task 완료 후
- `finishing-a-development-branch` 스킬 invoke
- 전체 테스트 재실행 + Merge / PR / 정리 옵션 제시
```

**수정 후**
```markdown
### 2. 모든 task 완료 후 — End-of-Run Consolidator (v1.1.7+)

이 단계는 1회만 발화. per-task append를 누적했다가 한꺼번에 정리.

#### 2-1. 누적 accumulator + buffer 디렉토리 종합

```bash
# Validate every task has a manifest
python -c "
from pathlib import Path
from scripts.changelog_buffer import list_buffer_files
files = list_buffer_files(Path('.js-super/changelog-buffer/<slug>'))
print(f'Found {len(files)} manifests; expected {len(plan_tasks)}')
"
```

If counts mismatch → STOP, ask user (some task likely BLOCKED or interrupted).

#### 2-2. "구현 요약" 메시지를 메인이 사용자에게 출력 (AC-2)

```
✅ <slug> 모든 task 완료. 구현 요약:
- 계획서 N tasks → 실제 본 commit M개 (follow-up M' 포함)
- RISK 트리거: side-effect=X / breaking=Y / race=Z (총 N건)
- 누락: <list 또는 "없음">
- 초과: <list 또는 "없음">  ← plan에 없던 follow-up commit 의 변경 범위
- 코드 변경 0건 task: <task 번호 list>  ← [검증] entry로 별도 기록
다음 단계: PR 작성 / finishing-a-development-branch
```

이 메시지가 plan ↔ 실제 코드 갭을 한 번에 노출 — 다음 단계(PR / merge) 진입의 자연스러운 게이트.

#### 2-3. footer 1회 일괄 갱신

```bash
# Generate consolidated [코드-수정] (batch: tasks N..M) entry
python -c "
from pathlib import Path
from scripts.changelog_buffer import consolidate_to_entry
print(consolidate_to_entry(
    manifests_dir=Path('.js-super/changelog-buffer/<slug>'),
    ch_id='<from change_id helper>',
    timestamp='<now>',
))
" >> .tmp-batch-entry.md
```

- Read `<slug>-implementation-plan.md` (1회)
- Edit `<slug>-implementation-plan.md` (`.tmp-batch-entry.md` 내용을 footer 끝에 append)
- 코드 변경 0건 task가 있으면 별도 `[검증]` entry도 함께 append (별도 CH-id)
- `rm .tmp-batch-entry.md`

#### 2-4. 단일 log commit + buffer cleanup

```bash
git add <slug>-implementation-plan.md
git commit -m "[log] all tasks: <one-line summary>"
rm -rf .js-super/changelog-buffer/<slug>
```

#### 2-5. finishing-a-development-branch invoke

- 전체 테스트 재실행 + Merge / PR / 정리 옵션 제시

### 3. 다음 세션 시작 시 stale buffer 검출

세션 시작 시 (이 스킬 호출 직후, 0번 단계 직전) `.js-super/changelog-buffer/<slug>/` 잔존 검사:

```bash
python -c "
from pathlib import Path
from scripts.changelog_buffer import detect_stale_buffer
stale = detect_stale_buffer(Path('.js-super/changelog-buffer'), '<slug>')
print(stale or 'no stale buffer')
"
```

발견되면 사용자에게 안내:
> "이전 세션의 미정리 buffer 발견: `.js-super/changelog-buffer/<slug>/task-{N..M}.md`. 복구해서 consolidator 1회만 실행할까요? — yes / no"

yes → §2-1~2-4 만 실행 (이전 task 본 commit은 이미 git에 있음 → 새 task 진입 안 함).
no → 사용자가 직접 정리 또는 삭제.
```

- [ ] **Step 4: Per-task Sequence diagram 의 노란색 박스 라벨 갱신 — 변경이력 append 표현 제거**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:87-88`)
```
    "[main] Read plan.md\n+ Edit plan.md (변경이력 append)" [shape=box style=filled fillcolor=lightyellow];
    "[main] git add plan.md\n+ git commit -m \"[log] task N\"" [shape=box style=filled fillcolor=lightyellow];
```

**수정 후**
```
    "[main] Read manifest\n+ accumulator merge\n(footer 안 건드림)" [shape=box style=filled fillcolor=lightyellow];
    "[end-of-run] consolidator\n→ 구현 요약 + footer 1회 + [log] all tasks" [shape=box style=filled fillcolor=lightcyan];
```

원본 (`skills/js-super-subagent-driven-development/SKILL.md:104-107`)
```
    "[main] Edit code: insert RISK comments\n+ follow-up commit" -> "[main] Read plan.md\n+ Edit plan.md (변경이력 append)";
    "RISK trigger?" -> "[main] Read plan.md\n+ Edit plan.md (변경이력 append)" [label="no"];
    "[main] Read plan.md\n+ Edit plan.md (변경이력 append)" -> "[main] git add plan.md\n+ git commit -m \"[log] task N\"";
    "[main] git add plan.md\n+ git commit -m \"[log] task N\"" -> "Mark task done in TodoWrite";
```

**수정 후**
```
    "[main] Edit code: insert RISK comments\n+ follow-up commit" -> "[main] Read manifest\n+ accumulator merge\n(footer 안 건드림)";
    "RISK trigger?" -> "[main] Read manifest\n+ accumulator merge\n(footer 안 건드림)" [label="no"];
    "[main] Read manifest\n+ accumulator merge\n(footer 안 건드림)" -> "Mark task done in TodoWrite";
    "Mark task done in TodoWrite" -> "[end-of-run] consolidator\n→ 구현 요약 + footer 1회 + [log] all tasks" [label="last task"];
```

- [ ] **Step 5: Acceptance §5 갱신 (per-task append → buffer manifest)**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:222-228`)
```markdown
A task is complete in this skill only when ALL hold:
1. Implementer reported DONE
2. Spec reviewer reported ✅ (재리뷰 후라도 OK)
3. 메인이 `git diff BASE_SHA HEAD` 추출 완료
4. 3-checklist 결과가 결정됨 (트리거 0이거나 RISK 주석 + commit 완료)
5. 변경이력 [코드-수정] entry append 완료 + commit
6. TodoWrite 체크
```

**수정 후**
```markdown
A task is complete in this skill only when ALL hold:
1. Implementer reported DONE + buffer manifest written (`.js-super/changelog-buffer/<slug>/task-NN.md`)
2. Spec reviewer reported ✅ (재리뷰 후라도 OK)
3. 메인이 `git diff BASE_SHA HEAD` 추출 완료
4. 3-checklist 결과가 결정됨 (트리거 0이거나 RISK 주석 + commit 완료)
5. 메인이 buffer manifest validate + accumulator 갱신 완료 (footer/commit 발화 없음 — §2 에서 1회 처리)
6. TodoWrite 체크

The whole run is complete only when §2 (End-of-Run Consolidator) emits the 구현 요약 message, appends consolidated entries, runs `[log] all tasks` commit, and removes the buffer directory.
```

- [ ] **Step 6: Red Flags 표 — "후처리는 끝에 한꺼번에 하자" 행을 v1.1.7 에 맞게 inversion**

**원본** (`skills/js-super-subagent-driven-development/SKILL.md:215-218`)
```markdown
| Thought | Reality |
|---|---|
| "spec reviewer도 빼자, 사전 게이트가 있잖아" | 사전 게이트는 plan ↔ 상위 정합성, spec reviewer는 plan task ↔ 코드 정합성. 다른 시각. |
| "후처리는 끝에 한꺼번에 하자" | task별 commit 격리가 깨지고 history 더러워짐. task당 즉시. |
| "RISK 트리거 잡으면 implementer한테 재시켜야 하나" | 아니. 메인이 직접 Edit. implementer 재디스패치는 비용↑. |
```

**수정 후**
```markdown
| Thought | Reality |
|---|---|
| "spec reviewer도 빼자, 사전 게이트가 있잖아" | 사전 게이트는 plan ↔ 상위 정합성, spec reviewer는 plan task ↔ 코드 정합성. 다른 시각. |
| "RISK 주석 follow-up commit도 끝에 모아 하자" | 아니. RISK 주석은 task별 즉시 (코드 인접 commit). batch 대상은 변경이력 footer 갱신뿐. |
| "RISK 트리거 잡으면 implementer한테 재시켜야 하나" | 아니. 메인이 직접 Edit. implementer 재디스패치는 비용↑. |
```

- [ ] **Step 7: 사후 grep 검증**

```bash
grep -nE 'End-of-Run Consolidator|accumulator merge|stale buffer|구현 요약|consolidate_to_entry' skills/js-super-subagent-driven-development/SKILL.md
```
Expected: ≥4 매치

- [ ] **Step 8: commit**

```bash
git add skills/js-super-subagent-driven-development/SKILL.md
git commit -m "feat(v1.1.7): subagent skill — end-of-run consolidator + stale recovery — Task 6/11"
```

---

### Task 7: `executing-plans/SKILL.md` — 인라인 모드 batch (D5)

**Files:**
- Modify: `skills/executing-plans/SKILL.md`

- [ ] **Step 1: 사전 grep — 현재 Phase 2 단계 위치**

```bash
grep -nE 'Phase 2 — Once per task|Batched log' skills/executing-plans/SKILL.md
```
Expected: 2 매치 부근 (line 69-74)

- [ ] **Step 2: Phase 2 의 "Batched log" 단계를 in-memory accumulator 로 교체**

**원본** (`skills/executing-plans/SKILL.md:69-75`)
```markdown
**Phase 2 — Once per task, AFTER all task edits + tests pass (commit happens LAST):**

The order matters: extract diff first (while plan.md is still clean), then edit plan.md, then commit code + plan together as ONE atomic task commit. This guarantees `git diff HEAD -- <code_files>` returns ONLY this task's code changes, never polluted by previous tasks' log appends.

3. **Extract before/after from working tree**: `git diff HEAD -- <code files only, NOT plan.md>` — parse hunks to fill 변경 전 / 변경 후 code blocks per file:line. (Working tree vs last commit's HEAD — captures THIS task's code edits since the last task commit.)
4. **Batched log**: Read <slug>-implementation-plan.md ONCE. Build ONE consolidated [코드-수정] entry covering ALL code edits made in this task. Edit ONCE to append. (Schema: id / 이유 / 무엇이 / 영향범위 / 위험 카테고리 / 세부 변경 list / 변경 전 코드 / 변경 후 코드 — see change-history skill for batched format.)
5. **Commit (scoped, code + plan together)**: `git add <explicit list of code files touched in this task> <slug>-implementation-plan.md` then `git commit -m "<task summary>"`. NEVER use `git add -A` or `git add .` — they sweep in unrelated untracked files (`.DS_Store`, build artifacts, temp logs). The code-file list MUST come from the in-memory `(file:line, ...)` tuples tracked during Phase 1; the plan file is added explicitly because it was just edited in step 4.
```

**수정 후**
```markdown
**Phase 2 — Once per task, AFTER all task edits + tests pass (commit happens LAST):**

Per task: code-only commit (plan.md untouched). Footer entry is deferred to end-of-run consolidator (v1.1.7+). This batches N tasks into a single consolidated [코드-수정] entry, drastically reducing footer noise + Read/Edit cost.

3. **Capture diff for accumulator** (NOT for footer): `git diff HEAD -- <code files only>` — parse hunks. Append `(task_id, file:line_range, summary, risk_categories, planned_commit_msg)` to in-memory accumulator. Do NOT touch <slug>-implementation-plan.md here.
4. **Commit (scoped, code only)**: `git add <explicit list of code files touched in this task>` then `git commit -m "<task summary>"`. NEVER use `git add -A` or `git add .`. The code-file list MUST come from the in-memory `(file:line, ...)` tuples tracked during Phase 1. plan.md is NOT included in this commit — it gets its own single `[log] all tasks` commit at end-of-run.

**Phase 3 — End-of-Run Consolidator (v1.1.7+, runs ONCE after final task):**

5. **Render "구현 요약" message** to the user: planned tasks vs actual commits (incl. follow-ups), RISK triggers by category, 누락/초과 list, code-zero-change tasks (→ separate `[검증]` entry).
6. **Build consolidated batch entry**: from in-memory accumulator → ONE `[코드-수정] (batch: tasks N..M)` entry per change-history slim schema (코드 블록 생략, 연관 commit SHA 참조). For any code-zero-change task, build a separate `[검증]` entry.
7. **Single footer append + log commit**: Read <slug>-implementation-plan.md once → Edit (append batch entry + 검증 entries) → `git add <slug>-implementation-plan.md` → `git commit -m "[log] all tasks: <one-line summary>"`.
8. **Cleanup**: nothing for inline mode (no buffer dir). Subagent path cleans `.js-super/changelog-buffer/<slug>/` separately — see `js-super-subagent-driven-development` skill §2-4.

This Phase 3 ordering is the **single source of truth for inline mode**. Subagent mode uses the same Phase 3 logic but reads manifests from the buffer directory instead of in-memory accumulator (per `js-super-subagent-driven-development` §2).
```

- [ ] **Step 3: 사후 grep 검증**

```bash
grep -nE 'Phase 3 — End-of-Run Consolidator|accumulator|\[log\] all tasks' skills/executing-plans/SKILL.md
```
Expected: ≥3 매치

- [ ] **Step 4: commit**

```bash
git add skills/executing-plans/SKILL.md
git commit -m "feat(v1.1.7): inline mode — Phase 3 end-of-run consolidator — Task 7/11"
```

---

### Task 8: Fixtures F1~F5 + README

**Files:**
- Create: `skills/js-super-subagent-driven-development/tests/F1-basic-batch/manifests/task-01.md`
- Create: `skills/js-super-subagent-driven-development/tests/F1-basic-batch/manifests/task-02.md`
- Create: `skills/js-super-subagent-driven-development/tests/F1-basic-batch/expected-entry.md`
- Create: `skills/js-super-subagent-driven-development/tests/F2-zero-code-task/manifests/task-01.md`
- Create: `skills/js-super-subagent-driven-development/tests/F2-zero-code-task/expected-entry.md`
- Create: `skills/js-super-subagent-driven-development/tests/F3-mode-schema-divergence/per-task-expected.md`
- Create: `skills/js-super-subagent-driven-development/tests/F3-mode-schema-divergence/single-mode-expected.md`
- Create: `skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/manifests/task-01.md`
- Create: `skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/manifests/task-02.md`
- Create: `skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/expected-detection.md`
- Create: `skills/js-super-subagent-driven-development/tests/F5-cleanup/before-state.md`
- Create: `skills/js-super-subagent-driven-development/tests/F5-cleanup/after-state.md`
- Create: `skills/js-super-subagent-driven-development/tests/README.md`

- [ ] **Step 1: failing pytest 작성 — F1 basic batch consolidation 골든 비교**

**수정 후** (`scripts/tests/test_changelog_buffer.py` append)
```python
def test_F1_basic_batch_fixture():
    fixtures = Path("skills/js-super-subagent-driven-development/tests/F1-basic-batch")
    out = consolidate_to_entry(
        manifests_dir=fixtures / "manifests",
        ch_id="CH-FIXTURE-100",
        timestamp="2026-05-09 18:00",
    )
    expected = (fixtures / "expected-entry.md").read_text()
    assert out.strip() == expected.strip()
```

- [ ] **Step 2: F1 fixtures 작성 — task-01.md / task-02.md / expected-entry.md**

**수정 후** (`skills/js-super-subagent-driven-development/tests/F1-basic-batch/manifests/task-01.md`, 신규)
```yaml
---
task_id: 1
task_name: "Init module"
status: DONE
base_sha: aaa0000
commits:
- sha: aaa1111
  message: "feat: init module"
files_changed:
- path: src/init.py
  line_range: "1-12"
  summary: "Create module entrypoint"
  risk_hints: []
concerns: []
---
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F1-basic-batch/manifests/task-02.md`, 신규)
```yaml
---
task_id: 2
task_name: "Wire validator"
status: DONE
base_sha: aaa1111
commits:
- sha: bbb2222
  message: "feat: wire validator"
files_changed:
- path: src/validator.py
  line_range: "5-30"
  summary: "Add input validator"
  risk_hints:
  - side-effect
concerns: []
---
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F1-basic-batch/expected-entry.md`, 신규)
```markdown
### [2026-05-09 18:00] [코드-수정] (batch: tasks 1..2)
- **id**: CH-FIXTURE-100
- **이유**: 서브에이전트 모드 task batch 종합 (end-of-run consolidation)
- **무엇이**: src/init.py, src/validator.py
- **영향범위**: 누적 (task별 세부 참조)
- **위험 카테고리**: side-effect
- **task별 세부 (2건)**:
  - Task 1: `src/init.py:1-12` — Create module entrypoint (`none`) — commits: `aaa1111`
  - Task 2: `src/validator.py:5-30` — Add input validator (`side-effect`) — commits: `bbb2222`
- **연관 commits**: aaa1111, bbb2222
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
```

- [ ] **Step 3: F2~F5 fixtures + tests/README.md 작성 (분량 압축, 핵심 케이스만)**

**수정 후** (`skills/js-super-subagent-driven-development/tests/F2-zero-code-task/manifests/task-01.md`, 신규)
```yaml
---
task_id: 1
task_name: "Static grep verification"
status: DONE
base_sha: aaa0000
commits: []
files_changed: []
concerns: []
verification:
  result: PASS
  details: "G1 grep 통과"
---
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F2-zero-code-task/expected-entry.md`, 신규)
```markdown
### [2026-05-09 18:00] [검증] (task: Task 1 — Static grep verification)
- **id**: CH-FIXTURE-100
- **이유**: 정적 grep 통과 검증
- **무엇이**: G1 grep
- **결과**: PASS — G1 grep 통과
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F3-mode-schema-divergence/per-task-expected.md`, 신규)
```markdown
# F3-per-task-mode (commit_policy: per-task / git-fast)
- 코드 블록 없음
- "변경 전/후 코드: 생략 — `git show <SHA>` 로 조회" 라인 필수
- "연관 commits" 라인 필수
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F3-mode-schema-divergence/single-mode-expected.md`, 신규)
```markdown
# F3-single-mode (commit_policy: single | none / memory-fallback)
- "변경 전 코드" + "변경 후 코드" 코드 블록 필수 (legacy fat schema)
- "연관 commits" 라인 없음 (commit이 1개뿐 또는 없음)
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/manifests/task-01.md`, 신규)
```yaml
---
task_id: 1
task_name: "Half-finished run task 1"
status: DONE
base_sha: aaa0000
commits:
- sha: aaa1111
  message: "feat: ..."
files_changed:
- path: src/x.py
  line_range: "1-5"
  summary: "..."
  risk_hints: []
concerns: []
---
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/manifests/task-02.md`, 신규)
```yaml
---
task_id: 2
task_name: "Half-finished run task 2"
status: DONE
base_sha: aaa1111
commits:
- sha: bbb2222
  message: "feat: ..."
files_changed:
- path: src/y.py
  line_range: "1-5"
  summary: "..."
  risk_hints: []
concerns: []
---
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F4-interrupt-recovery/expected-detection.md`, 신규)
```markdown
# F4-interrupt-recovery
세션 시작 시 `detect_stale_buffer(root, "F4")` 호출 결과:
- root/F4 디렉토리 존재 + task-01.md task-02.md 잔존
- 반환: `<root>/F4` (Path)
- 사용자에게 복구 prompt 노출되어야 함
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F5-cleanup/before-state.md`, 신규)
```markdown
# F5-cleanup before
- `.js-super/changelog-buffer/<slug>/task-{01,02}.md` 존재
- consolidator 직전 상태
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/F5-cleanup/after-state.md`, 신규)
```markdown
# F5-cleanup after
- consolidator 성공
- `[log] all tasks` commit 완료
- `.js-super/changelog-buffer/<slug>/` 디렉토리 자체 사라짐 (`rm -rf`)
```

**수정 후** (`skills/js-super-subagent-driven-development/tests/README.md`, 신규)
```markdown
# js-super-subagent-driven-development tests (v1.1.7)

| Fixture | 검증 대상 | 연결 AC | 자동? |
|---|---|---|---|
| F1-basic-batch | 2-task → consolidated entry 1개 (slim schema) | AC-1, AC-4 | ✅ pytest |
| F2-zero-code-task | 코드 0건 task → [검증] entry | AC-3 | (수동 비교) |
| F3-mode-schema-divergence | per-task vs single 모드 schema 분기 | AC-4 | (수동 비교) |
| F4-interrupt-recovery | 세션 끊긴 후 buffer 잔존 detection | R2 mitigation | ✅ pytest |
| F5-cleanup | consolidator 성공 후 buffer 디렉토리 cleanup | R4 mitigation | (수동 dogfood) |

자동 (pytest) 항목은 `scripts/tests/test_changelog_buffer.py` 의 `test_F1_basic_batch_fixture` 등으로 호출됨. 나머지는 dogfood (I1~I4) 에서 사용자가 직접 비교 검증.
```

- [ ] **Step 4: pytest 실행 — F1 fixture 통과 확인**

```bash
pytest scripts/tests/test_changelog_buffer.py::test_F1_basic_batch_fixture -v
```
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add skills/js-super-subagent-driven-development/tests scripts/tests/test_changelog_buffer.py
git commit -m "test(v1.1.7): F1~F5 fixtures + README — Task 8/11"
```

---

### Task 9: README.md v1.1.7 wording

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 사전 grep — line 22 v1.1.6 wording 위치**

```bash
grep -n 'v1\.1\.6\|docs-pretty.*code-pretty' README.md | head -5
```
Expected: 1~2 매치

- [ ] **Step 2: line 22 한 줄 갱신 — v1.1.7 batch consolidator 정책 추가**

**원본** (`README.md:22` 부근, 정확한 line 은 grep 으로 확인 후 교체)
```markdown
**v1.1.6**: docs-pretty/code-pretty doc-type별 분기 (산문 post-approval 1회 / 코드 per-draft-state) + Before/After 코드블록 컨벤션
```

**수정 후**
```markdown
**v1.1.7**: 서브에이전트 + 인라인 모드 변경이력 일괄정리 — task별 즉시 append → end-of-run consolidator 1회 (`[코드-수정] (batch: tasks N..M)` slim schema, `git show` 로 코드 조회) + 비-코드 task용 `[검증]`/`[릴리즈]` entry type + buffer 인터럽트 복구 (`.js-super/changelog-buffer/`)
```

(주의: 정확한 원문은 README.md 의 v1.1.6 줄 — 파일이 다른 경우 가까운 버전 changelog 라인을 위에 추가)

- [ ] **Step 3: 사후 grep 검증**

```bash
grep -n 'v1\.1\.7' README.md
```
Expected: ≥1 매치

- [ ] **Step 4: commit**

```bash
git add README.md
git commit -m "docs(v1.1.7): README — batch consolidator + [검증]/[릴리즈] one-liner — Task 9/11"
```

---

### Task 10: Version bump 1.1.6 → 1.1.7

**Files:**
- Modify: `package.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json`

- [ ] **Step 1: 사전 grep — 현재 버전 6 매니페스트 모두 1.1.6 인지 확인**

```bash
grep -n '1\.1\.6' package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json
```
Expected: ≥6 매치

- [ ] **Step 2: bump 스크립트 실행**

```bash
bash bump-version.sh 1.1.7
```
Expected output: 6 파일 모두 1.1.6 → 1.1.7 동기화

- [ ] **Step 3: 사후 grep 검증**

```bash
grep -nE '"version":\s*"1\.1\.7"' package.json .claude-plugin/plugin.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json
grep -nE '"version":\s*"1\.1\.7"' .claude-plugin/marketplace.json
```
Expected: 6 매치

- [ ] **Step 4: commit**

```bash
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json
git commit -m "chore: bump version 1.1.6 → 1.1.7"
```

---

### Task 11: 정적 검증 (G1~G3) + git tag v1.1.7

**Files:**
- (none — 검증/태그만)

- [ ] **Step 1: G1 — implementer-prompt 에 Changes Manifest 섹션 명시**

```bash
grep -nE 'Changes Manifest \(REQUIRED|\.js-super/changelog-buffer' skills/js-super-subagent-driven-development/implementer-prompt.md
```
Expected: ≥2 매치

- [ ] **Step 2: G2 — change-history 에 신규 entry type 명시**

```bash
grep -nE '\[검증\] \(v1\.1\.7|\[릴리즈\] \(v1\.1\.7|End-of-Run Consolidated' skills/change-history/SKILL.md
```
Expected: ≥3 매치

- [ ] **Step 3: G3 — `.gitignore` 에 buffer 경로 명시**

```bash
grep -n '\.js-super' .gitignore
```
Expected: ≥1 매치

- [ ] **Step 4: 전체 pytest 재실행 — 회귀 없음 확인**

```bash
source .venv/bin/activate
pytest scripts/tests/test_changelog_buffer.py -v
```
Expected: 6+ tests 모두 PASS

- [ ] **Step 5: git tag v1.1.7**

```bash
git tag -a v1.1.7 -m "v1.1.7 — subagent batch changelog consolidator + [검증]/[릴리즈] entries + buffer recovery"
```

- [ ] **Step 6: tag 확인 (push 는 사용자 수동)**

```bash
git tag --list 'v1.1.*'
```
Expected: ..., v1.1.6, v1.1.7

---

## 2. 위험 코드 지점

(tech-design §6 R1~R7 → 구현 위치 매핑)

- `scripts/changelog_buffer.py:write_manifest` — **side-effect**: `mkdir -p` 실패 시 manifest 손실 (R1) | mitigation: `target.parent.mkdir(parents=True, exist_ok=True)` + implementer-prompt 의 BLOCKED 보고 정책 (Task 1 / Task 5)
- `scripts/changelog_buffer.py:detect_stale_buffer` — **side-effect**: 인터럽트 잔존 buffer 미감지 시 footer 갱신 누락 (R2) | mitigation: 다음 세션 시작 시 호출 + 사용자 prompt (Task 2 / Task 6 §3)
- `skills/change-history/SKILL.md:Common Entry Schema` — **breaking**: schema 표 신규 entry type 추가로 외부 grep/parser 깨짐 가능 (R3) | mitigation: 기존 5종 그대로 유지, 추가만 (Task 4 Step 2~3)
- `.gitignore` — **side-effect**: cleanup 실패 시 leftover 누적 (R4) | mitigation: `.js-super/` 무조건 ignore + Task 6 §2-4 의 `rm -rf` (Task 1 / Task 6)
- `skills/change-history/SKILL.md:Acceptance §3` — **breaking**: per-task 모드 슬림 entry 도입으로 사용자 push-back 가능 (R5) | mitigation: schema 분기 명시 + trade-off 문서화 (Task 4 Step 4) — 추가 escape hatch 는 v1.1.8 backlog 후보
- `skills/executing-plans/SKILL.md:Phase 3` — **breaking**: 인라인 모드 패턴 변경 → v1.1.6 plan dogfood 와 호환 안 됨 (R6) | mitigation: 신규 plan 부터 적용, v1.1.6 plan footer 사후 재정리 안 함 (PRD 범위 밖, Task 7 + plan §3 롤백)
- `scripts/changelog_buffer.py:write_manifest` (path) — **race**: 다중 워크트리에서 같은 slug buffer 충돌 (R7) | mitigation: implementer-prompt 의 buffer 경로에 워크트리 분리 명시 — 각 워크트리는 자신의 `.js-super/` 를 가지므로 자연 격리됨 (Task 5 + .gitignore)

## 3. 롤백 전략

- **Code rollback**: 각 task commit (Task 1~10) 은 명확히 분리됨 → `git revert <SHA>` 또는 `git reset --hard <pre-Task-1-SHA>` 가능. v1.1.7 tag 은 Task 11 step 5 에서 박힘 → 롤백 시 `git tag -d v1.1.7` 도 함께.
- **Helper / fixtures**: 신규 파일이라 삭제만 하면 됨 (`rm -rf scripts/changelog_buffer.py scripts/tests/test_changelog_buffer.py skills/js-super-subagent-driven-development/tests`).
- **Skill 본문**: change-history / js-super-subagent-driven-development / executing-plans / implementer-prompt 4 파일 — `git checkout <pre-v1.1.7-SHA> -- <file>` 로 단일 파일 복원 가능.
- **Buffer 디렉토리**: `.gitignore` 등록 + 실제 사용은 v1.1.7 dogfood 부터 → 롤백 시 `rm -rf .js-super/` 한 번이면 깨끗.
- **Version**: `bump-version.sh 1.1.6` 로 6 매니페스트 일괄 복원.
- **Migration**: 없음 — v1.1.6 plan 의 기존 변경이력 entry 17개는 그대로 유지 (PRD 범위 밖 명시 따름).

---

## 변경이력
<!-- change-history skill auto-appends entries here, oldest first -->

### [2026-05-09 18:10] [구현계획서-수정]
- **id**: CH-20260509-003
- **이유**: 신규 구현계획서 작성 (v1.1.7 — 11 task 분해 + commit_policy: per-task)
- **무엇이**: 서브에이전트-변경이력-일괄정리-implementation-plan.md 전체 (Header / §1 Tasks 1~11 / §2 R1~R7 위험 코드 지점 / §3 롤백 전략)
- **영향범위**: 없음 (최초 생성). 다음 단계에서 /execute-plan 진입 시 11 task 실행 트리거. AC-1~5 + D1~D6 + R1~R7 + F1~F5 모두 task 매핑 완료 (verifying-spec gap=0 / conflict=0). Test 자동화: F1/F4 pytest, 나머지는 수동 비교 또는 dogfood.
- **연관 항목**: CH-20260509-001 (requirements), CH-20260509-002 (tech-design)

### [2026-05-09 18:25] [코드-수정] (task: Task 1 — .gitignore + helper skeleton)
- **id**: CH-20260509-004
- **이유**: v1.1.7 buffer 인프라 부트스트랩 — `.js-super/` ignore + write_manifest/read_manifest YAML helper
- **무엇이**: `.gitignore`, `scripts/changelog_buffer.py` (신규), `scripts/tests/test_changelog_buffer.py` (신규)
- **영향범위**: scripts/ 신규 모듈. 후속 Task 2/3/8 helper 확장 + Task 5 implementer-prompt 가 호출.
- **위험 카테고리**: side-effect (R1: mkdir 실패 케이스 — write_manifest의 `parents=True, exist_ok=True` 로 mitigation)
- **세부 변경 (3건)**:
  - `.gitignore:17-19` — `.js-super/` ignore 항목 추가 (R4 mitigation)
  - `scripts/changelog_buffer.py:1-27` (신규) — `write_manifest` + `read_manifest` YAML frontmatter 형식
  - `scripts/tests/test_changelog_buffer.py:1-23` (신규) — TDD failing test → PASS
- **연관 commits**: (이번 commit SHA, 후속 commit에서 채워짐)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회

### [2026-05-09 18:35] [코드-수정] (task: Task 2 — list + stale detection)
- **id**: CH-20260509-005
- **이유**: interrupt recovery 인프라 — buffer 파일 정렬 + 잔존 detection
- **무엇이**: `scripts/changelog_buffer.py` (확장), `scripts/tests/test_changelog_buffer.py` (확장)
- **영향범위**: helper 모듈만. 후속 Task 6 §3 (stale recovery) + Task 8 F4 fixture 가 사용.
- **위험 카테고리**: side-effect (R2 mitigation: detect_stale_buffer 가 잔존 buffer 자동 검출 — manifest 누락 방지)
- **세부 변경 (2건)**:
  - `scripts/changelog_buffer.py:30-45` — `list_buffer_files` (task id 정렬) + `detect_stale_buffer` (slug 디렉토리 잔존 시 Path 반환)
  - `scripts/tests/test_changelog_buffer.py:6-10,30-49` — import 확장 + `_write` helper + 3 테스트 추가 (sort / stale present / stale absent)
- **연관 commits**: (이번 commit SHA)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회

### [2026-05-09 18:45] [코드-수정] (task: Task 3 — consolidate_to_entry)
- **id**: CH-20260509-006
- **이유**: end-of-run consolidator 핵심 helper — manifest list → slim batch entry markdown 생성
- **무엇이**: `scripts/changelog_buffer.py` (확장), `scripts/tests/test_changelog_buffer.py` (확장)
- **영향범위**: end-of-run flow의 단일 source of truth. Task 6 §2-3 + Task 7 Phase 3 + Task 8 F1 fixture가 호출.
- **위험 카테고리**: none (helper 함수, side-effect 없음 — 입력 manifest는 실제 task의 결과 / 출력은 plan footer에 append 될 markdown 문자열)
- **세부 변경 (2건)**:
  - `scripts/changelog_buffer.py:46-85` — `consolidate_to_entry(manifests_dir, ch_id, timestamp)`. AC-4 충족: 코드 블록 생략 + 연관 commits SHA 참조 + task별 세부 list
  - `scripts/tests/test_changelog_buffer.py:59-85` — 2-task 시나리오 골든 비교 (assertion 6개 — tag/CH/files/risks/생략 라인/SHAs)
- **연관 commits**: (이번 commit SHA)
- **변경 전/후 코드**: 생략 — `git show <SHA>` 로 조회
