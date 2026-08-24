"""Keep the advisor's SIGNAL inputs fresh.

The advisor reads spot/walls from the periscope snapshots, which the scanner
already refreshes every cycle. But the ENTRY flag — VIX backwardation inside a
golden cross — comes from `data/swing/panel.parquet`, and nothing was scheduled
to update that. It was two days stale while the board displayed a live spot,
which is the worst combination: it looks current and isn't.

This refreshes only what the signal needs (the VIX complex, SPY, and the sector
set used for breadth) rather than re-pulling all 45 tickers, so it is cheap
enough to run every scanner cycle.
"""
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(ROOT, "data", "swing", "panel.parquet")

# Only what the entry signal and breadth read.
NEEDED = ["SPY", "QQQ", "^VIX", "^VIX3M", "^GSPC", "^NDX",
          "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]


def refresh(lookback_days=400):
    if not os.path.exists(PANEL):
        print("panel missing; run scripts/swing_data.py first", file=sys.stderr)
        return False

    old = pd.read_parquet(PANEL)
    start = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    frames = []
    for i in range(0, len(NEEDED), 6):
        batch = NEEDED[i:i + 6]
        try:
            df = yf.download(batch, start=start, auto_adjust=True, progress=False,
                             group_by="ticker", threads=False)
        except Exception as exc:  # noqa: BLE001
            print(f"  fetch failed {batch}: {exc}", file=sys.stderr)
            continue
        for tk in batch:
            try:
                sub = df[tk] if len(batch) > 1 else df
            except KeyError:
                continue
            sub = sub.dropna(how="all")
            if sub.empty:
                continue
            d = sub.reset_index()
            d.columns = [str(c).lower() for c in d.columns]
            d["ticker"] = tk
            frames.append(d[["date", "ticker", "open", "high", "low", "close", "volume"]])

    if not frames:
        return False

    new = pd.concat(frames, ignore_index=True)
    new["date"] = pd.to_datetime(new["date"]).dt.tz_localize(None)

    # Replace the refreshed window for these tickers; keep everything else.
    cutoff = new["date"].min()
    keep = old[~((old.ticker.isin(NEEDED)) & (old.date >= cutoff))]
    out = (pd.concat([keep, new], ignore_index=True)
             .drop_duplicates(subset=["ticker", "date"], keep="last")
             .sort_values(["ticker", "date"])
             .reset_index(drop=True))
    out.to_parquet(PANEL, index=False)

    latest = out[out.ticker == "^VIX"].date.max()
    print(f"  panel refreshed -> {len(out):,} rows, VIX through {latest.date()}")
    return True


if __name__ == "__main__":
    refresh()
