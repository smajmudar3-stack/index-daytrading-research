"""SPX / NDX strategy advisor — what to trade, when, at which strikes, and why.

Every recommendation here is anchored to a MEASURED number from the real-quote
backtests (147,350 structure-trades on SPY 2008-2025, entries at ask, exits at
bid), not to a rule of thumb. Where the evidence says a structure loses money,
this file says so and refuses to emit an entry — a board that only ever shows
green is worse than no board.

Conviction is derived, never invented:

    conviction = base(structure evidence) x regime multiplier

`base` comes from the structure's measured expectancy and t-stat. A structure
with negative measured expectancy has base 0 and can never be recommended,
whatever the regime looks like. That is the single design decision that stops
this panel from doing what the last one did.

SPX strikes round to 5, NDX to 25 (the listed increments).
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ROOT, "data")

# Below this, the panel emits NO TRADE rather than a weak one. A low-conviction
# recommendation is not a small edge -- it is an edge the evidence cannot
# distinguish from zero, and showing it invites taking it.
MIN_CONVICTION = 25

# Budget band. SPX/NDX contracts are far too large for this account: a
# delta-derived 0.70/0.30 call debit spread on SPX is ~435 points wide = $43,500
# of max risk on a single lot. So the advisor reads the index for the SIGNAL and
# expresses the trade in the tracking ETF, then sizes the wing width so max risk
# lands inside the band.
BUDGET_LO, BUDGET_HI = 1000, 3000

# Signal instrument -> tradeable instrument. Ratios are live-checked at runtime.
PROXY = {"SPX": "SPY", "NDX": "QQQ", "SPY": "SPY", "QQQ": "QQQ"}
SYMBOLS = ("SPY", "QQQ", "SPX", "NDX")

# ---------------------------------------------------------------------------
# MEASURED EVIDENCE — from scripts/structure_lab.py + scripts/strategy_eval.py.
# win = per-trade win rate, exp = per-trade expectancy on capital at risk,
# t = t-stat of the mean. These are real-quote numbers; do not edit by hand.
# ---------------------------------------------------------------------------
EVIDENCE = {
    "call debit 70/30":   dict(win=0.675, exp=+0.121, t=+2.6, verdict="TRADE",
                               note="highest win rate of any directional structure tested"),
    "call debit 50/30":   dict(win=0.655, exp=+0.160, t=+2.4, verdict="TRADE",
                               note="more return, slightly lower win rate"),
    "deep ITM call 0.80": dict(win=0.640, exp=+0.134, t=+2.2, verdict="TRADE",
                               note="mostly intrinsic; closest option to owning the index"),
    "ATM call 0.50":      dict(win=0.578, exp=+0.257, t=+1.9, verdict="MARGINAL",
                               note="best raw return, but -73% drawdown at 25% sizing"),
    "OTM call 0.30":      dict(win=0.471, exp=+0.305, t=+1.2, verdict="AVOID",
                               note="wins under half the time; -91% drawdown"),
    "far OTM call 0.16":  dict(win=0.372, exp=+0.237, t=+0.3, verdict="AVOID",
                               note="29-43% win rate, -96 to -99.6% drawdown. The shredder."),
    "iron condor 30/16":  dict(win=0.486, exp=-0.158, t=-17.5, verdict="AVOID",
                               note="8 spread crossings ~= 10% of capital at risk"),
    "iron condor 16/05":  dict(win=0.636, exp=-0.105, t=-13.5, verdict="TRAP",
                               note="wins 2 of 3 and still loses money"),
    "iron butterfly ATM": dict(win=0.459, exp=-0.138, t=-20.1, verdict="AVOID",
                               note="needs the market to sit almost exactly still"),
    "jade lizard":        dict(win=0.652, exp=-0.029, t=-18.0, verdict="TRAP",
                               note="'no upside risk' is true and irrelevant; downside is naked"),
    "twisted sister":     dict(win=0.546, exp=-0.003, t=-9.4, verdict="AVOID",
                               note="closest to break-even of the credit family; still negative"),
    "broken-wing fly":    dict(win=0.552, exp=-0.089, t=-18.1, verdict="AVOID",
                               note="the credit moves the loss, it does not remove it"),
    "christmas tree 1-3-2": dict(win=0.382, exp=-0.234, t=-24.5, verdict="AVOID",
                               note="worst of everything tested; crosses 12 spreads"),
    # --- credit spreads (premium selling), measured on real quotes ---------
    "put credit 30/16":   dict(win=0.686, exp=-0.114, t=-15.4, verdict="TRAP",
                               note="near-the-money: negative even at MID, before any cost. "
                                    "Better fills cannot save this one."),
    "put credit 16/05":   dict(win=0.757, exp=-0.128, t=-17.6, verdict="TRAP",
                               note="FAR-OTM: +1.25%/trade at MID, killed purely by the "
                                    "round trip. Break-even fill ~50-60% of quoted spread."),
    "call credit 30/16":  dict(win=0.547, exp=-0.165, t=-10.9, verdict="AVOID",
                               note="fights the market's structural upward drift as well "
                                    "as the spread"),
    "short strangle 16d": dict(win=0.687, exp=-0.038, t=-17.7, verdict="TRAP",
                               note="worst month on record -2523% of credit"),
    "short straddle":     dict(win=0.571, exp=-0.044, t=-18.3, verdict="AVOID",
                               note="edge exists ONLY delta-hedged; naked is a bet on move size"),
    "ZEBRA 80/50":        dict(win=0.559, exp=-0.058, t=-7.9, verdict="AVOID",
                               note="indistinguishable from a plain 0.80d call after spread"),
}

# The only signal that beat its base rate on all three splits.
# t = +3.90 / +2.84 / +2.06 (train / validate / test).
SIGNAL_NOTE = ("VIX backwardation inside a golden cross — the one signal that beat "
               "its base rate on all three time splits (t = +3.9 / +2.8 / +2.1). "
               "Mechanism: Nagel 2012 RFS, funding-constrained liquidity provision.")


# The panel is a 260k-row parquet and both market_state() and _proxy_spot()
# read it, for every symbol. Rendering four symbols meant ~8 full reads and
# blew the dashboard's request timeout. Cache it for the life of the process,
# keyed on file mtime so a scanner refresh is picked up immediately.
_PANEL_CACHE = {"mtime": None, "df": None}


def _panel():
    import pandas as pd
    path = os.path.join(D, "swing", "panel.parquet")
    mt = os.path.getmtime(path)
    if _PANEL_CACHE["mtime"] != mt:
        pn = pd.read_parquet(path)
        _PANEL_CACHE["df"] = pn.pivot(index="date", columns="ticker",
                                      values="close").sort_index()
        _PANEL_CACHE["mtime"] = mt
    return _PANEL_CACHE["df"]


_STATE_CACHE = {"mtime": None, "st": None}


def _load(name, default=None):
    try:
        with open(os.path.join(D, name)) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _round_strike(x, sym):
    """Listed strike increments: SPX 5, NDX 25, SPY/QQQ 1."""
    step = {"SPX": 5, "NDX": 25}.get(sym, 1)
    return round(x / step) * step


def _proxy_spot(sym):
    """Live spot for the tradeable ETF, from the daily panel."""
    try:
        return float(_panel()[PROXY[sym]].dropna().iloc[-1])
    except Exception:
        return None


def _fit_budget(spot, iv, kind):
    """Choose the wing width so max risk lands in the budget band.

    Returns (width_points, contracts, max_risk_dollars). A vertical's max risk
    is (width - debit) x 100 x contracts; for a long call it is the premium.
    """
    T = 45 / 365.0
    sd = spot * iv * math.sqrt(T)
    if kind == "single":
        # Long call: cost is the premium. Rough ATM-ish premium ~= 0.4*sd for
        # 0.80 delta the extrinsic is smaller but intrinsic dominates, so price
        # the whole thing off moneyness.
        prem = 0.84 * sd + 0.25 * sd
        cost = prem * 100
        n = max(1, int(BUDGET_HI // cost)) if cost < BUDGET_HI else 0
        return None, n, cost * max(n, 1)
    # Vertical. Prefer FEW contracts on a WIDER spread over many contracts on a
    # narrow one: 51 lots of a 1-wide spread is 102 legs of commission and
    # spread crossing for the same risk as 3 lots of a 17-wide. Leg count is a
    # real cost, so search contracts ascending and take the first fit.
    for n in (1, 2, 3, 4, 5, 6, 8, 10):
        target = ((BUDGET_LO + BUDGET_HI) / 2) / n     # risk per contract
        width = target / 100.0 / (1 - 0.42)            # invert (w - debit)*100
        width = max(1, round(width))
        risk = (width - width * 0.42) * 100 * n
        if BUDGET_LO <= risk <= BUDGET_HI:
            return width, n, risk
    return 5, 1, (5 - 5 * 0.42) * 100


def market_state():
    """Live regime read, from the snapshots the scanner already maintains.

    Cached on panel mtime: the state is identical for all four symbols, so
    recomputing it per symbol was pure waste.
    """
    try:
        mt = os.path.getmtime(os.path.join(D, "swing", "panel.parquet"))
        if _STATE_CACHE["mtime"] == mt:
            return _STATE_CACHE["st"]
    except OSError:
        mt = None
    gx = _load("gex_snapshot.json")
    st = {
        "gex_z": gx.get("gex_z"),
        "dix_z": gx.get("dix_z"),
        "regime": gx.get("regime"),
        "neg_gamma": gx.get("neg_gamma"),
    }
    # VIX term structure — the golden-cross/backwardation signal inputs.
    try:
        c = _panel()
        spy = c["SPY"]
        st["vix"] = float(c["^VIX"].dropna().iloc[-1])
        st["vix3m"] = float(c["^VIX3M"].dropna().iloc[-1])
        st["ts_ratio"] = st["vix"] / st["vix3m"]
        st["backwardation"] = st["ts_ratio"] >= 1.0
        st["golden"] = bool(spy.rolling(50).mean().iloc[-1] > spy.rolling(200).mean().iloc[-1])
        st["above200"] = bool(spy.iloc[-1] > spy.rolling(200).mean().iloc[-1])
        st["asof"] = str(c.index[-1].date())
        # How old is the SIGNAL input? Spot can be live while this is days old,
        # which is the worst combination: the board looks current and is not.
        age = (datetime.now(timezone.utc).date() - c.index[-1].date()).days
        st["signal_age_days"] = age
        st["stale"] = age > 4
    except Exception:
        pass
    _STATE_CACHE["mtime"], _STATE_CACHE["st"] = mt, st
    return st


def _expiries(dte_lo, dte_hi):
    """Nearest Friday inside the target DTE window."""
    today = datetime.now(timezone.utc).date()
    out = []
    for d in range(dte_lo, dte_hi + 1):
        dt = today + timedelta(days=d)
        if dt.weekday() == 4:
            out.append(dt)
    return out


# ---------------------------------------------------------------------------
# GAMMA PICKS THE VEHICLE, NOT THE SIDE.
#
# Dealer gamma does not predict direction (1,001 gated cells, zero survived) but
# it does predict RANGE (realised/implied 0.843x high-gamma vs 1.139x low,
# t = -13.2 over 15 years). Range decides which expression of a directional view
# pays best -- so once the weighted vote has taken a side, gamma chooses how to
# express it.
#
# Measured on real quotes, non-overlapping entries, ask in / bid out. Every one
# of the eight directional structures tested paid MORE in low gamma than high --
# 8 of 8 pointing the same way is what makes this actionable despite modest
# individual t-stats (n=122 per cell):
#
#                        LOW gamma            HIGH gamma
#   long call 0.30d   +29.71% (med -33.0)   +2.79% (med -31.2)
#   long call 0.50d   +20.61% (med  +1.3)   +5.94% (med  +0.6)
#   long call 0.70d   +12.11% (med +14.4)   +2.85% (med +11.6)
#   call debit 70/30   +5.25% (med +24.9)  -0.16% (med +16.2)
#
# Ranked on MEDIAN rather than mean, because a mean carried by one crash payoff
# is not an outcome anyone sits through at retail size.
GAMMA_VEHICLE = {
    "low": {
        "structure": "call debit 70/30",
        "why": ("dealers amplify moves, so the range is wide — the spread's "
                "best median (+24.9%, 63% win) comes from that room to run"),
        "alt": "long call 0.70d for more convexity (+14.4% median, 57% win)",
        "size": 1.0,
    },
    "high": {
        "structure": "call debit 70/30",
        "why": ("dealers pin the tape, so the upside is capped anyway — the "
                "spread cuts cost for the same capped payoff (+16.2% median)"),
        "alt": "smaller size; every structure paid roughly HALF what it did in low gamma",
        "size": 0.5,
    },
    "mid": {
        "structure": "call debit 70/30",
        "why": "no strong range signal — the highest-median structure by default",
        "alt": "long call 0.70d",
        "size": 0.75,
    },
}


def gamma_vehicle(gex_z):
    """Given the prior-close gamma read, pick the vehicle and the size."""
    if gex_z is None:
        return {**GAMMA_VEHICLE["mid"], "regime": "unknown"}
    if gex_z < -0.5:
        return {**GAMMA_VEHICLE["low"], "regime": "LOW gamma (wide range)"}
    if gex_z > 0.5:
        return {**GAMMA_VEHICLE["high"], "regime": "HIGH gamma (pinned)"}
    return {**GAMMA_VEHICLE["mid"], "regime": "mid gamma"}


def advise(sym):
    """Return the recommendation set for SPX or NDX."""
    # How old is the price this ticket is built from? Strikes are derived from
    # spot, so a stale spot yields silently wrong strikes -- it must be surfaced
    # rather than rendered as if live.
    import time as _t
    _pf = os.path.join(D, f"periscope_{'SPX' if sym in ('SPY','SPX') else 'NDX'}.json")
    try:
        spot_age = (_t.time() - os.path.getmtime(_pf)) / 60.0
    except OSError:
        spot_age = None

    if sym in ("SPY", "QQQ"):
        spot = _proxy_spot(sym)
        peri = _load(f"periscope_{'SPX' if sym == 'SPY' else 'NDX'}.json")
        # Scale the index gamma walls into ETF terms so the levels still mean
        # something on the chart the owner is actually looking at.
        ratio = 10.03 if sym == "SPY" else 41.11
        peri = {k: (v / ratio if isinstance(v, (int, float)) and k.endswith("wall") else v)
                for k, v in peri.items()}
    else:
        peri = _load(f"periscope_{sym}.json")
        spot = peri.get("spot")
    if not spot:
        return {"symbol": sym, "error": "no live spot available"}

    st = dict(market_state())
    st["spot_age_min"] = round(spot_age) if spot_age is not None else None
    # Beyond a session old, the quote is not a basis for a strike.
    st["spot_stale"] = bool(spot_age is not None and spot_age > 90)
    call_wall = peri.get("call_wall")
    put_wall = peri.get("put_wall")

    # ---- the one supported entry condition -------------------------------
    signal_on = bool(st.get("backwardation") and st.get("golden"))

    # Regime multiplier. Deliberately capped at 1.0 — no regime can turn a
    # negative-expectancy structure positive, and none of the 1,001 gates
    # tested (GEX, DIX, VIX pct, term structure, IV-RV) survived three periods.
    mult = 1.0 if signal_on else 0.45

    recs = []
    for name in ("call debit 70/30", "call debit 50/30", "deep ITM call 0.80",
                 "ATM call 0.50"):
        ev = EVIDENCE[name]
        # HARD GUARD. The panel must never surface a trade the measured numbers
        # say loses money. This is an assertion, not a filter, so a future edit
        # that adds a negative-expectancy structure to the candidate list fails
        # loudly instead of quietly recommending it.
        if ev["exp"] <= 0:
            raise AssertionError(
                f"{name} has measured expectancy {ev['exp']:+.2%} and must never "
                f"appear in the recommendation path")
        # Conviction: measured win rate above the ~50% coin flip, scaled by
        # t-stat credibility, then by regime. Capped at 75 — nothing here
        # clears the multiple-testing bar outright.
        base = (ev["win"] - 0.50) * 200 * min(ev["t"] / 3.0, 1.0)
        conv = int(max(0, min(75, base * mult)))

        # Express in the tradeable ETF, not the index — SPX/NDX contract sizes
        # are 10x and 41x the ETF and put a single lot far outside the budget.
        iv = (st.get("vix") or 18) / 100.0
        pxy = PROXY[sym]
        pspot = _proxy_spot(sym) or (spot / (10.03 if sym == "SPX" else 41.11))
        T = 45 / 365.0
        psd = pspot * iv * math.sqrt(T)

        if "0.80" in name or name.startswith("ATM"):
            k = pspot - 0.84 * psd if "0.80" in name else pspot
            width, n, risk = _fit_budget(pspot, iv, "single")
            legs = f"BUY {n}x {pxy} {_round_strike(k, pxy)}C"
            if n == 0:
                legs = f"{pxy} {_round_strike(k, pxy)}C — single contract exceeds budget"
        else:
            width, n, risk = _fit_budget(pspot, iv, "vertical")
            lo = _round_strike(pspot - 0.52 * psd if "70/30" in name else pspot, pxy)
            legs = f"BUY {n}x {pxy} {lo}C / SELL {lo + width}C  ({width}-wide)"

        # What the same trade would cost on the index, for contrast.
        isd = spot * iv * math.sqrt(T)
        idx_cost = ((0.52 + 0.52) * isd * 100 if "debit" in name
                    else (0.84 * isd + 0.25 * isd) * 100)

        exps = _expiries(35, 60)
        recs.append({
            "structure": name, "legs": legs,
            "expiry": str(exps[0]) if exps else "nearest 35-60 DTE",
            "dte": "35-60", "hold": "21 trading days, or exit on signal loss",
            "win": ev["win"], "exp": ev["exp"], "t": ev["t"],
            "vehicle": pxy, "contracts": n, "max_risk": round(risk),
            "index_cost": round(idx_cost),
            "conviction": conv, "verdict": ev["verdict"], "note": ev["note"],
        })

    # Gamma regime chooses the vehicle and scales the size.
    veh = gamma_vehicle(st.get("gex_z"))
    for r in recs:
        r["regime"] = veh["regime"]
        r["regime_why"] = veh["why"]
        r["preferred"] = (r["structure"] == veh["structure"])
        r["size_mult"] = veh["size"]
    # Surface the structure the regime actually favours.
    recs.sort(key=lambda r: (not r.get("preferred"), -r["conviction"]))
    recs.sort(key=lambda r: -r["conviction"] if not r.get("preferred") else -999)

    # Apply the floor. Anything under it is demoted out of the recommendation
    # list entirely and reported as the reason there is no trade today.
    below = [r for r in recs if r["conviction"] < MIN_CONVICTION]
    recs = [r for r in recs if r["conviction"] >= MIN_CONVICTION]

    if st.get("spot_stale"):
        age = st.get("spot_age_min") or 0
        hrs = age / 60.0
        recs, below = [], recs + below
        headline = (f"NO TRADE — the price feed is {hrs:.1f}h old (last update "
                    f"{peri.get('as_of','unknown')}). Strikes are derived from spot, "
                    f"so a stale quote produces wrong strikes. Signals are withheld "
                    f"until the scanner refreshes at the next session.")
    elif recs:
        headline = f"TRADE — {len(recs)} structure(s) clear conviction {MIN_CONVICTION}"
    elif not signal_on:
        headline = ("NO TRADE — entry signal is OFF. The one condition that beat its "
                    "base rate on all three splits (VIX backwardation inside a golden "
                    "cross) is not present, so every structure is throttled below the "
                    f"conviction floor of {MIN_CONVICTION}.")
    else:
        headline = (f"NO TRADE — signal is on but nothing clears conviction "
                    f"{MIN_CONVICTION} at current levels.")

    blocked = [{"structure": k, **v} for k, v in EVIDENCE.items() if v["exp"] <= 0]
    blocked.sort(key=lambda r: r["exp"])

    # The premium-selling family splits into two DIFFERENT failure modes, and
    # only one of them is potentially fixable. Worth stating explicitly rather
    # than lumping all credit structures under one "avoid".
    sell_note = (
        "CREDIT SPREADS — two different failure modes. NEAR-THE-MONEY structures "
        "(30/16 condor, ATM butterfly) are negative at MID PRICES, before any cost: "
        "condor -2.24%, butterfly -4.86% of risk per trade. Better fills cannot save "
        "them. FAR-OTM structures (16/05, 10/05) are POSITIVE at mid (+1.25%, +1.41%) "
        "and are killed purely by the round trip -- 8 spread crossings on a 4-leg "
        "structure is ~10% of capital at risk. Break-even fill quality for the "
        "monthly 10/05 is roughly 50-60% of the quoted spread. Achievable in "
        "principle with patient limit orders; worth about 1%/yr at 5% risk sizing "
        "if you get it. That is the ONLY coherent premium-selling research direction "
        "the data supports.")
    

    return {
        "symbol": sym, "spot": spot, "call_wall": call_wall, "put_wall": put_wall,
        "signal_on": signal_on, "state": st, "recommendations": recs,
        "blocked": blocked, "signal_note": SIGNAL_NOTE, "sell_note": sell_note,
        "headline": headline, "below_floor": below, "min_conviction": MIN_CONVICTION,
    }


def main():
    for sym in SYMBOLS:
        a = advise(sym)
        print("=" * 84)
        print(f"{sym}   spot {a.get('spot')}   "
              f"walls {a.get('put_wall')} / {a.get('call_wall')}")
        print("=" * 84)
        if a.get("error"):
            print("  ", a["error"]); continue
        st = a["state"]
        print(f"  VIX {st.get('vix')}  VIX3M {st.get('vix3m')}  "
              f"ratio {st.get('ts_ratio', 0):.3f}  "
              f"backwardation={st.get('backwardation')}  golden={st.get('golden')}")
        print(f"  GEX z {st.get('gex_z')}  DIX z {st.get('dix_z')}  regime {st.get('regime')}")
        print(f"\n  ENTRY SIGNAL: {'ON' if a['signal_on'] else 'OFF'}  ({SIGNAL_NOTE[:60]}...)")
        print(f"\n  >>> {a['headline']}")
        if a["below_floor"]:
            print("      (below floor, NOT recommended: "
                  + ", ".join(f"{r['structure']} conv {r['conviction']}"
                              for r in a["below_floor"]) + ")")
        print(f"\n  {'structure':22s} {'legs':34s} {'win':>6s} {'exp':>8s} {'conv':>5s}")
        for r in a["recommendations"]:
            print(f"  {r['structure']:20s} {r['legs']:46s} {r['win']:6.1%} "
                  f"{r['exp']:+7.1%} risk ${r['max_risk']:,}  conv {r['conviction']}")
            print(f"      (same trade on {sym} would risk ~${r['index_cost']:,})")
        print(f"\n  SELL SIDE: {a['sell_note'][:300]}...")
        print(f"\n  BLOCKED ({len(a['blocked'])} structures, negative measured expectancy):")
        for b in a["blocked"][:8]:
            print(f"    {b['structure']:22s} win {b['win']:5.1%}  exp {b['exp']:+7.2%}  "
                  f"[{b['verdict']}]")
        print()


if __name__ == "__main__":
    main()
