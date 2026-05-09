"""Subagent changelog buffer helpers (v1.1.7).

Implementer subagents write Changes Manifest as YAML frontmatter to
.js-super/changelog-buffer/<slug>/task-NN.md. The main agent reads
these at end-of-run to consolidate into a single 변경이력 entry.
"""
from pathlib import Path

import yaml


def write_manifest(target: Path, manifest: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True)
    target.write_text(f"---\n{body}---\n", encoding="utf-8")


def read_manifest(target: Path) -> dict:
    text = target.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter: {target}")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"malformed manifest: {target}")
    return yaml.safe_load(parts[1])


def list_buffer_files(buffer_dir: Path) -> list[Path]:
    """Return task-*.md files sorted by numeric task id."""
    if not buffer_dir.exists():
        return []
    files = list(buffer_dir.glob("task-*.md"))
    return sorted(files, key=lambda p: int(p.stem.split("-")[1]))


def detect_stale_buffer(root: Path, slug: str) -> Path | None:
    """Return the slug subdir under root if it exists with manifests, else None."""
    candidate = root / slug
    if not candidate.exists():
        return None
    if not list_buffer_files(candidate):
        return None
    return candidate
