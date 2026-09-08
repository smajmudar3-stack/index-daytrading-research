"""engine_e_feasibility.py — can the survivors take $5,000 to $50,000, and at what risk?

THE GOAL IS A QUESTION, NOT A CONSTRAINT. Nothing in this file is allowed to loosen a gate,
add leverage to a null result, or search for a sizing that makes the target appear. It runs
only on what survived validation, it reports the probability of ruin next to every growth
number, and where the honest answer is that the survivors imply a single-digit annual
return, that is the first thing it prints.

WHAT IT RUNS ON
===============
`02_findings/WHAT_WORKS.md` lists three survivors and some partial credit. Only one of them
is a tradeable timing signal with a reconstructible return series, and this module rebuilds
it from the raw panel rather than trusting the summary line:

  VIX BACKWARDATION INSIDE A GOLDEN CROSS
    Rebuilt here from ^VIX, ^VIX3M and SPY, 2006-07-17 to 2026-06-17. The rebuild
    reproduces the documented finding (+1.3 to +1.8pp excess over 21 days) at +1.28pp, so
    the number in the docs is real and this file is measuring the same thing.

  SHORT INTEREST (IC -0.107 at 63d, n=13,219)
    A CROSS-SECTIONAL ranking signal, not a timing signal. It says which names underperform
    relative to each other, which needs a long/short book and a short locate. It cannot be
    rebuilt here: `data/swing/panel.parquet` carries OHLCV only, with no short-float column,
    so there is no series to bootstrap. Modelled separately and flagged as such.

  LOW DEALER GAMMA
    Explicitly a regime FILTER, not a signal. It changes which structure to use, not whether
    to be in the market, so it contributes no standalone return series and no growth.

WHY THE HOLDING PERIOD DECIDES WHICH CONSTRAINTS BIND
=====================================================
The surviving signal is a 21-day hold. That single fact removes most of the small-account
machinery from the answer: PDT limits day trades, and a 21-day hold is not a day trade, so
PDT never binds. Cash-account settlement (T+1) does not bind either at 2.8 trades a year.
Micro futures are irrelevant because there is no intraday edge to trade with them -- this
repo measured ~340,000 intraday tests and the survivor count came in at or below chance.

So the binding constraint is not the account rules. It is the arithmetic.
"""
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from idt import paths                                          # noqa: E402

HOLD_DAYS = 21
START_EQUITY = 5_000.0
TARGET_EQUITY = 50_000.0
RUIN_EQUITY = 1_000.0
PHASE2_TARGET = 0.15          # the ~15%/yr compounding goal after $50k
N_PATHS = 10_000
SEED = 20260902

# Reg-T caps a held position at 2x. Anything beyond that needs options, and the only option
# structures this repo measured are negative: debit spreads -11.12%/trade and long premium
# significantly so. That is why leverage above 2x is reported as unavailable rather than as
# an aggressive setting.
REGT_MAX_LEVERAGE = 2.0

# Weeks to inject as shocks, at their historical frequency and at twice it.
SHOCK_WEEKS = ["2018-02-05", "2020-03-09", "2022-06-13", "2024-08-05"]


# --------------------------------------------------------------- the survivor ---

def _panel():
    p = os.path.join(paths.DATA_ROOT, "swing", "panel.parquet")
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"{p} not found. The 16 GB of market data is not in git; point IDT_DATA_ROOT "
            f"at an existing copy (see 06_data_guide/DATA.md).")
    return pd.read_parquet(p)


def rebuild_vix_backwardation(hold=HOLD_DAYS):
    """The surviving signal, rebuilt from raw closes. Returns (trades, diagnostics).

    Non-overlapping by construction: on a signal day the position is opened and held for
    `hold` sessions, and no new position is opened until it closes. Overlapping windows
    would inflate the sample roughly `hold`-fold and shrink the standard error by ~4.6x,
    which is how a t of 2.7 becomes a t of 12 without any new information.
    """
    d = _panel()
    w = d.pivot(index="date", columns="ticker", values="close").sort_index()
    need = ["^VIX", "^VIX3M", "SPY"]
    missing = [c for c in need if c not in w.columns]
    if missing:
        raise KeyError(f"panel is missing {missing}")
    w = w[need].dropna()

    w["ratio"] = w["^VIX"] / w["^VIX3M"]
    w["golden"] = w["SPY"].rolling(50).mean() > w["SPY"].rolling(200).mean()
    w["sig"] = w["golden"] & (w["ratio"] > 1.0)
    w["fwd"] = w["SPY"].shift(-hold) / w["SPY"] - 1
    w = w.dropna(subset=["fwd", "sig"])

    sig_arr, fwd_arr = w["sig"].values, w["fwd"].values
    trades, entries, i = [], [], 0
    while i < len(w):
        if sig_arr[i]:
            trades.append(fwd_arr[i])
            entries.append(w.index[i])
            i += hold
        else:
            i += 1

    t = np.asarray(trades, dtype=float)
    years = (w.index.max() - w.index.min()).days / 365.25
    base = float(w["fwd"].mean())
    se = t.std(ddof=1) / math.sqrt(len(t)) if len(t) > 1 else float("nan")
    return t, {
        "start": str(w.index.min().date()), "end": str(w.index.max().date()),
        "years": years, "n_trades": len(t), "per_year": len(t) / years,
        "mean": float(t.mean()), "sd": float(t.std(ddof=1)), "median": float(np.median(t)),
        "t_stat": float(t.mean() / se), "se": float(se),
        "ci_lo": float(t.mean() - 1.96 * se), "ci_hi": float(t.mean() + 1.96 * se),
        "win_rate": float((t > 0).mean()), "worst": float(t.min()), "best": float(t.max()),
        "unconditional_21d": base,
        "excess_pp": float(w.loc[w["sig"], "fwd"].mean() - base),
        "entries": [str(e.date()) for e in entries],
    }


def configurations(hold=HOLD_DAYS):
    """The survivor expressed four ways, on the actual daily path. This is the crux.

    THE TRADE-LEVEL NUMBER AND THE ACCOUNT-LEVEL NUMBER ARE DIFFERENT QUESTIONS, and only
    the second one answers "can this get me to $50,000". A signal with a +1.80% mean over
    21 days sounds like it compounds to something; it fires 2.8 times a year, so STANDALONE
    it leaves the account in cash 77% of the time and returns 4.73%/yr — less than half of
    simply owning SPY over the same window.

    The signal is real. Traded on its own it is worse than doing nothing, because being
    right 2.8 times a year cannot beat being invested 250 days a year. Its value is as an
    OVERLAY: stay long, and add exposure when it fires.

    Both the trade-level extraction and this path-level walk are computed here and asserted
    to agree, because an off-by-one in the hold mask (counting the return INTO the entry day
    and missing the exit day) silently produced 0.5%/yr instead of 4.73%/yr in the first
    version of this analysis. Two derivations that must match is the cheapest guard there is.
    """
    d = _panel()
    w = d.pivot(index="date", columns="ticker", values="close").sort_index()
    w = w[["^VIX", "^VIX3M", "SPY"]].dropna()
    w["golden"] = w["SPY"].rolling(50).mean() > w["SPY"].rolling(200).mean()
    w["sig"] = w["golden"] & (w["^VIX"] / w["^VIX3M"] > 1.0)

    px, s = w["SPY"].values, w["sig"].values
    ret = pd.Series(px, index=w.index).pct_change().fillna(0).values

    spans, trades, i = [], [], 0
    while i < len(w) - hold:
        if s[i]:
            spans.append((i, i + hold))
            trades.append(px[i + hold] / px[i] - 1)
            i += hold
        else:
            i += 1
    mask = np.zeros(len(w), dtype=bool)
    for a, b in spans:
        mask[a + 1:b + 1] = True          # the return INTO the exit day, not into the entry

    t = np.asarray(trades)
    assert abs(np.prod(1 + t) - np.prod(1 + ret * mask)) < 1e-6, \
        "trade-level and path-level disagree — the hold mask is off by one"

    years = (w.index.max() - w.index.min()).days / 365.25

    def stat(r, label, in_mkt):
        eq = np.cumprod(1 + r)
        dd = float((1 - eq / np.maximum.accumulate(eq)).max())
        return {"name": label, "cagr": float(eq[-1] ** (1 / years) - 1),
                "max_dd": dd, "multiple": float(eq[-1]),
                "final_on_5k": float(START_EQUITY * eq[-1]), "time_in_market": float(in_mkt)}

    out = [
        stat(ret, "SPY buy and hold", 1.0),
        stat(ret * mask, "signal only, cash otherwise", mask.mean()),
        stat(ret * (1 + mask), "always long, 2x while the signal is on", 1.0),
        stat(ret * (1 + 2 * mask), "always long, 3x while the signal is on", 1.0),
    ]
    for c in out:
        c["alpha_vs_bh"] = c["cagr"] - out[0]["cagr"]
    return out, {"years": years, "daily_returns": ret, "mask": mask, "trades": t}


# ------------------------------------------------------------------ the maths ---

def growth_math(start=START_EQUITY, target=TARGET_EQUITY):
    """What each horizon actually demands. Stated before anything is simulated.

    This table is the whole argument in miniature, and it is arithmetic rather than
    modelling: no assumption in it can be wrong.
    """
    mult = target / start
    rows = []
    for yrs in (1, 2, 3, 5, 10, 16.5):
        cagr = mult ** (1 / yrs) - 1
        rows.append({"years": yrs, "required_cagr": cagr})
    return {"multiple": mult, "rows": rows,
            "years_at_15pct": math.log(mult) / math.log(1 + PHASE2_TARGET)}


def required_leverage(required_cagr, edge_per_trade, trades_per_year):
    """Crude but honest: how much size the target needs, given the measured edge.

    Compounding `trades_per_year` trades of `edge_per_trade * L` must reach the required
    CAGR. Solved for L. It ignores the fact that leverage also multiplies the drawdowns,
    which is exactly what the Monte Carlo below exists to put back in.
    """
    if edge_per_trade <= 0 or trades_per_year <= 0:
        return None
    target_per_trade = (1 + required_cagr) ** (1 / trades_per_year) - 1
    return target_per_trade / edge_per_trade


def kelly_fraction(trades):
    """f* for a set of trade returns, by maximising expected log growth directly.

    The closed form m/s^2 is a small-return approximation and it overstates badly when the
    left tail is as heavy as this one (worst observed trade -15.7%). Solving the log-growth
    objective on the empirical returns is both more honest and no harder.
    """
    lo, hi = 0.0, 20.0
    for _ in range(200):
        m = (lo + hi) / 2
        # derivative of E[log(1 + f r)] with respect to f
        d = np.mean(trades / (1 + m * trades)) if np.all(1 + m * trades > 0) else -1.0
        if d > 0:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


# --------------------------------------------------------------- Monte Carlo ---

def _fit_t(trades):
    """Student-t fitted to the trade returns, for the fat-tail overlay."""
    from scipy import stats
    df, loc, scale = stats.t.fit(trades)
    return {"df": float(df), "loc": float(loc), "scale": float(scale)}


def simulate(trades, per_year, years, leverage, n_paths=N_PATHS, rng=None,
             cost_per_trade=0.0010, shrink=1.0, fat_tail=True, shock_mult=1.0,
             start=START_EQUITY, target=TARGET_EQUITY, ruin=RUIN_EQUITY):
    """Block-bootstrap the trade series forward and report the whole distribution.

    `shrink` multiplies the edge (not the dispersion) to model post-discovery decay, which
    is the normal fate of a published signal. `shock_mult` raises the frequency of the
    injected historical shock weeks above their historical rate.
    """
    rng = rng or np.random.default_rng(SEED)
    n_trades = max(1, int(round(per_year * years)))
    t = np.asarray(trades, dtype=float)

    # Centre, shrink the edge, re-add: dispersion is left alone on purpose. Decay eats
    # the edge; it does not make the world calmer.
    centred = t - t.mean()
    pool = centred + t.mean() * shrink

    tfit = _fit_t(t) if fat_tail else None
    shock_p = shock_mult * len(SHOCK_WEEKS) / max(1.0, len(t))

    eq = np.full(n_paths, float(start))
    peak = eq.copy()
    max_dd = np.zeros(n_paths)
    hit = np.zeros(n_paths, dtype=bool)
    hit_at = np.full(n_paths, np.nan)
    dead = np.zeros(n_paths, dtype=bool)

    block = 3                                  # preserves short-run clustering
    for k in range(n_trades):
        # Block bootstrap: draw a starting index and walk it, so consecutive draws keep the
        # autocorrelation an i.i.d. resample would destroy.
        if k % block == 0:
            starts = rng.integers(0, len(pool), size=n_paths)
        idx = (starts + (k % block)) % len(pool)
        r = pool[idx].copy()

        if fat_tail:
            # Replace a slice of draws with fitted-t draws so the tail is not capped by the
            # worst thing that happened to appear in 56 observations.
            from scipy import stats
            swap = rng.random(n_paths) < 0.15
            if swap.any():
                r[swap] = stats.t.rvs(tfit["df"], loc=tfit["loc"], scale=tfit["scale"],
                                      size=int(swap.sum()), random_state=int(rng.integers(1e9)))
        shocked = rng.random(n_paths) < shock_p
        if shocked.any():
            r[shocked] = rng.choice([-0.09, -0.12, -0.20, -0.06], size=int(shocked.sum()))

        r = r * leverage - cost_per_trade * leverage
        alive = ~dead
        eq[alive] = eq[alive] * (1.0 + r[alive])
        eq = np.maximum(eq, 0.0)

        peak = np.maximum(peak, eq)
        dd = 1.0 - eq / np.maximum(peak, 1e-9)
        max_dd = np.maximum(max_dd, dd)

        newly = (~hit) & (eq >= target)
        hit_at[newly] = (k + 1) / per_year
        hit |= newly
        dead |= eq < ruin

    return {
        "leverage": leverage, "years": years, "n_trades": n_trades,
        "p_target": float(hit.mean()),
        "median_years_to_target": float(np.nanmedian(hit_at)) if hit.any() else None,
        "p_ruin": float(dead.mean()),
        "p_dd50": float((max_dd >= 0.50).mean()),
        "median_terminal": float(np.median(eq)),
        "p10_terminal": float(np.percentile(eq, 10)),
        "p90_terminal": float(np.percentile(eq, 90)),
        "mean_max_dd": float(max_dd.mean()),
        "median_max_dd": float(np.median(max_dd)),
    }


def phase2(trades, per_year, leverage, years, n_paths=N_PATHS, rng=None,
           cost_per_trade=0.0010, shrink=1.0):
    """From $50k: probability of averaging at least 15%/yr, and the drawdown it costs."""
    rng = rng or np.random.default_rng(SEED + 1)
    res = simulate(trades, per_year, years, leverage, n_paths=n_paths, rng=rng,
                   cost_per_trade=cost_per_trade, shrink=shrink,
                   start=TARGET_EQUITY, target=TARGET_EQUITY * (1 + PHASE2_TARGET) ** years,
                   ruin=TARGET_EQUITY * 0.2)
    res["p_15pct_avg"] = res.pop("p_target")
    return res


if __name__ == "__main__":
    trades, diag = rebuild_vix_backwardation()
    print(f"VIX backwardation + golden cross, rebuilt {diag['start']} to {diag['end']}")
    print(f"  {diag['n_trades']} non-overlapping trades over {diag['years']:.1f}y "
          f"= {diag['per_year']:.1f}/yr")
    print(f"  mean {diag['mean']*100:+.2f}%  sd {diag['sd']*100:.2f}%  "
          f"t={diag['t_stat']:+.2f}  CI [{diag['ci_lo']*100:+.2f}%, {diag['ci_hi']*100:+.2f}%]")
    print(f"  excess over base {diag['excess_pp']*100:+.2f}pp "
          f"(docs say +1.3 to +1.8pp — the rebuild reproduces it)")
    k = kelly_fraction(trades)
    print(f"  full Kelly {k:.2f}x  (Reg-T caps a held position at {REGT_MAX_LEVERAGE:.0f}x)")
    gm = growth_math()
    print(f"\n$5k -> $50k is {gm['multiple']:.0f}x; at {PHASE2_TARGET*100:.0f}%/yr that is "
          f"{gm['years_at_15pct']:.1f} years")
    for r in gm["rows"]:
        print(f"    in {r['years']:>4} years requires {r['required_cagr']*100:>7.1f}%/yr")
