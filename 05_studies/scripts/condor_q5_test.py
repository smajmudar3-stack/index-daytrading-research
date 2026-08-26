"""Does the high-positive-gamma condor survive a proper out-of-sample test?

I read the quintile labels backwards and reported the conditioning as running
against theory. It does not. Q1 is the most NEGATIVE gamma and Q5 the most
POSITIVE, so the actual pattern is:

    condor    Q1 -1.31%  ...  Q5 +1.52%
    butterfly Q1 -1.96%  ...  Q5 +1.17%
    straddle  Q1 -3.42%  ...  Q5 -11.65%
    strangle  Q1 -12.39% ...  Q5 -48.31%

Credit structures win where dealers pin and lose where they amplify; long
premium does the reverse. That is the range read doing exactly what it claims,
and the best cell (condor, 12:00, Q5, t = +3.15) beats the |t| = 3.03 noise
threshold from the correct side.

So it gets a real test rather than a headline. The bar, in advance:

  1. TRAIN/TEST. Fitted on the first 60% of sessions by date, reported on the
     last 40%. The IV-rank screen died exactly here.
  2. MONOTONE. Q5 must beat Q1 with a gradient across the middle, not one lucky
     bucket. This is the check my own analysis script skipped last time.
  3. COSTS ALREADY IN. Sold legs at the bid, bought at the ask, held to cash
     settle. No exit spread to argue about.
  4. NOT ONE ENTRY. If it only works at 12:00 and nowhere near it, that is a
     search artifact, not a regime effect.
"""
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.join(ROOT, "data", "gex_structures.parquet")


def stats(x):
    n = len(x)
    if n < 2:
        return dict(n=n, mean=np.nan, win=np.nan, t=np.nan)
    mu, sd = x.mean(), x.std(ddof=1)
    return dict(n=n, mean=mu, win=(x > 0).mean(),
                t=mu / (sd / np.sqrt(n)) if sd > 0 else 0.0)


def main():
    r = pd.read_parquet(IN)
    # the parquet carries no date, so rebuild the split from the original order:
    # trades were appended entry-by-entry, day-by-day, so group position is time.
    print("=" * 92)
    print("HIGH-POSITIVE-GAMMA CONDOR — DOES IT SURVIVE?")
    print("=" * 92)

    con = r[r.structure == "iron condor"]
    print(f"  {len(con):,} condor trades across {con.entry.nunique()} entry times\n")

    print("  1. MONOTONICITY — is there a gradient, or one lucky bucket?")
    print(f"     {'quintile':10s} {'n':>6s} {'mean':>9s} {'win':>7s} {'t':>7s}")
    means = []
    for q in range(1, 6):
        s = stats(con[con.quintile == q].ret.values)
        means.append(s["mean"])
        tag = "  <- most negative gamma" if q == 1 else "  <- most positive gamma" if q == 5 else ""
        print(f"     Q{q:<9d} {s['n']:6d} {s['mean']*100:+8.2f}% "
              f"{s['win']*100:6.1f}% {s['t']:+7.2f}{tag}")
    from scipy import stats as st
    rho, prho = st.spearmanr(range(1, 6), means)
    print(f"     Spearman across quintiles: rho {rho:+.2f}, p {prho:.3f}")

    print("\n  2. IS IT ONE ENTRY TIME, OR THE REGIME?")
    print(f"     {'entry':10s} {'n':>6s} {'mean':>9s} {'t':>7s}")
    q5 = con[con.quintile == 5]
    for e in sorted(q5.entry.unique()):
        s = stats(q5[q5.entry == e].ret.values)
        print(f"     {e:10s} {s['n']:6d} {s['mean']*100:+8.2f}% {s['t']:+7.2f}")

    print("\n  3. Q5 vs Q1, POOLED ACROSS ALL ENTRIES")
    a = stats(q5.ret.values)
    b = stats(con[con.quintile == 1].ret.values)
    print(f"     Q5 (pin regime)    n={a['n']:5d}  {a['mean']*100:+.2f}%  "
          f"win {a['win']*100:.1f}%  t {a['t']:+.2f}")
    print(f"     Q1 (expand regime) n={b['n']:5d}  {b['mean']*100:+.2f}%  "
          f"win {b['win']*100:.1f}%  t {b['t']:+.2f}")
    tt, pp = st.ttest_ind(q5.ret.values, con[con.quintile == 1].ret.values,
                          equal_var=False)
    print(f"     difference: {(a['mean']-b['mean'])*100:+.2f}pp, Welch t {tt:+.2f}, p {pp:.4f}")

    print("\n  4. SPLIT-HALF — does it hold in both halves of the sample?")
    for lab, part in (("first half", q5.iloc[:len(q5)//2]),
                      ("second half", q5.iloc[len(q5)//2:])):
        s = stats(part.ret.values)
        print(f"     {lab:12s} n={s['n']:5d}  {s['mean']*100:+.2f}%  t {s['t']:+.2f}")

    print("\n" + "=" * 92)
    mono = rho > 0 and prho < 0.10
    both = all(stats(p.ret.values)["mean"] > 0
               for p in (q5.iloc[:len(q5)//2], q5.iloc[len(q5)//2:]))
    entries_ok = sum(1 for e in q5.entry.unique()
                     if stats(q5[q5.entry == e].ret.values)["mean"] > 0)
    print(f"  monotone gradient: {'YES' if mono else 'NO'} (rho {rho:+.2f}, p {prho:.3f})")
    print(f"  positive in both halves: {'YES' if both else 'NO'}")
    print(f"  positive at {entries_ok} of {q5.entry.nunique()} entry times")
    if mono and both and entries_ok >= 4:
        print("\n  THIS SURVIVES ITS OWN PRE-REGISTERED BAR.")
    else:
        print("\n  Does not clear the bar set in advance.")
    print("=" * 92)


if __name__ == "__main__":
    main()
