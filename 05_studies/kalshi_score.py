"""kalshi_score.py — does the same event trade at different prices on Kalshi and Polymarket,
and is the gap ever larger than both venues' fees? Scores `04_live_system/kalshi_recorder.py`.

Only pairs whose two legs RESOLVE AT THE SAME TIME count. The daily "Bitcoin above X"
strikes resolve at 5pm ET on Kalshi and noon ET on Polymarket, so a price gap between
them is time value, not mispricing; they are reported separately as "not the same event".
For the true pairs (the 15-minute windows): the distribution of the YES-mid difference, the
share of ticks where buying YES on one venue and NO on the other costs under $1.00 after
both taker fees, the deepest such moment, and the depth available at it.
"""
import os
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402


def main():
    c = sqlite3.connect(paths.state("kalshi_pairs.db"))
    d = pd.read_sql("SELECT * FROM pairs", c)
    c.close()
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
        if len(arb):
            a = arb.sort_values("best_cost").iloc[0]
            depth = min(x for x in (a.k_yes_ask_sz, a.p_yes_bid_sz, a.k_yes_bid_sz, a.p_yes_ask_sz) if pd.notna(x)) if any(pd.notna(x) for x in (a.k_yes_ask_sz, a.p_yes_bid_sz)) else None
            print(f"  deepest: {a.k_ticker} vs {a.p_slug} at cost {a.best_cost:.3f}, depth ~{depth} contracts, "
                  f"gross edge ${(1-a.best_cost)*(depth or 0):.2f} if fully filled")


if __name__ == "__main__":
    main()
