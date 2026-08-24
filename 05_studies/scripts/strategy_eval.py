"""Evaluate candidate swing strategies through REAL SPY option quotes.

This is the file that answers "what is the win rate, monthly yield, annual
yield and max drawdown" -- and it answers it with actual bid/ask from
data/opt_eod/SPY_options.parquet (24.7M rows, 2008-2025), NOT a pricing model.

That distinction is the whole point. The previous "validated" edge in this repo
(+3.7%/trade, 91% win, t=+7.4) was produced by Black-Scholes with a linear skew
approximation and collapsed to -1.70%/trade on real quotes. Every number below
is struck at prices someone could actually have traded:

    entries are filled at the ASK, exits at the BID.

No mid-price fills, no modelled greeks, no assumed slippage -- the spread IS
the cost, taken from the quote.

The signal under test is the one that survived the 3,536-configuration sweep on
all three time splits: buy the dip while the market is healthy. It is deliberately
expressed several different ways so the STRUCTURE question is answered on the
same trades, since structure -- not signal -- is what killed the last attempt.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

from swing_lab import SPLITS, pch, slice_dates  # noqa: E402

SWING = paths.data("swing", "panel.parquet")
OPT = paths.data("opt_eod", "SPY_options.parquet")
OUT = paths.data("swing")

HOLD = 21          # trading days -- the horizon the signal was validated at
MIN_DTE = 35       # option must outlive the hold with time value left
MAX_DTE = 75
TRADING_DAYS = 252


# --------------------------------------------------------------------------
# signals
# --------------------------------------------------------------------------
def build_signals():
    p = pd.read_parquet(paths.require_data(SWING))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    spy = close["SPY"]

    sig = pd.DataFrame(index=close.index)

    # Market health: how many sectors are in their own uptrend. Breadth beats
    # the index itself as a health read because the index is cap-weighted and
    # can be held up by a handful of names.
    sectors = [c for c in ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP",
                           "XLU", "XLB", "XLRE", "XLC"] if c in close.columns]
    above = pd.DataFrame({s: (close[s] > close[s].rolling(200).mean()).astype(float)
                          for s in sectors})
    sig["breadth"] = above.mean(axis=1)
    sig["above50"] = (spy > spy.rolling(50).mean()).astype(float)
    sig["above200"] = (spy > spy.rolling(200).mean()).astype(float)
    sig["golden"] = (spy.rolling(50).mean() > spy.rolling(200).mean()).astype(float)

    # The dip itself, measured from the running high. cummax is past-only.
    sig["dd"] = spy / spy.cummax() - 1.0

    if "^VIX" in close.columns and "^VIX3M" in close.columns:
        sig["backward"] = (close["^VIX"] / close["^VIX3M"] >= 1.0).astype(float)
    else:
        sig["backward"] = 0.0

    # Shift: everything is known at the prior close, traded the next day.
    sig = sig.shift(1)

    rules = {
        "breadth_hi+dip3": (sig.breadth > 0.6) & (sig.dd < -0.03),
        "above50+dip3": (sig.above50 > 0) & (sig.dd < -0.03),
        "backward+golden": (sig.backward > 0) & (sig.golden > 0),
        "above200+dip3": (sig.above200 > 0) & (sig.dd < -0.03),
    }
    return close, spy, {k: v.fillna(False) for k, v in rules.items()}


def entry_dates(cond, index, hold=HOLD):
    """Non-overlapping entries -- one position at a time, no double counting."""
    c = cond.reindex(index).fillna(False).values
    idx = np.flatnonzero(c)
    picked, last = [], -10**9
    for i in idx:
        if i - last >= hold:
            picked.append(i)
            last = i
    return [index[i] for i in picked if i + hold < len(index)]


# --------------------------------------------------------------------------
# real option chain access
# --------------------------------------------------------------------------
def load_chain(dates_needed):
    """Load only the sessions we actually trade -- 24.7M rows won't fit twice."""
    cols = ["date", "expiration", "strike", "type", "bid", "ask",
            "delta", "implied_volatility", "open_interest", "volume"]
    want = pd.to_datetime(sorted(set(dates_needed)))
    tbl = pq.read_table(paths.require_data(OPT), columns=cols,
                        filters=[("date", "in", list(want))])
    d = tbl.to_pandas()
    d["date"] = pd.to_datetime(d["date"])
    d["expiration"] = pd.to_datetime(d["expiration"])
    d["dte"] = (d["expiration"] - d["date"]).dt.days
    return d


def pick_contract(chain, date, target_delta, kind="call",
                  min_dte=MIN_DTE, max_dte=MAX_DTE):
    """Nearest-delta liquid contract in the DTE window.

    Selecting by DELTA rather than by a fixed % strike is the correct
    convention -- it holds probability-of-profit roughly constant as vol and
    time change, which a fixed moneyness does not.
    """
    c = chain[(chain.date == date) & (chain.type == kind) &
              (chain.dte >= min_dte) & (chain.dte <= max_dte)]
    if c.empty:
        return None
    # Liquidity screen: a quote with no OI and a huge spread is not tradeable.
    c = c[(c.bid > 0.05) & (c.ask > c.bid) & (c.open_interest > 10)]
    if c.empty:
        return None
    c = c.copy()
    c["spread_pct"] = (c.ask - c.bid) / ((c.ask + c.bid) / 2)
    c = c[c.spread_pct < 0.25]           # reject untradeable quotes
    if c.empty:
        return None
    # Prefer the expiry closest to 45 DTE, then the closest delta within it.
    c["dte_err"] = (c.dte - 45).abs()
    best_exp = c.loc[c.dte_err.idxmin(), "expiration"]
    c = c[c.expiration == best_exp]
    c["derr"] = (c.delta.abs() - abs(target_delta)).abs()
    return c.loc[c.derr.idxmin()]


def find_exit(chain, exit_date, strike, expiration, kind):
    """Locate the same contract on the exit date."""
    c = chain[(chain.date == exit_date) & (chain.type == kind) &
              (chain.strike == strike) & (chain.expiration == expiration)]
    if c.empty:
        return None
    return c.iloc[0]


# --------------------------------------------------------------------------
# structures
# --------------------------------------------------------------------------
STRUCTURES = [
    ("deep ITM call (0.80d)", "single", 0.80),
    ("ITM call (0.70d)", "single", 0.70),
    ("ATM call (0.50d)", "single", 0.50),
    ("OTM call (0.30d)", "single", 0.30),
    ("far OTM call (0.16d)", "single", 0.16),
    ("call debit 0.70/0.30", "debit", (0.70, 0.30)),
    ("call debit 0.50/0.30", "debit", (0.50, 0.30)),
]


def run_trade(chain, d_entry, d_exit, kind_spec, spec):
    """Return the net % return on capital at risk, filled at ask/bid."""
    if kind_spec == "single":
        c = pick_contract(chain, d_entry, spec)
        if c is None:
            return None
        x = find_exit(chain, d_exit, c.strike, c.expiration, "call")
        if x is None:
            return None
        entry = c.ask                     # we pay the offer
        exit_ = x.bid                     # we hit the bid
        if entry <= 0:
            return None
        return (exit_ - entry) / entry

    if kind_spec == "debit":
        dl, ds = spec
        cl = pick_contract(chain, d_entry, dl)
        if cl is None:
            return None
        # Short leg must share the long leg's expiry to be a vertical.
        c = chain[(chain.date == d_entry) & (chain.type == "call") &
                  (chain.expiration == cl.expiration) &
                  (chain.bid > 0.02) & (chain.ask > chain.bid)]
        if c.empty:
            return None
        c = c.copy()
        c["derr"] = (c.delta.abs() - ds).abs()
        cs = c.loc[c.derr.idxmin()]
        if cs.strike <= cl.strike:
            return None

        xl = find_exit(chain, d_exit, cl.strike, cl.expiration, "call")
        xs = find_exit(chain, d_exit, cs.strike, cs.expiration, "call")
        if xl is None or xs is None:
            return None

        entry = cl.ask - cs.bid           # pay offer on long, hit bid on short
        exit_ = xl.bid - xs.ask           # unwind the same way, against us
        if entry <= 0:
            return None
        return (exit_ - entry) / entry
    return None


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def summarize(trades, label, years, hold=HOLD):
    """Per-trade stats plus a compounded curve at a stated position size.

    `years` is the ACTUAL elapsed calendar span of the trades, not an assumed
    trades-per-year. Annualising a signal that fires 5x a year as though it
    fired 12x doubles the reported CAGR out of thin air -- a pure bookkeeping
    error that looks exactly like an edge.
    """
    r = pd.Series([t for t in trades if t is not None]).dropna()
    if len(r) < 8 or years <= 0:
        return None

    out = {"strategy": label, "trades": len(r), "win": (r > 0).mean(),
           "avg_trade": r.mean(), "best": r.max(), "worst": r.min(),
           "per_year": len(r) / years}

    for frac, tag in ((1.00, "full"), (0.25, "q25")):
        eq = (1 + r * frac).cumprod()
        total = eq.iloc[-1]
        cagr = total ** (1 / years) - 1 if total > 0 else -1.0
        dd = (eq / eq.cummax() - 1).min()
        out[f"cagr_{tag}"] = cagr
        out[f"monthly_{tag}"] = (1 + cagr) ** (1 / 12) - 1 if cagr > -1 else -1.0
        out[f"maxdd_{tag}"] = dd
    return out


HOLDS = [5, 10, 21, 42]   # "days to 2 weeks" and beyond -- all timeframes


def main():
    close, spy, rules = build_signals()
    idx = close.index[(close.index >= "2008-01-02") & (close.index <= "2025-12-31")]

    print("=" * 104)
    print("STRATEGY EVALUATION -- real SPY option quotes; entries filled at ASK, exits at BID")
    print("=" * 104)
    print(f"  window {idx[0].date()} -> {idx[-1].date()}   holding periods tested: {HOLDS} trading days")

    all_rows = []
    for hold in HOLDS:
        plans, need = {}, set()
        for name, cond in rules.items():
            ents = entry_dates(cond, idx, hold=hold)
            pos = {d: idx[min(idx.get_loc(d) + hold, len(idx) - 1)] for d in ents}
            plans[name] = pos
            need |= set(pos.keys()) | set(pos.values())

        print(f"\n  [hold={hold}d] loading real chains for {len(need)} sessions ...", flush=True)
        chain = load_chain(need)

        for sname, pos in plans.items():
            if not pos:
                continue
            span = (max(pos.values()) - min(pos.keys())).days / 365.25
            for label, kind_spec, spec in STRUCTURES:
                trades = [run_trade(chain, a, b, kind_spec, spec) for a, b in pos.items()]
                r = summarize(trades, f"{sname}|{label}", span, hold)
                if r:
                    r.update(signal=sname, structure=label, hold=hold)
                    all_rows.append(r)
            tr = [spy.loc[b] / spy.loc[a] - 1 - 0.0002 for a, b in pos.items()]
            r = summarize(tr, f"{sname}|SPY SHARES", span, hold)
            if r:
                r.update(signal=sname, structure="SPY SHARES", hold=hold)
                all_rows.append(r)
        del chain

    res = pd.DataFrame(all_rows)
    res.to_parquet(os.path.join(OUT, "strategy_eval.parquet"), index=False)

    print("\n" + "=" * 104)
    print("ALL VARIANTS -- ranked by CAGR at 25% of account per trade")
    print("  (annualised on ACTUAL elapsed time, not an assumed trade count)")
    print("=" * 104)
    print(f"  {'signal':17s} {'structure':22s} {'hold':>4s} {'n':>4s} {'/yr':>4s} "
          f"{'win':>6s} {'avg/trade':>10s} {'MONTHLY':>8s} {'YEARLY':>8s} {'maxDD':>8s}")
    top = res.sort_values("cagr_q25", ascending=False).head(30)
    for _, x in top.iterrows():
        print(f"  {x['signal']:17s} {x['structure']:22s} {int(x['hold']):4d} "
              f"{int(x['trades']):4d} {x['per_year']:4.1f} {x['win']:6.1%} "
              f"{x['avg_trade']:+10.2%} {x['monthly_q25']:+8.2%} "
              f"{x['cagr_q25']:+8.1%} {x['maxdd_q25']:+8.1%}")

    print("\n" + "=" * 104)
    print("HIGHEST WIN RATE (>=60%), ranked -- the '60%+ win rate' target")
    print("=" * 104)
    hw = res[res.win >= 0.60].sort_values("win", ascending=False).head(25)
    print(f"  {'signal':17s} {'structure':22s} {'hold':>4s} {'n':>4s} "
          f"{'win':>6s} {'avg/trade':>10s} {'MONTHLY':>8s} {'YEARLY':>8s} {'maxDD':>8s}")
    for _, x in hw.iterrows():
        print(f"  {x['signal']:17s} {x['structure']:22s} {int(x['hold']):4d} "
              f"{int(x['trades']):4d} {x['win']:6.1%} {x['avg_trade']:+10.2%} "
              f"{x['monthly_q25']:+8.2%} {x['cagr_q25']:+8.1%} {x['maxdd_q25']:+8.1%}")

    print("\n" + "=" * 104)
    print("RISK-ADJUSTED -- yearly return divided by max drawdown (the survivability ranking)")
    print("=" * 104)
    r2 = res[(res.cagr_q25 > 0) & (res.trades >= 20)].copy()
    r2["calmar"] = r2.cagr_q25 / r2.maxdd_q25.abs()
    print(f"  {'signal':17s} {'structure':22s} {'hold':>4s} {'win':>6s} "
          f"{'MONTHLY':>8s} {'YEARLY':>8s} {'maxDD':>8s} {'ret/DD':>7s}")
    for _, x in r2.sort_values("calmar", ascending=False).head(20).iterrows():
        print(f"  {x['signal']:17s} {x['structure']:22s} {int(x['hold']):4d} "
              f"{x['win']:6.1%} {x['monthly_q25']:+8.2%} {x['cagr_q25']:+8.1%} "
              f"{x['maxdd_q25']:+8.1%} {x['calmar']:7.2f}")

    bh = pch(spy.loc[idx])
    eq = (1 + bh.fillna(0)).cumprod()
    yrs = (idx[-1] - idx[0]).days / 365.25
    print(f"\n  BENCHMARK  SPY buy & hold: YEARLY {eq.iloc[-1]**(1/yrs)-1:+.1%}, "
          f"MONTHLY {(eq.iloc[-1]**(1/yrs))**(1/12)-1:+.2%}, maxDD {(eq/eq.cummax()-1).min():+.1%}")


if __name__ == "__main__":
    main()
