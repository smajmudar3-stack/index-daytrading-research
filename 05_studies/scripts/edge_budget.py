"""The edge budget: what directional hit rate does a once-a-day intraday trade actually need,
in each instrument, to be worth trading? Grounded in the real move distribution measured from
data/spxw/data_opt.parquet (1,919 sessions of real SPX spot, 2016-09..2024-05).

This is the number the whole research programme should be measured against.
"""
import numpy as np
import pandas as pd

from idt import paths


HOR = {"30 min": ("11:00:00", "11:30:00"),
       "60 min": ("11:00:00", "12:00:00"),
       "90 min": ("11:00:00", "12:30:00"),
       "120 min": ("10:00:00", "12:00:00")}

# round-trip cost as a fraction of notional
COSTS = {
    "ES  (1 tick + comm)": 0.000050,
    "MES (1 tick + comm)": 0.000073,
    "SPY shares (1c + fee)": 0.000030,
    "0DTE ATM opt: spread only": None,     # filled from the panel
    "0DTE ATM opt: spread+theta (empirical)": None,
}

# The verdict text, hoisted to a constant so the work below can sit under a main
# guard: indenting a triple-quoted string would silently reindent its contents.
VERDICT = """
0DTE OPTIONS -- measured directly from real SPXW quotes by scripts/option_drag.py
(buy at the ask 11:00, sell at the bid 12:30, fixed strike, 1,395 sessions):

  long ATM call : right +38.4% / wrong -53.5%  ->  break-even hit rate 58.2%
  long ATM put  : right +45.9% / wrong -53.4%  ->  break-even hit rate 53.8%

The quoted spread is only ~3.8% of mid. The hurdle is theta plus the collapse of delta
when you are wrong -- not the spread. This is the same mechanism FINDINGS.md documented:
a 57.9%-win-rate signal expressed as a call credit spread returned exactly 0.00%.

READ THIS OFF THE TABLE:
  - Nothing in the published microstructure literature delivers a 55%+ directional hit
    rate at a 90-minute horizon on an index. The best documented numbers are ~51% at
    1 minute on single stocks, decaying to ~0 by 30 minutes.
  - A real, stable 53% signal is worth Sharpe ~0.3 traded once a day in futures, and is
    worth NEGATIVE money in long 0DTE options.
  - The 55% bar used in the FINDINGS.md indicator sweep was the right bar FOR OPTIONS.
    For delta-1 the bar is ~51.5% -- but a 52-53% signal still only buys Sharpe 0.1-0.3,
    so relaxing the bar does not rescue the programme. It changes the instrument, not
    the conclusion.
"""


def main():
    d = pd.read_parquet(paths.require_data("spxw", "data_opt.parquet"),
                        columns=["quote_date", "quote_time", "active_underlying_price"])
    d["quote_time"] = d["quote_time"].astype(str)
    px = (d.groupby(["quote_date", "quote_time"])["active_underlying_price"]
            .first().unstack().sort_index())

    print(f"{'horizon':9s} {'n':>5s} {'E|move|':>8s} {'sd(move)':>9s} "
          f"{'P(|move|>0.3%)':>15s}")
    for lbl, (a, b) in HOR.items():
        r = (px[b] / px[a] - 1).dropna()
        print(f"{lbl:9s} {len(r):5d} {r.abs().mean()*100:7.3f}% {r.std()*100:8.3f}% "
              f"{np.mean(r.abs() > 0.003)*100:14.1f}%")

    print("\n=== Break-even hit rate and resulting Sharpe, ONE trade per day, 90-min hold ===")
    r = (px["12:30:00"] / px["11:00:00"] - 1).dropna()
    m, sd = r.abs().mean(), r.std()
    print(f"(E|move| = {m*100:.3f}%, sd = {sd*100:.3f}%, 252 trades/yr)\n")

    print("DELTA-1 (cost is a fraction of notional; payoff is the move itself)")
    print(f"{'instrument':32s} {'RT cost':>9s} {'break-even p':>13s}"
          f" {'p for SR=0.5':>13s} {'p for SR=1.0':>13s}")
    for name, c in [("ES futures", 0.000050), ("MES futures", 0.000073),
                    ("SPY shares", 0.000030)]:
        # EV per trade = (2p-1)*m - c ;  SR = EV/sd * sqrt(252)
        def p_for(sr, c=c):
            ev = sr * sd / np.sqrt(252)
            return 0.5 + (ev + c) / (2 * m)
        print(f"{name:32s} {c*1e4:8.2f}bp {p_for(0)*100:12.1f}% "
              f"{p_for(0.5)*100:12.1f}% {p_for(1.0)*100:12.1f}%")

    print(VERDICT)


if __name__ == "__main__":
    main()
