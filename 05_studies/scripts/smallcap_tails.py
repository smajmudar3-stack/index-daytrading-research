"""Do small / low-priced stocks have fatter tails — and can you trade them?

The large-cap study measured P(3 sigma) at 3.01% over 42 days. Small and
low-priced names should be materially fatter than that; that is the whole
reason to look there.

But there is a real tension and it is the point of this file:

    MORE TAIL  (small caps move more)  vs  WORSE EXECUTION (their options are
    wider, thinner, and sometimes do not exist at all).

The large-cap work already showed execution is what decides the outcome —
far-OTM buying was -45.6% overall but +5.6% once filtered to <=20% spread. So
measuring the extra tail without measuring the extra spread would answer half
the question and the wrong half.

Two passes:
  1. TAIL by price bucket and by market-cap proxy — how much fatter, exactly.
  2. OPTION REALITY for those same names, straight from the local chain: do
     contracts exist, what do they cost, and what is the real spread?
"""
import os
import subprocess
import warnings
from io import StringIO

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")
DOLT = paths.data("dolt")
OUT = paths.data("bigmove")

H = 42                       # the horizon that tested strongest
PRICE_BUCKETS = [(0, 2, "<$2 (penny)"), (2, 5, "$2-5"), (5, 10, "$5-10"),
                 (10, 25, "$10-25"), (25, 75, "$25-75"), (75, 1e9, ">$75")]


def dolt(sql, timeout=900):
    r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"], cwd=DOLT,
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(r.stdout))


def main():
    print("=" * 100)
    print("SMALL / LOW-PRICED NAMES — is the tail fatter, and is it tradeable?")
    print("=" * 100)

    # Which names does the option chain actually cover? That is the real
    # universe -- a stock with no listed options is not a candidate however
    # much it moves.
    print("\n  finding the optionable universe and its price levels ...", flush=True)
    latest = dolt("select max(`date`) as d from options.option_chain")
    if latest.empty:
        print("  no chain"); return
    LD = str(latest.iloc[0, 0])

    # Underlying price proxied by the strike whose call delta is nearest 0.50.
    atm = dolt(f"""select act_symbol, avg(strike) as px, count(*) as n
                   from options.option_chain
                   where `date`='{LD}' and call_put='Call'
                     and delta between 0.45 and 0.55
                   group by act_symbol""")
    if atm.empty:
        print("  could not derive prices"); return
    atm = atm[atm.n >= 1]
    print(f"  {len(atm):,} optionable names on {LD}")

    # ---- tail by price bucket, from the daily bars -----------------------
    print("\n  pulling daily history for the tail measurement ...", flush=True)
    ohlc = dolt("""select act_symbol, `date`, `close`
                    from stocks.ohlcv where `date` >= '2021-01-01'""")
    if ohlc.empty:
        print("  no ohlcv"); return
    ohlc["date"] = pd.to_datetime(ohlc["date"])
    ohlc = ohlc.rename(columns={"act_symbol": "ticker"})
    print(f"  {len(ohlc):,} daily bars, {ohlc.ticker.nunique():,} names")

    rows = []
    for t, g in ohlc.groupby("ticker"):
        g = g.sort_values("date")
        c = g["close"].astype(float)
        if len(c) < 300:
            continue
        r = c.pct_change(fill_method=None)
        sig = r.rolling(60).std()
        # SPLIT GUARD: the split table in this dataset is 33% duplicate rows and
        # ohlcv is unadjusted, so a raw return series contains fake -90% days.
        # Any single day beyond +/-60% is treated as a corporate action, not a
        # move, and dropped rather than counted as a black swan.
        r = r.mask(r.abs() > 0.60)
        fmax = c.rolling(H).max().shift(-H) / c - 1
        fmin = c.rolling(H).min().shift(-H) / c - 1
        move = pd.concat([fmax.abs(), fmin.abs()], axis=1).max(axis=1)
        d = pd.DataFrame({"ticker": t, "date": g["date"].values,
                          "px": c.values, "sig": sig.values,
                          "move_sig": (move / (sig * np.sqrt(H))).values})
        rows.append(d)
    d = pd.concat(rows, ignore_index=True).dropna()
    d = d[np.isfinite(d.move_sig) & (d.sig > 0)]
    d.to_parquet(os.path.join(OUT, "smallcap_panel.parquet"), index=False)
    print(f"  {len(d):,} stock-days measured\n")

    print("=" * 100)
    print(f"1. TAIL FREQUENCY BY SHARE PRICE ({H}-day window, move in own sigma)")
    print("=" * 100)
    print(f"  {'price bucket':14s} {'n':>10s} {'names':>7s} {'P(2sig)':>9s} "
          f"{'P(3sig)':>9s} {'P(4sig)':>9s} {'P(5sig)':>9s}")
    for lo, hi, lab in PRICE_BUCKETS:
        s = d[(d.px >= lo) & (d.px < hi)]
        if len(s) < 2000:
            continue
        print(f"  {lab:14s} {len(s):10,d} {s.ticker.nunique():7,d} "
              f"{(s.move_sig>=2).mean()*100:8.2f}% {(s.move_sig>=3).mean()*100:8.2f}% "
              f"{(s.move_sig>=4).mean()*100:8.2f}% {(s.move_sig>=5).mean()*100:8.2f}%")

    # Raw move size matters too: a 3-sigma move on a quiet name may be smaller
    # in percent than a 2-sigma move on a volatile one.
    print(f"\n  {'price bucket':14s} {'median |move|':>14s} {'p90 |move|':>12s} "
          f"{'p99 |move|':>12s}   (raw %, not sigma)")
    for lo, hi, lab in PRICE_BUCKETS:
        s = d[(d.px >= lo) & (d.px < hi)]
        if len(s) < 2000:
            continue
        raw = s.move_sig * s.sig * np.sqrt(H) * 100
        print(f"  {lab:14s} {raw.median():13.1f}% {raw.quantile(0.90):11.1f}% "
              f"{raw.quantile(0.99):11.1f}%")

    # ---- 2. can you actually buy the option? -----------------------------
    print("\n" + "=" * 100)
    print("2. OPTION REALITY — spreads on far-OTM calls, by underlying price")
    print("=" * 100)
    ch = dolt(f"""select act_symbol, strike, bid, ask, delta, expiration
                  from options.option_chain
                  where `date`='{LD}' and call_put='Call'
                    and delta between 0.08 and 0.20 and bid > 0""")
    if ch.empty:
        print("  no far-OTM contracts returned"); return
    ch = ch.merge(atm[["act_symbol", "px"]], on="act_symbol", how="left").dropna(subset=["px"])
    ch["mid"] = (ch.bid + ch.ask) / 2
    ch = ch[ch.mid > 0]
    ch["spread"] = (ch.ask - ch.bid) / ch.mid

    print(f"  {'price bucket':14s} {'names':>7s} {'contracts':>10s} "
          f"{'med cost':>10s} {'med spread':>11s} {'% tradeable':>12s}")
    for lo, hi, lab in PRICE_BUCKETS:
        s = ch[(ch.px >= lo) & (ch.px < hi)]
        if len(s) < 30:
            continue
        print(f"  {lab:14s} {s.act_symbol.nunique():7,d} {len(s):10,d} "
              f"${s.ask.median()*100:9.0f} {s.spread.median()*100:10.1f}% "
              f"{(s.spread<=0.20).mean()*100:11.1f}%")

    print("\n" + "=" * 100)
    print("  The two tables answer the question jointly: table 1 is how much more")
    print("  tail the cheaper names give you, table 2 is how much of it execution")
    print("  takes back. A bucket only works if the lift in table 1 survives the")
    print("  spread in table 2 -- and '% tradeable' is how many candidates remain.")


if __name__ == "__main__":
    main()
