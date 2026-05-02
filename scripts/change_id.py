"""Generate next CH-id (CH-YYYYMMDD-NNN) by scanning feature folder MDs."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

CH_PATTERN = re.compile(r"CH-(\d{8})-(\d{3})")


def next_change_id(feature_dir: Path, today: date) -> str:
    today_str = today.strftime("%Y%m%d")
    max_seq = 0
    for md_file in feature_dir.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for match in CH_PATTERN.finditer(text):
            day, seq = match.group(1), int(match.group(2))
            if day == today_str:
                max_seq = max(max_seq, seq)
    return f"CH-{today_str}-{max_seq + 1:03d}"


if __name__ == "__main__":
    import sys
    from datetime import date as _date

    if len(sys.argv) != 2:
        print("usage: python -m scripts.change_id <feature-dir>", file=sys.stderr)
        sys.exit(2)
    print(next_change_id(Path(sys.argv[1]), _date.today()))
