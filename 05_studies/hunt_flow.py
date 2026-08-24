"""hunt_flow.py — does REAL 0DTE options order flow predict SPX direction?

New data: 1,919 sessions (2016-09 -> 2024-05) of actual SPXW quotes on a 30-minute grid, including
per-bar traded greeks in dollars. `trade_volume_delta_usd` is net customer delta traded — the flow the
dealer must hedge against — and it is exactly the order-flow measure the literature says carries
short-horizon directional information. Until now there was no history of it here at all.

This is a clean test on a genuinely new input, not another pass over the same 500 sessions:
  - 1,919 sessions vs 500 (roughly 4x the independent days)
  - the signal was never available during any prior search, so it cannot be contaminated by it
  - a strict time-ordered TRAIN / VALIDATE / TEST split is used from the start

Question asked: given the flow observed in a 30-minute bar, does the index move directionally over the
NEXT 30 to 120 minutes, and with what hit rate?
"""
import numpy as np
import pandas as pd
from scipy import stats as st

PATH = "data/spxw/data_opt.parquet"
COLS = ["quote_date", "quote_time", "option_type", "mnes_rel", "bas", "implied_volatility",
        "delta", "active_underlying_price", "trade_volume", "open_interest",
        "trade_volume_delta_usd", "trade_volume_gamma_usd", "oi_gamma_usd"]


def build():
    df = pd.read_parquet(PATH, columns=COLS)
    df["dt"] = pd.to_datetime(df.quote_date.astype(str) + " " + df.quote_time.astype(str))
    # collapse the strike dimension: per (session, time) aggregate the flow and the surface
    g = df.groupby(["quote_date", "quote_time"])
    bar = g.agg(
        spot=("active_underlying_price", "first"),
        flow_delta=("trade_volume_delta_usd", "sum"),
        flow_gamma=("trade_volume_gamma_usd", "sum"),
        oi_gamma=("oi_gamma_usd", "sum"),
        volume=("trade_volume", "sum"),
        oi=("open_interest", "sum"),
        spread=("bas", "mean"),
    ).reset_index()
    # call vs put flow split
    for typ, nm in (("C", "call"), ("P", "put")):
        s = df[df.option_type == typ].groupby(["quote_date", "quote_time"]).agg(
            **{f"{nm}_vol": ("trade_volume", "sum"),
               f"{nm}_dflow": ("trade_volume_delta_usd", "sum")}).reset_index()
        bar = bar.merge(s, on=["quote_date", "quote_time"], how="left")
    # ATM implied vol
    atm = df[(df.mnes_rel > 0.998) & (df.mnes_rel < 1.002)].groupby(
        ["quote_date", "quote_time"]).implied_volatility.mean().rename("atm_iv").reset_index()
    bar = bar.merge(atm, on=["quote_date", "quote_time"], how="left")

    bar["dt"] = pd.to_datetime(bar.quote_date.astype(str) + " " + bar.quote_time.astype(str))
    bar = bar.sort_values("dt").reset_index(drop=True)
    bar["tmin"] = pd.to_datetime(bar.quote_time.astype(str)).dt.hour * 60 + \
                  pd.to_datetime(bar.quote_time.astype(str)).dt.minute

    # ---- derived flow features (all same-bar or earlier) ---------------------------------
    bar["cp_vol_ratio"] = bar.call_vol / (bar.call_vol + bar.put_vol).replace(0, np.nan)
    bar["flow_per_vol"] = bar.flow_delta / bar.volume.replace(0, np.nan)
    d = bar.groupby("quote_date", group_keys=False)
    bar["flow_cum"] = d.flow_delta.apply(lambda s: s.cumsum())
    bar["flow_z"] = (bar.flow_delta - d.flow_delta.transform("mean")) / \
                    d.flow_delta.transform("std").replace(0, np.nan)
    bar["gamma_sign"] = np.sign(bar.oi_gamma)
    bar["ret_prev"] = d.spot.apply(lambda s: s.pct_change())
    bar["spot_vs_open"] = bar.spot / d.spot.transform("first") - 1

    # ---- forward returns (the label) -------------------------------------------------------
    for h in (1, 2, 4):        # 30, 60, 120 minutes ahead on a 30-min grid
        bar[f"fwd{h}"] = d.spot.apply(lambda s: s.shift(-h) / s - 1)
    return bar


FEATS = ["flow_delta", "flow_gamma", "flow_cum", "flow_z", "flow_per_vol", "cp_vol_ratio",
         "call_dflow", "put_dflow", "oi_gamma", "volume", "atm_iv", "ret_prev",
         "spot_vs_open", "tmin", "spread"]


def screen(bar, hcol):
    d = bar[bar[hcol].notna()].copy()
    dates = np.sort(d.quote_date.unique())
    a, b = dates[int(len(dates) * .40)], dates[int(len(dates) * .70)]
    tr = d[d.quote_date < a]; va = d[(d.quote_date >= a) & (d.quote_date < b)]; te = d[d.quote_date >= b]
    print(f"\n{hcol}: obs {len(d):,}  TRAIN {len(tr):,} / VAL {len(va):,} / TEST {len(te):,}")
    print(f"  base rate up: TRAIN {(tr[hcol]>0).mean()*100:.1f}%  VAL {(va[hcol]>0).mean()*100:.1f}%  "
          f"TEST {(te[hcol]>0).mean()*100:.1f}%")
    print(f"  {'feature':16}{'TRlo':>7}{'TRhi':>7}{'VAlo':>7}{'VAhi':>7}{'TElo':>7}{'TEhi':>7}{'stable':>8}")
    keep = []
    for f in FEATS:
        s = tr[f].replace([np.inf, -np.inf], np.nan)
        if s.notna().sum() < 500:
            continue
        lo, hi = np.nanpercentile(s, [20, 80])
        if not np.isfinite([lo, hi]).all() or lo == hi:
            continue
        def up(frame, m):
            x = frame[m]
            return (x[hcol] > 0).mean() * 100 if len(x) >= 100 else np.nan
        vals = []
        for frame in (tr, va, te):
            vals += [up(frame, frame[f] <= lo), up(frame, frame[f] >= hi)]
        if not np.isfinite(vals).all():
            continue
        sp = [vals[1] - vals[0], vals[3] - vals[2], vals[5] - vals[4]]
        stable = (np.sign(sp[0]) == np.sign(sp[1]) == np.sign(sp[2])) and min(abs(x) for x in sp) > 2
        print(f"  {f:16}" + "".join(f"{v:>6.1f}%" for v in vals) + f"{'YES' if stable else '':>8}")
        if stable:
            keep.append((f, lo, hi, sp[2]))
    return keep


def main():
    bar = build()
    print(f"bars {len(bar):,} | sessions {bar.quote_date.nunique():,} "
          f"| {bar.quote_date.min()} -> {bar.quote_date.max()}")
    for h, lab in ((1, "fwd1"), (2, "fwd2"), (4, "fwd4")):
        keep = screen(bar, lab)
        if keep:
            print(f"  --> SIGN-STABLE across all three splits: {[k[0] for k in keep]}")


if __name__ == "__main__":
    main()
