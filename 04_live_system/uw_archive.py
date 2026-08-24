"""uw_archive.py — capture Unusual Whales order flow every scan cycle so it becomes BACKTESTABLE.

The problem this solves: order-flow imbalance is the most credible published source of short-horizon
directional predictability, and it is the one input with zero history here. `uw_client` is a live API
only — it can tell you what flow looks like right now, but there is no archive to test against the
500 sessions of minute bars. So no amount of analysis can currently say whether it predicts direction.

This writes one row per symbol per cycle to data/uw_flow.jsonl. After a few weeks it becomes a real
dataset that can be joined to the minute bars on timestamp and tested exactly like every other feature
— with the enormous advantage that it is collected FORWARD, so there is no hindsight contamination and
no possibility of the look-ahead bias that invalidates most intraday studies.

Captured per cycle (whatever the API returns; missing fields are simply absent):
  net premium ticks   — the cumulative call vs put premium tape, the core order-flow measure
  flow alerts         — large/unusual prints with side and premium
  greek exposure      — dealer gamma/delta by strike
  max pain, implied move, gamma flip

Nothing here trades or decides anything. It only records.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "uw_flow.jsonl")
SYMBOLS = ("SPY", "QQQ")


def _mkt_open():
    n = datetime.now(ET)
    return n.weekday() < 5 and 570 <= (n.hour * 60 + n.minute) < 960


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def snapshot(sym):
    """One flow snapshot. Returns None if UW is unavailable so the caller can skip silently."""
    try:
        import uw_client as UW
    except Exception:
        return None
    if not UW.available():
        return None
    row = {"ts": datetime.now(ET).isoformat(timespec="seconds"),
           "date": datetime.now(ET).date().isoformat(),
           "mins": datetime.now(ET).hour * 60 + datetime.now(ET).minute,
           "sym": sym}
    # --- net premium tape: the core order-flow signal --------------------------------
    try:
        intr = UW.intraday_flow(sym)
        if isinstance(intr, dict):
            row["net_prem"] = _num(intr.get("net_premium") or intr.get("net_call_premium"))
            row["call_prem"] = _num(intr.get("call_premium"))
            row["put_prem"] = _num(intr.get("put_premium"))
            row["flow_bias"] = intr.get("bias")
        elif isinstance(intr, list) and intr:
            last = intr[-1]
            row["net_prem"] = _num(last.get("net_premium"))
            row["call_prem"] = _num(last.get("call_premium"))
            row["put_prem"] = _num(last.get("put_premium"))
    except Exception:
        pass
    # --- aggregate read (dir score, flip, walls, implied move) -------------------------
    try:
        full = UW.full_read(sym)
        if isinstance(full, dict):
            for k in ("dir_score", "overall", "uw_flip", "uw_net_gex"):
                if k in full:
                    row[k] = full[k] if not isinstance(full[k], (dict, list)) else None
            im = full.get("implied_move")
            if isinstance(im, dict):
                row["implied_move_pct"] = _num(im.get("move_pct"))
            mp = full.get("max_pain")
            row["max_pain"] = _num(mp.get("strike")) if isinstance(mp, dict) else _num(mp)
    except Exception:
        pass
    # --- large prints: count and net signed premium -------------------------------------
    try:
        alerts = UW.flow_alerts(sym)
        rows = alerts if isinstance(alerts, list) else (alerts or {}).get("data") or []
        n_c = n_p = 0
        prem_c = prem_p = 0.0
        for a in rows[:100]:
            is_call = UW._is_call(a) if hasattr(UW, "_is_call") else None
            pr = _num(a.get("total_premium") or a.get("premium")) or 0.0
            if is_call is True:
                n_c += 1; prem_c += pr
            elif is_call is False:
                n_p += 1; prem_p += pr
        row["alert_calls"] = n_c
        row["alert_puts"] = n_p
        row["alert_call_prem"] = round(prem_c, 2)
        row["alert_put_prem"] = round(prem_p, 2)
        if (prem_c + prem_p) > 0:
            row["alert_cp_ratio"] = round(prem_c / (prem_c + prem_p), 4)
    except Exception:
        pass
    # spot, so the archive can be joined to bars without a second lookup
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import yfinance as yf
        row["spot"] = round(float(yf.Ticker(sym).fast_info["lastPrice"]), 4)
    except Exception:
        pass
    return row


def run(force=False):
    if not force and not _mkt_open():
        return {"ran": False, "why": "market closed"}
    wrote = []
    for sym in SYMBOLS:
        r = snapshot(sym)
        if not r:
            continue
        try:
            with open(OUT, "a") as f:
                f.write(json.dumps(r, default=str) + "\n")
            wrote.append(sym)
        except Exception:
            pass
    return {"ran": bool(wrote), "symbols": wrote}


def stats():
    """How much archive have we accumulated?"""
    n, days, syms = 0, set(), set()
    try:
        with open(OUT) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                n += 1
                days.add(r.get("date"))
                syms.add(r.get("sym"))
    except FileNotFoundError:
        return {"rows": 0, "sessions": 0}
    return {"rows": n, "sessions": len(days), "symbols": sorted(syms),
            "usable_in": max(0, 20 - len(days))}


if __name__ == "__main__":
    import sys
    r = run(force="--force" in sys.argv)
    print("captured:", r)
    print("archive:", stats())
