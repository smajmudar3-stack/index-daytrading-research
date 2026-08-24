"""Every option structure, every timeframe, every regime -- on REAL SPY quotes.

A general N-leg engine. Each structure is declared as a list of legs specified
by TARGET DELTA (not fixed strikes), so the same definition is comparable
across 2008's volatility and 2017's. Fills are struck at the real quote:

    every long leg is bought at the ASK, every short leg sold at the BID,
    and the whole thing is unwound the same way, against you, at exit.

That is 2 spread crossings per leg per round trip. A 4-leg condor pays 8. The
engine charges it rather than assuming a slippage number, which is the single
biggest reason modelled condor backtests look profitable and real ones do not.

Structures covered (the owner's full list plus the standard set):
  directional : long call/put at 5 deltas, debit spreads, ZEBRA
  premium     : credit spreads, iron condor, iron butterfly, jade lizard,
                twisted sister, broken-wing butterfly, christmas tree
  volatility  : long/short straddle, long/short strangle

Regimes tested: VIX level, VIX term structure, breadth, dip, IV rank, and
dealer-gamma (DIX/GEX) where available.
"""
import os
import sys
import warnings
from collections import defaultdict

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from idt import paths

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

SWING = paths.data("swing", "panel.parquet")
OPT = paths.data("opt_eod", "SPY_options.parquet")
GEX = paths.data("squeeze_dix_gex.csv")
OUT = paths.data("swing")

# (delta, kind, qty). Positive qty = long (pay ask), negative = short (hit bid).
# Deltas are absolute; puts are matched on |delta|.
STRUCTURES = {
    # ---- directional, long premium ------------------------------------
    "long call 0.80d":      [(0.80, "call", +1)],
    "long call 0.70d":      [(0.70, "call", +1)],
    "long call 0.50d":      [(0.50, "call", +1)],
    "long call 0.30d":      [(0.30, "call", +1)],
    "long call 0.16d":      [(0.16, "call", +1)],
    "long put 0.50d":       [(0.50, "put", +1)],
    "long put 0.30d":       [(0.30, "put", +1)],
    "call debit 70/30":     [(0.70, "call", +1), (0.30, "call", -1)],
    "call debit 50/30":     [(0.50, "call", +1), (0.30, "call", -1)],
    "put debit 50/30":      [(0.50, "put", +1), (0.30, "put", -1)],
    # ZEBRA: 2 ITM long, 1 ATM short -- near-zero extrinsic, stock-like.
    "ZEBRA call 70/50":     [(0.70, "call", +2), (0.50, "call", -1)],
    "ZEBRA call 80/50":     [(0.80, "call", +2), (0.50, "call", -1)],

    # ---- premium selling, defined risk --------------------------------
    "put credit 30/16":     [(0.30, "put", -1), (0.16, "put", +1)],
    "put credit 16/05":     [(0.16, "put", -1), (0.05, "put", +1)],
    "call credit 30/16":    [(0.30, "call", -1), (0.16, "call", +1)],
    "iron condor 30/16":    [(0.30, "put", -1), (0.16, "put", +1),
                             (0.30, "call", -1), (0.16, "call", +1)],
    "iron condor 16/05":    [(0.16, "put", -1), (0.05, "put", +1),
                             (0.16, "call", -1), (0.05, "call", +1)],
    "iron butterfly ATM":   [(0.50, "put", -1), (0.16, "put", +1),
                             (0.50, "call", -1), (0.16, "call", +1)],
    # Broken wing: short body, near wing tight, far wing pushed out.
    "broken-wing fly (put)": [(0.50, "put", +1), (0.30, "put", -2),
                              (0.05, "put", +1)],
    # Jade lizard: short put + short call spread; no upside risk if the
    # credit exceeds the call-spread width.
    "jade lizard":          [(0.30, "put", -1), (0.30, "call", -1),
                             (0.16, "call", +1)],
    "twisted sister":       [(0.30, "call", -1), (0.30, "put", -1),
                             (0.16, "put", +1)],
    # Christmas tree, 1-3-2 call ratio.
    "christmas tree call":  [(0.50, "call", +1), (0.30, "call", -3),
                             (0.16, "call", +2)],

    # ---- volatility ---------------------------------------------------
    "long straddle":        [(0.50, "call", +1), (0.50, "put", +1)],
    "short straddle":       [(0.50, "call", -1), (0.50, "put", -1)],
    "long strangle 30d":    [(0.30, "call", +1), (0.30, "put", +1)],
    "short strangle 30d":   [(0.30, "call", -1), (0.30, "put", -1)],
    "short strangle 16d":   [(0.16, "call", -1), (0.16, "put", -1)],
}

DTE_TARGETS = [7, 14, 30, 45]        # weekly through monthly-plus
HOLD_FRACTIONS = [0.5, 1.0]          # exit halfway to expiry, or at expiry


def build_context():
    """Market-state factors used to gate entries."""
    p = pd.read_parquet(paths.require_data(SWING))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    spy = close["SPY"]

    ctx = pd.DataFrame(index=close.index)
    sectors = [c for c in close.columns if c.startswith("XL")]
    above = pd.DataFrame({s: (close[s] > close[s].rolling(200).mean()).astype(float)
                          for s in sectors})
    ctx["breadth"] = above.mean(axis=1)
    ctx["above200"] = (spy > spy.rolling(200).mean()).astype(float)
    ctx["above50"] = (spy > spy.rolling(50).mean()).astype(float)
    ctx["dd"] = spy / spy.cummax() - 1.0
    if "^VIX" in close.columns:
        v = close["^VIX"]
        ctx["vix"] = v
        # Past-only percentile of VIX in its own trailing 2y distribution.
        ctx["vix_pct"] = v.rolling(504, min_periods=252).apply(
            lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    if "^VIX" in close.columns and "^VIX3M" in close.columns:
        ctx["contango"] = (close["^VIX"] / close["^VIX3M"] < 1.0).astype(float)

    # Dealer gamma / dark-pool index, if the SqueezeMetrics file is present.
    if os.path.exists(GEX):          # optional file; absence is a documented degrade
        g = pd.read_csv(GEX)
        dcol = [c for c in g.columns if c.lower().startswith("date")][0]
        g[dcol] = pd.to_datetime(g[dcol])
        g = g.set_index(dcol).sort_index()
        for c in g.columns:
            if c.lower() in ("gex", "dix"):
                s = pd.to_numeric(g[c], errors="coerce").reindex(ctx.index).ffill()
                ctx[c.lower()] = s
                ctx[f"{c.lower()}_z"] = ((s - s.rolling(252, min_periods=126).mean())
                                         / s.rolling(252, min_periods=126).std())

    return close, spy, ctx.shift(1)   # known at prior close


def regimes(ctx):
    r = {"ALL": pd.Series(True, index=ctx.index)}
    if "vix_pct" in ctx:
        r["VIX low (<33pct)"] = ctx.vix_pct < 0.33
        r["VIX high (>67pct)"] = ctx.vix_pct > 0.67
    if "contango" in ctx:
        r["contango"] = ctx.contango > 0
        r["backwardation"] = ctx.contango <= 0
    if "above200" in ctx:
        r["bull (>200dma)"] = ctx.above200 > 0
        r["bear (<200dma)"] = ctx.above200 <= 0
    if "breadth" in ctx:
        r["breadth>0.6 + dip3"] = (ctx.breadth > 0.6) & (ctx.dd < -0.03)
    if "gex_z" in ctx:
        r["high dealer gamma"] = ctx.gex_z > 0.5
        r["low dealer gamma"] = ctx.gex_z < -0.5
    if "dix_z" in ctx:
        r["high DIX"] = ctx.dix_z > 0.5
    return {k: v.fillna(False) for k, v in r.items()}


def price_legs(day_chain, legs, side):
    """Cost to OPEN (side=+1) or to CLOSE (side=-1) the structure.

    Returns (cash_flow, detail). Cash flow is negative for a net debit.
    Long legs cross to the ask when opening and to the bid when closing;
    short legs do the reverse. There is no mid-price anywhere.
    """
    total = 0.0
    picked = []
    for delta, kind, qty in legs:
        c = day_chain[day_chain.type == kind]
        if c.empty:
            return None, None
        c = c.assign(derr=(c.delta.abs() - delta).abs())
        row = c.loc[c.derr.idxmin()]
        if row.bid <= 0 or row.ask <= row.bid:
            return None, None
        eff = qty * side
        px = row.ask if eff > 0 else row.bid     # buying -> ask, selling -> bid
        total -= eff * px                        # cash out when buying
        picked.append((row.strike, kind, qty, row.expiration))
    return total, picked


def expired_value(picked, spot):
    """Intrinsic value of the legs, used when a contract has left the chain.

    Dropping such trades instead would remove precisely the positions that
    went to zero -- a survivorship filter on the losing side.
    """
    total = 0.0
    for strike, kind, qty, _ in picked:
        intrinsic = max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
        total += qty * intrinsic
    return total


def close_legs(day_chain, picked):
    """Unwind the exact contracts opened, again at the adverse side."""
    total = 0.0
    for strike, kind, qty, expiry in picked:
        c = day_chain[(day_chain.type == kind) & (day_chain.strike == strike) &
                      (day_chain.expiration == expiry)]
        if c.empty:
            return None
        row = c.iloc[0]
        # Closing reverses the sign: a long leg is sold at the bid.
        px = row.bid if qty > 0 else row.ask
        total += qty * px
    return total


def max_loss_at_expiry(picked, spot, lo=0.30, hi=2.50, n=4001):
    """True worst-case payoff, evaluated across a wide terminal-price grid.

    Replaces a strike-width heuristic that silently ignored NAKED legs. A jade
    lizard is a short put PLUS a short call spread -- the call side is defined,
    the put side is not. Measuring only the call-spread width made the
    denominator ~50x too small and turned an ordinary credit trade into a
    fictitious +800%/yr. Evaluating the actual payoff cannot make that mistake.

    Returns (max_loss, unbounded_flag). Unbounded means a naked short leg
    dominates the tail, in which case % return on "capital" is not defined and
    the caller must substitute a margin requirement.
    """
    S = np.linspace(spot * lo, spot * hi, n)
    payoff = np.zeros_like(S)
    for strike, kind, qty, _ in picked:
        intrinsic = np.maximum(S - strike, 0.0) if kind == "call" else np.maximum(strike - S, 0.0)
        payoff += qty * intrinsic

    # A naked short shows up as a payoff still falling at the edge of the grid.
    edge_slope_lo = payoff[1] - payoff[0]
    edge_slope_hi = payoff[-1] - payoff[-2]
    unbounded = (edge_slope_lo > 1e-9) or (edge_slope_hi < -1e-9)
    return float(payoff.min()), unbounded


def capital_at_risk(open_cash, picked, legs, spot):
    """Denominator for the % return -- the money genuinely at risk.

    net debit          -> the debit paid
    defined-risk credit-> worst expiry payoff + credit received
    naked / unbounded  -> 20% of notional per naked short (a Reg-T style margin
                          proxy), because a naked short has no max loss and
                          dividing by a tiny credit manufactures huge returns.
    """
    worst, unbounded = max_loss_at_expiry(picked, spot)
    if unbounded:
        naked = sum(abs(q) for _, _, q, _ in picked)
        return 0.20 * spot * max(naked, 1), True

    # worst is negative (a loss) for a spread; total risk nets the cash taken in.
    risk = -(worst + open_cash)
    if open_cash < 0:                      # net debit -> risk is the debit
        risk = max(abs(open_cash), risk)
    return (max(risk, 0.01), False)


def run_year(year, structures, regs, ctx, spy):
    """Backtest one calendar year; keeps memory bounded."""
    cols = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
            "implied_volatility", "open_interest"]
    tbl = pq.read_table(paths.require_data(OPT), columns=cols,
        filters=[("date", ">=", pd.Timestamp(f"{year}-01-01")),
                 ("date", "<=", pd.Timestamp(f"{year}-12-31"))])
    ch = tbl.to_pandas()
    if ch.empty:
        return []
    ch["date"] = pd.to_datetime(ch["date"])
    ch["expiration"] = pd.to_datetime(ch["expiration"])
    ch["dte"] = (ch["expiration"] - ch["date"]).dt.days
    # CRITICAL: the liquidity screen may be applied ONLY at entry.
    # Applying `bid > 0` to the EXIT chain deletes every option that expired
    # worthless -- i.e. it silently deletes the losers and manufactures a 100%
    # win rate. Exit pricing must accept a zero bid, because zero is the
    # correct price of a worthless option.
    ch_exit = ch[ch.ask >= ch.bid].copy()          # everything quotable
    ch_entry = ch[(ch.bid > 0.02) & (ch.ask > ch.bid) & (ch.open_interest > 5) &
                  (ch.delta.abs() > 0.02) & (ch.delta.abs() < 0.98)]
    if ch_entry.empty:
        return []

    by_date = {d: g for d, g in ch_entry.groupby("date")}
    by_date_exit = {d: g for d, g in ch_exit.groupby("date")}
    dates = sorted(by_date)
    exit_dates = set(by_date_exit)
    rows = []

    # Enter weekly (every 5th session) to keep trades non-overlapping-ish and
    # the sample size sane.
    for i in range(0, len(dates), 5):
        d0 = dates[i]
        day = by_date[d0]

        for dte_t in DTE_TARGETS:
            cand = day[(day.dte >= max(dte_t - 3, 1)) & (day.dte <= dte_t + 7)]
            if cand.empty:
                continue
            exp = cand.groupby("expiration").size().idxmax()
            leg_day = cand[cand.expiration == exp]
            real_dte = int((exp - d0).days)

            for hf in HOLD_FRACTIONS:
                # Exit date: fraction of the way to expiry (1.0 == at expiry).
                target = d0 + pd.Timedelta(days=int(round(real_dte * hf)))
                later = [d for d in dates if d >= target]
                if not later:
                    continue
                d1 = later[0]
                if d1 <= d0:
                    continue

                for sname, legs in structures.items():
                    oc, picked = price_legs(leg_day, legs, +1)
                    if oc is None:
                        continue
                    spot = float(spy.loc[:d0].iloc[-1])
                    cap, naked = capital_at_risk(oc, picked, legs, spot)
                    if cap <= 0.01:
                        continue

                    if d1 not in by_date_exit:
                        continue
                    cc = close_legs(by_date_exit[d1], picked)
                    if cc is None:
                        # Contract absent from the exit chain entirely -- treat
                        # a vanished option as expired worthless rather than
                        # dropping the trade, which would bias the sample.
                        cc = expired_value(picked, float(spy.loc[:d1].iloc[-1]))
                    if cc is None:
                        continue
                    pnl = oc + cc
                    rows.append({
                        "date": d0, "structure": sname, "dte": real_dte,
                        "hold_frac": hf, "ret": pnl / cap, "cap": cap,
                        "naked": naked,
                    })
    return rows


def main():
    close, spy, ctx = build_context()
    regs = regimes(ctx)

    years = range(2008, 2026)
    print("=" * 100)
    print("STRUCTURE LAB -- every structure x timeframe x regime, on REAL SPY quotes")
    print("=" * 100)
    print(f"  {len(STRUCTURES)} structures x {len(DTE_TARGETS)} DTE targets x "
          f"{len(HOLD_FRACTIONS)} hold fractions x {len(regs)} regimes")
    print(f"  fills: long legs at ASK, short legs at BID, unwound adversely at exit\n")

    all_rows = []
    for y in years:
        r = run_year(y, STRUCTURES, regs, ctx, spy)
        all_rows.extend(r)
        print(f"    {y}: {len(r):6d} structure-trades", flush=True)

    df = pd.DataFrame(all_rows)
    df.to_parquet(os.path.join(OUT, "structure_trades.parquet"), index=False)
    print(f"\n  total {len(df):,} structure-trades\n")

    # ---- aggregate by structure x dte x hold x regime ------------------
    out = []
    for (sname, dte, hf), g in df.groupby(["structure", "dte", "hold_frac"]):
        for rname, mask in regs.items():
            m = mask.reindex(g.date.values)
            gg = g[m.values] if len(m) == len(g) else g
            if len(gg) < 25:
                continue
            r = gg.ret
            yrs = (gg.date.max() - gg.date.min()).days / 365.25
            if yrs <= 0.5:
                continue
            step = np.maximum(1 + r.values * 0.25, 0.0)   # cannot lose >100% of stake
            eq = step.cumprod()
            cagr = eq[-1] ** (1 / yrs) - 1 if eq[-1] > 0 else -1.0
            dd = (eq / np.maximum.accumulate(eq) - 1).min()
            out.append({
                "structure": sname, "dte": dte, "hold": hf, "regime": rname,
                "n": len(gg), "win": (r > 0).mean(), "avg": r.mean(),
                "t": r.mean() / (r.std() / np.sqrt(len(r))) if r.std() > 0 else 0,
                "cagr": cagr, "monthly": (1 + cagr) ** (1 / 12) - 1 if cagr > -1 else -1,
                "maxdd": dd,
            })

    res = pd.DataFrame(out)
    res.to_parquet(os.path.join(OUT, "structure_summary.parquet"), index=False)
    print(f"  {len(res)} structure/timeframe/regime cells with n>=25\n")

    def show(title, sub, n=25):
        print("=" * 100)
        print(title)
        print("=" * 100)
        print(f"  {'structure':22s} {'dte':>4s} {'hold':>5s} {'regime':20s} "
              f"{'n':>4s} {'win':>6s} {'avg':>8s} {'t':>6s} {'MONTH':>8s} {'YEAR':>8s} {'maxDD':>8s}")
        for _, x in sub.head(n).iterrows():
            print(f"  {x['structure']:22s} {int(x['dte']):4d} {x['hold']:5.1f} "
                  f"{x['regime']:20s} {int(x['n']):4d} {x['win']:6.1%} "
                  f"{x['avg']:+8.2%} {x['t']:+6.2f} {x['monthly']:+8.2%} "
                  f"{x['cagr']:+8.1%} {x['maxdd']:+8.1%}")
        print()

    sig = res[res.t > 2.0]
    show("STATISTICALLY POSITIVE (t > 2) -- ranked by t-stat", sig.sort_values("t", ascending=False))
    show("HIGHEST WIN RATE with positive expectancy",
         res[(res.avg > 0)].sort_values("win", ascending=False))
    show("BEST YEARLY RETURN (25% sizing)", res.sort_values("cagr", ascending=False))
    show("BEST RETURN / DRAWDOWN",
         res[(res.cagr > 0)].assign(cal=lambda d: d.cagr / d.maxdd.abs())
            .sort_values("cal", ascending=False))

    n_trials = len(res)
    print(f"  MULTIPLE-TESTING BAR: {n_trials} cells tested -> expected best |t| "
          f"under the null ~ {np.sqrt(2*np.log(max(n_trials,2))):.2f}")
    print("  Treat anything below that as search noise, not an edge.")


if __name__ == "__main__":
    main()
