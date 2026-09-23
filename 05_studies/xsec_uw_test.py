"""xsec_uw_test.py — the Unusual Whales inputs, scored the way everything else was.

Inputs: DATA_ROOT/uw_hist/daily/<endpoint>__<ticker>.parquet from
05_studies/scripts/uw_history_pull.py (300 names by dollar volume, pulled 2026-09-22):

    options_volume   ~2 years daily: call/put volume, ask- and bid-side volume, net call and
                     put premium, 30-day average volumes   -> the FLOW family
    greek_exposure   ~1 year daily: dealer call/put gamma, delta, charm, vanna
    realized_vol     ~1 year daily: the vendor's own implied vs realised volatility
    insider          purchases / sells counts and notionals by filing date, 2003 ->
    (flow_alerts came back six weeks deep and darkpool one day deep; not testable yet)

Labels and universe: the Dolt panel (05_studies/xsec_predictors_test.py) -- split-adjusted
forward returns from the next open, close >= $10, dollar volume >= $10m -- which ends
2026-08-06, so the overlap is ~98 weeks for the flow family and ~45 for the greeks.
Method identical: one observation per name per week, Spearman IC per date, Fama-MacBeth t,
two halves instead of three splits (the history is short), and the noise bar stated.
Features signed as the literature would predict, so +IC = "as published".
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import universe, weekly  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
UW = os.path.join(paths.DATA_ROOT, "uw_hist", "daily")


def load(ep, datecol="date"):
    out = []
    for f in glob.glob(os.path.join(UW, f"{ep}__*.parquet")):
        d = pd.read_parquet(f)
        if "_empty" in d.columns or datecol not in d.columns:
            continue
        d["act_symbol"] = os.path.basename(f).split("__")[1].replace(".parquet", "")
        out.append(d)
    if not out:
        return pd.DataFrame()
    d = pd.concat(out, ignore_index=True)
    d["date"] = pd.to_datetime(d[datecol]).dt.tz_localize(None).dt.normalize()
    for c in d.columns:
        if c not in ("date", "act_symbol", datecol) and d[c].dtype == object:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.drop_duplicates(["act_symbol", "date"]).sort_values(["act_symbol", "date"])


def flow_features():
    v = load("options_volume")
    g = v.groupby("act_symbol", group_keys=False)
    tot = (v.call_volume + v.put_volume).replace(0, np.nan)
    v["pcr"] = v.put_volume / v.call_volume.replace(0, np.nan)
    # Pan-Poteshman-style signed volume: buyer-initiated calls minus buyer-initiated puts
    v["lean"] = ((v.call_volume_ask_side - v.call_volume_bid_side)
                 - (v.put_volume_ask_side - v.put_volume_bid_side)) / tot
    v["net_prem"] = (v.net_call_premium - v.net_put_premium) / (v.call_premium + v.put_premium).replace(0, np.nan)
    v["surge"] = tot / (v.avg_30_day_call_volume + v.avg_30_day_put_volume).replace(0, np.nan)
    v["lean_5d"] = g.lean.transform(lambda s: s.rolling(5, min_periods=3).mean())
    v["net_prem_5d"] = g.net_prem.transform(lambda s: s.rolling(5, min_periods=3).mean())
    v["pcr_5d"] = g.pcr.transform(lambda s: s.rolling(5, min_periods=3).mean())
    v["opt_vol"] = tot
    return v[["date", "act_symbol", "pcr", "pcr_5d", "lean", "lean_5d", "net_prem", "net_prem_5d", "surge", "opt_vol"]]


def greek_features():
    gx = load("greek_exposure")
    if gx.empty:
        return gx
    gx["net_gamma"] = gx.call_gamma + gx.put_gamma
    gx["net_delta"] = gx.call_delta + gx.put_delta
    gx["net_vanna"] = gx.call_vanna + gx.put_vanna
    gx["net_charm"] = gx.call_charm + gx.put_charm
    g = gx.groupby("act_symbol", group_keys=False)
    gx["d_gamma_5d"] = g.net_gamma.diff(5)
    gx["d_delta_5d"] = g.net_delta.diff(5)
    return gx[["date", "act_symbol", "net_gamma", "net_delta", "net_vanna", "net_charm", "d_gamma_5d", "d_delta_5d"]]


def vol_features():
    rv = load("realized_vol")
    if rv.empty:
        return rv
    rv["uw_ivrv"] = rv.implied_volatility - rv.realized_volatility
    rv["uw_iv_ratio"] = rv.implied_volatility / rv.realized_volatility.replace(0, np.nan)
    return rv[["date", "act_symbol", "uw_ivrv", "uw_iv_ratio"]]


def insider_features():
    ins = load("insider", datecol="filing_date")
    if ins.empty:
        return ins
    ins = ins.sort_values(["act_symbol", "date"])
    g = ins.groupby("act_symbol", group_keys=False)
    ins["net_buys_30d"] = g.purchases.transform(lambda s: s.rolling(30, min_periods=1).sum()) \
        - g.sells.transform(lambda s: s.rolling(30, min_periods=1).sum())
    ins["net_notional_30d"] = g.purchases_notional.transform(lambda s: s.rolling(30, min_periods=1).sum()) \
        - g.sells_notional.transform(lambda s: s.rolling(30, min_periods=1).sum())
    return ins[["date", "act_symbol", "net_buys_30d", "net_notional_30d"]]


FEATURES = {
    "lean":            (+1, "signed option volume, same day (Pan-Poteshman proxy) -> up"),
    "lean_5d":         (+1, "signed option volume, 5-day mean -> up"),
    "net_prem":        (+1, "net call minus net put premium, same day -> up"),
    "net_prem_5d":     (+1, "net premium, 5-day mean -> up"),
    "pcr":             (-1, "put/call volume ratio -> down"),
    "pcr_5d":          (-1, "put/call volume ratio, 5-day -> down"),
    "os_ratio":        (-1, "Johnson-So option/stock volume -> down"),
    "surge":           (-1, "option volume vs 30-day average (attention) -> down"),
    "net_gamma":       (0,  "dealer net gamma: no directional claim"),
    "net_delta":       (0,  "dealer net delta: no directional claim"),
    "net_vanna":       (0,  "dealer net vanna: no directional claim"),
    "d_gamma_5d":      (0,  "change in dealer gamma: no claim"),
    "d_delta_5d":      (0,  "change in dealer delta: no claim"),
    "uw_ivrv":         (0,  "vendor IV - RV: no directional claim"),
    "net_buys_30d":    (+1, "insider purchases minus sells, 30 filing days -> up"),
    "net_notional_30d": (+1, "insider net notional, 30 days -> up"),
}


def ic_table(d, ycol):
    rows = []
    for f, (sgn, src) in FEATURES.items():
        if f not in d:
            continue
        s = sgn if sgn != 0 else 1
        x = d[[f, ycol, "date"]].dropna()
        x = x[np.isfinite(x[f])]
        if x.date.nunique() < 15:
            continue
        ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * s, g[ycol])[0] if len(g) >= 30 else np.nan,
                                      include_groups=False).dropna()
        if len(ics) < 15:
            continue
        half = ics.index[len(ics) // 2]
        a, b = ics[ics.index < half], ics[ics.index >= half]
        rows.append({"feature": f, "sign": "+" if sgn > 0 else ("-" if sgn < 0 else "0"),
                     "weeks": len(ics), "n": len(x), "IC": ics.mean(),
                     "t": ics.mean() / ics.std() * np.sqrt(len(ics)), "hit": (ics > 0).mean(),
                     "1st half": f"{a.mean():+.3f} (t{a.mean()/a.std()*np.sqrt(len(a)):+.1f})",
                     "2nd half": f"{b.mean():+.3f} (t{b.mean()/b.std()*np.sqrt(len(b)):+.1f})"})
    return pd.DataFrame(rows).sort_values("t", ascending=False)


def main():
    pd.set_option("display.width", 250)
    base = pd.read_parquet(os.path.join(PANEL, "xsec_panel.parquet"))
    base["act_symbol"] = base.act_symbol.astype(str)
    base = universe(base)[["date", "act_symbol", "fwd5", "fwd10", "fwd21", "atm_iv", "rv21"]]
    vol = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), columns=["date", "act_symbol", "volume"])
    vol["act_symbol"] = vol.act_symbol.astype(str)
    base = base.merge(vol, on=["date", "act_symbol"], how="left")
    d = base.merge(flow_features(), on=["date", "act_symbol"], how="inner")
    d["os_ratio"] = d.opt_vol * 100 / d.volume.replace(0, np.nan)
    for fe in (greek_features(), vol_features(), insider_features()):
        if not fe.empty:
            d = d.merge(fe, on=["date", "act_symbol"], how="left")
    print(f"joined panel: {len(d):,} name-days, {d.act_symbol.nunique()} names, "
          f"{d.date.min().date()} .. {d.date.max().date()}")
    for h, every in ((5, 1), (10, 2), (21, 4)):
        w = weekly(d, every)
        print(f"\n===== horizon {h}d: {w.date.nunique()} dates, {len(w):,} obs =====")
        t = ic_table(w, f"fwd{h}")
        print(t.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    n = len(FEATURES) * 3
    print(f"\n{n} tests; expected max |t| under the null ~ {np.sqrt(2*np.log(n)):.1f}")
    d.to_parquet(os.path.join(PANEL, "uw_panel.parquet"), index=False)


if __name__ == "__main__":
    main()
