"""price_cache.py — one daily-bar cache for every book, so a throttled vendor degrades a few
names instead of blocking the whole scan.

WHY. From 2026-10-02 to 10-19 yfinance returned 300–800 of the ~1,700 names each book asked
for, every cycle, and the outage guard (added so an unpriced name is never "refused")
blocked the stock book, the ranker and the stress book for seventeen days: no cohorts, no
marks. Each book fetched its whole universe from scratch every run, in batches of 120, and
the vendor throttles exactly that. The fix is memory: bars live in `prices.db`, a run only
asks for what is missing since the last close, asks in small batches with backoff, and a
name that still fails stays at yesterday's bar, flagged, instead of vanishing.

    history(tickers, days=400) -> {ticker: DataFrame[open, high, low, close, volume]}
        serves from the cache; fetches only tickers whose newest bar is older than the last
        session (or absent), in batches of BATCH, sleeping and halving the batch on an empty
        answer; stops asking after BUDGET_S seconds and reports what it could not refresh.
    coverage(tickers) -> (fresh, stale, missing)

Bars are yfinance's auto-adjusted daily bars, stored by (ticker, date). Nothing here knows
what a book is; it only keeps the bars.
"""
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from idt import db as _db
from idt import paths

ET = ZoneInfo("America/New_York")
DB = paths.state("prices.db")
BATCH = 40
BUDGET_S = 240
SLEEP_S = 2.0


def _con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS bars (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
                 PRIMARY KEY (ticker, date))""")
    c.execute("""CREATE TABLE IF NOT EXISTS status (ticker TEXT PRIMARY KEY, newest TEXT, tried REAL, fails INTEGER DEFAULT 0, note TEXT)""")
    return c


def last_session(now=None):
    """The most recent weekday whose close is in the past (16:00 ET), as YYYY-MM-DD."""
    now = now or datetime.now(ET)
    d = now.date()
    if now.weekday() < 5 and now.hour < 16:
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def _newest(c, tickers):
    q = ",".join("?" * len(tickers))
    return dict(c.execute(f"SELECT ticker, MAX(date) FROM bars WHERE ticker IN ({q}) GROUP BY ticker", tickers).fetchall()) if tickers else {}


def _store(c, tk, df):
    rows = []
    for ts, r in df.iterrows():
        try:
            rows.append((tk, ts.strftime("%Y-%m-%d"), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]),
                         float(r["volume"]) if pd.notna(r.get("volume")) else None))
        except (KeyError, TypeError, ValueError):
            continue
    c.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def _fetch(chunk, period):
    import yfinance as yf
    raw = yf.download(chunk, period=period, interval="1d", progress=False, auto_adjust=True, group_by="ticker", threads=False)
    out = {}
    for tk in chunk:
        try:
            d = (raw[tk] if len(chunk) > 1 else raw).dropna(how="all").rename(columns=str.lower)
            if len(d) and "close" in d:
                out[tk] = d
        except (KeyError, TypeError, AttributeError):
            continue
    return out


def refresh(tickers, days=400, budget_s=BUDGET_S, now=None):
    """Fetch what is missing or stale. Returns {fetched, failed, skipped_fresh, seconds}."""
    c = _con()
    tickers = sorted({t for t in tickers if t})
    target = last_session(now)
    newest = _newest(c, tickers)
    need = [t for t in tickers if (newest.get(t) or "") < target]
    fresh = len(tickers) - len(need)
    t0 = time.time()
    fetched, failed = 0, []
    batch = BATCH
    i = 0
    while i < len(need) and time.time() - t0 < budget_s:
        chunk = need[i:i + batch]
        # a name with history only needs the tail; a new name needs the whole window
        period = "1y" if any((newest.get(t) is None) for t in chunk) else "1mo"
        if days > 300 and period == "1mo" and any((newest.get(t) or "") < (datetime.now(ET) - timedelta(days=20)).strftime("%Y-%m-%d") for t in chunk):
            period = "3mo"
        try:
            got = _fetch(chunk, period)
        except Exception:                                     # noqa: BLE001
            got = {}
        for tk in chunk:
            if tk in got:
                _store(c, tk, got[tk])
                c.execute("INSERT OR REPLACE INTO status VALUES (?,?,?,?,?)", (tk, got[tk].index[-1].strftime("%Y-%m-%d"), time.time(), 0, None))
                fetched += 1
            else:
                prev = c.execute("SELECT fails FROM status WHERE ticker=?", (tk,)).fetchone()
                c.execute("INSERT OR REPLACE INTO status VALUES (?,?,?,?,?)", (tk, newest.get(tk), time.time(), (prev[0] if prev else 0) + 1, "no data"))
                failed.append(tk)
        c.commit()
        if len(got) < len(chunk) * 0.5:
            batch = max(10, batch // 2)                       # throttled: smaller asks, longer waits
            time.sleep(SLEEP_S * 3)
        else:
            time.sleep(SLEEP_S)
        i += len(chunk)
    c.close()
    return {"fetched": fetched, "failed": failed, "not_tried": need[i:], "fresh": fresh, "seconds": round(time.time() - t0)}


def history(tickers, days=400, refresh_first=True, budget_s=BUDGET_S, now=None):
    """{ticker: DataFrame} from the cache, refreshed first when asked. SPY is always included."""
    tickers = sorted({t for t in tickers if t} | {"SPY"})
    rep = refresh(tickers, days=days, budget_s=budget_s, now=now) if refresh_first else None
    c = _con()
    since = (datetime.now(ET) - timedelta(days=int(days * 1.5))).strftime("%Y-%m-%d")
    q = ",".join("?" * len(tickers))
    df = pd.read_sql(f"SELECT * FROM bars WHERE ticker IN ({q}) AND date >= ? ORDER BY ticker, date", c, params=[*tickers, since])
    c.close()
    out = {}
    for tk, g in df.groupby("ticker"):
        g = g.set_index(pd.to_datetime(g.date))[["open", "high", "low", "close", "volume"]]
        g.index.name = None
        out[tk] = g
    if rep is not None:
        out["_report"] = rep
    return out


def coverage(tickers, now=None):
    c = _con()
    target = last_session(now)
    newest = _newest(c, sorted({t for t in tickers if t}))
    c.close()
    fresh = [t for t in tickers if newest.get(t) == target]
    stale = [t for t in tickers if newest.get(t) and newest.get(t) < target]
    missing = [t for t in tickers if not newest.get(t)]
    return fresh, stale, missing


if __name__ == "__main__":
    import sys
    tks = sys.argv[1:] or ["SPY", "AAPL", "MSFT"]
    h = history(tks)
    print(h.pop("_report", None))
    for k, v in h.items():
        print(k, len(v), v.index.min().date(), v.index.max().date())
