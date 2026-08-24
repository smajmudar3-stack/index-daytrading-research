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
"""
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "positions.db")


def _con():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS pos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, sym TEXT, dir TEXT, strike REAL, entry_prem REAL,
        qty INTEGER, entry_under REAL, entry_time TEXT, status TEXT DEFAULT 'open',
        exit_prem REAL, exit_under REAL, exit_time TEXT, pnl_pct REAL, pnl_dollar REAL,
        half_sold INTEGER DEFAULT 0, last_action TEXT, note TEXT)""")
    for col, typ in [("cur_under", "REAL"), ("cur_move", "REAL"), ("cur_action", "TEXT"),
                     ("cur_reason", "TEXT"), ("cur_optpnl", "REAL"), ("updated", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE pos ADD COLUMN {col} {typ}")
        except Exception:
            pass
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
    c = _con()
    c.execute("""INSERT INTO pos(sym,dir,strike,entry_prem,qty,entry_under,entry_time,status)
        VALUES(?,?,?,?,?,?,?,'open')""",
              (sym, dir, float(strike), float(entry_prem), int(qty), under,
               datetime.now(ET).isoformat(timespec="seconds")))
    c.commit(); c.close()


def list_open():
    c = _con(); r = c.execute("SELECT * FROM pos WHERE status='open' ORDER BY id DESC").fetchall(); c.close()
    return [dict(x) for x in r]


def list_closed(n=20):
    c = _con(); r = c.execute("SELECT * FROM pos WHERE status='closed' ORDER BY exit_time DESC LIMIT ?", (n,)).fetchall(); c.close()
    return [dict(x) for x in r]


def mark_half(pid):
    c = _con(); c.execute("UPDATE pos SET half_sold=1 WHERE id=?", (pid,)); c.commit(); c.close()


def close(pid, exit_prem, under=None):
    c = _con(); p = c.execute("SELECT * FROM pos WHERE id=?", (pid,)).fetchone()
    if not p:
        c.close(); return
    ep = float(exit_prem)
    pnl_pct = (ep / p["entry_prem"] - 1) * 100 if p["entry_prem"] else 0
    pnl_dollar = (ep - p["entry_prem"]) * p["qty"]      # per-contract premium × qty (premium already $/contract)
    c.execute("""UPDATE pos SET status='closed', exit_prem=?, exit_under=?, exit_time=?, pnl_pct=?, pnl_dollar=?
        WHERE id=?""", (ep, under, datetime.now(ET).isoformat(timespec="seconds"),
                        round(pnl_pct, 1), round(pnl_dollar), pid))
    c.commit(); c.close()


def _peri(sym):
    import json
    try:
        return json.load(open(os.path.join(HERE, "data", f"periscope_{sym}.json")))
    except Exception:
        return {}


def _spot(yfsym):
    import yfinance as yf
    return float(yf.Ticker(yfsym).fast_info["lastPrice"])


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
            return "SELL", f"lost the gamma flip ({flip:.0f}) — call thesis invalidated"
        if "PUT" in sig or "bearish" in str(sig).lower():
            return "SELL", "signal flipped bearish — cut it"
        if move < -0.35:
            return "SELL", f"−{abs(move):.1f}% under entry — stop hit"
        if cw and spot >= cw * 0.999 and not p["half_sold"]:
            return "SELL_HALF", f"hit the call wall {cw:.0f} (target) — bank half, trail the rest"
        if cw and spot > cw and flow == "bullish":
            return "ADD", f"cleanly broke the call wall {cw:.0f} with bullish flow — runner can add"
        return "HOLD", f"+{move:.2f}% from entry — holding toward {cw:.0f}" if move >= 0 else f"{move:.2f}% — watching the flip {flip:.0f}"
    else:  # put
        if flip and spot > flip:
            return "SELL", f"reclaimed the gamma flip ({flip:.0f}) — put thesis invalidated"
        if "CALL" in sig or "bullish" in str(sig).lower():
            return "SELL", "signal flipped bullish — cut it"
        if move > 0.35:
            return "SELL", f"+{move:.1f}% above entry — stop hit"
        if pw and spot <= pw * 1.001 and not p["half_sold"]:
            return "SELL_HALF", f"hit the put wall {pw:.0f} (target) — bank half, trail the rest"
        if pw and spot < pw and flow == "bearish":
            return "ADD", f"broke the put wall {pw:.0f} with bearish flow — runner can add"
        return "HOLD", f"{-move:.2f}% in your favor — holding toward {pw:.0f}"


def _notify(title, msg):
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
    except Exception:
        pass


YF = {"SPX": "^SPX", "NDX": "^NDX", "SPY": "SPY", "QQQ": "QQQ"}


def manage():
    """Evaluate every open position; ping when the action CHANGES to an actionable one."""
    for p in list_open():
        peri = _peri(p["sym"])
        if not peri.get("ok"):
            continue
        try:
            spot = _spot(YF.get(p["sym"], "^" + p["sym"]))
        except Exception:
            continue
        action, reason = evaluate(p, spot, peri)
        move = (spot / (p["entry_under"] or spot) - 1) * 100
        optpnl = _est_optpnl(p, spot)
        # ping on a NEW actionable transition
        if action != (p.get("last_action") or "") and action in ("SELL", "SELL_HALF", "ADD"):
            emoji = {"SELL": "🔴 SELL", "SELL_HALF": "🟡 SELL HALF", "ADD": "🟢 ADD"}[action]
            _notify(f"{emoji} {p['sym']} {p['strike']:.0f}{p['dir'][0].upper()}",
                    f"{reason}. (entry ${p['entry_prem']:.0f}, est {optpnl:+.0f}%)" if optpnl is not None
                    else f"{reason}.")
        c = _con()
        c.execute("""UPDATE pos SET last_action=?, cur_action=?, cur_reason=?, cur_under=?, cur_move=?,
            cur_optpnl=?, updated=? WHERE id=?""",
                  (action, action, reason, round(spot, 2), round(move, 2), optpnl,
                   datetime.now(ET).isoformat(timespec="seconds"), p["id"]))
        c.commit(); c.close()


def pnl_summary():
    c = _con(); rows = c.execute("SELECT * FROM pos WHERE status='closed'").fetchall(); c.close()
    if not rows:
        return {"n": 0}
    tot = sum(r["pnl_dollar"] or 0 for r in rows)
    wins = sum(1 for r in rows if (r["pnl_dollar"] or 0) > 0)
    return {"n": len(rows), "win": round(wins / len(rows) * 100), "total_dollar": round(tot),
            "avg_pct": round(sum(r["pnl_pct"] or 0 for r in rows) / len(rows), 1)}


if __name__ == "__main__":
    manage()
    print("open:", len(list_open()), "| closed:", pnl_summary())
