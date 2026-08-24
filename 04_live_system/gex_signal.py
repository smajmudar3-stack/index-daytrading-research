"""gex_signal.py — LIVE 0DTE dealer-gamma REGIME signal (the real, 15-year-robust edge).

What it is: dealer Gamma Exposure (GEX) from the prior close is known before today's open and
predicts the day's INTRADAY RANGE with a huge, monotone, every-year-stable effect (2011-2026,
t=-16). It does NOT predict direction. So it answers the one question that most improves naked
0DTE call/put trading: SHOULD I BE BUYING PREMIUM TODAY AT ALL, and how much fuel is in the tank?

  low / negative gamma  -> big range (dealers amplify)  -> GO: naked directional has fuel, press size
  high / positive gamma -> pin / chop (dealers dampen)  -> NO-GO: theta death, sit out or sell premium

Direction (call vs put) is NOT in GEX — get it from your opening drive + flow (Unusual Whales /
Market Chameleon / Barchart). This tool sizes the OPPORTUNITY; the trigger picks the side.

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
        if dist < -0.001:                               # below the flip → short gamma → trend/big range
            regime = "SHORT GAMMA (live)"; stance = "buy_premium"; call = "GO — trend regime (dealers amplify)"
            note = ("UW same-day: price is BELOW the zero-gamma flip → dealers short gamma → they push moves "
                    "further → big-range/trend day. Naked longs have fuel; ride the direction, bail on a reclaim above flip.")
        elif dist < 0.003:                              # right around the flip → transitional
            regime = "AT/NEAR FLIP (live)"; stance = "selective"; call = "TRANSITIONAL — watch the flip"
            note = ("UW same-day: price is sitting near the zero-gamma flip — the coiled line. Regime can tip either "
                    "way. Trade only on a decisive break (below = puts/trend, hold above = calls/pin-grind).")
        else:                                           # comfortably above flip → long gamma → pin
            regime = "LONG GAMMA / PIN (live)"; stance = "sell_premium"; call = "PIN — naked premium bleeds"
            note = ("UW same-day: price is above the zero-gamma flip with net long dealer gamma → they fade moves → "
                    "pin/chop. Naked longs bleed theta; use spreads, or sell premium (condor) around the pin.")
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
        dix_call = "BULLISH tilt — high dark-pool buying on a low-gamma day (→ favor CALLS; 60% green, t=+3.0)"
    elif dz > 0.5:
        dix_call = "mild bullish — DIX high but gamma not low (weaker signal)"
    elif dz < -0.5:
        dix_call = "DIX low — no long edge; don't force a call, wait for the drive/flow"
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

    # regime label + naked-premium call
    if neg:
        regime = "NEGATIVE GAMMA"; call = "GO — big-range regime"
        note = ("Dealers are SHORT gamma: they buy rallies / sell dips, AMPLIFYING moves. This is the "
                "top ~9% of days for intraday range (avg ~2.4% vs ~1.0% normal). Naked long calls/puts "
                "have the most fuel here — theta gets paid off by the move. Press size when a direction sets up.")
        stance = "buy_premium"
    elif q <= 2:
        regime = f"LOW GAMMA (Q{q}/5)"; call = "GO — above-average range"
        note = ("Gamma is low: dealers dampen less, so moves extend. Good conditions for naked directional "
                "0DTE — wait for the opening drive/flow to pick the side, then ride it.")
        stance = "buy_premium"
    elif q == 3:
        regime = "MID GAMMA (Q3/5)"; call = "NEUTRAL — average day"
        note = ("Middle regime — no range edge either way. Only buy naked premium with a strong directional "
                "trigger; otherwise the day likely chops enough to bleed theta.")
        stance = "selective"
    else:
        regime = f"HIGH GAMMA (Q{q}/5)"; call = "NO-GO for naked premium — PIN/CHOP"
        note = ("Dealers are LONG gamma: they sell rallies / buy dips, PINNING the index. Smallest-range "
                "regime (avg ~0.7%). Naked long 0DTE bleeds theta here — this is the leak. Either sit out, "
                "or FLIP to being the seller (iron condor / credit spread) — condor survival is highest now.")
        stance = "sell_premium"

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
        bias = "⚔️ CONFLICT — stand down"; conv = 22
        dhint = ("Night-before DIX leaned BULLISH but LIVE UW flow flipped BEARISH — the signals disagree. "
                 "Don't force a side. Wait for them to align, or trade only the periscope flip break (below flip = "
                 "puts, reclaim + hold = calls).")
    elif net > 0.15:
        bias = "BULLISH — favor CALLS"; conv = min(78, 48 + int(net * 40))
        dhint = None
    elif net < -0.15:
        bias = "BEARISH — favor PUTS"; conv = min(72, 42 + int(-net * 40))
        dhint = ("Lean is bearish. There's no reliable night-before PUT edge, so treat this as a REACTIVE play: "
                 "buy puts on a decisive break BELOW the gamma flip (short gamma amplifies the drop).")
    else:
        bias = "NEUTRAL — no clean edge"; conv = 30
        dhint = None

    # THESIS: vehicle depends on the RECONCILED direction AND the range regime.
    # A naked long only pays when RANGE is there; bullish into a PIN = slow grind = use a SPREAD not naked.
    range_word = ("BIG range likely (trend)" if stance == "buy_premium"
                  else "small range / pin likely" if stance == "sell_premium" else "average range")
    bull = "BULLISH" in bias
    bear = "BEARISH" in bias
    if conflict:
        action = dhint
    elif bull and stance == "buy_premium":
        action = (f"Clean bullish + big-range/short-gamma = IDEAL naked-CALL day. Buy a naked CALL (ATM/1-ITM, "
                  f"nearest 0DTE) once price holds above the gamma flip. {conv}/100. Target ~{eff_oc}%; bail on a flip loss.")
    elif bull and stance in ("selective", "sell_premium"):
        action = (f"Bullish, but it's a PIN day — a NAKED call bleeds theta on a slow grind. Use a CALL DEBIT SPREAD "
                  f"(buy ATM / sell ~+{max(0.5,eff_oc or 0.5):.1f}%) or shares; go naked only on a break above the call wall.")
    elif bear:
        action = dhint
    elif stance == "sell_premium":
        action = ("No directional edge and gamma pins the tape — don't buy premium. Sit out, or SELL an iron condor "
                  f"around the pin (~±{(eff_oc or 0.5)*1.3:.1f}%; ~{bk['cond75']}% survive to close).")
    elif stance == "buy_premium":
        action = ("Big-range regime but no clear side. Wait for the open: take the side of the opening drive + flow; "
                  "naked is fine here because the range supports it. Bail on a flip break against you.")
    else:
        action = ("No clean edge and average range. Wait for the open: CALL on a hold above the flip with a clean drive "
                  "(prefer a spread); PUT on a decisive break below the flip. Else sit out.")
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
        "direction_playbook": [
            "GEX gives you the REGIME (how big), never the SIDE. Pick the side from a trigger:",
            "1) Opening drive: at ~10:00 ET, trade the side of 09:30->10:00 move (on low-gamma days it tends to continue).",
            "2) Flow confirmation: Unusual Whales (sweeps/large 0DTE prints), Market Chameleon (options volume/PCR), Barchart (unusual options) — take the side the size is leaning.",
            "3) Level: above prior-day VWAP/high = call bias; below = put bias.",
            "On NO-GO (high-gamma) days: skip naked premium OR sell an iron condor around the pin instead.",
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
