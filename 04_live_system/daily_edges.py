"""Day-trading edges testable on 21 years of daily OHLC (SPY/QQQ = SPX/NDX proxies).

The most robust intraday structure shows up in daily bars:
  - overnight (prev_close -> open) vs intraday (open -> close): where does the drift live?
  - opening gap: does a gap fade or continue by the close?
  - day-of-week intraday tendencies.

Costs: SPY/QQQ are penny-wide; we charge 2 bps round trip per position (spread+slippage),
which is generous for these ETFs. Everything is CAUSAL (a gap at the open is known before
the intraday trade).
"""
import numpy as np
import pandas as pd
import yfinance as yf

COST = 0.0002  # 2 bps round trip


def load(tk):
    df = yf.download(tk, start="2005-01-01", interval="1d", progress=False,
                     auto_adjust=False, multi_level_index=False)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
    df["prev_close"] = df["close"].shift(1)
    df["overnight"] = df["open"] / df["prev_close"] - 1     # close(t-1) -> open(t)
    df["intraday"] = df["close"] / df["open"] - 1           # open(t) -> close(t)
    df["full"] = df["close"] / df["prev_close"] - 1
    return df.dropna()


def sharpe(r):
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 5 and r.std() > 0 else 0.0


def summarize(name, r):
    r = r.dropna()
    eq = (1 + r).prod()
    cagr = eq ** (252 / len(r)) - 1
    dd = ((1 + r).cumprod() / (1 + r).cumprod().cummax() - 1).min()
    print(f"  {name:28} Sharpe {sharpe(r):+5.2f}  CAGR {cagr*100:+6.2f}%  maxDD {dd*100:6.1f}%  "
          f"win% {(r>0).mean()*100:4.1f}  n={len(r)}")


for tk in ["SPY", "QQQ"]:
    d = load(tk)
    print(f"\n===== {tk}  ({d.index.min().date()}..{d.index.max().date()}, {len(d)} days) =====")
    print("  --- WHERE THE RETURN LIVES (gross) ---")
    summarize("buy & hold (full day)", d["full"])
    summarize("overnight only (MOC->MOO)", d["overnight"])
    summarize("intraday only (MOO->MOC)", d["intraday"])
    print("  --- net of 2bps/round-trip ---")
    summarize("overnight only NET", d["overnight"] - COST)
    summarize("intraday only NET", d["intraday"] - COST)

    # gap fade/continuation: bucket next intraday return by the opening gap
    print("  --- opening GAP -> that day's intraday return (fade vs continue) ---")
    d["gapb"] = pd.qcut(d["overnight"], 5, labels=["big down", "down", "flat", "up", "big up"])
    for b in ["big down", "down", "flat", "up", "big up"]:
        x = d.loc[d.gapb == b]
        print(f"    gap {b:9}: intraday mean {x['intraday'].mean()*100:+.3f}%  "
              f"win% {(x['intraday']>0).mean()*100:.0f}  n={len(x)}")

    # simple gap-fade strategy: on a big gap UP, short intraday; big gap DOWN, long intraday
    big = d[d.gapb.isin(["big up", "big down"])].copy()
    big["fade"] = np.where(big.gapb == "big up", -big["intraday"], big["intraday"]) - COST
    print(f"    -> GAP-FADE (fade the extreme gap, hold to close): "
          f"Sharpe {sharpe(big['fade']):+.2f}  mean {big['fade'].mean()*100:+.3f}%/day  "
          f"win% {(big['fade']>0).mean()*100:.0f}  n={len(big)}")

    # day of week intraday
    print("  --- intraday return by weekday ---")
    d["dow"] = d.index.dayofweek
    for i, nm in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        x = d.loc[d.dow == i, "intraday"]
        print(f"    {nm}: {x.mean()*100:+.3f}%  win% {(x>0).mean()*100:.0f}  n={len(x)}")
