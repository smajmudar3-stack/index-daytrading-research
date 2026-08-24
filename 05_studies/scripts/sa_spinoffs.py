import json, time, urllib.request, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

def deref(nodes_data, idx):
    """Resolve SvelteKit devalue-style flat array."""
    v = nodes_data[idx]
    if isinstance(v, dict):
        return {k: deref(nodes_data, i) for k, i in v.items()}
    if isinstance(v, list):
        return [deref(nodes_data, i) for i in v]
    return v

def get_year(year):
    url = f"https://stockanalysis.com/actions/spinoffs/{year}/__data.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = json.load(urllib.request.urlopen(req, timeout=30))
    node = [n for n in raw["nodes"] if n and n.get("type") == "data"][-1]
    arr = node["data"]
    top = deref(arr, 0)
    return top


def main():
    rows = []
    for y in range(1998, 2027):
        try:
            top = get_year(y)
            d = top.get("data") or []
            for r in d:
                r["year"] = y
            rows.extend(d)
            print(f"{y}: {len(d)} rows", file=sys.stderr)
        except Exception as e:
            print(f"{y}: ERROR {e}", file=sys.stderr)
        time.sleep(0.4)

    json.dump(rows, open("sa_spinoffs.json", "w"), indent=1)
    print(f"TOTAL {len(rows)}")

    # survivorship probe: '$' prefix = has a stockanalysis page
    no_dollar_spinco = [r for r in rows if not str(r.get("symbol", "")).startswith("$")]
    print(f"spincos WITHOUT $ prefix (likely delisted/no page): {len(no_dollar_spinco)}")
    print("examples:", [(r["year"], r["oldname"], r["symbol"], r["name"]) for r in no_dollar_spinco[:12]])
    print("keys seen:", sorted({k for r in rows for k in r}))


if __name__ == "__main__":
    main()
