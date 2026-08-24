"""rules.py — the VALIDATED trade rules, as executable code.

Everything here comes from `RULES.md` (backtest_0dte_rules.py / backtest_swing_rules.py), which tested
these walk-forward, out-of-sample, against controls and permutation nulls. This module is the bridge
between that research and the live agent: the agent is told what survived, what was killed, and whether
today's gate is open.

THE ONE VALIDATED EDGE
    Prior-close dealer gamma predicts the intraday RANGE, and the option market does not fully price it.
    Measured against VIX9D (a real market-implied price), high-gamma days realise 0.843x the implied
    move vs 1.139x on low-gamma days, t = -13.2, stable across all four sub-periods of 15 years.
    It is a RANGE forecast, never a direction forecast.

THE RULE
    prior-close GEX z > +0.5  ->  sell a 0DTE index iron condor, shorts at ~1.25 SD of the REMAINING
    session move, wings ~1 SD, entered 10:30-13:00 ET, stopped at -0.5x max risk, one at a time.
    Otherwise: stand down. (In 2022 that meant 6 trades all year. That is the feature.)

*** CORRECTION 2026-08-05 — THE MODELLED EDGE DID NOT SURVIVE REAL QUOTES ***
    The +3.7%/trade, 91%-win figure came from Black-Scholes with a linear skew approximation. Re-run on
    1,919 sessions of ACTUAL SPXW bid/ask (2016-09 -> 2024-05, no pricing model anywhere), the same
    structure returns roughly ZERO:
        11:00 entry, 0.5% OTM shorts : -1.70%/trade  (t = -0.99)
        12:00 entry, 0.7% OTM shorts : +0.95%/trade  (t = +0.82)  <- best cell, not significant
        most other entry/strike cells: negative
        CAGR at 5% risk ~ +3.6% with a -22% drawdown; no year-over-year consistency
    The model overstated the credit (it misprices the wings), which is where the entire apparent edge
    came from. Treat the condor as approximately break-even until real-fill evidence says otherwise.
    Do NOT quote the +3.7% number.

WHAT WAS KILLED (do not let the agent drift back into these)
    - Buying 0DTE premium on any directional signal: -10% to -11%/trade. Dead.
    - "Below the gamma flip = buy premium": long straddles lose -7.2%. The correct rule is STAND DOWN.
    - DIX as a premium-selling filter: permutation p = 0.494. Nothing.
    - Sector-rotation relative strength: picks do WORSE than random, permutation p = 0.867.
    - All swing option structures: beaten by simply owning SPY on return, Sharpe and drawdown.
"""
import os
import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

GEX_Z_GATE = 0.5           # the whole edge — fires ~81 days/yr (32% of sessions)
ENTRY_START = (10, 30)     # not at the open: the opening drive is the least pin-like part of the day
ENTRY_END = (13, 0)        # after 14:00 there isn't enough credit left
SHORT_SD = 1.25            # short strikes, in SD of the REMAINING-session move
WING_SD = 1.0              # wing width
STOP_R = 0.5               # software stop at -0.5x max risk
RISK_PCT = 5.0             # 5% of account per condor (backtested max DD -8%)
MAX_CONCURRENT = 1         # one condor at a time — the correlated-tail cap

# Cash-settled index is the researched product. SPX is unaffordable at this account size (~$2,375 per
# condor vs a $600 cap) and XSP has no quotable chain through our data source, so the ETFs are the live
# proxies — with the caveat that both are PHYSICALLY settled, which is exactly why
# risk_gates.force_close_reason() flattens them before the bell.
#
# SPY carries the researched signal directly (the study used SPY as the SPX proxy). QQQ is included
# because the NDX gamma board is computed alongside SPX, but note the edge was validated on the S&P
# series — QQQ is the same mechanism applied to a correlated index, not an independently tested one.
PRODUCT = "SPY"
PRODUCTS = ("SPY", "QQQ")
UNIVERSE_0DTE = set(PRODUCTS)      # the ONLY symbols allowed for 0DTE at this account size


def _load(name):
    try:
        return json.load(open(os.path.join(HERE, "data", name)))
    except Exception:
        return {}


def gex_z():
    """Prior-close dealer-gamma z-score. This is the causal, past-only signal the rule is built on —
    NOT the intraday 'live regime' label, which is a different (unvalidated) construct."""
    g = _load("gex_snapshot.json")
    z = g.get("gex_z")
    return float(z) if z is not None else None


def _mins_now():
    n = datetime.now(ET)
    return n.hour * 60 + n.minute


def _mins_to_close():
    return max(0, 16 * 60 - _mins_now())


def sd_remaining(sym=PRODUCT):
    """SD of the remaining-session move = ATM IV x sqrt(minutes left / 390) x spot."""
    try:
        import warnings
        warnings.filterwarnings("ignore")
        import yfinance as yf
        import option_pricer as OP
        spot = float(yf.Ticker(OP._yf(sym)).fast_info["lastPrice"])
        exp = OP.resolve_expiry(sym, "0DTE")
        if not exp:
            return None
        ch = OP._chain(sym, exp)
        if ch is None:
            return None
        calls = ch.calls
        row = calls.iloc[(calls["strike"] - spot).abs().argmin()]
        iv = float(row.get("impliedVolatility") or 0)
        if iv <= 0:
            return None
        # IV is annualised. The remaining session is (minutes_left / 390) of a trading day, and there
        # are 252 trading days in a year, so the period variance fraction is (mins/390)/252.
        session_frac = max(_mins_to_close(), 1) / 390.0
        year_frac = session_frac / 252.0
        sd = spot * iv * math.sqrt(year_frac)
        return {"spot": spot, "expiry": exp, "atm_iv": round(iv, 4),
                "minutes_left": _mins_to_close(), "sd": round(sd, 3)}
    except Exception:
        return None


def gate_state():
    """Is the validated rule live right now, and if not, why not?"""
    z = gex_z()
    now = _mins_now()
    reasons = []
    if z is None:
        reasons.append("prior-close GEX z-score unavailable")
    elif z <= GEX_Z_GATE:
        reasons.append(f"gamma gate shut: prior-close GEX z {z:+.2f} <= +{GEX_Z_GATE} — stand down, do not trade 0DTE today")
    if now < ENTRY_START[0] * 60 + ENTRY_START[1]:
        reasons.append(f"before {ENTRY_START[0]}:{ENTRY_START[1]:02d} ET entry window")
    if now > ENTRY_END[0] * 60 + ENTRY_END[1]:
        reasons.append(f"after {ENTRY_END[0]}:{ENTRY_END[1]:02d} ET — not enough credit left")
    try:
        import risk_gates
        ev = risk_gates.events_today()
        if ev:
            reasons.append(f"event blackout ({', '.join(ev)})")
    except Exception:
        pass
    return {"open": not reasons, "gex_z": z, "reasons": reasons}


def build_condor(sym=PRODUCT, account=None):
    """Construct and price today's condor to the validated spec. Returns None if it can't be built."""
    import option_pricer as OP
    s = sd_remaining(sym)
    if not s or not s.get("sd"):
        return None
    # Below ~15 minutes there is no session left to trade and SD collapses toward zero, which would
    # produce a nonsense structure. Refuse rather than emit one.
    if s.get("minutes_left", 0) < 15:
        return {"ok": False, "reject": f"only {s.get('minutes_left')} minutes left in the session", "spec": s}
    spot, sd, exp = s["spot"], s["sd"], s["expiry"]
    # Snap to strikes that ACTUALLY EXIST — the listed grid is not uniform.
    short_c = OP.pick_strike(sym, exp, "C", spot + SHORT_SD * sd)
    short_p = OP.pick_strike(sym, exp, "P", spot - SHORT_SD * sd)
    if short_c is None or short_p is None:
        return {"ok": False, "reject": "no listed strikes near the target short strikes", "spec": s}
    wing_target = max(WING_SD * sd, 1.0)
    long_c = OP.pick_strike(sym, exp, "C", short_c + wing_target, away_from=short_c, min_distance=wing_target)
    long_p = OP.pick_strike(sym, exp, "P", short_p - wing_target, away_from=short_p, min_distance=wing_target)
    if long_c is None or long_p is None:
        return {"ok": False, "reject": "no listed wing strikes far enough out to build the condor", "spec": s}
    # Use the ACTUAL wing widths achieved; they can differ per side on a sparse grid.
    wing_c, wing_p = long_c - short_c, short_p - long_p
    wing = max(wing_c, wing_p)          # max loss is set by the wider side
    legs = [{"right": "C", "strike": short_c, "qty": -1},
            {"right": "C", "strike": long_c, "qty": 1},
            {"right": "P", "strike": short_p, "qty": -1},
            {"right": "P", "strike": long_p, "qty": 1}]
    r = OP.price_structure(sym, exp, legs)
    if r.get("net") is None:
        return {"ok": False, "reject": r.get("reject"), "spec": s}
    credit = -r["net"]                      # net is negative for a credit structure
    risk_pts = wing - credit
    pct_of_width = credit / wing * 100 if wing else 0
    out = {"ok": True, "sym": sym, "expiry": exp, "spot": spot, "sd": sd,
           "short_put": short_p, "short_call": short_c, "long_put": long_p, "long_call": long_c,
           "wing": wing, "wing_call": wing_c, "wing_put": wing_p,
           "credit": round(credit, 3), "risk_pts": round(risk_pts, 3),
           "credit_pct_of_width": round(pct_of_width, 1),
           # RULES.md §1.1 reference breakevens (4.2% high-gamma / 9.6% low-gamma) were derived for a
           # FULL-SESSION SPX 1.25SD/1SD condor. A late-session SPY structure is not the same animal, so
           # this is recorded for comparison, NOT used as a pass/fail gate. Confirming or killing the
           # edge against real credits is exactly what log_credit() below is accumulating evidence for.
           "reference_breakeven_full_session_spx": 4.2 if (gex_z() or 0) > GEX_Z_GATE else 9.6,
           "tradeable": r.get("tradeable"), "reject": r.get("reject"),
           "pkg_spread_pct": r.get("pkg_spread_pct"), "legs": legs}
    try:
        import sizing
        out["sizing"] = sizing.size_trade(risk_pts, 80, account=account)
    except Exception:
        pass
    return out


CREDIT_LOG = os.path.join(HERE, "data", "credit_log.jsonl")


def log_credit(sym=PRODUCT):
    """RULES.md §6.1 — the single highest-value validation step.

    Every P&L number in the research came from a MODEL, because there are no historical option chains
    here. The way to confirm or kill the edge is to log what the market actually pays for this exact
    structure, session after session, and compare it to the model-free breakevens. One row per session
    in the entry window; after ~60 sessions this is a real answer rather than an assumption.

    This only observes. It never trades."""
    today = datetime.now(ET).date().isoformat()
    try:
        with open(CREDIT_LOG) as f:
            for line in f:
                r = json.loads(line)
                if r.get("date") == today and r.get("sym") == sym:
                    return None                      # already logged this symbol this session
    except Exception:
        pass
    now = _mins_now()
    if not (ENTRY_START[0] * 60 + ENTRY_START[1] <= now <= ENTRY_END[0] * 60 + ENTRY_END[1]):
        return None
    c = build_condor(sym)
    if not c or not c.get("ok"):
        return None
    row = {"date": today, "ts": datetime.now(ET).isoformat(timespec="seconds"),
           "sym": sym, "gex_z": gex_z(), "gate_open": (gex_z() or -9) > GEX_Z_GATE,
           "spot": c["spot"], "sd": c["sd"], "short_put": c["short_put"], "short_call": c["short_call"],
           "wing": c["wing"], "credit": c["credit"], "credit_pct_of_width": c["credit_pct_of_width"],
           "pkg_spread_pct": c.get("pkg_spread_pct"), "tradeable": c.get("tradeable"),
           "reference_breakeven": c.get("reference_breakeven_full_session_spx")}
    try:
        with open(CREDIT_LOG, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception:
        return None
    return row


def credit_evidence():
    """Summarise what real quotes have paid so far, split by whether the gamma gate was open."""
    rows = []
    try:
        with open(CREDIT_LOG) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return {"n": 0}
    hi = [r["credit_pct_of_width"] for r in rows if r.get("gate_open")]
    lo = [r["credit_pct_of_width"] for r in rows if not r.get("gate_open")]
    def _avg(x):
        return round(sum(x) / len(x), 1) if x else None
    return {"n": len(rows), "n_high_gamma": len(hi), "n_low_gamma": len(lo),
            "avg_credit_pct_high_gamma": _avg(hi), "avg_credit_pct_low_gamma": _avg(lo),
            "sessions_needed": max(0, 60 - len(rows))}


def prompt_block():
    """What the agent is told about the validated research. This is the highest-authority block in its
    prompt — it is the only part backed by out-of-sample testing."""
    g = gate_state()
    z = g.get("gex_z")
    zs = f"{z:+.2f}" if z is not None else "unavailable"
    state = ("OPEN — the validated setup is live" if g["open"]
             else "SHUT — " + "; ".join(g["reasons"]))
    return (
        "VALIDATED RESEARCH (this outranks your own pattern-matching — it is the only part of this board "
        "backed by out-of-sample testing over 15 years; see RULES.md).\n"
        "THE ONE REAL EDGE: prior-close dealer gamma predicts the intraday RANGE and the option market "
        "does not fully price it (realised/implied 0.843x on high-gamma days vs 1.139x on low, t=-13.2). "
        "It is a RANGE edge, never a direction edge.\n"
        f"THE RULE: prior-close GEX z > +{GEX_Z_GATE} -> sell a 0DTE iron condor, shorts ~{SHORT_SD} SD of the "
        f"REMAINING-session move, wings ~{WING_SD} SD, enter {ENTRY_START[0]}:{ENTRY_START[1]:02d}-"
        f"{ENTRY_END[0]}:{ENTRY_END[1]:02d} ET, stop at -{STOP_R}x max risk, {MAX_CONCURRENT} at a time, "
        f"{RISK_PCT}% risk. Otherwise STAND DOWN.\n"
        "IMPORTANT CORRECTION: the +3.7%/trade backtest figure came from a pricing MODEL. Re-tested on "
        "1,919 sessions of real SPXW bid/ask it is approximately ZERO (best cell +0.95%/trade, t=+0.82; "
        "the 11:00 entry we use is -1.70%). The model overstated the credit. Treat this structure as "
        "break-even, size it accordingly, and do not present it as a proven edge.\n"
        f"TODAY: prior-close GEX z = {zs}. Gate is {state}.\n"
        "EXPLICITLY REJECTED BY TESTING — do not propose these, they lose money:\n"
        "  (1) Buying 0DTE premium on ANY directional signal (-10% to -11%/trade). No 0DTE long calls/puts "
        "or debit spreads.\n"
        "  (2) 'Below the gamma flip = buy premium' — long straddles on short-gamma days lose -7.2%. The "
        "correct action on a short-gamma day is STAND DOWN, not buy.\n"
        "  (3) DIX as a premium-selling filter (permutation p=0.494 — noise).\n"
        "  (4) Sector-rotation relative strength for swing picks — the picks do WORSE than random "
        "(p=0.867). Do not justify a swing trade with sector rotation.\n"
        "  (5) Swing option structures generally — long index spreads and 35-DTE put credit spreads both "
        "lose to simply owning SPY on return, Sharpe AND drawdown. If you want equity exposure, the honest "
        "answer is to own the index, not to pay premium.\n"
        "If the gate is SHUT, the correct output is STAND_DOWN. Standing down is the strategy working."
    )


if __name__ == "__main__":
    g = gate_state()
    print(f"prior-close GEX z: {g['gex_z']} | gate {'OPEN' if g['open'] else 'SHUT'}")
    for r in g["reasons"]:
        print("   -", r)
    s = sd_remaining()
    print("\nremaining-session spec:", s)
    c = build_condor()
    if c and c.get("ok"):
        print(f"\ntoday's condor ({c['sym']} {c['expiry']}): "
              f"{c['short_put']-c['wing']}/{c['short_put']}P .. {c['short_call']}/{c['short_call']+c['wing']}C")
        print(f"  credit {c['credit']} on {c['wing']}-wide = {c['credit_pct_of_width']}% of width "
              f"(breakeven bar {c['breakeven_bar']}%) | risk {c['risk_pts']} pts")
        print(f"  tradeable {c['tradeable']} pkg-spread {c.get('pkg_spread_pct')}% | {c.get('reject') or 'clean'}")
        print(f"  sizing: {(c.get('sizing') or {}).get('reason')}")
    else:
        print("\ncondor could not be built:", (c or {}).get("reject"))
