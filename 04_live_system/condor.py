"""condor.py — accurate 0DTE iron-condor play, gated by gamma regime + time of day.

Survival table is the backtested (condor_backtest.py) survival-to-close on HIGH-gamma pin days by
entry time × width. The live signal reads today's regime + the current ET time and returns the
condor with real survival odds and wall-matched strikes — or None when a condor is NOT favorable
(trend/low-gamma days, or too early for the width).
"""

from idt import bs
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


# Pricing lives in idt.bs now. There were four copies of Black-Scholes in this repo
# with two different risk-free rates, so the same structure priced differently
# depending on which module happened to price it. Given that a MODELLED price
# overstating a credit was the entire apparent 0DTE edge, four copies of the model
# was not a style problem.
def _ncdf(x):
    return bs.ncdf(x)


def _bs(S, K, T, iv, r=bs.RISK_FREE, call=True):
    """Black-Scholes price (per 1 index point; x100 for $/contract)."""
    return float(bs.price(S, K, T, iv, r=r, call=call))

# backtested survival % on HIGH-gamma pin days: {entry_minute_ET: {width_pct: survival%}}
SURV = {
    585: {0.4: 29, 0.5: 47, 0.6: 63, 0.75: 78, 1.0: 89},    # 09:45
    630: {0.4: 45, 0.5: 61, 0.6: 73, 0.75: 83, 1.0: 92},    # 10:30
    690: {0.4: 57, 0.5: 71, 0.6: 76, 0.75: 89, 1.0: 95},    # 11:30
    780: {0.4: 69, 0.5: 81, 0.6: 86, 0.75: 92, 1.0: 97},    # 13:00
    840: {0.4: 79, 0.5: 85, 0.6: 89, 0.75: 94, 1.0: 99},    # 14:00
    870: {0.4: 83, 0.5: 89, 0.6: 92, 0.75: 97, 1.0: 100},   # 14:30
}
_TIMES = sorted(SURV)


def _survival(mins, width_pct, regime):
    """Interpolate survival for the current time+width. MID gamma ≈ HIGH (afternoon), LOW = not viable."""
    if regime == "low":
        return None
    t = min(max(mins, _TIMES[0]), _TIMES[-1])
    lo = max([x for x in _TIMES if x <= t], default=_TIMES[0])
    hi = min([x for x in _TIMES if x >= t], default=_TIMES[-1])
    def at(tt): return SURV[tt].get(width_pct, SURV[tt][0.75])
    s = at(lo) if lo == hi else at(lo) + (at(hi) - at(lo)) * (t - lo) / (hi - lo)
    if regime == "mid":
        s -= 3           # mid-gamma slightly lower than pin in the morning; ~equal by afternoon
    return round(s)


def _price_condor(spot, sp, sc, lp, lc, T, iv):
    """Net credit + max loss per contract ($), from BS. mult=100 ($/point)."""
    mult = 100
    credit = (_bs(spot, sp, T, iv, call=False) + _bs(spot, sc, T, iv, call=True)
              - _bs(spot, lp, T, iv, call=False) - _bs(spot, lc, T, iv, call=True))
    wing = min(sp - lp, lc - sc)
    max_loss = (wing - credit)
    return round(credit * mult), round(max_loss * mult), wing


def play(spot, regime, call_wall=None, put_wall=None, now=None, rnd=25, iv=None, rr_max=3.0):
    """regime: 'pin'/'mid'/'low'. iv = annualized (e.g. 0.11). rr_max = worst acceptable risk:reward.
    Computes real credit/max-loss/R:R/EV and REFUSES condors whose credit is too thin for the risk."""
    n = now or datetime.now(ET)
    mins = n.hour * 60 + n.minute
    rth = n.weekday() < 5 and 570 <= mins < 960
    if regime == "low":
        return {"go": False, "col": "mut",
                "why": "TREND/low-gamma day — condor survival is poor (38-77%). Don't sell premium into a trend."}
    hrs = max(0.25, (960 - mins) / 60.0)
    T = hrs / (24 * 365)
    iv = iv if (iv and iv > 0) else 0.11               # fallback ~11% if none supplied

    def k(pct, sign):
        return round(spot * (1 + sign * pct / 100) / rnd) * rnd

    # SEARCH short-strike width × wing width → maximize EV subject to R:R ≤ target. Closer strikes
    # collect more credit (better R:R) but survive less — this finds the sweet spot, or SKIPs if none.
    best = None
    for w in (0.4, 0.5, 0.6, 0.75, 1.0):
        s = _survival(mins, w, "pin" if regime == "pin" else "mid")
        if s is None:
            continue
        sc, sp = k(w, +1), k(w, -1)
        for wpts in [rnd, 2 * rnd, 3 * rnd, 4 * rnd, 6 * rnd]:
            lp, lc = sp - wpts, sc + wpts
            credit, max_loss, _ = _price_condor(spot, sp, sc, lp, lc, T, iv)
            if credit <= 0 or max_loss <= 0:
                continue
            rr = max_loss / credit
            ev = s / 100 * credit - (1 - s / 100) * max_loss
            if rr > rr_max:
                continue                                # respect the user's R:R cap
            cand = {"w": w, "surv": s, "sc": sc, "sp": sp, "lp": lp, "lc": lc,
                    "credit": credit, "max_loss": max_loss, "rr": round(rr, 1), "ev": round(ev)}
            if best is None or ev > best["ev"]:
                best = cand
    if not best:
        return {"go": False, "col": "mut",
                "why": f"No condor clears a 1:{rr_max:.0f} R:R here — credit is too thin for the risk (deep pin / "
                       "low IV). This is the trap: high survival but the reward doesn't justify it. SKIP."}

    surv = best["surv"]; sc, sp = best["sc"], best["sp"]
    worth = best["ev"] > 0
    be_surv = round((1 - best["credit"] / (best["credit"] + best["max_loss"])) * 100)
    width = best["w"]
    timing = ("PRIME — power-hour pin" if mins >= 780 else "OK — improves into the afternoon" if mins >= 630
              else "EARLY — range not set; wait past ~11:30 or skip")
    return {"go": worth, "col": "red" if worth else "mut",
            "width": width, "survival": surv, "breakeven_surv": be_surv, "timing": timing, "rth": rth,
            "short_call": sc, "short_put": sp, "long_call": best["lc"], "long_put": best["lp"],
            "credit": best["credit"], "max_loss": best["max_loss"], "rr": best["rr"], "ev": best["ev"],
            "call_wall": call_wall, "put_wall": put_wall,
            "why": (f"~${best['credit']} credit / ${best['max_loss']} max loss = <b>1:{best['rr']} R:R</b>. "
                    f"Survival {surv}% vs breakeven {be_surv}% → EV {'+' if best['ev']>0 else ''}${best['ev']}/contract. "
                    + ("WORTH IT." if worth else "SKIP — reward too small for the risk (survival doesn't clear breakeven, or R:R worse than 1:%.0f)." % rr_max)),
            "note": "Defined risk (wings sized for R:R). Best afternoon; skew away from strong flow. Tail risk = a news break — size small."}


if __name__ == "__main__":
    import json
    for reg in ("pin", "mid", "low"):
        print(reg, "->", json.dumps(play(7669, reg, 7675, 7650), default=str)[:200])
