"""kalshi_score.py — does the same event trade at different prices on Kalshi and Polymarket,
and is the gap ever larger than both venues' fees? Scores `04_live_system/kalshi_recorder.py`.

Only pairs whose two legs RESOLVE AT THE SAME TIME count. The daily "Bitcoin above X"
strikes resolve at 5pm ET on Kalshi and noon ET on Polymarket, so a price gap between
them is time value, not mispricing; they are reported separately as "not the same event".
For the true pairs (the 15-minute windows): the distribution of the YES-mid difference, the
share of ticks where buying YES on one venue and NO on the other costs under $1.00 after
both taker fees, the deepest such moment, and the depth available at it.

Then the part that decides it: the venues define "up" against DIFFERENT references (CF
Benchmarks 60 s average vs Chainlink spot at the open; see kalshi_recorder.py), so each
window's result on both venues is joined in and every sub-$1 tick is settled at what it
actually paid — $1 when the venues agree, $0 or $2 when they do not. The disagreement
rate and the settled P&L of the sub-$1 ticks are the verdict, not the quote gap.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402


def main():
    c = sqlite3.connect(paths.state("kalshi_pairs.db"))
    d = pd.read_sql("SELECT * FROM pairs", c)
    res = pd.read_sql("SELECT kind, window_end, strike, k_result, p_yes_final FROM resolutions", c)
    c.close()
    d = d.merge(res, on=["kind", "window_end", "strike"], how="left")
    d["secs_left"] = pd.to_datetime(d.window_end).astype("int64") / 1e9 - d.ts
    d["same_event"] = d.window_end == d.p_end
    d["k_mid"] = (d.k_yes_bid + d.k_yes_ask) / 2
    d["p_mid"] = (d.p_yes_bid + d.p_yes_ask) / 2
    d["mid_gap"] = d.k_mid - d.p_mid
    d["best_cost"] = d[["cost_a_fee", "cost_b_fee"]].min(axis=1)
    hours = (d.ts.max() - d.ts.min()) / 3600 if len(d) else 0
    print(f"{len(d):,} paired ticks over {hours:.1f} h; {d.same_event.sum():,} on the same resolution time")
    for lab, s in (("SAME EVENT (15-minute windows)", d[d.same_event]), ("NOT the same event (daily strikes, 5pm vs noon)", d[~d.same_event])):
        if s.empty:
            continue
        arb = s[s.best_cost < 1.0]
        print(f"\n{lab}: {len(s):,} ticks, {s.k_ticker.nunique()} contracts")
        print(f"  Kalshi spread median {(s.k_yes_ask - s.k_yes_bid).median():.3f}, Polymarket {(s.p_yes_ask - s.p_yes_bid).median():.3f}")
        print(f"  YES mid gap (Kalshi - Polymarket): median {s.mid_gap.median():+.4f}, 5th/95th pct "
              f"{s.mid_gap.quantile(.05):+.3f} / {s.mid_gap.quantile(.95):+.3f}")
        print(f"  two-leg cost after both fees: median {s.best_cost.median():.3f}, min {s.best_cost.min():.3f}; "
              f"ticks under $1.00: {len(arb):,} ({len(arb)/len(s)*100:.2f}%)")
        r = s.drop_duplicates(["window_end", "strike"]).dropna(subset=["k_result", "p_yes_final"])
        if len(r):
            dis = ((r.k_result == "yes") != (r.p_yes_final >= 0.5)).sum()
            print(f"  resolved on both venues: {len(r)} windows; venues DISAGREE on {dis} ({dis/len(r)*100:.1f}%)")
        if len(arb):
            b = arb.dropna(subset=["k_result", "p_yes_final"]).copy()
            if len(b):
                k_yes = (b.k_result == "yes").astype(float); p_yes = (b.p_yes_final >= 0.5).astype(float)
                pay_a = k_yes + (1 - p_yes); pay_b = p_yes + (1 - k_yes)
                b["pay"] = np.where(b.cost_a_fee <= b.cost_b_fee, pay_a, pay_b)
                b["pnl"] = b.pay - b.best_cost
                late = b[b.secs_left <= 120]
                print(f"  sub-$1 ticks settled: {len(b)}, mean P&L per $1 pair {b.pnl.mean():+.4f} (paid $2: {(b.pay==2).sum()}, "
                      f"paid $0: {(b.pay==0).sum()}); last-2-minute ticks {len(late)}, mean {late.pnl.mean():+.4f}" if len(late) else
                      f"  sub-$1 ticks settled: {len(b)}, mean P&L per $1 pair {b.pnl.mean():+.4f}")
            a = arb.sort_values("best_cost").iloc[0]
            depth = min(x for x in (a.k_yes_ask_sz, a.p_yes_bid_sz, a.k_yes_bid_sz, a.p_yes_ask_sz) if pd.notna(x)) if any(pd.notna(x) for x in (a.k_yes_ask_sz, a.p_yes_bid_sz)) else None
            print(f"  deepest: {a.k_ticker} vs {a.p_slug} at cost {a.best_cost:.3f}, depth ~{depth} contracts, "
                  f"gross edge ${(1-a.best_cost)*(depth or 0):.2f} if fully filled")


if __name__ == "__main__":
    main()
