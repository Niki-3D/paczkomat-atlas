"""Audit the 500-sample for field nullability, distributions, coordinate bounds."""
import json, re
from collections import Counter, defaultdict

d = json.load(open("recon/samples/sample_500.json", encoding="utf-8"))
items = d["items"]
N = len(items)
print(f"=== AUDIT N={N} (country=PL) ===\n")

# field presence / null counts
present = defaultdict(int)
nullc = defaultdict(int)
type_seen = defaultdict(set)
for it in items:
    for k, v in it.items():
        present[k] += 1
        if v is None or v == [] or v == {} or v == "":
            nullc[k] += 1
        type_seen[k].add(type(v).__name__)

print("--- field presence / null rates ---")
for k in sorted(present.keys()):
    pres = present[k]; nl = nullc[k]
    types = "/".join(sorted(type_seen[k]))
    print(f"  {k:42s} present={pres}/{N}  null/empty={nl}  types={types}")

# distributions
def dist(field, top=None):
    vs = [it.get(field) for it in items]
    c = Counter(vs)
    res = c.most_common(top) if top else c.most_common()
    print(f"\n--- {field} ---")
    for v, n in res:
        print(f"  {v!r:50s} {n} ({100*n/N:.1f}%)")
    return c

dist("country")
dist("status")
dist("physical_type")
dist("physical_type_mapped")
dist("location_type")
dist("location_category")
dist("payment_available")
dist("easy_access_zone")
dist("location_247")
dist("air_index_level")
dist("opening_hours", top=10)
dist("agency", top=10)
tc2 = Counter(tuple(it.get("type") or []) for it in items)
print("\n--- type (tuple) ---")
for v, n in tc2.most_common():
    print(f"  {v!r:50s} {n}")

# functions multi-value
fc = Counter()
for it in items:
    for f in it.get("functions") or []:
        fc[f] += 1
print("\n--- functions (multi-value) ---")
for v, n in fc.most_common():
    print(f"  {v:48s} {n} ({100*n/N:.1f}%)")

# supported_locker_temperatures
tc = Counter()
for it in items:
    v = it.get("supported_locker_temperatures")
    if v is None:
        tc["__None__"] += 1
    elif isinstance(v, list):
        for x in v: tc[x] += 1
    else:
        tc[str(v)] += 1
print("\n--- supported_locker_temperatures ---")
for v, n in tc.most_common():
    print(f"  {v}: {n}")

# coordinate bounds
lats = [it["location"]["latitude"] for it in items if it.get("location")]
lons = [it["location"]["longitude"] for it in items if it.get("location")]
print(f"\n--- coord bounds (PL) ---")
print(f"  lat min={min(lats):.4f} max={max(lats):.4f}")
print(f"  lon min={min(lons):.4f} max={max(lons):.4f}")
# PL bbox roughly: lat 49-54.9, lon 14-24.2
out_of_bbox = [(it["name"], it["location"]) for it in items
               if not (49.0 <= it["location"]["latitude"] <= 54.9 and 14.0 <= it["location"]["longitude"] <= 24.2)]
print(f"  outside PL bbox: {len(out_of_bbox)}")
for n, loc in out_of_bbox[:5]: print(f"    {n}: {loc}")

# naming prefix
print("\n--- naming prefix -> cities ---")
prefix_city = defaultdict(Counter)
for it in items:
    m = re.match(r"^([A-Z]{2,4})", it["name"])
    if m:
        pfx = m.group(1)
        city = it.get("address_details", {}).get("city", "?")
        prefix_city[pfx][city] += 1
# print top 20 prefixes
top_prefixes = sorted(prefix_city.items(), key=lambda x: -sum(x[1].values()))[:25]
for pfx, ccount in top_prefixes:
    top_city = ccount.most_common(1)[0]
    total = sum(ccount.values())
    print(f"  {pfx}: total {total}, top city: {top_city[0]} ({top_city[1]})")

# locker_availability shape
print("\n--- locker_availability examples ---")
la_status = Counter()
la_shapes = set()
for it in items:
    la = it.get("locker_availability") or {}
    la_status[la.get("status")] += 1
    la_shapes.add(json.dumps(sorted((la.get("details") or {}).keys())))
for s, n in la_status.most_common():
    print(f"  status={s}: {n}")
print(f"  detail key shapes: {la_shapes}")

# opening_hours shape
oh_unique = set()
for it in items:
    oh = it.get("opening_hours")
    if isinstance(oh, str):
        oh_unique.add(oh)
    else:
        oh_unique.add(type(oh).__name__)
print(f"\n--- opening_hours: {len(oh_unique)} unique. samples: {list(oh_unique)[:6]}")

# operating_hours_extended
ohe = Counter()
for it in items:
    v = it.get("operating_hours_extended")
    if v is None:
        ohe["None"] += 1
    elif isinstance(v, dict) and v.get("customer") is None:
        ohe["{customer:null}"] += 1
    else:
        ohe[str(v)[:60]] += 1
print(f"\n--- operating_hours_extended dist ---")
for v,n in ohe.most_common(10):
    print(f"  {v}: {n}")

# address normalization — city variants
city_variants = Counter()
for it in items:
    c1 = (it.get("address_details") or {}).get("city")
    city_variants[c1] += 1
print(f"\n--- unique cities in sample: {len(city_variants)}")
# show ones with suspect casing/whitespace
sus = [c for c in city_variants if c and (c != c.strip() or c.lower() != c.lower())]

# province dist
prov = Counter((it.get("address_details") or {}).get("province") for it in items)
print(f"\n--- province dist ---")
for p, n in prov.most_common():
    print(f"  {p}: {n}")
