"""momentum_intraday.py — the Zarattini "Beat the Market" intraday momentum breakout, tested on our
minute data + conditioned on gamma regime.

Method (faithful-ish to Strategy 2): volatility-scaled breakout band from the 14-day rolling mean of
|price - open| at each minute-of-day; go WITH a break beyond the band, filtered by EMA(100) trend;
exit when price reverts across VWAP or the opposite band, else liquidate 15:55. This is MOMENTUM
(continuation), the opposite of the wall-fade that just failed. Hypothesis: works, and best on
LOW-gamma (trend) days.
"""
import glob
import numpy as np
import pandas as pd
from scipy import stats

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
G["gz"] = ((G.gex - G.gex.rolling(252, min_periods=60).mean()) / G.gex.rolling(252, min_periods=60).std()).shift(1)
gzmap = G.set_index(G["date"].dt.date)["gz"]

COST = 0.0003       # ~3bps round trip
BAND_K = 1.0        # band multiple of the rolling mean-abs-deviation

# --- load minute SPY, build per-day frames keyed by minute-of-day ---
days = {}
for f in sorted(glob.glob("data/minute/SPY/*.parquet")):
    m = pd.read_parquet(f).between_time("09:30", "15:59")
    for day, g in m.groupby(m.index.date):
        g = g.between_time("09:30", "15:58")
        if len(g) < 200:
            continue
        g = g.copy()
        g["mod"] = range(len(g))                       # minute-of-day index
        g["open_day"] = g["close"].iloc[0]
        g["dev"] = (g["close"] - g["open_day"]) / g["open_day"]
        g["ema"] = g["close"].ewm(span=100, adjust=False).mean()
        days[day] = g.reset_index(drop=True)

order = sorted(days)
# rolling 14-day band of |dev| by minute-of-day
hist = []
trades = []
for day in order:
    g = days[day]
    if len(hist) >= 14:
        past = pd.concat(hist[-14:])
        band = past.groupby("mod")["absdev"].mean()
    else:
        band = None
    if band is not None:
        pos = 0; entry = 0.0; entered = False
        for _, r in g.iterrows():
            b = band.get(r["mod"], np.nan)
            if np.isnan(b):
                continue
            ub, lb = BAND_K * b, -BAND_K * b
            if pos == 0 and not entered:                # ONE entry per day, on the first clean breakout
                if r["dev"] > ub and r["close"] > r["ema"]:
                    pos = 1; entry = r["close"]; entered = True
                elif r["dev"] < lb and r["close"] < r["ema"]:
                    pos = -1; entry = r["close"]; entered = True
            elif pos != 0:
                # HOLD the trend — exit only on a decisive OPPOSITE-band break (real reversal), else EOD
                if (pos == 1 and r["dev"] < lb) or (pos == -1 and r["dev"] > ub):
                    ret = (r["close"] - entry) / entry * pos - COST
                    trades.append((day, gzmap.get(day, np.nan), ret)); pos = 0
        if pos != 0:                                   # liquidate EOD 15:58
            ret = (g["close"].iloc[-1] - entry) / entry * pos - COST
            trades.append((day, gzmap.get(day, np.nan), ret))
    g["absdev"] = g["dev"].abs()
    hist.append(g[["mod", "absdev"]])

T = pd.DataFrame(trades, columns=["day", "gz", "ret"]).dropna(subset=["gz"])
print(f"{len(T)} trades across {T.day.nunique()} days ({T.day.min()} → {T.day.max()})\n")

def rpt(lab, s):
    if len(s) < 20:
        print(f"  {lab:<24} n={len(s)} too few"); return
    t, p = stats.ttest_1samp(s, 0)
    print(f"  {lab:<24} n={len(s):>5}  avg {s.mean()*1e4:+6.1f}bps  win {(s>0).mean()*100:4.0f}%  "
          f"sum {s.sum()*100:+6.1f}%  t {t:+5.2f}  p {p:.3f}")

print("Intraday MOMENTUM breakout (vol-band + EMA100), by gamma regime:")
rpt("ALL", T.ret)
rpt("LOW gamma (gz<-0.5)", T[T.gz < -0.5].ret)
rpt("MID", T[T.gz.between(-0.5, 0.5)].ret)
rpt("HIGH gamma (gz>0.5)", T[T.gz > 0.5].ret)
print("\nExpect: POSITIVE overall (esp. LOW/negative gamma = trend days). This is the validated-in-lit edge;")
print("if it holds net of cost here, THIS is the scalp/small-play engine (momentum, not fade).")
