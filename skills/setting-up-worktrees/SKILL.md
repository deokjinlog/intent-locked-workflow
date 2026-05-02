---
name: setting-up-worktrees
description: Use when the user asks to create one or more git worktrees ("워크트리 만들어줘", "<티켓명> 워크트리"). Default location is <project-root>/.worktrees/<branch-name>; creates the branch from current HEAD if it doesn't exist, then auto-copies ALL existing .env* files (.env, .env.local, .env.production, etc.) so the user can immediately build/run a server in each worktree. NEVER asks the user which env files to copy — always auto-glob.
---

# Setting Up Worktrees (Quick Batch Creation)

User-personal workflow shortcut for spinning up multiple parallel work streams. Each worktree gets its own branch and an automatic copy of every `.env*` file present in the project root, so the user can build/run servers concurrently without env-loading fights.

<HARD-GATE>
This skill MUST be invoked from a git repository. If the current working directory is not inside a git repo (`git rev-parse --is-inside-work-tree` returns false), abort and tell the user to run `git init` first or switch to the target project.
</HARD-GATE>

<HARD-GATE>
NEVER ask the user which env files to copy. ALWAYS auto-glob `.env*` in the project root and copy every match. The user only specifies branch names — env-file selection is automatic. The single exception: if the user EXPLICITLY says "X 파일은 복사하지 마" (exclude pattern), honor that.
</HARD-GATE>

## Trigger Examples

- 단수: `/worktree feature-a`
- 복수: `/worktree feature-a feature-b feature-c`
- 자연어: "워크트리 3개 만들어줘. 브랜치는 feature-a, feature-b, feature-c."

> 사용자가 실제 티켓명(예: `TICKET-123-기능명`)으로 호출하면 그대로 브랜치명에 사용한다. 위 `feature-a` 등은 placeholder.

## Defaults (No User Prompt)

| Knob | Default behavior |
|---|---|
| Worktree root | `<project-root>/.worktrees/` (override only if user explicitly asks) |
| Branch creation | If branch missing → `-b <name>` from current HEAD. Existing local → use as-is. Remote-only → `-B <name> origin/<name>` |
| Env files copied | **Auto-glob `.env*` (excludes `.env.example`, `.env.sample`)**. ALL matches copied to every worktree. |
| `.worktrees/` in `.gitignore` | Auto-add if missing |

## Process

```dot
digraph wt_flow {
    "Verify git repo" [shape=box];
    "Parse branch list" [shape=box];
    "Auto-glob .env* files\n(no user prompt)" [shape=box];
    "Ensure .worktrees/ exists\n+ in .gitignore" [shape=box];
    "For each branch" [shape=box];
    "Branch exists?" [shape=diamond];
    "git worktree add <path> <branch>" [shape=box];
    "git worktree add -b <branch> <path>" [shape=box];
    "Copy ALL detected env files" [shape=box];
    "Report summary" [shape=doublecircle];

    "Verify git repo" -> "Parse branch list";
    "Parse branch list" -> "Auto-glob .env* files\n(no user prompt)";
    "Auto-glob .env* files\n(no user prompt)" -> "Ensure .worktrees/ exists\n+ in .gitignore";
    "Ensure .worktrees/ exists\n+ in .gitignore" -> "For each branch";
    "For each branch" -> "Branch exists?";
    "Branch exists?" -> "git worktree add <path> <branch>" [label="local or remote"];
    "Branch exists?" -> "git worktree add -b <branch> <path>" [label="new"];
    "git worktree add <path> <branch>" -> "Copy ALL detected env files";
    "git worktree add -b <branch> <path>" -> "Copy ALL detected env files";
    "Copy ALL detected env files" -> "For each branch" [label="next"];
    "Copy ALL detected env files" -> "Report summary" [label="done"];
}
```

## Procedure (Step-by-Step)

**Step 0 — Verify git context**

```bash
git rev-parse --is-inside-work-tree   # must print "true"
ROOT=$(git rev-parse --show-toplevel)
```

If not in a repo, abort with: "현재 디렉터리가 git repo 아닙니다. `git init` 후 다시 호출해주세요."

**Step 1 — Parse branch names from user's message**

Extract `BRANCHES=(...)` from the user's message. Korean ticket-style names like `<TICKET>-<번호>-<설명>` are fine (UTF-8 OK). Do NOT ask about env files — those are auto-detected.

**Step 2 — Auto-detect `.env*` files (NO user prompt)**

```bash
ENV_FILES=()
for f in "$ROOT"/.env*; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    # Skip templates (committed examples) — they're already in the worktree via git checkout
    case "$name" in
        .env.example|.env.sample|.env.template) continue ;;
    esac
    ENV_FILES+=("$name")
done
```

If `ENV_FILES` is empty after this, log a notice ("ℹ️ 프로젝트 루트에 .env* 파일 없음 — env 복사 skip") and proceed without copying. Don't abort.

**Step 3 — Ensure `.worktrees/` exists and is gitignored**

```bash
mkdir -p "$ROOT/.worktrees"

if ! grep -qE '^\.worktrees/?$' "$ROOT/.gitignore" 2>/dev/null; then
    echo ".worktrees/" >> "$ROOT/.gitignore"
fi
```

**Step 4 — For each branch, create or attach the worktree**

```bash
for BR in "${BRANCHES[@]}"; do
    WT_PATH="$ROOT/.worktrees/$BR"

    # Already a worktree? Skip with notice
    if [ -d "$WT_PATH" ]; then
        echo "⏭️  $BR — 이미 존재 ($WT_PATH), 건너뜀"
        continue
    fi

    # Branch exists locally?
    if git show-ref --verify --quiet "refs/heads/$BR"; then
        git worktree add "$WT_PATH" "$BR"
    # Exists on remote?
    elif git show-ref --verify --quiet "refs/remotes/origin/$BR"; then
        git worktree add -B "$BR" "$WT_PATH" "origin/$BR"
    # Brand new
    else
        git worktree add -b "$BR" "$WT_PATH"
    fi
done
```

**Step 5 — Copy ALL detected env files into each worktree (no prompts)**

```bash
for BR in "${BRANCHES[@]}"; do
    WT_PATH="$ROOT/.worktrees/$BR"
    [ -d "$WT_PATH" ] || continue   # was skipped earlier
    for EF in "${ENV_FILES[@]}"; do
        cp "$ROOT/$EF" "$WT_PATH/$EF"
        echo "📋 $BR ← $EF 복사 완료"
    done
done
```

**Step 6 — Report summary**

Print a Korean-friendly summary listing each worktree path + the env files copied:

```
✅ 워크트리 생성 완료 (n개)
감지된 .env* 파일: .env, .env.local, .env.production (3개)

- feature-a   → .worktrees/feature-a   (.env ✓ .env.local ✓ .env.production ✓)
- feature-b   → .worktrees/feature-b   (.env ✓ .env.local ✓ .env.production ✓)
- feature-c   → .worktrees/feature-c   (.env ✓ .env.local ✓ .env.production ✓)

각 워크트리에서 바로 빌드·서버 실행 가능합니다.
정리: `git worktree remove <path>`
```

## Anti-Patterns

| Wrong | Right |
|---|---|
| Asking the user "which env files to copy?" | Forbidden by HARD-GATE. Auto-glob `.env*` and copy all (except templates). |
| Skipping env copy because user didn't mention it | Always copy all detected `.env*`. The point is build-ready worktrees. |
| Force-create when worktree path already exists | Detect + skip with notice. Don't clobber user's WIP. |
| Skip `.gitignore` update | Always add `.worktrees/` (idempotent check). |
| Use `git checkout -b` first then `worktree add` | Prefer `worktree add -b <branch> <path>` (atomic). |
| Copy `.env.example` (template, already in git) | Excluded from glob. |

## Red Flags

| Thought | Reality |
|---|---|
| "Branch name has Korean — might break" | git handles UTF-8 branch names fine. Don't sanitize unless user asks. |
| "Should I confirm which env files?" | NO. HARD-GATE forbids it. Auto-glob always. |
| ".gitignore is annoying to update" | Idempotent: only append if not already there. One-time cost. |
| "User has secrets in .env, scary to copy automatically" | Files are already on disk; copying within the same machine doesn't expand exposure. The .worktrees/ folder is gitignored. |

## Cleanup (separate operation)

If the user later asks to remove a worktree:

```bash
git worktree remove "$ROOT/.worktrees/<branch>"
git branch -d <branch>   # only if no longer needed
```

This skill does NOT auto-remove. Removal is destructive and must be explicit.

## Acceptance

After running this skill:
1. Each requested branch has a worktree at `<root>/.worktrees/<branch>/`
2. Every `.env*` file from the project root (except `.env.example`/`.env.sample`/`.env.template`) is copied into each worktree
3. `.worktrees/` is in `.gitignore`
4. `git worktree list` shows all created worktrees
5. User got a summary report listing each worktree's path + per-file copy status
6. The user was NOT asked which env files to copy

## Related Skills

- `using-git-worktrees` (upstream, broader) — general guidance on worktree workflows
- `executing-plans` — often run inside a freshly-created worktree
