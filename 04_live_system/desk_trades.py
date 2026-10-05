"""desk_trades.py — the emails as trades: three paper books built straight from the desk
notes, each with a ledger that fills at the next open and marks against SPY.
RECORDS; PLACES NOTHING.

WHY THIS EXISTS. Sholo (2026-10-05): "the email should be heavily helping with trades, not
just desk notes." Until now the notes did one thing: their themes made a name ELIGIBLE for
the weekly options engine, whose measured-basis and spread gates refuse almost everything,
so a week of notes produced no position. Meanwhile the notes name tickers with a stance in
nearly every theme, the author reports his own trades ("bought Oct 9 146/143 USO put
spread", "reduced GLD 0.25 unit"), and every note argues for something. None of that was
kept as a position or scored. Now it is, three ways:

  THEIR BOOK   every desk_book entry the overlay accumulates (desk_notes.merge_note no
               longer overwrites them). The action text is parsed into a direction and a
               kind; an opening trade in a tradeable asset becomes a paper position in the
               UNDERLYING (an option spread is mirrored as its direction in shares, and the
               card says so); a later close/reduce on the same asset closes it.
  THEIR CALLS  every `implications` entry the ingest now extracts: instrument, direction
               (long / short / avoid), horizon, conviction, the note's own reasoning. Each
               becomes a paper position for the horizon it names (days 5, weeks 21,
               months 63 sessions). "avoid" is booked as a paper short, because the only
               way to score "avoid" is whether the name underperformed.
  THEME BOOK   every theme touched by a note in the last THEME_WINDOW_DAYS: its `favours`
               are longs and its `against` are shorts, netted per ticker; a ticker on both
               sides is a stated conflict and is not traded.

Nothing here is backtested: the notes only exist from 2026-09-17. These ledgers ARE the
measurement — after a quarter they say whether following the desk's names, the desk's own
trades, or the notes' explicit calls beats SPY, separately. Until then the measured books
(ranker, stress, stock book) are the ones with numbers behind them, and the Today page
states these as "from the desk notes, unmeasured".
"""
import json
import re
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import desk_notes
from idt import db as _db
from idt import paths, snapshots

ET = ZoneInfo("America/New_York")
OUT = "desk_trades_snapshot.json"
DB = paths.state("desk_trades.db")

HOLD_SESSIONS = 21
HOLD_DAYS = {5: 8, 21: 30, 63: 92}
HORIZON_SESSIONS = {"days": 5, "weeks": 21, "months": 63}
CALL_WINDOW_DAYS = 14
THEME_WINDOW_DAYS = 14
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,5}$")

_CLOSE = ("closed", "close ", "exit", "sold all", "sold out", "took off", "unwound", "flat", "stopped out", "covered")
_REDUCE = ("reduced", "trimmed", "cut ", "sold ", "took profit", "scaled out", "lightened")
_ADD = ("added", "increased", "bought more", "scaled in", "pressed")
_BEAR = ("put debit", "bought put", "bought the put", "long put", "puts", "call credit", "sold call", "short ", "shorted", "bearish")
_BULL = ("call debit", "bought call", "long call", "calls", "put credit", "sold put", "bought", "long ", "added", "bullish")
_HEDGE = ("protection", "hedge", "insurance", "cover the", "collar")


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


def _notify(title, msg):
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
        return True
    except Exception:                                         # noqa: BLE001
        return False


# ----------------------------------------------------------------- parsing ---

def parse_action(text):
    """(direction, kind) from the desk's own words. direction +1 long / -1 short / 0 unknown;
    kind in open / add / reduce / close / hedge. A hedge on an existing position is recorded
    and never mirrored: a put spread bought to protect a long is not a short view."""
    t = f" {(text or '').lower()} "
    kind = "open"
    if any(w in t for w in _CLOSE):
        kind = "close"
    elif any(w in t for w in _REDUCE):
        kind = "reduce"
    elif any(w in t for w in _ADD):
        kind = "add"
    if any(w in t for w in _HEDGE):
        kind = "hedge"
    direction = 0
    if any(w in t for w in _BEAR):
        direction = -1
    if direction == 0 and any(w in t for w in _BULL):
        direction = 1
    if kind in ("close", "reduce") and direction == 0:
        direction = 1                                          # "sold GLD" closes a long by default
    return direction, kind


def positions_from(overlay, now=None):
    """Every position the overlay implies right now, by source, plus the stated exclusions.
    Pure; takes the overlay dict. Dates compare against `now`."""
    now = now or _now()
    out, closes, conflicts, skipped = [], [], [], []
    # THEIR BOOK
    for b in overlay.get("desk_book") or []:
        if not isinstance(b, dict):
            continue
        asset = str(b.get("asset") or "").upper().strip()
        ts = desk_notes._parse_stamp(b.get("date"))
        if not TICKER_RE.match(asset) or ts is None:
            skipped.append({"source": "desk", "what": asset or "?", "why": "not a tradeable ticker or undated"})
            continue
        if (now.timestamp() - ts) > CALL_WINDOW_DAYS * 86400:
            continue
        d, kind = parse_action(b.get("action"))
        if kind in ("close", "reduce"):
            closes.append({"ticker": asset, "src_date": b.get("date"), "why": b.get("action")})
            continue
        if kind == "hedge" or d == 0:
            skipped.append({"source": "desk", "what": asset, "why": f"{kind}: {b.get('action')}"})
            continue
        out.append({"source": "desk", "ticker": asset, "dir": d, "hold": HOLD_SESSIONS, "src_date": b.get("date"),
                    "why": f"their book: {b.get('action')}" + (f" — {b.get('note')}" if b.get("note") else ""),
                    "conviction": None, "horizon": "weeks"})
    # THEIR CALLS
    for c in desk_notes.calls(overlay, within_days=CALL_WINDOW_DAYS):
        tk = str(c.get("instrument") or "").upper().strip()
        if not TICKER_RE.match(tk):
            skipped.append({"source": "call", "what": tk or "?", "why": "instrument is not a ticker"})
            continue
        d = 1 if c.get("direction") == "long" else -1
        hz = str(c.get("horizon") or "weeks").lower()
        hold = HORIZON_SESSIONS.get(hz, HOLD_SESSIONS)
        out.append({"source": "call", "ticker": tk, "dir": d, "hold": hold, "src_date": c.get("date"),
                    "why": c.get("why") or "", "conviction": c.get("conviction"), "horizon": hz,
                    "label": c.get("direction")})
    # THEME BOOK
    net, why = {}, {}
    for t in desk_notes.themes(overlay):
        ts = desk_notes._parse_stamp(t.get("updated"))
        if ts is None or (now.timestamp() - ts) > THEME_WINDOW_DAYS * 86400:
            continue
        for tk in t.get("favours") or []:
            tk = str(tk).upper()
            net[tk] = net.get(tk, 0) + 1
            why.setdefault(tk, []).append(f"+ {t.get('label')}")
        for tk in t.get("against") or []:
            tk = str(tk).upper()
            net[tk] = net.get(tk, 0) - 1
            why.setdefault(tk, []).append(f"- {t.get('label')}")
    for tk, n in net.items():
        if not TICKER_RE.match(tk):
            continue
        both = any(w.startswith("+") for w in why[tk]) and any(w.startswith("-") for w in why[tk])
        if both:
            conflicts.append({"ticker": tk, "net": n, "themes": why[tk]})
            continue
        out.append({"source": "theme", "ticker": tk, "dir": 1 if n > 0 else -1, "hold": HOLD_SESSIONS, "src_date": None,
                    "why": "; ".join(why[tk]), "conviction": None, "horizon": "weeks"})
    return out, closes, conflicts, skipped


# --------------------------------------------------------------------- run ---

def _prices(tickers, period="4mo"):
    from swing_ranker import _prices as _p
    return _p(tickers, period=period)


def run(now=None):
    now = now or _now()
    ov, st = desk_notes.overlay()
    base = {"as_of": _stamp(), "positions": [], "closes": [], "conflicts": [], "skipped": [], "new": []}
    if ov is None or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        out = {**base, "ok": False, "overlay_as_of": None, "blocked": f"desk-note overlay {st}"}
        snapshots.write(OUT, out)
        return out
    pos, closes, conflicts, skipped = positions_from(ov, now=now)
    names = sorted({p["ticker"] for p in pos} | {c["ticker"] for c in closes})
    px = _prices(names) if names else {}
    unpriced = [t for t in names if t not in px]
    pos = [p for p in pos if p["ticker"] in px]
    out = {**base, "ok": True, "overlay_as_of": ov.get("as_of"), "positions": pos, "closes": closes,
           "conflicts": conflicts, "skipped": skipped + [{"source": "price", "what": t, "why": "no price history"} for t in unpriced],
           "n_desk": sum(p["source"] == "desk" for p in pos), "n_call": sum(p["source"] == "call" for p in pos),
           "n_theme": sum(p["source"] == "theme" for p in pos)}
    try:
        res = book(pos, closes, px, now=now)
        out["ledger_result"] = res
        out["new"] = res.get("new_names") or []
        if out["new"]:
            _notify("Desk notes: new paper positions", f"{len(out['new'])} from the emails: " + ", ".join(out["new"][:6]))
    except Exception as e:                                    # noqa: BLE001
        out["ledger_error"] = f"{type(e).__name__}: {e}"
    snapshots.write(OUT, out)
    return out


# ------------------------------------------------------------------ ledger ---

def _con():
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY, issued TEXT NOT NULL, source TEXT NOT NULL, ticker TEXT NOT NULL, dir INTEGER NOT NULL,
        hold INTEGER, src_date TEXT, why TEXT, conviction TEXT, horizon TEXT,
        entry_date TEXT, entry REAL, spy_entry REAL, exit_due TEXT,
        status TEXT NOT NULL DEFAULT 'pending', cur REAL, spy_cur REAL,
        pnl_pct REAL, rel_pct REAL, updated TEXT, closed TEXT, close_why TEXT)""")
    return con


def book(positions, closes, px, now=None):
    """One open position per (source, ticker, dir); explicit desk closes close desk positions;
    fills at the next open; marks against SPY with the sign of the position; closes at due."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    now = now or _now()
    today = now.date().isoformat()
    stamp = _stamp()
    added, new_names = 0, []
    for p in positions:
        if con.execute("SELECT 1 FROM positions WHERE source=? AND ticker=? AND dir=? AND status IN ('pending','open')",
                       (p["source"], p["ticker"], p["dir"])).fetchone():
            continue
        con.execute("INSERT INTO positions (issued, source, ticker, dir, hold, src_date, why, conviction, horizon, status) "
                    "VALUES (?,?,?,?,?,?,?,?,?,'pending')",
                    (stamp, p["source"], p["ticker"], p["dir"], p["hold"], p.get("src_date"), p.get("why"), p.get("conviction"), p.get("horizon")))
        added += 1
        new_names.append(f"{p['ticker']} {'long' if p['dir'] > 0 else 'short'} ({p['source']})")
    for c in closes:
        con.execute("UPDATE positions SET status='closing', close_why=? WHERE source='desk' AND ticker=? AND status IN ('pending','open')",
                    (c.get("why"), c["ticker"]))
    spy = px.get("SPY")
    filled = marked = closed = 0
    for r in con.execute("SELECT * FROM positions WHERE status IN ('pending','open','closing')").fetchall():
        r = dict(r)
        d = px.get(r["ticker"])
        if d is None or spy is None:
            continue
        if r["status"] == "pending" or (r["status"] == "closing" and r["entry"] is None):
            after = d[d.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            s_after = spy[spy.index.strftime("%Y-%m-%d") > r["issued"][:10]]
            if not len(after) or not len(s_after):
                continue
            ed = after.index[0].strftime("%Y-%m-%d")
            due = (after.index[0] + timedelta(days=HOLD_DAYS.get(r["hold"] or HOLD_SESSIONS, 30))).strftime("%Y-%m-%d")
            con.execute("UPDATE positions SET status=?, entry_date=?, entry=?, spy_entry=?, exit_due=? WHERE id=?",
                        ("open" if r["status"] == "pending" else "closing", ed, float(after["open"].iloc[0]), float(s_after["open"].iloc[0]), due, r["id"]))
            filled += 1
            r.update(entry=float(after["open"].iloc[0]), spy_entry=float(s_after["open"].iloc[0]), exit_due=due)
        dc, sc = d["close"].dropna(), spy["close"].dropna()
        if not len(dc) or not len(sc) or not r.get("entry"):
            continue
        cur, scur = float(dc.iloc[-1]), float(sc.iloc[-1])
        pnl = r["dir"] * (cur / r["entry"] - 1) * 100
        rel = r["dir"] * ((cur / r["entry"] - 1) - (scur / r["spy_entry"] - 1)) * 100
        done = today >= r["exit_due"] or r["status"] == "closing"
        con.execute("UPDATE positions SET cur=?, spy_cur=?, pnl_pct=?, rel_pct=?, updated=?, status=?, closed=? WHERE id=?",
                    (cur, scur, round(pnl, 2), round(rel, 2), stamp, "closed" if done else "open", stamp if done else None, r["id"]))
        marked += 1
        closed += int(done)
    con.commit()
    con.close()
    return {"ok": True, "added": added, "filled": filled, "marked": marked, "closed": closed, "new_names": new_names}


def mark(now=None):
    con = _con()
    if con is None:
        return {"ok": False, "why": "ledger database could not be opened"}
    names = [r[0] for r in con.execute("SELECT DISTINCT ticker FROM positions WHERE status IN ('pending','open','closing')")]
    con.close()
    if not names:
        return {"ok": True, "added": 0, "filled": 0, "marked": 0, "closed": 0}
    return book([], [], _prices(names), now=now)


def ledger(limit=200):
    con = _con()
    if con is None:
        return {"open": [], "closed": [], "summary": {"n": 0}, "by_source": {}}
    rows = [dict(r) for r in con.execute("SELECT * FROM positions ORDER BY issued DESC, id ASC LIMIT ?", (limit,))]
    con.close()
    op = [r for r in rows if r["status"] in ("open", "pending", "closing")]
    cl = [r for r in rows if r["status"] == "closed"]

    def _sum(rs):
        sc = [r for r in rs if r.get("rel_pct") is not None]
        return {"n": len(rs), "hit_rate": round(100 * sum(1 for r in sc if r["rel_pct"] > 0) / len(sc), 0) if sc else None,
                "avg_rel_pct": round(sum(r["rel_pct"] for r in sc) / len(sc), 2) if sc else None,
                "avg_pnl_pct": round(sum(r["pnl_pct"] for r in sc) / len(sc), 2) if sc else None}
    by = {}
    for src in ("desk", "call", "theme"):
        by[src] = {"open": _sum([r for r in op if r["source"] == src]), "closed": _sum([r for r in cl if r["source"] == src])}
    return {"open": op, "closed": cl, "summary": {**_sum(cl), "n_open": len(op)}, "by_source": by}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str)[:3000])
