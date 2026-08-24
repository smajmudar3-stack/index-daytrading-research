"""confluence.py — does SIGNAL CONFLUENCE (how many validated bullish signals agree) improve win-rate?

The 4 validated bullish signals (from direction_signals.py): high-DIX+low-gamma, very-high-DIX,
high-DIX+backwardation, high-DIX+uptrend. Question: does requiring MORE of them to fire raise the
open→close win-rate (so conviction should scale with confluence)? And where's the sweet spot before
it gets too picky (too few trades)? Calibrates the conviction score with evidence.
"""
import pandas as pd
from scipy import stats
import yfinance as yf

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
px = yf.download(["SPY", "^VIX", "^VIX9D"], start="2011-05-01", interval="1d", progress=False, auto_adjust=True)
d = pd.DataFrame({"date": px.index})
d["open"] = px["Open"]["SPY"].values; d["close"] = px["Close"]["SPY"].values
d["spyc"] = px["Close"]["SPY"].values; d["vix"] = px["Close"]["^VIX"].values; d["vix9"] = px["Close"]["^VIX9D"].values
d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)
d = d.merge(G[["date", "dix", "gex"]], on="date", how="left").sort_values("date").reset_index(drop=True)

d["dz"] = ((d.dix - d.dix.rolling(252, min_periods=60).mean()) / d.dix.rolling(252, min_periods=60).std()).shift(1)
d["gz"] = ((d.gex - d.gex.rolling(252, min_periods=60).mean()) / d.gex.rolling(252, min_periods=60).std()).shift(1)
d["trend"] = (d.spyc > d.spyc.rolling(200).mean()).shift(1)
d["ts"] = (d.vix9 / d.vix).shift(1)
d["oc"] = (d.close - d.open) / d.open * 100
d = d.dropna(subset=["dz", "gz", "oc", "trend", "ts"]).reset_index(drop=True)

# the 4 validated bullish signals
d["s1"] = (d.dz > 0.5) & (d.gz < -0.5)
d["s2"] = d.dz > 1.0
d["s3"] = (d.dz > 0.5) & (d.ts < 1.0)
d["s4"] = (d.dz > 0.5) & d.trend
d["confluence"] = d[["s1", "s2", "s3", "s4"]].sum(axis=1)

print(f"sample {len(d)} days · baseline green {(d.oc>0).mean()*100:.1f}%\n")
print(f"{'confluence':>11}{'n':>7}{'win%':>8}{'avg oc%':>10}{'t':>7}")
for c in range(0, 5):
    s = d[d.confluence == c]["oc"]
    if len(s) < 15:
        print(f"{c:>11}{len(s):>7}   too few"); continue
    t, p = stats.ttest_1samp(s, 0)
    print(f"{c:>11}{len(s):>7}{(s>0).mean()*100:>8.0f}{s.mean():>+10.3f}{t:>+7.2f}")

print("\ncumulative (>=k signals):")
for k in range(1, 5):
    s = d[d.confluence >= k]["oc"]
    if len(s) < 15:
        continue
    t, p = stats.ttest_1samp(s, 0)
    print(f"  >={k}: n={len(s):>4}  win={ (s>0).mean()*100:.0f}%  avg={s.mean():+.3f}%  t={t:+.2f}  "
          f"(trades/yr ~{len(s)/((d.date.max()-d.date.min()).days/365):.0f})")
print("\n=> pick the k where win% is clearly up but trades/yr is still usable (not too picky).")
