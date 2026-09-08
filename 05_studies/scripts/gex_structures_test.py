"""Are gamma-conditioned condors and straddles actually positive?

The range read is real: realised/implied comes in at 0.843x on high-gamma days
and 1.139x on low-gamma days, t = -13.2. The question this settles is whether
that converts into a profitable STRUCTURE at real prices, which is a different
claim and the one that matters.

Every combination is tested: 4 structures x 5 gamma quintiles x 5 entry times,
on 1,919 sessions of real SPXW bid/ask.

FILLS. Sold legs fill at the BID, bought legs at the ASK, in both directions.
Mid-price fills are what produced this repo's retracted "+3.7% per trade,
VALIDATED & ROBUST" condor, and re-running that same structure on these quotes
is part of the point.

SETTLEMENT. 0DTE, held to the 16:00 cash settle, so the exit is intrinsic value
and costs nothing. There is no exit spread to argue about and no survivorship
filter: a leg that finishes worthless is worth zero and stays in the sample.

GAMMA. Computed from the panel's own oi_gamma at the 10:00 snapshot, signed
calls-minus-puts, then split into quintiles across the full history. This is a
0DTE net gamma, not the full surface -- stated because it is a real limitation,
not a footnote.

DENOMINATOR. Credit structures are reported on capital at risk (width minus
credit). Debit structures are reported on premium paid. Reporting a credit
structure on premium received is how a strangle once showed +800%/yr here.
"""
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")

ENTRIES = ["10:00:00", "10:30:00", "11:00:00", "11:30:00", "12:00:00"]
WING = 0.010          # condor/butterfly wing, as a fraction of spot
SHORT_OTM = 0.005     # condor short strikes, as a fraction of spot


def load():
    d = pd.read_parquet(SPXW, columns=[
        "quote_date", "quote_time", "option_type", "mnes_rel", "mid", "bas",
        "oi_gamma", "active_underlying_price"])
    d["quote_date"] = pd.to_datetime(d["quote_date"])
    # mid and bas are FRACTIONS OF SPOT in this panel, not dollars.
    d["px"] = d.mid * d.active_underlying_price
    d["half"] = d.bas * d.active_underlying_price / 2.0
    d["ask"] = d.px + d.half
    d["bid"] = (d.px - d.half).clip(lower=0.0)
    d["k"] = d.mnes_rel * d.active_underlying_price     # strike in index points
    return d


def gamma_quintiles(d):
    snap = d[d.quote_time == pd.Timestamp("10:00").time()]
    sgn = np.where(snap.option_type.values == "C", 1.0, -1.0)
    g = snap.assign(g=snap.oi_gamma.values * sgn).groupby("quote_date")["g"].sum()
    return pd.qcut(g, 5, labels=False, duplicates="drop") + 1


def leg(chain, target_k, want):
    """Nearest listed strike to target, and its fill price on the right side."""
    if chain.empty:
        return None
    i = (chain.k - target_k).abs().idxmin()
    r = chain.loc[i]
    if abs(r.k - target_k) > 0.02 * r.active_underlying_price:
        return None
    return {"k": float(r.k), "fill": float(r.bid if want == "sell" else r.ask)}


def settle(d):
    """Underlying at the 16:00 snapshot, per day."""
    s = d[d.quote_time == pd.Timestamp("16:00").time()]
    return s.groupby("quote_date")["active_underlying_price"].median()


def main():
    d = load()
    q = gamma_quintiles(d)
    close = settle(d)
    print(f"  {d.quote_date.nunique():,} sessions, {len(d):,} quotes")
    print(f"  gamma quintiles on {len(q):,} days, settle on {len(close):,}\n")

    rows = []
    for entry in ENTRIES:
        t = pd.Timestamp(entry).time()
        snap = d[d.quote_time == t]
        for day, g in snap.groupby("quote_date"):
            if day not in q.index or day not in close.index:
                continue
            spot = float(g.active_underlying_price.median())
            sT = float(close[day])
            calls, puts = g[g.option_type == "C"], g[g.option_type == "P"]
            if calls.empty or puts.empty:
                continue
            qq = int(q[day])

            atm_c = leg(calls, spot, "sell")
            atm_p = leg(puts, spot, "sell")
            sc = leg(calls, spot * (1 + SHORT_OTM), "sell")
            sp = leg(puts, spot * (1 - SHORT_OTM), "sell")
            lc = leg(calls, spot * (1 + SHORT_OTM + WING), "buy")
            lp = leg(puts, spot * (1 - SHORT_OTM - WING), "buy")
            b_c = leg(calls, spot, "buy")
            b_p = leg(puts, spot, "buy")
            l_c = leg(calls, spot * (1 + SHORT_OTM), "buy")
            l_p = leg(puts, spot * (1 - SHORT_OTM), "buy")

            def payoff(k, kind):
                return max(0.0, sT - k) if kind == "C" else max(0.0, k - sT)

            # iron condor -- credit, on capital at risk
            if all([sc, sp, lc, lp]):
                cr = sc["fill"] + sp["fill"] - lc["fill"] - lp["fill"]
                width = max(lc["k"] - sc["k"], sp["k"] - lp["k"])
                pnl = cr - payoff(sc["k"], "C") - payoff(sp["k"], "P") \
                         + payoff(lc["k"], "C") + payoff(lp["k"], "P")
                risk = width - cr
                if risk > 0:
                    rows.append(("iron condor", entry, qq, pnl / risk))

            # iron butterfly -- credit, on capital at risk
            if all([atm_c, atm_p, lc, lp]):
                cr = atm_c["fill"] + atm_p["fill"] - lc["fill"] - lp["fill"]
                width = max(lc["k"] - atm_c["k"], atm_p["k"] - lp["k"])
                pnl = cr - payoff(atm_c["k"], "C") - payoff(atm_p["k"], "P") \
                         + payoff(lc["k"], "C") + payoff(lp["k"], "P")
                risk = width - cr
                if risk > 0:
                    rows.append(("iron butterfly", entry, qq, pnl / risk))

            # long straddle -- debit, on premium paid
            if b_c and b_p:
                cost = b_c["fill"] + b_p["fill"]
                if cost > 0:
                    pnl = payoff(b_c["k"], "C") + payoff(b_p["k"], "P") - cost
                    rows.append(("long straddle", entry, qq, pnl / cost))

            # long strangle -- debit, on premium paid
            if l_c and l_p:
                cost = l_c["fill"] + l_p["fill"]
                if cost > 0:
                    pnl = payoff(l_c["k"], "C") + payoff(l_p["k"], "P") - cost
                    rows.append(("long strangle", entry, qq, pnl / cost))

    r = pd.DataFrame(rows, columns=["structure", "entry", "quintile", "ret"])
    r.to_parquet(os.path.join(ROOT, "data", "gex_structures.parquet"), index=False)
    n_tests = r.groupby(["structure", "entry", "quintile"]).ngroups
    thr = np.sqrt(2 * np.log(max(n_tests, 2)))

    print("=" * 98)
    print("GAMMA-CONDITIONED STRUCTURES ON REAL SPXW QUOTES")
    print("=" * 98)
    print(f"  {len(r):,} trades · {n_tests} cells · noise threshold |t| = {thr:.2f}\n")

    print("  BY STRUCTURE, ALL GAMMA REGIMES POOLED")
    print(f"  {'structure':16s} {'n':>7s} {'mean':>9s} {'median':>9s} {'win':>7s} {'t':>7s}")
    for s, g in r.groupby("structure"):
        x = g.ret.values
        t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        print(f"  {s:16s} {len(x):7,d} {x.mean()*100:+8.2f}% {np.median(x)*100:+8.2f}% "
              f"{(x > 0).mean()*100:6.1f}% {t:+7.2f}")

    print(f"\n  BY GAMMA QUINTILE  (1 = most positive gamma, 5 = most negative)")
    print(f"  {'structure':16s} " + " ".join(f"{'Q'+str(i):>13s}" for i in range(1, 6)))
    for s, g in r.groupby("structure"):
        cells = []
        for qi in range(1, 6):
            x = g[g.quintile == qi].ret.values
            cells.append(f"{x.mean()*100:+7.2f}% n{len(x):<4d}" if len(x) > 30 else f"{'--':>13s}")
        print(f"  {s:16s} " + " ".join(cells))

    print(f"\n  BEST CELL PER STRUCTURE (any entry, any quintile)")
    print(f"  {'structure':16s} {'entry':9s} {'Q':>2s} {'n':>6s} {'mean':>9s} {'t':>7s}  verdict")
    for s, g in r.groupby("structure"):
        best, bt = None, -99
        for (e, qi), c in g.groupby(["entry", "quintile"]):
            if len(c) < 40:
                continue
            x = c.ret.values
            t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
            if t > bt:
                bt, best = t, (e, qi, len(x), x.mean(), t)
        if best:
            e, qi, n, mu, t = best
            v = "beats noise" if t > thr else "below the noise threshold"
            print(f"  {s:16s} {e:9s} {qi:2d} {n:6d} {mu*100:+8.2f}% {t:+7.2f}  {v}")

    print("\n" + "=" * 98)
    pos = [(s, g.ret.mean()) for s, g in r.groupby("structure") if g.ret.mean() > 0]
    if pos:
        print("  Structures with positive mean, pooled: " +
              ", ".join(f"{s} {m*100:+.2f}%" for s, m in pos))
    else:
        print("  NO structure has a positive mean at any gamma regime.")
    print("  A cell must clear |t| = %.2f to be distinguishable from noise at this" % thr)
    print("  number of tests. Anything below it is what the search itself produces.")
    print("=" * 98)


if __name__ == "__main__":
    main()
