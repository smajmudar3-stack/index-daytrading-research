"""Find MULTIPLE real index edges, measure their correlation, and merge the uncorrelated
winners into one system. Tradeable via MES/MNQ or SPY/QQQ. 2005-2026, realistic costs.

Edges tested (each a daily return stream so they can be combined as a portfolio):
  E1 OVERNIGHT drift, trend+vol filtered   (close->open; the anchor edge)
  E2 RSI-2 DIP-BUY in uptrend (Connors)     (buy oversold close>200sma, exit on RSI recovery)
  E3 INTRADAY after a down-gap              (open->close on days that gapped down in uptrend)
  E4 daily TREND-follow                      (hold when close>50>200; else flat)
The point: if E1..E4 are weakly correlated, the equal-risk MERGE has a much higher Sharpe
than any single one (diversification = the one free lunch).
"""
import numpy as np
import pandas as pd
import yfinance as yf

COST = 0.0001


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up/(dn+1e-12))


def sh(r):
    r = r.dropna()
    return r.mean()/r.std()*np.sqrt(252) if len(r) > 20 and r.std() > 0 else 0


def load(tk):
    d = yf.download(tk, start="2005-01-01", interval="1d", progress=False, auto_adjust=False,
                    multi_level_index=False).rename(columns=str.lower)
    vix = yf.download("^VIX", start="2005-01-01", progress=False, auto_adjust=False,
                      multi_level_index=False).rename(columns=str.lower)["close"]
    d["overnight"] = d["open"]/d["close"].shift(1) - 1
    d["intraday"] = d["close"]/d["open"] - 1
    d["ret"] = d["close"].pct_change()
    d["sma200"] = d["close"].rolling(200).mean()
    d["sma50"] = d["close"].rolling(50).mean()
    d["above200"] = d["close"] > d["sma200"]
    d["rsi2"] = rsi(d["close"], 2)
    d["vix"] = vix.reindex(d.index).ffill()
    d["vixma"] = d["vix"].rolling(20).mean()
    return d.dropna()


def build(tk):
    d = load(tk)
    # E1 overnight trend+vol
    m1 = d["above200"] & (d["vix"] < d["vixma"]*1.2)
    e1 = pd.Series(np.where(m1, d["overnight"] - COST, 0.0), index=d.index)
    # E2 RSI-2 dip buy in uptrend: in-position while rsi2<60 after an rsi2<10 trigger, above 200sma
    e2 = np.zeros(len(d)); inpos = False
    r2 = d["rsi2"].to_numpy(); a200 = d["above200"].to_numpy(); rr = d["ret"].to_numpy()
    for i in range(1, len(d)):
        if not inpos and r2[i-1] < 10 and a200[i-1]:
            inpos = True
        elif inpos and (r2[i-1] > 60 or not a200[i-1]):
            inpos = False
        e2[i] = (rr[i] - COST) if inpos else 0.0
    e2 = pd.Series(e2, index=d.index)
    # E3 intraday on days that gapped down (>-0.3%) while in uptrend -> fade the gap (long intraday)
    m3 = d["above200"] & (d["overnight"] < -0.003)
    e3 = pd.Series(np.where(m3, d["intraday"] - COST, 0.0), index=d.index)
    # E4 daily trend follow
    m4 = (d["close"] > d["sma50"]) & (d["sma50"] > d["sma200"])
    e4 = pd.Series(np.where(m4.shift(1).fillna(False), d["ret"] - COST*0.1, 0.0), index=d.index)
    return pd.DataFrame({"E1_overnight": e1, "E2_rsi2dip": e2, "E3_gapfade": e3, "E4_trend": e4})


def main():
    for tk in ["SPY", "QQQ"]:
        E = build(tk)
        print(f"\n===== {tk} — individual edges =====")
        for c in E.columns:
            r = E[c]
            cagr = (1+r).prod()**(252/len(r)) - 1
            dd = ((1+r).cumprod()/(1+r).cumprod().cummax()-1).min()
            print(f"  {c:14} Sharpe {sh(r):+5.2f}  CAGR {cagr*100:+6.2f}%  maxDD {dd*100:6.1f}%  "
                  f"exp {(r!=0).mean()*100:3.0f}%")
        print("  correlation matrix:")
        corr = E[E.columns].corr()
        print(corr.round(2).to_string().replace("\n", "\n    "))
        # equal-risk merge: scale each to same vol, average
        vols = E.std().replace(0, np.nan)
        w = (1/vols)/(1/vols).sum()
        merged = (E * w).sum(axis=1)
        cagr = (1+merged).prod()**(252/len(merged)) - 1
        dd = ((1+merged).cumprod()/(1+merged).cumprod().cummax()-1).min()
        print(f"  >>> MERGED (equal-risk): Sharpe {sh(merged):+.2f}  CAGR {cagr*100:+.1f}%  maxDD {dd*100:.1f}%")


if __name__ == "__main__":
    main()
