"""hunt_indicators.py — the full technical-indicator battery, then every combination against it.

Adds the standard TradingView-style indicator set to the intraday feature matrix so that the
combination search covers them alongside GEX / DIX / VWAP rather than only the bespoke features:

  Bollinger Bands (%B, bandwidth, squeeze)      Keltner Channels (position, squeeze vs BB)
  MACD (line, signal, histogram, cross)         Donchian channel position
  Stochastic (%K, %D)                           Williams %R
  CCI                                           MFI (volume-weighted RSI)
  ADX / DI+ / DI- (trend strength)              OBV slope
  Parabolic-SAR distance                        Pivot points (S1/R1 distance)
  ATR bands                                     Rate of change, TRIX
  Volume-profile POC distance                   Cumulative delta proxy

All are computed strictly per-session from current-and-past bars only.
"""
import numpy as np
import pandas as pd

import hunt_features as HF


def _g(df):
    return df.groupby("date", group_keys=False)


def add_indicators(out):
    g = _g(out)
    c, h, l, v = out.close, out.high, out.low, out.volume

    # ---- Bollinger -------------------------------------------------------------------
    ma20 = g.close.apply(lambda s: s.rolling(20, min_periods=5).mean())
    sd20 = g.close.apply(lambda s: s.rolling(20, min_periods=5).std())
    out["bb_pctb"] = (c - (ma20 - 2 * sd20)) / (4 * sd20).replace(0, np.nan)
    out["bb_width"] = (4 * sd20) / ma20
    out["bb_squeeze"] = out.bb_width / _g(out).bb_width.apply(
        lambda s: s.rolling(60, min_periods=10).mean())

    # ---- Keltner + squeeze vs BB ------------------------------------------------------
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    out["_tr"] = tr
    atr20 = _g(out)._tr.apply(lambda s: s.rolling(20, min_periods=5).mean())
    out["kc_pos"] = (c - ma20) / (2 * atr20).replace(0, np.nan)
    out["ttm_squeeze"] = ((2 * sd20) < (1.5 * atr20)).astype(float)

    # ---- MACD -------------------------------------------------------------------------
    e12 = g.close.apply(lambda s: s.ewm(span=12, adjust=False).mean())
    e26 = g.close.apply(lambda s: s.ewm(span=26, adjust=False).mean())
    out["macd"] = (e12 - e26) / c
    out["macd_sig"] = _g(out).macd.apply(lambda s: s.ewm(span=9, adjust=False).mean())
    out["macd_hist"] = out.macd - out.macd_sig

    # ---- Stochastic / Williams --------------------------------------------------------
    hh = g.high.apply(lambda s: s.rolling(14, min_periods=5).max())
    ll = g.low.apply(lambda s: s.rolling(14, min_periods=5).min())
    rng = (hh - ll).replace(0, np.nan)
    out["stoch_k"] = (c - ll) / rng * 100
    out["stoch_d"] = _g(out).stoch_k.apply(lambda s: s.rolling(3, min_periods=1).mean())
    out["willr"] = (hh - c) / rng * -100

    # ---- CCI ---------------------------------------------------------------------------
    tp = (h + l + c) / 3
    out["_tp"] = tp
    tpma = _g(out)._tp.apply(lambda s: s.rolling(20, min_periods=5).mean())
    tpmd = _g(out)._tp.apply(lambda s: s.rolling(20, min_periods=5).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True))
    out["cci"] = (tp - tpma) / (0.015 * tpmd.replace(0, np.nan))

    # ---- MFI ----------------------------------------------------------------------------
    mf = tp * v
    out["_pmf"] = np.where(tp > tp.shift(), mf, 0.0)
    out["_nmf"] = np.where(tp < tp.shift(), mf, 0.0)
    pmf = _g(out)._pmf.apply(lambda s: s.rolling(14, min_periods=5).sum())
    nmf = _g(out)._nmf.apply(lambda s: s.rolling(14, min_periods=5).sum())
    out["mfi"] = 100 - 100 / (1 + pmf / nmf.replace(0, np.nan))

    # ---- ADX / DI -------------------------------------------------------------------------
    up_m = h.diff()
    dn_m = -l.diff()
    out["_pdm"] = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    out["_ndm"] = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    atr14 = _g(out)._tr.apply(lambda s: s.rolling(14, min_periods=5).mean())
    pdi = 100 * _g(out)._pdm.apply(lambda s: s.rolling(14, min_periods=5).mean()) / atr14.replace(0, np.nan)
    ndi = 100 * _g(out)._ndm.apply(lambda s: s.rolling(14, min_periods=5).mean()) / atr14.replace(0, np.nan)
    out["di_diff"] = pdi - ndi
    dx = ((pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)) * 100
    out["_dx"] = dx
    out["adx"] = _g(out)._dx.apply(lambda s: s.rolling(14, min_periods=5).mean())

    # ---- Donchian -----------------------------------------------------------------------
    dh = g.high.apply(lambda s: s.rolling(20, min_periods=5).max())
    dl = g.low.apply(lambda s: s.rolling(20, min_periods=5).min())
    out["donch_pos"] = (c - dl) / (dh - dl).replace(0, np.nan)

    # ---- OBV slope, cumulative delta proxy ------------------------------------------------
    sgn = np.sign(c.diff()).fillna(0)
    out["_obv"] = (sgn * v)
    obv = _g(out)._obv.apply(lambda s: s.cumsum())
    out["obv_slope"] = _g(out.assign(_o=obv))._o.apply(lambda s: s.diff(10)) / v.rolling(10).mean().replace(0, np.nan)
    body_frac = ((c - out.open) / (h - l).replace(0, np.nan)).clip(-1, 1).fillna(0)
    out["_cd"] = body_frac * v
    cd = _g(out)._cd.apply(lambda s: s.cumsum())
    out["cum_delta"] = cd / _g(out).volume.apply(lambda s: s.cumsum()).replace(0, np.nan)

    # ---- rate of change / TRIX ---------------------------------------------------------------
    out["roc10"] = g.close.apply(lambda s: s.pct_change(10))
    tx = g.close.apply(lambda s: s.ewm(span=9, adjust=False).mean()
                       .ewm(span=9, adjust=False).mean().ewm(span=9, adjust=False).mean())
    out["trix"] = _g(out.assign(_t=tx))._t.apply(lambda s: s.pct_change())

    # ---- pivots (prior session) -----------------------------------------------------------
    daily = out.groupby("date").agg(hi=("high", "max"), lo=("low", "min"), cl=("close", "last"))
    piv = ((daily.hi + daily.lo + daily.cl) / 3).shift()
    r1 = (2 * piv - daily.lo.shift())
    s1 = (2 * piv - daily.hi.shift())
    out["piv_dist"] = (c - out.date.map(piv)) / c
    out["r1_dist"] = (c - out.date.map(r1)) / c
    out["s1_dist"] = (c - out.date.map(s1)) / c

    # ---- volume-profile POC proxy (modal price of the session so far) -----------------------
    out["poc_dist"] = (c - out.vwap) / out.vwap        # vwap is the practical POC proxy intraday

    return out.drop(columns=[x for x in out.columns if x.startswith("_")], errors="ignore")


IND = ["bb_pctb", "bb_width", "bb_squeeze", "kc_pos", "ttm_squeeze", "macd", "macd_hist",
       "stoch_k", "stoch_d", "willr", "cci", "mfi", "adx", "di_diff", "donch_pos",
       "obv_slope", "cum_delta", "roc10", "trix", "piv_dist", "r1_dist", "s1_dist", "poc_dist"]

ALL_FEATS = HF.FEATURES + IND


def build(sym="QQQ"):
    df = HF.load(sym)
    df = HF.add_features(df)
    df = add_indicators(df)
    df = HF.add_daily(df)
    return df


if __name__ == "__main__":
    import sys
    d = build(sys.argv[1] if len(sys.argv) > 1 else "QQQ")
    have = [f for f in ALL_FEATS if f in d.columns]
    print(f"features built: {len(have)} / {len(ALL_FEATS)}")
    miss = [f for f in ALL_FEATS if f not in d.columns]
    if miss:
        print("missing:", miss)
    print(d[have].notna().mean().sort_values().head(8))
