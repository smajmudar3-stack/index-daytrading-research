"""hunt_horizons.py — every holding period from 15 min to 2 hours, both regime legs, TRAIN vs TEST.

The owner asked specifically that the whole 15-minute-to-2-hour band be swept rather than a few round
numbers. This prints TRAIN and TEST side by side for each cell so that the train-to-test degradation
is visible per configuration instead of being hidden behind a single chosen winner.

Read the TEST column only. The TRAIN column is shown to expose overfitting, not to be traded.
"""
import numpy as np
import pandas as pd

import hunt_features as HF
import hunt_strategy as HS

HOLDS = (15, 20, 25, 30, 40, 45, 60, 75, 90, 105, 120)


def run(sym="QQQ"):
    df = HF.load(sym)
    df = HF.add_features(df)
    df = HF.add_daily(df)
    dates = sorted(df.date.unique())
    split = dates[len(dates) // 2]
    tr_df, te_df = df[df.date < split], df[df.date >= split]
    print(f"\n{'='*104}\n{sym} — holding-period sweep, TP 100% / stop -50% / rvol>1.2\n{'='*104}")
    print(f"TRAIN {dates[0].date()}->{split.date()}   TEST {split.date()}->{dates[-1].date()}")

    legs = [("PIN  gz>0.5  FADE", dict(side="fade", gz_min=0.5, min_rvol=1.2)),
            ("TREND -0.5..0.5 FOLLOW", dict(side="follow", gz_min=-0.5, gz_max=0.5, min_rvol=1.2))]
    for label, cfg in legs:
        print(f"\n{label}")
        print(f"  {'hold':>6}{'TRAIN n':>9}{'win%':>7}{'avg':>8}   {'TEST n':>8}{'win%':>7}{'avg':>8}"
              f"{'mo% @10%':>10}{'maxDD':>8}")
        for h in HOLDS:
            a = HS.simulate(tr_df, cfg, 1.00, -0.50, h)
            b = HS.simulate(te_df, cfg, 1.00, -0.50, h)
            sa, sb = HS.summarize(a), HS.summarize(b, rf=0.10)
            if sa is None or sb is None:
                continue
            print(f"  {h:>5}m{sa['n']:>9}{sa['win']*100:>6.0f}%{sa['avg']*100:>+7.1f}%   "
                  f"{sb['n']:>8}{sb['win']*100:>6.0f}%{sb['avg']*100:>+7.1f}%"
                  f"{sb['mo_mean']*100:>+9.1f}%{-sb['mdd']:>7.0f}%")


if __name__ == "__main__":
    import sys
    for s in (sys.argv[1:] or ["QQQ", "SPY"]):
        run(s)
