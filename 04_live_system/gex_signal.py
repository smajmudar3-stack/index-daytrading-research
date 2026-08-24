"""gex_signal.py — LIVE 0DTE dealer-gamma RANGE regime (the one finding that survived).

What it is: dealer Gamma Exposure (GEX) from the prior close is known before today's open and
predicts the day's INTRADAY RANGE with a monotone, every-year-stable effect over 2011-2026.
Measured against VIX9D, a real market-priced implied vol, realised range comes in at 0.843x
implied on high-gamma days against 1.139x on low, t = -13.2, significant in every four-year
sub-period. It does NOT predict direction, and it never did.

  low / negative gamma  -> dealers hedge WITH the move  -> range runs wider than implied
  high / positive gamma -> dealers hedge AGAINST it     -> range comes in tighter, price pins

WHAT THIS MODULE IS NO LONGER ALLOWED TO SAY. This docstring used to quote t=-16 and frame the
regime as the question that "most improves naked 0DTE call/put trading", and the thesis it wrote
could read "IDEAL naked-CALL day. Buy a naked CALL". Both are retired:

  - t=-16 is the rounded beta against the repo's own causal vol forecast, not against a price
    anyone can trade. The figure worth quoting is t=-13.2 against VIX9D. See docs/VERDICT_LOG.md.
  - buying 0DTE premium on ANY directional signal in this repo measured -10% to -11% per trade,
    and the "low gamma means premium has fuel" version measured -7.2% (straddle) to -19.1%
    (strangle). A wide range does not make a long option profitable; it has to beat what the
    option already costs, and it does not.
  - selling the range does not work either at real prices: the 0DTE condor gated on this regime
    is approximately break-even on 1,919 sessions of real SPXW bid/ask.

So the regime read is genuine and it is reported as a RANGE FORECAST. It is an input to a
decision made elsewhere, not an instruction, and it carries no side.

Free data: SqueezeMetrics historical GEX CSV (updates ~daily). Writes data/gex_snapshot.json.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import urllib.request

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data", "squeeze_dix_gex.csv")
DAILY = os.path.join(HERE, "data", "gex_regime_daily.csv")   # historical buckets (from gex_regime.py)
OUT = os.path.join(HERE, "data", "gex_snapshot.json")
SRC = "https://squeezemetrics.com/monitor/static/DIX.csv"


def refresh():
    try:
        req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=25).read()
        if len(data) > 50000:
            open(CSV, "wb").write(data)
            return True
    except Exception:
        pass
    return False


def _buckets():
    """Historical intraday stats by gamma quintile — the empirical map from regime -> expected day."""
    d = pd.read_csv(DAILY, parse_dates=["date"])
    d = d.dropna(subset=["gex_z"]).copy()
    d["q"] = pd.qcut(d["gex_z"], 5, labels=[1, 2, 3, 4, 5])
    b = {}
    for q in [1, 2, 3, 4, 5]:
        g = d[d["q"] == q]
        b[q] = {"range": round(g["rng"].mean() * 100, 2), "oc": round(g["oc"].mean() * 100, 2),
                "cond50": round(g["cond_50"].mean() * 100), "cond75": round(g["cond_75"].mean() * 100),
                "cond100": round(g["cond_100"].mean() * 100)}
    edges = d["gex_z"].quantile([0.2, 0.4, 0.6, 0.8]).tolist()
    negrng = round(d.loc[d["gex_z"].notna() & (d["neg_gamma"] if "neg_gamma" in d else False), "rng"].mean() * 100, 2) \
        if "neg_gamma" in d.columns and d["neg_gamma"].any() else None
    return b, edges


def _bucket_of(z, edges, buckets):
    q = 1 + sum(z > e for e in edges)
    return q, buckets[q]


def _backcheck(g, buckets, edges):
    """How did the regime do on the LAST completed session? GEX[D-1] predicted session D's range."""
    try:
        import yfinance as yf
        spy = yf.download("SPY", period="10d", interval="1d", progress=False,
                          auto_adjust=True, multi_level_index=False).rename(columns=str.lower)
        spy.index = pd.to_datetime(spy.index).tz_localize(None)
        last_day = spy.index[-1].normalize()
        # predictor = last GEX row strictly before the last completed SPY session
        prior = g[g["date"] < last_day]
        if prior.empty:
            return None
        pz = float(prior.iloc[-1]["z"])
        _, pbk = _bucket_of(pz, edges, buckets)
        row = spy.iloc[-1]
        realized = (row["high"] - row["low"]) / row["open"] * 100
        return {"date": str(last_day.date()), "predicted_range": pbk["range"],
                "realized_range": round(float(realized), 2),
                "verdict": "in line" if realized <= pbk["range"] * 1.6 else "bigger than expected"}
    except Exception:
        return None


def _uw_live():
    """Same-day LIVE regime from Unusual Whales (replaces the 1-day-lagged SqueezeMetrics read when a
    key is set). Regime from spot-vs-UW-gamma-flip + net GEX sign; expected move from UW's implied move."""
    try:
        import uw_client
        if not uw_client.available():
            return None
        import yfinance as yf
        spot = float(yf.Ticker("^SPX").fast_info["lastPrice"])
        uw = uw_client.full_read("SPX", spot)
        if not uw:
            return None
        gex = uw.get("gex") or {}
        flip = gex.get("gamma_flip"); net = gex.get("net_gex")
        im = uw.get("implied_move") or {}
        move = im.get("move_pct")                       # market's own expected 0DTE move %
        dist = (spot / flip - 1) if flip else (0.02 if (net or 0) > 0 else -0.02)
        # Same vocabulary as the baseline path below: a range forecast, never a side and never
        # an order. These three branches used to end in "naked longs have fuel", "below = puts"
        # and "sell premium around the pin"; all three are refuted at real prices, and having
        # the LIVE path say something the BASELINE path no longer said was its own bug.
        if dist < -0.001:                               # below the flip -> dealers hedge with the move
            regime = "SHORT GAMMA (live)"; stance = "wide_range"; call = "WIDE range expected"
            note = ("UW same-day: price is BELOW the zero-gamma flip, so dealers are short gamma and hedge in the "
                    "direction of the move, pushing it further. Expect a wider range than implied. This says how "
                    "big, not which way.")
        elif dist < 0.003:                              # right around the flip -> undecided
            regime = "AT/NEAR FLIP (live)"; stance = "average_range"; call = "Regime undecided"
            note = ("UW same-day: price is sitting on the zero-gamma flip. Neither regime is established, so the "
                    "range read carries no information right now. A decisive move to either side resolves it.")
        else:                                           # comfortably above flip -> dealers hedge against
            regime = "LONG GAMMA / PIN (live)"; stance = "tight_range"; call = "TIGHT range expected — pin"
            note = ("UW same-day: price is above the zero-gamma flip with net long dealer gamma, so dealers fade "
                    "moves and the index pins. Expect a tighter range than implied. This is the best-evidenced "
                    "read the system has, and it still does not convert into a profitable trade at real quotes.")
        exp_oc = move if move else None
        exp_range = round(move * 1.7, 2) if move else None
        return {"stance": stance, "regime": regime, "call": call, "note": note,
                "exp_oc": exp_oc, "exp_range": exp_range, "spot": round(spot, 2),
                "flip": flip, "net_gex": net, "flip_dist_pct": round(dist * 100, 2) if flip else None,
                "iv": im.get("iv"), "overall_bias": uw.get("overall_bias"), "dir_score": uw.get("dir_score"),
                "source": "unusualwhales"}
    except Exception:
        return None


def run():
    refresh()
    g = pd.read_csv(CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    g["z"] = (g["gex"] - g["gex"].rolling(252, min_periods=60).mean()) / g["gex"].rolling(252, min_periods=60).std()
    latest = g.iloc[-1]      # freshest close -> this is the read for the NEXT session
    gex_bn = latest["gex"] / 1e9
    z = float(latest["z"])
    neg = latest["gex"] < 0
    dix = float(latest["dix"])

    buckets, edges = _buckets()
    q, bk = _bucket_of(z, edges, buckets)

    # DIX direction tilt (high dark-pool buying + low gamma = bullish, t=+3.0 p=.003, 15yr)
    dz_series = (g["dix"] - g["dix"].rolling(252, min_periods=60).mean()) / g["dix"].rolling(252, min_periods=60).std()
    dz = float(dz_series.iloc[-1])
    if dz > 0.5 and q <= 2:
        dix_call = ("BULLISH tilt — high dark-pool buying on a low-gamma day (60% green, t=+3.0 on the "
                    "UNDERLYING). Real on the index, but it was not monetisable in 0DTE options: the move is "
                    "+12.8bp and the option costs ~0.37% of spot. Context, not a trade.")
    elif dz > 0.5:
        dix_call = "mild bullish — DIX high but gamma not low (weaker signal)"
    elif dz < -0.5:
        dix_call = "DIX low — no bullish tilt today."
    else:
        dix_call = "DIX neutral — direction from opening drive + flow only"

    # live trend + VIX context for the validated bullish signal set
    trend_up = vix_lvl = vix_ts = None
    try:
        import yfinance as yf
        p2 = yf.download(["SPY", "^VIX", "^VIX9D"], period="1y", interval="1d",
                         progress=False, auto_adjust=True)
        spyc = p2["Close"]["SPY"].dropna()
        trend_up = bool(spyc.iloc[-1] > spyc.tail(200).mean())
        vix_lvl = float(p2["Close"]["^VIX"].dropna().iloc[-1])
        vix_ts = float(p2["Close"]["^VIX9D"].dropna().iloc[-1] / vix_lvl)   # <1 = backwardation/stress
    except Exception:
        pass

    # MACRO REGIME (downside-awareness — the honest "bearish" layer: no same-day put edge, but the tail
    # is fatter in a bear/high-vol regime → momentum breaks DOWN more readily, condor tail skews down).
    if vix_lvl is not None:
        if trend_up is False and (vix_lvl > 22 or (vix_ts and vix_ts < 0.95)):
            macro_regime = "BEAR / high-vol"
            macro_note = ("Below 200d + stressed vol → downside tail elevated. Momentum breaks DOWN carry more; "
                          "puts on a flip-break work better here; condor tail-risk is to the downside (skew puts wider).")
        elif trend_up is False or vix_lvl > 20:
            macro_regime = "CAUTIOUS / choppy"
            macro_note = "No strong bull tailwind — respect both sides; don't assume dips get bought."
        else:
            macro_regime = "BULL / calm"
            macro_note = "Upward drift intact — dips tend to get bought; puts are reactive-only (flip-break)."
    else:
        macro_regime = macro_note = None

    # which VALIDATED bullish signals are firing right now (from direction_signals.py backtest)
    fired = []
    if dz > 0.5 and z < -0.5:
        fired.append(("High DIX + low gamma", 60, "+3.09"))
    if dz > 1.0:
        fired.append(("Very high DIX (z>1)", 57, "+2.65"))
    if dz > 0.5 and vix_ts is not None and vix_ts < 1.0:
        fired.append(("High DIX + backwardation (buy-the-stress)", 56, "+2.25"))
    if dz > 0.5 and trend_up:
        fired.append(("High DIX + uptrend", 55, "+2.05"))
    # NIGHT-BEFORE (DIX) direction only — a preliminary vote, reconciled with LIVE flow below.
    if fired:
        nb_best = max(w for _, w, _ in fired)
        nb_conv = min(75, nb_best + (len(fired) - 1) * 4)
        nb_bias = "bullish"
    else:
        nb_conv = 30 if dz > 0 else 20
        nb_bias = "neutral"

    # Regime label and the RANGE forecast it implies.
    #
    # `stance` used to be buy_premium / sell_premium, i.e. an order. Both directions of that
    # order are refuted at real prices (see the module docstring), so the field now names the
    # range expectation instead: wide / average / tight. Downstream code reads `stance`, so the
    # key is kept and only its vocabulary changed; anything still branching on the old values
    # will fall through to the neutral path rather than silently taking the retired branch.
    if neg:
        regime = "NEGATIVE GAMMA"; call = "WIDE range expected"
        note = ("Dealers are SHORT gamma: they buy rallies and sell dips, so their hedging runs WITH the move "
                "and amplifies it. This is the top ~9% of days for intraday range (avg ~2.4% against ~1.0% "
                "normal). That is a forecast of SIZE, not of side, and a wide range does not by itself make a "
                "long option pay: it still has to beat what the option costs, which it did not in testing.")
        stance = "wide_range"
    elif q <= 2:
        regime = f"LOW GAMMA (Q{q}/5)"; call = "Above-average range expected"
        note = ("Gamma is low, so dealer hedging dampens less and moves extend further than on a typical day. "
                "A statement about range only. No directional edge was found in this data at any horizon.")
        stance = "wide_range"
    elif q == 3:
        regime = "MID GAMMA (Q3/5)"; call = "Average range expected"
        note = ("Middle regime, no range edge in either direction. This is the regime that tells you least.")
        stance = "average_range"
    else:
        regime = f"HIGH GAMMA (Q{q}/5)"; call = "TIGHT range expected — pin"
        note = ("Dealers are LONG gamma: they sell rallies and buy dips, so their hedging runs AGAINST the move "
                "and pins the index. Smallest-range regime (avg ~0.7%), and realised range comes in at 0.843x "
                "the VIX9D-implied move against 1.139x on low-gamma days (t = -13.2). This is the strongest and "
                "best-evidenced read the system has. It still does not convert into a profitable condor at real "
                "quotes, which is itself the finding: the market has this priced.")
        stance = "tight_range"

    # SqueezeMetrics values are the 15-yr BACKTESTED BASELINE (prior close). If a UW key is set, the
    # LIVE same-day read takes over the headline regime/stance/expected-range; SM stays as the baseline.
    baseline = {"regime": regime, "stance": stance, "call": call, "note": note,
                "exp_range": bk["range"], "exp_oc": bk["oc"], "quintile": int(q),
                "source": "SqueezeMetrics prior close (15-yr baseline)"}
    uw_live = _uw_live()
    if uw_live:
        stance = uw_live["stance"]; regime = uw_live["regime"]; call = uw_live["call"]; note = uw_live["note"]
        eff_range = uw_live["exp_range"] if uw_live["exp_range"] is not None else bk["range"]
        eff_oc = uw_live["exp_oc"] if uw_live["exp_oc"] is not None else bk["oc"]
        regime_source = "Unusual Whales — SAME-DAY (real-time)"
    else:
        eff_range = bk["range"]; eff_oc = bk["oc"]
        regime_source = "SqueezeMetrics — prior close (15-yr backtested)"

    # ===== RECONCILE every direction input into ONE decision (nothing isolated / contradictory) =====
    # Inputs: DIX night-before (backtested 55-60% bullish edge) + LIVE UW flow (sweep + intraday tape).
    # LIVE flow is weighted higher (it's current). If they conflict, conviction collapses and we stand down.
    live_score = (uw_live or {}).get("dir_score")            # -100..100, or None if no UW key
    live_bias = (uw_live or {}).get("overall_bias")
    inputs = []
    if fired:
        inputs.append({"src": "DIX (night-before, 15-yr)", "bias": "bullish", "val": +0.6, "w": 0.4})
    if live_score is not None:
        inputs.append({"src": "UW live flow (real-time)", "bias": live_bias, "val": live_score / 100.0, "w": 0.6})
    # THE WIDER UW SURFACE. The 0DTE read was using one endpoint out of 83.
    # These add information that is orthogonal to price and gamma, each weighted
    # by what it MEASURED rather than by how interesting it sounds.
    # SPX/NDX are indices with no dark pool prints and no short interest, so
    # both are read through the tracking ETF where the shares actually trade.
    try:
        import uw_endpoints as _ue
        import signal_weights as _sw
        _p = _ue.profile("SPY")
        if _p.get("dp_buy_share") is not None:
            _v = (float(_p["dp_buy_share"]) - 0.5) * 2
            _w = _sw.weight("dp_buy_share")[0]
            if _w > 0:
                inputs.append({"src": "dark pool buy-share", "val": _v, "w": _w,
                               "bias": "bullish" if _v > 0 else "bearish"})
        # NEGATIVE by measurement: IC -0.068 at 21d over 13,219 observations,
        # monotone in horizon. Heavily shorted underperforms -- the opposite of
        # the squeeze-fuel intuition my earlier prior encoded.
        if _p.get("short_float_pct") is not None:
            _v = -min(float(_p["short_float_pct"]) / 20.0, 1.0)
            _w = _sw.weight("short_float_pct")[0]
            if _w > 0:
                inputs.append({"src": "short interest (neg by measurement)",
                               "val": _v, "w": _w,
                               "bias": "bearish" if _v < 0 else "bullish"})
    except Exception as _e:
        print(f"  uw surface unavailable: {_e}")

    wsum = sum(i["w"] for i in inputs) or 1.0
    net = sum(i["val"] * i["w"] for i in inputs) / wsum       # -1..+1 reconciled direction
    conflict = bool(fired and live_score is not None and live_score < -12)  # DIX bullish vs UW bearish

    if conflict:
        # These labels are LEANS, not orders. "favor CALLS" / "favor PUTS" were the old wording
        # and they read as instructions on the page; the underlying directional read measured
        # -10% to -11% per trade out of sample (docs/VERDICT_LOG.md).
        bias = "CONFLICT — inputs disagree"; conv = 22
        dhint = ("The night-before DIX read leaned bullish and live flow leaned bearish. When the two inputs "
                 "disagree the reconciled lean carries no information.")
    elif net > 0.15:
        bias = "BULLISH LEAN"; conv = min(78, 48 + int(net * 40))
        dhint = None
    elif net < -0.15:
        bias = "BEARISH LEAN"; conv = min(72, 42 + int(-net * 40))
        dhint = ("Bearish lean. No reliable night-before directional edge was found in this data, so this is "
                 "context only.")
    else:
        bias = "NEUTRAL — no clean edge"; conv = 30
        dhint = None

    # THESIS: the range forecast, plus the reconciled lean reported as context.
    #
    # This block used to choose a VEHICLE and write an order: "IDEAL naked-CALL day. Buy a naked
    # CALL (ATM/1-ITM, nearest 0DTE)", "buy puts on a decisive break BELOW the gamma flip", "SELL
    # an iron condor around the pin". Every one of those is refuted or unproven at real prices
    # (docs/VERDICT_LOG.md), and the thesis string is printed straight onto the dashboard. So the
    # thesis now states the range expectation and names the lean as a lean. What to do about it is
    # decided in one place, by master_call and the deterministic gates, and it is not decided here.
    range_word = ("wide range likely" if stance == "wide_range"
                  else "tight range / pin likely" if stance == "tight_range" else "average range")
    bull = "BULLISH" in bias
    bear = "BEARISH" in bias
    lean_note = ("Inputs disagree, so the lean carries no information today." if conflict
                 else f"Lean is {'bullish' if bull else 'bearish' if bear else 'neutral'} at {conv}/100, "
                      "which is context for a decision made elsewhere, not a trade. No directional edge in "
                      "this data survived out-of-sample testing.")
    if stance == "wide_range":
        action = (f"Dealer hedging runs with the move today, so expect a wider range than implied "
                  f"(~{eff_oc}% open to close). A wide range is not by itself profitable: a long option still has "
                  f"to beat its own cost, and in testing it did not. {lean_note}")
    elif stance == "tight_range":
        action = (f"Dealer hedging runs against the move today, so expect a tighter range than implied "
                  f"(~{eff_oc}% open to close; ~{bk['cond75']}% of 1.25-SD condors survived to the close in the "
                  f"backtest). Selling that range is approximately break-even at real quotes, so this is a "
                  f"regime read, not a setup. {lean_note}")
    else:
        action = (f"Average range regime (~{eff_oc}% open to close). This is the regime that tells you least. "
                  f"{lean_note}")
    thesis = f"SPX today: {range_word}, {bias}. {action}"
    master_dir = ("conflict" if conflict else "bullish" if net > 0.15 else "bearish" if net < -0.15 else "neutral")
    reconcile = {"net": round(net, 2), "conflict": conflict, "master_dir": master_dir,
                 "inputs": [{"src": i["src"], "bias": i["bias"], "score": round(i["val"] * 100)} for i in inputs]}

    exp_move = latest["price"] * bk["oc"] / 100
    snap = {
        "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),   # when THIS tool last refreshed
        "gex_date": str(latest["date"].date()),                    # the close the GEX was measured at
        "applies_to": "next session after " + str(latest["date"].date()),
        "gex_bn": round(gex_bn, 2), "gex_z": round(z, 2), "neg_gamma": bool(neg),
        "spx_proxy": round(float(latest["price"]), 2), "dix": round(dix, 3), "dix_z": round(dz, 2),
        "dix_tilt": dix_call,
        "quintile": int(q), "regime": regime, "call": call, "stance": stance, "note": note,
        "regime_source": regime_source, "uw_live": uw_live, "baseline": baseline,
        "exp_range_pct": eff_range, "exp_oc_pct": eff_oc, "exp_move_pts": round(exp_move, 1),
        "condor_survival": {"pm0_5": bk["cond50"], "pm0_75": bk["cond75"], "pm1_0": bk["cond100"]},
        "index": "SPX", "spx_level": (uw_live or {}).get("spot") or round(float(latest["price"]), 2),
        "bias": bias, "conviction": int(conv), "thesis": thesis, "reconcile": reconcile,
        "master_dir": master_dir,
        "signals_firing": [{"name": n, "win": w, "t": t} for n, w, t in fired],
        "trend_up": trend_up, "vix": round(vix_lvl, 1) if vix_lvl else None,
        "vix_ts": round(vix_ts, 3) if vix_ts else None,
        "macro_regime": macro_regime, "macro_note": macro_note,
        "backcheck": _backcheck(g, buckets, edges),
        "caveat": ("Regime sets the AVERAGE range and the ODDS — it does NOT cap the day. A strong "
                   "catalyst with institutions buying (high DIX) can trend even in positive gamma. "
                   "Probabilistic tilt, not a ceiling — size accordingly."),
        "buckets": buckets,
        # This list used to be a "direction_playbook" telling the reader how to pick a side and
        # then trade it. Every avenue in it was tested here and failed: 56 features and 220
        # conditions produced ZERO combinations clearing 55% on both train and validate, real
        # 0DTE order flow over 16,152 observations was null with a sign that flips between
        # splits, and the opening-drive continuation did not replicate across SPY/QQQ/IWM. See
        # 02_findings/FINDINGS.md. What replaces it is the honest version: what was looked for,
        # and what was found.
        "direction_findings": [
            "Dealer gamma gives the RANGE (how big), never the SIDE. Nothing here gives the side.",
            "Technical indicators: 56 features, 220 conditions, thousands of combinations, three-way split -> ZERO cleared 55% on train AND validate.",
            "Real 0DTE order flow: 16,152 observations over 1,919 sessions -> null, and the sign flips between splits.",
            "Candlestick and price-action patterns: ~30 patterns measured against the base rate -> none held +4pp on all three splits.",
            "Opening-drive continuation: replicated on QQQ only, 1 of 3 symbols, which is what a fitted result looks like.",
            "The practical consequence: there is no validated intraday directional trade here, and the flip-break version of one measured -7.2% to -19.1% per trade.",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(snap, open(OUT, "w"), indent=2, default=str)
    try:
        import signal_tracker
        signal_tracker.log(snap)      # accountability: record today's call for the running win-rate
    except Exception:
        pass
    print(f"GEX {snap['gex_date']}: {gex_bn:+.1f}bn  z {z:+.2f}  -> {regime}")
    print(f"  {call}")
    print(f"  expected intraday range ~{bk['range']}%  (~{exp_move:.0f} SPX pts open->close)")
    print(f"  condor survival @±0.75%: {bk['cond75']}%")
    return snap


if __name__ == "__main__":
    run()
