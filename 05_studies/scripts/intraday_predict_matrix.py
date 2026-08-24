"""Does any half-hour of the day predict any other? The full matrix.

This is the honest version of the "market intraday momentum" test (Gao, Han, Li
& Zhou 2018), whose headline claim is that the first half-hour return predicts
the last half-hour return. Rather than testing that one pair and declaring
victory, this tests EVERY ordered pair of half-hour buckets -- because testing
one pair and finding t=2.5 means nothing if you would have accepted any of 78
pairs.

Three guards, all of which have burned this repo before:

  1. MULTIPLE TESTING. With N ordered pairs the expected best |t| under the null
     is ~sqrt(2*ln(N)). That threshold is printed and enforced, not assumed away.

  2. NO OVERLAP. Predictor and outcome are disjoint half-hour windows on the
     same day. A predictor that shares even one minute with its outcome
     manufactures t-stats.

  3. OUT OF SAMPLE. Every pair is fit on the first 60% of days and reported on
     the remaining 40%. An effect that is real degrades; an effect that is
     fitted reverses.

Data: SPXW chain snapshots, 1,919 trading days, 2016-09 to 2024-05. The
underlying price is taken from active_underlying_price, deduplicated to one
value per (date, time).
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")


def load_path():
    """One underlying price per (date, time) -> a half-hourly price path."""
    df = pd.read_parquet(SPXW, columns=["quote_date", "quote_time",
                                        "active_underlying_price"])
    df = df.dropna(subset=["active_underlying_price"])
    # The chain has many rows per timestamp; the underlying is the same on each.
    px = (df.groupby(["quote_date", "quote_time"])["active_underlying_price"]
            .median().unstack())
    px = px.reindex(sorted(px.columns), axis=1)
    px.index = pd.to_datetime(px.index)
    return px.sort_index()


def main():
    px = load_path()
    times = list(px.columns)
    print("=" * 92)
    print("INTRADAY PREDICTABILITY MATRIX -- SPXW underlying")
    print("=" * 92)
    print(f"  {len(px):,} trading days   {px.index.min().date()} -> {px.index.max().date()}")
    print(f"  {len(times)} snapshots/day: {', '.join(str(t) for t in times)}")

    # Half-hour log returns between consecutive snapshots.
    lr = np.log(px).diff(axis=1).iloc[:, 1:]
    lr = lr.dropna(how="any")
    buckets = list(lr.columns)
    print(f"  {len(lr):,} complete days, {len(buckets)} half-hour buckets\n")

    # Coverage: how much of the day's move happens in each bucket.
    print("  bucket volatility (annualized-ish, bp per half hour):")
    for b in buckets:
        print(f"    ->{b}   sd {lr[b].std()*1e4:7.1f} bp   "
              f"mean {lr[b].mean()*1e4:+7.2f} bp")

    split = int(len(lr) * 0.60)
    tr, te = lr.iloc[:split], lr.iloc[split:]
    print(f"\n  train {len(tr):,} days ({tr.index.min().date()}->{tr.index.max().date()})"
          f"   test {len(te):,} days ({te.index.min().date()}->{te.index.max().date()})")

    # Every ordered pair where the predictor strictly precedes the outcome.
    pairs = [(i, j) for i in range(len(buckets)) for j in range(len(buckets)) if j > i]
    n_tests = len(pairs)
    thresh = np.sqrt(2 * np.log(n_tests))
    print(f"\n  {n_tests} non-overlapping ordered pairs tested")
    print(f"  multiple-testing threshold: expected best |t| under null = "
          f"sqrt(2*ln({n_tests})) = {thresh:.2f}")
    print("  -> a pair must beat this in TRAIN and hold its sign in TEST.\n")

    rows = []
    for i, j in pairs:
        a, b = buckets[i], buckets[j]
        x, y = tr[a].values, tr[b].values
        if len(x) < 100:
            continue
        sl, ic, r, p, se = stats.linregress(x, y)
        t = sl / se if se > 0 else 0.0
        # Out of sample: same slope sign?
        xo, yo = te[a].values, te[b].values
        slo, _, ro, _, seo = stats.linregress(xo, yo)
        to = slo / seo if seo > 0 else 0.0
        rows.append(dict(pred=str(a), out=str(b), t_train=t, r_train=r,
                         t_test=to, r_test=ro,
                         holds=(np.sign(sl) == np.sign(slo)) and abs(to) > 1.96))

    res = pd.DataFrame(rows).sort_values("t_train", key=abs, ascending=False)

    print("=" * 92)
    print("  TOP 12 BY IN-SAMPLE |t|")
    print("=" * 92)
    print(f"  {'predictor':>10s} -> {'outcome':<10s} {'t_train':>8s} {'r_train':>8s} "
          f"{'t_test':>8s} {'r_test':>8s}  {'verdict'}")
    for _, r in res.head(12).iterrows():
        beat = abs(r.t_train) > thresh
        v = ("SURVIVES" if (beat and r.holds) else
             "fails OOS" if beat else "below noise threshold")
        print(f"  {r.pred:>10s} -> {r.out:<10s} {r.t_train:8.2f} {r.r_train:8.3f} "
              f"{r.t_test:8.2f} {r.r_test:8.3f}  {v}")

    surv = res[(res.t_train.abs() > thresh) & res.holds]
    print("\n" + "=" * 92)
    if len(surv) == 0:
        print(f"  NOTHING SURVIVES. {n_tests} pairs tested; the largest |t| was "
              f"{res.t_train.abs().max():.2f}")
        print(f"  against a noise threshold of {thresh:.2f}.")
        best = res.iloc[0]
        print(f"  Best pair {best.pred}->{best.out}: r={best.r_train:.3f} in train, "
              f"{best.r_test:.3f} in test.")
    else:
        print(f"  {len(surv)} pair(s) beat the noise threshold AND held out of sample:")
        for _, r in surv.iterrows():
            print(f"    {r.pred} -> {r.out}: t {r.t_train:.2f} -> {r.t_test:.2f}, "
                  f"r {r.r_train:.3f} -> {r.r_test:.3f}")
    print("=" * 92)

    # The specific published claim, called out by name regardless of rank.
    first, last = buckets[0], buckets[-1]
    row = res[(res.pred == str(first)) & (res.out == str(last))]
    if len(row):
        r = row.iloc[0]
        print(f"\n  GAO ET AL. CLAIM ({first} bucket -> {last} bucket):")
        print(f"    train t={r.t_train:.2f} r={r.r_train:.3f} | "
              f"test t={r.t_test:.2f} r={r.r_test:.3f}")
        print(f"    {'holds' if r.holds and abs(r.t_train) > thresh else 'DOES NOT hold at this threshold'}")

    res.to_csv(os.path.join(ROOT, "data", "intraday_matrix.csv"), index=False)
    print(f"\n  full matrix -> data/intraday_matrix.csv")


if __name__ == "__main__":
    main()
