"""stress_reversal.py — the stress book: when VIX is above 25, buy the week's biggest losers
and hold ten sessions, in shares. Paper only, with a ledger. RECORDS; PLACES NOTHING.

WHY THIS EXISTS. 02_findings/signal_accuracy.md scored 68 factors and found nothing that
calls a single stock's direction more than ~50% of the time — EXCEPT in one regime. When
the tape is stressed, last month's and last week's biggest losers bounce: the bottom decile
of a reversal composite (rank of 1-month return, 1-week return and 20-day Bollinger
position, averaged) bought and held ten sessions made +1.55% over SPY per hold (t 2.0),
hit rate 0.55, wins 1.3x losses, positive in every split, every regime definition tried
(VIX > 25, VIX top 30% of its year, SPY under its 200-day, SPY 12-month negative), every
hold (5/10/21 sessions), at 30 bp a side, and in every year with an on-week. The bottom 40
names did better still (+2.59%/hold, t 2.6, hit 0.56). OUT of the regime the same trade is
flat to negative (-8 to -13%/yr net). 05_studies/regime_reversal_test.py.

The mechanism is published, which is why it is allowed to run on 34 non-overlapping dates:
Nagel (2012, RFS, "Evaporating Liquidity") shows short-term reversal returns are the
compensation for providing liquidity and are predicted by VIX; when volatility is high the
market-makers step back and whoever buys the forced selling gets paid for it. That is what
this book is: a liquidity provider that only shows up when the price of liquidity is high.

WHAT IT DOES, once a day:
  1. reads ^VIX; if the last close is not above VIX_ON the book is OFF and says so, with
     the level, and issues nothing (this is the state most of the time: on ~16% of weeks);
  2. when ON and no cohort was issued in the last ISSUE_GAP_SESSIONS, prices the
     dashboard's universe (universe_builder, ~1,550 names, batched), screens to
     close >= MIN_PRICE and 20-day dollar volume >= MIN_ADV, ranks the reversal composite,
     and issues the bottom N_PICKS as the cohort;
  3. the LEDGER: every pick is recorded once, filled at the NEXT session's open, marked
     daily against SPY over the same window, and closed after HOLD_SESSIONS. The entry is
     frozen; a losing pick stays visibly losing. Overlapping cohorts are expected (issue
     every 5 sessions, hold 10), exactly as the backtest sampled.

THIS PANEL IS CONTEXT. It ranks; it does not state an action. Only `panels/today.answer`
may do that.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "stress_reversal_snapshot.json"
DB = paths.state("stress_reversal.db")

VIX_ON = 25.0               # the regime: every split positive above this; off below
N_PICKS = 40                # the bottom 40 by the composite: +2.59%/hold, t 2.6, hit 0.56
MIN_PRICE = 10.0
MIN_ADV = 10e6
HOLD_SESSIONS = 10          # +1.55% decile / +2.59% top-40 per hold; 5 and 21 also positive
HOLD_DAYS = 15              # calendar approximation of 10 sessions
ISSUE_GAP_SESSIONS = 5      # a new cohort at most weekly, as the backtest sampled
MEASURED = {"per_hold_pct": 2.59, "t": 2.6, "hit": 0.562, "payoff": 1.42, "dates": 34,
            "splits": "+0.92 / +3.66 / +3.75", "source": "02_findings/stress_reversal.md"}


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


def _notify(title, msg):
    """Desktop ping, best effort; the ledger is the record and panels/today.answer the action."""
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
        return True
    except Exception:                                         # noqa: BLE001
        return False


# ------------------------------------------------------------------ inputs ---

def vix_now():
    """(last VIX close, its date) from yfinance. (None, why) on failure."""
    try:
        import yfinance as yf
        v = yf.download("^VIX", period="3mo", interval="1d", progress=False, auto_adjust=True)["Close"]
        v = v.iloc[:, 0] if hasattr(v, "columns") else v
        v = v.dropna()
        if not len(v):
            return None, "VIX history empty"
        return float(v.iloc[-1]), v.index[-1].strftime("%Y-%m-%d")
    except Exception as e:                                    # noqa: BLE001
        return None, f"VIX unreadable: {type(e).__name__}"


def universe():
    """The dashboard's discovered universe (S&P 1500). [] with a reason if absent."""
    try:
        import universe_builder
        meta, status = universe_builder.load()
    except Exception as e:                                    # noqa: BLE001
        return [], f"universe unreadable: {type(e).__name__}"
    if not meta:
        return [], f"universe {status}"
    return sorted(meta), None


def _prices(tickers):
    from swing_stock import _prices as _p
    return _p(tickers)


def composite(d):
    """The three reversal reads for one name's price frame. None if too short."""
    c = d["close"].dropna()
    if len(c) < 25:
        return None
    r1m = float(c.iloc[-1] / c.iloc[-22] - 1)
    r1w = float(c.iloc[-1] / c.iloc[-6] - 1)
    m20, s20 = float(c.tail(20).mean()), float(c.tail(20).std())
    bb = (float(c.iloc[-1]) - m20) / (2 * s20) if s20 > 0 else 0.0
    return {"ret1m": r1m, "ret1w": r1w, "bb_pos": bb}


def select(rows, n_picks=N_PICKS):
    """rows: [{ticker, close, adv20, ret1m, ret1w, bb_pos}]. Returns (picks, refused), ranked
    from the biggest loser. Pure. The composite is the mean RANK of the three reads, so no
    one read dominates by scale."""
    ok, refused = [], []
    for r in rows:
        if r.get("ret1m") is None:
            refused.append({**r, "why": "price history too short"})
        elif r.get("close") is None or r["close"] < MIN_PRICE:
            refused.append({**r, "why": f"price below ${MIN_PRICE:.0f}"})
        elif r.get("adv20") is None or r["adv20"] < MIN_ADV:
            refused.append({**r, "why": "20-day dollar volume below $10m"})
        else:
            ok.append(r)
    n = len(ok)
    if n == 0:
        return [], refused
    for k in ("ret1m", "ret1w", "bb_pos"):
        order = sorted(range(n), key=lambda i: ok[i][k])
        for rank, i in enumerate(order):
            ok[i][f"rk_{k}"] = (rank + 1) / n
    for r in ok:
        r["score"] = round((r["rk_ret1m"] + r["rk_ret1w"] + r["rk_bb_pos"]) / 3, 4)
    ok.sort(key=lambda r: r["score"])
    for i, r in enumerate(ok):
        r["rank"] = i + 1
        r["cohort"] = n
    picks = ok[:n_picks]
    for r in ok[n_picks:]:
        refused.append({**r, "why": f"ranked {r['rank']} of {n} on the reversal composite; the book takes the "
                                    f"{n_picks} biggest losers"})
    return picks, refused


# --------------------------------------------------------------------- run ---

def _last_issue(con):
    r = con.execute("SELECT MAX(issued) FROM picks").fetchone()
    return r[0] if r and r[0] else None


def run(now=None):
    """Read the regime; when on and due, build a cohort; always feed the ledger. Never raises."""
    now = now or _now()
    vix, vd = vix_now()
    base = {"as_of": _stamp(), "vix": vix, "vix_date": vd if vix is not None else None, "vix_on": VIX_ON,
            "hold_sessions": HOLD_SESSIONS, "n_picks": N_PICKS, "measured": MEASURED, "picks": [], "refused": []}
    if vix is None:
        out = {**base, "ok": False, "regime_on": False, "blocked": vd}
        snapshots.write(OUT, out)
        return out
    on = vix > VIX_ON
    con = _con()
    last = _last_issue(con) if con is not None else None
    if con is not None:
        con.close()
    due = True
    if last:
        try:
            due = (now.date() - datetime.strptime(last[:10], "%Y-%m-%d").date()).days >= ISSUE_GAP_SESSIONS + 2
        except ValueError:
            due = True
    if not on:
        out = {**base, "ok": True, "regime_on": False, "issued": False,
               "note": f"VIX {vix:.1f} on {vd}: below {VIX_ON:.0f}, the book is off. Out of the regime the same "
                       f"trade measured flat to negative; nothing is issued."}
        snapshots.write(OUT, out)
        _feed_ledger(out, now)
        return out
    if not due:
        out = {**base, "ok": True, "regime_on": True, "issued": False,
               "note": f"VIX {vix:.1f}: the regime is ON; last cohort issued {last[:10]}, next after "
                       f"{ISSUE_GAP_SESSIONS} sessions."}
        snapshots.write(OUT, out)
        _feed_ledger(out, now)
        return out
    names, err = universe()
    if err:
        out = {**base, "ok": False, "regime_on": True, "blocked": err}
        snapshots.write(OUT, out)
        return out
    px = _prices(names)
    rows = []
    for tk in names:
        d = px.get(tk)
        if d is None:
            continue
        d = d.dropna(subset=["close"])
        comp = composite(d)
        dv = (d["close"] * d["volume"]).dropna().tail(20)
        rows.append({"ticker": tk, "close": float(d["close"].iloc[-1]) if len(d) else None,
                     "adv20": float(dv.median()) if len(dv) >= 10 else None, **(comp or {"ret1m": None})})
    picks, refused = select(rows)
    out = {**base, "ok": True, "regime_on": True, "issued": bool(picks), "cohort_n": len(rows),
           "n_ranked": len(picks) + sum(1 for r in refused if "ranked" in r["why"]),
           "picks": picks, "refused": sorted(refused, key=lambda r: r.get("score") or 9)[:60],
           "note": f"VIX {vix:.1f} on {vd}: the regime is ON. The {len(picks)} biggest losers of "
                   f"{len(rows)} names by the reversal composite, for a {HOLD_SESSIONS}-session hold."}
    snapshots.write(OUT, out)
    try:
        out["ledger_result"] = book(picks, px, now=now, vix=vix)
        if picks:
            _notify(f"Stress book ON: VIX {vix:.1f}, cohort issued (paper)",
                    f"{len(picks)} biggest losers, {HOLD_SESSIONS}-session hold; top: " + ", ".join(p["ticker"] for p in picks[:5]))
    except Exception as e:                                    # noqa: BLE001
        out["ledger_error"] = f"{type(e).__name__}: {e}"
    return out


def _feed_ledger(out, now):
    try:
        out["ledger_result"] = mark(now=now)
    except Exception as e:                                    # noqa: BLE001
        out["ledger_error"] = f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------ ledger ---

def _con():
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS picks (
        id INTEGER PRIMARY KEY, issued TEXT NOT NULL, ticker TEXT NOT NULL, vix REAL,
        score REAL, rank INTEGER, cohort INTEGER, ret1m REAL, ret1w REAL,
        entry_date TEXT, entry REAL, spy_entry REAL, exit_due TEXT,
        status TEXT NOT NULL DEFAULT 'pending', cur REAL, spy_cur REAL,
        pnl_pct REAL, rel_pct REAL, updated TEXT, closed TEXT,
        UNIQUE(ticker, issued))""")
    return con


def book(picks, px, now=None, vix=None):
    """Record new picks once (one cohort per issue stamp); fill pending at the next open;
    mark and close the rest. Same contract as swing_stock.book."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    now = now or _now()
    today = now.date().isoformat()
    stamp = _stamp()
    added = 0
    for p in picks:
        cur = con.execute("SELECT 1 FROM picks WHERE ticker=? AND substr(issued,1,10)=?",
                          (p["ticker"], stamp[:10])).fetchone()
        if cur:
            continue
        con.execute("INSERT INTO picks (issued, ticker, vix, score, rank, cohort, ret1m, ret1w, status) "
                    "VALUES (?,?,?,?,?,?,?,?,'pending')",
                    (stamp, p["ticker"], vix, p.get("score"), p.get("rank"), p.get("cohort"),
                     p.get("ret1m"), p.get("ret1w")))
        added += 1
    spy = px.get("SPY")
    filled = marked = closed = 0
    for r in con.execute("SELECT * FROM picks WHERE status IN ('pending','open')").fetchall():
        r = dict(r)
        d = px.get(r["ticker"])
        if d is None or spy is None:
            continue
        if r["status"] == "pending":
            after = d[d.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            s_after = spy[spy.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            if not len(after) or not len(s_after):
                continue
            ed = after.index[0].strftime("%Y-%m-%d")
            due = (after.index[0] + timedelta(days=HOLD_DAYS)).strftime("%Y-%m-%d")
            con.execute("UPDATE picks SET status='open', entry_date=?, entry=?, spy_entry=?, exit_due=? WHERE id=?",
                        (ed, float(after["open"].iloc[0]), float(s_after["open"].iloc[0]), due, r["id"]))
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
        con.execute("UPDATE picks SET cur=?, spy_cur=?, pnl_pct=?, rel_pct=?, updated=?, status=?, closed=? WHERE id=?",
                    (cur, scur, round(pnl, 2), round(rel, 2), stamp, "closed" if done else "open",
                     stamp if done else None, r["id"]))
        marked += 1
        closed += int(done)
    con.commit()
    con.close()
    return {"ok": True, "added": added, "filled": filled, "marked": marked, "closed": closed}


def mark(now=None):
    """Fill pending picks and re-mark open ones without rebuilding a cohort."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    names = [r[0] for r in con.execute("SELECT DISTINCT ticker FROM picks WHERE status IN ('pending','open')")]
    con.close()
    if not names:
        return {"ok": True, "added": 0, "filled": 0, "marked": 0, "closed": 0}
    return book([], _prices(names), now=now)


def ledger(limit=120):
    """Open and closed picks for the panel, plus a summary by cohort. Never raises."""
    con = _con()
    if con is None:
        return {"open": [], "closed": [], "summary": {"n": 0}}
    rows = [dict(r) for r in con.execute("SELECT * FROM picks ORDER BY issued DESC, rank ASC LIMIT ?", (limit,))]
    con.close()
    op = [r for r in rows if r["status"] in ("open", "pending")]
    cl = [r for r in rows if r["status"] == "closed"]
    sc = [r for r in cl if r["rel_pct"] is not None]
    summary = {"n": len(cl), "n_open": len(op), "cohorts": len({r["issued"][:10] for r in rows}),
               "hit_rate": round(100 * sum(1 for r in sc if r["rel_pct"] > 0) / len(sc), 0) if sc else None,
               "avg_rel_pct": round(sum(r["rel_pct"] for r in sc) / len(sc), 2) if sc else None,
               "avg_pnl_pct": round(sum(r["pnl_pct"] for r in sc) / len(sc), 2) if sc else None}
    return {"open": op, "closed": cl, "summary": summary}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str)[:3000])
