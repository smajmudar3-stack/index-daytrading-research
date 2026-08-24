"""backtest_intraday_v2.py — can we make the DIRECTION call better?

v1 found the mechanics roughly break-even (-0.4%/trade) with a 43-49% hit rate. The owner's diagnosis
is correct: direction is the binding constraint, not the structure. This tests whether any available
conditioning variable actually improves the directional hit rate.

Two defects in v1 are fixed first, both of which cost real accuracy:
  1. v1 only ever bought CALLS, even when price broke DOWN through the opening range. Direction now
     follows the break.
  2. v1 applied NO gamma filter. That is backwards. The validated finding is that HIGH gamma compresses
     the range (0.843x implied) - which is exactly why the condor works there. The corollary is that
     LOW/negative gamma days expand it (1.139x), and those are the days a directional trade has fuel.
     Buying premium on a high-gamma pin day is fighting the one thing this repo has actually proven.

Filters tested (each reported with its control, so the marginal contribution is visible):
  gamma regime, DIX confluence agreement, opening-range width vs expected move, volume confirmation.

ANTI-OVERFIT: 500 sessions is a small sample and this searches a wide grid. Everything is split
TRAIN (first half) / TEST (second half); parameters are chosen on TRAIN only and the TEST number is
what counts. Both are printed so the gap is visible.
"""
import glob
import numpy as np
import pandas as pd

import bt_options as bo
import backtest_0dte_rules as B

from idt import paths

SPREAD, FEE = 0.010, 0.05
OR_MIN, SESSION_MIN = 30, 390
START = 2000.0


def load_minutes(sym="SPY"):
    fs = sorted(glob.glob(paths.require_data("minute", sym) + "/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in fs])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df["date"] = df.index.normalize().tz_localize(None)
    df["mins"] = df.index.hour * 60 + df.index.minute
    return df[(df.mins >= 570) & (df.mins < 960)]


def daily_panel():
    d = B.build_panel()
    d = B.add_signals(d)
    d["date"] = pd.to_datetime(d.date)
    return d.set_index("date")[["sig_hat", "conf", "gz", "dz"]]


def opt(S, K, ml, iv, call):
    return bo.bs(S, K, max(ml, 0.5) / SESSION_MIN / 252.0, iv, call)


def run_day(bars, iv, tp, stop, hold, cfg, row):
    o = bars[bars.mins < 570 + OR_MIN]
    if len(o) < 10:
        return None
    hi, lo = o.high.max(), o.low.min()
    orw = (hi - lo) / o.close.iloc[-1]                 # opening-range width, fractional
    exp_move = iv / bo.SQRT252                          # 1-day sigma, fractional
    # FILTER: opening range must be TIGHT relative to the day's expected move. A wide OR means the
    # move already happened; a tight one that breaks is a real initiation.
    if cfg.get("max_or") is not None and orw > cfg["max_or"] * exp_move:
        return None
    live = bars[(bars.mins >= 570 + OR_MIN) & (bars.mins <= 780)]
    if live.empty:
        return None
    vol_ref = o.volume.mean()
    trig = None
    for ts, r in live.iterrows():
        up = r.close > hi and r.close > r.vwap
        dn = r.close < lo and r.close < r.vwap
        if not (up or dn):
            continue
        if cfg.get("min_rvol") and vol_ref > 0 and r.volume < cfg["min_rvol"] * vol_ref:
            continue                                    # FILTER: needs real volume behind the break
        side = "call" if up else "put"
        # FILTER: only trade breaks that agree with the DIX confluence read
        if cfg.get("conf_agree") and side == "call" and row.conf < 2:
            continue
        if cfg.get("conf_agree") and side == "put" and row.conf >= 2:
            continue
        trig = (r, side)
        break
    if trig is None:
        return None
    r0, side = trig
    call = side == "call"
    S0, m0 = r0.close, r0.mins
    K = round(S0)
    e_mid = opt(S0, K, SESSION_MIN - (m0 - 570), iv, call)
    if e_mid <= 0.05:
        return None
    entry = e_mid * (1 + SPREAD) + FEE / 100.0
    path = bars[(bars.mins > m0) & (bars.mins <= min(m0 + hold, 955))]
    for ts, r in path.iterrows():
        ml = SESSION_MIN - (r.mins - 570)
        adv = r.low if call else r.high
        fav = r.high if call else r.low
        if (opt(adv, K, ml, iv, call) * (1 - SPREAD) - entry) / entry <= stop:
            return stop, side
        if (opt(fav, K, ml, iv, call) * (1 - SPREAD) - entry) / entry >= tp:
            return tp, side
    if len(path):
        last = path.iloc[-1]
        ex = opt(last.close, K, SESSION_MIN - (last.mins - 570), iv, call) * (1 - SPREAD)
        return (ex - entry) / entry, side
    return None


def backtest(mins, panel, tp, stop, hold, cfg):
    out = []
    for date, bars in mins.groupby("date"):
        if date not in panel.index:
            continue
        row = panel.loc[date]
        sig = float(row.sig_hat)
        if not np.isfinite(sig) or sig <= 0:
            continue
        gz = float(row.gz)
        if cfg.get("gz_max") is not None and gz > cfg["gz_max"]:
            continue                                    # FILTER: gamma regime
        r = run_day(bars, sig * bo.SQRT252, tp, stop, hold, cfg, row)
        if r is not None:
            out.append({"date": date, "ret": r[0], "side": r[1], "gz": gz})
    return pd.DataFrame(out)


def stats(tr, rf=0.25):
    if tr.empty or len(tr) < 20:
        return None
    s = tr.copy()
    s["wk"] = pd.to_datetime(s.date).dt.to_period("W")
    wk = s.groupby("wk")["ret"].apply(lambda x: np.prod(1 + x * rf) - 1).values
    eq = np.cumprod(1 + wk)
    peak = np.maximum.accumulate(eq)
    return dict(n=len(tr), win=(tr.ret > 0).mean(), avg=tr.ret.mean(),
                mean_wk=wk.mean(), final=eq[-1], mdd=((peak - eq) / peak).max() * 100)


def main():
    mins = load_minutes("SPY")
    panel = daily_panel()
    dates = sorted(mins.date.unique())
    split = dates[len(dates) // 2]
    tr_m = mins[mins.date < split]
    te_m = mins[mins.date >= split]
    print("IMPROVING THE DIRECTION CALL — SPY 0DTE, intraday hold")
    print(f"TRAIN {dates[0].date()} -> {split.date()}   TEST {split.date()} -> {dates[-1].date()}")
    print("v1 defects fixed: direction now follows the break (puts allowed), gamma regime available\n")

    TP, STOP, HOLD = 1.00, -0.50, 30       # v1's best mechanics, held fixed
    variants = [
        ("baseline (v1: calls only, no filter)", dict(calls_only=True)),
        ("+ direction follows the break", dict()),
        ("+ only gz < 0   (short gamma)", dict(gz_max=0.0)),
        ("+ only gz < -0.5 (strong short gamma)", dict(gz_max=-0.5)),
        ("+ tight opening range (<0.8 sigma)", dict(gz_max=0.0, max_or=0.8)),
        ("+ volume confirmation (1.2x)", dict(gz_max=0.0, min_rvol=1.2)),
        ("+ DIX confluence agreement", dict(gz_max=0.0, conf_agree=True)),
        ("+ tight OR AND volume", dict(gz_max=0.0, max_or=0.8, min_rvol=1.2)),
    ]
    print(f"{'variant':42}{'TRAIN n':>9}{'win%':>7}{'avg':>8}   {'TEST n':>8}{'win%':>7}{'avg':>8}{'mean wk':>10}")
    print("-" * 100)
    for label, cfg in variants:
        c = dict(cfg)
        calls_only = c.pop("calls_only", False)
        a = backtest(tr_m, panel, TP, STOP, HOLD, c)
        b = backtest(te_m, panel, TP, STOP, HOLD, c)
        if calls_only:
            a = a[a.side == "call"] if not a.empty else a
            b = b[b.side == "call"] if not b.empty else b
        sa, sb = stats(a), stats(b)
        if sa is None or sb is None:
            print(f"{label:42}{'too few trades':>40}")
            continue
        print(f"{label:42}{sa['n']:>9}{sa['win']*100:>6.0f}%{sa['avg']*100:>+7.1f}%   "
              f"{sb['n']:>8}{sb['win']*100:>6.0f}%{sb['avg']*100:>+7.1f}%{sb['mean_wk']*100:>+9.2f}%")

    # does the gamma regime actually separate directional outcomes? (the core hypothesis)
    print("\n== DOES GAMMA REGIME SEPARATE DIRECTIONAL OUTCOMES? (all sessions, no other filter) ==")
    allt = backtest(mins, panel, TP, STOP, HOLD, {})
    if not allt.empty:
        for lab, m in (("gz < -0.5 (big range expected)", allt.gz < -0.5),
                       ("-0.5 <= gz < 0.5", (allt.gz >= -0.5) & (allt.gz < 0.5)),
                       ("gz >= 0.5 (pin — condor territory)", allt.gz >= 0.5)):
            s = allt[m]
            if len(s) < 15:
                continue
            print(f"  {lab:36} n={len(s):4d}  win {(s.ret>0).mean()*100:3.0f}%  "
                  f"avg {s.ret.mean()*100:+.1f}%")
        print("\n== CALLS vs PUTS ==")
        for side in ("call", "put"):
            s = allt[allt.side == side]
            if len(s) < 15:
                continue
            print(f"  {side:6} n={len(s):4d}  win {(s.ret>0).mean()*100:3.0f}%  avg {s.ret.mean()*100:+.1f}%")


if __name__ == "__main__":
    main()
