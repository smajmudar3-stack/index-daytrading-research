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

# The desk's vocabulary, as regular expressions on word boundaries. "monetized", "stopped
# out", "took profit", "went long", "entered ... put spread" all appeared in the first two
# weeks of notes and none matched the first draft's substring lists.
_CLOSE_RE = re.compile(r"\b(closed|closes?|exit(?:ed)?|sold (?:all|out|the)|took off|unwound|flat|stopped out|covered|monetiz\w*|took profits?)\b")
_REDUCE_RE = re.compile(r"\b(reduced|trimmed|cut|lightened|scaled out|sold)\b")
_ADD_RE = re.compile(r"\b(added|increased|bought more|scaled in|pressed|to full size|full size)\b")
_HOLD_RE = re.compile(r"\b(kept|holding|held|still (?:long|short)|no change|staying)\b")
_HEDGE_RE = re.compile(r"\b(protect\w*|hedge[sd]?|hedging|insurance|collar|cover the|brace|against (?:the |our )?(?:existing )?(?:long|short|position))\b")
_BEAR_RE = re.compile(r"\b(put debit|put spreads?|bought (?:the )?puts?|long puts?|puts|call credit|sold calls?|short(?:ed)?|bearish|went short|downside)\b")
_BULL_RE = re.compile(r"\b(call debit|call spreads?|bought (?:the )?calls?|long calls?|calls|put credit|sold puts?|bought|long|went long|bullish|entered|upside|position from half)\b")


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
    """(direction, kind, is_option) from the desk's own words. direction +1 / -1 / 0 unknown;
    kind in open / add / reduce / close / hold / hedge. `is_option` says the line is about an
    option structure, which matters for the stateful read below: a put spread on a name the
    desk is long is protection, not a short view, and closing it does not close the name."""
    t = f" {(text or '').lower()} "
    is_option = bool(re.search(r"\b(put|puts|call|calls|spread|debit|credit|collar)\b", t))
    kind = "open"
    if _CLOSE_RE.search(t):
        kind = "close"
    elif _REDUCE_RE.search(t):
        kind = "reduce"
    elif _ADD_RE.search(t):
        kind = "add"
    elif _HOLD_RE.search(t):
        kind = "hold"
    if _HEDGE_RE.search(t):
        kind = "hedge"
    direction = 0
    if _BEAR_RE.search(t):
        direction = -1
    if direction == 0 and _BULL_RE.search(t):
        direction = 1
    if kind in ("close", "reduce", "hold", "add") and direction == 0:          # "added 0.5 unit" is a long add
        direction = 1
    return direction, kind, is_option


def desk_state(entries):
    """Walk the desk's own entries for ONE asset in date order and return (state, trail):
    state +1 long / -1 short / 0 flat, trail = what each line did. The rules, each from a
    line in the first two weeks of notes:
      * an option structure AGAINST an open position is a hedge (USO put spreads on a USO
        long): recorded, never mirrored, and closing it does not close the position;
      * a structure in a NEW direction on a flat book opens that direction (IWM put spread =
        short IWM); a structure in the opposite direction to an open position flips it;
      * close / monetize / stopped out / exit on the position itself goes flat;
      * reduce keeps the position; hold with no open position implies one is open (long)."""
    state, trail = 0, []
    for b in entries:
        d, kind, opt = parse_action(b.get("action"))
        before = state
        if kind == "hedge" or (opt and d != 0 and state != 0 and d == -state and kind in ("open", "add")):
            trail.append((b.get("date"), "hedge", state)); continue
        if kind == "close":
            if opt and state != 0 and d == -state:
                trail.append((b.get("date"), "hedge closed", state)); continue
            state = 0
        elif kind in ("open", "add"):
            if d != 0:
                state = d
        elif kind == "hold":
            if state == 0:
                state = d or 1
        trail.append((b.get("date"), kind, state if state != before or kind != "reduce" else state))
    return state, trail


def positions_from(overlay, now=None):
    """Every position the overlay implies right now, by source, plus the stated exclusions.
    Pure; takes the overlay dict. Dates compare against `now`."""
    now = now or _now()
    out, closes, conflicts, skipped = [], [], [], []
    # THEIR BOOK, read statefully per asset: the desk's CURRENT position is what is mirrored
    by_asset = {}
    for b in overlay.get("desk_book") or []:
        if not isinstance(b, dict):
            continue
        asset = str(b.get("asset") or "").upper().strip()
        ts = desk_notes._parse_stamp(b.get("date"))
        if not TICKER_RE.match(asset) or ts is None:
            skipped.append({"source": "desk", "what": asset or "?", "why": "not a tradeable ticker or undated"})
            continue
        if (now.timestamp() - ts) > CALL_WINDOW_DAYS * 86400 * 2:
            continue
        by_asset.setdefault(asset, []).append(b)
    for asset, entries in by_asset.items():
        entries.sort(key=lambda b: b.get("date") or "")
        state, trail = desk_state(entries)
        last = entries[-1]
        if state == 0:
            closes.append({"ticker": asset, "src_date": last.get("date"), "why": last.get("action")})
            skipped.append({"source": "desk", "what": asset, "why": f"the desk is flat: last line {last.get('date', '')[:10]} \"{last.get('action')}\""})
            continue
        opened = next((b for b in reversed(entries) if parse_action(b.get("action"))[1] in ("open", "add")), last)
        out.append({"source": "desk", "ticker": asset, "dir": state, "hold": HOLD_SESSIONS, "src_date": opened.get("date"),
                    "why": f"their book, {len(entries)} lines: latest \"{last.get('action')}\"" + (f" — {last.get('note')}" if last.get("note") else ""),
                    "conviction": None, "horizon": "weeks"})
    # THEIR CALLS: the NEWEST call per instrument wins; an older call the desk has since
    # reversed is superseded, not held beside it (USO long and USO short were both booked once)
    latest = {}
    for c in desk_notes.calls(overlay, within_days=CALL_WINDOW_DAYS):      # newest first
        tk = str(c.get("instrument") or "").upper().strip()
        if not TICKER_RE.match(tk):
            skipped.append({"source": "call", "what": tk or "?", "why": "instrument is not a ticker"})
            continue
        if _HEDGE_RE.search(f" {str(c.get('why') or '').lower()} "):
            skipped.append({"source": "call", "what": tk, "why": f"protection on an existing position, not a view: {str(c.get('why'))[:80]}"})
            continue
        if tk in latest:
            if latest[tk]["direction"] != c.get("direction"):
                skipped.append({"source": "call", "what": tk, "why": f"older call ({str(c.get('date'))[:10]} {c.get('direction')}) superseded by {str(latest[tk].get('date'))[:10]} {latest[tk]['direction']}"})
            continue
        latest[tk] = c
    for tk, c in latest.items():
        d = 1 if c.get("direction") == "long" else -1
        hz = str(c.get("horizon") or "weeks").lower()
        out.append({"source": "call", "ticker": tk, "dir": d, "hold": HORIZON_SESSIONS.get(hz, HOLD_SESSIONS), "src_date": c.get("date"),
                    "why": c.get("why") or "", "conviction": c.get("conviction"), "horizon": hz, "label": c.get("direction")})
    # a call reversed since it was booked closes the older paper position
    for tk, c in latest.items():
        closes.append({"ticker": tk, "source": "call", "keep_dir": 1 if c.get("direction") == "long" else -1,
                       "src_date": c.get("date"), "why": f"superseded by the {str(c.get('date'))[:10]} call: {c.get('direction')}"})
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
        if c.get("source") == "call":
            con.execute("UPDATE positions SET status='closing', close_why=? WHERE source='call' AND ticker=? AND dir<>? AND status IN ('pending','open')",
                        (c.get("why"), c["ticker"], c["keep_dir"]))
        else:
            con.execute("UPDATE positions SET status='closing', close_why=? WHERE source='desk' AND ticker=? AND status IN ('pending','open')",
                        (c.get("why"), c["ticker"]))
    spy = px.get("SPY")
    filled = marked = closed = 0
    for r in con.execute("SELECT * FROM positions WHERE status IN ('pending','open','closing')").fetchall():
        r = dict(r)
        d = px.get(r["ticker"])
        if d is None or spy is None:
            continue
        if r["status"] == "closing" and r["entry"] is None:
            con.execute("UPDATE positions SET status='void', closed=?, updated=? WHERE id=?", (stamp, stamp, r["id"]))
            continue
        if r["status"] == "pending":
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
