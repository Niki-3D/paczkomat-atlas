"""Paginate GUS BDL variable 72305 and write a combined JSON.

Stand-alone helper invoked by scripts/download_static_data.sh.
Avoids a jq dependency so the download flow works on Windows without
extra tooling. Idempotent: re-running over an existing combined file
is a no-op (the bash caller decides whether to call us).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

VARIABLE = 72305
YEAR = 2024
PAGE_SIZE = 100
SLEEP_BETWEEN_PAGES = 1.0  # be polite

URL_TMPL = (
    "https://bdl.stat.gov.pl/api/v1/data/by-variable/{var}"
    "?format=json&year={year}&page-size={ps}&page={page}"
)


def fetch_page(page: int) -> dict[str, Any]:
    url = URL_TMPL.format(var=VARIABLE, year=YEAR, ps=PAGE_SIZE, page=page)
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
    print(f"GUS BDL: {len(combined)} records written to {out_path}", flush=True)


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/gus/population_gmina_2024.json")
    main(target)
