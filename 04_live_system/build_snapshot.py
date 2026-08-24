"""build_snapshot.py — computes the live day-trading snapshot -> data/snapshot.json.

Two honest parts:
  OVERNIGHT EDGE — the one real backtested strategy (buy MOC / sell MOO). Reports the
    21y stats and the CURRENT action given the clock (long overnight vs flat intraday).
  LEVELS — objective intraday structure for discretionary trading (NOT auto signals):
    opening range (5/15/30m), session VWAP + sigma bands, prior-day H/L/C, overnight H/L,
    today's gap + its historical tendency, and where price sits vs each level.
Values shown in both the ETF and the index (NDX from QQP, SPX from SPY) via the live ratio.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

ET = ZoneInfo("America/New_York")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "snapshot.json")
PAIRS = [("QQQ", "^NDX", "NDX"), ("SPY", "^GSPC", "SPX")]


def overnight_stats(tk):
    d = yf.download(tk, start="2005-01-01", interval="1d", progress=False,
                    auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
    on = (d["open"] / d["close"].shift(1) - 1).dropna() - 0.0002
    intr = (d["close"] / d["open"] - 1).dropna()
    eq = (1 + on).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return {"sharpe": round(float(on.mean() / on.std() * np.sqrt(252)), 2),
            "cagr": round(float(eq.iloc[-1] ** (252 / len(on)) - 1) * 100, 1),
            "maxdd": round(float(dd) * 100, 1), "win": round(float((on > 0).mean()) * 100, 1),
            "intraday_cagr": round(float((1 + intr).prod() ** (252 / len(intr)) - 1) * 100, 1),
            "n_years": round(len(on) / 252, 0),
            "gap_hist": d}


def clock_state():
    now = datetime.now(ET)
    wd = now.weekday()
    hm = now.hour * 60 + now.minute
    if wd >= 5:
        return "weekend", "LONG overnight — you're holding from Friday's close; sell at Monday's open."
    if hm < 9 * 60 + 30:
        return "pre_open", "LONG overnight — SELL AT THE OPEN (9:30 ET). Then stay flat all day."
    if hm < 16 * 60:
        return "session", "FLAT — the edge is overnight, not intraday. Do nothing. BUY AT THE CLOSE (16:00 ET)."
    return "post_close", "LONG overnight — you BOUGHT at the close; hold to tomorrow's open."


def intraday_levels(etf, idx_sym, idx_name):
    try:
        bars = yf.download(etf, period="2d", interval="5m", progress=False,
                           auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
        daily = yf.download(etf, period="1mo", interval="1d", progress=False,
                            auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
        iq = yf.Ticker(idx_sym).history(period="1d")["Close"].iloc[-1]
        eq = yf.Ticker(etf).history(period="1d")["Close"].iloc[-1]
    except Exception as e:
        return {"error": str(e)[:80]}
    ratio = float(iq) / float(eq)
    bars.index = bars.index.tz_convert(ET)
    days = sorted(set(bars.index.date))
    if not days:
        return {"error": "no intraday bars"}
    today = days[-1]
    tb = bars[bars.index.date == today].between_time("09:30", "16:00")
    prior = daily.iloc[-2]
    prior_close = float(prior["close"])
    overnight_bars = bars[(bars.index.date == today) & (bars.index.strftime("%H:%M") < "09:30")]
    if tb.empty:
        # pre-market: show prior day + overnight only
        last = float(bars["close"].iloc[-1])
        return {"index": idx_name, "etf": etf, "ratio": round(ratio, 2), "phase": "pre-market",
                "price": round(last * ratio, 1), "prior_close": round(prior_close * ratio, 1),
                "prior_high": round(float(prior["high"]) * ratio, 1), "prior_low": round(float(prior["low"]) * ratio, 1),
                "gap_pct": round((last / prior_close - 1) * 100, 2)}
    o = tb.between_time("09:30", "09:35")["open"].iloc[0]
    tp = (tb["high"] + tb["low"] + tb["close"]) / 3
    vwap = float((tp * tb["volume"]).cumsum().iloc[-1] / tb["volume"].cumsum().iloc[-1])
    dev = (tb["close"] - (tp * tb["volume"]).cumsum() / tb["volume"].cumsum())
    sig = float(dev.std())
    last = float(tb["close"].iloc[-1])

    def rng(mins):
        seg = tb.between_time("09:30", (pd.Timestamp("09:30") + pd.Timedelta(minutes=mins)).strftime("%H:%M"))
        return round(float(seg["high"].max()) * ratio, 1), round(float(seg["low"].min()) * ratio, 1)

    or15h, or15l = rng(15)
    or30h, or30l = rng(30)
    gap = (o / prior_close - 1) * 100
    return {
        "index": idx_name, "etf": etf, "ratio": round(ratio, 2), "phase": "session",
        "price": round(last * ratio, 1),
        "vwap": round(vwap * ratio, 1), "vwap_up": round((vwap + 2 * sig) * ratio, 1),
        "vwap_dn": round((vwap - 2 * sig) * ratio, 1),
        "or15_high": or15h, "or15_low": or15l, "or30_high": or30h, "or30_low": or30l,
        "prior_close": round(prior_close * ratio, 1),
        "prior_high": round(float(prior["high"]) * ratio, 1), "prior_low": round(float(prior["low"]) * ratio, 1),
        "sess_high": round(float(tb["high"].max()) * ratio, 1), "sess_low": round(float(tb["low"].min()) * ratio, 1),
        "gap_pct": round(gap, 2),
        "vs_vwap": "above" if last > vwap else "below",
        "vs_or15": "above" if last * ratio > or15h else ("below" if last * ratio < or15l else "inside"),
    }


# backtested condor win rates (from zero_dte.py, 2y minute data) by entry time & short dist
_WR = {
    "SPX": {"11:30": {0.005: 77, 0.0075: 90}, "13:30": {0.005: 86, 0.0075: 94}},
    "NDX": {"11:30": {0.005: 67, 0.0075: 82}, "13:30": {0.005: 80, 0.0075: 90}},
}


def next_0dte_expiry():
    """SPXW/NDXP expire every trading day. Return today if a weekday pre-close, else next."""
    now = datetime.now(ET)
    d = now.date()
    if now.weekday() < 5 and now.hour < 16:
        return d
    nd = d + pd.Timedelta(days=1)
    while nd.weekday() >= 5:
        nd = nd + pd.Timedelta(days=1)
    return nd


def zero_dte_plan(idx_name, spot, step):
    """Iron-condor strikes at +/-0.5% and +/-0.75% of spot, rounded to the strike step,
    with the backtested win rate for an ~11:30 and ~13:30 entry."""
    if spot is None:
        return None
    def rnd(x):
        return round(x / step) * step
    plans = []
    for D, tag in [(0.0075, "conservative"), (0.005, "standard")]:
        sc = rnd(spot * (1 + D)); sp = rnd(spot * (1 - D))
        wing = 2 * step if idx_name == "SPX" else 4 * step
        plans.append({
            "tag": tag, "short_dist_pct": D * 100,
            "short_put": sp, "long_put": sp - wing, "short_call": sc, "long_call": sc + wing,
            "wing": wing,
            "win_1130": _WR[idx_name]["11:30"][D], "win_1330": _WR[idx_name]["13:30"][D],
        })
    return {"index": idx_name, "expiry": str(next_0dte_expiry()), "spot": round(spot, 1),
            "step": step, "plans": plans}


def gap_tendency(daily, gap_pct):
    d = daily.copy()
    d["on"] = d["open"] / d["close"].shift(1) - 1
    d["intr"] = d["close"] / d["open"] - 1
    d = d.dropna()
    if gap_pct > 0.3:
        sub = d[d["on"] > 0.003]
    elif gap_pct < -0.3:
        sub = d[d["on"] < -0.003]
    else:
        sub = d[d["on"].abs() <= 0.003]
    if len(sub) < 20:
        return None
    return {"n": len(sub), "intraday_mean": round(float(sub["intr"].mean()) * 100, 3),
            "intraday_win": round(float((sub["intr"] > 0).mean()) * 100, 0)}


def run():
    phase, action = clock_state()
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "phase": phase,
           "overnight_action": action, "overnight": {}, "overnight_exec": [],
           "levels": [], "zero_dte": []}
    steps = {"SPX": 5, "NDX": 25}
    ACCOUNT = 2500.0
    for etf in ("QQQ", "SPY"):
        try:
            px = float(yf.Ticker(etf).history(period="1d")["Close"].iloc[-1])
            shares = int(ACCOUNT // px)
            out["overnight_exec"].append({"etf": etf, "price": round(px, 2), "shares": shares,
                                          "cost": round(shares * px, 0)})
        except Exception:
            pass
    for etf, idx_sym, idx_name in PAIRS:
        st = overnight_stats(etf)
        daily = st.pop("gap_hist")
        out["overnight"][etf] = st
        lv = intraday_levels(etf, idx_sym, idx_name)
        if "gap_pct" in lv:
            lv["gap_tendency"] = gap_tendency(daily, lv["gap_pct"])
        out["levels"].append(lv)
        out["zero_dte"].append(zero_dte_plan(idx_name, lv.get("price"), steps[idx_name]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    print(f"snapshot written {out['as_of']} phase={phase}")
    return out


if __name__ == "__main__":
    run()
