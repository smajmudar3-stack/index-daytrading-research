"""weekly_swing.py — weekly-expiry trade cards, conditioned on macro before technicals.

WHY THIS REPLACES THE SWING PANEL FOR WEEKLY WORK
=================================================
`swing_signals.py` was audited against its own live output on 2026-09-02. Six defects,
all reproducible in that snapshot, and every one of them is fixed here by construction:

  1. STRIKES THAT DO NOT EXIST. `structure()` computed strikes as `round(last*(1+pct), 0)`.
     On TTD (~$14.50) that produced "Buy 14P / Sell 14P" -- a zero-width spread, which is
     not a trade. On RIOT it produced a $1-wide spread on a $19 stock. On COST (~$920) it
     produced "Sell 969C / Buy 1015C", neither of which is a listed strike; COST lists in
     $5 increments. Here every strike is SNAPPED TO THE REAL LADDER read off the chain, and
     a spread whose legs collapse to the same strike is refused rather than printed.

  2. NOT WEEKLY. The `timeframe` field said "1-2 weeks" but was set by `abs(m20) <
     abs(m60)/2`, a momentum ratio with no horizon in it, and the structure targeted the
     ~35 DTE expiry. Every card in that snapshot expired 2026-10-09, 37 days out. Here the
     expiry is chosen from the chain's REAL weekly expiries inside a stated DTE window, and
     preferentially the one that CONTAINS the catalyst being traded.

  3. THE MACRO WAS WORTH PLUS OR MINUS FIVE POINTS. `macro_tilt` was the only non-price
     input to survive to the output, and it moved conviction by at most 5. Everything else
     -- the MA stack, RSI, 20/60/120-day momentum -- is the same price series transformed
     four ways. So the call was technicals wearing a macro hat. Here the macro overlay
     (`desk_notes.py`) is the PRIMARY voter and holds a VETO: a name with no macro basis is
     not proposed, and a name whose trend fights its macro theme is stood down.

  4. EVERY PICK WAS BEARISH OR NEUTRAL. Eight of eight. Because momentum over 20/60/120
     days was negative across a tape that had gone sideways for three weeks, and because
     the regime rule below docked another 8 points from anything bullish.

  5. "RISK-OFF" AT VIX 15.2. `market_context()` fires RISK-OFF when
     `defensive > cyclical + 1`. Energy leading on an oil-war shock satisfied that, so the
     tape was labelled risk-off while VIX sat at 15.2 and QQQ was flat-to-higher on the
     back of chips. A sector-shock label was being read as an equity-risk label. This
     module does not use that regime word at all; it reads the drivers themselves.

  6. NO EXITS. Not one card carried a target, a stop, or a level that would prove it
     wrong. Every card here carries all three, and the invalidation is a PRICE, not a mood.

WHAT THIS IS NOT
================
This is not a backtested edge and nothing in this file claims it is. `02_findings/` is
unambiguous: every swing OPTIONS structure this repo tested was beaten by simply owning
SPY on return, Sharpe and drawdown, and sector-rotation picks did WORSE than random
(p=0.867). Those results falsify SYSTEMATIC, PRICE-DERIVED swing overlays -- which is
exactly what defect 3 above describes, and exactly what was producing the bad cards.

They do not test a macro-conditioned discretionary book, because this repo has never had
one to test. So the honest status of this module is UNPROVEN, not validated, and it says
so on the panel. What it does buy you is that every card names the macro theme it is
expressing and the level that kills it, so it can be scored later. `scorecard.py` picks
these up on a 21-day horizon.

WHAT IT DOES REUSE FROM THE VALIDATED WORK
==========================================
Three findings from `02_findings/WHAT_WORKS.md` are load-bearing here:

  - THE SPREAD FILTER. Far-OTM buying measured -45.6% overall; filtering to contracts with
    a bid-ask spread of 20% or less took it to +5.6%. Execution mattered more than any
    signal tested for choosing which contract to buy. So `MAX_SPREAD_PCT` is a hard gate,
    not a preference, and a leg that fails it kills the card.
  - THE DELTA BAND. Returns improved monotonically toward the money, reaching +26.1% in
    the 16-30 delta band. Short strikes are placed there deliberately.
  - REAL FILLS ONLY. Every leg is priced at the ASK when bought and the BID when sold.
    The repo's central lesson is that a modelled credit which ignored the wings turned
    +3.7%/trade into approximately break-even on real quotes.

Writes `data/weekly_snapshot.json`. Paper only; nothing here places an order.
"""
import math
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from idt import bs, snapshots

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import desk_notes                                             # noqa: E402

ET = ZoneInfo("America/New_York")
OUT = "weekly_snapshot.json"

# ---------------------------------------------------------------- the knobs ---
DTE_MIN, DTE_MAX = 2, 16      # "weekly" means this window, and nothing outside it
DTE_MIN_SWING = 5             # ...but a trade with no event of its own gets a real week
MACRO_BUFFER_DAYS = 3         # days a position must have LEFT after a macro print
BACK_DTE_TARGET = 35          # the reference expiry for the IV term-structure read

# TWO EXECUTION GATES, BECAUSE THEY MEASURE DIFFERENT THINGS.
#
# The +5.6% spread finding is specifically about which contract to BUY: a 20%-wide quote
# on a leg you pay for is 20% of your premium gone at the door. It does NOT transfer to a
# leg you sell -- applying a RELATIVE limit to a $0.15 short strike refuses every credit
# spread on a $65 ETF, which is what the first version of this file did to XLE, XHB and
# XLRE. What actually matters on a spread is the total half-spread cost measured against
# the money at risk, so that is the second gate and it is the binding one.
MAX_BUY_SPREAD_PCT = 20.0     # the measured filter, applied where it was measured
# ROUND TRIP, not one way. You cross the spread on every leg getting in AND getting out,
# so the true cost is the FULL bid-ask on each leg, not half of it. The first version
# summed half-spreads while calling the result "round-trip", which understated the cost of
# every card by exactly a factor of two -- and `weekly_book` caught it immediately, by
# marking six fresh positions and finding them all instantly negative by more than the
# gate claimed was possible.
# 20% is not generous, it is what weekly spreads actually cost. A 10-wide call spread
# bought for 4.00 with a 0.25 bid-ask on each leg gives back 1.00 on the round trip: 25%
# of the money at risk, before the underlying moves at all. The limit exists to reject the
# egregious ones; the number itself is printed on every card, because the honest response
# to "this costs 18% to trade" is to let the reader see it, not to hide it behind a pass.
MAX_TRADE_COST_PCT = 20.0     # full round-trip slippage as a share of max risk
MIN_OPEN_INTEREST = 10        # a strike nobody holds is a strike you cannot leave
SHORT_DELTA_LO, SHORT_DELTA_HI = 0.16, 0.30    # the measured band for short strikes
TERM_RICH = 1.25              # front/back ATM IV above this = front vol is the thing to sell
IV_RICH_VS_RV = 1.15          # ATM IV this far above realised = rich
IV_CHEAP_VS_RV = 0.95
MAX_CARDS = 6

# NDX-first, because that is the dashboard this feeds. The mega-caps ARE the index: these
# names are roughly half of NDX by weight, so a card on them is a card on the index with a
# stated reason attached. The ETFs are here only so a theme that names one can express it.
UNIVERSE = [
    "QQQ",                                                    # the tradeable NDX proxy
    "NVDA", "AVGO", "MSFT", "AAPL", "AMZN", "META", "GOOGL",
    "TSLA", "AMD", "NFLX", "COST", "PLTR", "MU", "ORCL", "CRM",
    "SMH", "XLE", "XLRE", "XHB", "XOM", "CVX", "CRWD", "DELL",
]


# ------------------------------------------------------------------- helpers ---

def _now():
    return datetime.now(ET)


def _yf():
    import yfinance as yf
    return yf


def _hist(tk):
    """One year of daily closes, or None. Never raises."""
    try:
        d = _yf().download(tk, period="1y", interval="1d", progress=False,
                           auto_adjust=True, multi_level_index=False)
    except Exception:                                         # noqa: BLE001
        return None
    if d is None or len(d) < 60:
        return None
    d = d.rename(columns=str.lower)
    return d.dropna(subset=["close"])


def _realised_vol(closes, n=20):
    r = closes.pct_change().tail(n)
    if r.count() < max(5, n // 2):
        return None
    return float(r.std() * math.sqrt(252) * 100)


def _mid(bid, ask):
    """None unless BOTH sides are real. A one-sided quote is not a price."""
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return None
    if not (b > 0 and a > 0 and a >= b):
        return None
    return (a + b) / 2.0


def _spread_pct(bid, ask):
    m = _mid(bid, ask)
    if m is None or m <= 0:
        return None
    return float((float(ask) - float(bid)) / m * 100)


# ------------------------------------------------------------------- chains ---

def _expiries(tk):
    try:
        return list(_yf().Ticker(tk).options or [])
    except Exception:                                         # noqa: BLE001
        return []


def _dte(exp):
    try:
        d = datetime.strptime(exp, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - _now().date()).days


def _pick_weekly(tk, own_events, macro_events):
    """The weekly expiry to trade, and why that one.

    THE DISTINCTION THAT MATTERS. An event on the NAME and an event on the TAPE want
    opposite expiries, and the first version of this file treated them the same. Friday's
    payrolls print pulled every single card onto the 2-day expiry, so six "weekly" trades
    all died on Friday morning's number. That is not a weekly book, it is six lottery
    tickets on one macro print.

      - The name's OWN event (earnings): take the FIRST expiry at or after it. You are
        buying the repricing, so you must still be holding when it happens.
      - A MACRO event (payrolls, CPI, FOMC): take the first expiry at least
        MACRO_BUFFER_DAYS PAST it. The print is a hazard the position has to survive, not
        the thing being bought, and an option that expires into it has no time left to be
        right afterwards.
      - Neither: the middle of the window.
    """
    floor = DTE_MIN if own_events else DTE_MIN_SWING
    cands = [(e, d) for e in _expiries(tk)
             for d in [_dte(e)] if d is not None and floor <= d <= DTE_MAX]
    if not cands:
        return None, None, f"no listed expiry between {floor} and {DTE_MAX} days out"

    for c in own_events:
        covering = [(e, d) for e, d in cands if d >= c["days_away"]]
        if covering:
            e, d = min(covering, key=lambda x: x[1])
            return e, d, f"covers {c['label']} on {c['date']} (+{c['days_away']}d)"

    for c in macro_events:
        after = [(e, d) for e, d in cands if d >= c["days_away"] + MACRO_BUFFER_DAYS]
        if after:
            e, d = min(after, key=lambda x: x[1])
            return e, d, (f"clears {c['label']} on {c['date']} (+{c['days_away']}d) with "
                          f"{d - c['days_away']} days left to work afterwards")

    mid = (floor + DTE_MAX) / 2
    e, d = min(cands, key=lambda x: abs(x[1] - mid))
    return e, d, "no dated event in the window; middle of the weekly window"


def _pick_back(tk, front_dte):
    """The reference expiry for the term-structure read: nearest to ~35 DTE, past front."""
    best = None
    for e in _expiries(tk):
        d = _dte(e)
        if d is None or d <= front_dte + 2:
            continue
        if best is None or abs(d - BACK_DTE_TARGET) < abs(best[1] - BACK_DTE_TARGET):
            best = (e, d)
    return best or (None, None)


def _chain(tk, exp):
    try:
        c = _yf().Ticker(tk).option_chain(exp)
    except Exception:                                         # noqa: BLE001
        return None, None
    return c.calls, c.puts


def _ladder(calls, puts):
    """The real strike ladder, and its typical increment.

    THIS IS THE FIX FOR THE BROKEN STRIKES. Every strike this module emits comes off this
    list. Nothing is ever computed as a percentage of spot and rounded.
    """
    ks = set()
    for df in (calls, puts):
        if df is not None and len(df):
            ks.update(float(k) for k in df["strike"].tolist())
    ks = sorted(ks)
    if len(ks) < 4:
        return ks, None
    gaps = [round(b - a, 4) for a, b in zip(ks, ks[1:], strict=False) if b > a]
    inc = float(pd.Series(gaps).mode().iloc[0]) if gaps else None
    return ks, inc


def _side_ladder(df):
    """The strikes listed ON THIS SIDE of the chain.

    Calls and puts do not always list the same strikes, especially in the wings. The
    first version of this file snapped against the UNION and then looked the strike up in
    the calls frame, so a put-only strike came back as "no such listed strike" and killed
    otherwise fine candidates. Snap against the side you are going to trade.
    """
    if df is None or not len(df):
        return []
    return sorted(float(k) for k in df["strike"].tolist())


def _snap(ladder, target, exclude=()):
    """The listed strike nearest `target`, never one already used by another leg."""
    avail = [k for k in ladder if k not in exclude]
    return min(avail, key=lambda k: abs(k - target)) if avail else None


def _row(df, strike):
    if df is None or not len(df):
        return None
    m = df[df["strike"] == strike]
    return m.iloc[0] if len(m) else None


def _atm_iv(calls, puts, spot):
    """ATM implied vol as a percentage, averaged across the nearest call and put."""
    ivs = []
    for df in (calls, puts):
        if df is None or not len(df):
            continue
        r = df.iloc[(df["strike"] - spot).abs().argmin()]
        try:
            v = float(r["impliedVolatility"])
        except (TypeError, ValueError, KeyError):
            continue
        if 0.01 < v < 5.0:
            ivs.append(v * 100)
    return float(np.mean(ivs)) if ivs else None


def _implied_move(calls, puts, spot, ladder):
    """The move the front week is pricing, from the ATM straddle. Percent of spot.

    The desk's own NVDA note is the template: "the market is pricing only about a 5.5%
    move, versus roughly a 7.4% average realized". Comparing what is priced against what
    tends to happen is the whole question on an event week.
    """
    k = _snap(ladder, spot)
    if k is None:
        return None
    c, p = _row(calls, k), _row(puts, k)
    if c is None or p is None:
        return None
    cm, pm = _mid(c.get("bid"), c.get("ask")), _mid(p.get("bid"), p.get("ask"))
    if cm is None or pm is None:
        return None
    return float((cm + pm) / spot * 100)


def _leg_quote(df, strike, buying):
    """One leg, priced the way it would actually fill, plus its liquidity verdict.

    Bought at the ASK, sold at the BID. This is the repo's central methodological lesson
    and it is not negotiable: modelling the mid is how +3.7%/trade became break-even.
    """
    r = _row(df, strike)
    if r is None:
        return None, f"{strike:g} is not listed on this side of the chain"
    bid, ask = r.get("bid"), r.get("ask")
    sp = _spread_pct(bid, ask)
    if sp is None:
        return None, f"{strike:g} has no two-sided quote"
    if buying and sp > MAX_BUY_SPREAD_PCT:
        return None, (f"{strike:g} costs {sp:.0f}% of its own price in spread and this leg "
                      f"is bought (limit {MAX_BUY_SPREAD_PCT:.0f}%)")
    try:
        oi = int(r.get("openInterest") or 0)
    except (TypeError, ValueError):
        oi = 0
    if oi < MIN_OPEN_INTEREST:
        return None, f"{strike:g} has {oi} open interest (limit {MIN_OPEN_INTEREST})"
    px = float(ask) if buying else float(bid)
    return {"strike": float(strike), "price": px, "spread_pct": round(sp, 1),
            "half_spread": (float(ask) - float(bid)) / 2.0,
            "oi": oi, "buying": bool(buying),
            "iv": float(r.get("impliedVolatility") or 0) * 100}, None


def _delta_strike(df, spot, dte, target_delta, call=True):
    """The listed strike closest to a target delta, using the chain's own IVs."""
    if df is None or not len(df):
        return None
    T = max(dte, 1) / 365.0
    best, bestd = None, 9e9
    for _, r in df.iterrows():
        try:
            iv = float(r["impliedVolatility"])
            k = float(r["strike"])
        except (TypeError, ValueError, KeyError):
            continue
        if not (0.01 < iv < 5.0):
            continue
        d = abs(float(bs.delta(spot, k, T, iv, call=call)))
        if abs(d - target_delta) < bestd:
            best, bestd = k, abs(d - target_delta)
    return best


# -------------------------------------------------------------- the decision ---

def _trend(px):
    """The technical read. DEMOTED to a confirming voter -- it can no longer lead.

    Kept because a name in an aligned trend does tend to continue, at roughly a 55-60%
    hit rate over weeks. Not kept as a reason to trade on its own, because 55-60% is
    exactly the number that produced eight bearish cards on a flat tape.
    """
    c = px["close"]
    last = float(c.iloc[-1])
    s50 = float(c.tail(50).mean())
    s200 = float(c.tail(200).mean()) if len(c) >= 200 else s50
    m20 = last / float(c.iloc[-21]) - 1 if len(c) > 21 else 0.0
    m60 = last / float(c.iloc[-61]) - 1 if len(c) > 61 else 0.0
    score = float(np.tanh((m60 * 2 + m20) * 3))
    if last > s50 > s200:
        score = min(1.0, score + 0.20)
    elif last < s50 < s200:
        score = max(-1.0, score - 0.20)
    return {"score": round(score, 3), "last": round(last, 2),
            "m20": round(m20 * 100, 1), "m60": round(m60 * 100, 1),
            "above50": last > s50, "above200": last > s200,
            "hi20": round(float(px["high"].tail(20).max()), 2),
            "lo20": round(float(px["low"].tail(20).min()), 2)}


def _macro_view(macro, tk):
    """The overlay's verdict on this name: (+1|-1|0, themes, why) or a stand-down.

    A ticker named by two themes pointing opposite ways is a CONFLICT and is stood down.
    That is a real disagreement in the macro read, and taking it at half size is how you
    lose slowly with a good-sounding reason.
    """
    hits = desk_notes.theme_for(macro, tk)
    if not hits:
        return {"side": 0, "themes": [], "why": None,
                "stand_down": "no desk-note theme names this ticker"}
    sides = {s for _, s in hits}
    if len(sides) > 1:
        labels = " vs ".join(t["label"] for t, _ in hits)
        return {"side": 0, "themes": [t for t, _ in hits], "why": None,
                "stand_down": f"the overlay contradicts itself here — {labels}"}
    side = hits[0][1]
    # A `dispersion` theme is explicitly not a directional view on the whole name.
    stances = {t.get("stance") for t, _ in hits}
    ts = [t for t, _ in hits]
    why = " ".join(t["why"] for t in ts)
    return {"side": side, "themes": ts, "why": why, "stances": sorted(stances),
            "stand_down": None}


TREND_CONFLICT = 0.35


def _decide(macro_view, trend, own_catalyst=None):
    """Macro leads, trend confirms. Neither is allowed to overrule the other silently.

    THE CATALYST EXCEPTION. A hard macro-versus-tape disagreement normally stands the name
    down -- that is defect 3 being fixed, and it is right most weeks. It is WRONG into a
    dated event on that name. AVGO went into its own print down 7% over 60 days while the
    overlay called it the week's most important AI report: that is not a reason to skip
    the week, it is a reason not to express it directionally. So the conflict routes the
    card to a volatility structure and prints the disagreement on it, rather than
    discarding the only real catalyst on the board.
    """
    if macro_view["stand_down"]:
        return None, macro_view["stand_down"], False
    side = macro_view["side"]
    t = trend["score"]
    clash = (side > 0 and t < -TREND_CONFLICT) or (side < 0 and t > TREND_CONFLICT)
    if clash:
        msg = (f"the overlay argues for {'upside' if side > 0 else 'downside'} but the tape "
               f"disagrees hard (trend {t:+.2f}, {trend['m60']:+.0f}% over 60d)")
        if not own_catalyst:
            return None, msg + " — stood down", False
        return ("bullish" if side > 0 else "bearish"), \
               (msg + f", so this is expressed as a volatility trade around "
                      f"{own_catalyst['label']}, not a directional one"), True
    conf = "confirmed by the tape" if (side > 0) == (t > 0) and abs(t) > 0.1 else \
           "not confirmed by the tape either way"
    return ("bullish" if side > 0 else "bearish"), conf, False


# --------------------------------------------------------------- structures ---

def _vertical(calls, puts, spot, dte, ladder, inc, bullish, debit):
    """A real, listed, non-degenerate vertical. Returns (card_bits, refusal).

    THE ZERO-WIDTH GUARD. The long and short legs are snapped separately and the short is
    forbidden from landing on the long's strike. If the ladder is too coarse to place a
    real spread on this name at this price, the card is REFUSED. That is what should have
    happened to "Buy 14P / Sell 14P".
    """
    # debit bullish -> call debit; debit bearish -> put debit
    # credit bullish -> put credit;  credit bearish -> call credit
    df = (calls if bullish else puts) if debit else (puts if bullish else calls)
    side = _side_ladder(df)
    if len(side) < 2:
        return None, "fewer than two strikes listed on the side this structure needs"

    if debit:
        long_k = _snap(side, spot)
        if long_k is None:
            return None, "no listed strike near spot"
        width_target = max(inc or 1.0, spot * 0.05)
        tgt = long_k + width_target if bullish else long_k - width_target
        short_k = _snap(side, tgt, exclude={long_k})
    else:
        short_k = _delta_strike(df, spot, dte,
                                (SHORT_DELTA_LO + SHORT_DELTA_HI) / 2, call=not bullish)
        if short_k is None:
            return None, "could not place a short strike in the 16-30 delta band"
        width_target = max(inc or 1.0, spot * 0.05)
        tgt = short_k - width_target if bullish else short_k + width_target
        long_k = _snap(side, tgt, exclude={short_k})

    if long_k is None or short_k is None:
        return None, "the listed ladder has no second strike to pair with"
    width = abs(long_k - short_k)
    if width <= 0:
        return None, "both legs snapped to the same listed strike — no spread exists here"
    if inc and width < inc - 1e-9:
        return None, f"the only pairing is narrower than the ${inc:g} listed increment"

    lq, e1 = _leg_quote(df, long_k, buying=debit)
    if e1:
        return None, e1
    sq, e2 = _leg_quote(df, short_k, buying=not debit)
    if e2:
        return None, e2

    net = (lq["price"] - sq["price"]) if debit else (sq["price"] - lq["price"])
    if net <= 0:
        return None, ("priced at or below zero on real bid/ask once each leg is filled the "
                      "way it would actually fill — no edge to take")
    if not debit and net >= width:
        return None, "the credit exceeds the width, which means the quotes are stale"

    right = "C" if (bullish == debit) else "P"
    if debit:
        legs = f"Buy {long_k:g}{right} / Sell {short_k:g}{right}"
        max_risk, max_reward = net, width - net
    else:
        legs = f"Sell {short_k:g}{right} / Buy {long_k:g}{right}"
        max_risk, max_reward = width - net, net

    # THE BINDING EXECUTION GATE. Half the bid-ask on each leg is what getting in and out
    # actually costs. Measured against the money at risk, it is the number that decides
    # whether an edge survives the trade -- which is the single lesson this repo paid the
    # most to learn.
    cost = 2 * (lq["half_spread"] + sq["half_spread"])       # in AND out, both legs
    cost_pct = (cost / max_risk * 100) if max_risk > 0 else 999
    if cost_pct > MAX_TRADE_COST_PCT:
        return None, (f"round-trip spread costs {cost_pct:.0f}% of the ${max_risk*100:.0f} at "
                      f"risk (limit {MAX_TRADE_COST_PCT:.0f}%) — the execution eats the trade")

    return {"legs": legs, "width": round(width, 2), "net": round(net, 2),
            "debit": debit, "right": right,
            "long_strike": long_k, "short_strike": short_k,
            "max_risk": round(max_risk * 100, 0), "max_reward": round(max_reward * 100, 0),
            "rr": round(max_reward / max_risk, 2) if max_risk > 0 else None,
            "cost_pct": round(cost_pct, 1),
            "worst_spread_pct": max(lq["spread_pct"], sq["spread_pct"])}, None


def _calendar(tk, spot, front_exp, front_dte, back_exp, ladder, calls_f, calls_b, bullish):
    """Sell the expensive front week, own the cheaper back. The desk's own NVDA structure.

    "Aug. 28 ATM IV is around 82% versus ~45% by Sep. 18, making call calendars attractive
    for a contained bullish move." This fires only when the term structure is genuinely
    that shape, measured, not assumed.
    """
    if calls_b is None or not len(calls_b):
        return None, "no back-month chain to own"
    # The strike must be listed in BOTH expiries or it is not a calendar.
    shared = sorted(set(_side_ladder(calls_f)) & set(_side_ladder(calls_b)))
    if len(shared) < 1:
        return None, "the two expiries share no listed strike"
    k = _snap(shared, spot * (1.02 if bullish else 0.98))
    if k is None:
        return None, "no listed strike near the calendar centre"
    sq, e1 = _leg_quote(calls_f, k, buying=False)
    if e1:
        return None, f"front leg: {e1}"
    lq, e2 = _leg_quote(calls_b, k, buying=True)
    if e2:
        return None, f"back leg: {e2}"
    net = lq["price"] - sq["price"]
    if net <= 0:
        return None, "the back month is not more expensive than the front on real quotes"
    cost = 2 * (lq["half_spread"] + sq["half_spread"])       # in AND out, both legs
    cost_pct = cost / net * 100
    if cost_pct > MAX_TRADE_COST_PCT * 2:
        # A calendar's risk IS its debit, so the same cost is a bigger share of it. The
        # limit is doubled rather than dropped, and the number is printed on the card.
        return None, (f"round-trip spread costs {cost_pct:.0f}% of the ${net*100:.0f} debit "
                      f"— the execution eats the trade")
    return {"legs": f"Sell {k:g}C {front_exp} / Buy {k:g}C {back_exp}",
            "width": None, "net": round(net, 2), "debit": True, "right": "C",
            "long_strike": k, "short_strike": k,
            "max_risk": round(net * 100, 0), "max_reward": None,
            "rr": None, "calendar": True, "cost_pct": round(cost_pct, 1),
            "worst_spread_pct": max(lq["spread_pct"], sq["spread_pct"])}, None


def _exits(struct, trend, direction, spot, implied_move):
    """Target, stop, and the PRICE that proves the idea wrong.

    Not one card in the old snapshot carried any of these. A trade you cannot lose on a
    stated level is a trade you hold until it is a different, worse trade.
    """
    # Both a SENTENCE and a NUMBER. The sentence is what you read; the number is what
    # `weekly_book` compares the live mark against every cycle. Deriving the number
    # separately in the tracker would let the two drift, and then the page would say
    # "target 6.00" while the tracker closed the trade at something else.
    if struct.get("calendar"):
        target_net = round(struct["net"] * 1.30, 2)
        stop_net = round(struct["net"] * 0.50, 2)
        target = f"close at {target_net:.2f} (+30% on the debit), or the morning after the catalyst"
        stop = f"close at {stop_net:.2f} (-50% of the debit)"
    elif struct["debit"]:
        target_net = round(struct["width"] * 0.6, 2)
        stop_net = round(struct["net"] * 0.50, 2)
        target = (f"close at {target_net:.2f} "
                  f"(60% of the ${struct['width']:g} width)")
        stop = f"close at {stop_net:.2f} (-50% of the {struct['net']:.2f} debit)"
    else:
        target_net = round(struct["net"] * 0.45, 2)
        stop_net = round(struct["net"] * 2.0, 2)
        target = f"buy it back at {target_net:.2f} (keep ~55% of the credit)"
        stop = (f"close at {stop_net:.2f}, 2x the credit, or if "
                f"{struct['short_strike']:g} trades through")

    if direction == "bullish":
        level = trend["lo20"]
        inval = (f"a close below {level:g} — the 20-day low. Below that the tape is no "
                 f"longer confirming the macro read and the reason for the trade is gone.")
    else:
        level = trend["hi20"]
        inval = (f"a close above {level:g} — the 20-day high. Above that the tape is no "
                 f"longer confirming the macro read and the reason for the trade is gone.")

    if implied_move:
        inval += (f" The week is pricing a {implied_move:.1f}% move, so size for that, "
                  f"not for the move you want.")
    return {"target": target, "stop": stop, "invalidation": inval,
            "invalidation_level": level,
            "target_net": target_net, "stop_net": stop_net}


# ------------------------------------------------------------------- the run ---

def build_card(tk, macro, catalysts, index_short_gamma):
    """One candidate, all the way through. Returns (card, refusal_reason)."""
    view = _macro_view(macro, tk)
    px = _hist(tk)
    if px is None:
        return None, {"ticker": tk, "why": "no usable price history"}
    trend = _trend(px)
    spot = trend["last"]

    own = [c for c in catalysts
           if tk.upper() in [x.upper() for x in (c.get("tickers") or [])]]
    direction, conf, vol_only = _decide(view, trend, own[0] if own else None)
    if direction is None:
        return None, {"ticker": tk, "why": conf, "themes":
                      [t["label"] for t in view.get("themes") or []]}

    macro_cats = [c for c in catalysts if not c.get("tickers")]
    front, fdte, exp_why = _pick_weekly(tk, own, macro_cats)
    if front is None:
        return None, {"ticker": tk, "why": exp_why}

    calls_f, puts_f = _chain(tk, front)
    if calls_f is None or not len(calls_f):
        return None, {"ticker": tk, "why": f"no readable chain for {front}"}
    ladder, inc = _ladder(calls_f, puts_f)
    if len(ladder) < 4:
        return None, {"ticker": tk, "why": f"only {len(ladder)} listed strikes for {front}"}

    iv_front = _atm_iv(calls_f, puts_f, spot)
    rv = _realised_vol(px["close"])
    imove = _implied_move(calls_f, puts_f, spot, ladder)

    back, bdte = _pick_back(tk, fdte)
    calls_b = None
    iv_back = None
    if back:
        calls_b, puts_b = _chain(tk, back)
        iv_back = _atm_iv(calls_b, puts_b, spot)
    term = round(iv_front / iv_back, 2) if (iv_front and iv_back) else None

    rich = bool(iv_front and rv and iv_front > rv * IV_RICH_VS_RV)
    cheap = bool(iv_front and rv and iv_front < rv * IV_CHEAP_VS_RV)
    bullish = direction == "bullish"

    # --- the structure choice, in the order the evidence supports ---------------
    tried = []
    struct = err = None
    covers_catalyst = (exp_why or "").startswith("covers")

    want_calendar = calls_b is not None and (
        (term and term >= TERM_RICH and covers_catalyst) or vol_only)
    if want_calendar:
        struct, err = _calendar(tk, spot, front, fdte, back, ladder, calls_f, calls_b, bullish)
        kind = ("Calendar — sell the event week, own the month",
                (f"front ATM IV {iv_front:.0f}% against {iv_back:.0f}% at {bdte}d "
                 f"({term:.2f}x). " if term else "")
                + "The event premium sits in the front week, so the trade is to sell that "
                  "and own the cheaper longer-dated view with defined risk. This is the "
                  "structure the desk itself put on for NVDA's print.")
        if err:
            tried.append(f"calendar: {err}")
            struct = None

    if struct is None and vol_only:
        # The whole reason for this card was that the direction is contested. Falling
        # back to a directional vertical would take exactly the bet just ruled out.
        return None, {"ticker": tk,
                      "why": f"{conf}; and the calendar could not be built — "
                             + "; ".join(tried)}

    if struct is None:
        use_debit = not rich if (rich or cheap) else True
        struct, err = _vertical(calls_f, puts_f, spot, fdte, ladder, inc, bullish, use_debit)
        if err:
            tried.append(f"{'debit' if use_debit else 'credit'} vertical: {err}")
            struct, err2 = _vertical(calls_f, puts_f, spot, fdte, ladder, inc,
                                     bullish, not use_debit)
            if err2:
                tried.append(f"{'credit' if use_debit else 'debit'} vertical: {err2}")
                return None, {"ticker": tk, "why": "; ".join(tried)}
            use_debit = not use_debit
        band = ("rich" if rich else "cheap" if cheap else "fair")
        if use_debit:
            kind = (f"{'Call' if bullish else 'Put'} debit spread",
                    f"front-week IV {iv_front:.0f}% against {rv:.0f}% realised is {band}, so "
                    f"paying for the move is the cheaper side of the trade. Defined risk.")
        else:
            kind = (f"{'Put' if bullish else 'Call'} credit spread",
                    f"front-week IV {iv_front:.0f}% against {rv:.0f}% realised is {band}, so "
                    f"the premium is worth collecting. Short strike placed in the 16-30 delta "
                    f"band, the only band this repo measured positive.")

    exits = _exits(struct, trend, direction, spot, imove)

    # A stand-alone range trade is refused outright while the index is short gamma. That
    # is the one dealer-gamma finding that survived: below the flip, realised range came
    # in at 1.139x implied, t = -13.2. Selling range into that is selling the wrong side
    # of a measured effect.
    warn = None
    if not struct["debit"] and index_short_gamma:
        warn = ("NDX is below its gamma flip, so dealers hedge WITH the move and realised "
                "range measured 1.139x implied (t = -13.2). This is a directional credit "
                "spread, not a range trade, but size it knowing range is expanding.")

    return {
        "ticker": tk, "spot": spot, "direction": direction,
        "expiry": front, "dte": fdte, "expiry_why": exp_why,
        "structure": kind[0], "structure_why": kind[1],
        "legs": struct["legs"], "net": struct["net"], "width": struct.get("width"),
        "max_risk_usd": struct["max_risk"], "max_reward_usd": struct.get("max_reward"),
        "rr": struct.get("rr"), "is_debit": struct["debit"],
        "is_calendar": bool(struct.get("calendar")), "vol_only": vol_only,
        "cost_pct": struct.get("cost_pct"),
        "worst_spread_pct": struct["worst_spread_pct"],
        # The legs in machine-readable form. `weekly_book` re-prices exactly these
        # contracts every cycle, so the tracked position is the recommended one and not
        # a re-derivation that could quietly pick different strikes.
        "long_strike": struct["long_strike"], "short_strike": struct["short_strike"],
        "right": struct["right"],
        "back_expiry": back if struct.get("calendar") else None,
        "iv_front": round(iv_front, 1) if iv_front else None,
        "iv_back": round(iv_back, 1) if iv_back else None,
        "term_ratio": term, "rvol": round(rv, 1) if rv else None,
        "implied_move_pct": round(imove, 1) if imove else None,
        "themes": [{"label": t["label"], "stance": t.get("stance"),
                    "basis": t.get("basis"), "why": t["why"]} for t in view["themes"]],
        "macro_why": view["why"], "tape": conf,
        "trend": trend, "warn": warn, **exits,
    }, None


def _market_open():
    try:
        import session
        return bool(session.awake())
    except Exception:                                         # noqa: BLE001
        return None


def run(force=False):
    """Every card, plus every refusal and its reason. Refusals are the useful half.

    AFTER THE BELL, THE LAST GOOD BOOK STANDS. Quotes widen the moment the market shuts,
    so a cycle that runs at 18:00 prices every leg off something nobody would trade at:
    the execution gate then rejects almost everything, and a page that had six cards at
    15:55 shows none at 18:05 for no reason connected to the market. Worse, the few that
    survive carry a net debit that is fiction.

    So outside market hours this keeps the snapshot from the last open session rather than
    replacing it, and says on the snapshot that it is doing so. `force=True` overrides,
    for testing.
    """
    if not force and _market_open() is not True:
        prev, st = snapshots.read(OUT)
        if st in ("ok", "stale") and prev and prev.get("ok") and prev.get("cards"):
            prev = dict(prev)
            prev["held_from"] = prev.get("as_of")
            prev["held_note"] = (
                "Held from the last open session. After the bell the bid-ask widens to "
                "something nobody trades at, so re-pricing these legs now would replace a "
                "real book with a fictional one.")
            snapshots.write(OUT, prev)
            print(f"weekly: market closed — held {len(prev['cards'])} card(s) "
                  f"from {prev.get('held_from')}")
            return prev

    macro, status = desk_notes.overlay()
    if status != "ok":
        why, fix = snapshots.explain(desk_notes.FILE, status)
        out = {"ok": False, "as_of": _now().strftime("%Y-%m-%d %H:%M ET"),
               "cards": [], "refusals": [], "macro_as_of": None,
               "blocked": f"The macro overlay is {status}. {why}", "fix": fix}
        snapshots.write(OUT, out)
        print(f"weekly: BLOCKED — overlay {status}")
        return out

    cats = desk_notes.catalysts(macro, within_days=DTE_MAX)
    # Tag the catalysts that belong to one name, so a QQQ card is not routed to AVGO's
    # earnings expiry and vice versa.
    for c in cats:
        lab = (c.get("label") or "").upper()
        c["tickers"] = [t for t in UNIVERSE if lab.startswith(t + " ")]

    short_gamma = _index_short_gamma()

    cards, refusals = [], []
    for tk in UNIVERSE:
        try:
            card, why = build_card(tk, macro, cats, short_gamma)
        except Exception as e:                                # noqa: BLE001
            refusals.append({"ticker": tk, "why": f"{type(e).__name__}: {str(e)[:120]}"})
            continue
        (cards.append(card) if card else refusals.append(why))

    # Rank by how much is actually behind the card: a stated theme, tape confirmation,
    # a real catalyst in the window, and an execution cost that is not eating the edge.
    def rank(c):
        s = 2.0 * len(c["themes"])
        s += 1.5 if "confirmed" in (c["tape"] or "") and "not " not in c["tape"] else 0
        s += 1.5 if "covers" in (c["expiry_why"] or "") else 0
        s += 1.0 if (c["rr"] or 0) >= 1.0 else 0
        s -= (c["worst_spread_pct"] or 0) / 20.0
        return s

    cards.sort(key=rank, reverse=True)
    out = {
        "ok": True,
        "as_of": _now().strftime("%Y-%m-%d %H:%M ET"),
        "macro_as_of": macro.get("as_of"),
        "macro_age_h": round((desk_notes.age_min(macro) or 0) / 60, 1),
        "regime_line": macro.get("regime_line"),
        "catalysts": [{k: v for k, v in c.items() if k != "date_obj"} for c in cats],
        "index_short_gamma": short_gamma,
        "index_read": index_read(macro),
        "cards": cards[:MAX_CARDS],
        "refusals": refusals,
        "n_considered": len(UNIVERSE),
    }
    snapshots.write(OUT, out)
    print(f"weekly {out['as_of']}: {len(out['cards'])} cards, "
          f"{len(refusals)} refused, from {len(UNIVERSE)} names")
    for c in out["cards"]:
        print(f"  {c['ticker']:5} {c['direction']:8} {c['expiry']} ({c['dte']}d)  "
              f"{c['structure']:38} {c['legs']}")
    for r in refusals:
        print(f"    - {r.get('ticker','?'):5} {r.get('why','')[:110]}")
    return out


def index_read(macro):
    """What the macro says about NDX ITSELF, which is usually "not directionally".

    This exists because the honest answer for the index is a REFUSAL, and a refusal that
    is silently filtered out of a list of cards looks identical to a bug. The old panel's
    failure mode was the opposite one -- it always had something to say -- so saying
    "there is no index trade here, and here is precisely why" is the point, not a gap.
    """
    p, st = snapshots.read("periscope_NDX.json")
    theme = next((t for t in desk_notes.themes(macro)
                  if t.get("key") == "ndx_multiple_hurdle"), None)
    rows = []
    if theme:
        rows.append({"k": theme["label"], "v": "", "sub": theme["why"]})

    hurdle = desk_notes.driver(macro, "us10y")
    if hurdle:
        rows.append({"k": "The hurdle", "v": f"{hurdle.get('label')} {hurdle.get('level')}",
                     "sub": hurdle.get("note")})

    if st == "ok" and p:
        spot, flip = p.get("spot"), p.get("gamma_flip")
        try:
            below = float(spot) < float(flip)
            rows.append({
                "k": "Live NDX gamma",
                "v": f"{'below' if below else 'above'} the flip",
                "sub": (f"Spot {float(spot):,.0f} against a flip at {float(flip):,.0f}, "
                        f"put wall {p.get('put_wall')}, call wall {p.get('call_wall')}. "
                        + ("Dealers are short gamma, so they hedge WITH the move and "
                           "realised range measured 1.139x implied (t = -13.2). Selling "
                           "range into that is the wrong side of the one dealer-gamma "
                           "result that survived."
                           if below else
                           "Dealers are long gamma, so moves get damped and range "
                           "compresses. That is a range statement, never a direction.")),
                "severity": "watch" if below else "info"})
        except (TypeError, ValueError):
            pass

    rows.append({
        "k": "Directional index trade this week", "v": "NONE", "severity": "stop",
        "sub": ("The two forces on NDX point opposite ways and both are real: AI earnings "
                "are converting to revenue while the 10y caps what any multiple is worth. "
                "That is a dispersion setup, so the trades are on the NAMES the overlay "
                "can argue for, and there is no index card. This repo also measured no "
                "directional edge in ~340,000 tests, so an index direction here would be "
                "invented, not found.")})
    return {"rows": rows, "has_periscope": st == "ok"}


def _index_short_gamma():
    """Is NDX below its gamma flip right now? None when unreadable — never assumed."""
    p, st = snapshots.read("periscope_NDX.json")
    if st != "ok" or not p:
        return None
    spot, flip = p.get("spot"), p.get("gamma_flip")
    try:
        return float(spot) < float(flip)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    run()
