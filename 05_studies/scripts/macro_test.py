"""Does the macro/rates narrative actually predict sector returns at swing horizon?

The desk notes the owner reads make specific, testable claims:
  "If the long end drops, Housing / Real Estate / rate-sensitives catch a bid."
  "Curve steepens (front rallies, back sticky) -> Regionals vulnerable."
  "Weak retail sales -> XRT."

Each is a conditional forecast, so each is checkable. This measures two things
separately, because they are different questions:

  1. SENSITIVITY (beta) — does the sector move WITH rates contemporaneously?
     Almost certainly yes, and it is descriptive, not tradeable.
  2. PREDICTIVENESS — does a rate/curve move TODAY forecast the sector's
     return over the NEXT 5-21 days, beyond what the market already does?

Only (2) is worth trading, and the whole session's evidence says to expect (2)
to be far weaker than (1). Measured against the base rate, three-way split, and
scored against the number of trials.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

PANEL = paths.data("swing", "panel.parquet")

SPLITS = {"2006-2013": ("2006-01-01", "2013-12-31"),
          "2014-2019": ("2014-01-01", "2019-12-31"),
          "2020-2026": ("2020-01-01", "2026-12-31")}

# The sectors the desk notes actually name, plus the standard set.
SECTORS = ["XLF", "KRE", "XRT", "XLY", "XLRE", "ITB", "XHB", "JETS", "XLE",
           "XLK", "SMH", "XLU", "XLP", "XLI", "IYT", "XLV", "XLB", "XME"]

HORIZONS = [5, 10, 21]


def load():
    p = pd.read_parquet(paths.require_data(PANEL))
    c = p.pivot(index="date", columns="ticker", values="close").sort_index()

    m = pd.DataFrame(index=c.index)
    # Rates. ^TNX/^FVX/^IRX quote yields DIRECTLY in percent (yfinance no
    # longer uses the x10 convention) — dividing by 10 made every yield read
    # 10x too small and silently muted the whole macro layer.
    if "^TNX" in c:
        m["y10"] = c["^TNX"]
    if "^FVX" in c:
        m["y5"] = c["^FVX"]
    if "^IRX" in c:
        m["y3m"] = c["^IRX"]
    if "y10" in m and "y3m" in m:
        m["curve"] = m["y10"] - m["y3m"]          # 10y-3m slope
    if "TLT" in c:
        m["tlt"] = c["TLT"]
    # Credit: HYG vs duration-matched Treasury = risk appetite.
    if "HYG" in c and "IEF" in c:
        m["credit"] = c["HYG"] / c["IEF"]
    return c, m


def main():
    c, m = load()
    print("=" * 92)
    print("DOES THE MACRO NARRATIVE PREDICT SECTORS? (swing horizon, 3-way split)")
    print("=" * 92)
    print(f"  {c.index[0].date()} -> {c.index[-1].date()}   "
          f"macro series: {', '.join(m.columns)}")

    # Signals, all past-only: a 5-day CHANGE known at yesterday's close.
    sig = pd.DataFrame(index=c.index)
    if "y10" in m:
        sig["long_end_down"] = -(m.y10 - m.y10.shift(5))     # yields falling
    if "curve" in m:
        sig["curve_steepen"] = m.curve - m.curve.shift(5)
    if "credit" in m:
        sig["credit_improve"] = m.credit.pct_change(5, fill_method=None)
    if "tlt" in m:
        sig["tlt_up"] = m.tlt.pct_change(5, fill_method=None)
    sig = sig.shift(1)

    have = [s for s in SECTORS if s in c.columns]
    rows = []
    for h in HORIZONS:
        for sname in sig.columns:
            s = sig[sname]
            # Trade only the decisive quintile of the signal.
            hi = s > s.rolling(252, min_periods=126).quantile(0.80)
            for sec in have:
                fwd = c[sec].shift(-h) / c[sec] - 1.0
                rec = {"signal": sname, "sector": sec, "horizon": h}
                ok = True
                for lab, (a, b) in SPLITS.items():
                    win = (c.index >= a) & (c.index <= b)
                    f_all = fwd[win].dropna()
                    f_sig = fwd[win & hi.fillna(False)].dropna()
                    if len(f_sig) < 40 or len(f_all) < 200:
                        ok = False
                        break
                    # EXCESS over the sector's own unconditional drift. Beating
                    # zero is not an edge -- equities drift up.
                    rec[f"{lab}_exc"] = f_sig.mean() - f_all.mean()
                    rec[f"{lab}_t"] = ((f_sig.mean() - f_all.mean())
                                       / (f_sig.std() / np.sqrt(len(f_sig))))
                    rec[f"{lab}_n"] = len(f_sig)
                if ok:
                    rows.append(rec)

    res = pd.DataFrame(rows)
    if res.empty:
        print("\n  insufficient overlapping data")
        return

    labs = list(SPLITS)
    res["all_pos"] = np.logical_and.reduce([res[f"{l}_exc"] > 0 for l in labs])
    res["min_t"] = res[[f"{l}_t" for l in labs]].min(axis=1)
    res["avg_exc"] = res[[f"{l}_exc" for l in labs]].mean(axis=1)

    n_trials = len(res)
    bar = np.sqrt(2 * np.log(max(n_trials, 2)))
    print(f"\n  {n_trials} sector x signal x horizon cells tested")
    print(f"  multiple-testing bar: expected best |t| under the null = {bar:.2f}")

    print("\n" + "=" * 92)
    print("POSITIVE EXCESS RETURN IN ALL THREE PERIODS")
    print("=" * 92)
    surv = res[res.all_pos].sort_values("min_t", ascending=False)
    if surv.empty:
        print("  NONE.")
    else:
        print(f"  {'signal':16s} {'sector':7s} {'h':>3s} " +
              " ".join(f"{l:>12s}" for l in labs) + f" {'worst t':>8s}")
        for _, x in surv.head(18).iterrows():
            print(f"  {x['signal']:16s} {x['sector']:7s} {int(x['horizon']):3d} " +
                  " ".join(f"{x[f'{l}_exc']:+11.2%}" for l in labs) +
                  f" {x['min_t']:+8.2f}")
        clears = surv[surv.min_t > bar]
        print(f"\n  of {len(surv)} consistent cells, {len(clears)} clear the "
              f"multiple-testing bar of {bar:.2f}")

    print("\n" + "=" * 92)
    print("CONTEMPORANEOUS SENSITIVITY (descriptive — what moves WITH rates)")
    print("  This is real and useful for context. It is NOT a forecast.")
    print("=" * 92)
    if "y10" in m:
        dy = m.y10.diff()
        print(f"  {'sector':8s} {'beta to 10y yield chg':>24s} {'corr':>8s}")
        betas = []
        for sec in have:
            r = c[sec].pct_change(fill_method=None)
            d = pd.concat([r, dy], axis=1).dropna()
            if len(d) < 500:
                continue
            b = np.polyfit(d.iloc[:, 1], d.iloc[:, 0], 1)[0]
            betas.append((sec, b, d.corr().iloc[0, 1]))
        for sec, b, cr in sorted(betas, key=lambda x: x[1]):
            print(f"  {sec:8s} {b:+24.3f} {cr:+8.2f}")


if __name__ == "__main__":
    main()
