from pathlib import Path

import pytest

from scripts.changelog_buffer import (
    write_manifest,
    read_manifest,
    list_buffer_files,
    detect_stale_buffer,
)


def _write(p: Path, manifest: dict):
    write_manifest(p, manifest)


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
