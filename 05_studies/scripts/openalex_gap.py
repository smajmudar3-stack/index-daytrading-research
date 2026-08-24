"""Fill remaining gaps: recent works citing Cusatis-Miles-Woolridge, plus targeted title searches."""
import json, time, urllib.parse, urllib.request

MAIL = "smajmudar886@gmail.com"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"research ({MAIL})"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception:
            time.sleep(3 * (i + 1))
    return {"results": []}

def abstract(w):
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))

def show(w):
    au = ", ".join((a.get("author") or {}).get("display_name", "") for a in (w.get("authorships") or [])[:5])
    pl = w.get("primary_location") or {}
    s = (pl.get("source") or {}).get("display_name") or ""
    oa = (w.get("best_oa_location") or {}).get("pdf_url") or ""
    print(f"\n--- {w.get('title')} ({w.get('publication_year')}) | {s} | cites={w.get('cited_by_count')}")
    print(f"    authors: {au} | doi: {w.get('doi')}")
    if oa:
        print(f"    OA PDF: {oa}")
    ab = abstract(w)
    if ab:
        print(f"    ABSTRACT: {ab[:1800]}")

# 1. Recent (2010+) works citing CMW 1993, sorted by citations
print("########## RECENT WORK CITING Cusatis-Miles-Woolridge 1993 (2010+)")
d = get("https://api.openalex.org/works?filter=cites:W1539020160,from_publication_date:2010-01-01"
        f"&sort=cited_by_count:desc&per_page=25&mailto={MAIL}")
print(f"total citing works 2010+: {d.get('meta',{}).get('count')}")
for w in d.get("results", []):
    show(w)

# 2. Targeted title searches
TITLES = {
    "McConnellOvtch": "predictability of long-term spinoff returns",
    "IndexEffect": "the disappearing index effect",
    "MergerArb": "characteristics of risk and return in risk arbitrage",
    "SPAC": "a sober look at spacs",
    "SpinoffPost2015a": "spin-off long-run performance",
    "SpinoffPost2015b": "corporate spinoffs shareholder wealth long run",
    "ChenZimm": "open source cross-sectional asset pricing",
    "PostEarnBank": "the aggregate performance of bankrupt firms",
}
for k, t in TITLES.items():
    print(f"\n########## TITLE SEARCH {k}: {t}")
    d = get(f"https://api.openalex.org/works?filter=title.search:{urllib.parse.quote(t)}"
            f"&per_page=6&mailto={MAIL}")
    print(f"count={d.get('meta',{}).get('count')}")
    for w in d.get("results", []):
        show(w)
    time.sleep(1)
print("\nDONE")
