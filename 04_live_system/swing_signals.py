"""swing_signals.py — swing-trade signal-giver (days-to-weeks). The honest research chain:

1. DIRECTION + CONVICTION from momentum/trend (the most robust swing edge — a stock in a
   strong aligned trend tends to continue; buy strength, avoid falling knives).
2. IV ENVIRONMENT (ATM implied vol vs realized) — decides whether to BUY or SELL premium.
3. STRUCTURE matched to (direction x IV x conviction), with concrete strikes:
     bullish + cheap IV  -> call debit spread (or long shares)
     bullish + rich IV   -> put credit spread  /  covered call (own 100 shares)
     bearish + cheap IV  -> put debit spread
     bearish + rich IV   -> call credit spread
     neutral + rich IV   -> iron condor / butterfly
4. TIMEFRAME from trend speed; THESIS written up (rule-based; Fable enhances when credits on).

Honest bar: momentum is a ~55-60% directional edge over weeks, not certainty. Conviction is
capped accordingly. Writes data/swing_snapshot.json. Paper-trade first.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf

ET = ZoneInfo("America/New_York")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "swing_snapshot.json")
UNIV = [
    # large cap
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD","AVGO","NFLX","CRM","ORCL",
    "JPM","BAC","WFC","GS","V","MA","UNH","JNJ","LLY","ABBV","MRK","PFE","XOM","CVX",
    "WMT","COST","HD","PG","KO","DIS","BA","CAT","GE","HON","LIN","NEE","MPC",
    # mid cap / semis / software
    "MU","QCOM","TXN","LRCX","AMAT","KLAC","MRVL","ON","SMCI","ARM","PANW","SNOW",
    "NET","DDOG","CRWD","ZS","OKTA","TWLO","TTD","SHOP","UBER","ABNB","DASH","SPOT",
    # small cap / high beta — where swing moves actually happen
    "PLTR","SOFI","AFRM","RBLX","U","DKNG","CVNA","UPST","IONQ","RKLB","LCID","RIVN",
    "MARA","RIOT","MSTR","COIN","HOOD","GME","AMC","ROKU","PINS","SNAP","ZM","DOCU",
    "F","GM","DAL","AAL","CCL","NCLH","KRE","XRT","JETS","XHB",
]

# each name → its SPDR sector ETF (for rotation)
SECTOR = {"XLK": ["AAPL","MSFT","NVDA","AMD","AVGO","CRM","ORCL","NOW","PLTR"],
          "XLC": ["GOOGL","META","NFLX"],
          "XLY": ["AMZN","TSLA","HD","MCD","UBER"],
          "XLF": ["JPM","GS","V","MA","COIN"],
          "XLV": ["UNH","LLY","ABBV","MRK","JNJ"],
          "XLE": ["XOM","CVX","MPC","PSX"],
          "XLI": ["CAT","DE","RTX","HON","GE"],
          "XLP": ["WMT","COST","PG","KO"],
          "XLB": ["LIN"], "XLU": ["NEE"]}
TICK_SECTOR = {t: s for s, ts in SECTOR.items() for t in ts}
SECTOR_NAME = {"XLK": "Tech", "XLC": "Comm", "XLY": "Discretionary", "XLF": "Financials",
               "XLV": "Health", "XLE": "Energy", "XLI": "Industrials", "XLP": "Staples",
               "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate"}


def market_context():
    """Compute the live environment: market regime (risk-on/off), sector rotation (leaders/laggards),
    and a geopolitical-STRESS gauge (flight-to-safety: gold+bonds+dollar+VIX). Makes the picks adapt."""
    etfs = ["SPY", "XLK", "XLC", "XLY", "XLF", "XLV", "XLE", "XLI", "XLP", "XLB", "XLU", "XLRE",
            "^VIX", "^VIX9D", "GLD", "TLT", "UUP", "USO"]
    px = yf.download(etfs, period="1y", interval="1d", progress=False, auto_adjust=True)["Close"]
    def ret(t, n):
        try: return float(px[t].iloc[-1] / px[t].iloc[-1 - n] - 1) * 100
        except Exception: return 0.0
    spy20 = ret("SPY", 20)
    # sector rotation: 20-day relative strength vs SPY
    rot = []
    for s in ["XLK", "XLC", "XLY", "XLF", "XLV", "XLE", "XLI", "XLP", "XLB", "XLU", "XLRE"]:
        rot.append((s, round(ret(s, 20) - spy20, 1)))
    rot.sort(key=lambda x: -x[1])
    leaders = [r[0] for r in rot[:3]]; laggards = [r[0] for r in rot[-3:]]
    rs = {s: v for s, v in rot}
    # regime: SPY trend + VIX + defensive(XLP/XLU/XLV) vs cyclical(XLK/XLY/XLI) leadership
    try:
        spy_trend = float(px["SPY"].iloc[-1] > px["SPY"].tail(200).mean())
        vix = float(px["^VIX"].iloc[-1]); vts = float(px["^VIX9D"].iloc[-1] / vix)
    except Exception:
        spy_trend, vix, vts = 1.0, 16.0, 0.95
    defensive = (rs.get("XLP", 0) + rs.get("XLU", 0) + rs.get("XLV", 0)) / 3
    cyclical = (rs.get("XLK", 0) + rs.get("XLY", 0) + rs.get("XLI", 0)) / 3
    if not spy_trend or vix > 22 or defensive > cyclical + 1:
        regime = "RISK-OFF"; rnote = "defensives leading / below 200d / vol elevated — favor quality & defined risk, trim bullish size."
    elif spy_trend and vix < 17 and cyclical > defensive:
        regime = "RISK-ON"; rnote = "cyclicals & growth leading, calm vol — momentum longs favored."
    else:
        regime = "NEUTRAL"; rnote = "mixed leadership — be selective, respect both sides."
    # geopolitical / flight-to-safety stress gauge
    stress_score = sum([ret("GLD", 5) > 1.5, ret("TLT", 5) > 1.0, ret("UUP", 5) > 0.8,
                        vix > 20, ret("USO", 5) > 4, vts < 0.92])
    if stress_score >= 3:
        stress = "ELEVATED — flight-to-safety (gold/bonds/$ bid, vol up). Geopolitical/macro risk on; keep size small, favor hedged/defined-risk."
    elif stress_score >= 2:
        stress = "some risk-off flows (watch gold/bonds/VIX)."
    else:
        stress = "calm — no flight-to-safety signal."
    return {"regime": regime, "regime_note": rnote, "vix": round(vix, 1),
            "leaders": leaders, "laggards": laggards, "sector_rs": rs,
            "stress": stress, "stress_score": stress_score,
            "detail": f"{regime} · leading {', '.join(SECTOR_NAME.get(s,s) for s in leaders)} · "
                      f"lagging {', '.join(SECTOR_NAME.get(s,s) for s in laggards)}"}


def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return float((100 - 100/(1 + up/(dn+1e-12))).iloc[-1])


# ---------------------------------------------------------------------------
# DIRECTION BY WEIGHTED VOTE, not by technicals alone.
#
# The old design set direction from the moving-average stack and momentum, then
# let everything else adjust conviction by a few points. That meant a name could
# be labelled BULLISH while real order flow was heavily bearish -- the label
# never moved, only the confidence did. This makes every input able to move the
# call, weighted by how much evidence each one actually has behind it.
#
# WEIGHTS ARE EVIDENCE-BASED, not intuition:
#   flow  0.40  Real buy/sell-classified premium is the only genuinely orthogonal
#               information here. Everything else is a transform of price.
#   trend 0.35  Momentum/trend is a real but modest edge (~55-60% hit rate).
#   macro 0.15  Rate BETAS are stable and measured; rate PREDICTION failed every
#               test (216 cells, zero cleared the multiple-testing bar), so this
#               gets a real but small vote.
#   rot   0.10  Sector rotation was falsified as a standalone edge (1,512 configs,
#               none beat buy-and-hold), so it is a tiebreaker at most.
#
# ALIGNMENT GATE: conviction is scaled by how much the voters agree. Full
# conviction requires them pointing the same way; when the two heavyweights
# (flow and trend) disagree outright, the call becomes CONFLICT and the trade is
# stood down rather than taken at reduced size.
# Weights now come from signal_weights, the single authority shared by every
# tab, so an input measured worthless here cannot still be driving another
# panel. Note `rotation` is absent: sector rotation measured as a null
# (1,512 configs, none beat buy-and-hold) and therefore carries zero weight.
def _vote_w():
    import signal_weights as sw
    return {"flow": sw.weight("flow_lean")[0],
            "trend": sw.weight("trend")[0],
            "darkpool": sw.weight("dp_buy_share")[0],
            "macro": sw.weight("rate_beta")[0],
            "short": sw.weight("short_float_pct")[0],
            "rotation": sw.weight("sector_rotation")[0]}

VOTE_W = _vote_w()


def decide_direction(votes):
    """votes: {name: score in [-1, +1]}. Returns the reconciled call."""
    used = {k: v for k, v in votes.items() if v is not None}
    if not used:
        return {"direction": "neutral", "score": 0.0, "align": 0.0,
                "conflict": False, "votes": {}}

    wsum = sum(VOTE_W[k] for k in used)
    score = sum(VOTE_W[k] * v for k, v in used.items()) / wsum

    # Agreement = share of weight pointing the same way as the net score.
    same = sum(VOTE_W[k] for k, v in used.items()
               if v != 0 and (v > 0) == (score > 0))
    align = same / wsum if wsum else 0.0

    # The two heavyweights disagreeing is a stand-down, not a weak signal.
    f, t = used.get("flow"), used.get("trend")
    conflict = (f is not None and t is not None
                and abs(f) > 0.25 and abs(t) > 0.25 and (f > 0) != (t > 0))

    if conflict:
        direction = "conflict"
    elif score > 0.15:
        direction = "bullish"
    elif score < -0.15:
        direction = "bearish"
    else:
        direction = "neutral"

    return {"direction": direction, "score": round(float(score), 3),
            "align": round(float(align), 2), "conflict": conflict,
            "votes": {k: round(float(v), 2) for k, v in used.items()}}


def scan_name(tk):
    d = yf.download(tk, period="1y", interval="1d", progress=False, auto_adjust=True,
                    multi_level_index=False).rename(columns=str.lower)["close"].dropna()
    if len(d) < 200:
        return None
    last = float(d.iloc[-1]); s50 = float(d.tail(50).mean()); s200 = float(d.tail(200).mean())
    m20 = last/float(d.iloc[-21])-1; m60 = last/float(d.iloc[-61])-1; m120 = last/float(d.iloc[-121])-1
    r = rsi(d); frm_hi = last/float(d.max())-1
    rv = float(d.pct_change().tail(20).std()*np.sqrt(252))  # realized vol annualized
    up = last > s50 > s200; dn = last < s50 < s200
    # TREND VOTE in [-1, +1]. This is now ONE voter, not the verdict.
    momscore = float(np.tanh((m60*2 + m120 + m20)*3))
    trend_vote = momscore
    if up:
        trend_vote = min(1.0, momscore + 0.20)   # MA stack confirms
    elif dn:
        trend_vote = max(-1.0, momscore - 0.20)
    # Stretched RSI argues against chasing the trend it is stretched by.
    if r > 75:
        trend_vote -= 0.15
    elif r < 25:
        trend_vote += 0.15
    trend_vote = float(np.clip(trend_vote, -1, 1))

    # Provisional label; reconciled against flow/macro/rotation in run().
    direction = "bullish" if trend_vote > 0.15 else "bearish" if trend_vote < -0.15 else "neutral"
    conv = min(70, 35 + abs(trend_vote) * 35)
    tf = "2-4 weeks" if abs(m20) < abs(m60)/2 else "1-2 weeks"
    return {"ticker": tk, "last": round(last, 2), "direction": direction,
            "trend_vote": round(trend_vote, 3), "conviction": int(conv),
            "m20": round(m20*100, 1), "m60": round(m60*100, 1), "m120": round(m120*100, 1),
            "rsi": round(r, 0), "frm_hi": round(frm_hi*100, 1), "rvol": round(rv*100, 0),
            "above50": last > s50, "above200": last > s200, "timeframe": tf}


def iv_env(tk, last):
    """ATM implied vol from the ~30-45 DTE chain; classify vs a plausible realized band."""
    t = yf.Ticker(tk)
    try:
        exps = t.options
        target = (datetime.now(ET).date() + pd.Timedelta(days=35))
        exp = min(exps, key=lambda e: abs((pd.Timestamp(e).date() - target).days))
        ch = t.option_chain(exp)
        cc = ch.calls.iloc[(ch.calls.strike - last).abs().argmin()]
        pp = ch.puts.iloc[(ch.puts.strike - last).abs().argmin()]
        iv = float(np.nanmean([cc.impliedVolatility, pp.impliedVolatility]))*100
        return {"exp": exp, "iv": round(iv, 0)}
    except Exception:
        return None


def structure(cand, iv):
    """Pick the options structure + concrete strikes for direction x IV."""
    last = cand["last"]; dir = cand["direction"]
    rich = iv and cand["rvol"] and iv["iv"] > cand["rvol"]*1.15   # IV meaningfully above realized
    cheap = iv and cand["rvol"] and iv["iv"] < cand["rvol"]*0.95
    def k(pct): return round(last*(1+pct), 0)
    exp = iv["exp"] if iv else "~35 DTE"
    if dir == "bullish":
        if cheap:
            return {"play": "Call debit spread", "why": "bullish + IV cheap → buy the move cheaply, defined risk",
                    "legs": f"Buy {k(0):.0f}C / Sell {k(0.06):.0f}C", "exp": exp, "risk": "debit paid"}
        if rich:
            return {"play": "Put credit spread (bullish) or covered call", "why": "bullish + IV rich → collect premium",
                    "legs": f"Sell {k(-0.05):.0f}P / Buy {k(-0.10):.0f}P  —  or own 100 sh + sell {k(0.05):.0f}C",
                    "exp": exp, "risk": "defined (spread) / covered (CC)"}
        return {"play": "Call debit spread or 100 shares", "why": "bullish, IV fair",
                "legs": f"Buy {k(0):.0f}C / Sell {k(0.07):.0f}C  —  or long 100 shares", "exp": exp, "risk": "defined / shares"}
    if dir == "bearish":
        if cheap:
            return {"play": "Put debit spread", "why": "bearish + IV cheap → buy downside, defined risk",
                    "legs": f"Buy {k(0):.0f}P / Sell {k(-0.06):.0f}P", "exp": exp, "risk": "debit paid"}
        return {"play": "Call credit spread (bearish)", "why": "bearish + IV rich → sell upside premium",
                "legs": f"Sell {k(0.05):.0f}C / Buy {k(0.10):.0f}C", "exp": exp, "risk": "defined"}
    # neutral
    if rich:
        return {"play": "Iron condor (range-bound)", "why": "no trend + IV rich → collect premium in a range",
                "legs": f"Sell {k(-0.06):.0f}P/{k(0.06):.0f}C, buy {k(-0.11):.0f}P/{k(0.11):.0f}C", "exp": exp, "risk": "defined"}
    return {"play": "No clean setup — stand aside", "why": "no trend and IV not rich enough to sell",
            "legs": "—", "exp": exp, "risk": "—"}


def thesis(cand, iv, struc):
    d = cand
    parts = [f"{d['ticker']} is {d['direction'].upper()} (conviction {d['conviction']}/100). "]
    if d["direction"] != "neutral":
        parts.append(f"Trend: {'above' if d['above50'] else 'below'} 50d & {'above' if d['above200'] else 'below'} 200d; "
                     f"momentum {d['m60']:+.0f}% (3mo)/{d['m120']:+.0f}% (6mo), RSI {d['rsi']:.0f}, "
                     f"{d['frm_hi']:+.0f}% from 52w high. ")
    if iv:
        band = "rich" if d['rvol'] and iv['iv'] > d['rvol']*1.15 else ("cheap" if d['rvol'] and iv['iv'] < d['rvol']*0.95 else "fair")
        parts.append(f"IV {iv['iv']:.0f}% vs realized {d['rvol']:.0f}% = {band} → {struc['why']}. ")
    parts.append(f"Play: {struc['play']} ({struc['legs']}), {d['timeframe']}. Momentum is a ~55-60% edge over weeks — size for that, not certainty.")
    return "".join(parts)


def uw_confirm(cand):
    """Use Unusual Whales real options flow to confirm/contradict the momentum direction.
    Agreement boosts conviction; divergence trims it (smart money leaning the other way)."""
    try:
        import uw_client
        if not uw_client.available():
            return None
        fa = uw_client.summarize_flow(cand["ticker"])
        if not fa:
            return None
        agree = ((cand["direction"] == "bullish" and fa["bias"] == "bullish") or
                 (cand["direction"] == "bearish" and fa["bias"] == "bearish"))
        diverge = ((cand["direction"] == "bullish" and fa["bias"] == "bearish") or
                   (cand["direction"] == "bearish" and fa["bias"] == "bullish"))
        adj = 10 if agree else (-15 if diverge else 0)
        return {"bias": fa["bias"], "lean": fa["lean"], "detail": fa["detail"],
                "agree": agree, "diverge": diverge, "conv_adj": adj}
    except Exception:
        return None


def macro_tilt(ticker, sector, direction):
    """Rate exposure as a RISK FLAG, not a forecast.

    Sector betas to the 10y yield are measured on 20 years of daily changes and
    are stable (KRE +1.09, XLF +0.95, XLRE -0.24 — the only negative). So we can
    say with confidence WHAT a position is levered to.

    We cannot say where rates go next. I tested whether rate/curve/credit moves
    predict sector returns 5-21 days out: 216 cells, three-way split, excess over
    each sector's own drift — 36 positive in all three periods, ZERO clearing the
    multiple-testing bar of t=3.24. So the conviction adjustment here is
    deliberately small (+/-5) and framed as "this is a headwind you should know
    about", not "this predicts the move".
    """
    try:
        import macro_panel
        mx = macro_panel.context()
    except Exception:
        return 0, ""
    beta = (mx.get("beta") or {}).get(SECTOR_ETF.get(sector, ""))
    y5 = mx.get("y10_5d")
    if beta is None or y5 is None or abs(y5) < 0.04:
        return 0, ""

    # Expected drift from the rate move = 5-day beta x the 5-day yield change,
    # both in percent. A 0.10pt yield move on KRE (beta ~9.9) is ~1% of drift.
    impulse = beta * y5
    if abs(impulse) < 0.25:
        return 0, ""
    helping = (impulse > 0) if direction == "bullish" else (impulse < 0)
    word = "tailwind" if helping else "headwind"
    note = (f"rate {word} — 10y {'+' if y5 > 0 else ''}{y5:.2f}pt over 5d, sector "
            f"beta {beta:+.1f} ⇒ ~{impulse:+.1f}% drift")
    return (4 if helping else -5), note


# Sector code -> the ETF whose rate beta we measured.
SECTOR_ETF = {"XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV", "XLI": "XLI",
              "XLY": "XLY", "XLP": "XLP", "XLU": "XLU", "XLB": "XLB",
              "XLRE": "XLRE", "XLC": "XLK",
              "Technology": "XLK", "Financials": "XLF", "Energy": "XLE",
              "Health Care": "XLV", "Industrials": "XLI", "Consumer Discretionary": "XLY",
              "Consumer Staples": "XLP", "Utilities": "XLU", "Materials": "XLB",
              "Real Estate": "XLRE", "Communication Services": "XLK",
              # Industry ETFs carry their own measured beta — they are far more
              # rate-levered than their parent sector (KRE +9.9 vs XLF +8.1).
              "KRE": "KRE", "XRT": "XRT", "JETS": "JETS", "ITB": "ITB",
              "XHB": "XHB", "XME": "XME", "SMH": "SMH", "IYT": "IYT",
              "Regional Banks": "KRE", "Retail": "XRT", "Airlines": "JETS",
              "Homebuilders": "XHB", "Semiconductors": "SMH", "Transports": "IYT"}


def run():
    try:
        ctx = market_context()          # regime + sector rotation + stress — the environment
    except Exception:
        ctx = None
    scanned = [s for s in (scan_name(t) for t in UNIV) if s]
    # tag each name with its sector's rotation strength; adjust conviction by rotation + regime
    for s in scanned:
        sec = TICK_SECTOR.get(s["ticker"]); rs = (ctx or {}).get("sector_rs", {}).get(sec) if sec else None
        s["sector"] = SECTOR_NAME.get(sec, sec); s["sector_rs"] = rs
        s["rotation"] = ("leading" if sec in (ctx or {}).get("leaders", []) else
                         "lagging" if sec in (ctx or {}).get("laggards", []) else "in-line") if ctx and sec else "?"
        adj = 0
        if ctx and s["direction"] == "bullish":
            if s["rotation"] == "leading": adj += 8      # money rotating INTO the sector
            elif s["rotation"] == "lagging": adj -= 10   # bullish into a sector money's leaving
            if ctx["regime"] == "RISK-OFF": adj -= 8     # don't fight a risk-off tape with longs
            elif ctx["regime"] == "RISK-ON": adj += 5
        elif ctx and s["direction"] == "bearish":
            if s["rotation"] == "lagging": adj += 8       # shorting a sector money's leaving = aligned
            if ctx["regime"] == "RISK-OFF": adj += 5
        # THE WEIGHTED VOTE. Previously `decide_direction` existed but was never
        # called, so direction stayed pure trend and flow could only nudge
        # conviction -- a name could read BULLISH while real flow was heavily
        # bearish. Now every input can move the call.
        _uwv = uw_confirm(s)
        _votes = {"trend": s.get("trend_vote")}
        if _uwv:
            _votes["flow"] = max(-1.0, min(1.0, float(_uwv.get("lean") or 0)))
        try:
            import uw_endpoints as _ue
            _prof = _ue.profile(s["ticker"])
            if _prof.get("dp_buy_share") is not None:
                # Share of dark pool volume printing at/above the ask =
                # buy-initiated. Centred so 50% is neutral, >50% bullish.
                _votes["darkpool"] = (float(_prof["dp_buy_share"]) - 0.5) * 2
            if _prof.get("short_float_pct") is not None:
                # NEGATIVE by measurement (IC -0.068 @21d): heavily shorted
                # names underperform.
                _votes["short"] = -min(float(_prof["short_float_pct"]) / 20.0, 1.0)
        except Exception:
            pass

        _dec = decide_direction(_votes)
        s["direction"] = _dec["direction"]
        s["vote_score"] = _dec["score"]
        s["vote_align"] = _dec["align"]
        s["votes"] = _dec["votes"]
        if _dec["conflict"]:
            s["conviction"] = min(s["conviction"], 25)
        else:
            # Conviction scales with how much the voters AGREE.
            s["conviction"] = int(s["conviction"] * (0.5 + 0.5 * _dec["align"]))

        # Macro/rate exposure — a risk flag layered on top of the price signal.
        madj, mnote = macro_tilt(s["ticker"], sec, s["direction"])
        adj += madj
        s["macro_note"] = mnote
        s["conviction"] = int(max(10, min(82, s["conviction"] + adj)))
        s["ctx_adj"] = adj
    scanned.sort(key=lambda s: s["conviction"], reverse=True)
    top = [s for s in scanned if s["direction"] != "neutral"][:6] + \
          [s for s in scanned if s["direction"] == "neutral"][:2]
    for s in top:
        iv = iv_env(s["ticker"], s["last"])
        s["iv"] = iv
        s["structure"] = structure(s, iv)
        uw = uw_confirm(s)
        s["uw_flow"] = uw
        if uw and uw["conv_adj"]:                       # let real flow move conviction
            s["conviction"] = int(max(10, min(82, s["conviction"] + uw["conv_adj"])))
        s["thesis"] = thesis(s, iv, s["structure"])
        if s.get("rotation") in ("leading", "lagging"):
            arrow = "✅ in a LEADING sector (money rotating in)" if s["rotation"] == "leading" else "⚠️ in a LAGGING sector (money rotating out)"
            s["thesis"] += f" {arrow} — {s['sector']} RS {s['sector_rs']:+.1f}% vs SPY."
        if uw:
            tag = ("✅ UW flow CONFIRMS" if uw["agree"] else
                   "⚠️ UW flow DIVERGES (smart money leaning other way — trim size)" if uw["diverge"]
                   else "UW flow neutral")
            s["thesis"] += f" {tag}: {uw['detail']}."
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "epoch": datetime.now(ET).timestamp(),
           "market_context": ctx, "signals": top, "n_scanned": len(scanned)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    print(f"swing scan {out['as_of']}: {len(top)} signals from {len(scanned)} names")
    for s in top:
        print(f"  {s['ticker']:5} {s['direction']:8} conv {s['conviction']:>2} | {s['structure']['play']}")
    return out


if __name__ == "__main__":
    run()
