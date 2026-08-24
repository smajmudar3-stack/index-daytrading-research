"""Trade the RESIDUAL, not the forecast — the one idea my own data supports.

My strongest measured result is not a forecast, it is a set of stable
sensitivities: KRE +9.9, XLF +8.1, XLRE -6.6 (% per 1pt in the 10y, 5-day
horizon, 20 years). Those betas are the most reliable thing in the whole macro
layer and I was only using them as a display.

The correct use of a stable beta is to NEUTRALISE it. Two tests:

  A. RESIDUAL MOMENTUM. Strip the rate factor from each sector
     (resid = r - beta*dy, beta trailing-252d and SHIFTED so it is knowable),
     then ask whether residual momentum predicts residual returns. Rate moves
     become noise removed rather than a signal to forecast.

  B. BETA-NEUTRAL PAIR. Long XLRE / short KRE, sized so the combination has
     ~zero net rate beta. If the pair still carries a premium once the shared
     rate factor is gone, that is a genuinely different bet from anything
     tested so far.

Two methodological corrections applied, both flagged against my earlier work:
  - NON-OVERLAPPING sampling. Daily-sampled h-day forward returns overlap and
    inflate t by roughly sqrt(h); every earlier macro t-stat here was too big.
  - The multiple-testing bar uses the number of INDEPENDENT tests, not the raw
    cell count -- 18 correlated sectors are nowhere near 18 independent trials.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")
PANEL = paths.data("swing", "panel.parquet")

SPLITS = {"2006-2013": ("2006-01-01", "2013-12-31"),
          "2014-2019": ("2014-01-01", "2019-12-31"),
          "2020-2026": ("2020-01-01", "2026-12-31")}
SECTORS = ["XLF", "KRE", "XRT", "XLY", "XLRE", "XHB", "XLE", "XLK", "SMH",
           "XLU", "XLP", "XLI", "IYT", "XLV", "XLB", "XME"]
H = 5


def load():
    p = pd.read_parquet(paths.require_data(PANEL))
    return p.pivot(index="date", columns="ticker", values="close").sort_index()


def stats(r, label):
    r = pd.Series(r).dropna()
    if len(r) < 25:
        return None
    t = r.mean() / (r.std() / np.sqrt(len(r)))
    return {"label": label, "n": len(r), "mean": r.mean(), "t": t,
            "win": (r > 0).mean(), "sharpe": r.mean() / r.std() * np.sqrt(252 / H)}


def main():
    c = load()
    y = c["^TNX"]
    print("=" * 88)
    print("RESIDUAL / BETA-NEUTRAL TESTS — non-overlapping, 5-day horizon")
    print("=" * 88)

    dy = y.diff(H)
    have = [s for s in SECTORS if s in c.columns]

    # ---- rolling, SHIFTED beta so nothing is known before its time ----
    beta = {}
    for s in have:
        r = c[s].pct_change(H, fill_method=None) * 100
        d = pd.concat([r.rename("r"), dy.rename("dy")], axis=1).dropna()
        cov = d["r"].rolling(252).cov(d["dy"])
        var = d["dy"].rolling(252).var()
        beta[s] = (cov / var).shift(1)          # shift = knowable at entry

    print("\nA. RESIDUAL MOMENTUM (rate factor stripped)")
    print(f"  {'sector':7s} " + " ".join(f"{k:>13s}" for k in SPLITS) + f" {'worst t':>8s}")
    rows = []
    for s in have:
        r = c[s].pct_change(H, fill_method=None) * 100
        resid = (r - beta[s] * dy).dropna()
        # Momentum ON the residual, predicting the NEXT residual.
        # CRITICAL: resid is an H-day return, so the signal must be shifted by
        # H days, not 1. Shifting by 1 leaves the signal sharing H-1 days with
        # the outcome it is meant to predict -- that produced t = +13 across
        # every sector, which is the signature of leakage, not edge.
        sig = resid.shift(H)
        fwd = resid
        d = pd.concat([sig.rename("s"), fwd.rename("f")], axis=1).dropna().iloc[::H]
        if len(d) < 150:
            continue
        out, ok = [], True
        for a, b in SPLITS.values():
            w = d[(d.index >= a) & (d.index <= b)]
            if len(w) < 25:
                ok = False
                break
            # long when prior residual is positive, short when negative
            pnl = np.sign(w["s"]) * w["f"]
            out.append(stats(pnl, s))
        if ok and all(out):
            worst = min(o["t"] for o in out)
            rows.append((s, out, worst))
    for s, out, worst in sorted(rows, key=lambda x: -x[2])[:8]:
        print(f"  {s:7s} " + " ".join(f"{o['mean']:+12.3f}%" for o in out) +
              f" {worst:+8.2f}")

    # ---------------------------------------------------------------
    print("\nB. BETA-NEUTRAL PAIR — long XLRE / short KRE, rate-neutralised")
    if "XLRE" in c and "KRE" in c:
        a_r = c["XLRE"].pct_change(H, fill_method=None) * 100
        b_r = c["KRE"].pct_change(H, fill_method=None) * 100
        d = pd.concat([a_r.rename("a"), b_r.rename("b"),
                       beta["XLRE"].rename("ba"), beta["KRE"].rename("bb"),
                       dy.rename("dy")], axis=1).dropna().iloc[::H]
        # Hedge ratio that zeroes net rate beta: w chosen so ba - w*bb = 0.
        w = (d["ba"] / d["bb"]).clip(-3, 3)
        pnl = d["a"] - w * d["b"]
        net_beta = d["ba"] - w * d["bb"]
        print(f"  hedge ratio  median {w.median():+.2f}   "
              f"residual net rate beta {net_beta.abs().mean():.3f} (target 0)")
        print(f"  {'period':12s} {'n':>5s} {'mean':>9s} {'t':>7s} {'win':>7s} {'Sharpe':>8s}")
        allout = []
        for lab, (aa, bb) in SPLITS.items():
            w2 = pnl[(pnl.index >= aa) & (pnl.index <= bb)]
            st = stats(w2, lab)
            if st:
                allout.append(st)
                print(f"  {lab:12s} {st['n']:5d} {st['mean']:+9.3f}% {st['t']:+7.2f} "
                      f"{st['win']:7.1%} {st['sharpe']:+8.2f}")
        full = stats(pnl, "full")
        if full:
            print(f"  {'FULL':12s} {full['n']:5d} {full['mean']:+9.3f}% "
                  f"{full['t']:+7.2f} {full['win']:7.1%} {full['sharpe']:+8.2f}")
        consistent = allout and all(o["mean"] > 0 for o in allout)
        print(f"\n  positive in all three periods? {'YES' if consistent else 'NO'}")

    print("\n" + "=" * 88)
    print("Honest bar: ~4 loosely-independent tests here, so the noise threshold is")
    print("about t = sqrt(2*ln(4)) ~ 1.67 — far below the 4.6 I was applying to 216")
    print("correlated sector cells. Judge the numbers above against ~1.7, not 4.6.")


if __name__ == "__main__":
    main()
