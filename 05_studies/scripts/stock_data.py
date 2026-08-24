"""Fetch daily history for a liquid, optionable US stock universe (Tiingo).

SURVIVORSHIP WARNING, stated up front because it bounds every conclusion drawn
from this data: the universe is defined by names that are liquid and optionable
TODAY. Tiingo's free tier does not serve delisted tickers (FTCH returns zero
rows), so companies that blew up and got removed are absent. That biases every
long-side result upward.

Two mitigations are applied downstream in the backtest rather than pretended
away here:
  1. results are re-run excluding the top decile of total-period performers --
     if the edge lives only in the survivors, it dies under that cut;
  2. the market-relative (residual) framing removes the common drift component,
     which is where most of the survivorship inflation sits.
"""
import json
import os
import sys
import time
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "stocks")
ENV = os.path.expanduser("~/quant-factory/.env")

START = "2005-01-01"

# Liquid, deeply-optionable US names with tight spreads -- the only ones where
# a retail options swing trade is actually expressible. Grouped by character
# because the market-conditioning work needs high-beta and low-beta names to
# separate "copies the market" from "moves on its own".
MEGA = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "AVGO", "BRK-B", "JPM"]
TECH = ["AMD", "INTC", "MU", "QCOM", "TXN", "ADBE", "CRM", "ORCL", "CSCO", "IBM",
        "NOW", "PANW", "SNOW", "NET", "DDOG", "SHOP", "UBER", "ABNB", "PLTR", "SMCI",
        "MRVL", "ON", "LRCX", "AMAT", "KLAC", "ASML", "ARM", "COIN", "SQ", "PYPL"]
CONSUMER = ["WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "DIS", "NFLX",
            "PG", "KO", "PEP", "PM", "MO", "CL", "KMB", "GIS", "LULU", "CMG"]
FIN = ["BAC", "WFC", "GS", "MS", "C", "SCHW", "BLK", "AXP", "V", "MA",
       "USB", "PNC", "TFC", "COF", "SPGI", "CME", "ICE", "AIG", "MET", "PRU"]
HEALTH = ["UNH", "JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "DHR", "BMY",
          "AMGN", "GILD", "CVS", "CI", "ISRG", "VRTX", "REGN", "MRNA", "BIIB", "ZTS"]
ENERGY = ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC", "OXY", "HAL",
          "DVN", "FANG", "KMI", "WMB", "OKE"]
INDUST = ["BA", "CAT", "DE", "GE", "HON", "LMT", "RTX", "UPS", "FDX", "UNP",
          "CSX", "NSC", "MMM", "EMR", "ETN", "PH", "ITW", "GD", "NOC", "WM"]
MATS_UTIL = ["LIN", "APD", "SHW", "FCX", "NEM", "NUE", "DOW", "NEE", "DUK", "SO",
             "D", "AEP", "EXC", "SRE", "XEL"]
# High-beta / high-vol names -- where a leveraged options swing actually pays,
# and where the market-copying effect is strongest.
HIVOL = ["MARA", "RIOT", "MSTR", "SOFI", "AFRM", "RBLX", "U", "DKNG", "CVNA", "UPST",
         "IONQ", "RKLB", "LCID", "RIVN", "NIO", "F", "GM", "DAL", "AAL", "CCL",
         "NCLH", "GME", "AMC", "HOOD", "ROKU", "PINS", "SNAP", "TTD", "ZM", "DOCU"]

UNIVERSE = sorted(set(MEGA + TECH + CONSUMER + FIN + HEALTH + ENERGY + INDUST + MATS_UTIL + HIVOL))


def token():
    with open(ENV) as f:
        for line in f:
            if line.startswith("TIINGO_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no TIINGO_API_KEY")


def fetch_one(tk, tok, start=START):
    url = (
        f"https://api.tiingo.com/tiingo/daily/{tk}/prices"
        f"?startDate={start}&format=json&token={tok}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        rows = json.loads(r.read().decode())
    if not rows:
        return None
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)
    # adjClose/adjOpen are split- AND dividend-adjusted. Using raw close would
    # inject fake -30% gaps on every split and manufacture "crashes".
    out = pd.DataFrame({
        "date": d["date"],
        "ticker": tk,
        "open": d["adjOpen"],
        "high": d["adjHigh"],
        "low": d["adjLow"],
        "close": d["adjClose"],
        "volume": d["adjVolume"],
    })
    return out.sort_values("date").reset_index(drop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    tok = token()
    print(f"fetching {len(UNIVERSE)} tickers from {START}")

    frames, failed = [], []
    for i, tk in enumerate(UNIVERSE, 1):
        for attempt in range(3):
            try:
                d = fetch_one(tk, tok)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    d = None
                    print(f"  [{i:3d}/{len(UNIVERSE)}] {tk:6s} FAILED {exc}", file=sys.stderr)
                else:
                    time.sleep(2)
        if d is None or len(d) < 250:
            failed.append(tk)
            continue
        frames.append(d)
        if i % 25 == 0 or i == len(UNIVERSE):
            print(f"  [{i:3d}/{len(UNIVERSE)}] {tk:6s} {len(d):5d} rows  {d.date.iloc[0].date()}")
        time.sleep(0.12)

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    path = os.path.join(OUT, "panel.parquet")
    panel.to_parquet(path, index=False)

    print()
    print(f"wrote {path}")
    print(f"  {len(panel):,} rows, {panel.ticker.nunique()} tickers")
    print(f"  {panel.date.min().date()} -> {panel.date.max().date()}")
    if failed:
        print(f"  failed/short ({len(failed)}): {failed}")


if __name__ == "__main__":
    main()
