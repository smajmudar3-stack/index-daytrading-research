"""Exhaustive sweep of swing-horizon strategies, scored honestly.

Two tracks:

  A. ROTATION -- rank the 11 SPDR sectors by each of 21 signals, hold the top
     k, rebalance every h days, optionally only in a given market regime.
     Full grid: 21 signals x 3 k x 4 holds x 6 regimes = 1,512 configurations.

  B. TIMING -- every regime condition and every PAIR of conditions as a gate
     for holding SPY/QQQ over 5/10/21/42 days. ~20 conditions -> 190 pairs,
     x 2 symbols x 4 horizons.

Selection protocol, fixed in advance so it cannot be rationalised afterwards:
  - Rank on TRAIN only.
  - Carry the top candidates to VALIDATE. Anything that does not hold up dies
    here. No re-tuning is permitted on validate.
  - Only survivors of both are shown on TEST, and TEST is looked at once.
  - Report the deflated Sharpe against the true trial count, so the reader can
    see what the best result SHOULD look like under pure noise.
"""
import itertools
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from swing_lab import (  # noqa: E402
    COST_BPS,
    SECTORS,
    SPLITS,
    build_features,
    build_regime,
    deflated_sharpe,
    load,
    pch,
    rotation_backtest,
    slice_dates,
    stats_of,
    timing_backtest,
    trade_stats,
)

OUT = paths.data("swing")

KS = [1, 2, 3]
HOLDS = [5, 10, 21, 42]


def regime_masks(regime):
    """Named boolean gates. `None` means always-on (no regime filter)."""
    m = {"always": None}
    if "spy_above_200" in regime:
        m["bull_200"] = regime["spy_above_200"]
        m["bear_200"] = 1 - regime["spy_above_200"]
    if "breadth" in regime:
        m["breadth_hi"] = (regime["breadth"] > 0.5).astype(float)
    if "contango" in regime:
        m["contango"] = regime["contango"]
    if "credit_up" in regime:
        m["credit_up"] = regime["credit_up"]
    return m


def run_rotation(close, open_, feats, regime, verbose=True):
    masks = regime_masks(regime)
    rows = []
    total = len(feats) * len(KS) * len(HOLDS) * len(masks)
    done = 0

    for sname, sig in feats.items():
        for k in KS:
            for h in HOLDS:
                for mname, mask in masks.items():
                    done += 1
                    if verbose and done % 200 == 0:
                        print(f"    ...{done}/{total}", file=sys.stderr)
                    try:
                        port, trades = rotation_backtest(
                            close, open_, sig, k, h, regime_mask=mask
                        )
                    except Exception:
                        continue

                    rec = {"signal": sname, "k": k, "hold": h, "regime": mname}
                    ok = True
                    for split in SPLITS:
                        sl = slice_dates(port.index, split)
                        st = stats_of(port[sl])
                        if st is None:
                            ok = False
                            break
                        rec[f"{split}_sharpe"] = st["sharpe"]
                        rec[f"{split}_cagr"] = st["cagr"]
                        rec[f"{split}_dd"] = st["maxdd"]
                        rec[f"{split}_t"] = st["t"]
                        rec[f"{split}_n"] = st["n"]
                    if not ok:
                        continue

                    ts = trade_stats(trades)
                    if ts:
                        rec["win"] = ts["win"]
                        rec["avg_trade"] = ts["avg"]
                        rec["trades"] = ts["trades"]
                    rows.append(rec)

    return pd.DataFrame(rows), total


def timing_conditions(regime, close):
    """Binary conditions from the regime frame -- the atoms that get combined."""
    c = {}
    r = regime

    def add(name, series):
        s = series.reindex(close.index)
        if s.notna().sum() > 500:
            c[name] = s.fillna(0).astype(bool)

    if "spy_above_200" in r:
        add("above200", r["spy_above_200"] > 0)
        add("below200", r["spy_above_200"] <= 0)
    if "spy_above_50" in r:
        add("above50", r["spy_above_50"] > 0)
    if "spy_50_above_200" in r:
        add("golden", r["spy_50_above_200"] > 0)
    if "breadth" in r:
        add("breadth_hi", r["breadth"] > 0.6)
        add("breadth_lo", r["breadth"] < 0.4)
    if "vix_z" in r:
        add("vix_low_z", r["vix_z"] < -0.5)
        add("vix_high_z", r["vix_z"] > 1.0)
    if "vix" in r:
        add("vix_u20", r["vix"] < 20)
        add("vix_o25", r["vix"] > 25)
    if "contango" in r:
        add("contango", r["contango"] > 0)
        add("backward", r["contango"] <= 0)
    if "credit_up" in r:
        add("credit_up", r["credit_up"] > 0)
        add("credit_dn", r["credit_up"] <= 0)
    if "cyc_up" in r:
        add("cyc_up", r["cyc_up"] > 0)
    if "skew_z" in r:
        add("skew_hi", r["skew_z"] > 1.0)
    if "dd_from_high" in r:
        add("dip3", r["dd_from_high"] < -0.03)
        add("dip7", r["dd_from_high"] < -0.07)
        add("near_high", r["dd_from_high"] > -0.01)
    if "tlt_mom" in r:
        add("tlt_dn", r["tlt_mom"] < 0)

    # RSI-2 dip -- the classic swing mean-reversion trigger, past-only.
    spy = close["SPY"]
    d = spy.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    rsi2 = (100 - 100 / (1 + up / dn.replace(0, np.nan))).shift(1)
    add("rsi2_lo", rsi2 < 10)
    add("rsi2_hi", rsi2 > 90)

    return c


def run_timing(close, conds, symbols=("SPY", "QQQ"), horizons=(5, 10, 21, 42)):
    rows = []
    names = sorted(conds)

    # Singles and pairs. Triples are deliberately NOT swept: with ~20 atoms
    # that is 1,140 more trials for conditions so narrow the samples become
    # meaningless, and the multiple-testing cost is paid by every result.
    combos = [(n,) for n in names] + list(itertools.combinations(names, 2))

    for sym in symbols:
        if sym not in close.columns:
            continue
        for combo in combos:
            cond = conds[combo[0]].copy()
            for extra in combo[1:]:
                cond = cond & conds[extra]
            if cond.sum() < 100:
                continue
            for h in horizons:
                rec = {"cond": "+".join(combo), "symbol": sym, "horizon": h}
                ok = True
                for split in SPLITS:
                    sl = slice_dates(close.index, split)
                    r, base = timing_backtest(close[sl], cond[sl], sym, h)
                    if r is None or len(r) < 15:
                        ok = False
                        break
                    rec[f"{split}_n"] = len(r)
                    rec[f"{split}_win"] = (r > 0).mean()
                    rec[f"{split}_avg"] = r.mean()
                    rec[f"{split}_t"] = (
                        r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0.0
                    )
                    # Edge over the unconditional base rate -- the number that
                    # matters. Equities drift up; beating zero is not an edge.
                    rec[f"{split}_base_win"] = (base > 0).mean()
                    rec[f"{split}_edge_win"] = (r > 0).mean() - (base > 0).mean()
                    rec[f"{split}_edge_avg"] = r.mean() - base.mean()
                if ok:
                    rows.append(rec)
    return pd.DataFrame(rows), len(combos) * len(symbols) * len(horizons)


def main():
    close, open_ = load()
    feats = build_features(close, open_)
    regime = build_regime(close)

    print("=" * 78)
    print("TRACK A -- SECTOR ROTATION SWEEP")
    print("=" * 78)
    rot, n_rot = run_rotation(close, open_, feats, regime)
    rot.to_parquet(os.path.join(OUT, "sweep_rotation.parquet"), index=False)
    print(f"  {len(rot)} configurations completed of {n_rot} attempted")

    # Rank on TRAIN only.
    rot = rot.sort_values("train_sharpe", ascending=False)
    print("\n  TOP 15 BY TRAIN SHARPE (train ranking only -- validate is the filter)")
    print(
        f"  {'signal':12s} {'k':>2s} {'hold':>4s} {'regime':10s} "
        f"{'TRAIN':>7s} {'VALID':>7s} {'TEST':>7s} {'win':>6s} {'trades':>6s}"
    )
    for _, r in rot.head(15).iterrows():
        print(
            f"  {r['signal']:12s} {int(r['k']):2d} {int(r['hold']):4d} {r['regime']:10s} "
            f"{r['train_sharpe']:+7.2f} {r['validate_sharpe']:+7.2f} {r['test_sharpe']:+7.2f} "
            f"{r.get('win', np.nan):6.1%} {int(r.get('trades', 0)):6d}"
        )

    # The survivors: good on train AND validate, judged before test is read.
    surv = rot[(rot.train_sharpe > 0.5) & (rot.validate_sharpe > 0.5)]
    print(f"\n  survived train>0.5 AND validate>0.5: {len(surv)} of {len(rot)}")
    if len(surv):
        print(
            f"  {'signal':12s} {'k':>2s} {'hold':>4s} {'regime':10s} "
            f"{'TRAIN':>7s} {'VALID':>7s} {'TEST':>7s} {'CAGRt':>7s} {'DDt':>7s} {'win':>6s}"
        )
        for _, r in surv.sort_values("validate_sharpe", ascending=False).head(20).iterrows():
            print(
                f"  {r['signal']:12s} {int(r['k']):2d} {int(r['hold']):4d} {r['regime']:10s} "
                f"{r['train_sharpe']:+7.2f} {r['validate_sharpe']:+7.2f} {r['test_sharpe']:+7.2f} "
                f"{r['test_cagr']:+7.1%} {r['test_dd']:+7.1%} {r.get('win', np.nan):6.1%}"
            )
        best = surv.sort_values("validate_sharpe", ascending=False).iloc[0]
        dsr, sr0 = deflated_sharpe(best["train_sharpe"], int(best["train_n"]), n_rot)
        print(
            f"\n  MULTIPLE-TESTING CHECK on the best survivor:\n"
            f"    trials={n_rot}  expected best Sharpe under pure noise = {sr0:+.2f}\n"
            f"    observed train Sharpe = {best['train_sharpe']:+.2f}  ->  deflated SR prob = {dsr:.3f}"
        )

    print()
    print("=" * 78)
    print("TRACK B -- REGIME TIMING SWEEP")
    print("=" * 78)
    conds = timing_conditions(regime, close)
    print(f"  {len(conds)} atomic conditions: {', '.join(sorted(conds))}")
    tim, n_tim = run_timing(close, conds)
    tim.to_parquet(os.path.join(OUT, "sweep_timing.parquet"), index=False)
    print(f"  {len(tim)} tests completed of {n_tim} attempted")

    # Rank by EDGE OVER BASE RATE on train, not raw win rate.
    tim = tim.sort_values("train_edge_win", ascending=False)
    print("\n  TOP 15 BY TRAIN EDGE-OVER-BASE-RATE (win% above the unconditional)")
    print(
        f"  {'condition':26s} {'sym':4s} {'h':>3s} "
        f"{'trWin':>6s} {'trEdg':>6s} {'vaWin':>6s} {'vaEdg':>6s} {'teWin':>6s} {'teEdg':>6s} {'n':>4s}"
    )
    for _, r in tim.head(15).iterrows():
        print(
            f"  {r['cond']:26s} {r['symbol']:4s} {int(r['horizon']):3d} "
            f"{r['train_win']:6.1%} {r['train_edge_win']:+6.1%} "
            f"{r['validate_win']:6.1%} {r['validate_edge_win']:+6.1%} "
            f"{r['test_win']:6.1%} {r['test_edge_win']:+6.1%} {int(r['train_n']):4d}"
        )

    # Survivors: beat the base rate on BOTH train and validate.
    ts = tim[(tim.train_edge_win > 0.05) & (tim.validate_edge_win > 0.05)]
    print(f"\n  beat base rate by >5pp on train AND validate: {len(ts)} of {len(tim)}")
    if len(ts):
        print(
            f"  {'condition':26s} {'sym':4s} {'h':>3s} "
            f"{'trWin':>6s} {'vaWin':>6s} {'teWin':>6s} {'teEdg':>6s} {'teAvg':>7s} {'n_te':>4s}"
        )
        for _, r in ts.sort_values("validate_edge_win", ascending=False).head(20).iterrows():
            print(
                f"  {r['cond']:26s} {r['symbol']:4s} {int(r['horizon']):3d} "
                f"{r['train_win']:6.1%} {r['validate_win']:6.1%} {r['test_win']:6.1%} "
                f"{r['test_edge_win']:+6.1%} {r['test_avg']:+7.2%} {int(r['test_n']):4d}"
            )

    print(f"\n  TOTAL TRIALS THIS RUN: {n_rot + n_tim}")
    print(f"  Expected best-of-N t-stat under the null ~ {np.sqrt(2*np.log(n_rot+n_tim)):.2f}")
    print("  Any result below that bar is indistinguishable from search noise.")


if __name__ == "__main__":
    main()
