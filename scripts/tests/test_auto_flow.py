import pytest
from pathlib import Path
from scripts.auto_flow import parse_interrupt, find_latest_slug


@pytest.mark.parametrize("text,expected", [
    ("stop", True),
    ("멈춰", True),
    ("잠깐", True),
    ("중단", True),
    ("abort", True),
    ("취소", True),
    ("어 잠시만", True),
    ("Stop please", True),
    ("계속 진행", False),
    ("OK 좋아요", False),
    ("그래 다음 단계로", False),
])
def test_parse_interrupt(text, expected):
    assert parse_interrupt(text) is expected


def test_find_latest_slug_picks_most_recent_mtime(tmp_path):
    older = tmp_path / "2026-05-01-old"
    older.mkdir()
    newer = tmp_path / "2026-05-10-new"
    newer.mkdir()
    import os, time
    time.sleep(0.01)
    os.utime(newer, None)
    assert find_latest_slug(tmp_path) == "new"


def test_find_latest_slug_returns_none_when_empty(tmp_path):
    assert find_latest_slug(tmp_path) is None


def test_find_latest_slug_skips_non_dirs(tmp_path):
    (tmp_path / "2026-05-01-real").mkdir()
    (tmp_path / "stray.md").write_text("noise")
    assert find_latest_slug(tmp_path) == "real"
