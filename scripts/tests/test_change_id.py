from pathlib import Path
import tempfile
from datetime import date

from scripts.change_id import next_change_id


def test_first_id_when_no_history(tmp_path: Path):
    feature_dir = tmp_path
    (feature_dir / "요구사항.md").write_text("# 요구사항\n\n## 변경이력\n", encoding="utf-8")
    today = date(2026, 5, 2)
    assert next_change_id(feature_dir, today) == "CH-20260502-001"


def test_increment_within_same_day(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "# 요구사항\n\n## 변경이력\n\n### [2026-05-02 10:00] [요구사항-수정]\n- **id**: CH-20260502-001\n",
        encoding="utf-8",
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-002"


def test_reset_for_new_day(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "## 변경이력\n\n### [2026-05-01 10:00] [요구사항-수정]\n- **id**: CH-20260501-007\n",
        encoding="utf-8",
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-001"


def test_scans_all_md_files(tmp_path: Path):
    (tmp_path / "요구사항.md").write_text(
        "## 변경이력\n### [2026-05-02 10:00]\n- **id**: CH-20260502-001\n", encoding="utf-8"
    )
    (tmp_path / "구현계획서.md").write_text(
        "## 변경이력\n### [2026-05-02 11:00]\n- **id**: CH-20260502-005\n", encoding="utf-8"
    )
    assert next_change_id(tmp_path, date(2026, 5, 2)) == "CH-20260502-006"
