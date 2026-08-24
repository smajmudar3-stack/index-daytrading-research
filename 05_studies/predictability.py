"""How predictable is 'tomorrow' really? Take the BEST setup we have — a stock in a strong
uptrend that pulled back a few days (exactly PSX's setup) — and measure, across 15 years and
~40 stocks, how often the NEXT day (and next 3 days) was actually green. This is the honest
ceiling of single-day prediction: a probability, not a certainty."""
import numpy as np
import pandas as pd
import yfinance as yf

UNIV = ["XOM","CVX","COP","MPC","PSX","VLO","LLY","UNH","JNJ","ABBV","MRK","PFE","CAT","DE",
        "HON","RTX","GE","JPM","GS","V","MA","PG","KO","PEP","COST","WMT","HD","NKE","MCD",
        "FCX","NEM","LIN","NUE","NEE","DUK","AAPL","MSFT","NVDA","AMZN","META"]

hits1, hits3, r1, r3, n = 0, 0, [], [], 0
for tk in UNIV:
    try:
        c = yf.download(tk, start="2010-01-01", interval="1d", progress=False, auto_adjust=True,
                        multi_level_index=False)["Close"].dropna()
    except Exception:
        continue
    if len(c) < 300:
        continue
    sma50 = c.rolling(50).mean(); sma200 = c.rolling(200).mean()
    m120 = c / c.shift(120) - 1
    hi5 = c.rolling(5).max()
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 - 100/(1 + up/(dn+1e-12))
    # PSX-like setup: strong uptrend + 120d momo>20% + pulled back 2-6% from 5d high + RSI 55-72
    setup = ((c > sma50) & (sma50 > sma200) & (m120 > 0.20) &
             (c/hi5 - 1 < -0.02) & (c/hi5 - 1 > -0.06) & (rsi > 55) & (rsi < 72))
    fwd1 = c.shift(-1) / c - 1
    fwd3 = c.shift(-3) / c - 1
    idx = setup & fwd3.notna()
    hits1 += (fwd1[idx] > 0).sum(); hits3 += (fwd3[idx] > 0).sum()
    r1 += list(fwd1[idx].dropna()); r3 += list(fwd3[idx].dropna())
    n += idx.sum()

r1, r3 = np.array(r1), np.array(r3)
print(f"'Strong uptrend + mild pullback' setup (exactly PSX today), 2010-2026:")
print(f"  matches found: {n:,} across {len(UNIV)} stocks")
print(f"  NEXT DAY  green: {hits1/n*100:.1f}%   mean {r1.mean()*100:+.2f}%   std {r1.std()*100:.2f}%")
print(f"  NEXT 3 DAYS green: {hits3/n*100:.1f}%   mean {r3.mean()*100:+.2f}%   std {r3.std()*100:.2f}%")
print(f"\n  signal (edge) = the {r1.mean()*100:+.2f}% mean tilt.  noise = the {r1.std()*100:.2f}% daily std.")
print(f"  signal-to-noise next day = {r1.mean()/r1.std():.3f}  (edge is ~{abs(r1.mean()/r1.std())*100:.0f}% the size of the randomness)")
