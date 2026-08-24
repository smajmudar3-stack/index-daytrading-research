"""The Baltussen test done properly: full-surface NGE + the true 09:30 open.

The SPXW attempt failed to replicate, but it deviated from the paper in two
ways that both matter: it used a 0DTE +/-2% moneyness slice instead of the full
option surface, and it started r_ROD at 10:00 instead of the open. A null from a
different test is not a refutation.

This version fixes both:

  NGE     Unusual Whales /greek-exposure returns call_gamma and put_gamma for
          the WHOLE surface, already signed (calls +, puts -). Net gamma is
          their sum. This is the quantity the paper defines.

  r_ROD   09:30 open -> 15:30 close, from minute bars.
  r_LH    15:30 -> session close.

LOOK-AHEAD: the paper conditions on NGE_{t-1}, and so does this -- the previous
session's end-of-day exposure, which is known before the open on day t.

The cost is sample size: UW returns ~250 days, so after intersecting with the
minute bars and lagging by one day this is a ~200-day test. That is small, and
the report states the standard error so the result cannot be over-read.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)          # uw_client lives at the repo root
import uw_client as uw            # noqa: E402
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
T1530 = pd.Timestamp("15:30").time()
CLOSE_T = pd.Timestamp("16:00").time()


def nge_series(sym):
    r = uw._get(f"/api/stock/{sym}/greek-exposure")
    rows = r.get("data", r) if isinstance(r, dict) else r
    if not rows:
        return pd.Series(dtype=float)
    d = pd.DataFrame(rows)
    for c in ("call_gamma", "put_gamma"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["date"]).dt.date
    # calls positive, puts already negative -> net dealer gamma
    s = (d.set_index("date")["call_gamma"] + d.set_index("date")["put_gamma"])
    return s.sort_index().dropna()


def day_returns(sym):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)].copy()
    df["day"] = pd.DatetimeIndex(df.index).date
    df["t"] = pd.DatetimeIndex(df.index).time
    out = []
    for d, g in df.groupby("day"):
        if g["t"].iloc[-1] < pd.Timestamp("15:55").time():
            continue
        o = g[g.t == OPEN_T]["open"]
        p1530 = g[g.t <= T1530]["close"]
        if not len(o) or not len(p1530):
            continue
        out.append(dict(day=d, r_rod=p1530.iloc[-1] / o.iloc[0] - 1,
                        r_lh=g["close"].iloc[-1] / p1530.iloc[-1] - 1))
    return pd.DataFrame(out).set_index("day")


def report(sym, d):
    print(f"\n  {sym}   n = {len(d)}   {min(d.index)} -> {max(d.index)}")
    neg, pos = d[d.nge < 0], d[d.nge >= 0]
    print(f"    dealers SHORT gamma {len(neg)} days ({len(neg)/len(d)*100:.0f}%), "
          f"LONG {len(pos)} days")
    print(f"    {'regime':26s} {'beta':>8s} {'t':>7s} {'R2':>8s} "
          f"{'signPnL':>9s} {'t':>6s} {'n':>5s}")
    for lab, s in (("NGE >= 0 (long gamma)", pos), ("NGE <  0 (short gamma)", neg)):
        if len(s) < 25:
            print(f"    {lab:26s}  too few days ({len(s)})")
            continue
        sl, _, r, p, se = stats.linregress(s.r_rod, s.r_lh)
        t = sl / se if se > 0 else 0.0
        pnl = np.sign(s.r_rod) * s.r_lh
        tt = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl)))
        print(f"    {lab:26s} {sl:8.2f} {t:7.2f} {r*r*100:7.2f}% "
              f"{pnl.mean()*1e4:+8.2f}bp {tt:+6.2f} {len(s):5d}")
    return neg, pos


def main():
    print("=" * 96)
    print("BALTUSSEN DEALER-GAMMA TEST -- full-surface NGE, true 09:30 open")
    print("=" * 96)
    print("  NGE_{t-1} = previous session's call_gamma + put_gamma (whole surface, UW)")
    print("  r_ROD = 09:30 open -> 15:30    traded window = 15:30 -> close")

    pooled = []
    for sym in ("SPY", "QQQ", "IWM"):
        try:
            nge = nge_series(sym)
        except Exception as e:
            print(f"\n  {sym}: UW error {str(e)[:60]}")
            continue
        if nge.empty:
            print(f"\n  {sym}: no exposure data")
            continue
        rets = day_returns(sym)
        d = rets.join(nge.rename("nge_today"), how="inner")
        # LAG: condition on the PREVIOUS session's exposure.
        d["nge"] = d["nge_today"].shift(1)
        d = d.dropna()
        if len(d) < 60:
            print(f"\n  {sym}: only {len(d)} overlapping days, skipping")
            continue
        report(sym, d)
        pooled.append(d.assign(sym=sym))

    if pooled:
        allp = pd.concat(pooled)
        print("\n" + "=" * 96)
        print("  POOLED ACROSS INSTRUMENTS")
        print("=" * 96)
        neg, pos = allp[allp.nge < 0], allp[allp.nge >= 0]
        for lab, s in (("long gamma", pos), ("short gamma", neg)):
            if len(s) < 25:
                continue
            sl, _, r, p, se = stats.linregress(s.r_rod, s.r_lh)
            pnl = np.sign(s.r_rod) * s.r_lh
            tt = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl)))
            se_hit = np.sqrt(0.25 / len(pnl)) * 100
            print(f"    {lab:12s} n={len(s):4d}  beta {sl:6.2f} (t {sl/se:+5.2f})  "
                  f"R2 {r*r*100:5.2f}%   signPnL {pnl.mean()*1e4:+6.2f}bp "
                  f"(t {tt:+5.2f})  hit {(pnl>0).mean()*100:.1f}% +/- {se_hit:.1f}")

        print("\n  Baltussen: long gamma beta 0.82 (t 1.03, R2 0.05%);")
        print("             short gamma beta 6.63 (t 4.78, R2 3.58%).")
        print("  Replication requires short-gamma beta to be LARGE and POSITIVE")
        print("  and materially bigger than the long-gamma beta.")


if __name__ == "__main__":
    main()
