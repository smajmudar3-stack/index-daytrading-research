"""Exhaustive intraday pattern/indicator scan on 2y of 5-min bars (SPY/QQQ = 0DTE underlying).
Tests the toolkit day-traders actually use — EMA crosses, VWAP, RSI, MACD, Bollinger,
breakouts, momentum, candles — measuring forward returns (net of costs) with t-stats so we
keep only what's statistically real, not noise. Directional edge here = a tradeable 0DTE signal.

For each signal we take the trade in its intended direction and measure the move over the next
30min / 60min / to-the-close. |t|>=2 and consistent across horizons = a real candidate.
"""
import glob
import numpy as np
import pandas as pd

from idt import paths

RT = 0.0003  # 3 bps round trip on the underlying


def load5(tk):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(paths.require_data("minute", tk) + "/*.parquet"))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "16:00")
    o = df["open"].resample("5min").first(); h = df["high"].resample("5min").max()
    l = df["low"].resample("5min").min(); c = df["close"].resample("5min").last()
    v = df["volume"].resample("5min").sum()
    b = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "vol": v}).dropna()
    b = b.between_time("09:30", "15:59")
    b["day"] = b.index.date
    return b


def indicators(b):
    c = b["close"]
    b["ema9"] = c.ewm(span=9, adjust=False).mean()
    b["ema21"] = c.ewm(span=21, adjust=False).mean()
    b["ema50"] = c.ewm(span=50, adjust=False).mean()
    d = c.diff()
    for n in (2, 14):
        up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
        b[f"rsi{n}"] = 100 - 100/(1 + up/(dn+1e-12))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    b["macd"] = macd; b["macd_sig"] = macd.ewm(span=9, adjust=False).mean()
    ma20 = c.rolling(20).mean(); sd20 = c.rolling(20).std()
    b["bb_up"] = ma20 + 2*sd20; b["bb_dn"] = ma20 - 2*sd20
    tr = pd.concat([b["high"]-b["low"], (b["high"]-c.shift()).abs(), (b["low"]-c.shift()).abs()], axis=1).max(axis=1)
    b["atr"] = tr.rolling(14).mean()
    # session VWAP (resets daily)
    tp = (b["high"]+b["low"]+b["close"])/3
    b["vwap"] = (tp*b["vol"]).groupby(b["day"]).cumsum() / b["vol"].groupby(b["day"]).cumsum()
    return b


def fwd(b, bars):
    """forward return over `bars` 5-min bars, capped at the session close (EOD-aware)."""
    c = b["close"]
    f = c.shift(-bars)/c - 1
    # zero out where the horizon crosses into the next day
    same = b["day"].values == pd.Series(b["day"]).shift(-bars).values
    return f.where(same)


def eod(b):
    close_of_day = b.groupby("day")["close"].transform("last")
    return close_of_day / b["close"] - 1


def test(name, sig, direction, b, F30, F60, FE):
    """sig=boolean entries; direction=+1 long/-1 short. report net expectancy + t across horizons."""
    m = sig.fillna(False).values
    if m.sum() < 30:
        return None
    out = {"name": name, "n": int(m.sum())}
    for lbl, F in [("30m", F30), ("60m", F60), ("EOD", FE)]:
        r = (direction * F[m] - RT).dropna()
        if len(r) < 20:
            out[lbl] = (0, 0, 0); continue
        t = r.mean()/(r.std()/np.sqrt(len(r))) if r.std() > 0 else 0
        out[lbl] = (r.mean()*100, t, (r > 0).mean()*100)
    return out


def run(tk):
    b = indicators(load5(tk))
    F30, F60, FE = fwd(b, 6), fwd(b, 12), eod(b)
    c = b["close"]
    x = lambda s: s & ~s.shift(1).fillna(False)  # rising-edge (new signal only)
    sigs = [
        ("EMA9>21 cross", x(b.ema9 > b.ema21), +1),
        ("EMA9<21 cross (short)", x(b.ema9 < b.ema21), -1),
        ("price cross >VWAP", x(c > b.vwap), +1),
        ("price cross <VWAP (short)", x(c < b.vwap), -1),
        ("above VWAP & ema9>21 (trend long)", x((c > b.vwap) & (b.ema9 > b.ema21)), +1),
        ("RSI14 cross up 30", x(b.rsi14 > 30) & (b.rsi14.shift(1) <= 30), +1),
        ("RSI14 cross dn 70 (short)", x(b.rsi14 < 70) & (b.rsi14.shift(1) >= 70), -1),
        ("RSI14>70 fade (short)", x(b.rsi14 > 70), -1),
        ("RSI14<30 bounce (long)", x(b.rsi14 < 30), +1),
        ("MACD bull cross", x(b.macd > b.macd_sig), +1),
        ("MACD bear cross (short)", x(b.macd < b.macd_sig), -1),
        ("close < lower BB (mean-rev long)", x(c < b.bb_dn), +1),
        ("close > upper BB (breakout long)", x(c > b.bb_up), +1),
        ("close > upper BB (fade short)", x(c > b.bb_up), -1),
        ("break 12-bar high (momentum)", x(c > b.high.rolling(12).max().shift(1)), +1),
        ("break 12-bar low (short)", x(c < b.low.rolling(12).min().shift(1)), -1),
        ("3 up bars (momentum)", x((c > c.shift(1)) & (c.shift(1) > c.shift(2)) & (c.shift(2) > c.shift(3))), +1),
        ("3 down bars (reversal long)", x((c < c.shift(1)) & (c.shift(1) < c.shift(2)) & (c.shift(2) < c.shift(3))), +1),
        ("bullish engulf", x((c > b.open.shift(1).where(b.open.shift(1) > c.shift(1), b.close.shift(1))) & (c > b.open) & (b.close.shift(1) < b.open.shift(1)) & (b.open < b.close.shift(1)) & (c > b.open.shift(1))), +1),
        ("above ema50 & pullback to ema9 (long)", x((c > b.ema50) & (b.low <= b.ema9) & (c > b.ema9)), +1),
    ]
    rows = [r for r in (test(n, s, d, b, F30, F60, FE) for n, s, d in sigs) if r]
    print(f"\n===== {tk} — intraday 5-min signals ({b['day'].nunique()} sessions) =====")
    print(f"  {'signal':40} {'n':>5}   30m:ret/t/win     60m:ret/t/win     EOD:ret/t/win")
    def keyf(r): return max(abs(r['30m'][1]), abs(r['60m'][1]), abs(r['EOD'][1]))
    for r in sorted(rows, key=keyf, reverse=True):
        def f(h): return f"{r[h][0]:+.3f}/{r[h][1]:+.1f}/{r[h][2]:.0f}"
        flag = " <== |t|>2" if keyf(r) >= 2 else ""
        print(f"  {r['name']:40} {r['n']:>5}   {f('30m'):>16} {f('60m'):>16} {f('EOD'):>16}{flag}")


def main():
    for tk in ["SPY", "QQQ"]:
        run(tk)


if __name__ == "__main__":
    main()
