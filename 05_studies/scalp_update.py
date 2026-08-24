"""scalp_update.py — FAST live scalp updater for the morning momentum window (9:30–12:00 ET).

Momentum breakouts need live price, not 5-min-old data. This pulls just the live price + session
high/low for SPX & NDX (cheap), reads the gamma regime/levels from the periscope snapshots, and writes
scalp_snapshot.json with the live scalp read. Runs every ~60s (its own launchd job) but does real work
ONLY 9:30–12:00 ET on weekdays (the momentum-breakout window; after noon, pinning dominates).

Signal (from the backtest): trend/low-gamma day → go WITH a break of the session high (long) / low
(short); pin/high-gamma day → SIT OUT (fading loses). Mid-range → wait for the break.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "scalp_snapshot.json")


def _window_open():
    n = datetime.now(ET); m = n.hour * 60 + n.minute
    return n.weekday() < 5 and 570 <= m < 720          # 9:30–12:00 ET


def _peri(sym):
    try:
        return json.load(open(os.path.join(HERE, "data", f"periscope_{sym}.json")))
    except Exception:
        return {}


def _live(yfsym):
    import yfinance as yf
    fi = yf.Ticker(yfsym).fast_info
    return {"last": float(fi["lastPrice"]), "open": float(fi["open"]),
            "high": float(fi["dayHigh"]), "low": float(fi["dayLow"])}


def scalp(sym, yfsym):
    p = _peri(sym)
    try:
        q = _live(yfsym)
    except Exception:
        return None
    last, op, hi, lo = q["last"], q["open"], q["high"], q["low"]
    rng = hi - lo if hi > lo else 1
    pos = (last - lo) / rng                              # 0=at low, 1=at high
    flip = (p.get("uw") or {}).get("uw_flip") or p.get("gamma_flip")
    long_gamma = (p.get("net_gex_musd") or 0) > 0 or (flip and last >= flip)
    uw_intra = ((p.get("uw") or {}).get("intraday") or {}).get("bias")   # live UW tape flow
    flow_bear = uw_intra == "bearish"
    tgt = round(last * 0.0012)
    base = {"symbol": sym, "last": round(last, 2), "day_high": round(hi, 2), "day_low": round(lo, 2),
            "pos_in_range": round(pos, 2), "flip": flip}
    below_flip = bool(flip and last < flip)
    # PUT trigger is REACTIVE + FLOW-CONFIRMED (systematic short triggers don't backtest — upward drift).
    if below_flip and flow_bear:
        base.update({"dir": "SHORT (flow-confirmed)", "col": "red",
                     "why": f"price BELOW the gamma flip {flip:.0f} (short gamma) AND UW tape flow is BEARISH "
                            "(real money buying puts) → the one put setup with confirmation",
                     "entry": f"buy PUTS / short below {last:.0f}", "target": f"−{tgt} pts, TRAIL to the put wall",
                     "stop": f"back above the flip {flip:.0f}",
                     "note": "Reactive + flow-confirmed (NOT a backtested systematic edge — intraday shorts fight the "
                             "drift). Only valid while flow stays bearish; bail on a flip reclaim."})
        return base
    if long_gamma:
        base.update({"dir": "SIT OUT", "col": "mut",
                     "why": "PIN regime (long gamma) — no scalp edge; fading loses (t=−14), momentum fails on pins.",
                     "entry": "no scalp — wait for a trend day", "target": "—", "stop": "—",
                     "note": "Morning window but gamma is long → chop. Save it."})
        return base
    # trend / low-gamma day → LONG momentum breakout only (short breakouts don't validate — drift)
    if pos >= 0.85 or last >= hi - rng * 0.02:
        base.update({"dir": "LONG breakout", "col": "go",
                     "why": f"trend day + price at/breaking the session HIGH {hi:.0f} → momentum long",
                     "entry": f"long a break above {hi:.0f}", "target": f"+{tgt} pts then TRAIL (let it run)",
                     "stop": f"back below {max(lo, flip or 0):.0f}", "note": "Momentum, not fade — trail winners."})
    elif below_flip:
        base.update({"dir": "WAIT — below flip, flow not confirming", "col": "info",
                     "why": f"below the flip {flip:.0f} but UW tape flow isn't bearish yet — a put needs flow confirmation",
                     "entry": "wait for UW bearish flow to confirm the short", "target": "—", "stop": "—",
                     "note": "Intraday shorts without flow confirmation fight the upward drift (backtested negative)."})
    else:
        base.update({"dir": "WAIT — mid-range", "col": "info",
                     "why": f"trend day but price mid-range ({pos*100:.0f}% of today's {lo:.0f}–{hi:.0f})",
                     "entry": "wait for a break of the session high (long) or a flow-confirmed flip loss (put)",
                     "target": "—", "stop": "—", "note": "Long breaks work on trend days; shorts need flow confirmation."})
    return base


def _notify(title, msg):
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
    except Exception:
        pass


def _prior_dirs():
    try:
        old = json.load(open(OUT))
        return {p["symbol"]: p.get("dir") for p in old.get("plays", [])}
    except Exception:
        return {}


def run(force=False):
    if not (_window_open() or force):
        return None
    prior = _prior_dirs()
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET"), "window": _window_open(), "plays": []}
    for sym, yfsym in (("NDX", "^NDX"), ("SPX", "^SPX")):
        s = scalp(sym, yfsym)
        if not s:
            continue
        out["plays"].append(s)
        # PING on a NEW actionable setup: tell the user the naked call/put + strike
        actionable = ("LONG breakout" in s["dir"]) or ("flow-confirmed" in s["dir"])
        if actionable and prior.get(sym) != s["dir"] and _window_open():
            rnd = 25 if sym == "NDX" else 5                 # strike spacing
            atm = round(s["last"] / rnd) * rnd
            if "LONG" in s["dir"]:
                _notify(f"🚀 {sym} LONG breakout — buy CALLS",
                        f"Buy the {atm} call, 0DTE (ATM/1-ITM). Break above {s['day_high']}. Trail — let it run.")
            else:
                _notify(f"🔻 {sym} PUT setup (flow-confirmed) — buy PUTS",
                        f"Buy the {atm} put, 0DTE. Below flip {s.get('flip')} + UW flow bearish. Trail to put wall; bail on flip reclaim.")
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(run(force="force" in sys.argv), indent=2, default=str))
