#!/usr/bin/env bash
# Symlink the main repo's Claude Code memory dir into each worktree's
# encoded project dir under ~/.claude/projects/.
#
# This script exists because Claude Code main agents have been observed to
# "mentally simulate" inline shell snippets in SKILL.md instead of executing
# them — leading to wrong path encodings (e.g. preserving Korean codepoints
# instead of replacing them). Invoking a real .sh file removes that escape
# hatch: the main agent can only call this script, not rewrite its logic.
#
# Usage: setup-memory-symlinks.sh <repo-root-abs> <branch1> [<branch2> ...]
# Exits 0 on success (including all-skip cases). Exits non-zero only on
# argument errors. Per-branch issues are reported but do not abort the run.

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "usage: $0 <repo-root-abs> <branch1> [<branch2> ...]" >&2
    exit 2
fi

ROOT="$1"
shift
BRANCHES=("$@")

# Claude Code's actual encoding: every codepoint outside [A-Za-z0-9-]
# becomes '-'. Verified empirically against ~/.claude/projects/ entries
# (Korean ticket names produce N dashes per N Korean chars).
encode_claude_path() {
    printf '%s' "$1" | sed 's|[^A-Za-z0-9-]|-|g'
}

MAIN_ENC="$(encode_claude_path "$ROOT")"
MAIN_MEMORY="$HOME/.claude/projects/${MAIN_ENC}/memory"

if [ ! -d "$MAIN_MEMORY" ]; then
    echo "ℹ️  메인 레포에 Claude 메모리 폴더 없음 ($MAIN_MEMORY) — 모든 워크트리 심링크 생략"
    exit 0
fi

for BR in "${BRANCHES[@]}"; do
    WT_PATH="$ROOT/.worktrees/$BR"

    if [ ! -d "$WT_PATH" ]; then
        echo "⏭️  $BR — 워크트리 디렉터리 없음 ($WT_PATH), skip"
        continue
    fi

    WT_ENC="$(encode_claude_path "$WT_PATH")"
    WT_PROJECT_DIR="$HOME/.claude/projects/${WT_ENC}"
    WT_MEMORY="${WT_PROJECT_DIR}/memory"

    if [ -e "$WT_MEMORY" ] || [ -L "$WT_MEMORY" ]; then
        echo "⏭️  $BR — 워크트리 메모리 폴더 이미 존재 ($WT_MEMORY), skip (수동 마이그레이션 필요 시 직접)"
        continue
    fi

    mkdir -p "$WT_PROJECT_DIR"
    ln -s "$MAIN_MEMORY" "$WT_MEMORY"
    echo "🔗 $BR ← Claude 메모리 폴더 심링크 ($WT_PROJECT_DIR)"
done
