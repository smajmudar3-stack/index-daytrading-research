"""backtest_directional.py — directional 0DTE only, at 25% sizing, on the system's own filter.
What is the WEEKLY yield?

No condors here. This isolates the directional sleeve the account owner has enabled, using the same
gating the live system applies:

  - the repo's best directional signal: DIX bullish confluence >= 2 of 4 (this is `dir_mask`, the same
    construct RULES.md §2.1 found to be genuinely real on the UNDERLYING: +12.8bp open->close, t=+3.04,
    consistent across all four sub-periods)
  - entry inside the session, one trade per day
  - a premium stop, matching the live -50% stop on debit structures
  - 25% of the account risked per trade, per the owner's chosen sizing

Structures tested separately, because they have very different payoff shapes:
  long ATM call        — the lottery ticket
  ATM/+1SD debit spread— the capped version the live system would place

Reported as WEEKLY yield, plus the distribution, because a mean is meaningless on a payoff this skewed.
"""
import numpy as np
import pandas as pd

import backtest_0dte_rules as B
import backtest_daily as BD

OOS_START = "2016-01-01"
RISK_FRAC = 0.25
CONF_K = 2               # >=2 of 4 DIX confluence signals — the system's directional filter
STOP = -0.50             # premium stop: cut a long at -50% of the debit
START = 2000.0


def build(structure, short_sd, stop=STOP, k=CONF_K, aware=BD.AWARE_EVIDENCE):
    full = B.build_panel()
    full = B.add_signals(full)
    B.TILT = B.fit_tilt(full[full.date < OOS_START])
    B.AWARE = aware
    d = full[full.date >= OOS_START].copy()
    mask = B.dir_mask(d, dict(k=k, gzmax=None))
    tr = B.run_rule(d, mask, structure, short_sd=short_sd, side="call", stop=stop)
    return d, tr


def weekly(d, tr, risk_frac):
    """Collapse to ISO weeks: compound the trades inside each week."""
    s = d[["date"]].copy()
    s["ret"] = s.date.map(dict(zip(tr.date, tr.ret))).fillna(0.0) * risk_frac
    s["wk"] = s.date.dt.to_period("W")
    wk = s.groupby("wk")["ret"].apply(lambda x: np.prod(1 + x) - 1)
    return wk


def report(label, d, tr, risk_frac=RISK_FRAC):
    r = tr.ret.values
    if len(r) == 0:
        print(f"\n{label}: no trades")
        return
    wk = weekly(d, tr, risk_frac)
    a = wk.values
    eq = np.cumprod(1 + a)
    peak = np.maximum.accumulate(eq)
    mdd = ((peak - eq) / peak).max() * 100
    n_wk = len(a)
    yrs = n_wk / 52

    print(f"\n{'='*78}\n{label}   ({len(r)} trades, {risk_frac*100:.0f}% risk/trade)")
    print(f"{'='*78}")
    print(f"  per trade : mean {r.mean()*100:+.2f}%  median {np.median(r)*100:+.2f}%  "
          f"win {(r>0).mean()*100:.0f}%  best {r.max()*100:+.0f}%  worst {r.min()*100:+.0f}%")
    print(f"\n  WEEKLY YIELD")
    print(f"    mean       {a.mean()*100:+.2f}%/week")
    print(f"    median     {np.median(a)*100:+.2f}%/week   <- the typical week")
    print(f"    win rate   {(a>0).mean()*100:.0f}% of weeks positive")
    print(f"    best week  {a.max()*100:+.1f}%      worst week {a.min()*100:+.1f}%")
    for q in (5, 25, 75, 95):
        print(f"    {q:>2}th pct   {np.percentile(a,q)*100:+.1f}%")
    print(f"\n  COMPOUNDED over {n_wk} weeks ({yrs:.1f} yrs)")
    print(f"    final multiple x{eq[-1]:.4f}   max drawdown -{mdd:.1f}%")
    print(f"    ${START:,.0f}  ->  ${START*eq[-1]:,.2f}")
    # how long until the account is effectively gone
    below = np.where(eq <= 0.10)[0]
    if len(below):
        print(f"    account down 90% after {below[0]+1} weeks")
    # 2-week rolling, the owner's stated horizon
    roll = np.array([np.prod(1 + a[i:i+2]) for i in range(len(a) - 2)])
    print(f"\n  TWO-WEEK WINDOWS  median {(np.median(roll)-1)*100:+.1f}%   "
          f"best {(roll.max()-1)*100:+.1f}%   worst {(roll.min()-1)*100:+.1f}%")
    print(f"    P(5x in 2 weeks) = {(roll>=5).mean()*100:.2f}%")


def main():
    print("DIRECTIONAL 0DTE ONLY — no condors — filter: DIX bullish confluence >= 2 of 4")
    print(f"stop {STOP*100:.0f}% of premium | sizing {RISK_FRAC*100:.0f}% of account per trade")
    print("assumption cell: AWARE 0.35 / vrp 1.10 (the evidence cell used throughout RULES.md)")

    d1, t1 = build("long", 0.0)
    report("LONG ATM CALL (the lottery ticket)", d1, t1)

    d2, t2 = build("debit", 1.0)
    report("ATM/+1SD CALL DEBIT SPREAD (what the live system would place)", d2, t2)

    # sizing sweep on the better of the two, to show sizing cannot rescue a negative edge
    print(f"\n{'='*78}\nSIZING SWEEP — debit spread, does more size help?\n{'='*78}")
    print(f"  {'risk/trade':>11} {'mean wk':>10} {'median wk':>11} {'$2k after 1yr':>15} {'maxDD':>8}")
    for rf in (0.06, 0.12, 0.25, 0.50):
        wk = weekly(d2, t2, rf).values
        eq = np.cumprod(1 + wk)
        peak = np.maximum.accumulate(eq); mdd = ((peak - eq) / peak).max() * 100
        yr1 = np.prod(1 + wk[:52]) if len(wk) >= 52 else np.nan
        print(f"  {rf*100:10.0f}% {wk.mean()*100:+9.2f}% {np.median(wk)*100:+10.2f}% "
              f"{START*yr1:>14,.0f} {-mdd:7.0f}%")


if __name__ == "__main__":
    main()
