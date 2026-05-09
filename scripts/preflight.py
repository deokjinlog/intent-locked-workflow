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
