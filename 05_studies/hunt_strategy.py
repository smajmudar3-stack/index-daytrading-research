"""hunt_strategy.py — turn the surviving signals into an actual traded rule and measure it.

Two things survived the univariate screen with a CONSISTENT sign across train and test:
  gz      high dealer gamma -> a clean move, when it happens, is mostly DOWN (12.8% up train / 29.0% test)
  or_pos  position in the opening range -> high = more likely to resolve down

Plus, from the earlier intraday work: volume confirmation on the trigger bar mattered more than any
other mechanic.

This tests the CORRECTED rule. The earlier version bought calls on up-breaks and lost on high-gamma
days; if high gamma resolves DOWN, the fix is to trade the side the regime favours rather than the
side the break points at.

Measured the way the owner actually trades: signal -> buy the option -> take profit at a premium
target, stop at a premium stop, hard time stop. Options priced per minute with Black-Scholes on the
remaining session so theta is charged properly. Train/test split is time-ordered.
"""
import numpy as np
import pandas as pd

import bt_options as bo
import hunt_features as HF

SPREAD, FEE = 0.010, 0.05
SESSION_MIN = 390
START = 2000.0


def opt(S, K, ml, iv, call):
    return bo.bs(S, K, max(ml, 0.5) / SESSION_MIN / 252.0, iv, call)


def simulate(df, cfg, tp, stop, hold):
    """One trade per session at most. cfg decides IF and WHICH SIDE."""
    trades = []
    for date, g in df.groupby("date"):
        if g.empty:
            continue
        iv_d = float(g.sig_hat.iloc[0]) * bo.SQRT252 if np.isfinite(g.sig_hat.iloc[0]) else np.nan
        if not np.isfinite(iv_d) or iv_d <= 0:
            continue
        gz = float(g.gz.iloc[0]) if np.isfinite(g.gz.iloc[0]) else 0.0
        # regime gate
        if cfg.get("gz_min") is not None and gz < cfg["gz_min"]:
            continue
        if cfg.get("gz_max") is not None and gz > cfg["gz_max"]:
            continue
        live = g[(g.mins >= cfg.get("start_min", 600)) & (g.mins <= cfg.get("last_min", 780))]
        if live.empty:
            continue
        entry_row = None
        for ts, r in live.iterrows():
            if not np.isfinite(r.rvol) or r.rvol < cfg.get("min_rvol", 0):
                continue
            if cfg.get("min_orpos") is not None and not (np.isfinite(r.or_pos) and r.or_pos >= cfg["min_orpos"]):
                continue
            if cfg.get("max_orpos") is not None and not (np.isfinite(r.or_pos) and r.or_pos <= cfg["max_orpos"]):
                continue
            entry_row = r
            break
        if entry_row is None:
            continue
        side = cfg["side"]
        if side == "follow":
            side = "call" if entry_row.close > entry_row.vwap else "put"
        if side == "fade":
            side = "put" if entry_row.close > entry_row.vwap else "call"
        call = side == "call"
        S0, m0 = entry_row.close, entry_row.mins
        K = round(S0)
        e_mid = opt(S0, K, SESSION_MIN - (m0 - 570), iv_d, call)
        if e_mid <= 0.05:
            continue
        entry = e_mid * (1 + SPREAD) + FEE / 100.0
        path = g[(g.mins > m0) & (g.mins <= min(m0 + hold, 955))]
        ret = None
        for ts, r in path.iterrows():
            ml = SESSION_MIN - (r.mins - 570)
            adv = r.low if call else r.high
            fav = r.high if call else r.low
            if (opt(adv, K, ml, iv_d, call) * (1 - SPREAD) - entry) / entry <= stop:
                ret = stop
                break
            if (opt(fav, K, ml, iv_d, call) * (1 - SPREAD) - entry) / entry >= tp:
                ret = tp
                break
        if ret is None and len(path):
            last = path.iloc[-1]
            ex = opt(last.close, K, SESSION_MIN - (last.mins - 570), iv_d, call) * (1 - SPREAD)
            ret = (ex - entry) / entry
        if ret is not None:
            trades.append({"date": date, "ret": ret, "side": side, "gz": gz})
    return pd.DataFrame(trades)


def summarize(tr, rf=0.25):
    if tr.empty or len(tr) < 15:
        return None
    s = tr.copy()
    s["mo"] = pd.to_datetime(s.date).dt.to_period("M")
    mo = s.groupby("mo")["ret"].apply(lambda x: np.prod(1 + x * rf) - 1).values
    eq = np.cumprod(1 + mo)
    peak = np.maximum.accumulate(eq)
    return dict(n=len(tr), win=(tr.ret > 0).mean(), avg=tr.ret.mean(),
                mo_mean=mo.mean(), mo_med=np.median(mo), months=len(mo),
                final=eq[-1], mdd=((peak - eq) / peak).max() * 100)


def main():
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    print(f"STRATEGY HUNT — {sym}, intraday directional 0DTE")
    df = HF.load(sym)
    df = HF.add_features(df)
    df = HF.add_daily(df)
    dates = sorted(df.date.unique())
    split = dates[len(dates) // 2]
    tr_df, te_df = df[df.date < split], df[df.date >= split]
    print(f"TRAIN {dates[0].date()}->{split.date()}  TEST {split.date()}->{dates[-1].date()}\n")

    TP, STOP, HOLD = 1.00, -0.50, 30
    variants = [
        ("follow break, no regime filter",      dict(side="follow", min_rvol=1.2)),
        ("high gz (>0.5) -> BUY PUTS",          dict(side="put", gz_min=0.5, min_rvol=1.2)),
        ("high gz (>0.5) -> buy calls (ctrl)",  dict(side="call", gz_min=0.5, min_rvol=1.2)),
        ("high gz + fade the vwap side",        dict(side="fade", gz_min=0.5, min_rvol=1.2)),
        ("high gz + puts + upper OR (>0.6)",    dict(side="put", gz_min=0.5, min_rvol=1.2, min_orpos=0.6)),
        ("mid gz (-0.5..0.5) follow break",     dict(side="follow", gz_min=-0.5, gz_max=0.5, min_rvol=1.2)),
        ("low gz (<-0.5) -> BUY PUTS",          dict(side="put", gz_max=-0.5, min_rvol=1.2)),
        ("low gz (<-0.5) follow break",         dict(side="follow", gz_max=-0.5, min_rvol=1.2)),
    ]
    print(f"{'variant':38}{'TRAIN n':>8}{'win%':>7}{'avg':>8}  {'TEST n':>7}{'win%':>7}{'avg':>8}"
          f"{'mo%':>8}{'maxDD':>8}")
    print("-" * 96)
    for label, cfg in variants:
        a = simulate(tr_df, cfg, TP, STOP, HOLD)
        b = simulate(te_df, cfg, TP, STOP, HOLD)
        sa, sb = summarize(a), summarize(b)
        if sa is None or sb is None:
            print(f"{label:38}{'too few trades':>58}")
            continue
        print(f"{label:38}{sa['n']:>8}{sa['win']*100:>6.0f}%{sa['avg']*100:>+7.1f}%  "
              f"{sb['n']:>7}{sb['win']*100:>6.0f}%{sb['avg']*100:>+7.1f}%"
              f"{sb['mo_mean']*100:>+7.1f}%{-sb['mdd']:>7.0f}%")


if __name__ == "__main__":
    main()
