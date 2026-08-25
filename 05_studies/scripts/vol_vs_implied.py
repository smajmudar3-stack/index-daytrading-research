"""HAR predicts volatility. Does it predict anything the OPTION MARKET does not?

R2 of 39.8% for realized volatility is real, but it is not by itself a trade.
Options are priced off implied volatility, so the only question that pays is
whether a forecast contains information the market has not already put in the
price.

The test is an encompassing regression:

    log RV_{t+1} = a + b * log IV_t + c * HAR_forecast_t

  c ~ 0   -> VIX already contains everything HAR knows. No trade.
  c > 0   -> HAR has orthogonal information the market has not priced.

Then the economics, which is a separate question from the statistics:

  VRP = IV^2 - RV^2, the premium paid for insurance. It is persistently
  positive, which is why selling volatility looks attractive and why every
  credit structure in this repo still lost money after costs. Being right about
  direction of mispricing is not the same as clearing the spread.

VIX is used as the implied benchmark for SPY and VXN for QQQ. Both are 30-day
measures being compared against a 1-day forecast, so they are rescaled to a
daily variance and the horizon mismatch is stated rather than hidden.
"""
import glob
import os

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, "data", "minute")
OPEN_T = pd.Timestamp("09:30").time()
CLOSE_T = pd.Timestamp("16:00").time()
PAIR = {"SPY": "^VIX", "QQQ": "^VXN"}


def realized_vol(sym, bar_min=5):
    df = pd.concat([pd.read_parquet(f)
                    for f in sorted(glob.glob(os.path.join(MIN, sym, "*.parquet")))])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    idx = pd.DatetimeIndex(df.index)
    df = df[(idx.time >= OPEN_T) & (idx.time <= CLOSE_T)]
    px = df["close"].resample(f"{bar_min}min").last().dropna()
    r = np.log(px).diff()
    day = pd.DatetimeIndex(r.index).date
    rv = r.groupby(day).apply(lambda s: np.sum(s.values ** 2))
    cnt = r.groupby(day).size()
    return rv[(cnt >= 50) & (rv > 0)]


def implied_daily_var(tkr):
    v = yf.download(tkr, start="2024-06-01", end="2026-08-20",
                    progress=False, auto_adjust=False)["Close"]
    if isinstance(v, pd.DataFrame):
        v = v.iloc[:, 0]
    v.index = pd.DatetimeIndex(v.index).date
    # VIX is an annualised 30-day vol in percent -> daily variance.
    return (v / 100.0) ** 2 / 252.0


def main():
    print("=" * 94)
    print("DOES THE FORECAST BEAT THE MARKET'S OWN FORECAST?")
    print("=" * 94)

    for sym, vix_t in PAIR.items():
        rv = realized_vol(sym)
        lrv = np.log(rv)
        iv = implied_daily_var(vix_t)

        d = pd.DataFrame({"y": lrv})
        d["x_d"] = lrv.shift(1)
        d["x_w"] = lrv.shift(1).rolling(5).mean()
        d["x_m"] = lrv.shift(1).rolling(22).mean()
        d["liv"] = np.log(iv.reindex(d.index).shift(1))   # yesterday's close
        d = d.dropna()
        if len(d) < 200:
            print(f"\n  {sym}: only {len(d)} usable days"); continue

        # Walk-forward HAR forecast, so the regressor is genuinely out of sample.
        X = np.column_stack([np.ones(len(d)), d.x_d, d.x_w, d.x_m])
        y = d.y.values
        fc = np.full(len(d), np.nan)
        for i in range(150, len(d)):
            b, *_ = np.linalg.lstsq(X[:i], y[:i], rcond=None)
            fc[i] = X[i] @ b
        d["har"] = fc
        s = d.dropna()

        print(f"\n  {sym} vs {vix_t}   n = {len(s)}   "
              f"{min(s.index)} -> {max(s.index)}")

        rv_ann = np.sqrt(np.exp(s.y) * 252) * 100
        iv_ann = np.sqrt(np.exp(s.liv) * 252) * 100
        print(f"    realized  {rv_ann.mean():5.1f}%   implied {iv_ann.mean():5.1f}%"
              f"   variance premium {iv_ann.mean()-rv_ann.mean():+5.1f} vol pts")

        print(f"\n    {'encompassing regression':32s} {'coef':>9s} {'t':>7s}")
        for nm, cols in (("log IV alone", ["liv"]),
                         ("HAR forecast alone", ["har"]),
                         ("BOTH", ["liv", "har"])):
            Z = np.column_stack([np.ones(len(s))] + [s[c].values for c in cols])
            b, *_ = np.linalg.lstsq(Z, s.y.values, rcond=None)
            res = s.y.values - Z @ b
            s2 = res @ res / (len(s) - Z.shape[1])
            se = np.sqrt(np.diag(s2 * np.linalg.inv(Z.T @ Z)))
            r2 = 1 - (res @ res) / np.sum((s.y.values - s.y.mean()) ** 2)
            parts = "  ".join(f"{c}={b[i+1]:+.3f} (t {b[i+1]/se[i+1]:+.2f})"
                              for i, c in enumerate(cols))
            print(f"    {nm:32s} R2 {r2*100:5.1f}%   {parts}")

        # Economic version: does the forecast identify days RV will exceed IV?
        rich = s.har < s.liv          # forecast says realized below implied -> sell vol
        real = s.y < s.liv            # what actually happened
        hit = (rich == real).mean()
        base = max(real.mean(), 1 - real.mean())
        se_hit = np.sqrt(0.25 / len(s)) * 100
        print(f"\n    RV came in BELOW implied on {real.mean()*100:.1f}% of days "
              f"(the variance risk premium)")
        print(f"    forecast direction correct  {hit*100:.1f}% +/- {se_hit:.1f}"
              f"   vs always-say-below {base*100:.1f}%")
        print(f"    -> forecast edge over the constant call: "
              f"{(hit-base)*100:+.1f} points")

    print("\n" + "=" * 94)
    print("  If HAR's coefficient collapses once log IV is included, the market")
    print("  has already priced the forecast and there is nothing to trade.")
    print("=" * 94)


if __name__ == "__main__":
    main()
