"""Fetch and cache the daily panel for swing-horizon research.

Universe = sector ETFs (the rotation candidates) + broad indices + macro/regime
proxies. Everything daily, adjusted, as far back as each ticker goes.

Written to data/swing/ as parquet. Re-running refreshes in place.
"""
import os
import sys
import time

import pandas as pd
import yfinance as yf

from idt import paths

OUT = paths.data("swing")

# The 11 SPDR sectors — the rotation universe. XLRE (2015) and XLC (2018) are
# late additions; the backtest must handle ragged start dates, not drop them.
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]

# Broad + style + size, for relative strength and factor-rotation signals.
BROAD = ["SPY", "QQQ", "IWM", "DIA", "MDY", "EFA", "EEM", "IWF", "IWD", "MTUM", "QUAL", "USMV", "VLUE", "SIZE"]

# Macro / regime instruments. Credit spread (HYG vs LQD/IEF), duration (TLT/IEF),
# real assets (GLD/DBC), dollar (UUP). These drive the bull/bear conditioning.
MACRO = ["TLT", "IEF", "SHY", "HYG", "LQD", "GLD", "SLV", "DBC", "USO", "UUP", "FXE", "VNQ"]

# Volatility complex. ^VIX and ^VIX3M give the term structure, which is the
# single most-cited swing-horizon regime signal.
VOL = ["^VIX", "^VIX3M", "^VIX9D", "^VVIX", "^SKEW", "^GSPC", "^NDX", "^RUT"]

ALL = SECTORS + BROAD + MACRO + VOL

START = "1998-01-01"


def fetch(tickers, start=START, chunk=8, pause=1.0):
    """Download in small chunks — yfinance rate-limits large multi-ticker pulls."""
    frames = {}
    for i in range(0, len(tickers), chunk):
        batch = tickers[i : i + chunk]
        for attempt in range(3):
            try:
                df = yf.download(
                    batch,
                    start=start,
                    auto_adjust=True,
                    progress=False,
                    group_by="ticker",
                    threads=False,
                )
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  retry {attempt+1} for {batch}: {exc}", file=sys.stderr)
                time.sleep(3)
        else:
            print(f"  FAILED {batch}", file=sys.stderr)
            continue

        for tk in batch:
            try:
                sub = df[tk] if len(batch) > 1 else df
            except KeyError:
                print(f"  missing {tk}", file=sys.stderr)
                continue
            sub = sub.dropna(how="all")
            if sub.empty:
                print(f"  empty {tk}", file=sys.stderr)
                continue
            frames[tk] = sub
            print(f"  {tk:8s} {len(sub):6d} rows  {sub.index[0].date()} -> {sub.index[-1].date()}")
        time.sleep(pause)
    return frames


def main():
    os.makedirs(OUT, exist_ok=True)
    print(f"fetching {len(ALL)} tickers from {START}")
    frames = fetch(ALL)

    # One tidy long panel is easier to reason about than 50 files, and small
    # enough (~50 tickers x ~7000 days) that memory is a non-issue.
    rows = []
    for tk, df in frames.items():
        d = df.reset_index()
        d.columns = [str(c).lower() for c in d.columns]
        d["ticker"] = tk
        rows.append(d[["date", "ticker", "open", "high", "low", "close", "volume"]])

    panel = pd.concat(rows, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"]).dt.tz_localize(None)
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)

    path = os.path.join(OUT, "panel.parquet")
    panel.to_parquet(path, index=False)

    print()
    print(f"wrote {path}")
    print(f"  {len(panel):,} rows, {panel.ticker.nunique()} tickers")
    print(f"  {panel.date.min().date()} -> {panel.date.max().date()}")
    missing = sorted(set(ALL) - set(panel.ticker.unique()))
    if missing:
        print(f"  MISSING: {missing}")


if __name__ == "__main__":
    main()
