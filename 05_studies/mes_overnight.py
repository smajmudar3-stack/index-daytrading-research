"""MES/ES overnight strategy research — build the best HONEST S&P futures edge.

The one real S&P edge (verified this session): the overnight session (RTH close -> next open)
holds the drift; the intraday session is a coin flip that loses to costs. Futures (MES) let
you trade the overnight directly. We enhance it and validate honestly:

  A. raw overnight (long close->open every night)
  B. + TREND filter (only hold overnight when close > 200d SMA -> skip bear-market gap-downs)
  C. + VOL filter (also skip when VIX is spiking / above a threshold)
  D. walk-forward (is the trend filter robust OOS, or fit?)

Costs: MES round trip ~ $1.24 (1 tick slippage) + ~$1 commission ~= $2.5/contract; on ~$37k
notional that's ~0.7 bps. We charge 1 bp/night to be safe. MES = $5 x index point.
"""
import numpy as np
import pandas as pd
import yfinance as yf

COST = 0.0001  # 1 bp per night round trip (generous for MES)


def load():
    spy = yf.download("SPY", start="2005-01-01", interval="1d", progress=False,
                      auto_adjust=False, multi_level_index=False).rename(columns=str.lower)
    vix = yf.download("^VIX", start="2005-01-01", interval="1d", progress=False,
                      auto_adjust=False, multi_level_index=False).rename(columns=str.lower)["close"]
    spy["overnight"] = spy["open"] / spy["close"].shift(1) - 1
    spy["sma200"] = spy["close"].rolling(200).mean()
    spy["above200"] = spy["close"] > spy["sma200"]
    spy["vix"] = vix.reindex(spy.index).ffill()
    spy["vix_ma"] = spy["vix"].rolling(20).mean()
    return spy.dropna()


def stats(name, ret, exposure=None):
    r = ret.dropna()
    if len(r) < 20:
        print(f"  {name:32} n={len(r)}"); return
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (252 / len(r)) - 1
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0
    dd = (eq / eq.cummax() - 1).min()
    exp = f"  exp {exposure*100:3.0f}%" if exposure is not None else ""
    print(f"  {name:32} Sharpe {sharpe:+5.2f}  CAGR {cagr*100:+6.2f}%  maxDD {dd*100:6.1f}%  "
          f"win {(r>0).mean()*100:4.1f}%{exp}")


d = load()
print(f"===== SPY/ES overnight, {d.index.min().date()}..{d.index.max().date()} ({len(d)} nights) =====")
on = d["overnight"]
stats("buy & hold (all day)", d["close"].pct_change())
stats("A. raw overnight (every night)", on - COST)
# B. trend filter
onB = np.where(d["above200"], on - COST, 0.0)
stats("B. overnight ONLY if >200d SMA", pd.Series(onB, index=d.index), d["above200"].mean())
# C. + vol filter (skip when VIX > its 20d avg * 1.3, i.e. vol spiking)
calm = d["above200"] & (d["vix"] < d["vix_ma"] * 1.3)
onC = np.where(calm, on - COST, 0.0)
stats("C. + skip vol spikes", pd.Series(onC, index=d.index), calm.mean())
# also: overnight when BELOW 200 (bear) — should be bad
onbear = np.where(~d["above200"], on - COST, 0.0)
stats("(overnight in downtrends only)", pd.Series(onbear, index=d.index), (~d["above200"]).mean())

# D. walk-forward: the trend filter has no fitted params, but test stability by decade
print("\n  --- strategy B by period (stability) ---")
for lo, hi in [("2005","2010"),("2010","2015"),("2015","2020"),("2020","2026")]:
    seg = d[(d.index >= lo) & (d.index < hi)]
    r = pd.Series(np.where(seg["above200"], seg["overnight"] - COST, 0.0), index=seg.index)
    stats(f"  {lo}-{hi}", r, seg["above200"].mean())

# MES $ translation for strategy B
print("\n  --- MES dollar terms (strategy B, 1 contract) ---")
spx_now = float(d["close"].iloc[-1]) * 10  # SPY*10 ~ SPX; MES = $5 x SPX point
onB_ser = pd.Series(onB, index=d.index)
r = onB_ser[onB_ser != 0]
per_night_pts = onB_ser.mean() * spx_now / 10 * 10  # avg % * SPX level
avg_pt = onB_ser.mean() * spx_now
print(f"  SPX ~{spx_now:.0f}, 1 MES = ${5*spx_now:,.0f} notional, ${5:.0f}/point")
print(f"  avg per-night: {onB_ser.mean()*100:+.3f}% = {onB_ser.mean()*spx_now:+.1f} SPX pts = ${onB_ser.mean()*spx_now*5:+.2f}/contract")
print(f"  nights/yr traded ~{d['above200'].mean()*252:.0f}; est $/yr per MES ~${onB_ser.mean()*spx_now*5*252:+,.0f}")
print(f"  (raw % return {(np.prod(1+onB_ser)**(252/len(onB_ser))-1)*100:+.1f}%/yr on ~${5*spx_now:,.0f} notional)")
