"""monitor.py — minute-level watch over OPEN 0DTE positions.

A 0DTE position's entire life is one session, so the 5-minute scan cadence is too slow to manage it:
the difference between a -0.5R stop honoured and a max loss taken can be a few minutes. This runs every
60 seconds and is a cheap no-op whenever nothing is open, so it costs almost nothing on a quiet day.

It calls the SAME rule-based risk manager the main cycle uses (ai_trader.manage_open) — there is no
second, divergent copy of the exit logic. No LLM call is made here; exits must be deterministic and
instant.

Swing positions are deliberately NOT managed at this cadence: they are multi-week structures where
minute-level reaction is noise, and they are handled on the hourly swing pass instead.
"""
import os
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STATE = os.path.join(HERE, "data", "monitor_state.json")


def _mkt_open():
    n = datetime.now(ET)
    return n.weekday() < 5 and 570 <= (n.hour * 60 + n.minute) < 960


def open_0dte():
    try:
        import ai_trader
        return [t for t in ai_trader.open_trades()
                if (t.get("expiry") or "").upper() == "0DTE"]
    except Exception:
        return []


def run():
    if not _mkt_open():
        return {"ran": False, "why": "market closed"}
    pos = open_0dte()
    if not pos:
        return {"ran": False, "why": "no open 0DTE positions"}
    try:
        import ai_trader
        ai_trader.manage_open()          # the single shared exit engine — rules only, no LLM
    except Exception as e:
        return {"ran": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
    still = open_0dte()
    out = {"ran": True, "ts": datetime.now(ET).isoformat(timespec="seconds"),
           "watched": len(pos), "still_open": len(still),
           "closed_this_tick": [t["id"] for t in pos if t["id"] not in {s["id"] for s in still}]}
    try:
        json.dump(out, open(STATE, "w"), indent=2, default=str)
    except Exception:
        pass
    return out


if __name__ == "__main__":
    r = run()
    if r.get("ran"):
        print(f"monitored {r['watched']} open 0DTE position(s); {r['still_open']} still open"
              + (f"; closed {r['closed_this_tick']}" if r.get("closed_this_tick") else ""))
    else:
        print("idle —", r.get("why") or r.get("error"))
