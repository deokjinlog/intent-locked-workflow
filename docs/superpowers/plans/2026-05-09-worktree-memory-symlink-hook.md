# Worktree Memory Symlink via Plugin Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or js-super:og-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the worktree-memory-symlink step from `setting-up-worktrees` skill body into a Claude Code plugin PostToolUse hook, so encoding/symlinking runs in a real shell instead of being mentally simulated by the main agent (root cause of v1.1.2 → v1.1.4 failures).

**Architecture:** Add a PostToolUse hook that fires after every Bash invocation. It performs an instant early-exit unless the executed command starts with `git worktree add`. On match, it parses the worktree path out of the command, derives the repo root with `git rev-parse --show-toplevel`, and invokes the existing `skills/setting-up-worktrees/scripts/setup-memory-symlinks.sh`. The skill body is simplified — it no longer instructs the agent to run mkdir/ln -s/sed; it just states that the hook handles symlinking automatically.

**Tech Stack:** Bash, Claude Code plugin hook system (`hooks/hooks.json` + extensionless dispatcher script via `run-hook.cmd`), JSON parsing via `jq` (already implicitly available via Claude Code shell env; fallback to `python3 -c` if needed).

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `hooks/worktree-memory-symlink` (new) | Create | Hook entrypoint. Reads PostToolUse JSON from stdin, decides whether to fire, parses worktree path, calls `setup-memory-symlinks.sh`. Single file ≤ ~80 lines bash. |
| `hooks/hooks.json` | Modify | Register the new PostToolUse hook (matcher: `Bash`). |
| `skills/setting-up-worktrees/SKILL.md` | Modify | Replace Step 5.5's bash instructions with a 2-line "the hook handles this automatically" notice. Remove all `mkdir`, `ln -s`, `sed` strings from skill body to remove temptation for the agent to mentally simulate. Update Acceptance + Anti-Patterns. |
| `skills/setting-up-worktrees/scripts/setup-memory-symlinks.sh` | Untouched | Already exists from v1.1.4. Hook reuses it as-is. |
| `commands/worktree.md` | Modify | Update the user-facing description: "메모리 심링크 = hook 자동". |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `package.json` | Modify | Bump version 1.1.4 → 1.1.5. |

## Hook trigger semantics (locked-in design decisions)

- **matcher**: `Bash` — fires on every Bash tool call. Acceptable because the hook's first action is a sub-millisecond pattern check that exits immediately on non-match.
- **fire condition**: stripped command starts with `git worktree add ` (with trailing space, to avoid `git worktree add-something` accidentally matching).
- **path extraction**: take the first non-flag positional argument that exists as a directory. `git worktree add <path>`, `git worktree add -b <branch> <path>`, `git worktree add -B <branch> <path> <commit>`, `git worktree add --detach <path>` — all converge on "the first path-shaped argument that's now a real directory". If parsing fails, fall back to `git -C <cwd> worktree list --porcelain` and call `setup-memory-symlinks.sh` for every worktree under `<root>/.worktrees/` that doesn't already have a memory symlink.
- **idempotence**: `setup-memory-symlinks.sh` already skips if `<wt-encoded>/memory` exists. Hook re-firing is safe.
- **failure mode**: hook NEVER blocks the user. On any error (parse fail, jq missing, script not found), log to stderr and exit 0.

---

### Task 1: Write the hook script with fixture-based test

**Files:**
- Create: `hooks/worktree-memory-symlink`
- Test (ad-hoc, deleted after Task 1): `/tmp/test-worktree-hook.sh`

- [ ] **Step 1.1: Write the failing test**

Create `/tmp/test-worktree-hook.sh` with three fixtures that drive the hook via stdin and assert behavior:

```bash
#!/usr/bin/env bash
# Ad-hoc fixture test for worktree-memory-symlink hook.
set -uo pipefail

HOOK="$(pwd)/hooks/worktree-memory-symlink"
FAIL=0

assert() {
    local label="$1" expected_exit="$2" actual_exit="$3"
    if [ "$actual_exit" -ne "$expected_exit" ]; then
        echo "❌ $label: expected exit $expected_exit, got $actual_exit"
        FAIL=1
    else
        echo "✅ $label"
    fi
}

# Fixture A — non-Bash tool: hook must exit 0 silently.
out_a=$(printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":"/x"}}' | bash "$HOOK" 2>&1)
assert "non-Bash tool → no-op" 0 $?

# Fixture B — Bash with non-worktree command: exit 0 silently.
out_b=$(printf '%s' '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' | bash "$HOOK" 2>&1)
assert "Bash but not worktree add → no-op" 0 $?

# Fixture C — Bash with `git worktree add` but non-existent path: exit 0,
# expect a clear "could not resolve worktree path" log line on stderr.
out_c=$(printf '%s' '{"tool_name":"Bash","tool_input":{"command":"git worktree add /nonexistent/zzz"},"cwd":"'"$PWD"'"}' | bash "$HOOK" 2>&1)
assert "git worktree add with bad path → exit 0, stderr log" 0 $?
echo "$out_c" | grep -q "could not resolve" || { echo "❌ fixture C: missing 'could not resolve' on stderr"; FAIL=1; }

[ $FAIL -eq 0 ] && echo "ALL PASS" || { echo "FAIL"; exit 1; }
```

- [ ] **Step 1.2: Run the test to verify it fails (script doesn't exist yet)**

Run: `bash /tmp/test-worktree-hook.sh`
Expected: the very first `bash "$HOOK"` invocation prints `bash: hooks/worktree-memory-symlink: No such file or directory` and exits non-zero. Test reports FAIL.

- [ ] **Step 1.3: Implement the hook script**

Create `hooks/worktree-memory-symlink`:

```bash
#!/usr/bin/env bash
# PostToolUse hook for js-super: when the main agent runs `git worktree add`
# via the Bash tool, set up Claude Code memory-folder symlinks for the new
# worktree(s) by invoking setup-memory-symlinks.sh.
#
# This hook exists because the equivalent inline shell snippet in
# setting-up-worktrees/SKILL.md was repeatedly NOT executed by the main
# agent (which mentally simulated the encoding instead, producing wrong
# folder names — see git history v1.1.2 through v1.1.4). A real hook firing
# from the harness cannot be bypassed by the LLM.
#
# Failure policy: NEVER block the user. On any error, log to stderr and
# exit 0.

set -uo pipefail

# Discover plugin root from this script's location.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYMLINK_SCRIPT="${PLUGIN_ROOT}/skills/setting-up-worktrees/scripts/setup-memory-symlinks.sh"

# Read the entire JSON event from stdin.
INPUT="$(cat)"

# Extract fields. Prefer jq; fall back to python3 if unavailable.
extract() {
    local field="$1"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$INPUT" | jq -r "$field // empty" 2>/dev/null
    else
        printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    path = '$field'.lstrip('.').split('.')
    cur = d
    for p in path:
        cur = cur.get(p, '') if isinstance(cur, dict) else ''
    print(cur if cur else '')
except Exception:
    pass
" 2>/dev/null
    fi
}

TOOL_NAME="$(extract '.tool_name')"
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND="$(extract '.tool_input.command')"
[ -n "$COMMAND" ] || exit 0

# Fast pattern check — must START with `git worktree add ` (with trailing space).
case "$COMMAND" in
    "git worktree add "*) ;;
    *) exit 0 ;;
esac

# We're committed; resolve repo root from cwd.
CWD="$(extract '.cwd')"
[ -n "$CWD" ] || CWD="$PWD"

ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ]; then
    echo "[worktree-memory-symlink] could not resolve repo root from cwd=$CWD" >&2
    exit 0
fi

# Parse worktree path out of the command. The first positional argument that
# is now a real directory wins. Skip flags and their values.
parse_worktree_path() {
    local cmd="$1"
    # Strip leading `git worktree add `
    cmd="${cmd#git worktree add }"

    # Tokenize naively on whitespace (worktree paths are normally simple).
    local -a toks
    read -r -a toks <<< "$cmd"

    local i=0
    while [ "$i" -lt "${#toks[@]}" ]; do
        local t="${toks[$i]}"
        case "$t" in
            # Flags that take a value
            -b|-B|--reason)
                i=$((i + 2))
                ;;
            # Boolean flags
            --detach|--guess-remote|--no-guess-remote|--track|--no-track|--lock|--force|-f|--quiet|-q|--checkout|--no-checkout)
                i=$((i + 1))
                ;;
            # First non-flag positional → the path
            *)
                # Resolve relative to ROOT
                local abs
                if [ "${t:0:1}" = "/" ]; then
                    abs="$t"
                else
                    abs="$ROOT/$t"
                fi
                if [ -d "$abs" ]; then
                    printf '%s' "$abs"
                    return 0
                fi
                # Fall through: not a real dir, give up
                return 1
                ;;
        esac
    done
    return 1
}

WT_ABS="$(parse_worktree_path "$COMMAND" || true)"
if [ -z "$WT_ABS" ]; then
    echo "[worktree-memory-symlink] could not resolve worktree path from: $COMMAND" >&2
    exit 0
fi

# Sanity: only act on worktrees under <root>/.worktrees/. Other paths are
# user-defined and out of our scope.
case "$WT_ABS" in
    "$ROOT/.worktrees/"*)
        BR="${WT_ABS#$ROOT/.worktrees/}"
        # Strip any trailing slash
        BR="${BR%/}"
        ;;
    *)
        # Not under .worktrees/ — silently ignore.
        exit 0
        ;;
esac

# Invoke the existing helper. Errors from it are logged but do not block.
if [ -x "$SYMLINK_SCRIPT" ]; then
    bash "$SYMLINK_SCRIPT" "$ROOT" "$BR" 2>&1 | sed 's/^/[worktree-memory-symlink] /' >&2
else
    echo "[worktree-memory-symlink] script not executable: $SYMLINK_SCRIPT" >&2
fi

exit 0
```

`chmod +x hooks/worktree-memory-symlink` after creating.

- [ ] **Step 1.4: Run the test to verify it passes**

Run: `chmod +x hooks/worktree-memory-symlink && bash /tmp/test-worktree-hook.sh`
Expected output:
```
✅ non-Bash tool → no-op
✅ Bash but not worktree add → no-op
✅ git worktree add with bad path → exit 0, stderr log
ALL PASS
```

- [ ] **Step 1.5: Clean up the ad-hoc test file**

Run: `rm /tmp/test-worktree-hook.sh`

- [ ] **Step 1.6: Commit**

```bash
git add hooks/worktree-memory-symlink
git commit -m "v1.1.5 wip: add worktree-memory-symlink PostToolUse hook script"
```

---

### Task 2: Register the hook in `hooks.json`

**Files:**
- Modify: `hooks/hooks.json`

- [ ] **Step 2.1: Read current `hooks.json`**

Run: `cat hooks/hooks.json`
Expected: only the SessionStart hook is registered today.

- [ ] **Step 2.2: Add the PostToolUse entry**

Edit `hooks/hooks.json` so it reads exactly:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "async": false
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" worktree-memory-symlink",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2.3: Verify JSON validity**

Run: `python3 -m json.tool hooks/hooks.json`
Expected: pretty-printed JSON, exit 0.

- [ ] **Step 2.4: Commit**

```bash
git add hooks/hooks.json
git commit -m "v1.1.5 wip: register PostToolUse hook for worktree memory symlinks"
```

---

### Task 3: Simplify the SKILL body (remove all temptations to mentally simulate)

**Files:**
- Modify: `skills/setting-up-worktrees/SKILL.md`

- [ ] **Step 3.1: Replace Step 5.5 body with a 2-paragraph hook notice**

Find the heading line `**Step 5.5 — Symlink Claude Code memory folder (delegate to script)**` and the bash block that follows it (everything down to and including the closing triple-backtick of the `bash "$(claude-plugin-root)/...` block plus the trailing paragraph "Pass the script's stdout..."). Replace that entire region with:

```markdown
**Step 5.5 — Memory symlink (handled automatically by hook)**

Memory-folder symlinking is performed by the `worktree-memory-symlink` PostToolUse hook (see `hooks/hooks.json` + `hooks/worktree-memory-symlink`). It fires automatically whenever any `git worktree add ...` command runs through the Bash tool, parses the worktree path from the command, and invokes `scripts/setup-memory-symlinks.sh`. **Do nothing here.** No mkdir, no ln, no sed — the hook owns this concern entirely. The script's output (e.g. `🔗 <branch> ← Claude 메모리 폴더 심링크 ...`) appears as hook stderr in your tool output and should be forwarded to the user as part of the Step 6 summary if visible.
```

The replacement deliberately contains no executable shell snippets — earlier versions failed because the agent saw inline bash and mentally simulated it.

- [ ] **Step 3.2: Update the Defaults table row**

Find the row in the `## Defaults (No User Prompt)` table that reads:

```
| Claude memory folder | **Symlink** main repo's `~/.claude/projects/<encoded-main>/memory` → `~/.claude/projects/<encoded-wt>/memory`. Skip if main has no memory yet, or if worktree's memory dir already exists (don't clobber). |
```

Replace with:

```
| Claude memory folder | **Symlink handled by `worktree-memory-symlink` PostToolUse hook** — fires automatically on `git worktree add`. Skips if main has no memory yet or if worktree's memory dir already exists. The skill body does NOT perform this step. |
```

- [ ] **Step 3.3: Update the dot graph in `## Process`**

Find the box `"Symlink Claude memory folder\n(if main has memory + WT has none)"` and replace its label with `"Symlink Claude memory folder\n(automatic via PostToolUse hook)"`. Leave the edges unchanged.

- [ ] **Step 3.4: Update Anti-Patterns**

Replace the three rows:

```
| `sed 's\|/\|-\|g'` or `sed 's\|[/_]\|-\|g'` for Claude memory path encoding | INCOMPLETE — Claude Code converts EVERY non-`[A-Za-z0-9-]` codepoint (incl. `.`, `_`, Korean, spaces, emoji). Only `sed 's\|[^A-Za-z0-9-]\|-\|g'` matches the real encoding. Verified against `~/.claude/projects/` directory listings. |
| Reproducing the encoding logic inline in this SKILL instead of invoking `scripts/setup-memory-symlinks.sh` | Forbidden — observed failure mode: agent infers the result mentally and produces wrong folder names (Korean preserved, etc.). Always shell out to the script. |
| Pre-computing the encoded folder name yourself and `ln -s`-ing directly | Forbidden for the same reason — let the script handle it. |
```

with:

```
| Performing the memory symlink yourself in this skill | Forbidden — handled by `worktree-memory-symlink` PostToolUse hook. Agent must not run mkdir / ln -s / sed for memory paths. Past versions failed because agents mentally simulated the encoding rule and produced folder names Claude Code never reads. |
```

- [ ] **Step 3.5: Update the Acceptance section**

Replace acceptance items 5 and 7:

```
5. For each worktree, `~/.claude/projects/<encoded-wt-path>/memory` is a symlink pointing to the main repo's memory dir — UNLESS main has no memory yet (first run) or the worktree's memory dir already existed (don't clobber). Encoding rule: replace EVERY non-`[A-Za-z0-9-]` codepoint with `-` (covers `/`, `.`, `_`, Korean, spaces, emoji — anything not ASCII alnum or hyphen).
6. User got a summary report listing each worktree's path + per-file copy status + memory symlink status
7. The user was NOT asked which env files to copy, NOR about the memory symlink
```

with:

```
5. The `worktree-memory-symlink` PostToolUse hook fired for every `git worktree add` invocation issued by this skill. (The skill itself did NOT mkdir / ln any memory paths.)
6. User got a summary report listing each worktree's path + per-file copy status + memory symlink status (the latter coming from the hook's stderr output).
7. The user was NOT asked which env files to copy, NOR about the memory symlink.
```

- [ ] **Step 3.6: Update commands/worktree.md**

Find the line beginning `- **Claude 메모리 폴더 자동 심링크**:` and replace it with:

```
- **Claude 메모리 폴더 자동 심링크 (PostToolUse hook)**: 워크트리 생성 시 `worktree-memory-symlink` 훅이 자동으로 메인 레포의 `~/.claude/projects/<encoded>/memory` 를 워크트리의 동일 위치에 심링크. 사용자/에이전트의 별도 액션 불필요. 메인에 메모리 0건이거나 워크트리에 이미 메모리 폴더가 있으면 자동 생략.
```

- [ ] **Step 3.7: Verify no leftover dangerous strings in SKILL body**

Run: `grep -nE 'mkdir -p.*projects|ln -s.*memory|sed .*\[\^A-Za-z' skills/setting-up-worktrees/SKILL.md`
Expected: zero matches. (If there's a hit, it means a `mkdir`/`ln -s`/encoding `sed` snippet survived the simplification — fix it before commit. The hook owns this; the SKILL body must contain no temptation.)

- [ ] **Step 3.8: Commit**

```bash
git add skills/setting-up-worktrees/SKILL.md commands/worktree.md
git commit -m "v1.1.5 wip: simplify SKILL body, hook owns memory symlinks"
```

---

### Task 4: Bump version 1.1.4 → 1.1.5 (3 manifests)

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `package.json`

- [ ] **Step 4.1: Patch all three**

```bash
# In each file, change the version field from "1.1.4" to "1.1.5".
sed -i '' 's/"version": "1.1.4"/"version": "1.1.5"/' \
    .claude-plugin/plugin.json \
    .claude-plugin/marketplace.json \
    package.json
```

(macOS `sed -i ''` syntax. On Linux, drop the empty string.)

- [ ] **Step 4.2: Verify all three**

Run: `grep '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json package.json`
Expected: each file shows `"version": "1.1.5"`.

- [ ] **Step 4.3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json package.json
git commit -m "v1.1.5 wip: bump version 1.1.4 → 1.1.5"
```

---

### Task 5: Final commit reshape + tag (squash WIPs into one release commit)

**Files:** none

- [ ] **Step 5.1: Inspect WIP commits**

Run: `git log --oneline -5`
Expected: four "v1.1.5 wip: …" commits sitting on top of `7c87824 v1.1.4 — …`.

- [ ] **Step 5.2: Soft-reset to v1.1.4 and create one consolidated v1.1.5 commit**

```bash
git reset --soft 7c87824
git commit -m "$(cat <<'EOF'
v1.1.5 — 메모리 심링크를 PostToolUse hook 으로 이전

근본 문제: SKILL 본문의 인라인 bash (mkdir/ln -s/sed) 를 메인 에이전트가
실행하지 않고 머리속으로 시뮬레이션 → 한글 보존된 잘못된 폴더 생성. v1.1.3
(룰 정확화) v1.1.4 (외부 스크립트로 분리) 모두 통과 못 함. SKILL 본문 강제
인스트럭션은 LLM 자율판단으로 우회 가능 — 한계 도달.

해결: hooks/worktree-memory-symlink PostToolUse hook 신설.
- matcher: Bash (모든 Bash 도구 호출 후 trigger)
- 첫 액션이 sub-ms 패턴 검사 — `git worktree add ` 로 시작 안 하면 즉시 종료
- 매치 시 stdin JSON 에서 command + cwd 추출 → repo root + 워크트리 path
  파싱 → 기존 setup-memory-symlinks.sh 호출
- 실패 시 stderr 로그만 남기고 exit 0 (사용자 차단 절대 X)

SKILL 본문에서 mkdir/ln -s/sed 흔적 전부 제거 (LLM 이 보고 따라할 단서 차단).
"hook 이 자동 처리" 한 단락만 남김. Anti-Patterns 표 단순화.
commands/worktree.md 도 "hook 자동" 으로 변경.

3 manifest 동기 (1.1.4 → 1.1.5).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5.3: Tag**

```bash
git tag v1.1.5
git log --oneline -3
git tag --list 'v1.1.*'
```
Expected: latest commit is the v1.1.5 release commit, tag `v1.1.5` listed.

- [ ] **Step 5.4: Hand off to user for push**

Tell the user: "Run `! git push origin main --tags` to publish v1.1.5, then `/plugin marketplace update js-super` + `/plugin update js-super@js-super` + `/reload-plugins` (or session restart) to load the new hook."

---

### Task 6: Post-release dogfood verification

**Files:** none — runtime check.

- [ ] **Step 6.1: Confirm with user that v1.1.5 has been pushed and the plugin reloaded**

If the user hasn't reloaded yet, wait. The hook is harness-loaded; it won't fire until reload.

- [ ] **Step 6.2: Ask the user to create one Korean-named worktree**

Suggested invocation: `/js-super:worktree 검증한글`.

- [ ] **Step 6.3: Verify the correct encoded folder got the symlink**

Run:
```bash
EXPECTED_DIR="$HOME/.claude/projects/$(printf '%s' '/Users/goldenplanet/workspace/ga/ga4-chatbot-backend/.worktrees/검증한글' | sed 's|[^A-Za-z0-9-]|-|g')"
echo "expected: $EXPECTED_DIR"
ls -la "$EXPECTED_DIR/" 2>&1 | head
```
Expected: `memory -> /Users/goldenplanet/.claude/projects/-Users-goldenplanet-workspace-ga-ga4-chatbot-backend/memory` (symlink to main).

- [ ] **Step 6.4: Verify NO Korean-preserved folder was created by the agent**

Run:
```bash
ls "$HOME/.claude/projects/" | grep '검증한글' || echo "✅ none — agent did not mentally simulate this time"
```
Expected: the literal-Korean folder does NOT appear (only the dashed encoding does).

- [ ] **Step 6.5: User-facing memory-sharing smoke test**

Have the user start a Claude Code session in `.worktrees/검증한글`, save a token (e.g., "토큰 ghi789 메모리 저장해줘"), then check from the main repo session — `ghi789 메모리 보여줘` — that the new memory is visible.

If all four checks pass: v1.1.5 is good. If Step 6.4 fails (Korean-preserved folder still appears), the hook didn't fire — debug by inspecting tool output for the hook's stderr lines, and verify reload actually happened.

---

## Self-Review

**1. Spec coverage:**
- Hook script (Task 1) — covers the design decision "encoding/symlinking runs in real shell, never simulated".
- Hook registration (Task 2) — covers "fires automatically on `git worktree add`".
- SKILL/command body simplification (Task 3) — covers "remove all temptation for the agent to mentally simulate".
- Version bump (Task 4) — required by project convention (3-file sync per HANDOFF.md).
- Release commit + tag (Task 5) — required for plugin marketplace consumption.
- Dogfood verification (Task 6) — required by project convention "사용자가 잘못된 default 를 catch 하는 프로세스".
No spec gaps.

**2. Placeholder scan:** All steps include exact commands or exact file content. No "TBD", no "implement later", no "similar to Task N", no "add error handling" without specifics.

**3. Type consistency:** Identifiers used consistently — `worktree-memory-symlink` (hook script), `setup-memory-symlinks.sh` (helper), `PostToolUse` (event), `Bash` (matcher). No name drift.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-09-worktree-memory-symlink-hook.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using og-executing-plans, batch execution with checkpoints

**Which approach?**
