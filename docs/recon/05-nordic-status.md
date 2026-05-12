# Nordic Status Mystery — SE, DK, FI

**Date:** 2026-05-12
**Trigger:** Phase 3 full EU ingest. `mv_country_kpi` reported 0 lockers and 0 PUDOs for SE/DK/FI despite raw counts of 4,454 / 2,375 / 2,375 records respectively. Investigation explains the discrepancy.

---

## 1. Status distribution

| Country | Status | Count |
|---|---|---:|
| DK | Disabled | 2,375 |
| FI | Disabled | 2,375 |
| SE | Disabled | 4,454 |

100% of records in all three countries are `Disabled` — none `Operating`, `Created`, or `Overloaded`. That's why `mv_country_kpi` (which filters to `Operating + Overloaded`) shows zero across the board.

## 2. Hypothesis: decommissioned Mondial Relay legacy catalog

Sampling three records from each Nordic country surfaces an identical profile:

```
country | name    | status   | partner_id | mondial_relay_id | agency | physical_type
SE      | SE000001| Disabled |    99      |     00001        |  6680  |  (null)
DK      | DK000006| Disabled |    99      |     00006        |  6670  |  (null)
FI      | FI010278| Disabled |    99      |     10278        |  6690  |  (null)
```

Every Nordic record has:
- `partner_id = 99` (= Mondial Relay, same code as French PUDOs)
- A populated `mondial_relay_id`
- A country-specific `agency` code (6670/6680/6690 — DK/SE/FI)
- No `physical_type` (= not an InPost machine)
- A synthetic naming pattern (`<CC><NNNNNN>`)

Cross-checking against active Mondial Relay markets:

| Country | Total | Operating Mondial Relay | Disabled Mondial Relay | Operating non-Mondial-Relay |
|---|---:|---:|---:|---:|
| FR | 26,577 | 7,164 | 7,253 | 10,418 |
| ES | 14,700 | 6,695 | 3,415 | 4,259 |
| BE | 1,796 | 876 | 336 | 512 |
| NL | 1,450 | 977 | 402 | 27 |
| PT | 3,191 | 1,833 | 838 | 488 |
| **SE** | 4,454 | **0** | 4,454 | 0 |
| **DK** | 2,375 | **0** | 2,375 | 0 |
| **FI** | 2,375 | **0** | 2,375 | 0 |

In every "real" Mondial Relay market, there are both Operating and Disabled records — a normal mix of active points plus closed ones over time. The Nordics show ONLY Disabled — the entire footprint is dormant.

InPost acquired Mondial Relay in 2021. The Nordic Mondial Relay network appears to have been wound down (or never connected to the live status feed). The 9,204 Nordic records are stale catalog entries: real coordinates, real shop addresses, but inactive.

This is **not pre-launch** (those would be `Created`). It is **post-decommissioning** noise from the acquisition.

## 3. Sample raw record (DK, anonymized)

```
{
  "name": "DK000006",
  "country": "DK",
  "status": "Disabled",
  "type": ["pok", "pop"],
  "partner_id": 99,
  "mondial_relay_id": "00006",
  "agency": "6670",
  "location_category": "Generic",
  "location_247": false,
  "physical_type": null,
  "location": {"latitude": 5x.xxxx, "longitude": 1x.xxxx},
  "address_details": {"city": "...", "province": null, "post_code": "..."}
}
```

The shape is identical to a French Mondial Relay PUDO except `status` is `Disabled` instead of `Operating`.

## 4. Implications for dashboard

- **The current `mv_country_kpi` filter is correct.** Filtering to `status IN ('Operating', 'Overloaded')` correctly excludes these decommissioned records. Nordics legitimately have 0 operational reach.
- **The dashboard needs a contextual note** for DK/SE/FI. "0 lockers, 0 PUDOs" without explanation looks like a data bug. Suggested treatment:
  - **Country card UI**: show `0 active / 9,204 decommissioned legacy (Mondial Relay)` with a tooltip explaining the acquisition history.
  - **Map**: do not render Nordic Disabled points on choropleth or hex layers (they're noise).
  - **Country selector**: keep Nordics in the list — the analytical story ("InPost holds Mondial Relay catalog but no live network in DK/SE/FI") is interesting in itself.
- **Do NOT widen the status filter** to include `Disabled` in dashboard MVs. Doing so would dilute every other country's headline numbers with inactive points and reverse the recommendation.

## 5. Recommendation

Add a `legacy_pudo` boolean column (or equivalent flag in `mv_country_kpi`) so the API can surface a single "decommissioned" count per country without re-deriving the partner_id+status pattern at query time. Defer to Phase 5 (API layer) — schema stays as-is for now.

## 6. New `physical_type` values discovered in PL ingest

Tangential finding from the same investigation (Phase 3 PL data):

- `legacy` — 33 rows in PL. Recon (Phase 0) called this GB-only.
- `bankopaczkomaty` — 30 rows in PL, brand-new value. Almost certainly the PKO BP banking-partner branded lockers (literally "bank lockers"). Treat as a normal locker variant.

Rule update applied alongside the Nordic note.
