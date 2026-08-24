"""OpenAlex lookups for the spinoff / event-driven anomaly literature."""
import json, os, time, urllib.parse, urllib.request

from idt import paths

MAIL = "smajmudar886@gmail.com"
BASE = "https://api.openalex.org/works"

QUERIES = {
    "CMW1993": "Restructuring through spinoffs the stock market evidence Cusatis",
    "DesaiJain1999": "Firm performance and focus long-run stock market performance following spinoffs",
    "McConnellOvtch": "Predictability of long-term spinoff returns McConnell Ovtchinnikov",
    "VeldMeta": "Value creation through spin-offs a review of the empirical evidence",
    "VeldEuro": "Do spin-offs really create value European case Veld Veld-Merkoulova",
    "SpinoffRecent": "corporate spin-off long-run abnormal returns evidence 2018 2020",
    "SpinoffIndex": "index fund forced selling spinoff institutional investors abnormal returns",
    "McLeanPontiff": "Does academic research destroy stock return predictability",
    "ChenVelikov": "Accounting for the anomaly zoo a trading cost perspective",
    "HouXueZhang": "Replicating anomalies Hou Xue Zhang",
    "ChenZimmermann": "Open source cross-sectional asset pricing Chen Zimmermann",
    "Fama1998": "Market efficiency long-term returns and behavioral finance Fama",
    "IndexEffect": "The disappearing index effect Greenwood Sammon",
    "MergerArb": "Characteristics of risk and return in risk arbitrage Mitchell Pulvino",
    "SPAC": "A sober look at SPACs Klausner Ohlrogge Ruan",
    "Bankruptcy": "Aggregate performance of bankrupt firms stock returns emergence Chapter 11",
    "SpinoffOperating": "spinoff operating performance improvement focus evidence",
    "SpinoffTax": "taxable versus tax-free spinoffs abnormal returns",
}

def q(search, per_page=4):
    url = (f"{BASE}?search={urllib.parse.quote(search)}&per_page={per_page}"
           f"&mailto={MAIL}")
    req = urllib.request.Request(url, headers={"User-Agent": f"research ({MAIL})"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception:
            time.sleep(3 * (i + 1))
    return {"results": []}

def src(w):
    pl = w.get("primary_location") or {}
    s = pl.get("source") or {}
    return s.get("display_name") or ""

def abstract(w):
    inv = w.get("abstract_inverted_index")
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def main():
    out = {}
    for key, s in QUERIES.items():
        d = q(s)
        out[key] = d
        print(f"\n############ {key}: {s}")
        for w in d.get("results", []):
            au = ", ".join((a.get("author") or {}).get("display_name", "") for a in (w.get("authorships") or [])[:5])
            oa = (w.get("best_oa_location") or {}).get("pdf_url") or ""
            doi = w.get("doi") or ""
            print(f"\n--- {w.get('title')} ({w.get('publication_year')}) | {src(w)} | cites={w.get('cited_by_count')}")
            print(f"    authors: {au}")
            print(f"    doi: {doi}")
            if oa:
                print(f"    OA PDF: {oa}")
            ab = abstract(w)
            if ab:
                print(f"    ABSTRACT: {ab[:2000]}")
        time.sleep(1)

    out_dir = paths.data("scratch")   # was a /private/tmp dir that no longer exists
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "openalex.json"), "w") as f:
        json.dump(out, f)
    print("\nDONE")


if __name__ == "__main__":
    main()
