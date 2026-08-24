"""direction_signals.py — hunt for MORE high-conviction BULLISH and BEARISH day signals.

Builds on the DIX finding (high DIX + low GEX = bullish, t=+3.0). Now test a wider set of free,
tradeable-at-open signals and their combos, split by BULLISH vs BEARISH, ranked by conviction:
  DIX (dark-pool buying), GEX regime, trend (200d), VIX level + term structure (VIX9D/VIX),
  1-day reversal, 3-day momentum. Target = today's OPEN->CLOSE return (naked 0DTE captures this).
All predictors from PRIOR close = zero look-ahead. Reports win rate + avg + t for each.
"""
import numpy as np
import pandas as pd
from scipy import stats
import yfinance as yf

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
px = yf.download(["SPY", "^VIX", "^VIX9D"], start="2011-05-01", interval="1d",
                 progress=False, auto_adjust=True)
spy = px["Close"]["SPY"].rename("spy").to_frame()
spy["open"] = px["Open"]["SPY"]; spy["high"] = px["High"]["SPY"]; spy["low"] = px["Low"]["SPY"]; spy["close"] = px["Close"]["SPY"]
spy["vix"] = px["Close"]["^VIX"]; spy["vix9d"] = px["Close"]["^VIX9D"]
spy = spy.reset_index().rename(columns={"Date": "date"})
spy["date"] = pd.to_datetime(spy["date"]).dt.tz_localize(None)

d = spy.merge(G[["date", "dix", "gex"]], on="date", how="left").sort_values("date").reset_index(drop=True)
# prior-close predictors (lag 1 = known at today's open)
d["dixz"] = ((d.dix - d.dix.rolling(252, min_periods=60).mean()) / d.dix.rolling(252, min_periods=60).std()).shift(1)
d["gexz"] = ((d.gex - d.gex.rolling(252, min_periods=60).mean()) / d.gex.rolling(252, min_periods=60).std()).shift(1)
d["trend"] = (d.close > d.close.rolling(200).mean()).shift(1)          # above 200d SMA
d["vixlvl"] = d.vix.shift(1)
d["vix_ts"] = (d.vix9d / d.vix).shift(1)                                # <1 = backwardation (stress)
d["mom3"] = (d.close.pct_change(3)).shift(1)
d["rev1"] = (d.close.pct_change(1)).shift(1)                            # prior day return (reversal check)
d["oc"] = (d.close - d.open) / d.open * 100                            # TARGET: today open->close %
d = d.dropna(subset=["dixz", "gexz", "oc", "trend"]).reset_index(drop=True)
print(f"sample {len(d)} days {d.date.min().date()}->{d.date.max().date()}  base rate green {(d.oc>0).mean()*100:.1f}%\n")

def score(name, mask):
    s = d.loc[mask, "oc"]
    if len(s) < 30:
        return None
    t, p = stats.ttest_1samp(s, 0)
    return {"signal": name, "n": len(s), "avg_oc": s.mean(), "win": (s > 0).mean() * 100, "t": t, "p": p}

signals = [
    # --- BULLISH candidates ---
    ("BULL: high DIX + low gamma", (d.dixz > 0.5) & (d.gexz < -0.5)),
    ("BULL: high DIX + uptrend", (d.dixz > 0.5) & (d.trend)),
    ("BULL: high DIX + low gamma + uptrend", (d.dixz > 0.5) & (d.gexz < -0.5) & (d.trend)),
    ("BULL: very high DIX (z>1)", d.dixz > 1.0),
    ("BULL: uptrend + calm VIX(<18)", (d.trend) & (d.vixlvl < 18)),
    ("BULL: high DIX + backwardation(stress buy)", (d.dixz > 0.5) & (d.vix_ts < 1.0)),
    ("BULL: prior big down + high DIX (dip buy)", (d.rev1 < -1.0) & (d.dixz > 0)),
    # --- BEARISH candidates ---
    ("BEAR: low DIX + low gamma", (d.dixz < -0.5) & (d.gexz < -0.5)),
    ("BEAR: low DIX + downtrend", (d.dixz < -0.5) & (~d.trend)),
    ("BEAR: low DIX + downtrend + neg gamma", (d.dixz < -0.5) & (~d.trend) & (d.gexz < -0.5)),
    ("BEAR: very low DIX (z<-1)", d.dixz < -1.0),
    ("BEAR: downtrend + high VIX(>25)", (~d.trend) & (d.vixlvl > 25)),
    ("BEAR: backwardation + downtrend", (d.vix_ts < 0.95) & (~d.trend)),
    ("BEAR: low DIX + backwardation", (d.dixz < -0.5) & (d.vix_ts < 1.0)),
    ("BEAR: prior big up + low DIX (fade)", (d.rev1 > 1.0) & (d.dixz < 0)),
]
res = [r for r in (score(n, m) for n, m in signals) if r]
res.sort(key=lambda r: abs(r["t"]), reverse=True)
print(f"{'signal':<44}{'n':>5}{'avg oc%':>9}{'win%':>7}{'t':>7}{'p':>8}  edge")
for r in res:
    edge = "★BULL" if r["avg_oc"] > 0 and r["p"] < 0.05 else ("★BEAR" if r["avg_oc"] < 0 and r["p"] < 0.05 else "—")
    print(f"{r['signal']:<44}{r['n']:>5}{r['avg_oc']:>+9.3f}{r['win']:>7.0f}{r['t']:>+7.2f}{r['p']:>8.3f}  {edge}")

print("\n★ = statistically significant (p<0.05). Bullish = buy calls; Bearish = buy puts.")
print("Conviction ~ |t| and how far win% is from the ~54% base rate.")
