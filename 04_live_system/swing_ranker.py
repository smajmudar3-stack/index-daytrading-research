"""swing_ranker.py — the swing stock ranker: every name that reported in the last quarter,
ranked on the three inputs that measured positive in every time split at a four-week hold,
the top 25 issued weekly as a cohort in SHARES and held 21 sessions. Paper, with a ledger.
RECORDS; PLACES NOTHING.

WHY THIS EXISTS. The weekly OPTIONS book refuses a card without a measured basis and most
weeks issues nothing, which is correct for options (a 14-DTE vertical costs 8-15% of its
risk in bid-ask) and useless as a source of swing ideas. Sholo asked for the swing to
produce: rank undervalued names on everything that moves a stock, weighted by how much it
moves THAT stock. Both halves were measured before this was built:

  * "everything that moves a stock": 68 factors, 02_findings/signal_accuracy.md. At four
    weeks the top decile of any single factor beats SPY 47-49% of the time. Three inputs
    were positive in all three splits at BOTH four and thirteen weeks: earnings surprise,
    residual momentum (the name's own 12-1 return with the market stripped out) and 12-1
    momentum. Value (FCF and buyback yield) was positive at 1-4 weeks but needs statements
    the live loop does not fetch; it stays in the quarterly study.
  * "weighted by how much it moves that stock": 05_studies/per_name_weights_test.py fit
    each name's own weights on its own past. IC +0.015 against +0.034 for equal weights;
    the per-name sign agreed with the pooled sign on 36-65% of names. Per-name weights are
    that name's past accidents. Equal rank weights are used; the name's three values are
    printed so the reader can see what moved it.

THE RULE, measured on 643,687 name-weeks 2018-2026 (signal_accuracy.py follow-ups):
    names that reported in the last 63 sessions; composite = mean rank of SUE, residual
    momentum, 12-1 momentum; top 25; 21-session hold:
        +0.84% over SPY per hold, hit rate 0.49, wins 1.24x losses, 54% of cohorts
        positive, 42% turnover, +9.3%/yr net of 15 bp a side; splits +0.87 / +0.79 / +0.87.
    At 63 sessions the same rule is +3.71% per hold (t 2.4), 75% of cohorts positive, all
    splits positive. SUE alone is larger on average and zero in 2022-23; this one is the
    smaller, steadier rule.

WHAT IT DOES, weekly:
  1. reads the quarterly stock book's snapshot (every ranked reporter with its SUE, close
     and volume: the vendor calls were already spent there);
  2. fetches 14 months of prices in batches of 120, computes residual momentum and 12-1
     momentum, ranks the composite, issues the top N_PICKS as this week's cohort;
  3. the LEDGER fills each pick at the NEXT open, marks against SPY, closes after
     HOLD_SESSIONS; a desktop ping says a cohort was issued. It is context on the page;
     only panels/today.answer states an action.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "swing_ranker_snapshot.json"
DB = paths.state("swing_ranker.db")
STOCK_SNAPSHOT = "swing_stock_snapshot.json"

N_PICKS = 25
HOLD_SESSIONS = 21
HOLD_DAYS = 30
ISSUE_GAP_DAYS = 6          # one cohort a week
MIN_PRICE = 10.0
MIN_ADV = 10e6
MEASURED = {"per_hold_pct": 0.84, "hit": 0.487, "payoff": 1.24, "cohort_hit": 0.54, "net_pct_yr": 9.3,
            "splits": "+0.87 / +0.79 / +0.87", "source": "02_findings/signal_accuracy.md"}


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


def _notify(title, msg):
    """Desktop ping, best effort; the ledger is the record."""
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
        return True
    except Exception:                                         # noqa: BLE001
        return False


# ------------------------------------------------------------------ inputs ---

def reporters():
    """[{ticker, sue, close, adv20, report_date}] from the stock book's snapshot: every name it
    ranked (picks and refused-on-rank alike). ([], why) if the book has not run."""
    p, st = snapshots.read(STOCK_SNAPSHOT)
    if p is None or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        return [], f"stock book snapshot {st}"
    if not p.get("ok"):
        return [], p.get("blocked") or "stock book did not run"
    rows = []
    for r in (p.get("picks") or []) + (p.get("refused") or []):
        if r.get("sue") is None or r.get("close") is None or r.get("adv20") is None:
            continue
        rows.append({"ticker": r["ticker"], "sue": r["sue"], "close": r["close"], "adv20": r["adv20"],
                     "report_date": r.get("report_date")})
    return rows, (None if rows else "the stock book ranked no names")


def _prices(tickers, period="14mo"):
    """{ticker: DataFrame[open, close, volume]}, batched by 120. Never raises."""
    try:
        import yfinance as yf
    except Exception:                                         # noqa: BLE001
        return {}
    names = sorted(set(tickers) | {"SPY"})
    out = {}
    for i in range(0, len(names), 120):
        chunk = names[i:i + 120]
        try:
            raw = yf.download(chunk, period=period, interval="1d", progress=False, auto_adjust=True,
                              group_by="ticker", threads=True)
        except Exception:                                     # noqa: BLE001
            continue
        for tk in chunk:
            try:
                d = (raw[tk] if len(chunk) > 1 else raw).dropna(how="all").rename(columns=str.lower)
                if len(d) >= 5 and "close" in d:
                    out[tk] = d
            except (KeyError, TypeError, AttributeError):
                continue
    return out


def momentum(d, spy):
    """(mom12_1, resid_mom) for one name from ~14 months of closes and SPY's. None if short."""
    c = d["close"].dropna()
    s = spy["close"].dropna().reindex(c.index).ffill()
    if len(c) < 260:
        return None
    mom = float(c.iloc[-22] / c.iloc[-253] - 1)
    r = c.pct_change().iloc[-252:]
    rm = s.pct_change().reindex(r.index).iloc[-252:]
    ok = r.notna() & rm.notna()
    r, rm = r[ok], rm[ok]
    if len(r) < 200 or rm.var() == 0:
        return None
    beta = float(r.cov(rm) / rm.var())
    resid = r - beta * rm
    win = resid.iloc[:-21]                                     # months 2..12 of residuals
    sd = float(win.std())
    return {"mom12_1": mom, "resid_mom": float(win.sum() / (sd * (len(win) ** 0.5))) if sd > 0 else 0.0, "beta": beta}


def select(rows, n_picks=N_PICKS):
    """rows: [{ticker, sue, mom12_1, resid_mom, close, adv20}]. (picks, refused), ranked. Pure."""
    ok, refused = [], []
    for r in rows:
        if r.get("mom12_1") is None or r.get("resid_mom") is None:
            refused.append({**r, "why": "price history shorter than a year"})
        elif r.get("close") is None or r["close"] < MIN_PRICE:
            refused.append({**r, "why": f"price below ${MIN_PRICE:.0f}"})
        elif r.get("adv20") is None or r["adv20"] < MIN_ADV:
            refused.append({**r, "why": "20-day dollar volume below $10m"})
        else:
            ok.append(r)
    n = len(ok)
    if n == 0:
        return [], refused
    for k in ("sue", "resid_mom", "mom12_1"):
        order = sorted(range(n), key=lambda i: ok[i][k])
        for rank, i in enumerate(order):
            ok[i][f"rk_{k}"] = (rank + 1) / n
    for r in ok:
        r["score"] = round((r["rk_sue"] + r["rk_resid_mom"] + r["rk_mom12_1"]) / 3, 4)
    ok.sort(key=lambda r: -r["score"])
    for i, r in enumerate(ok):
        r["rank"] = i + 1
        r["cohort"] = n
    picks = ok[:n_picks]
    for r in ok[n_picks:]:
        refused.append({**r, "why": f"ranked {r['rank']} of {n} on surprise + residual momentum + 12-1; the cohort is the top {n_picks}"})
    return picks, refused


# --------------------------------------------------------------------- run ---

def _last_issue(con):
    r = con.execute("SELECT MAX(issued) FROM picks").fetchone()
    return r[0] if r and r[0] else None


def run(now=None):
    """Issue this week's cohort if due; always feed the ledger. Never raises."""
    now = now or _now()
    base = {"as_of": _stamp(), "hold_sessions": HOLD_SESSIONS, "n_picks": N_PICKS, "measured": MEASURED,
            "picks": [], "refused": []}
    con = _con()
    last = _last_issue(con) if con is not None else None
    if con is not None:
        con.close()
    due = True
    if last:
        try:
            due = (now.date() - datetime.strptime(last[:10], "%Y-%m-%d").date()).days >= ISSUE_GAP_DAYS
        except ValueError:
            due = True
    if not due:
        out = {**base, "ok": True, "issued": False, "last_issued": last[:10],
               "note": f"this week's cohort was issued {last[:10]}; the next is due after {ISSUE_GAP_DAYS} days"}
        snapshots.write(OUT, out)
        _feed(out, now)
        return out
    rows, err = reporters()
    if err:
        out = {**base, "ok": False, "issued": False, "blocked": err}
        snapshots.write(OUT, out)
        return out
    px = _prices([r["ticker"] for r in rows])
    spy = px.get("SPY")
    for r in rows:
        d = px.get(r["ticker"])
        m = momentum(d, spy) if (d is not None and spy is not None) else None
        r.update(m or {"mom12_1": None, "resid_mom": None})
        if d is not None and len(d):
            r["spot"] = float(d["close"].dropna().iloc[-1]) if len(d["close"].dropna()) else None
    picks, refused = select(rows)
    out = {**base, "ok": True, "issued": bool(picks), "cohort_n": len(rows),
           "n_ranked": len(picks) + sum(1 for r in refused if "ranked" in r["why"]),
           "picks": picks, "refused": sorted(refused, key=lambda r: -(r.get("score") or -9))[:60],
           "note": f"{len(picks)} of {len(rows)} names that reported in the last quarter, ranked on surprise + "
                   f"residual momentum + 12-1 momentum (equal rank weights), for a {HOLD_SESSIONS}-session hold in shares."}
    snapshots.write(OUT, out)
    try:
        out["ledger_result"] = book(picks, px, now=now)
        if picks:
            _notify("Swing ranker: new cohort issued (paper)",
                    f"{len(picks)} names, {HOLD_SESSIONS}-session hold; top: " + ", ".join(p["ticker"] for p in picks[:5]))
    except Exception as e:                                    # noqa: BLE001
        out["ledger_error"] = f"{type(e).__name__}: {e}"
    return out


def _feed(out, now):
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
        id INTEGER PRIMARY KEY, issued TEXT NOT NULL, ticker TEXT NOT NULL,
        score REAL, rank INTEGER, cohort INTEGER, sue REAL, resid_mom REAL, mom12_1 REAL,
        entry_date TEXT, entry REAL, spy_entry REAL, exit_due TEXT,
        status TEXT NOT NULL DEFAULT 'pending', cur REAL, spy_cur REAL,
        pnl_pct REAL, rel_pct REAL, updated TEXT, closed TEXT,
        UNIQUE(ticker, issued))""")
    return con


def book(picks, px, now=None):
    """Record new picks once per cohort; fill pending at the next open; mark and close."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    now = now or _now()
    today = now.date().isoformat()
    stamp = _stamp()
    added = 0
    for p in picks:
        if con.execute("SELECT 1 FROM picks WHERE ticker=? AND substr(issued,1,10)=?", (p["ticker"], stamp[:10])).fetchone():
            continue
        con.execute("INSERT INTO picks (issued, ticker, score, rank, cohort, sue, resid_mom, mom12_1, status) "
                    "VALUES (?,?,?,?,?,?,?,?,'pending')",
                    (stamp, p["ticker"], p.get("score"), p.get("rank"), p.get("cohort"), p.get("sue"),
                     p.get("resid_mom"), p.get("mom12_1")))
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
            r.update(status="open", entry=float(after["open"].iloc[0]), spy_entry=float(s_after["open"].iloc[0]), exit_due=due)
        dc, sc = d["close"].dropna(), spy["close"].dropna()
        if not len(dc) or not len(sc):
            continue
        cur, scur = float(dc.iloc[-1]), float(sc.iloc[-1])
        pnl = (cur / r["entry"] - 1) * 100
        rel = pnl - (scur / r["spy_entry"] - 1) * 100
        done = today >= r["exit_due"]
        con.execute("UPDATE picks SET cur=?, spy_cur=?, pnl_pct=?, rel_pct=?, updated=?, status=?, closed=? WHERE id=?",
                    (cur, scur, round(pnl, 2), round(rel, 2), stamp, "closed" if done else "open", stamp if done else None, r["id"]))
        marked += 1
        closed += int(done)
    con.commit()
    con.close()
    return {"ok": True, "added": added, "filled": filled, "marked": marked, "closed": closed}


def mark(now=None):
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    names = [r[0] for r in con.execute("SELECT DISTINCT ticker FROM picks WHERE status IN ('pending','open')")]
    con.close()
    if not names:
        return {"ok": True, "added": 0, "filled": 0, "marked": 0, "closed": 0}
    return book([], _prices(names, period="4mo"), now=now)


def ledger(limit=120):
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
