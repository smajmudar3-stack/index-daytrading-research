"""intraday_live.py — live intraday pattern scanner for the signal-giver.

Computes which classic day-trader patterns are firing RIGHT NOW on SPY/QQQ 5-min bars, and
stamps each with its HONEST backtested edge (from intraday_patterns.py: all ~zero/negative,
t<0). Purpose: let the user paper-trade them and SEE they're noise — vs the real edges
(overnight, 0DTE premium-sell) shown elsewhere. Writes data/intraday_snapshot.json.

Backtested edge table (EOD horizon, net of costs, 2y 5-min, 500 sessions) — every pattern's
directional expectancy is negative once you pay the spread. 'edge_t' is the t-stat.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf

ET = ZoneInfo("America/New_York")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "intraday_snapshot.json")

# name -> (direction traded, backtested EOD expectancy %, t-stat, win%)  [SPY, representative]
EDGE = {
    "EMA 9/21 bull cross": (+1, +0.00, +0.1, 47),
    "EMA 9/21 bear cross": (-1, -0.045, -1.9, 43),
    "Price > VWAP": (+1, -0.006, -0.4, 49),
    "Price < VWAP": (-1, -0.045, -2.7, 44),
    "RSI-14 < 30 (oversold)": (+1, -0.008, -0.3, 50),
    "RSI-14 > 70 (overbought)": (-1, -0.018, -0.9, 41),
    "MACD bull cross": (+1, -0.007, -0.4, 48),
    "MACD bear cross": (-1, -0.056, -3.3, 41),
    "Break 12-bar high": (+1, -0.044, -3.7, 47),
    "Break 12-bar low": (-1, -0.028, -2.0, 43),
    "Close < lower Bollinger": (+1, -0.026, -1.4, 47),
    "Close > upper Bollinger": (+1, -0.020, -1.2, 45),
    "3 up bars (momentum)": (+1, -0.031, -2.7, 47),
}


def bars5(tk):
    df = yf.download(tk, period="5d", interval="5m", progress=False, auto_adjust=False,
                     multi_level_index=False).rename(columns=str.lower)
    df.index = df.index.tz_convert(ET)
    df = df.between_time("09:30", "16:00")
    df["day"] = df.index.date
    c = df["close"]
    df["ema9"] = c.ewm(span=9, adjust=False).mean(); df["ema21"] = c.ewm(span=21, adjust=False).mean()
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi14"] = 100 - 100/(1 + up/(dn+1e-12))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["macd"] = macd; df["sig"] = macd.ewm(span=9, adjust=False).mean()
    ma = c.rolling(20).mean(); sd = c.rolling(20).std()
    df["bbu"] = ma+2*sd; df["bbl"] = ma-2*sd
    tp = (df["high"]+df["low"]+df["close"])/3
    df["vwap"] = (tp*df["volume"]).groupby(df["day"]).cumsum()/df["volume"].groupby(df["day"]).cumsum()
    return df


def firing(tk):
    df = bars5(tk)
    if len(df) < 30:
        return {"etf": tk, "error": "insufficient bars"}
    a, p = df.iloc[-1], df.iloc[-2]      # current & prior bar
    fires = {
        "EMA 9/21 bull cross": a.ema9 > a.ema21 and p.ema9 <= p.ema21,
        "EMA 9/21 bear cross": a.ema9 < a.ema21 and p.ema9 >= p.ema21,
        "Price > VWAP": a.close > a.vwap and p.close <= p.vwap,
        "Price < VWAP": a.close < a.vwap and p.close >= p.vwap,
        "RSI-14 < 30 (oversold)": a.rsi14 < 30,
        "RSI-14 > 70 (overbought)": a.rsi14 > 70,
        "MACD bull cross": a.macd > a.sig and p.macd <= p.sig,
        "MACD bear cross": a.macd < a.sig and p.macd >= p.sig,
        "Break 12-bar high": a.close > df["high"].iloc[-13:-1].max(),
        "Break 12-bar low": a.close < df["low"].iloc[-13:-1].min(),
        "Close < lower Bollinger": a.close < a.bbl,
        "Close > upper Bollinger": a.close > a.bbu,
        "3 up bars (momentum)": a.close > p.close > df["close"].iloc[-3] > df["close"].iloc[-4],
    }
    out = []
    for name, on in fires.items():
        d, ret, t, win = EDGE[name]
        out.append({"name": name, "firing": bool(on), "dir": "long" if d > 0 else "short",
                    "edge_ret": ret, "edge_t": t, "edge_win": win})
    return {"etf": tk, "price": round(float(a.close), 2), "rsi": round(float(a.rsi14), 0),
            "vs_vwap": "above" if a.close > a.vwap else "below", "patterns": out,
            "n_firing": sum(1 for x in out if x["firing"])}


def run():
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET"),
           "epoch": datetime.now(ET).timestamp(), "scan": []}
    for tk in ["SPY", "QQQ"]:
        try:
            out["scan"].append(firing(tk))
        except Exception as e:
            out["scan"].append({"etf": tk, "error": str(e)[:80]})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    print(f"intraday scan written {out['as_of']}")
    return out


if __name__ == "__main__":
    run()
