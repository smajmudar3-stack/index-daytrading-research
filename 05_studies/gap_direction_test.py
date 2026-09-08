"""gap_direction_test.py — which way does a gap actually pay, and does the volume filter help?

WHY THIS EXISTS. `gap_scanner.py` shipped two setups, both LONG, and claimed "+1.25%/trade
t=6.6" for the gap-and-go in its docstring. That number appears nowhere in `02_findings/`
and has no entry in `docs/VERDICT_LOG.md` — the panel itself says so. This script measures
all four quadrants (gap up / gap down x long / short) on the scanner's own 47-name universe
and settles it.

THE HEADLINE, MEASURED
======================
    gap up >3%,   LONG  open->close   -0.33%/trade   t = -3.52   n = 4,822
    gap down >4%, LONG  open->close   +0.71%/trade   t = +5.04   n = 2,389

The scanner's flagship setup, GAP-AND-GO LONG, is SIGNIFICANTLY NEGATIVE. The down-gap
bounce is real. The panel has been emitting a buy signal on the losing side.

WHERE THE +1.25% CAME FROM: LOOKAHEAD
=====================================
Add the scanner's own RVOL >= 1.5 filter, computed from TODAY'S FULL-DAY VOLUME, and the
gap-up long turns into +1.07%/trade at t = +5.39 — which is essentially the docstring's
claim. But you cannot know today's full-day volume at the open, which is when the trade is
entered. It is not a filter, it is a peek at the answer: conditioning on "today turned out
to be a huge volume day" selects the days that trended, and trending days are exactly the
ones where buying the open pays.

The same filter DESTROYS the one real edge:

    gap down >4%, LONG, no volume filter          +0.71%   t = +5.04   n = 2,389
    gap down >4%, LONG, RVOL >= 1.5 (lookahead)   -0.20%   t = -0.72   n =   916

So the live scanner was doing the wrong thing twice over: requiring a filter that kills the
edge that exists, and using that same filter to manufacture an edge that does not.

IS THERE A SHORT EDGE? NO.
==========================
    gap up >3%,   SHORT  +0.03%/trade  t = +0.35     nothing
    gap down >4%, SHORT  -1.01%/trade  t = -7.16     the mirror of the long

The honest direction set is LONG on down-gaps and STAND ASIDE on up-gaps. Emitting a short
on a t of +0.35 would be inventing a signal to fill a slot, which is the specific failure
this repo exists to document.

ROBUSTNESS
==========
  per year        positive in 5 of 7 (2023 -0.32%, partial 2026 -0.17%)
  train/test      first half +1.03% t=+4.63, second half +0.39% t=+2.27 — degrades,
                  never flips. That is the shape of a real effect, and the same shape the
                  VIX-backwardation survivor shows.
  costs           survives to 50bp round trip (+0.36%, t=+2.57); dead at 100bp
  gap depth       -4 to -6%: +0.51%   -6 to -10%: +1.10%   -10 to -20%: +1.15%
                  beyond -20%: -1.08% (n=64) — catastrophic gaps do NOT bounce

The depth banding is knowable at the open, unlike volume, so it is the conditioner the live
scanner should use.
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")
# Plain conditionals rather than a module-level loop: the `import-time-work` gate forbids
# control flow at import, because a study module that DOES something on import turns
# `import x` into a research run.
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)

COST = 0.0015          # 15bp round trip, the figure the original claim used
YEARS = "6y"

# What the measurement supports, and nothing beyond it.
GAP_DN_MAX = -0.04     # a gap must be at least this deep to qualify
GAP_DN_FLOOR = -0.20   # ...and no deeper: beyond this the bounce reverses
GAP_UP_MIN = 0.03


def universe():
    from gap_scanner import UNIV
    return UNIV


def pull(tickers=None, period=YEARS):
    """Daily bars for the universe, shaped one row per name-day.

    Everything derived here is knowable AT THE OPEN except `rv_full`, which is kept
    deliberately so the lookahead can be demonstrated rather than asserted.
    """
    import yfinance as yf
    tickers = tickers or universe()
    d = yf.download(tickers, period=period, interval="1d", auto_adjust=False,
                    progress=False, group_by="ticker", threads=True)
    rows = []
    for tk in tickers:
        try:
            s = d[tk].dropna(how="all")
        except KeyError:
            continue
        if len(s) < 60:
            continue
        s = s.rename(columns=str.lower)
        prev = s["close"].shift(1)
        # `avgv` uses volume SHIFTED, so it is known before today's bar exists.
        avgv = s["volume"].shift(1).rolling(20).mean()
        rows.append(pd.DataFrame({
            "ticker": tk, "date": s.index,
            "gap": (s["open"] / prev - 1).values,
            "o2c": (s["close"] / s["open"] - 1).values,
            "rv_full": (s["volume"] / avgv).values,     # LOOKAHEAD — kept to show the trap
        }))
    return pd.concat(rows).dropna(subset=["gap", "o2c"])


def stat(r, cost=COST):
    r = np.asarray(r, dtype=float) - cost
    if len(r) < 2:
        return {"n": len(r)}
    se = r.std(ddof=1) / np.sqrt(len(r))
    return {"n": int(len(r)), "mean": float(r.mean()), "t": float(r.mean() / se),
            "ci_lo": float(r.mean() - 1.96 * se), "ci_hi": float(r.mean() + 1.96 * se),
            "win": float((r > 0).mean())}


def quadrants(df):
    """All four (direction x gap sign), with and without the lookahead volume filter."""
    out = {}
    beds = {
        "gap_up": df["gap"] >= GAP_UP_MIN,
        "gap_dn": df["gap"] <= GAP_DN_MAX,
        "gap_up_rvol": (df["gap"] >= GAP_UP_MIN) & (df["rv_full"] >= 1.5),
        "gap_dn_rvol": (df["gap"] <= GAP_DN_MAX) & (df["rv_full"] >= 1.5),
    }
    for name, m in beds.items():
        x = df[m]
        out[f"{name}::long"] = stat(x["o2c"])
        out[f"{name}::short"] = stat(-x["o2c"])
    return out


def robustness(df):
    """Per-year, train/test, cost curve, depth bands, and name concentration."""
    m = (df["gap"] <= GAP_DN_MAX)
    d = df[m].copy()
    d["year"] = pd.to_datetime(d["date"]).dt.year
    d = d.sort_values("date")

    by_year = {int(y): stat(g["o2c"]) for y, g in d.groupby("year")}
    half = len(d) // 2
    splits = {"first_half": stat(d.iloc[:half]["o2c"]),
              "second_half": stat(d.iloc[half:]["o2c"])}
    costs = {f"{int(c*1e4)}bp": stat(d["o2c"], cost=c)
             for c in (0.0015, 0.0030, 0.0050, 0.0100)}
    depth = {}
    for lo, hi in ((-0.06, -0.04), (-0.10, -0.06), (-0.20, -0.10), (-1.0, -0.20)):
        g = d[(d["gap"] > lo) & (d["gap"] <= hi)]
        if len(g) > 40:
            depth[f"({hi*100:+.0f}%,{lo*100:+.0f}%]"] = stat(g["o2c"])

    # CONCENTRATION. An "edge" carried by three meme stocks is a story about three stocks.
    per_name = {tk: stat(g["o2c"]) for tk, g in d.groupby("ticker") if len(g) >= 25}
    pos = sum(1 for v in per_name.values() if v.get("mean", 0) > 0)
    # Drop the single largest contributor and see whether it survives.
    contrib = {tk: v["mean"] * v["n"] for tk, v in per_name.items()}
    top = max(contrib, key=contrib.get) if contrib else None
    without_top = stat(d[d["ticker"] != top]["o2c"]) if top else None

    return {"by_year": by_year, "splits": splits, "costs": costs, "depth": depth,
            "n_names": len(per_name), "n_names_positive": pos,
            "largest_contributor": top, "without_largest": without_top,
            # The band the live scanner should actually trade.
            "tradeable_band": stat(d[(d["gap"] <= GAP_DN_MAX) &
                                     (d["gap"] >= GAP_DN_FLOOR)]["o2c"])}


def _line(label, s):
    if s.get("n", 0) < 2:
        return f"  {label:<40} n={s.get('n', 0):>5}  too few"
    return (f"  {label:<40} n={s['n']:>5}  {s['mean']*100:+6.2f}%  t={s['t']:+6.2f}  "
            f"CI [{s['ci_lo']*100:+5.2f}, {s['ci_hi']*100:+5.2f}]  win {s['win']*100:.0f}%")


if __name__ == "__main__":
    df = pull()
    print(f"{len(df):,} name-days, {df['ticker'].nunique()} names, "
          f"{pd.to_datetime(df['date']).min().date()} -> {pd.to_datetime(df['date']).max().date()}")

    print("\n=== FOUR QUADRANTS (costs 15bp round trip) ===")
    q = quadrants(df)
    for k in ("gap_up::long", "gap_up::short", "gap_dn::long", "gap_dn::short"):
        print(_line(k.replace("::", "  "), q[k]))
    print("\n  --- with RVOL>=1.5 from TODAY'S FULL-DAY volume (LOOKAHEAD) ---")
    for k in ("gap_up_rvol::long", "gap_dn_rvol::long"):
        print(_line(k.replace("::", "  "), q[k]))

    r = robustness(df)
    print("\n=== DOWN-GAP LONG ROBUSTNESS ===")
    for y, s in sorted(r["by_year"].items()):
        print(_line(str(y), s))
    print()
    for k, s in r["splits"].items():
        print(_line(k, s))
    print()
    for k, s in r["costs"].items():
        print(_line(f"cost {k}", s))
    print()
    for k, s in r["depth"].items():
        print(_line(f"gap {k}", s))
    print(f"\n  names with a positive mean: {r['n_names_positive']}/{r['n_names']}")
    print(_line(f"excluding {r['largest_contributor']}", r["without_largest"]))
    print(_line(f"TRADEABLE BAND {GAP_DN_MAX:.0%}..{GAP_DN_FLOOR:.0%}", r["tradeable_band"]))
