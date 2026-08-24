"""Refine + robustness-check the overnight strategy: is the vol filter overfit? Does
vol-targeting help? Final walk-forward."""
import numpy as np
import pandas as pd
import yfinance as yf

COST = 0.0001


def load():
    spy = yf.download("SPY", start="2005-01-01", interval="1d", progress=False,
                      auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
    vix = yf.download("^VIX", start="2005-01-01", interval="1d", progress=False,
                      auto_adjust=False, multi_level_index=False).rename(columns=str.lower)["close"]
    spy["on"] = spy["open"] / spy["close"].shift(1) - 1
    spy["above200"] = spy["close"] > spy["close"].rolling(200).mean()
    spy["vix"] = vix.reindex(spy.index).ffill()
    spy["vix_ma"] = spy["vix"].rolling(20).mean()
    return spy.dropna()


def sh(r):
    r = r.dropna()
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0


d = load()
on = d["on"]
print("=== vol-filter threshold sensitivity (relative VIX>ma*k -> skip) — robust if stable ===")
for k in (1.1, 1.2, 1.3, 1.4, 1.5, 99):
    mask = d["above200"] & (d["vix"] < d["vix_ma"] * k)
    r = pd.Series(np.where(mask, on - COST, 0.0), index=d.index)
    print(f"  k={k:>4}: Sharpe {sh(r):+.2f}  exp {mask.mean()*100:.0f}%")
print("=== absolute VIX skip thresholds ===")
for v in (20, 25, 30, 35, 999):
    mask = d["above200"] & (d["vix"] < v)
    r = pd.Series(np.where(mask, on - COST, 0.0), index=d.index)
    print(f"  skip VIX>{v:>3}: Sharpe {sh(r):+.2f}  exp {mask.mean()*100:.0f}%")

print("=== vol-targeting (scale position by inverse of trailing overnight vol) ===")
base = d["above200"] & (d["vix"] < d["vix_ma"] * 1.3)
raw = pd.Series(np.where(base, on - COST, 0.0), index=d.index)
onvol = on.rolling(20).std()
target = 0.005  # 0.5% nightly target
size = (target / onvol).clip(upper=3.0).shift(1)  # cap 3x, lagged (causal)
vt = pd.Series(np.where(base, (on * size - COST * size.abs()).fillna(0), 0.0), index=d.index)
print(f"  base (C):        Sharpe {sh(raw):+.2f}  CAGR {(np.prod(1+raw)**(252/len(raw))-1)*100:+.1f}%  maxDD {((1+raw).cumprod()/(1+raw).cumprod().cummax()-1).min()*100:.1f}%")
print(f"  vol-targeted:    Sharpe {sh(vt):+.2f}  CAGR {(np.prod(1+vt)**(252/len(vt))-1)*100:+.1f}%  maxDD {((1+vt).cumprod()/(1+vt).cumprod().cummax()-1).min()*100:.1f}%")

print("=== WALK-FORWARD: fit nothing; apply C out-of-sample by year ===")
yrs = sorted(set(d.index.year))
wf = []
for y in yrs:
    seg = d[d.index.year == y]
    mask = seg["above200"] & (seg["vix"] < seg["vix_ma"] * 1.3)
    r = pd.Series(np.where(mask, seg["on"] - COST, 0.0), index=seg.index)
    yr_ret = (1 + r).prod() - 1
    wf.append((y, yr_ret, sh(r)))
pos = sum(1 for _, rr, _ in wf if rr > 0)
print(f"  positive years: {pos}/{len(wf)}")
for y, rr, s in wf:
    print(f"    {y}: {rr*100:+6.1f}%  (Sharpe {s:+.2f})")
