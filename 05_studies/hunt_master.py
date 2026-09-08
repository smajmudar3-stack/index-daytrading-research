"""hunt_master.py — the definitive search. Every feature, every 1-3 way combination, 3-way split.

By this point the search space has been explored heavily enough that a single train/test split is no
longer trustworthy: with thousands of combinations, something will clear any two-way bar by luck. So:

    TRAIN    (first 40%)  - build thresholds, screen conditions
    VALIDATE (next  30%)  - select the winner among survivors
    TEST     (last  30%)  - touched EXACTLY ONCE, on the single selected rule

Anything that does not hold across all three is discarded. The TEST number is the only one to believe,
and it is reported alongside how many candidates were searched so the multiple-testing burden is
visible rather than buried.
"""
import itertools
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats as st

warnings.filterwarnings("ignore")

import hunt_indicators as HI
import hunt_conditional as HC

MIN_N = 30          # per-split sample floor
WIN_BAR = 0.55      # a candidate must beat this on TRAIN and VALIDATE to reach TEST


def splits(t):
    d = np.sort(t.dt.unique())
    a, b = d[int(len(d) * 0.40)], d[int(len(d) * 0.70)]
    return t[t.dt < a], t[(t.dt >= a) & (t.dt < b)], t[t.dt >= b]


def conditions(tr, feats):
    """Threshold conditions built on TRAIN only."""
    out = {}
    for f in feats:
        s = tr[f].replace([np.inf, -np.inf], np.nan)
        if s.notna().sum() < MIN_N * 2:
            continue
        try:
            q33, q50, q67 = np.nanpercentile(s, [33, 50, 67])
        except Exception:
            continue
        for nm, side, thr in ((">q67", "hi", q67), ("<q33", "lo", q33),
                              (">med", "hi", q50), ("<med", "lo", q50)):
            if np.isfinite(thr):
                out[f"{f}{nm}"] = (f, side, thr)
    return out


def apply_(d, spec):
    f, side, thr = spec
    s = d[f]
    return (s >= thr).fillna(False) if side == "hi" else (s <= thr).fillna(False)


def main():
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    hold = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    df = HI.build(sym)
    t = HC.fade_trades(df, hold=hold)
    # tag with the indicator columns too
    feats = [f for f in HI.ALL_FEATS if f in df.columns]
    ent_map = {}
    for date, g in df.groupby("date"):
        live = g[(g.mins >= 600) & (g.mins <= 780)]
        for ts, r in live.iterrows():
            if np.isfinite(r.rvol) and r.rvol >= 1.2:
                ent_map[date] = r
                break
    for f in feats:
        t[f] = t.date.map(lambda d: float(ent_map[d][f]) if d in ent_map and np.isfinite(ent_map[d].get(f, np.nan)) else np.nan)
    t["dt"] = pd.to_datetime(t.date)
    tr, va, te = splits(t)
    print(f"{sym} FADE hold={hold}m | trades {len(t)}  "
          f"TRAIN {len(tr)} ({tr.win.mean()*100:.1f}%)  "
          f"VAL {len(va)} ({va.win.mean()*100:.1f}%)  TEST {len(te)} ({te.win.mean()*100:.1f}%)")

    C = conditions(tr, feats)
    print(f"conditions built: {len(C)} from {len(feats)} features")

    # stage 1: univariate survivors on TRAIN and VALIDATE
    surv = []
    for nm, spec in C.items():
        a, b = tr[apply_(tr, spec)], va[apply_(va, spec)]
        if len(a) < MIN_N or len(b) < MIN_N:
            continue
        if a.win.mean() >= 0.52 and b.win.mean() >= 0.52:
            surv.append(nm)
    print(f"stage 1 — conditions clearing 52% on BOTH train and validate: {len(surv)}")

    # stage 2: all 1-3 combinations of survivors
    cands = []
    tested = 0
    for k in (1, 2, 3):
        for combo in itertools.combinations(surv, k):
            if len({C[c][0] for c in combo}) != len(combo):
                continue
            tested += 1
            ma = pd.Series(True, index=tr.index); mb = pd.Series(True, index=va.index)
            for c in combo:
                ma &= apply_(tr, C[c]); mb &= apply_(va, C[c])
            a, b = tr[ma], va[mb]
            if len(a) < MIN_N or len(b) < MIN_N:
                continue
            if a.win.mean() >= WIN_BAR and b.win.mean() >= WIN_BAR:
                cands.append((combo, len(a), a.win.mean(), len(b), b.win.mean(),
                              (a.win.mean() + b.win.mean()) / 2))
    print(f"stage 2 — {tested:,} combinations tested, {len(cands)} clear {WIN_BAR*100:.0f}% on both")

    if not cands:
        print("\nNo combination clears the bar on both TRAIN and VALIDATE.")
        return
    cands.sort(key=lambda r: -r[5])
    print("\ntop 12 by mean(train,val) win rate:")
    print(f"  {'conditions':56}{'TRn':>5}{'TRw':>7}{'VAn':>5}{'VAw':>7}")
    for combo, na, wa, nb, wb, _ in cands[:12]:
        print(f"  {' + '.join(combo):56}{na:>5}{wa*100:>6.1f}%{nb:>5}{wb*100:>6.1f}%")

    # stage 3: ONE evaluation on TEST
    best = cands[0][0]
    mt = pd.Series(True, index=te.index)
    for c in best:
        mt &= apply_(te, C[c])
    hold_out = te[mt]
    print(f"\n{'='*78}\nSELECTED: {' + '.join(best)}")
    print(f"{'='*78}")
    if len(hold_out) < 12:
        print(f"TEST n={len(hold_out)} — too small to conclude anything.")
        return
    r = hold_out.ret.values
    tt, pp = st.ttest_1samp(r, 0)
    print(f"  TEST n={len(hold_out)}  win {hold_out.win.mean()*100:.1f}%  "
          f"avg {r.mean()*100:+.2f}%  t={tt:+.2f}  p={pp:.4f}")
    print(f"  (searched {tested:,} combinations — Bonferroni bar for p is {0.05/max(tested,1):.2e})")

    full = t.copy()
    mf = pd.Series(True, index=full.index)
    for c in best:
        mf &= apply_(full, C[c])
    fl = full[mf]
    fl = fl.copy(); fl["mo"] = pd.to_datetime(fl.date).dt.to_period("M")
    print(f"\n  FULL SAMPLE n={len(fl)} win {fl.win.mean()*100:.1f}% avg {fl.ret.mean()*100:+.2f}%")
    for rf in (0.10, 0.25):
        mo = fl.groupby("mo")["ret"].apply(lambda x: np.prod(1 + x * rf) - 1).values
        if len(mo) < 3:
            continue
        eq = np.cumprod(1 + mo); pk = np.maximum.accumulate(eq)
        print(f"  {rf*100:3.0f}% risk: monthly mean {mo.mean()*100:+.1f}% median {np.median(mo)*100:+.1f}% | "
              f"{(mo>0).mean()*100:.0f}% green | maxDD -{((pk-eq)/pk).max()*100:.0f}% | "
              f"$2k->${2000*eq[-1]:,.0f} over {len(mo)} mo")


if __name__ == "__main__":
    main()
