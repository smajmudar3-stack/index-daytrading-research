"""regime_reversal_test.py — the one thing in the accuracy sweep that cleared 52%: buying
the month's biggest losers when the TAPE is bearish. Is it a trade?

signal_accuracy.py, split by regime, showed short-term reversal (last-month return, Bollinger
position, RSI, the down-day streak) with 52-54% top-decile hit rates and t 2-2.7 at four
weeks when SPY's 12-month return was negative or VIX sat in its top 30% — and nothing in
bull / low-VIX tapes. That table was 16-18 dates. This file asks the question properly:

  * FOUR regime definitions, all known at the time: SPY 12-month return < 0; SPY below its
    200-day average; VIX above 25; VIX in the top 30% of its trailing year. Each is a
    different amount of the sample, and a real effect should show in all of them.
  * THREE reversal signals (last-month return, last-week return, Bollinger position) and
    their average, bought in the bottom decile, held 5 / 10 / 21 sessions, non-overlapping.
  * Long-only (what a small account does) AND the bottom-minus-top spread (what the effect
    is), hit rate, payoff, net of 15 bp a side, the three splits, and the number of
    regime-dates the result rests on. Regime B (2022-23) is the only bear market in the
    sample, so "all splits positive" is impossible here; the honest bar is: positive in every
    regime definition, and at least two horizons, with the crash weeks and the rest shown
    separately.
  * The "boom" variant: names down >10% in the week, in a bear tape.
  * The ordinary-regime control: the same signals in the OTHER state, to show the switch.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from signal_accuracy import spy_close  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
COST = 0.0015


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def regimes(w):
    spy = spy_close()
    ma200 = spy.rolling(200).mean()
    w["spy_below_200"] = w.date.map((spy < ma200).astype(float))
    return {
        "SPY 12m < 0": w.spy_12m < 0,
        "SPY < 200-day MA": w.spy_below_200 > 0,
        "VIX > 25": w.vix > 25,
        "VIX top 30% of year": w.vix_rank > 0.7,
    }


def evaluate(d, score, h, label):
    y = f"ex{h}"
    d = d.assign(score=score).dropna(subset=["score", y])
    d = d[d.groupby("date").score.transform("size") >= 100]
    if d.date.nunique() < 8:
        print(f"  {label:58s} too few dates ({d.date.nunique()})")
        return None
    q = d.groupby("date").score.transform(lambda v: pd.qcut(v.rank(method="first"), 10, labels=False, duplicates="drop"))
    bot, top = d[q == 0], d[q == 9]                      # bottom decile of the score = biggest losers = the BUY
    s = bot.groupby("date")[y].mean()
    sp = (s - top.groupby("date")[y].mean()).dropna()
    win, loss = bot[bot[y] > 0][y].mean(), bot[bot[y] <= 0][y].mean()
    hold_w = max(1, h // 5)
    net = s.mean() - 2 * COST                                 # full turnover each hold, worst case
    splits = {k: f"{s[(s.index >= a) & (s.index <= b)].mean()*100:+.2f}({len(s[(s.index >= a) & (s.index <= b)])})" for k, (a, b) in SPLITS.items()}
    print(f"  {label:58s} dates {len(s):3d} | LONG losers: {s.mean()*100:+.2f}%/hold (t {_t(s):+.1f}) hit {(bot[y]>0).mean():.3f} "
          f"payoff {win/-loss:.2f} date-hit {(s>0).mean():.2f} net {net*52/hold_w*100:+.1f}%/yr | losers-minus-winners {sp.mean()*100:+.2f}% (t {_t(sp):+.1f}) | {splits}")
    return s


def main():
    pd.set_option("display.width", 250)
    w = pd.read_parquet(os.path.join(PANEL, "signal_panel.parquet"))
    regs = regimes(w)
    w["rev_avg"] = (w.groupby("date").rev1m.rank(pct=True) + w.groupby("date").rev1w.rank(pct=True)
                    + w.groupby("date").bb_pos.rank(pct=True)) / 3
    signals = {"last-month return": "rev1m", "last-week return": "rev1w", "Bollinger position": "bb_pos", "average of the three": "rev_avg"}
    for h in (5, 10, 21):
        step = max(1, h // 5)
        dates = np.sort(w.date.unique())[::step]
        d0 = w[w.date.isin(dates)]
        print(f"\n{'='*160}\nHOLD {h} SESSIONS ({len(dates)} non-overlapping dates). Buy the bottom decile of the signal (the biggest losers).")
        for rname, mask in regs.items():
            share = mask.reindex(d0.index).fillna(False)
            print(f"\n REGIME {rname}: {d0[share].date.nunique()} of {d0.date.nunique()} dates")
            for sname, col in signals.items():
                evaluate(d0[share], d0[share][col], h, f"in regime | {sname}")
            evaluate(d0[~share], d0[~share]["rev_avg"], h, "OUT of regime | average of the three (control)")
        # the boom variant
        print("\n CRASH NAMES (down >10% in the week) bought in each regime:")
        for rname, mask in regs.items():
            share = mask.reindex(d0.index).fillna(False)
            c = d0[share & (d0.rev1w < -0.10)]
            y = f"ex{h}"
            s = c.groupby("date")[y].agg(["mean", "size"])
            s = s[s["size"] >= 10]["mean"]
            if len(s) >= 8:
                win, loss = c[c[y] > 0][y].mean(), c[c[y] <= 0][y].mean()
                print(f"  {rname:24s} dates {len(s):3d} names/date {c.groupby('date').size().median():.0f} | {s.mean()*100:+.2f}%/hold (t {_t(s):+.1f}) "
                      f"hit {(c[y]>0).mean():.3f} payoff {win/-loss:.2f} date-hit {(s>0).mean():.2f} | "
                      f"{ {k: f'{s[(s.index >= a) & (s.index <= b)].mean()*100:+.2f}' for k, (a, b) in SPLITS.items()} }")
        c = d0[(~regs["SPY 12m < 0"].reindex(d0.index).fillna(False)) & (d0.rev1w < -0.10)]
        s = c.groupby(f"ex{h}").size() if False else c.groupby("date")[f"ex{h}"].mean()
        print(f"  {'control: bull tape':24s} dates {len(s):3d} | {s.mean()*100:+.2f}%/hold (t {_t(s):+.1f}) hit {(c[f'ex{h}']>0).mean():.3f}")
    # regime weeks, listed, so the reader can see which months carry the result
    print("\nBEAR-TAPE WEEKS (SPY 12m < 0) by quarter:")
    b = w[w.spy_12m < 0].drop_duplicates("date")
    print(b.groupby(b.date.dt.to_period("Q")).size().to_string())


if __name__ == "__main__":
    main()
