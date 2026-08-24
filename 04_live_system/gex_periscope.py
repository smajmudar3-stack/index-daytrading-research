"""gex_periscope.py — LIVE per-strike dealer-gamma PERISCOPE (magnet/reversal levels).

Where the SqueezeMetrics series gives ONE market-wide gamma number (lagged a day), this reads the
actual option chain NOW and maps dealer gamma by strike -> the levels that matter intraday:

  GAMMA FLIP : the price where net dealer gamma crosses zero. Above it dealers are long gamma
               (pin/mean-revert); below it short gamma (amplify/trend). THE regime line, live.
  CALL WALL  : strike with the most positive dealer gamma = magnet / resistance (price gets pinned under it).
  PUT WALL   : strike with the most negative dealer gamma = support (price gets defended above it).
  NET GEX    : total $-gamma per 1% move. Big + = pinned tape; near 0 / negative = unstable/trending.

Convention (standard SpotGamma-style): dealers are long customer calls, short customer puts ->
call gamma adds dealer gamma (+), put gamma subtracts (-). Gamma from Black-Scholes at each candidate
price. Source: yfinance chains (auto, for the dashboard). Robinhood live greeks/OI can spot-validate.

For 0DTE the near-expiry chain dominates gamma; we profile the nearest 1-2 expirations.
"""
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))


def _outpath(sym):
    return os.path.join(HERE, "data", f"periscope_{sym.replace('^', '')}.json")


def bs_gamma(S, K, T, iv, r=0.04):
    T = np.maximum(T, 1e-6); iv = np.maximum(iv, 1e-4)
    d1 = (np.log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * np.sqrt(T))
    return norm.pdf(d1) / (S * iv * np.sqrt(T))


_DAY = [None]        # scratch: (day_high, day_low, open) from the last chain() call


def _signal_quality(sig, spot, flip, cw, pw, dir_score):
    """Conviction 0-100 for the directional signal + an EXTENSION read (don't chase too late)."""
    bull = sig == "BUY CALLS"; bear = sig == "BUY PUTS"
    if not (bull or bear):
        return {"conviction": 0, "entry": "", "entry_col": "mut"}
    conv = 42 + min(33, abs(dir_score or 0) * 0.7)        # flow strength → base conviction
    day = _DAY[0]; rng_pos = None
    if day and day[0] > day[1]:
        rng_pos = (spot - day[1]) / (day[0] - day[1])     # 0=day low, 1=day high
    entry = "ok entry — room to run"; ecol = "go"
    if bull and cw:
        room = (cw - spot) / spot * 100                   # % up to the call wall (resistance)
        if room < 0.05:
            entry = f"⚠️ EXTENDED — at/above the call wall {cw:.0f}. Chasing risk; wait for a pullback to buy."; ecol = "red"; conv -= 28
        elif room < 0.2:
            entry = f"late-ish — only {room:.2f}% to the {cw:.0f} wall. Small size or wait for a dip."; ecol = "warn"; conv -= 12
        else:
            entry = f"ok entry — ~{room:.2f}% room to the {cw:.0f} wall"
        if rng_pos is not None and rng_pos > 0.9:
            entry += " · at day highs (extended)"; conv -= 10
    elif bear and pw:
        room = (spot - pw) / spot * 100
        if room < 0.05:
            entry = f"⚠️ EXTENDED — at/below the put wall {pw:.0f}. Chasing; wait for a bounce to buy."; ecol = "red"; conv -= 28
        elif room < 0.2:
            entry = f"late-ish — only {room:.2f}% to the {pw:.0f} wall. Small size or wait."; ecol = "warn"; conv -= 12
        else:
            entry = f"ok entry — ~{room:.2f}% room to the {pw:.0f} wall"
        if rng_pos is not None and rng_pos < 0.1:
            entry += " · at day lows (extended)"; conv -= 10
    return {"conviction": max(10, min(85, round(conv))), "entry": entry, "entry_col": ecol}


# yfinance carries TWO tickers for the S&P 500 and they do not agree intraday:
# `^SPX` is a sparse, delayed feed (observed 15 min behind, ~22 bars by 10:00)
# while `^GSPC` updates continuously (~37 bars). The option chain only exists
# under ^SPX, so we must keep pulling the chain from there — but taking SPOT
# from the same handle is what made every SPX level read ~12 points high.
#
# So: chain from ^SPX, spot from ^GSPC, and cross-check against the ETF, which
# is the most liquid and freshest feed of the three. If the index feed drifts
# from ETF x ratio by more than the tolerance, trust the ETF.
SPOT_SRC = {
    "^SPX": ("^GSPC", "SPY"),
    "SPX":  ("^GSPC", "SPY"),
    "^NDX": ("^NDX", "QQQ"),
    "NDX":  ("^NDX", "QQQ"),
}
_SPOT_SRC_USED = [None]      # which feed the last chain() call trusted
SPOT_TOL = 0.0015          # 15 bps; beyond this the index feed is considered stale


# The index/ETF ratio drifts only with dividends, so refetching it on every
# call was pointless -- and it hammered yfinance hard enough to get the whole
# process rate-limited ("possibly delisted; no price data found"), which is
# what stalled the dashboard. Cache it for the session.
_RATIO_CACHE = {}


def _uw_spot(sym):
    """Real-time spot from Unusual Whales, which is not delayed.

    yfinance index quotes run 15+ minutes behind, which is why levels and
    strikes kept reading wrong intraday. UW's 1-minute bar is the freshest
    source available here. Index tickers 422 on the ohlc endpoint, so SPX/NDX
    are derived from their ETF and the live ratio.
    """
    try:
        import uw_client as uw
        if not uw.available():
            return None, None
        etf = {"^SPX": "SPY", "SPX": "SPY", "SPY": "SPY",
               "^NDX": "QQQ", "NDX": "QQQ", "QQQ": "QQQ"}.get(sym)
        if not etf:
            return None, None
        rows = uw._rows(uw._get(f"/api/stock/{etf}/ohlc/1m", {"limit": 1}))
        if not rows:
            return None, None
        px = float(rows[0].get("close") or 0)
        if px <= 0:
            return None, None

        # AGE-CHECK THE BAR. Before the open (or during any UW gap) the "latest"
        # 1-minute bar is the PREVIOUS session's close, and using it writes a
        # stale price into a field the board presents as live. That is what made
        # SPX read ~37 points and NDX ~269 points too high: the periscope ran at
        # 09:29, one minute before the open, and stored yesterday's last bar.
        end = rows[0].get("end_time") or rows[0].get("start_time")
        if end:
            try:
                import pandas as _pd
                age_min = (_pd.Timestamp.utcnow().tz_localize(None)
                           - _pd.Timestamp(end).tz_localize(None)).total_seconds() / 60
                if age_min > 15:
                    return None, None      # too old to be "live" — fall through
            except Exception:
                pass
        if sym in ("SPY", "QQQ"):
            return px, f"UW {etf} 1m"
        ratio = _RATIO_CACHE.get(sym)
        if ratio is None:
            src = SPOT_SRC.get(sym, (None, None))[0]
            h = yf.download([src, etf], period="5d", interval="1d",
                            progress=False, auto_adjust=False)["Close"].dropna()
            ratio = float((h[src] / h[etf]).iloc[-1])
            _RATIO_CACHE[sym] = ratio
        return px * ratio, f"UW {etf}x{ratio:.2f} 1m"
    except Exception:
        return None, None


def _live_spot(sym, fallback):
    """Freshest trustworthy spot for `sym`, cross-checked against its ETF.

    Order of preference: UW real-time -> index feed -> ETF-implied -> whatever
    the chain ticker reported. yfinance is only reached when UW is unavailable.
    """
    px, src = _uw_spot(sym)
    if px:
        return px, src
    src, etf = SPOT_SRC.get(sym, (None, None))
    if not src:
        return fallback, "chain-ticker"
    try:
        idx = float(yf.Ticker(src).fast_info["lastPrice"])
    except Exception:
        return fallback, "chain-ticker (index feed unavailable)"
    try:
        e = float(yf.Ticker(etf).fast_info["lastPrice"])
        # The ratio MUST come from a different instant than the comparison,
        # otherwise implied == idx by construction and the check can never
        # fire. Derive it from the last few daily closes, which is stable
        # (it drifts only with dividends) and independent of the live prints.
        ratio = _RATIO_CACHE.get(sym)
        if ratio is None:
            h = yf.download([src, etf], period="5d", interval="1d",
                            progress=False, auto_adjust=False)["Close"].dropna()
            ratio = float((h[src] / h[etf]).iloc[-1])
            _RATIO_CACHE[sym] = ratio
        implied = e * ratio
        if abs(implied - idx) / idx > SPOT_TOL:
            return implied, f"{etf}x{ratio:.2f} (index feed stale)"
    except Exception:
        pass
    return idx, src


def chain(sym="SPY", n_exp=2):
    t = yf.Ticker(sym)
    fi = t.fast_info
    spot = float(fi["lastPrice"])
    # Replace a stale index print with the live cross-checked level. The chain
    # itself still comes from `t` (only ^SPX lists SPX options).
    spot, _src = _live_spot(sym, spot)
    _SPOT_SRC_USED[0] = _src
    try:
        _DAY[0] = (float(fi["dayHigh"]), float(fi["dayLow"]), float(fi["open"]))
    except Exception:
        _DAY[0] = None
    exps = list(t.options)[:n_exp]
    rows = []
    now = datetime.now(timezone.utc)
    for e in exps:
        exp_dt = datetime.strptime(e, "%Y-%m-%d").replace(hour=20, tzinfo=timezone.utc)  # ~16:00 ET expiry
        T = max((exp_dt - now).total_seconds() / (365 * 24 * 3600), 1e-6)
        oc = t.option_chain(e)
        for df, typ in ((oc.calls, "C"), (oc.puts, "P")):
            cols = ["strike", "openInterest", "impliedVolatility", "volume"]
            d = df[[c for c in cols if c in df.columns]].copy()
            d = d[(d["strike"] > spot * 0.9) & (d["strike"] < spot * 1.1)]   # focus near spot
            d["type"] = typ; d["exp"] = e; d["T"] = T
            rows.append(d)
    ch = pd.concat(rows, ignore_index=True).fillna({"openInterest": 0, "impliedVolatility": 0.15, "volume": 0})
    ch["openInterest"] = ch["openInterest"].replace(0, np.nan)
    ch["impliedVolatility"] = ch["impliedVolatility"].clip(0.03, 3.0)
    if "volume" not in ch.columns:
        ch["volume"] = 0
    return spot, ch.dropna(subset=["openInterest"])


def flow(ch, spot):
    """Direction/conviction from today's option VOLUME (a free flow proxy).
    call/put volume imbalance = directional pressure; volume>OI = FRESH positioning (unusual)."""
    near = ch[(ch["strike"] > spot * 0.97) & (ch["strike"] < spot * 1.03)]   # tight ATM band
    cvol = float(near.loc[near["type"] == "C", "volume"].sum())
    pvol = float(near.loc[near["type"] == "P", "volume"].sum())
    cp = cvol / pvol if pvol > 0 else (2.0 if cvol > 0 else 1.0)
    pcr = pvol / cvol if cvol > 0 else 1.0
    # unusual = strikes where today's volume exceeds resting OI (new bets, not closing)
    ch = ch.assign(vox=ch["volume"] / ch["openInterest"].replace(0, np.nan))
    unusual = ch[(ch["vox"] > 1.0) & (ch["volume"] > 500)]
    ucall = int((unusual["type"] == "C").sum()); uput = int((unusual["type"] == "P").sum())
    cpd = ">10" if cp > 10 else f"{cp:.1f}"                 # cap display (thin-vol can spike the raw ratio)
    thin = " (thin volume — read lightly)" if (cvol + pvol) < 2000 else ""
    if cp >= 1.35 and ucall >= uput:
        bias = "bullish"; note = f"calls {cpd}× puts near ATM, {ucall} fresh call strikes{thin}"
    elif cp <= 0.7 and uput >= ucall:
        # cp can be exactly 0 when there is no ATM call volume at all (routine
        # after hours). Dividing by it crashed the whole periscope run and left
        # the snapshot frozen -- a stale board that still looked live.
        pc = (1 / cp) if cp > 0 else float("inf")
        pcd = ">10" if pc > 10 else f"{pc:.1f}"
        bias = "bearish"; note = f"puts {pcd}× calls near ATM, {uput} fresh put strikes{thin}"
    else:
        bias = "neutral"; note = f"balanced (calls {cpd}× puts){thin}"
    return {"bias": bias, "cp_ratio": round(cp, 2), "pcr": round(pcr, 2),
            "unusual_calls": ucall, "unusual_puts": uput, "note": note,
            "call_vol": int(cvol), "put_vol": int(pvol)}


def dealer_gamma_at(price, ch):
    """Net dealer $-gamma per 1% move, evaluated with each option's BS gamma at `price`."""
    g = bs_gamma(price, ch["strike"].values, ch["T"].values, ch["impliedVolatility"].values)
    sign = np.where(ch["type"].values == "C", 1.0, -1.0)      # long calls, short puts
    dollar = g * ch["openInterest"].values * 100 * price * price * 0.01 * sign
    return dollar.sum()


def per_strike(ch, spot):
    """Dealer gamma by strike (at current spot) -> walls."""
    g = bs_gamma(spot, ch["strike"].values, ch["T"].values, ch["impliedVolatility"].values)
    sign = np.where(ch["type"].values == "C", 1.0, -1.0)
    ch = ch.assign(dgex=g * ch["openInterest"].values * 100 * spot * spot * 0.01 * sign)
    by = ch.groupby("strike")["dgex"].sum().sort_index()
    return by


def recommend(spot, flip, net_pos, flow_bias, master=None):
    """Clear intraday signal. `master` = the reconciled SPX decision ('bullish'/'bearish'/'neutral'/
    'conflict') from gex_signal, when available — the periscope ALIGNS with it so panels never contradict.
    EXCEPTION: a live flip break overrides the master (real-time price action wins). Returns (sig, why, col)."""
    # 1) REACTIVE OVERRIDE — a flip break is a live regime change; it trumps the night-before master.
    if flip is not None:
        dist = (spot / flip - 1) * 100
        if dist < -0.05:                       # BELOW the flip = short gamma = downside amplifies
            ovr = " — this OVERRIDES the bullish read (live price action wins)" if master == "bullish" else ""
            return ("BUY PUTS", f"Price BROKE below the gamma flip ({flip:.0f}) → dealers short gamma → they SELL into "
                    f"weakness → downside accelerates. Buy puts / put debit spread; trail to the put wall{ovr}.", "red")
        if dist < 0.15:                        # sitting on the flip — coiled
            return ("AT FLIP — WAIT", f"Price is on the gamma flip ({flip:.0f}) — the coiled line. Break BELOW = puts; "
                    "reclaim + hold ABOVE = calls. Don't pre-position.", "info")
    # 2) ABOVE the flip — ALIGN with the master reconciled decision so nothing contradicts.
    if master == "conflict":
        return ("WAIT — signals conflict", "Master decision is CONFLICT (night-before DIX vs live UW flow disagree). "
                "No directional 0DTE — wait for them to align, or trade only a decisive flip break.", "info")
    if master == "bearish":
        return ("CAUTION — bearish, wait for a flip break", "Master lean is bearish but price is holding above the flip "
                "(pin). No long here. Buy puts only on a decisive break BELOW the flip.", "info")
    if master == "bullish":
        return ("BUY CALLS", "Master is bullish AND price holds above the flip → upside. Pin damps range, so prefer a "
                "CALL DEBIT SPREAD; go naked only on a break above the call wall with a strong drive.", "go")
    # 3) no master (e.g. NDX/QQQ, standalone) — fall back to this ticker's own live flow
    if flow_bias == "bullish":
        return ("BUY CALLS", "Above the flip with bullish flow → upside bias. Prefer a CALL DEBIT SPREAD; naked only on "
                "a break above the call wall.", "go")
    if flow_bias == "bearish":
        return ("CAUTION — bearish flow into a pin", "Above the flip (pin) but flow leans puts. No clean trade — wait "
                "for a flip break to confirm downside, or sit out.", "info")
    return ("WAIT / SELL PREMIUM", "Above the flip, no directional edge → pin regime. Sit out, or SELL an iron condor "
            "around the pin (defined risk).", "mut")


def run(sym="SPY"):
    OUT = _outpath(sym)
    prior = None
    try:
        prior = json.load(open(OUT))          # for flip-break detection across runs
    except Exception:
        pass
    try:
        spot, ch = chain(sym)
    except Exception as e:
        snap = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False, "error": str(e)[:120]}
        json.dump(snap, open(OUT, "w"), indent=2)
        print("periscope failed:", e); return snap

    by = per_strike(ch, spot)
    net = float(by.sum())
    # walls by gamma CONCENTRATION (robust for index chains that are long-gamma everywhere):
    # call wall = biggest gamma magnet AT/ABOVE spot (resistance); put wall = biggest AT/BELOW (support)
    above = by[by.index >= spot]; below = by[by.index <= spot]
    call_wall = float(above.abs().idxmax()) if len(above) else None
    put_wall = float(below.abs().idxmax()) if len(below) else None

    # gamma flip: scan a wide price grid, find where net dealer gamma crosses zero (nearest to spot)
    grid = np.linspace(spot * 0.90, spot * 1.10, 401)
    vals = np.array([dealer_gamma_at(p, ch) for p in grid])
    flip = None
    sign_change = np.where(np.diff(np.sign(vals)) != 0)[0]
    if len(sign_change):
        idx = sign_change[np.argmin(np.abs(grid[sign_change] - spot))]
        x0, x1, y0, y1 = grid[idx], grid[idx + 1], vals[idx], vals[idx + 1]
        flip = float(x0 - y0 * (x1 - x0) / (y1 - y0)) if y1 != y0 else float(x0)

    if flip and spot > flip:
        regime = "above gamma flip → dealers LONG gamma (pin/mean-revert; naked premium bleeds)"
    elif flip:
        regime = "below gamma flip → dealers SHORT gamma (amplify/trend; naked premium has fuel)"
    elif net > 0:
        regime = "deep LONG gamma — no flip within ±10% (strong pin; flip is far below spot)"
    else:
        regime = "deep SHORT gamma — no flip within ±10% (unstable; amplifies in either direction)"

    top = by.reindex(by.abs().sort_values(ascending=False).index).iloc[:8].sort_index()
    fl = flow(ch, spot)                              # free volume proxy (default)
    uw = None
    try:                                            # UW = the decision-maker layer when a key is set
        import uw_client
        if uw_client.available():
            uwsym = {"SPY": "SPY", "^SPX": "SPX", "^NDX": "QQQ", "QQQ": "QQQ"}.get(sym, sym.replace("^", ""))
            uw = uw_client.full_read(uwsym, spot)
            if uw and uw.get("flow"):
                # real UW flow (sweep + intraday) REPLACES the volume proxy for direction
                fa = uw["flow"]; inf = uw.get("intraday") or {}
                fl = {"bias": uw["overall_bias"], "cp_ratio": None, "pcr": None,
                      "note": fa["detail"] + " · " + inf.get("detail", ""), "source": "unusualwhales",
                      "dir_score": uw["dir_score"]}
    except Exception:
        uw = None
    dir_score = (uw or {}).get("dir_score", 0) if uw else 0
    dir_bias = (uw["overall_bias"] if uw else fl["bias"])
    # link to the MASTER reconciled SPX decision (only SPX has one) so panels never contradict
    master = None
    if sym in ("^SPX", "SPX", "SPY"):
        try:
            master = json.load(open(os.path.join(HERE, "data", "gex_snapshot.json"))).get("master_dir")
        except Exception:
            master = None
    sig, why, sigcol = recommend(spot, flip, net > 0, dir_bias, master)
    # PRICE-ACTION CONFIRMATION — flow must AGREE with price. Never say BUY CALLS while price is
    # falling on the day, or BUY PUTS while it's rising. Flow/price divergence → CAUTION, not a trade.
    day = _DAY[0]
    if day and day[2]:
        op = day[2]; dchg = (spot / op - 1) * 100
        if sig == "BUY CALLS" and dchg < -0.15:
            sig = "CAUTION — bullish flow, but price is FALLING"
            why = (f"UW flow leans bullish, but {sym.replace('^','')} is RED on the day ({dchg:+.1f}%) — flow/price "
                   "DIVERGENCE. Don't chase calls into a downtrend. Wait for price to turn up, or if it breaks the "
                   "flip, that's the put setup.")
            sigcol = "info"
        elif sig == "BUY PUTS" and dchg > 0.15:
            sig = "CAUTION — bearish flow, but price is RISING"
            why = (f"Flow leans bearish, but {sym.replace('^','')} is GREEN ({dchg:+.1f}%) — divergence. Don't short a "
                   "rising tape; wait for price to roll over.")
            sigcol = "info"

    # flip-break detection: compare current side-of-flip to the prior run's
    side = None if flip is None else ("above" if spot >= flip else "below")
    prior_side = (prior or {}).get("flip_side")
    flip_break = None
    if prior_side and side and prior_side != side:
        flip_break = "broke_down" if side == "below" else "reclaimed_up"

    snap = {
        "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": True, "symbol": sym,
        "spot": round(spot, 2), "net_gex_musd": round(net / 1e6, 1),
        "gamma_flip": round(flip, 2) if flip else None,
        "flip_dist_pct": round((spot / flip - 1) * 100, 2) if flip else None,
        "call_wall": call_wall, "put_wall": put_wall, "regime": regime, "flow": fl,
        "signal": sig, "signal_why": why, "signal_col": sigcol, "master_dir": master,
        "quality": _signal_quality(sig, spot, flip, call_wall, put_wall, dir_score),
        "flip_side": side, "flip_break": flip_break,
        "uw": ({"dir_score": uw.get("dir_score"), "overall": uw.get("overall_bias"),
                "flow": uw.get("flow"), "intraday": uw.get("intraday"),
                "max_pain": uw.get("max_pain"), "implied_move": uw.get("implied_move"),
                "uw_flip": (uw.get("gex") or {}).get("gamma_flip"),
                "uw_net_gex": (uw.get("gex") or {}).get("net_gex"),
                "proxy": ("QQQ" if sym == "^NDX" else None)} if uw else None),
        "profile": [{"strike": float(k), "dgex_musd": round(v / 1e6, 1)} for k, v in top.items()],
        "note": ("Live dealer-gamma map. Flip is the intraday regime line; call wall = magnet/resistance, "
                 "put wall = support. Pins strongest into the afternoon as 0DTE gamma peaks."),
    }
    json.dump(snap, open(OUT, "w"), indent=2, default=str)
    print(f"{sym} {spot:.2f} | net GEX {net/1e6:+.0f}M | flip {flip and round(flip,2)} "
          f"({snap.get('flip_dist_pct')}%) | call wall {call_wall} | put wall {put_wall}")
    print(f"  regime: {regime}")
    print(f"  flow: {fl['bias'].upper()} — {fl['note']} (PCR {fl['pcr']})")
    print(f"  SIGNAL: {sig}" + (f"   ⚠️ FLIP {flip_break.upper()}" if flip_break else ""))
    return snap


if __name__ == "__main__":
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else "SPY")
