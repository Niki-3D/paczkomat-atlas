"""Load GUS BDL population data into population_gmina.

Strategy: PRG-side-driven matching. PRG is the source of truth for which
gminy exist and what their TERYT is. For each PRG gmina, we look up a
BDL unit by (voj, normalized_name, rodzaj-mapped-kind) and pull its
population values.

Driving from PRG (not BDL) eliminates the noise from BDL's redundant
records for newly-converted gminas. Example: Książ Wielki is rural-only
in our 2022 PRG snapshot (rodzaj=2) but BDL classifies it as miasto-
wiejska (kind=3, 4, 5 + a legacy kind=2). PRG-side matching simply
picks the kind=2 entry that PRG expects.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from sqlalchemy import text

from paczkomat_atlas_api.db import SessionLocal
from paczkomat_atlas_api.logging import get_logger

log = get_logger("ingest.bdl")

BDL_DATA_FILE = Path("data/raw/gus/population_gmina_2024.json")
BDL_UNITS_FILE = Path("data/raw/gus/units_gmina.json")

# Polish letters that NFKD doesn't decompose (atomic codepoints) — map
# explicitly before normalization so e.g. 'słupsk' becomes 'slupsk', not 'supsk'.
_PL_DIACRITIC_MAP = str.maketrans({
    "ł": "l", "Ł": "l",
    "ą": "a", "Ą": "a",
    "ć": "c", "Ć": "c",
    "ę": "e", "Ę": "e",
    "ń": "n", "Ń": "n",
    "ó": "o", "Ó": "o",
    "ś": "s", "Ś": "s",
    "ź": "z", "Ź": "z",
    "ż": "z", "Ż": "z",
})

# PRG rodzaj → preferred BDL kind chain (first match wins).
# For converted gminas (e.g. rural in PRG, mixed in BDL), the fallback
# keeps coverage high without misclassifying.
RODZAJ_TO_KIND_CHAIN: dict[int, tuple[str, ...]] = {
    1: ("1", "4"),   # gmina miejska → try kind=1, fall back to kind=4 (miasto of mixed)
    2: ("2", "5"),   # gmina wiejska → try kind=2, fall back to kind=5 (obszar wiejski)
    3: ("3",),       # gmina miejsko-wiejska aggregate
    4: ("4", "1"),   # miasto in mixed → try kind=4, fall back to kind=1
    5: ("5", "2"),   # obszar wiejski in mixed → try kind=5, fall back to kind=2
}


def normalize_name(name: str) -> str:
    """Normalize gmina name for matching: strip diacritics, lower, trim,
    drop trailing ' - miasto' / ' - obszar wiejski' qualifiers that BDL
    appends on kind=4/kind=5 entries."""
    if not name:
        return ""
    name = name.replace("gmina ", "").replace("Gmina ", "").strip()
    # BDL appends "- miasto" / "- obszar wiejski" — strip for name-only match
    for suffix in (" - miasto", " - obszar wiejski"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    # BDL prefixes Warsaw with "M.st." (miasto stołeczne) and appends
    # version suffixes like " od 2002" / " do 2001" when admin geometry changes.
    if name.startswith("M.st."):
        name = name[len("M.st."):].lstrip(".").strip()
    for marker in (" do 20", " do 19", " od 20", " od 19"):
        idx = name.find(marker)
        if idx > 0:
            name = name[:idx].strip()
            break
    name = name.translate(_PL_DIACRITIC_MAP)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_form = nfkd.encode("ASCII", "ignore").decode("ASCII")
    return ascii_form.lower().strip()


def voivodeship_code_from_bdl_id(bdl_id: str) -> str | None:
    """BDL ID encodes voivodeship in chars 3-4 (0-indexed: positions 2-3)."""
    return bdl_id[2:4] if len(bdl_id) >= 4 else None


def build_bdl_unit_index(units: list[dict]) -> dict[tuple[str, str, str], str]:
    """Build (voj, normalized_name, kind) -> bdl_id index from BDL units."""
    index: dict[tuple[str, str, str], str] = {}
    for u in units:
        bdl_id = u.get("id")
        if not bdl_id:
            continue
        voj = voivodeship_code_from_bdl_id(bdl_id)
        name = normalize_name(u.get("name", ""))
        kind = str(u.get("kind", ""))
        if not voj or not name or not kind:
            continue
        index[(voj, name, kind)] = bdl_id
    return index


async def fetch_prg_gminy() -> list[tuple[str, str, str, int]]:
    """Return list of (teryt, voj_code, normalized_name, rodzaj) per PRG gmina."""
    sql = text("SELECT teryt, name FROM gminy")
    async with SessionLocal() as session:
        result = await session.execute(sql)
        rows = result.all()

    out: list[tuple[str, str, str, int]] = []
    for teryt, name in rows:
        out.append((teryt, teryt[:2], normalize_name(name), int(teryt[6])))
    return out


async def load_population_gmina() -> dict[str, float | int]:
    """Load GUS BDL gmina population by PRG-driven name+rodzaj matching."""
    if not BDL_DATA_FILE.exists():
        raise FileNotFoundError(f"BDL data not found at {BDL_DATA_FILE}.")
    if not BDL_UNITS_FILE.exists():
        raise FileNotFoundError(f"BDL units not found at {BDL_UNITS_FILE}.")

    with BDL_UNITS_FILE.open(encoding="utf-8") as f:
        units = json.load(f)

    bdl_index = build_bdl_unit_index(units)
    log.info("bdl.index_built", entries=len(bdl_index))

    # Population values per BDL id
    with BDL_DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    pop_by_bdl_id: dict[str, list[dict]] = {
        e["id"]: e.get("values", []) for e in data if e.get("id")
    }

    prg_gminy = await fetch_prg_gminy()
    log.info("bdl.prg_loaded", count=len(prg_gminy))

    rows: list[dict] = []
    matched = 0
    unmatched_examples: list[dict] = []

    for teryt, voj, name_norm, rodzaj in prg_gminy:
        kind_chain = RODZAJ_TO_KIND_CHAIN.get(rodzaj, ())
        found_bdl_id: str | None = None
        for kind in kind_chain:
            key = (voj, name_norm, kind)
            if key in bdl_index:
                found_bdl_id = bdl_index[key]
                break
        if not found_bdl_id:
            # Name-only fallback: ignore rodzaj/kind, accept if (voj, name) is unique
            # in BDL. Handles miasta na prawach powiatu and other classification
            # mismatches between PRG and BDL.
            candidates = [
                bid for (v, n, _k), bid in bdl_index.items()
                if v == voj and n == name_norm
            ]
            if len(set(candidates)) == 1:
                found_bdl_id = candidates[0]
                log.info("bdl.matched_name_only", teryt=teryt, name=name_norm, voj=voj)
        if not found_bdl_id:
            if len(unmatched_examples) < 10:
                unmatched_examples.append(
                    {"teryt": teryt, "voj": voj, "name": name_norm, "rodzaj": rodzaj}
                )
            continue

        matched += 1
        for v in pop_by_bdl_id.get(found_bdl_id, []):
            year = int(v.get("year", 0))
            val = v.get("val")
            if val is None or year == 0:
                continue
            rows.append({"teryt": teryt, "year": year, "value": int(val)})

    match_rate = matched / len(prg_gminy) if prg_gminy else 0
    log.info(
        "bdl.match_summary",
        matched=matched, total=len(prg_gminy), match_rate=f"{match_rate:.1%}",
    )

    if unmatched_examples:
        log.warning("bdl.unmatched_examples", examples=unmatched_examples)

    if match_rate < 0.95:
        raise RuntimeError(
            f"BDL→PRG match rate {match_rate:.1%} below 95% threshold. "
            f"Sample unmatched: {unmatched_examples[:3]}"
        )

    if not rows:
        return {"loaded": 0, "matched": matched, "match_rate": 0}

    sql = text("""
        INSERT INTO population_gmina (teryt, year, value)
        VALUES (:teryt, :year, :value)
        ON CONFLICT (teryt, year) DO UPDATE SET value = EXCLUDED.value
    """)
    async with SessionLocal() as session:
        for i in range(0, len(rows), 500):
            await session.execute(sql, rows[i:i + 500])
        await session.commit()

    log.info("bdl.loaded", rows=len(rows), matched=matched, match_rate=match_rate)
    return {"loaded": len(rows), "matched": matched, "match_rate": match_rate}
