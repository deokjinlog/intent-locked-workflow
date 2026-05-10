"""Helpers for auto-flow skills (v1.1.17+).

- parse_interrupt: detect user interrupt keyword (stop / 멈춰 / etc.) in transition turns.
- find_latest_slug: infer the latest <slug> from docs/features/ when slash command arg is omitted.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_INTERRUPT_PATTERNS = [
    r"\bstop\b",
    r"\babort\b",
    r"멈춰",
    r"잠깐",
    r"잠시만",
    r"중단",
    r"취소",
]
_INTERRUPT_RE = re.compile("|".join(_INTERRUPT_PATTERNS), re.IGNORECASE)

_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-(?P<slug>.+)$")


def parse_interrupt(text: str) -> bool:
    """Return True if `text` contains an interrupt keyword."""
    return bool(_INTERRUPT_RE.search(text))


def find_latest_slug(features_dir: Path) -> Optional[str]:
    """Return the slug of the most recently modified feature folder, or None."""
    if not features_dir.exists():
        return None
    candidates = []
    for child in features_dir.iterdir():
        if not child.is_dir():
            continue
        m = _FOLDER_RE.match(child.name)
        if not m:
            continue
        candidates.append((child.stat().st_mtime, m.group("slug")))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]
