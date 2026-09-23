"""polymarket_score.py — is there an edge in Polymarket's 5-minute crypto up-or-down
markets against live spot? Scores what `04_live_system/polymarket_recorder.py` recorded.

Two questions, both answered from the ticks of RESOLVED windows only:

  1. CALIBRATION. Bucket every tick by seconds left and by spot-vs-window-open (bp). In
     each cell: the average YES ask, and the fraction of those windows that resolved UP.
     If the ask is systematically BELOW the resolved rate, YES was cheap there -- that is
     the mispricing the viral post claims. If the two match, the market is priced.

  2. THE TRADE. "With <= N seconds left, buy the side that is ahead (YES if spot > open
     else NO) at its ask; hold to resolution." P&L per $1 of contracts, gross of any
     fee, one trade per window, across N in {30, 60, 120}. Win rate and mean are what
     the post's "$68 -> $6,732 in a night" would need to be enormous.

Both are printed per asset and pooled, with the number of windows, because a hundred
windows is one night and a thousand is a fortnight, and t-stats on fewer are theatre.
The cross-venue recorder's crossings are summarised at the end: how many gross gaps, how
many net of fees, and the largest.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402


def load():
    c = sqlite3.connect(paths.state("polymarket_5m.db"))
    t = pd.read_sql("SELECT * FROM ticks", c)
    w = pd.read_sql("SELECT * FROM windows", c)
    c.close()
    w = w[w.resolved.notna()]
    d = t.merge(w[["asset", "window_start", "first_spot", "resolved"]], on=["asset", "window_start"])
    d["mid"] = np.where(d.cb_bid.notna(), (d.cb_bid + d.cb_ask) / 2, (d.bus_bid + d.bus_ask) / 2)
    d["move_bp"] = (d.mid / d.first_spot - 1) * 1e4
    d["up"] = (d.resolved == "up").astype(float)
    d["no_ask"] = 1 - d.yes_bid            # buying NO = selling YES at the bid, in a binary market
    return d, w


def calibration(d):
    d = d.copy()
    d["t_bin"] = pd.cut(d.secs_left, [0, 30, 60, 120, 180, 240, 300], labels=["<30s", "30-60", "60-120", "120-180", "180-240", "240-300"])
    d["m_bin"] = pd.cut(d.move_bp, [-1e9, -20, -5, 5, 20, 1e9], labels=["<-20bp", "-20..-5", "-5..5", "5..20", ">20bp"])
    g = d.groupby(["t_bin", "m_bin"], observed=True).agg(
        n_ticks=("up", "size"), n_windows=("window_start", "nunique"),
        yes_ask=("yes_ask", "mean"), yes_bid=("yes_bid", "mean"), resolved_up=("up", "mean"))
    g["edge_buy_yes"] = g.resolved_up - g.yes_ask
    g["edge_buy_no"] = (1 - g.resolved_up) - (1 - g.yes_bid)
    return g


def trade(d, n_secs):
    """One trade per window: at the last tick with secs_left <= n_secs, buy the side ahead."""
    s = d[(d.secs_left <= n_secs) & (d.secs_left > 0) & d.yes_ask.notna() & d.yes_bid.notna()]
    s = s.sort_values("secs_left").groupby(["asset", "window_start"]).first().reset_index()
    s = s[s.move_bp.abs() >= 1]                                    # a side must be ahead
    ahead_up = s.move_bp > 0
    cost = np.where(ahead_up, s.yes_ask, s.no_ask)
    won = np.where(ahead_up, s.up == 1, s.up == 0)
    pnl = np.where(won, 1 - cost, -cost) / cost                     # return on premium paid
    return pd.DataFrame({"asset": s.asset, "window_start": s.window_start, "cost": cost,
                         "won": won, "ret": pnl, "move_bp": s.move_bp})


def main():
    pd.set_option("display.width", 220)
    d, w = load()
    print(f"resolved windows: {w.resolved.notna().sum()} ({w.groupby('asset').resolved.count().to_dict()}), "
          f"ticks on them: {len(d):,}; up-rate {d.drop_duplicates(['asset','window_start']).up.mean()*100:.1f}%")
    if len(d) < 100:
        print("not enough resolved windows yet; let the recorder run")
    else:
        print("\nCALIBRATION (all assets): YES ask vs fraction resolved UP, by seconds left x spot-vs-open")
        print(calibration(d).round(3).to_string())
        print("\nTHE TRADE: buy the side that is ahead with <= N seconds left, hold to resolution")
        rows = []
        for n in (30, 60, 120, 240):
            for asset in ["all"] + sorted(d.asset.unique()):
                t = trade(d if asset == "all" else d[d.asset == asset], n)
                if len(t) < 5:
                    continue
                rows.append({"N secs": n, "asset": asset, "trades": len(t), "win": t.won.mean(),
                             "avg cost": t.cost.mean(), "mean ret on premium": t.ret.mean(),
                             "t": t.ret.mean() / t.ret.std() * np.sqrt(len(t)) if t.ret.std() else np.nan,
                             "$68 -> after these trades": 68 * np.prod(1 + t.ret * 0.5)})   # half-Kelly-ish: 50% of stake each time
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:9.3f}"))
    c = sqlite3.connect(paths.state("crypto_venues.db"))
    k = pd.read_sql("SELECT asset, COUNT(*) n, SUM(net_bp>0) net_pos, MAX(gross_bp) max_gross, MAX(net_bp) max_net FROM crossings GROUP BY asset", c)
    q = pd.read_sql("SELECT COUNT(DISTINCT ts) polls, MIN(ts) t0, MAX(ts) t1 FROM quotes", c)
    c.close()
    print(f"\nCROSS-VENUE: {int(q.polls[0])} polls over {(q.t1[0]-q.t0[0])/3600:.1f} h")
    print(k.to_string(index=False))


if __name__ == "__main__":
    main()
