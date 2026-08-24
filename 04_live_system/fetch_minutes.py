"""fetch_minutes.py — pull 1-minute bars from Polygon for additional symbols.

Purpose is NOT more parameter search. The rule is already fixed. This adds INDEPENDENT SAMPLES:
symbols the rule was never fit on. If the fade edge is real it should appear in other liquid index
ETFs; if it was a QQQ-specific artefact of 500 sessions, it will not. That is a genuine test, whereas
searching more combinations on the same QQQ data can only manufacture false positives.
"""
import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests


def key():
    for p in ("/Users/sahilmajmudar/quant-factory/.env",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
        if os.path.exists(p):
            for l in open(p):
                if l.startswith("POLYGON_API_KEY="):
                    return l.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("POLYGON_API_KEY")


def month_bars(sym, y, m, k):
    start = date(y, m, 1)
    end = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1))
    url = (f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/minute/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={k}")
    rows, url_next = [], url
    for _ in range(12):                       # follow pagination
        r = requests.get(url_next, timeout=60)
        if r.status_code != 200:
            return None
        j = r.json()
        rows += j.get("results") or []
        nxt = j.get("next_url")
        if not nxt:
            break
        url_next = nxt + f"&apiKey={k}"
        time.sleep(13)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df.t, unit="ms", utc=True).dt.tz_convert("America/New_York")
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close",
                            "v": "volume", "vw": "vwap", "n": "trades"})
    return df.set_index("ts")[["open", "high", "low", "close", "volume", "vwap", "trades"]]


def fetch(sym, months=24):
    k = key()
    if not k:
        print("no POLYGON_API_KEY")
        return
    out_dir = os.path.join("data", "minute", sym)
    os.makedirs(out_dir, exist_ok=True)
    today = date.today()
    got = 0
    for i in range(months):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        path = os.path.join(out_dir, f"{y}-{m:02d}.parquet")
        if os.path.exists(path):
            continue
        df = month_bars(sym, y, m, k)
        if df is None or df.empty:
            print(f"  {sym} {y}-{m:02d}: none")
            continue
        df.to_parquet(path)
        got += 1
        print(f"  {sym} {y}-{m:02d}: {len(df):,} bars")
        time.sleep(13)   # free tier: 5 requests/minute
    print(f"{sym}: wrote {got} months")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["IWM", "DIA"]):
        print(f"--- {s} ---")
        fetch(s)
