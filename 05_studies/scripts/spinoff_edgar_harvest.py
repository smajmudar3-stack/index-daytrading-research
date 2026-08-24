#!/usr/bin/env python3
"""
Survivorship-bias-free US corporate spinoff dataset from SEC EDGAR.

Core idea: Form 10-12B is the registration statement a SpinCo files to register
its shares under Exchange Act 12(b) before being distributed to parent
shareholders. Every US spinoff of a company that will list on an exchange files
one. The EDGAR quarterly form index enumerates ALL of them, back to 1994,
regardless of whether the SpinCo later got acquired or delisted. That makes the
enumeration survivorship-bias-free BY CONSTRUCTION -- unlike any curated list.

Stage 1: harvest 10-12B filings from EDGAR full-index (free, no key, 1994+)
Stage 2: enrich each with ticker + exchange + distribution date by regexing the
         Form 10 information statement (works for delisted SpinCos too)

Rate limit: SEC allows 10 req/sec with a declaring User-Agent. We use 8/sec.

Usage:
    python scripts/spinoff_edgar_harvest.py index      # stage 1
    python scripts/spinoff_edgar_harvest.py enrich     # stage 2
    python scripts/spinoff_edgar_harvest.py forward    # forward calendar
"""
import os
import re
import sys
import time
import html
import datetime as dt

import requests
import pandas as pd

UA = os.environ.get("SEC_UA", "Sahil Majmudar smajmudar886@gmail.com")
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "spinoffs")
os.makedirs(OUT, exist_ok=True)

_last = [0.0]

# form.idx column widths differ pre/post ~2000, so match structurally:
# form | company (may contain spaces) | cik | YYYY-MM-DD | path (no spaces)
IDX_RE = re.compile(r"^(\S+)\s+(.*?)\s+(\d{3,10})\s+(\d{4}-\d{2}-\d{2})\s+(\S+)$")

CACHE = os.path.join(OUT, "_idx_cache")
os.makedirs(CACHE, exist_ok=True)


def get(url, tries=3):
    """Rate-limited SEC fetch (8 req/sec)."""
    for attempt in range(tries):
        wait = 0.125 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


# ---------------------------------------------------------------- stage 1
def harvest_index(start_year=1994):
    """Pull every 10-12B / 10-12B/A filing from the EDGAR quarterly form index."""
    rows = []
    now = dt.date.today()
    for year in range(start_year, now.year + 1):
        for qtr in (1, 2, 3, 4):
            if year == now.year and (qtr - 1) * 3 + 1 > now.month:
                continue
            # Cache only the 10-12B lines: turns a ~12 min / 500MB re-run into seconds.
            cp = os.path.join(CACHE, f"{year}Q{qtr}.txt")
            if os.path.exists(cp):
                with open(cp) as fh:
                    lines = fh.read().splitlines()
            else:
                url = f"https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"
                r = get(url)
                if r is None:
                    continue
                lines = [ln for ln in r.text.splitlines() if ln.startswith("10-12B")]
                with open(cp, "w") as fh:
                    fh.write("\n".join(lines))
            for line in lines:
                if not line.startswith("10-12B"):
                    continue
                # NB: column widths differ between pre-2000 and modern form.idx,
                # so parse structurally (right-anchored) rather than fixed-width.
                m = IDX_RE.match(line.rstrip())
                if not m:
                    continue
                form, company, cik, date, fname = m.groups()
                rows.append({
                    "form": form,
                    "company": company,
                    "cik": int(cik),
                    "filing_date": date,
                    "path": fname,
                    "accession": fname.split("/")[-1].replace(".txt", ""),
                })
            print(f"  {year} QTR{qtr}: cumulative {len(rows)}", flush=True)

    df = pd.DataFrame(rows).drop_duplicates(subset=["accession"])
    df = df.sort_values(["cik", "filing_date"]).reset_index(drop=True)
    p = os.path.join(OUT, "edgar_10_12b_filings.csv")
    df.to_csv(p, index=False)
    print(f"\n{len(df)} filings ({df.form.eq('10-12B').sum()} originals) -> {p}")

    # One row per SpinCo = first (original) 10-12B per CIK
    orig = df[df.form == "10-12B"].groupby("cik", as_index=False).first()
    orig = orig.rename(columns={"filing_date": "registration_date"})
    orig["n_amendments"] = orig.cik.map(df[df.form != "10-12B"].groupby("cik").size()).fillna(0).astype(int)
    p2 = os.path.join(OUT, "spinco_registrations.csv")
    orig.sort_values("registration_date").to_csv(p2, index=False)
    print(f"{len(orig)} unique SpinCo registrations -> {p2}")
    return orig


# ---------------------------------------------------------------- stage 2
# The information statement (Form 10 body or EX-99.1) reliably contains a
# sentence like: 'expects [SpinCo] common stock to be listed on the New York
# Stock Exchange under the symbol "XYZ"'. This recovers tickers for SpinCos
# that have since delisted, which the submissions API cannot do.
_Q = '"“”‘’`\''
# Requires the ticker to be quoted and uppercase -- prevents matching the word
# "symbols" or stray capitalised words. Verified against GE Vernova -> GEV.
SYM_RE = re.compile(r'symbols?\s*[' + _Q + r']\s*([A-Z]{1,5})\s*[.,]?\s*[' + _Q + r']')
EXCH_RE = re.compile(
    r'(New York Stock Exchange|NYSE American|NYSE Arca|NYSE|'
    r'Nasdaq Global Select Market|Nasdaq Global Market|Nasdaq Capital Market|'
    r'Nasdaq Stock Market|Nasdaq|NYSE MKT|American Stock Exchange)', re.I)
# 'the distribution date, which is expected to be July 2, 2024'
DIST_RE = re.compile(
    r'(?:[Dd]istribution\s+[Dd]ate[^.]{0,80}?|'
    r'expects?\s+to\s+(?:complete\s+the\s+distribution|distribute)[^.]{0,120}?|'
    r'[Dd]istribution\s+will\s+(?:occur|be\s+(?:made|completed))[^.]{0,120}?)'
    r'((?:January|February|March|April|May|June|July|August|September|October|'
    r'November|December)\s+\d{1,2},\s+(?:19|20)\d{2})')
PARENT_RE = re.compile(
    r'(?:wholly[\s-]owned\s+subsidiary\s+of|separation\s+from|spin[\s-]?off\s+from|'
    r'all\s+of\s+the\s+outstanding\s+(?:shares\s+of\s+)?common\s+stock\s+of\s+[^,]{0,60},?\s+'
    r'a\s+wholly[\s-]owned\s+subsidiary\s+of)\s+([A-Z][A-Za-z0-9&.,\- ]{2,60}?)'
    r'(?:\s*\(|,|\.|\s+\("|;)')
# 'one share of our common stock for every two shares of Parent common stock'
# NOTE: the ORIGINAL 10-12B usually leaves the ratio and distribution date as
# blanks -- terms are only fixed in the final 10-12B/A. Enrichment therefore
# reads the LAST amendment, not the first filing.
RATIO_RE = re.compile(
    r'([\w.-]+)\s+shares?\s+of\s+(?:our\s+)?common\s+stock\s+'
    r'for\s+e(?:ach|very)\s+([\w.-]+)?\s*shares?\s+of\s+([A-Za-z .,\-]{0,40}?)common\s+stock',
    re.I)


def _pick_doc(cik, accession):
    """Return text of the largest HTML/TXT doc in the filing (the info statement)."""
    acc = accession.replace("-", "")
    idx = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json")
    if idx is None:
        return None
    try:
        items = idx.json()["directory"]["item"]
    except Exception:
        return None
    cands = [i for i in items
             if i["name"].lower().endswith((".htm", ".html", ".txt"))
             and "-index" not in i["name"].lower()]
    if not cands:
        return None
    # Pre-2001 filings report size as "" -- fall back to the full submission .txt,
    # which for those years IS the whole filing including the info statement.
    cands.sort(key=lambda i: (int(i.get("size") or 0),
                              i["name"].lower().endswith(".txt")), reverse=True)
    for c in cands[:3]:
        r = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{c['name']}")
        if r is None:
            continue
        txt = re.sub(r"<[^>]+>", " ", r.text)
        txt = html.unescape(txt)          # &#147; -> curly quote; required for SYM_RE
        txt = txt.replace("\xa0", " ")
        txt = re.sub(r"\s+", " ", txt)
        if len(txt) > 5000:
            return txt
    return None


def enrich(limit=None):
    """Registration date comes from the FIRST 10-12B (earliest public signal);
    ticker/ratio/distribution date come from the LAST 10-12B/A (terms fixed)."""
    all_f = pd.read_csv(os.path.join(OUT, "edgar_10_12b_filings.csv"))
    df = pd.read_csv(os.path.join(OUT, "spinco_registrations.csv"))
    # Candidate accessions per CIK, newest first: a thin cover-page amendment may
    # omit the information statement, so we walk back until the ticker is found.
    cand = (all_f.sort_values("filing_date", ascending=False)
                 .groupby("cik")["accession"].apply(list).to_dict())
    if limit:
        df = df.head(limit)
    # Resume: this is a multi-hour job (multi-MB filings), so skip CIKs already done.
    out, done = [], set()
    pout = os.path.join(OUT, "spinoffs_enriched.csv")
    if os.path.exists(pout) and not limit:
        prev = pd.read_csv(pout)
        out = prev.to_dict("records")
        done = set(prev.cik)
        print(f"resuming: {len(done)} already enriched")
    for n, row in enumerate(df.itertuples()):
        if row.cik in done:
            continue
        rec = {"cik": row.cik, "company": row.company,
               "registration_date": row.registration_date,
               "accession": row.accession}
        for acc in cand.get(row.cik, [row.accession])[:4]:
            txt = _pick_doc(row.cik, acc)
            if not txt:
                continue
            head = txt[:250000]
            m = SYM_RE.search(head)
            if m:
                rec["ticker"] = m.group(1).upper()
            m = EXCH_RE.search(head)
            if m and not rec.get("exchange"):
                rec["exchange"] = m.group(1)
            m = DIST_RE.search(head)
            if m and not rec.get("distribution_date_stated"):
                rec["distribution_date_stated"] = m.group(1)
            m = PARENT_RE.search(head)
            if m and not rec.get("parent_guess"):
                rec["parent_guess"] = m.group(1).strip()
            m = RATIO_RE.search(head)
            if m and not rec.get("ratio_raw"):
                rec["ratio_raw"] = m.group(0).strip()[:150]
            rec["source_accession"] = acc
            if rec.get("ticker"):
                break
        # Current listing status from submissions API: a SpinCo with a ticker in
        # the info statement but NO ticker here has delisted or been acquired.
        r = get(f"https://data.sec.gov/submissions/CIK{row.cik:010d}.json")
        if r is not None:
            try:
                j = r.json()
                rec["ticker_current"] = (j.get("tickers") or [None])[0]
                rec["exchange_current"] = (j.get("exchanges") or [None])[0]
                rec["sic"] = j.get("sic")
                rec["sic_desc"] = j.get("sicDescription")
                fl = j.get("filings", {}).get("recent", {}).get("filingDate", [])
                rec["last_filing_date"] = fl[0] if fl else None
                forms = j.get("filings", {}).get("recent", {}).get("form", [])
                rec["ever_filed_form25"] = any(str(f).startswith("25") for f in forms)
            except Exception:
                pass
        rec["still_listed"] = bool(rec.get("ticker_current"))
        out.append(rec)
        if n % 25 == 0:
            print(f"  {n}/{len(df)} {row.company[:40]}", flush=True)
            pd.DataFrame(out).to_csv(os.path.join(OUT, "spinoffs_enriched.csv"), index=False)
    res = pd.DataFrame(out)
    p = os.path.join(OUT, "spinoffs_enriched.csv")
    res.to_csv(p, index=False)
    print(f"\n{len(res)} enriched -> {p}")
    if "ticker" in res:
        print(f"  ticker recovered: {res.ticker.notna().sum()}")
    print(f"  still listed today: {res.still_listed.sum()}  "
          f"(DEAD: {(~res.still_listed).sum()} <- these are the survivorship tail)")
    return res


# ---------------------------------------------------------------- forward
def forward(days=540):
    """Announced-but-not-yet-completed spinoffs: recent 10-12B filers whose
    registration has not yet gone effective / who have not started filing 10-Qs."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    url = ("https://efts.sec.gov/LATEST/search-index?q=%22information+statement%22"
           f"&forms=10-12B&dateRange=custom&startdt={since}&enddt={dt.date.today().isoformat()}")
    r = get(url)
    if r is None:
        print("FTS failed")
        return
    hits = r.json()["hits"]["hits"]
    seen, rows = set(), []
    for h in hits:
        s = h["_source"]
        cik = s["ciks"][0]
        if cik in seen:
            continue
        seen.add(cik)
        rows.append({
            "cik": int(cik),
            "name": s["display_names"][0],
            "form": s["form"],
            "filing_date": s["file_date"],
            "sic": (s.get("sics") or [None])[0],
            "accession": s["adsh"],
        })
    df = pd.DataFrame(rows).sort_values("filing_date", ascending=False)
    p = os.path.join(OUT, "forward_calendar.csv")
    df.to_csv(p, index=False)
    print(df.to_string(index=False))
    print(f"\n-> {p}")
    return df


def census():
    """Fast pass (1 request per SpinCo, ~2 min for all 741): current listing status
    from data.sec.gov. A SpinCo that registered shares but has no ticker today was
    acquired, went private, or delisted -- i.e. the survivorship tail that curated
    lists silently drop. Does NOT parse filings, so no historical ticker."""
    df = pd.read_csv(os.path.join(OUT, "spinco_registrations.csv"))
    out = []
    for n, row in enumerate(df.itertuples()):
        rec = {"cik": row.cik, "company": row.company,
               "registration_date": row.registration_date}
        r = get(f"https://data.sec.gov/submissions/CIK{row.cik:010d}.json")
        if r is not None:
            try:
                j = r.json()
                rec["ticker_current"] = (j.get("tickers") or [None])[0]
                rec["exchange_current"] = (j.get("exchanges") or [None])[0]
                rec["sic_desc"] = j.get("sicDescription")
                rec["state"] = j.get("stateOfIncorporation")
                recent = j.get("filings", {}).get("recent", {})
                fd = recent.get("filingDate", [])
                rec["last_filing_date"] = fd[0] if fd else None
                forms = recent.get("form", [])
                # Form 25 / 25-NSE = exchange delisting notification
                rec["filed_form25"] = any(str(f).startswith("25") for f in forms)
                rec["filed_15"] = any(str(f).startswith("15") for f in forms)
            except Exception:
                pass
        rec["still_listed"] = bool(rec.get("ticker_current"))
        out.append(rec)
        if n % 100 == 0:
            print(f"  {n}/{len(df)}", flush=True)
    res = pd.DataFrame(out)
    p = os.path.join(OUT, "spinco_census.csv")
    res.to_csv(p, index=False)
    alive, dead = res.still_listed.sum(), (~res.still_listed).sum()
    print(f"\n{len(res)} SpinCo registrations -> {p}")
    print(f"  still listed today : {alive} ({alive/len(res):.0%})")
    print(f"  NOT listed today   : {dead} ({dead/len(res):.0%})  <-- the survivorship tail")
    print(f"  filed Form 25 (delisting notice): {res.filed_form25.sum()}")
    res["yr"] = res.registration_date.str[:4].astype(int)
    res["decade"] = (res.yr // 10) * 10
    print("\nsurvival by decade of registration:")
    print(res.groupby("decade").agg(n=("cik", "size"),
                                    still_listed=("still_listed", "sum"),
                                    pct=("still_listed", "mean")).to_string())
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "index"
    if cmd == "index":
        harvest_index()
    elif cmd == "enrich":
        enrich(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "census":
        census()
    elif cmd == "forward":
        forward()
