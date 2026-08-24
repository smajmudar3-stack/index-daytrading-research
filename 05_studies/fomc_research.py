"""FOMC-day behavior + current QQQ options pricing, to ground tomorrow's play.

1. How do SPY/QQQ behave on FOMC decision days historically (2019-2026)? Full-day return,
   and (where I have minute data, 2024-2026) the PRE-2pm drift vs POST-2pm reaction.
2. Live implied move for QQQ on the Wed 0DTE (7/29) and Fri (7/31) expiries.
"""
import glob
import numpy as np
import pandas as pd
import yfinance as yf

# scheduled FOMC decision dates (2nd meeting day), 2019-2026
FOMC = [
    "2019-01-30","2019-03-20","2019-05-01","2019-06-19","2019-07-31","2019-09-18","2019-10-30","2019-12-11",
    "2020-01-29","2020-03-18","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16",
    "2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15",
    "2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14",
    "2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13",
    "2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18",
    "2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10",
    "2026-01-28","2026-03-18","2026-04-29","2026-06-17",
]
FOMC = pd.to_datetime(FOMC)

print("=== FOMC decision-day behavior (2019-2026) ===")
for tk in ["SPY", "QQQ"]:
    d = yf.download(tk, start="2018-06-01", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    d["prev_close"] = d["close"].shift(1)
    d["day_ret"] = d["close"] / d["prev_close"] - 1        # prev close -> FOMC close
    d["intra"] = d["close"] / d["open"] - 1
    fd = d[d.index.isin(FOMC)]
    dbefore = d[d.index.isin(FOMC - pd.Timedelta(days=1))]
    print(f"  {tk}: FOMC-day (prevclose->close) mean {fd['day_ret'].mean()*100:+.3f}%  "
          f"win% {(fd['day_ret']>0).mean()*100:.0f}  median {fd['day_ret'].median()*100:+.2f}%  n={len(fd)}")
    print(f"       |move| median {fd['day_ret'].abs().median()*100:.2f}%  90th {fd['day_ret'].abs().quantile(.9)*100:.2f}%  "
          f"(vol on the day)")
    print(f"       day-BEFORE-FOMC mean {dbefore['day_ret'].mean()*100:+.3f}%  win% {(dbefore['day_ret']>0).mean()*100:.0f}")

# pre-2pm drift vs post from minute data (2024-2026 FOMC days)
print("\n=== intraday pre-2pm drift vs post-2pm reaction on FOMC days (minute data 2024-26) ===")
for tk in ["SPY", "QQQ"]:
    files = sorted(glob.glob(f"data/minute/{tk}/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "16:00")
    pre, post = [], []
    for fd in FOMC:
        g = df[df.index.date == fd.date()]
        if len(g) < 100:
            continue
        o = g["close"].iloc[0]
        at2 = g.between_time("13:55", "14:05")["close"]
        c = g["close"].iloc[-1]
        if len(at2) == 0:
            continue
        p2 = at2.iloc[0]
        pre.append(p2 / o - 1)          # open -> 2pm (pre-announcement drift)
        post.append(c / p2 - 1)         # 2pm -> close (reaction)
    if pre:
        pre, post = np.array(pre), np.array(post)
        print(f"  {tk}: pre-2pm (open->2pm) mean {pre.mean()*100:+.3f}% win {(pre>0).mean()*100:.0f}%  |  "
              f"post-2pm (2pm->close) mean {post.mean()*100:+.3f}% win {(post>0).mean()*100:.0f}%  |move| {np.abs(post).mean()*100:.2f}%  n={len(pre)}")

# live QQQ implied move
print("\n=== live QQQ options implied move ===")
t = yf.Ticker("QQQ")
spot = float(t.history(period="1d")["Close"].iloc[-1])
for exp in [e for e in t.options if e >= "2026-07-29"][:3]:
    try:
        ch = t.option_chain(exp)
        calls, puts = ch.calls, ch.puts
        calls = calls.iloc[(calls.strike - spot).abs().argsort()[:1]]
        puts = puts.iloc[(puts.strike - spot).abs().argsort()[:1]]
        cp = float(calls.lastPrice.iloc[0]); pp = float(puts.lastPrice.iloc[0])
        straddle = cp + pp
        iv = float(np.nanmean([calls.impliedVolatility.iloc[0], puts.impliedVolatility.iloc[0]]))
        print(f"  {exp}: straddle ${straddle:.2f} -> implied move {straddle/spot*100:.2f}%  (IV {iv*100:.0f}%, spot {spot:.2f})")
    except Exception as e:
        print(f"  {exp}: err {str(e)[:50]}")
