"""0DTE research — the intraday excursion distribution that drives every 0DTE P&L.

0DTE index options (SPXW/NDXP) settle at the 4pm close, so a defined-risk seller's outcome
is decided by ONE thing: how far the index closes from where it sat at entry. We measure
that exactly from 2y of minute bars (SPY=SPX proxy, QQQ=NDX proxy):

  - distribution of |close/entry - 1| for entries through the day
  - condor win rate: P(index stays within +/-D of entry through the close) by entry time & D
  - max intraday excursion (mark-to-market pain / stop analysis)

Then an EV estimate for the iron-condor seller, honest that the CREDIT is assumed (pulled
live from the real 0DTE chain separately). Everything causal.
"""
import glob
import numpy as np
import pandas as pd


def load_minute(tk):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"data/minute/{tk}/*.parquet"))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    return df.between_time("09:30", "16:00")


ENTRIES = ["09:45", "10:30", "11:30", "12:30", "13:30", "14:30"]


def excursion_table(df):
    rows = {}
    for e in ENTRIES:
        moves, maxexc = [], []
        for _day, g in df.groupby(df.index.date):
            g = g.between_time("09:30", "16:00")
            at = g.between_time(e, "16:00")
            if len(at) < 3:
                continue
            entry = at["close"].iloc[0]
            close = at["close"].iloc[-1]
            moves.append(close / entry - 1)
            maxexc.append(max(at["high"].max() / entry - 1, entry / at["low"].min() - 1))
        rows[e] = (np.array(moves), np.array(maxexc))
    return rows


def condor_winrate(moves, D):
    """P(index closes within +/-D of entry) = keep full credit."""
    return float((np.abs(moves) < D).mean())


def condor_ev(moves, D, width_pct, credit_pct):
    """EV of a 0DTE iron condor in units of the notional, held to settle.
    shorts at +/-D, wings at +/-(D+width_pct). credit = credit_pct of notional."""
    m = np.abs(moves)
    pnl = np.where(m < D, credit_pct,
          np.where(m < D + width_pct, credit_pct - (m - D), credit_pct - width_pct))
    risk = width_pct - credit_pct
    return float(pnl.mean() / risk), float((pnl > 0).mean())  # EV in R, win rate


for tk, idx in [("SPY", "SPX"), ("QQQ", "NDX")]:
    df = load_minute(tk)
    ndays = len(set(df.index.date))
    print(f"\n===== {idx} (via {tk}, {ndays} sessions) — intraday excursion to the 4pm close =====")
    tab = excursion_table(df)
    print(f"  {'entry':>7} {'|move| med':>11} {'|move| 90p':>11} {'maxexc med':>11}  "
          f"{'P(<0.3%)':>9}{'P(<0.5%)':>9}{'P(<0.75%)':>10}{'P(<1.0%)':>9}")
    for e in ENTRIES:
        mv, mx = tab[e]
        print(f"  {e:>7} {np.median(np.abs(mv))*100:>10.2f}% {np.percentile(np.abs(mv),90)*100:>10.2f}% "
              f"{np.median(mx)*100:>10.2f}%  {condor_winrate(mv,0.003)*100:>8.0f}%{condor_winrate(mv,0.005)*100:>8.0f}%"
              f"{condor_winrate(mv,0.0075)*100:>9.0f}%{condor_winrate(mv,0.01)*100:>8.0f}%")

    # EV: iron condor entered ~11:30, shorts at +/-0.5% and +/-0.75%, wing 0.5%, sweep credit
    mv, _ = tab["11:30"]
    print("  --- 0DTE iron condor entered 11:30, wing 0.5% of index, held to close ---")
    print("  breakeven needs win% > risk/(risk+credit). Sweeping the assumed credit:")
    for D in (0.005, 0.0075):
        for cr in (0.0010, 0.0015, 0.0020):   # credit as % of index (e.g. 0.0015 = ~$1.1 on 750 SPX... )
            evR, wr = condor_ev(mv, D, 0.005, cr)
            be = 0.005 / (0.005 + cr) * 0  # placeholder
            print(f"    shorts +/-{D*100:.2f}%  credit {cr*100:.2f}% notional:  win {wr*100:.0f}%  EV {evR:+.3f}R/trade")
