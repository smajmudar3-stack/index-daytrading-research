"""Exhaustive gate-combination sweep: every 1..6-way combo, every structure.

The honest way to answer "have you tried every combination" is to try every
combination -- and then hold the winner to a bar that accounts for how many
were tried. Searching harder does not find more edge; it finds more noise that
LOOKS like edge, and the only defence is to raise the bar in proportion.

Two guards make this a real test rather than a fishing trip:

  1. MULTIPLE-TESTING BAR. With N trials the expected best |t| under the pure
     null is ~sqrt(2*ln(N)). At 50,000 combos that is ~4.65 -- so a t of 4
     found by searching 50,000 cells is WORSE than a t of 3 found by testing
     one pre-specified hypothesis. The bar is printed with every result.

  2. THREE-PERIOD CONSISTENCY. A cell must be positive in 2008-2013 AND
     2014-2019 AND 2020-2025. Any single-period winner is discarded no matter
     how large. This is what killed every previous candidate, and it is the
     cheapest defence against a cell that is one good year wearing a disguise.

Sample-size floors scale with combo depth because deep combos slice the data
thin: a 6-way gate that fires 40 times is not evidence of anything.
"""
import itertools
import os
import sys
import warnings

import numpy as np
import pandas as pd

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from daily_engine import context, gates  # noqa: E402

TRADES = paths.data("swing", "structure_trades.parquet")
OUT = paths.data("swing", "combo_sweep.parquet")

SPLITS = {"2008-2013": ("2008-01-01", "2013-12-31"),
          "2014-2019": ("2014-01-01", "2019-12-31"),
          "2020-2025": ("2020-01-01", "2025-12-31")}

MAX_DEPTH = 6
# Minimum trades in a cell, by combo depth. Deeper combos slice thinner, but a
# floor that scales down too fast just admits noise with a small denominator.
MIN_N = {1: 250, 2: 200, 3: 150, 4: 120, 5: 100, 6: 80}
MIN_N_SPLIT = 20          # per-period minimum for the consistency check


def main():
    d = pd.read_parquet(paths.require_data(TRADES)).drop_duplicates(
        subset=["date", "structure", "dte", "hold_frac"])
    c = context()
    G = gates(c)
    names = sorted(G)

    print("=" * 96)
    print("EXHAUSTIVE COMBINATION SWEEP")
    print("=" * 96)
    print(f"  {len(names)} gates: {', '.join(names)}")

    combos = []
    for k in range(1, MAX_DEPTH + 1):
        cs = list(itertools.combinations(names, k))
        combos.extend(cs)
        print(f"  depth {k}: {len(cs):>6,} combinations")
    print(f"  TOTAL: {len(combos):,} gate combinations")

    structures = sorted(d.structure.unique())
    print(f"  x {len(structures)} structures = {len(combos)*len(structures):,} cells to test\n")

    # Pre-resolve each gate to a date-indexed boolean once.
    gmask = {n: G[n].reindex(c.index).fillna(False) for n in names}
    dates = d.date.values

    # Map every trade to its gate vector once, then combine with AND. Doing the
    # reindex inside the loop would be ~50M pandas lookups.
    gvec = {n: gmask[n].reindex(pd.DatetimeIndex(dates)).fillna(False).values
            for n in names}

    by_struct = {s: g for s, g in d.groupby("structure")}
    idx_of = {s: d.index.get_indexer(g.index) for s, g in by_struct.items()}

    rows = []
    done = 0
    for combo in combos:
        m = gvec[combo[0]].copy()
        for extra in combo[1:]:
            m &= gvec[extra]
        if m.sum() < MIN_N[len(combo)]:
            continue
        gate_name = "+".join(combo)

        for s in structures:
            ii = idx_of[s]
            sel = m[ii]
            n = int(sel.sum())
            if n < MIN_N[len(combo)]:
                continue
            g = by_struct[s]
            r = g.ret.values[sel]
            sd = r.std()
            if sd == 0:
                continue
            t = r.mean() / (sd / np.sqrt(n))
            if t <= 0:                      # only positive cells are candidates
                continue

            # Three-period consistency, computed only for cells that pass the
            # pooled screen -- the expensive check runs on ~0.1% of cells.
            gd = g.date.values[sel]
            oos, ok = [], True
            for a, b in SPLITS.values():
                pm = (gd >= np.datetime64(a)) & (gd <= np.datetime64(b))
                if pm.sum() < MIN_N_SPLIT:
                    ok = False
                    break
                oos.append(float(r[pm].mean()))
            rows.append({
                "structure": s, "gate": gate_name, "depth": len(combo),
                "n": n, "win": float((r > 0).mean()), "avg": float(r.mean()),
                "t": float(t),
                "all_periods": bool(ok and all(v > 0 for v in oos)),
                "p1": oos[0] if ok else np.nan,
                "p2": oos[1] if ok else np.nan,
                "p3": oos[2] if ok else np.nan,
            })
        done += 1
        if done % 2000 == 0:
            print(f"    ...{done:,} gates screened, {len(rows):,} positive cells",
                  flush=True)

    res = pd.DataFrame(rows)
    if res.empty:
        print("\n  NO positive cells at any depth.")
        return
    res.to_parquet(OUT, index=False)

    n_trials = len(combos) * len(structures)
    bar = np.sqrt(2 * np.log(max(n_trials, 2)))

    print(f"\n  tested {n_trials:,} cells")
    print(f"  positive-mean cells: {len(res):,}")
    print(f"  MULTIPLE-TESTING BAR: expected best |t| under the pure null "
          f"= sqrt(2*ln({n_trials:,})) = {bar:.2f}")

    print("\n" + "=" * 96)
    print("TOP 20 BY t-STAT (pooled) — before any consistency filter")
    print("=" * 96)
    print(f"  {'structure':22s} {'gate':38s} {'d':>2s} {'n':>5s} "
          f"{'win':>6s} {'avg':>8s} {'t':>6s}")
    for _, x in res.sort_values("t", ascending=False).head(20).iterrows():
        print(f"  {x['structure']:22s} {x['gate'][:38]:38s} {int(x['depth']):2d} "
              f"{int(x['n']):5d} {x['win']:6.1%} {x['avg']:+8.2%} {x['t']:+6.2f}")

    surv = res[res.all_periods & (res.t > bar)]
    print("\n" + "=" * 96)
    print(f"SURVIVORS — positive in ALL THREE periods AND t > {bar:.2f}")
    print("=" * 96)
    if surv.empty:
        near = res[res.all_periods]
        print(f"  NONE of {n_trials:,} cells clear both bars.")
        print(f"  ({len(near):,} are positive in all three periods, but none reach "
              f"t > {bar:.2f}.)")
        if not near.empty:
            print("\n  Best three-period-consistent cells (all still BELOW the bar):")
            print(f"  {'structure':22s} {'gate':30s} {'n':>5s} {'t':>6s} "
                  f"{'p1':>8s} {'p2':>8s} {'p3':>8s}")
            for _, x in near.sort_values("t", ascending=False).head(10).iterrows():
                print(f"  {x['structure']:22s} {x['gate'][:30]:30s} {int(x['n']):5d} "
                      f"{x['t']:+6.2f} {x['p1']:+8.2%} {x['p2']:+8.2%} {x['p3']:+8.2%}")
    else:
        print(f"  {'structure':22s} {'gate':30s} {'d':>2s} {'n':>5s} {'win':>6s} "
              f"{'avg':>8s} {'t':>6s}")
        for _, x in surv.sort_values("t", ascending=False).head(25).iterrows():
            print(f"  {x['structure']:22s} {x['gate'][:30]:30s} {int(x['depth']):2d} "
                  f"{int(x['n']):5d} {x['win']:6.1%} {x['avg']:+8.2%} {x['t']:+6.2f}")

    # Does searching deeper help, or just find more noise?
    print("\n" + "=" * 96)
    print("DOES DEEPER SEARCHING HELP?")
    print("=" * 96)
    print(f"  {'depth':>5s} {'cells':>9s} {'positive':>9s} {'best t':>8s} "
          f"{'3-period survivors':>19s}")
    for k in range(1, MAX_DEPTH + 1):
        sub = res[res.depth == k]
        if sub.empty:
            continue
        print(f"  {k:5d} {len(sub):9,d} {(sub.avg>0).sum():9,d} "
              f"{sub.t.max():8.2f} {int((sub.all_periods & (sub.t>bar)).sum()):19d}")


if __name__ == "__main__":
    main()
