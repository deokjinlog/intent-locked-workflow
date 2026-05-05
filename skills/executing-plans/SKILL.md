---
name: executing-plans
description: Use when you have a written implementation plan (<slug>-implementation-plan.md) to execute in a separate session with review checkpoints. js-superpowers extension — picks git-fast mode (default, uses `git diff HEAD` against working tree pre-commit for before/after extraction so per-edit Read snapshot is skipped; commits code + plan log atomically per task) or memory-fallback mode (when no git or commits forbidden). Per-edit: risk-annotation 3-checklist + RISK comments. Per-task: ONE consolidated change-history [코드-수정] entry, drastically reducing 구현계획서.md Read/Edit cost.
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks task-by-task, with strict per-edit discipline that captures before/after code and risk annotations into <slug>-implementation-plan.md change-history.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note (subagent path):** This skill is the **inline** execution mode. If subagents are available (Claude Code, Codex) AND the user wants to preserve main context for large features, the recommended subagent path is `js-super-subagent-driven-development` (slim 2-stage: implementer + spec reviewer + main post-processing for RISK / 변경이력 / atomic commit). The original upstream `subagent-driven-development` (3-stage: + quality reviewer) is also available for compatibility but duplicates governance js-super already provides via `verifying-spec` + TDD + RISK + 변경이력.

## When to Use

- A <slug>-implementation-plan.md exists in `docs/features/<date>-<slug>/`
- Inline (single-session) execution preferred over per-task subagents
- Each task in the plan follows TDD bite-sized steps

## Plan Loading

### Step 1: Load and Review Plan
1. Read `docs/features/<date>-<slug>/<slug>-implementation-plan.md`
2. Review critically — list any gaps or concerns
3. If concerns exist: raise them with the user before starting
4. If clean: create TodoWrite tasks (one per plan task) and proceed

## Code Edit Discipline (REQUIRED — js-superpowers extension)

### Two execution modes

This skill picks ONE mode at task start based on git availability + plan policy:

| Mode | Trigger | Before-snapshot source |
|---|---|---|
| **git-fast** (default, optimized) | git repo present AND plan frontmatter `commit_policy: per-task` (or omitted) | `git diff HEAD -- <files>` (working tree vs HEAD) at task end, BEFORE commit |
| **memory-fallback** | git unavailable, OR plan frontmatter `commit_policy: single` / `none` | in-memory Read snapshot before every edit |

<HARD-GATE>
At task start (ONCE per `/execute-plan` run), run the mode check:

1. **Read plan frontmatter** for the `commit_policy` field (see writing-plans schema):
   - Field absent OR `per-task` → candidate mode = git-fast
   - `single` → candidate mode = memory-fallback (all tasks → one commit at end)
   - `none` → candidate mode = memory-fallback (no commits during run)
   - Any other value → STOP, ask user to clarify

2. **Check git availability**: `git rev-parse --git-dir` (Bash). If git unavailable, force mode = memory-fallback regardless of frontmatter.

3. **Final mode decision**:
   - Both checks point to git-fast → mode = git-fast
   - Either check forces memory-fallback → mode = memory-fallback. If frontmatter requested `single`/`none` (i.e., user-intentional), proceed silently. If git was unavailable but frontmatter said `per-task`, WARN the user once: "⚠️ git repo 미초기화 → memory-fallback 모드로 진행합니다. 변경 전 코드 보존 비용이 큽니다."

The chosen mode applies to the whole `/execute-plan` run. Do not switch mid-run.

**Why a frontmatter field, not prose detection:** Prose scanning ("commit 생략" 등 키워드 매칭) is unreliable. The frontmatter field is unambiguous, machine-checkable, and lives next to the plan it governs.
</HARD-GATE>

### git-fast mode (default)

**Phase 1 — Per code edit (repeat for each edit in the task):**
1. **Risk check**: Run risk-annotation 3-checklist on the planned change.
2. **Apply edit**: Edit/Write the file (insert `# ⚠️ RISK(...)` comments above risky lines as needed). Trust the Edit tool's success/failure return — do NOT re-Read just to confirm the comment landed.

(Repeat 1-2 for every code edit. Track `(file:line, risk_categories)` tuples in memory — before/after code is recovered from git later, no in-memory snapshot needed.)

**Phase 2 — Once per task, AFTER all task edits + tests pass (commit happens LAST):**

The order matters: extract diff first (while plan.md is still clean), then edit plan.md, then commit code + plan together as ONE atomic task commit. This guarantees `git diff HEAD -- <code_files>` returns ONLY this task's code changes, never polluted by previous tasks' log appends.

3. **Extract before/after from working tree**: `git diff HEAD -- <code files only, NOT plan.md>` — parse hunks to fill 변경 전 / 변경 후 code blocks per file:line. (Working tree vs last commit's HEAD — captures THIS task's code edits since the last task commit.)
4. **Batched log**: Read <slug>-implementation-plan.md ONCE. Build ONE consolidated [코드-수정] entry covering ALL code edits made in this task. Edit ONCE to append. (Schema: id / 이유 / 무엇이 / 영향범위 / 위험 카테고리 / 세부 변경 list / 변경 전 코드 / 변경 후 코드 — see change-history skill for batched format.)
5. **Commit (scoped, code + plan together)**: `git add <explicit list of code files touched in this task> <slug>-implementation-plan.md` then `git commit -m "<task summary>"`. NEVER use `git add -A` or `git add .` — they sweep in unrelated untracked files (`.DS_Store`, build artifacts, temp logs). The code-file list MUST come from the in-memory `(file:line, ...)` tuples tracked during Phase 1; the plan file is added explicitly because it was just edited in step 4.

### memory-fallback mode

**Phase 1 — Per code edit:**
1. **Before-snapshot**: Read the target file → capture the original code for the affected line range. Hold in memory.
2. **Risk check**: Run risk-annotation 3-checklist.
3. **Apply edit**: Edit/Write (with RISK comments).

(Repeat. Track `(file:line, before, after, risk_categories)` tuples in memory.)

**Phase 2 — Once per task, AFTER all edits + tests pass:**
4. **Batched log**: Read plan ONCE, append ONE consolidated [코드-수정] entry, Edit ONCE. Use in-memory snapshots for 변경 전 / 변경 후.
5. Commit if possible (some plans skip).

<HARD-GATE>
NEVER skip Phase 2 logging. In git-fast mode, **strict ordering is mandatory**: extract diff (while plan.md untouched) → edit plan.md → commit code + plan together. Reversing this (e.g., commit before diff, or edit plan before diff) will pollute future `git diff HEAD` outputs with stale log appends. In memory-fallback mode, before-snapshots must be captured BEFORE each edit (otherwise originals are gone) and held in memory until Phase 2.
</HARD-GATE>

## Trivial-Edit Exception (skip full discipline for tiny changes)

For changes that meet ALL of the following criteria, you MAY substitute a "trivial" path:

- Edit affects ≤ 3 lines
- No logic change (comments / docstrings / typos / unused-import cleanup / import reordering / whitespace only)
- risk-annotation 3-checklist returns 0/3 triggers (no side-effect / breaking / race signal)

When trivial:

1. **Skip before-snapshot** — irrelevant in both modes (git-fast doesn't need it; memory-fallback skips because no full block will be logged)
2. Risk check still runs to confirm 0/3
3. Apply edit runs as usual (typically no RISK comment needed since 0/3)
4. Log writes a **trivial entry** (no `git diff` extraction needed) instead of the full schema:

```markdown
### [YYYY-MM-DD HH:MM] [코드-수정] (trivial)
- **id**: CH-YYYYMMDD-NNN
- **이유**: <one-line reason, e.g. "타이포 수정 (witdraw → withdraw)">
- **무엇이**: <file:line>
```

No 영향범위, no 위험 카테고리, no before/after code blocks.

**git-fast mode: trivial 편집이라도 task당 1 commit은 반드시 유지.** 다음 task의 `git diff HEAD -- <code>` 가 깨끗하게 이번 task만 포함하려면 이번 task가 commit으로 닫혀야 함. "trivial이니 commit 생략"은 다음 task의 변경이력 정확성을 깨뜨림. (memory-fallback 모드는 commit 선택사항 그대로.)

**If ANY criterion is uncertain → fall back to full discipline.** Trivial is a fast path, not a shortcut for "anything that looks small".

<HARD-GATE>
Triviality is determined ONLY by the three criteria above. Logic changes — even one-line ones — are NOT trivial. When in doubt, take the safe path.
</HARD-GATE>

## Process Flow

```dot
digraph exec_flow {
    "Load <slug>-implementation-plan.md" [shape=box];
    "Critical review,\nraise concerns?" [shape=diamond];
    "Discuss with user" [shape=box];
    "Mode check\n(git-fast vs memory-fallback)" [shape=box];
    "Create TodoWrite" [shape=box];
    "Pick next [ ] task" [shape=box];
    "TDD: write failing test" [shape=box];
    "Run test → FAIL" [shape=box];
    "More edits in task?" [shape=diamond];
    "[memory-fallback]\nRead target file\n(before-snapshot)" [shape=box];
    "risk-annotation 3-checklist" [shape=box];
    "Apply Edit (with RISK comments)" [shape=box];
    "Run tests for this task" [shape=box];
    "All pass?" [shape=diamond];
    "[git-fast] git diff HEAD -- <code>\n→ extract before/after" [shape=box];
    "BATCHED LOG: ONE [코드-수정] entry\nfor whole task\n(Read+Edit 구현계획서.md once)" [shape=box];
    "[git-fast] git add <code> <plan>\n+ git commit (one atomic task commit)" [shape=box];
    "[memory-fallback] Commit if possible" [shape=box];
    "Mark task [x]" [shape=box];
    "All tasks done?" [shape=diamond];
    "Fix and retry" [shape=box];
    "Use finishing-a-development-branch" [shape=doublecircle];

    "Load <slug>-implementation-plan.md" -> "Critical review,\nraise concerns?";
    "Critical review,\nraise concerns?" -> "Discuss with user" [label="yes"];
    "Discuss with user" -> "Mode check\n(git-fast vs memory-fallback)";
    "Critical review,\nraise concerns?" -> "Mode check\n(git-fast vs memory-fallback)" [label="no"];
    "Mode check\n(git-fast vs memory-fallback)" -> "Create TodoWrite";
    "Create TodoWrite" -> "Pick next [ ] task";
    "Pick next [ ] task" -> "TDD: write failing test";
    "TDD: write failing test" -> "Run test → FAIL";
    "Run test → FAIL" -> "More edits in task?";
    "More edits in task?" -> "[memory-fallback]\nRead target file\n(before-snapshot)" [label="yes\n(memory-fallback)"];
    "More edits in task?" -> "risk-annotation 3-checklist" [label="yes\n(git-fast — skip Read)"];
    "[memory-fallback]\nRead target file\n(before-snapshot)" -> "risk-annotation 3-checklist";
    "risk-annotation 3-checklist" -> "Apply Edit (with RISK comments)";
    "Apply Edit (with RISK comments)" -> "More edits in task?";
    "More edits in task?" -> "Run tests for this task" [label="no — task edits done"];
    "Run tests for this task" -> "All pass?";
    "All pass?" -> "[git-fast] git diff HEAD -- <code>\n→ extract before/after" [label="yes (git-fast)"];
    "All pass?" -> "BATCHED LOG: ONE [코드-수정] entry\nfor whole task\n(Read+Edit 구현계획서.md once)" [label="yes (memory-fallback)"];
    "All pass?" -> "Fix and retry" [label="no"];
    "Fix and retry" -> "Apply Edit (with RISK comments)";
    "[git-fast] git diff HEAD -- <code>\n→ extract before/after" -> "BATCHED LOG: ONE [코드-수정] entry\nfor whole task\n(Read+Edit 구현계획서.md once)";
    "BATCHED LOG: ONE [코드-수정] entry\nfor whole task\n(Read+Edit 구현계획서.md once)" -> "[git-fast] git add <code> <plan>\n+ git commit (one atomic task commit)" [label="git-fast"];
    "BATCHED LOG: ONE [코드-수정] entry\nfor whole task\n(Read+Edit 구현계획서.md once)" -> "[memory-fallback] Commit if possible" [label="memory-fallback"];
    "[git-fast] git add <code> <plan>\n+ git commit (one atomic task commit)" -> "Mark task [x]";
    "[memory-fallback] Commit if possible" -> "Mark task [x]";
    "Mark task [x]" -> "All tasks done?";
    "All tasks done?" -> "Pick next [ ] task" [label="no"];
    "All tasks done?" -> "Use finishing-a-development-branch" [label="yes"];
}
```

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails repeatedly, instruction unclear)
- Plan has critical gaps preventing the next task
- A 위험 카테고리 is genuinely ambiguous AND the trigger seems significant
- Verification fails after two retries

Ask the user rather than guessing.

## When to Revisit Earlier Steps

**Return to Step 1 (Load and Review Plan) when:**
- The user updates the plan based on your feedback
- A fundamental approach in the plan needs rethinking (e.g., chosen library doesn't fit, an FR was misread)
- Mid-execution discoveries invalidate later tasks

**Don't force through blockers** — stop and ask. The plan can be wrong. If it is, route the change through `change-propagation` so <slug>-implementation-plan.md is updated coherently before resuming.

## Anti-Patterns

| Wrong | Right |
|---|---|
| (memory-fallback) Edit first, capture before-snapshot later | Always Read → snapshot → Edit. Otherwise original is gone. |
| (git-fast) Skip the per-task commit | Commit is REQUIRED — without it, the next task's `git diff HEAD` includes both tasks' changes and the log gets fabricated. |
| (git-fast) Edit plan.md BEFORE running `git diff` | The diff would then include the plan log append, polluting "변경 전 코드" with non-code content. Order: diff → edit plan → commit. |
| (git-fast) Commit code first, then edit plan as separate commit | Creates two commits per task; `git diff HEAD` next task is clean but commit history is noisy. The atomic single-commit approach (code + plan together at end) is correct. |
| (git-fast) `git add -A` or `git add .` | Sweeps unrelated untracked files into the commit. Use explicit file list from Phase 1 tuples + plan.md. |
| (git-fast) Include plan.md in the `git diff` extract | Extract scope = code files only. Plan changes are in the same commit but not in the "변경 전 코드" block. |
| Switch modes mid-run | Mode is decided at task-start mode-check. Stick to it. |
| Batch change-history entries at session end | Per-task immediate logging. Context evaporates fast. |
| Skip RISK annotation because "looks safe" | Run the 3-checklist. 0/3 means no annotation, but the check happens. |
| Skip Phase 2 logging | HARD-GATE violation. Revert + redo. |
| Marking a logic-changing edit as "trivial" to skip discipline | Triviality requires zero logic change AND 0/3 risk triggers AND ≤3 lines. Logic changes are NEVER trivial. |
| Force progress through a blocker | Stop. Ask. The plan can be wrong. |
| Inferring commit policy from prose ("commit 안 할게") | Read `commit_policy` from plan frontmatter only. If user wants a different policy, route through change-propagation to update the field, then re-run the mode check. |
| Frontmatter says `per-task` but user verbally says skip commits mid-run | Stop and reconcile the field first (change-propagation). Do not silently switch modes. |

## Red Flags

| Thought | Reality |
|---|---|
| "This is a tiny tweak, skip discipline" | Tiny tweaks are exactly where regressions hide. Run the 4 steps. |
| "User won't notice if I skip the entry" | The user is reviewing 변경이력 later. They'll notice. |
| "Plan said do X, but I think Y is better" | Stop. Update the plan via change-propagation, then proceed. |

## Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use `finishing-a-development-branch`
- Follow that skill to verify tests, present options, execute the user's choice

## Remember
- Review plan critically before starting
- Pick mode (git-fast vs memory-fallback) at task-start mode-check; do not switch
- Follow plan steps exactly
- Per-edit discipline: risk-check → apply (memory-fallback adds before-snapshot Read upfront)
- Per-task discipline: tests pass → (git-fast: commit + git diff) → batched log → mark task done
- Don't skip verifications — if a step says "run X, expect Y", run X and confirm Y
- Reference skills when the plan says to (e.g., "use risk-annotation here")
- Never start implementation on main/master without explicit user consent
- Ask when blocked

## Related Skills

- `risk-annotation` — invoked on every code edit for the 3-checklist
- `change-history` — invoked on every code edit for the [코드-수정] entry
- `change-propagation` — invoked when an in-flight insight requires plan/spec edits
- `js-super-subagent-driven-development` — recommended subagent path (slim 2-stage + main post-processing)
- `subagent-driven-development` — upstream original subagent path (3-stage, kept for compatibility)
- `finishing-a-development-branch` — final wrap-up after all tasks
