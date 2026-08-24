"""Rate-limited Semantic Scholar lookups for the spinoff / event-driven literature."""
import json, os, time, urllib.parse, urllib.request

from idt import paths

BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,year,abstract,venue,citationCount,authors,externalIds,openAccessPdf"

QUERIES = [
    "Restructuring through spinoffs stock market evidence Cusatis Miles Woolridge",
    "Firm performance and focus long-run stock market performance following spinoffs Desai Jain",
    "Predictability of long-term spinoff returns McConnell Ovtchinnikov",
    "Value creation through spin-offs review of empirical evidence Veld Veld-Merkoulova",
    "spinoff long-run abnormal returns out-of-sample recent evidence",
    "Does academic research destroy stock return predictability McLean Pontiff",
    "Accounting for the anomaly zoo trading costs Chen Velikov",
    "Replicating anomalies Hou Xue Zhang microcaps NYSE breakpoints",
    "disappearing index effect index inclusion S&P 500 Greenwood Sammon",
    "merger arbitrage returns risk Mitchell Pulvino",
    "SPAC returns Klausner Ohlrogge Ruan sober look",
    "post-bankruptcy equity returns Chapter 11 emergence abnormal returns",
]

def fetch(q, limit=5):
    url = f"{BASE}?query={urllib.parse.quote(q)}&limit={limit}&fields={FIELDS}"
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception:
            time.sleep(6 * (attempt + 1))
    return {"data": [], "error": "failed"}

def main():
    out = {}
    for q in QUERIES:
        d = fetch(q)
        out[q] = d
        print(f"\n########## {q}")
        for p in d.get("data", []):
            au = ", ".join(a["name"] for a in p.get("authors", [])[:4])
            pdf = (p.get("openAccessPdf") or {}).get("url") or ""
            print(f"\n--- {p.get('title')} ({p.get('year')}) | {p.get('venue')} | cites={p.get('citationCount')}")
            print(f"    authors: {au}")
            print(f"    ids: {p.get('externalIds')}")
            if pdf:
                print(f"    PDF: {pdf}")
            ab = p.get("abstract")
            if ab:
                print(f"    ABSTRACT: {ab[:1600]}")
        time.sleep(4)
    out_dir = paths.data("scratch")   # was a /private/tmp dir that no longer exists
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "lit.json"), "w") as f:
        json.dump(out, f, indent=1)

if __name__ == "__main__":
    main()
