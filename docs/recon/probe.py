"""InPost API recon. Read-only. 1s sleep between requests. Stop on 429."""
import json, time, sys, urllib.parse, urllib.request, urllib.error, os, pathlib

BASE = "https://api-global-points.easypack24.net/v1/points"
OUT = pathlib.Path("recon/samples")
OUT.mkdir(parents=True, exist_ok=True)

SESSION_LOG = []

def fetch(url, save_as=None, save_headers=False):
    """GET url, return (status, headers, body_text). Save JSON if save_as given."""
    req = urllib.request.Request(url, headers={"User-Agent": "recon/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
            hdrs = dict(r.headers.items())
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        hdrs = dict(e.headers.items()) if e.headers else {}
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
    except Exception as e:
        status = -1
        hdrs = {}
        body = f"EXC: {e}"

    if save_as:
        path = OUT / save_as
        try:
            obj = json.loads(body)
            path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            path.write_text(body, encoding="utf-8")
        if save_headers:
            (OUT / (save_as.rsplit(".",1)[0] + ".headers.txt")).write_text(
                "\n".join(f"{k}: {v}" for k,v in hdrs.items()), encoding="utf-8")

    SESSION_LOG.append({"url": url, "status": status, "size": len(body)})
    print(f"[{status}] {url[:120]} -> {len(body)}B  save={save_as}", flush=True)
    if status == 429:
        print("!!! 429 — STOPPING", flush=True)
        sys.exit(2)
    return status, hdrs, body

def js(body):
    try: return json.loads(body)
    except: return None

def sleep():
    time.sleep(1.0)

def main(stage):
    if stage in ("all","pagination"):
        print("\n=== PAGINATION & SCALE ===")
        # try per_page ceiling
        for pp in [25, 100, 500, 1000, 5000]:
            url = f"{BASE}?per_page={pp}&page=1"
            st, h, b = fetch(url, save_as=f"per_page_{pp}.json", save_headers=True)
            d = js(b)
            if d and "items" in d:
                print(f"  per_page={pp} -> got {len(d['items'])} items, total_pages={d.get('total_pages')}, count={d.get('count')}")
            elif d:
                print(f"  per_page={pp} -> body keys: {list(d.keys())}")
            sleep()

        # headers detail — etag/lastmod/cache?
        print("\n--- header inspection (per_page=1) ---")
        st, h, b = fetch(f"{BASE}?per_page=1", save_headers=True, save_as="headers_probe.json")
        for k in ["ETag","Last-Modified","Cache-Control","X-RateLimit-Limit","X-RateLimit-Remaining","Age","Expires"]:
            print(f"  {k}: {h.get(k)}")
        sleep()

    if stage in ("all","filters"):
        print("\n=== FILTERS ===")
        tests = [
            ("country_PL", "country=PL&per_page=1"),
            ("country_DE", "country=DE&per_page=1"),
            ("country_IT", "country=IT&per_page=1"),
            ("country_UK", "country=UK&per_page=1"),
            ("country_GB", "country=GB&per_page=1"),
            ("country_FR", "country=FR&per_page=1"),
            ("country_ES", "country=ES&per_page=1"),
            ("country_PT", "country=PT&per_page=1"),
            ("country_NL", "country=NL&per_page=1"),
            ("country_BE", "country=BE&per_page=1"),
            ("country_RO", "country=RO&per_page=1"),
            ("country_HU", "country=HU&per_page=1"),
            ("country_CZ", "country=CZ&per_page=1"),
            ("country_SK", "country=SK&per_page=1"),
            ("country_LT", "country=LT&per_page=1"),
            ("country_LV", "country=LV&per_page=1"),
            ("country_EE", "country=EE&per_page=1"),
            ("country_US", "country=US&per_page=1"),
            ("status_Operating", "status=Operating&per_page=1&country=PL"),
            ("status_Disabled", "status=Disabled&per_page=1&country=PL"),
            ("status_Created", "status=Created&per_page=1&country=PL"),
            ("status_NonOperating", "status=NonOperating&per_page=1&country=PL"),
            ("type_parcel_locker", "type=parcel_locker&per_page=1&country=PL"),
            ("type_pop", "type=pop&per_page=1&country=PL"),
            ("type_parcel_point", "type=parcel_point&per_page=1&country=PL"),
            ("type_pudo", "type=pudo&per_page=1&country=PL"),
            ("functions_parcel_collect", "functions=parcel_collect&per_page=1&country=PL"),
            ("functions_parcel_send", "functions=parcel_send&per_page=1&country=PL"),
            ("physical_type_newfm", "physical_type=newfm&per_page=1&country=PL"),
            ("physical_type_modular", "physical_type=modular&per_page=1&country=PL"),
            ("physical_type_screenless", "physical_type=screenless&per_page=1&country=PL"),
            ("physical_type_next", "physical_type=next&per_page=1&country=PL"),
            ("physical_type_indoor", "physical_type=indoor&per_page=1&country=PL"),
            ("physical_type_easyplus", "physical_type=easyplus&per_page=1&country=PL"),
            ("geo_warsaw", "relative_post_code=00-001&max_distance=5000&per_page=5"),
            ("city_warszawa", "city=Warszawa&per_page=1"),
            ("city_warszawa_lower", "city=warszawa&per_page=1"),
            ("city_warsaw", "city=Warsaw&per_page=1"),
            ("city_krakow_unicode", "city="+urllib.parse.quote("Kraków")+"&per_page=1"),
            ("city_krakow_ascii", "city=Krakow&per_page=1"),
            ("updated_after", "updated_after=2026-01-01&per_page=1"),
            ("updated_since", "updated_since=2026-01-01&per_page=1"),
            ("modified_after", "modified_after=2026-01-01&per_page=1"),
            ("fields_projection", "fields=name,location&per_page=1&country=PL"),
            ("province_mazowieckie", "province=mazowieckie&per_page=1"),
            ("post_code", "post_code=00-001&per_page=1"),
            ("invalid_param", "ZZZ_garbage=foo&per_page=1"),
            ("invalid_country", "country=XX&per_page=1"),
            ("location_247_true", "location_247=true&per_page=1&country=PL"),
            ("easy_access_true", "easy_access_zone=true&per_page=1&country=PL"),
            ("payment_avail_true", "payment_available=true&per_page=1&country=PL"),
        ]
        for label, qs in tests:
            url = f"{BASE}?{qs}"
            st, h, b = fetch(url, save_as=f"filter_{label}.json")
            d = js(b)
            if d and "count" in d:
                print(f"  {label:35s} -> {d.get('count')} matches")
            elif d:
                print(f"  {label:35s} -> keys={list(d.keys())[:6]}")
            sleep()

    if stage in ("all","individual"):
        print("\n=== INDIVIDUAL & SIBLING ENDPOINTS ===")
        # /v1/points/{name} from saved earlier
        d = js((OUT/"per_page_25.json").read_text(encoding="utf-8")) if (OUT/"per_page_25.json").exists() else None
        sample_name = None
        sample_href = None
        if d and d.get("items"):
            sample_name = d["items"][0]["name"]
            sample_href = d["items"][0].get("href")
        if not sample_name:
            sample_name = "KRA012"
        # try various forms
        forms = [
            (f"single_{sample_name}_bare", f"{BASE}/{sample_name}"),
        ]
        if sample_href:
            forms.append((f"single_{sample_name}_href", sample_href))
        # also try a specific known one
        forms.append(("single_KRA012", f"{BASE}/KRA012"))
        forms.append(("single_KRA012_PL", f"{BASE}/PL/KRA012"))
        forms.append(("single_WAW01N", f"{BASE}/WAW01N"))

        for label, url in forms:
            st, h, b = fetch(url, save_as=f"{label}.json")
            sleep()

        # sibling endpoints
        siblings = ["countries","stats","health","cities","status","metadata","providers","types","functions","provinces","point","apm"]
        base_root = "https://api-global-points.easypack24.net/v1"
        for s in siblings:
            st, h, b = fetch(f"{base_root}/{s}", save_as=f"sibling_{s}.json")
            sleep()

    if stage in ("all","sample500"):
        print("\n=== SAMPLE 500 (PL) ===")
        url = f"{BASE}?country=PL&per_page=500&page=1"
        st, h, b = fetch(url, save_as="sample_500.json")
        d = js(b)
        if d:
            print(f"  Got {len(d['items'])} items. count={d['count']} total_pages={d['total_pages']}")
        sleep()

    if stage in ("all","extra"):
        # try max per_page push — but only one extreme
        print("\n=== PUSH PER_PAGE LIMITS ===")
        for pp in [2000, 10000]:
            st, h, b = fetch(f"{BASE}?per_page={pp}&page=1&country=PL", save_as=f"per_page_push_{pp}.json")
            d = js(b)
            if d and "items" in d:
                print(f"  per_page={pp} -> {len(d['items'])} items, total_pages={d.get('total_pages')}")
            elif d:
                print(f"  per_page={pp} -> {b[:200]}")
            sleep()

    pathlib.Path("recon/samples/_session_log.json").write_text(json.dumps(SESSION_LOG, indent=2))
    print(f"\nDone. {len(SESSION_LOG)} requests.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
