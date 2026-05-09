"""Unit tests for scripts.preflight (v1.1.14)."""
from pathlib import Path

from scripts.preflight import (
    code_pretty_check,
    docs_pretty_check,
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
