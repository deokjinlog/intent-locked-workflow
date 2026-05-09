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
