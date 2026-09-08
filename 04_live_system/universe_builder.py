"""universe_builder.py — the tradable universe, discovered rather than typed out.

WHY. `weekly_swing.UNIVERSE_META` was 283 tickers I typed by hand, each with a sector and a
cap tier I assigned by hand. Two problems, and the second is worse than the first.

  1. It is small. 283 names out of a US market with roughly 1,900 optionable equities means
     the scan cannot see most of what is happening.
  2. It is MY list. Hand-picking the universe is a silent selection choice made before any
     measurement runs: every name in it is one I thought of, which correlates with names that
     have been in the news, which correlates with names that have already moved. A backtest
     over a universe chosen in 2026 for names that mattered in 2026 is survivorship bias with
     extra steps, and nothing downstream can detect it.

So the universe comes from the index constituent lists instead. S&P 500 + 400 + 600 is about
1,500 names, it carries an official GICS sector for each, and membership defines the cap tier
rather than my opinion of it.

WHAT MAKES THIS AFFORDABLE
==========================
A bigger universe is only useful if scanning it is cheap, and two things make it cheap:

  - History is fetched in BATCHES (see `weekly_swing._prefetch`). yfinance takes a list, so
    1,500 names cost ~25 calls instead of 1,500.
  - The expensive per-name work -- the option chain, the Unusual Whales flow -- happens only
    AFTER a name has a basis and clears a liquidity screen. Most of the universe never
    reaches it. Widening the front of the funnel does not widen the back.

THE LIQUIDITY SCREEN IS NOT OPTIONAL
====================================
Most of the S&P 600 cannot be traded in weekly options at any sane price. Rather than let
those names burn a chain fetch each and get refused on spread, `liquid()` screens them on
median dollar volume from data already in hand. A name that trades $3m/day does not have a
weekly option worth quoting, and this repo's own `MAX_TRADE_COST_PCT` would reject it anyway
-- three API calls later.
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from idt import paths                                          # noqa: E402

ET = ZoneInfo("America/New_York")
FILE = "universe.json"
REFRESH_AFTER_DAYS = 30

WIKI = {
    "large": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "mid": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "small": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}

# GICS sector -> the SPDR sector ETF this repo already measures rate betas and breadth against.
# Using the ETF as the sector key is deliberate: every downstream consumer (market_basis's
# RATE_BETA, sector_read, sector_corroboration) is already keyed this way, so a wider universe
# needs no new sector vocabulary.
GICS_TO_ETF = {
    "information technology": "XLK", "health care": "XLV", "financials": "XLF",
    "consumer discretionary": "XLY", "communication services": "XLC",
    "industrials": "XLI", "consumer staples": "XLP", "energy": "XLE",
    "utilities": "XLU", "real estate": "XLRE", "materials": "XLB",
}

# Median dollar volume below this and the weekly option is not quotable at a price worth
# paying. Chosen to sit above where MAX_TRADE_COST_PCT would reject the trade anyway.
MIN_DOLLAR_VOL = 25_000_000


def _path():
    return os.path.join(paths.STATE_ROOT, FILE)


def _fetch_index(url):
    """Ticker -> GICS sector for one index. Returns {} on any failure.

    Fetched with an explicit User-Agent: Wikipedia returns 403 to pandas' default, which is
    the kind of failure that reads as "the list is empty" if you do not check.
    """
    try:
        import io
        import urllib.request

        import pandas as pd
        req = urllib.request.Request(url, headers={
            "User-Agent": "index-daytrading-research/1.0 (universe builder; contact via repo)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        tables = pd.read_html(io.StringIO(html))
    except Exception:                                         # noqa: BLE001
        return {}
    for t in tables:
        cols = {str(c).strip().lower(): c for c in t.columns}
        sym = next((cols[k] for k in cols if k in ("symbol", "ticker")), None)
        sec = next((cols[k] for k in cols if "gics" in k and "sector" in k
                    and "sub" not in k), None)
        if sym is None or sec is None:
            continue
        out = {}
        for _, row in t.iterrows():
            tk = str(row[sym]).strip().upper().replace(".", "-")
            g = str(row[sec]).strip().lower()
            etf = GICS_TO_ETF.get(g)
            # A ticker with no GICS match is a parse artifact; dropping it is correct, and
            # counting the drops is how a layout change gets noticed instead of silently
            # shrinking the scan. Hyphens are kept: BRK-B and BF-B are real yfinance symbols.
            if etf and tk and tk.replace("-", "").isalnum():
                out[tk] = etf
        if len(out) > 50:
            return out
    return {}


def build():
    """Fetch all three indices. Returns (meta, note). Never raises."""
    meta, counts = {}, {}
    for cap, url in WIKI.items():
        got = _fetch_index(url)
        counts[cap] = len(got)
        for tk, etf in got.items():
            meta.setdefault(tk, (etf, cap))
    if len(meta) < 300:
        return None, (f"index pages yielded only {len(meta)} names ({counts}) — the table "
                      f"layout probably changed. Keeping the existing universe rather than "
                      f"shrinking the scan silently.")
    return meta, f"{len(meta)} names: {counts}"


def load():
    """(meta, status). `meta` maps ticker -> (sector_etf, cap_tier)."""
    p = _path()
    if not os.path.exists(p):
        return None, "absent"
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        meta = {k: tuple(v) for k, v in (d.get("meta") or {}).items()}
    except (json.JSONDecodeError, OSError, TypeError):
        return None, "unreadable"
    if not meta:
        return None, "empty"
    try:
        built = datetime.strptime(d.get("built_on", "")[:10], "%Y-%m-%d").date()
        age = (datetime.now(ET).date() - built).days
    except ValueError:
        return meta, "unverified"
    return meta, ("stale" if age > REFRESH_AFTER_DAYS else "ok")


def save(meta, note=""):
    os.makedirs(paths.STATE_ROOT, exist_ok=True)
    payload = {"built_on": datetime.now(ET).strftime("%Y-%m-%d"),
               "note": note, "n": len(meta),
               "meta": {k: list(v) for k, v in meta.items()}}
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, _path())
    return _path()


def liquid(closes, volumes, min_dollar_vol=MIN_DOLLAR_VOL):
    """Names whose median 20-day dollar volume clears the floor.

    Takes frames already fetched for the trend read, so the screen costs nothing extra.
    """
    keep, dropped = [], []
    for tk in closes.columns:
        try:
            dv = (closes[tk] * volumes[tk]).tail(20).median()
        except (KeyError, TypeError):
            continue
        if dv is not None and dv == dv and dv >= min_dollar_vol:
            keep.append(tk)
        else:
            dropped.append((tk, float(dv) if dv == dv else 0.0))
    return keep, dropped


if __name__ == "__main__":
    if "--build" in sys.argv:
        meta, note = build()
        print(note)
        if meta:
            save(meta, note)
            from collections import Counter
            print("  by sector:", dict(Counter(s for s, _ in meta.values())))
            print("  by cap:   ", dict(Counter(c for _, c in meta.values())))
    else:
        meta, status = load()
        print(f"universe {status}: {len(meta) if meta else 0} names")
