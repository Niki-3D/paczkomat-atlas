"""Fetch GUS BDL gmina-level units (level=6) for BDL_ID → TERYT mapping.

Stand-alone helper invoked by scripts/download_static_data.sh.
Mirrors download_bdl.py — stdlib only, idempotent, polite delays.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

LEVEL = 6  # gmina
PAGE_SIZE = 100
SLEEP_BETWEEN_PAGES = 1.0

URL_TMPL = (
    "https://bdl.stat.gov.pl/api/v1/units"
    "?level={level}&format=json&page-size={ps}&page={page}"
)


def fetch_page(page: int) -> dict[str, Any]:
    url = URL_TMPL.format(level=LEVEL, ps=PAGE_SIZE, page=page)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def main(out_path: Path) -> None:
    combined: list[dict[str, Any]] = []
    page = 0
    while True:
        body = fetch_page(page)
        results = body.get("results", [])
        combined.extend(results)
        total = body.get("totalRecords", 0)
        print(f"  page {page}: +{len(results)} (running {len(combined)} / {total})", flush=True)
        if "next" not in body.get("links", {}):
            break
        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(combined, ensure_ascii=False), encoding="utf-8")
    print(f"BDL units (level={LEVEL}): {len(combined)} written to {out_path}", flush=True)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/gus/units_gmina.json")
    main(target)
