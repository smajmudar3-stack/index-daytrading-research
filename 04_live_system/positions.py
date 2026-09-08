"""positions.py — live position manager for YOUR actual trades.

You tell it "I bought a call/put" (strike, premium, qty) from a periscope; it tracks the position
against the live gamma levels + flow every scan cycle and PINGS you when to SELL HALF (hit target),
SELL (stop/invalidated), or ADD (confirmed continuation). On close it records the REAL P&L (from your
entry/exit premium) into the P&L log — so the tracker reflects your actual fills, not estimates.

Management rules (level-based, from the periscope):
  CALL:  target = call wall (take half there) · stop = lose the gamma flip, OR signal flips bearish,
         OR price drops >0.35% under entry · add = clean break ABOVE the call wall with bullish flow.
  PUT:   mirror — target = put wall · stop = reclaim the flip / signal flips bullish · add = break
         below the put wall with bearish flow.

Every function that writes to the book returns {"ok": ...} and logs on failure. A close that does not
land must never look like a close that did: this file IS the record of your real fills.
"""
import json
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db, paths

log = logging.getLogger("positions")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand. The old os.path.join(HERE, "data", ...) with a bare
# sqlite3 handle gave no WAL and a 5-second lock while scan_all wrote the same file.
DB = paths.state("positions.db")

# Columns added after the table shipped. Applied by comparing against PRAGMA table_info rather than
# running ALTER inside a try/except that swallowed everything: that pattern hid real schema errors
# behind the same silence as "column already exists".
_MIGRATIONS = [("cur_under", "REAL"), ("cur_move", "REAL"), ("cur_action", "TEXT"),
               ("cur_reason", "TEXT"), ("cur_optpnl", "REAL"), ("updated", "TEXT")]


def _con():
    try:
        c = db.connect(DB)
    except sqlite3.Error as e:
        log.error("positions: cannot open the position book at %s: %s", DB, e)
        raise
    c.execute("""CREATE TABLE IF NOT EXISTS pos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, sym TEXT, dir TEXT, strike REAL, entry_prem REAL,
        qty INTEGER, entry_under REAL, entry_time TEXT, status TEXT DEFAULT 'open',
        exit_prem REAL, exit_under REAL, exit_time TEXT, pnl_pct REAL, pnl_dollar REAL,
        half_sold INTEGER DEFAULT 0, last_action TEXT, note TEXT)""")
    have = {r[1] for r in c.execute("PRAGMA table_info(pos)").fetchall()}
    for col, typ in _MIGRATIONS:
        if col not in have:
            c.execute(f"ALTER TABLE pos ADD COLUMN {col} {typ}")
    c.commit()
    c.row_factory = sqlite3.Row
    return c


def _est_optpnl(p, spot):
    """Rough live option P&L % via leverage (0DTE delta~0.55 on the entry premium). Estimate, capped."""
    if not (p["entry_under"] and p["entry_prem"]):
        return None
    prem_frac = (p["entry_prem"] / 100) / p["entry_under"]     # premium as fraction of underlying
    if prem_frac <= 0:
        return None
    lev = 0.55 / prem_frac
    move = (spot / p["entry_under"] - 1) * (1 if p["dir"] == "call" else -1)
    return round(max(-100.0, min(600.0, lev * move * 100)), 0)


def add(sym, dir, strike, entry_prem, qty=1, under=None):
    """Open a tracked position. Returns {"ok": True, "id": n} or {"ok": False, "reason": ...}."""
    c = _con()
    try:
        cur = c.execute("""INSERT INTO pos(sym,dir,strike,entry_prem,qty,entry_under,entry_time,status)
            VALUES(?,?,?,?,?,?,?,'open')""",
                        (sym, dir, float(strike), float(entry_prem), int(qty), under,
                         datetime.now(ET).isoformat(timespec="seconds")))
        c.commit()
        pid = cur.lastrowid
    except (sqlite3.Error, ValueError, TypeError) as e:
        # A position that failed to record is one you are holding and the system does not know about.
        log.error("positions.add: %s %s %s NOT recorded: %s", sym, dir, strike, e)
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        c.close()
    return {"ok": True, "id": pid}


def list_open():
    c = _con()
    try:
        r = c.execute("SELECT * FROM pos WHERE status='open' ORDER BY id DESC").fetchall()
    finally:
        c.close()
    return [dict(x) for x in r]


def list_closed(n=20):
    c = _con()
    try:
        r = c.execute("SELECT * FROM pos WHERE status='closed' ORDER BY exit_time DESC LIMIT ?", (n,)).fetchall()
    finally:
        c.close()
    return [dict(x) for x in r]


def mark_half(pid):
    c = _con()
    try:
        cur = c.execute("UPDATE pos SET half_sold=1 WHERE id=?", (pid,))
        c.commit()
    except sqlite3.Error as e:
        log.error("positions.mark_half: #%s not updated: %s", pid, e)
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        c.close()
    if not cur.rowcount:
        log.warning("positions.mark_half: no position #%s", pid)
        return {"ok": False, "reason": f"no position #{pid}"}
    return {"ok": True, "id": pid}


def close(pid, exit_prem, under=None):
    """Record the real exit. This is the fill that turns the P&L log into measurement, so a close that
    does not land returns ok=False and logs — it used to return None and look exactly like success."""
    c = _con()
    try:
        p = c.execute("SELECT * FROM pos WHERE id=?", (pid,)).fetchone()
        if not p:
            log.warning("positions.close: no position #%s — nothing was closed", pid)
            return {"ok": False, "reason": f"no position #{pid}"}
        if p["status"] == "closed":
            log.warning("positions.close: #%s is already closed — left as it was", pid)
            return {"ok": False, "reason": f"position #{pid} is already closed"}
        ep = float(exit_prem)
        pnl_pct = (ep / p["entry_prem"] - 1) * 100 if p["entry_prem"] else 0
        pnl_dollar = (ep - p["entry_prem"]) * p["qty"]      # per-contract premium × qty (premium already $/contract)
        c.execute("""UPDATE pos SET status='closed', exit_prem=?, exit_under=?, exit_time=?, pnl_pct=?, pnl_dollar=?
            WHERE id=?""", (ep, under, datetime.now(ET).isoformat(timespec="seconds"),
                            round(pnl_pct, 1), round(pnl_dollar), pid))
        c.commit()
    except (sqlite3.Error, ValueError, TypeError) as e:
        log.error("positions.close: #%s NOT closed (exit %s): %s", pid, exit_prem, e)
        return {"ok": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        c.close()
    return {"ok": True, "id": pid, "pnl_pct": round(pnl_pct, 1), "pnl_dollar": round(pnl_dollar)}


def _peri(sym):
    """The live gamma periscope snapshot for one symbol, or {} when it has not been written yet."""
    path = paths.state(f"periscope_{sym}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}          # first run, or the periscope has never been generated for this symbol
    except (OSError, json.JSONDecodeError) as e:
        # A corrupt snapshot is not an empty one: it means the writer failed halfway.
        log.warning("positions: periscope snapshot %s is unreadable (%s)", path, e)
        return {}


def _spot(yfsym):
    import yfinance as yf
    return float(yf.Ticker(yfsym).fast_info["lastPrice"])


def _lvl(x):
    """Format a gamma level for a message, or say it is missing. A None level used to reach a
    '{flip:.0f}' format string and raise TypeError out of manage(), which stopped every remaining
    position from being evaluated at all."""
    return f"{x:.0f}" if isinstance(x, (int, float)) else "n/a"


def evaluate(p, spot, peri):
    """Return (action, reason) for an open position given live spot + periscope. action in
    HOLD / SELL_HALF / SELL / ADD."""
    cw = peri.get("call_wall"); pw = peri.get("put_wall")
    flip = (peri.get("uw") or {}).get("uw_flip") or peri.get("gamma_flip")
    sig = peri.get("signal", "")
    flow = (peri.get("uw") or {}).get("overall") or ((peri.get("uw") or {}).get("intraday") or {}).get("bias")
    entry = p["entry_under"] or spot
    move = (spot / entry - 1) * 100
    if p["dir"] == "call":
        if flip and spot < flip:
            return "SELL", f"lost the gamma flip ({_lvl(flip)}) — call thesis invalidated"
        if "PUT" in sig or "bearish" in str(sig).lower():
            return "SELL", "signal flipped bearish — cut it"
        if move < -0.35:
            return "SELL", f"−{abs(move):.1f}% under entry — stop hit"
        if cw and spot >= cw * 0.999 and not p["half_sold"]:
            return "SELL_HALF", f"hit the call wall {_lvl(cw)} (target) — bank half, trail the rest"
        if cw and spot > cw and flow == "bullish":
            return "ADD", f"cleanly broke the call wall {_lvl(cw)} with bullish flow — runner can add"
        return "HOLD", (f"+{move:.2f}% from entry — holding toward {_lvl(cw)}" if move >= 0
                        else f"{move:.2f}% — watching the flip {_lvl(flip)}")
    else:  # put
        if flip and spot > flip:
            return "SELL", f"reclaimed the gamma flip ({_lvl(flip)}) — put thesis invalidated"
        if "CALL" in sig or "bullish" in str(sig).lower():
            return "SELL", "signal flipped bullish — cut it"
        if move > 0.35:
            return "SELL", f"+{move:.1f}% above entry — stop hit"
        if pw and spot <= pw * 1.001 and not p["half_sold"]:
            return "SELL_HALF", f"hit the put wall {_lvl(pw)} (target) — bank half, trail the rest"
        if pw and spot < pw and flow == "bearish":
            return "ADD", f"broke the put wall {_lvl(pw)} with bearish flow — runner can add"
        return "HOLD", f"{-move:.2f}% in your favor — holding toward {_lvl(pw)}"


def _notify(title, msg):
    """Desktop ping. Best-effort by design: the book is the record, a notification is a courtesy, and
    osascript simply does not exist off macOS. Logged at debug rather than warning so a Linux box does
    not print a scary line every cycle, but never swallowed silently — the return value says what
    happened."""
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
        return True
    except (OSError, ValueError) as e:
        log.debug("positions: desktop notification unavailable (%s: %s)", type(e).__name__, e)
        return False
    except Exception as e:                       # subprocess.TimeoutExpired and anything else
        log.debug("positions: desktop notification failed (%s: %s)", type(e).__name__, e)
        return False


YF = {"SPX": "^SPX", "NDX": "^NDX", "SPY": "SPY", "QQQ": "QQQ"}


def manage():
    """Evaluate every open position; ping when the action CHANGES to an actionable one.

    Returns a summary. An open position that could not be evaluated is counted and logged: it used to
    `continue` in silence, so a dead quote feed looked exactly like a quiet market."""
    summary = {"evaluated": 0, "skipped": [], "errors": []}
    try:
        openp = list_open()
    except sqlite3.Error as e:
        # No book, no management: every open position goes unwatched this cycle. scan_all catches
        # everything, so raising here would be silent; this at least reaches the log and the caller.
        log.error("positions.manage: the position book could not be read (%s) — NO position was "
                  "evaluated this cycle", e)
        summary["errors"].append({"error": f"{type(e).__name__}: {e}"})
        return summary
    for p in openp:
        pid = p["id"]
        peri = _peri(p["sym"])
        if not peri.get("ok"):
            why = "periscope snapshot missing or not ok"
            log.warning("positions.manage: #%s %s not evaluated — %s", pid, p["sym"], why)
            summary["skipped"].append({"id": pid, "sym": p["sym"], "why": why})
            continue
        try:
            spot = _spot(YF.get(p["sym"], "^" + p["sym"]))
        except Exception as e:
            log.warning("positions.manage: #%s %s not evaluated — no live quote (%s: %s)",
                        pid, p["sym"], type(e).__name__, e)
            summary["skipped"].append({"id": pid, "sym": p["sym"],
                                       "why": f"no live quote: {type(e).__name__}"})
            continue
        try:
            action, reason = evaluate(p, spot, peri)
        except Exception as e:
            log.error("positions.manage: #%s %s could not be evaluated: %s: %s",
                      pid, p["sym"], type(e).__name__, e)
            summary["errors"].append({"id": pid, "sym": p["sym"], "error": f"{type(e).__name__}: {e}"})
            continue
        move = (spot / (p["entry_under"] or spot) - 1) * 100
        optpnl = _est_optpnl(p, spot)
        # Write FIRST, ping second. The other order pinged you to SELL and then, if the write failed,
        # left last_action unchanged so the same ping fired again on every cycle.
        c = _con()
        try:
            c.execute("""UPDATE pos SET last_action=?, cur_action=?, cur_reason=?, cur_under=?, cur_move=?,
                cur_optpnl=?, updated=? WHERE id=?""",
                      (action, action, reason, round(spot, 2), round(move, 2), optpnl,
                       datetime.now(ET).isoformat(timespec="seconds"), pid))
            c.commit()
        except sqlite3.Error as e:
            log.error("positions.manage: #%s %s evaluated as %s but NOT saved: %s", pid, p["sym"], action, e)
            summary["errors"].append({"id": pid, "sym": p["sym"], "error": f"not saved: {e}"})
            continue
        finally:
            c.close()
        summary["evaluated"] += 1
        # ping on a NEW actionable transition
        if action != (p.get("last_action") or "") and action in ("SELL", "SELL_HALF", "ADD"):
            emoji = {"SELL": "🔴 SELL", "SELL_HALF": "🟡 SELL HALF", "ADD": "🟢 ADD"}[action]
            _notify(f"{emoji} {p['sym']} {p['strike']:.0f}{p['dir'][0].upper()}",
                    f"{reason}. (entry ${p['entry_prem']:.0f}, est {optpnl:+.0f}%)" if optpnl is not None
                    else f"{reason}.")
    return summary


def pnl_summary():
    c = _con()
    try:
        rows = c.execute("SELECT * FROM pos WHERE status='closed'").fetchall()
    finally:
        c.close()
    if not rows:
        return {"n": 0}
    tot = sum(r["pnl_dollar"] or 0 for r in rows)
    wins = sum(1 for r in rows if (r["pnl_dollar"] or 0) > 0)
    return {"n": len(rows), "win": round(wins / len(rows) * 100), "total_dollar": round(tot),
            "avg_pct": round(sum(r["pnl_pct"] or 0 for r in rows) / len(rows), 1)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    s = manage()
    print("open:", len(list_open()), "| closed:", pnl_summary())
    print("managed:", s["evaluated"], "| skipped:", len(s["skipped"]), "| errors:", len(s["errors"]))
    for x in s["skipped"] + s["errors"]:
        print("  ", x)
