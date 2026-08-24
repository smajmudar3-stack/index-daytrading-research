"""sizing_curve.py — how hard can this edge actually be sized before it destroys itself?

A 91% win rate invites the thought "size up massively". This script tests that directly on the real
out-of-sample trade distribution instead of arguing about it.

The thing that decides the answer is not the win rate, it is the LOSER. Losing trades hit the -0.5R
stop, so at risk fraction f a single loss costs 0.5*f of the account, and losses compound
multiplicatively. Geometric growth therefore peaks at some f and falls off a cliff after it — betting
past that point lowers your expected wealth even though the edge is unchanged and positive.

Outputs:
  1. the growth-optimal fraction (empirical Kelly) from the actual return series
  2. CAGR / drawdown / terminal wealth across the whole range of f
  3. bootstrap ruin probability - the chance of losing half the account, at each f
  4. what the observed worst losing streak does to the account at each f

Filed in 04_live_system/ by the bundle split, where its one import (backtest_daily)
lived in 05_studies/ and so the module could not run from either directory. It is a
research harness — it rebuilds the whole OOS panel and prints a table — so it belongs
here with the rest of them.
"""
import numpy as np
import pandas as pd

import backtest_daily as BD

START = 2000.0
RUIN_LEVEL = 0.50          # "ruin" = down 50% from the start; a real account stops here
N_BOOT = 4000
rng = np.random.default_rng(7)


def load_trades():
    d, tr = BD.build()                      # evidence cell, gate on, -0.5R stop
    return d, tr.ret.values


def geo_growth(r, f):
    """Geometric growth per trade at risk fraction f. Returns None if any outcome wipes the account."""
    x = 1 + f * r
    if np.any(x <= 0):
        return None
    return np.exp(np.mean(np.log(x)))


def optimal_f(r):
    grid = np.linspace(0.01, 3.0, 600)
    best_f, best_g = None, -np.inf
    for f in grid:
        g = geo_growth(r, f)
        if g is not None and g > best_g:
            best_g, best_f = g, f
    return best_f, best_g


def path_stats(r, f):
    x = 1 + f * r
    if np.any(x <= 0):
        return dict(wiped=True)
    eq = np.cumprod(x)
    peak = np.maximum.accumulate(eq)
    mdd = ((peak - eq) / peak).max() * 100
    n_yrs = len(r) / 81.0                    # ~81 trades per year
    cagr = (eq[-1] ** (1 / n_yrs) - 1) * 100
    return dict(wiped=False, final=eq[-1], cagr=cagr, mdd=mdd,
                ruin=(eq / peak).min() <= RUIN_LEVEL)


def bootstrap_ruin(r, f, n_trades=162):     # 162 trades ~ 2 years
    """Chance of drawing down 50% within ~2 years, resampling the real trade distribution."""
    if np.any(1 + f * r <= 0):
        return 1.0
    hits = 0
    for _ in range(N_BOOT):
        draw = rng.choice(r, size=n_trades, replace=True)
        eq = np.cumprod(1 + f * draw)
        if eq.min() <= RUIN_LEVEL:
            hits += 1
    return hits / N_BOOT


def main():
    d, r = load_trades()
    wins = r[r > 0]
    losses = r[r <= 0]
    print(f"trades {len(r)} | win rate {(r>0).mean()*100:.0f}% | "
          f"avg win {wins.mean()*100:+.2f}% | avg loss {losses.mean()*100:+.2f}% | worst {r.min()*100:+.1f}%")
    print(f"longest observed losing streak: {BD.streaks(r)}")

    f_opt, g_opt = optimal_f(r)
    print(f"\ngrowth-optimal risk fraction (empirical Kelly): f* = {f_opt*100:.0f}% of the account per trade")
    print(f"  ...but that is the MAXIMUM of a curve that then collapses. What it costs to sit at f*:")
    st = path_stats(r, f_opt)
    print(f"  at f* -> CAGR {st['cagr']:+.0f}%, max drawdown -{st['mdd']:.0f}%")

    print("\n== SIZING CURVE (real OOS trade sequence) ==")
    print(f"  {'risk/trade':>10} {'CAGR':>9} {'maxDD':>8} {'$2k becomes':>14} {'P(-50%) in 2yr':>15}  3 losses in a row")
    for f in (0.05, 0.12, 0.25, 0.40, 0.50, 0.75, 1.00, 1.50, 2.00):
        st = path_stats(r, f)
        if st.get("wiped"):
            print(f"  {f*100:9.0f}%  {'WIPED OUT — a single max loss ends the account':>60}")
            continue
        ruin = bootstrap_ruin(r, f)
        streak3 = (1 - 0.5 * f) ** 3         # three -0.5R losses back to back
        star = "  <- f*" if abs(f - f_opt) < 0.03 else ""
        print(f"  {f*100:9.0f}% {st['cagr']:+8.0f}% {-st['mdd']:7.0f}% "
              f"{START*st['final']:>13,.0f} {ruin*100:>14.1f}%   ${START*streak3:>6,.0f}{star}")

    print("\n== WHY IT TURNS OVER ==")
    print("  A loss is a stop at -50% of the amount risked, so at risk fraction f one loser costs 0.5*f")
    print("  of the ACCOUNT, and losses multiply. Three in a row happened in this very sample:")
    for f in (0.12, 0.25, 0.50, 1.00):
        print(f"    at {f*100:3.0f}% risk: 3 straight losses leave ${START*(1-0.5*f)**3:,.0f} "
              f"of ${START:,.0f}  ({((1-0.5*f)**3-1)*100:+.0f}%)")
    print("\n  Note f* is computed on the SAME data it is evaluated on, so it is optimistic by")
    print("  construction. Standard practice is a fraction of it (half-Kelly or less), because")
    print("  overbetting past f* loses money while underbetting only slows you down.")


if __name__ == "__main__":
    main()
