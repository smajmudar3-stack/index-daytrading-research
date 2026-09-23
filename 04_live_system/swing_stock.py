"""swing_stock.py — the quarterly stock book: the biggest earnings beats of the last ten
sessions, held for a quarter, in shares.

WHY THIS EXISTS. The weekly options book issues a card only on a measured basis, and most
weeks that is almost nothing. The one signal that measured strongly in this repo produces
a fresh crop every week: post-earnings-announcement drift on the SIZE of the surprise.
02_findings/fundamentals.md, 33,755 announcements, 2020-2026: the top quintile of
(reported EPS - consensus) / price beat the bottom quintile by +2.84% over the next 63
sessions, t +4.3, positive in all three time splits and 63% of weeks. It is worth nothing
at five days, which is why it is a STOCK book with a quarter's hold and not an options
card. Long-only against SPY it measured +4.7%/yr excess with a 52% monthly turnover
(05_studies/xsec_portfolio_test.py); this book is the forward test of that number.

WHAT IT DOES, once a day:
  1. who reported in the last COHORT_SESSIONS sessions (Unusual Whales calendar, two
     calls a session);
  2. each name's reported and estimated EPS for that print (yfinance earnings_dates), and
     its price on the report day, so SUE = (actual - estimate) / price -- the construction
     the backtest used, not a percent-of-estimate that explodes on tiny estimates;
  3. the tradeable subset (close >= MIN_PRICE, 20-day median dollar volume >= MIN_ADV);
  4. the top TOP_SHARE of the cohort by SUE are the picks; everything else is listed as
     refused with its rank, so a name absent from the picks is a name that was judged.
  5. the LEDGER: every pick is recorded once, filled at the NEXT session's open (never at
     a price that has already happened), marked daily against SPY over the same window, and
     closed after HOLD_SESSIONS. The entry is frozen; a losing pick stays visibly losing.

THIS PANEL IS CONTEXT. It ranks; it does not state an action. Only `panels/today.answer`
may do that (test_only_the_answer_panel_may_issue_an_action).
"""
import json
import math
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "swing_stock_snapshot.json"
DB = paths.state("swing_stock.db")

COHORT_SESSIONS = 10        # the print must be this recent
TOP_SHARE = 0.20            # the backtest's top quintile
MIN_PRICE = 10.0
MIN_ADV = 10e6
HOLD_SESSIONS = 63          # the horizon the drift measured on
HOLD_DAYS = 92              # calendar approximation of 63 sessions
MAX_PICKS = 25              # a fifth of a ~120-name cohort; sized for a small account


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ inputs ---

def reporters(sessions=COHORT_SESSIONS, now=None):
    """{TICKER: report_date} for every optionable name that reported in the window."""
    try:
        import earnings_vol
    except Exception:                                         # noqa: BLE001
        return {}, "earnings_vol unavailable"
    today = (now or _now()).date()
    out, d, seen = {}, today, 0
    while seen < sessions:
        if d.weekday() < 5:
            for ep in ("/api/earnings/premarket", "/api/earnings/afterhours"):
                for r in earnings_vol._rows(ep, {"date": d.isoformat()}) or []:
                    tk = (r.get("ticker") or r.get("symbol") or "").upper()
                    if tk and r.get("has_options"):
                        out.setdefault(tk, d.isoformat())
            seen += 1
        d -= timedelta(days=1)
    if not out:
        return {}, "the earnings calendar returned no reporters (vendor unavailable or quota)"
    return out, None


def surprise(ticker, report_date, now=None):
    """(reported, estimate) for the print on `report_date`, from yfinance. None if unknown."""
    try:
        import yfinance as yf
        ed = yf.Ticker(ticker).earnings_dates
    except Exception:                                         # noqa: BLE001
        return None
    if ed is None or not len(ed):
        return None
    rd = datetime.strptime(report_date, "%Y-%m-%d").date()
    best = None
    for ts, row in ed.iterrows():
        try:
            d = ts.date()
        except AttributeError:
            continue
        if abs((d - rd).days) > 3:
            continue
        rep, est = row.get("Reported EPS"), row.get("EPS Estimate")
        if rep is None or est is None or (isinstance(rep, float) and math.isnan(rep)) \
                or (isinstance(est, float) and math.isnan(est)):
            continue
        best = (float(rep), float(est))
        break
    return best


def sue(reported, estimate, price):
    if price is None or price <= 0:
        return None
    return (reported - estimate) / price


def select(rows, top=TOP_SHARE, max_picks=MAX_PICKS):
    """rows: [{ticker, sue, close, adv20, ...}]. Returns (picks, refused), both ranked.

    Pure, so it is testable: the cohort is whatever was passed in, the cut is a share of
    it, and every name comes back on one list or the other with its reason.
    """
    ok, refused = [], []
    for r in rows:
        if r.get("sue") is None:
            refused.append({**r, "why": "no reported/estimated EPS for this print"})
        elif r.get("close") is None or r["close"] < MIN_PRICE:
            refused.append({**r, "why": f"price below ${MIN_PRICE:.0f}"})
        elif r.get("adv20") is None or r["adv20"] < MIN_ADV:
            refused.append({**r, "why": "20-day dollar volume below $10m"})
        else:
            ok.append(r)
    ok.sort(key=lambda r: -r["sue"])
    n_pick = min(max_picks, int(math.floor(len(ok) * top)))
    for i, r in enumerate(ok):
        r["rank"] = i + 1
        r["cohort"] = len(ok)
    picks = ok[:n_pick]
    for r in ok[n_pick:]:
        refused.append({**r, "why": f"ranked {r['rank']} of {len(ok)} on surprise; the cut is the top "
                                    f"{int(top*100)}% (measured: the drift is in the top quintile)"})
    return picks, refused


# --------------------------------------------------------------------- run ---

def _prices(tickers):
    """{ticker: DataFrame[open, close, volume]} for ~70 sessions, batched. Never raises."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
        raw = yf.download(sorted(set(tickers) | {"SPY"}), period="4mo", interval="1d",
                          progress=False, auto_adjust=True, group_by="ticker", threads=True)
    except Exception:                                         # noqa: BLE001
        return {}
    out = {}
    for tk in set(tickers) | {"SPY"}:
        try:
            d = raw[tk].dropna(how="all").rename(columns=str.lower)
            if len(d) >= 5 and "close" in d:
                out[tk] = d
        except (KeyError, TypeError, AttributeError):
            continue
    return out


def run(now=None):
    """Build the cohort, rank it, write the snapshot, feed the ledger. Never raises to the caller."""
    reps, err = reporters(now=now)
    if err:
        out = {"ok": False, "as_of": _stamp(), "blocked": err, "picks": [], "refused": [],
               "cohort_n": 0}
        snapshots.write(OUT, out)
        return out
    px = _prices(list(reps))
    rows = []
    for tk, rd in sorted(reps.items()):
        d = px.get(tk)
        close = adv = None
        if d is not None:
            # A partial or unsettled session comes back as a NaN row at the end of the frame,
            # so "the last close" and "the first close on or after the print" both read
            # through NaNs rather than trusting positional rows.
            d = d.dropna(subset=["close"])
            after = d[d.index.strftime("%Y-%m-%d") >= rd]
            if len(after):
                close = float(after["close"].iloc[0])
            dv = (d["close"] * d["volume"]).dropna().tail(20)
            adv = float(dv.median()) if len(dv) >= 10 else None
        s = surprise(tk, rd, now=now)
        rows.append({"ticker": tk, "report_date": rd, "reported": s[0] if s else None,
                     "estimate": s[1] if s else None, "close": close, "adv20": adv,
                     "sue": sue(s[0], s[1], close) if (s and close) else None,
                     "sue_pct": round(sue(s[0], s[1], close) * 100, 2) if (s and close) else None,
                     "spot": float(d["close"].iloc[-1]) if d is not None and len(d) else None})
    picks, refused = select(rows)
    out = {"ok": True, "as_of": _stamp(), "cohort_n": len(rows), "n_ranked": len(picks) + sum(
        1 for r in refused if "ranked" in r["why"]),
        "picks": picks, "refused": sorted(refused, key=lambda r: -(r.get("sue") or -9)),
        "hold_sessions": HOLD_SESSIONS,
        "basis": ("earnings-surprise drift: top quintile of (reported - estimate) / price beat the "
                  "bottom by +2.84% over 63 sessions, t +4.3, 33,755 prints 2020-2026, all three "
                  "splits positive (02_findings/fundamentals.md)")}
    snapshots.write(OUT, out)
    try:
        book(picks, px, now=now)
    except Exception as e:                                    # noqa: BLE001
        out["ledger_error"] = f"{type(e).__name__}: {e}"
    return out


# ------------------------------------------------------------------ ledger ---

def _con():
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS picks (
        id INTEGER PRIMARY KEY, issued TEXT NOT NULL, ticker TEXT NOT NULL,
        report_date TEXT NOT NULL, sue REAL, rank INTEGER, cohort INTEGER,
        entry_date TEXT, entry REAL, spy_entry REAL, exit_due TEXT,
        status TEXT NOT NULL DEFAULT 'pending', cur REAL, spy_cur REAL,
        pnl_pct REAL, rel_pct REAL, updated TEXT, closed TEXT,
        UNIQUE(ticker, report_date))""")
    return con


def book(picks, px, now=None):
    """Record new picks once; fill pending ones at the next open; mark and close the rest."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    today = (now or _now()).date().isoformat()
    added = 0
    for p in picks:
        cur = con.execute("SELECT 1 FROM picks WHERE ticker=? AND report_date=?",
                          (p["ticker"], p["report_date"])).fetchone()
        if cur:
            continue
        con.execute("INSERT INTO picks (issued, ticker, report_date, sue, rank, cohort, status) "
                    "VALUES (?,?,?,?,?,?,'pending')",
                    (_stamp(), p["ticker"], p["report_date"], p["sue"], p.get("rank"), p.get("cohort")))
        added += 1
    spy = px.get("SPY")
    filled = marked = closed = 0
    for r in con.execute("SELECT * FROM picks WHERE status IN ('pending','open')").fetchall():
        r = dict(r)
        d = px.get(r["ticker"])
        if d is None or spy is None:
            continue
        if r["status"] == "pending":
            # the first session strictly after the issue date: its OPEN is the fill
            after = d[d.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            s_after = spy[spy.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            if not len(after) or not len(s_after):
                continue
            ed = after.index[0].strftime("%Y-%m-%d")
            due = (after.index[0] + timedelta(days=HOLD_DAYS)).strftime("%Y-%m-%d")
            con.execute("UPDATE picks SET status='open', entry_date=?, entry=?, spy_entry=?, exit_due=? "
                        "WHERE id=?", (ed, float(after["open"].iloc[0]), float(s_after["open"].iloc[0]),
                                       due, r["id"]))
            filled += 1
            r.update(status="open", entry=float(after["open"].iloc[0]),
                     spy_entry=float(s_after["open"].iloc[0]), exit_due=due)
        dc, sc = d["close"].dropna(), spy["close"].dropna()
        if not len(dc) or not len(sc):
            continue
        cur, scur = float(dc.iloc[-1]), float(sc.iloc[-1])
        pnl = (cur / r["entry"] - 1) * 100
        rel = pnl - (scur / r["spy_entry"] - 1) * 100
        done = today >= r["exit_due"]
        con.execute("UPDATE picks SET cur=?, spy_cur=?, pnl_pct=?, rel_pct=?, updated=?, status=?, closed=? "
                    "WHERE id=?", (cur, scur, round(pnl, 2), round(rel, 2), _stamp(),
                                   "closed" if done else "open", _stamp() if done else None, r["id"]))
        marked += 1
        closed += int(done)
    con.commit()
    con.close()
    return {"ok": True, "added": added, "filled": filled, "marked": marked, "closed": closed}


def ledger(limit=60):
    """Open and closed picks for the panel, plus a summary. Never raises."""
    con = _con()
    if con is None:
        return {"open": [], "closed": [], "summary": {"n": 0}}
    rows = [dict(r) for r in con.execute("SELECT * FROM picks ORDER BY issued DESC LIMIT ?", (limit,))]
    con.close()
    op = [r for r in rows if r["status"] in ("open", "pending")]
    cl = [r for r in rows if r["status"] == "closed"]
    sc = [r for r in cl if r["rel_pct"] is not None]
    summary = {"n": len(cl), "n_open": len(op),
               "hit_rate": round(100 * sum(1 for r in sc if r["rel_pct"] > 0) / len(sc), 0) if sc else None,
               "avg_rel_pct": round(sum(r["rel_pct"] for r in sc) / len(sc), 2) if sc else None,
               "avg_pnl_pct": round(sum(r["pnl_pct"] for r in sc) / len(sc), 2) if sc else None}
    return {"open": op, "closed": cl, "summary": summary}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str)[:3000])
