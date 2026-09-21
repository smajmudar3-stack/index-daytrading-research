"""uw_intraday_flow_test.py — does the vendor's per-minute signed options flow predict the
index proxies over the next 30 to 120 minutes?

Data: the Unusual Whales archive `uw_archive.py` has been writing since 2026-04-24 --
`net_prem_ticks` (per-minute net call premium, net put premium, net delta, ask/bid-side
volume) and `ohlc_1m` for SPY / QQQ / IWM, ~103 sessions. This is the vendor's own
classification of who is buying and who is selling, which is the thing the earlier
SPXW flow study (`hunt_flow.py`, null on 1,919 sessions) did not have.

Signals, all computed from flow at or before minute t, normalised PAST-ONLY (the
session's expanding mean and std, shifted one bar -- a whole-session z-score once produced
t = +15.6 out of pure leakage, FINDINGS.md §3):
    cum_delta      net delta flow accumulated since the open
    cum_prem       net (call - put) premium accumulated since the open
    d30_delta      net delta flow over the last 30 minutes
    d30_prem       net premium over the last 30 minutes
    imb30          (ask-side - bid-side volume) / total over the last 30 minutes
Labels: the forward 30 / 60 / 120-minute mid return from the SAME minute's close.

Read as METHODOLOGY_TRAPS #5 and #7 demand: Spearman as well as Pearson, leave-the-largest-
day-out, and the mirror test (a "signal" that fires both ways is volatility, not direction).
103 sessions × 3 names is small; a t below ~3 here is noise, and a t above 10 is a bug.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

H = os.path.join(paths.DATA_ROOT, "uw_hist")
HORIZONS = (30, 60, 120)


def load(sym):
    f = pd.read_parquet(os.path.join(H, "net_prem_ticks.parquet"))
    f = f[f._symbol == sym].copy()
    f["t"] = pd.to_datetime(f.tape_time, utc=True).dt.tz_convert("America/New_York")
    for c in ("net_call_premium", "net_put_premium", "net_delta", "call_volume_ask_side",
              "call_volume_bid_side", "put_volume_ask_side", "put_volume_bid_side"):
        f[c] = pd.to_numeric(f[c], errors="coerce")
    f = f.drop_duplicates("t").set_index("t").sort_index()
    px = pd.read_parquet(os.path.join(H, "ohlc_1m.parquet"))
    px = px[(px._symbol == sym) & (px.market_time == "r")].copy()
    px["t"] = pd.to_datetime(px.start_time, utc=True).dt.tz_convert("America/New_York")
    px["close"] = pd.to_numeric(px.close, errors="coerce")
    px = px.drop_duplicates("t").set_index("t").sort_index()[["close"]]
    d = px.join(f, how="inner")
    d["session"] = d.index.date
    d = d[(d.index.hour * 60 + d.index.minute >= 9 * 60 + 30) & (d.index.hour * 60 + d.index.minute < 16 * 60)]
    return d


def features(d):
    g = d.groupby("session", group_keys=False)
    d["prem"] = d.net_call_premium.fillna(0) - d.net_put_premium.fillna(0)
    d["dlt"] = d.net_delta.fillna(0)
    d["cum_delta"] = g.dlt.cumsum()
    d["cum_prem"] = g.prem.cumsum()
    d["d30_delta"] = g.dlt.transform(lambda s: s.rolling(30, min_periods=15).sum())
    d["d30_prem"] = g.prem.transform(lambda s: s.rolling(30, min_periods=15).sum())
    ask = d.call_volume_ask_side.fillna(0) - d.put_volume_ask_side.fillna(0)
    bid = d.call_volume_bid_side.fillna(0) - d.put_volume_bid_side.fillna(0)
    tot = (d.call_volume_ask_side.fillna(0) + d.call_volume_bid_side.fillna(0)
           + d.put_volume_ask_side.fillna(0) + d.put_volume_bid_side.fillna(0))
    d["imb_raw"] = (ask - bid)
    d["tot"] = tot
    d["imb30"] = (g.imb_raw.transform(lambda s: s.rolling(30, min_periods=15).sum())
                  / g.tot.transform(lambda s: s.rolling(30, min_periods=15).sum()).replace(0, np.nan))
    # past-only normalisation within the session
    for c in ("cum_delta", "cum_prem", "d30_delta", "d30_prem"):
        m = g[c].transform(lambda s: s.expanding().mean().shift(1))
        sd = g[c].transform(lambda s: s.expanding().std().shift(1))
        d[f"z_{c}"] = (d[c] - m) / sd.replace(0, np.nan)
    for h in HORIZONS:
        d[f"fwd{h}"] = g.close.transform(lambda s: s.shift(-h) / s - 1)
    return d


FEATS = ["z_cum_delta", "z_cum_prem", "z_d30_delta", "z_d30_prem", "imb30"]


def score(d, sym):
    rows = []
    # sample every 30 minutes so forward windows overlap as little as possible
    s = d[(d.index.minute % 30 == 0)]
    for f in FEATS:
        for h in HORIZONS:
            x = s[[f, f"fwd{h}", "session"]].dropna()
            if len(x) < 200:
                continue
            pr, sp = stats.pearsonr(x[f], x[f"fwd{h}"])[0], stats.spearmanr(x[f], x[f"fwd{h}"])[0]
            n = len(x)
            t_sp = sp * np.sqrt((n - 2) / max(1e-9, 1 - sp * sp))
            # leave out the session with the largest |feature|
            big = x.loc[x[f].abs().idxmax(), "session"]
            x2 = x[x.session != big]
            sp2 = stats.spearmanr(x2[f], x2[f"fwd{h}"])[0]
            # mirror: hit rate of sign(feature) == sign(fwd), split by feature sign
            up = x[x[f] > 0]; dn = x[x[f] < 0]
            rows.append({"sym": sym, "feature": f, "h": h, "n": n, "pearson": pr, "spearman": sp,
                         "t_sp": t_sp, "sp_drop_biggest_day": sp2,
                         "P(up|flow+)": (up[f"fwd{h}"] > 0).mean(), "P(dn|flow-)": (dn[f"fwd{h}"] < 0).mean(),
                         "bp/trade sign-follow": (np.sign(x[f]) * x[f"fwd{h}"]).mean() * 1e4})
    return pd.DataFrame(rows)


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
    out = []
    for sym in ("SPY", "QQQ", "IWM"):
        d = load(sym)
        if d.empty:
            print(sym, "no joined data"); continue
        d = features(d)
        print(f"{sym}: {d.session.nunique()} sessions, {len(d):,} minutes")
        out.append(score(d, sym))
    t = pd.concat(out, ignore_index=True)
    print(t.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    print(f"\n{len(t)} tests; expected max |t| under the null ~ {np.sqrt(2*np.log(len(t))):.1f}. "
          f"A round-trip on SPY options costs ~5-10 bp of notional; the last column is gross.")


if __name__ == "__main__":
    main()
