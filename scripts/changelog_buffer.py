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
