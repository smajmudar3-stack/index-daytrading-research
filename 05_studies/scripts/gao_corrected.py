"""Gao/Baltussen intraday momentum, with the outcome window defined correctly.

The previous run binned by floor("30min"), which put the single 16:00 bar in a
bin of its own. The "last half hour" it measured was therefore the last MINUTE
(15:59->16:00), not 15:30->16:00. That is not the published rule and the result
from it should be discarded.

This version anchors on explicit clock times instead of bins:

    r_first  = 09:30 open      -> 10:00 close
    r_penult = 15:00 close     -> 15:30 close
    r_last   = 15:30 close     -> session close      <-- the outcome

Three variants, in increasing fidelity to the literature:

  A. Gao et al. (2018)          sign(r_first) -> r_last
  B. first-last (quantrocket)   trade only when r_first and r_penult AGREE
  C. B, gated to VIX >= 20      Baltussen et al. (2021) supply the mechanism --
                                leveraged-ETF and hedging rebalance demand into
                                the close -- which predicts the effect should
                                strengthen with volatility. The reference
                                implementation disables the rule below VIX 20.

Costs are applied at the end, because a 30-minute-a-day equity rule is cheap
and the honest question is whether the gross effect exists at all first.
"""
import glob
import os

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
T = {k: pd.Timestamp(k).time() for k in ("09:30", "10:00", "15:00", "15:30", "16:00")}


def day_points(sym):
    """One row per day with the five anchor prices."""
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= T["09:30"]) & (idx.time <= T["16:00"])].copy()
    idx = pd.DatetimeIndex(df.index)
    df["day"], df["t"] = idx.date, idx.time

    def last_at_or_before(g, t):
        s = g[g.t <= t]
        return s["close"].iloc[-1] if len(s) else np.nan

    rows = []
    for d, g in df.groupby("day"):
        o = g[g.t == T["09:30"]]["open"]
        if not len(o):
            continue
        rows.append(dict(day=d, p_open=o.iloc[0],
                         p1000=last_at_or_before(g, T["10:00"]),
                         p1500=last_at_or_before(g, T["15:00"]),
                         p1530=last_at_or_before(g, T["15:30"]),
                         p_close=g["close"].iloc[-1],
                         last_t=g["t"].iloc[-1]))
    p = pd.DataFrame(rows).set_index("day").dropna()
    # Half days settle at 13:00; their 15:30->close window does not exist.
    p = p[p.last_t >= pd.Timestamp("15:55").time()]
    return pd.DataFrame({
        "r_first":  p.p1000 / p.p_open - 1,
        "r_penult": p.p1530 / p.p1500 - 1,
        "r_last":   p.p_close / p.p1530 - 1,
    })


def vix_series():
    v = yf.download("^VIX", start="2024-06-01", end="2026-08-20",
                    progress=False, auto_adjust=False)
    s = v["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.DatetimeIndex(s.index).date
    # Previous close, so the gate uses only information available at 15:30.
    return s.shift(1)


def evaluate(tag, pos, r_last, n_total):
    live = pos != 0
    if live.sum() < 20:
        print(f"    {tag:34s} too few trades ({live.sum()})")
        return
    pnl = (pos * r_last)[live]
    n = len(pnl)
    t = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(n)) if pnl.std() else 0.0
    hit = (pnl > 0).mean()
    bp = pnl.mean() * 1e4
    # Round trip in SPY: ~1bp all-in for a liquid 30-minute equity trade.
    net = bp - 1.0
    ann = pnl.mean() * n / (n_total / 252) * 100
    print(f"    {tag:34s} n={n:4d} ({n/n_total*100:4.1f}% of days)  hit {hit*100:5.1f}%  "
          f"{bp:+6.2f}bp  t={t:+5.2f}  net {net:+6.2f}bp  ~{ann:+5.1f}%/yr")


def main():
    vix = vix_series()
    print("=" * 100)
    print("GAO / BALTUSSEN INTRADAY MOMENTUM -- corrected outcome window (15:30 -> close)")
    print("=" * 100)
    print("  Data is 2024-2026, six-plus years after the 2018 publication: fully out of sample.\n")

    for sym in ("SPY", "QQQ", "IWM", "DIA"):
        d = day_points(sym)
        d["vix"] = pd.Series(vix.reindex(d.index).values, index=d.index)
        n_total = len(d)
        print(f"  {sym}  ({n_total} full sessions)")

        r = d.r_last
        # Correlation of the raw predictor, for reference.
        sl, _, rr, pp, se = stats.linregress(d.r_first, r)
        print(f"    {'raw corr r_first vs r_last':34s} r={rr:+.4f}  t={sl/se:+.2f}  p={pp:.3f}")

        evaluate("A. Gao: sign(r_first)", np.sign(d.r_first), r, n_total)

        agree = np.sign(d.r_first) * (np.sign(d.r_first) == np.sign(d.r_penult))
        evaluate("B. first+penult agree", pd.Series(agree, index=d.index), r, n_total)

        hi = d.vix >= 20
        evaluate("C. B, gated VIX>=20", pd.Series(agree, index=d.index).where(hi, 0),
                 r, n_total)
        evaluate("   (control) B, VIX<20", pd.Series(agree, index=d.index).where(~hi, 0),
                 r, n_total)
        print()

    print("=" * 100)
    print("  Baltussen's mechanism predicts C > control. If the VIX<20 control is")
    print("  as strong as the gated version, the gate is decoration, not mechanism.")
    print("=" * 100)


if __name__ == "__main__":
    main()
