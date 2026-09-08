"""trend_component_ic.py — do the trend components predict forward returns, or did I invent them?

WHY THIS EXISTS. `weekly_swing._trend` blends seven technical components into one score with
weights I chose by judgement:

    w4 0.20 · w12 0.30 · w26 0.15 · MA stack 0.15 · from-52w-high 0.10 · RSI 0.05 · RS 0.15

Nothing justified those numbers. They were picked to make the output look sensible, which is
the definition of fitting a model to the sample you are looking at. This measures each
component's actual information coefficient against forward returns, and asks whether the
hand-weighted blend beats its own parts.

WHAT THIS CAN AND CANNOT SETTLE
===============================
It CAN measure the price-derived components, because price history exists.

It CANNOT measure `flow_lean`, `dp_buy_share`, `short_float_pct` or `insider_open_buys`.
Unusual Whales serves those SAME-DAY only — there is no history to backtest against, which
is exactly why `signal_weights` tiers them "unmeasured" and says they can only be earned
forward. Any claim about their weight is a prior, and this file cannot turn it into evidence.

So this settles roughly half the vote. That is worth knowing precisely rather than assuming.

METHOD
======
  universe     the live 103-name weekly universe
  horizon      5, 10 and 21 trading days forward, which is the holding period
  IC           Spearman rank correlation, cross-sectional, per date, then averaged.
               Cross-sectional is the right frame: the engine ranks names against each
               other on a given day, it does not time one name in isolation.
  splits       three consecutive periods. A component that only works in one is not a
               component, it is a period.
  benchmark    plain 12-week momentum, which is what the composite replaced.

A real cross-sectional IC in equities is 0.02-0.05. Anything above 0.15 in this output is a
bug, not a discovery -- `signal_weights.IC_IMPLAUSIBLE` exists because a calibration file
once carried 0.62.
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)

HORIZONS = (5, 10, 21)
YEARS = "6y"
MIN_NAMES = 20          # a cross-sectional IC on five names is noise


def universe():
    from weekly_swing import UNIVERSE
    return [t for t in UNIVERSE if t not in ("SPY", "IWM")]


def pull(tickers=None, period=YEARS):
    import yfinance as yf
    tickers = tickers or universe()
    raw = yf.download(tickers + ["SPY"], period=period, interval="1d",
                      auto_adjust=True, progress=False, group_by="ticker", threads=True)
    closes, highs, lows = {}, {}, {}
    for tk in tickers + ["SPY"]:
        try:
            s = raw[tk].dropna(how="all").rename(columns=str.lower)
        except KeyError:
            continue
        if len(s) < 300:
            continue
        closes[tk] = s["close"]
        highs[tk] = s["high"]
        lows[tk] = s["low"]
    return pd.DataFrame(closes), pd.DataFrame(highs), pd.DataFrame(lows)


def _rsi(df, n=14):
    d = df.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / (dn + 1e-12))


def components(close):
    """Every component `_trend` uses, as a dict of aligned frames.

    Each is computed the same way the live engine computes it, so the IC measured here is
    the IC of the thing actually being traded rather than of a tidier proxy.
    """
    spy = close["SPY"]
    px = close.drop(columns=["SPY"])

    w4 = px / px.shift(20) - 1
    w12 = px / px.shift(60) - 1
    w26 = px / px.shift(130) - 1
    s50, s200 = px.rolling(50).mean(), px.rolling(200).mean()
    stack = ((px > s50) & (s50 > s200)).astype(float) - ((px < s50) & (s50 < s200)).astype(float)
    hi52 = px.rolling(252).max()
    from_hi = px / hi52 - 1
    rsi = _rsi(px)
    # Stretched cuts both ways: it argues against chasing, not for reversing.
    rsi_signal = pd.DataFrame(0.0, index=rsi.index, columns=rsi.columns)
    rsi_signal[rsi > 75] = -0.6
    rsi_signal[rsi < 25] = 0.6
    spy12 = spy / spy.shift(60) - 1
    rs12 = w12.sub(spy12, axis=0)

    return {
        "w4": np.tanh(w4 * 8), "w12": np.tanh(w12 * 4), "w26": np.tanh(w26 * 2.5),
        "ma_stack": stack,
        "from_hi": ((from_hi + 0.15) / 0.15).clip(-1, 1),
        "rsi": rsi_signal,
        "rs12": np.tanh(rs12 * 6),
        # the benchmark: the raw momentum the composite replaced
        "_raw_w12": w12,
    }


# The live weights, so the composite measured here is the one actually shipping.
LIVE_WEIGHTS = {"w4": 0.20, "w12": 0.30, "w26": 0.15, "ma_stack": 0.15,
                "from_hi": 0.10, "rsi": 0.05, "rs12": 0.15}


def composite(comp, weights):
    num = None
    den = 0.0
    for k, w in weights.items():
        if k not in comp or w == 0:
            continue
        c = comp[k].fillna(0.0) * w
        num = c if num is None else num + c
        den += w
    return num / den if den else num


def forward(close, h):
    px = close.drop(columns=["SPY"])
    return px.shift(-h) / px - 1


def ic(signal, fwd, min_names=MIN_NAMES):
    """Mean cross-sectional Spearman IC, its t-stat, and the number of dates used."""
    per_date = []
    idx = signal.index.intersection(fwd.index)
    for d in idx:
        s, f = signal.loc[d], fwd.loc[d]
        m = s.notna() & f.notna()
        if m.sum() < min_names:
            continue
        r = s[m].rank().corr(f[m].rank())
        if pd.notna(r):
            per_date.append(r)
    if len(per_date) < 30:
        return {"n_dates": len(per_date)}
    a = np.asarray(per_date)
    # Dates overlap because the horizon does, so the naive t is inflated. Deflate it by the
    # horizon: an honest standard error on overlapping windows, not a flattering one.
    se = a.std(ddof=1) / np.sqrt(len(a))
    return {"ic": float(a.mean()), "t_naive": float(a.mean() / se),
            "n_dates": len(a), "pos_share": float((a > 0).mean())}


def _t_deflated(res, h):
    if "ic" not in res:
        return None
    return res["t_naive"] / np.sqrt(h)


def run(period=YEARS):
    close, _high, _low = pull(period=period)
    comp = components(close)
    comp["COMPOSITE (live weights)"] = composite(comp, LIVE_WEIGHTS)

    out = {}
    for h in HORIZONS:
        fwd = forward(close, h)
        for name, sig in comp.items():
            out.setdefault(name, {})[h] = ic(sig, fwd)
    return out, close, comp


def splits(close, comp, h=21, n=3):
    """Same ICs, three consecutive periods. A component that works in one is a period."""
    fwd = forward(close, h)
    idx = comp["w12"].dropna(how="all").index
    bounds = np.array_split(idx, n)
    res = {}
    for name, sig in comp.items():
        row = []
        for b in bounds:
            row.append(ic(sig.loc[b], fwd.loc[fwd.index.intersection(b)]))
        res[name] = row
    return res, [(str(b[0].date()), str(b[-1].date())) for b in bounds]


if __name__ == "__main__":
    out, close, comp = run()
    n = close.shape[1] - 1
    print(f"{n} names, {close.index.min().date()} -> {close.index.max().date()}\n")

    print("CROSS-SECTIONAL IC vs FORWARD RETURN  (t deflated by sqrt(horizon) for overlap)")
    print(f"{'component':<26}" + "".join(f"{'IC@'+str(h):>10}{'t':>7}" for h in HORIZONS))
    order = list(LIVE_WEIGHTS) + ["_raw_w12", "COMPOSITE (live weights)"]
    for name in order:
        cells = ""
        for h in HORIZONS:
            r = out.get(name, {}).get(h, {})
            if "ic" not in r:
                cells += f"{'—':>10}{'':>7}"
            else:
                cells += f"{r['ic']:>+10.4f}{_t_deflated(r, h):>+7.1f}"
        w = LIVE_WEIGHTS.get(name)
        tag = f"  (w={w:.2f})" if w else ("  (benchmark)" if name == "_raw_w12" else "")
        print(f"{name:<26}{cells}{tag}")

    print("\nTHREE CONSECUTIVE SPLITS, 21-day horizon")
    sp, bounds = splits(close, comp)
    print(f"{'component':<26}" + "".join(f"{a[:7]+'..'+b[2:7]:>18}" for a, b in bounds))
    for name in order:
        row = ""
        for r in sp.get(name, []):
            row += (f"{'—':>18}" if "ic" not in r
                    else f"{r['ic']:>+11.4f} t{_t_deflated(r, 21):>+5.1f}")
        print(f"{name:<26}{row}")
