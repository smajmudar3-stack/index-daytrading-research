"""Does a long wing cost less than the tail it removes?

This is the question that decides whether premium selling is salvageable. The
variance premium is huge (implied 19.2% vs realized 13.6%, realized below
implied on 88.5% of days) and every credit structure tested still lost money.
If the tail is what eats it, a wing that costs less than the tail it removes
would fix the strategy. If the wing costs more, the tail is fairly priced and
premium selling is closed.

Design: hold the SHORT BODY FIXED and vary only the wings. The difference
between the two P&L distributions is the wing's entire economic effect, with no
confounding from strike selection.

    body   short 16-delta put + short 16-delta call   (sold at BID)
    wings  long  5-delta put + long  5-delta call     (bought at ASK)

Held to expiry, settled against the actual close, so the exit is intrinsic
value and there is no exit spread and no survivorship filter -- worthless legs
expire worthless and are counted, which is the trap that produced 100% win
rates here before.

Reported per structure in dollars, so the comparison is like-for-like on an
identical body. Capital-at-risk denominators are deliberately NOT used for the
naked version, because a short strangle has unbounded loss and any percentage
return for it is a fiction (the jade-lizard bug).
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(ROOT, "data", "opt_eod", "SPY_options.parquet")

DTE_LO, DTE_HI = 25, 40
BODY_D, WING_D = 0.16, 0.05
TOL = 0.04


def pick(g, target, tol=TOL):
    """Contract with delta nearest target, within tolerance, that is quotable."""
    g = g[(g.ask > 0) & (g.ask >= g.bid) & (g.open_interest > 5)]
    if g.empty:
        return None
    i = (g.delta.abs() - target).abs()
    j = i.idxmin()
    return g.loc[j] if i.loc[j] <= tol else None


def main():
    cols = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
            "open_interest"]
    d = pd.read_parquet(OPT, columns=cols)
    d["date"] = pd.to_datetime(d["date"])
    d["expiration"] = pd.to_datetime(d["expiration"])
    d["dte"] = (d.expiration - d["date"]).dt.days
    d["cp"] = d.type.str.lower().str[0]
    d = d[(d.dte >= DTE_LO) & (d.dte <= DTE_HI) & d.delta.notna()]

    # SETTLEMENT: the actual underlying close, not a delta-derived proxy.
    # Deriving spot from the 0.45-0.55 delta strike was biased ~+1.2% high,
    # because for longer-dated expiries the 50-delta strike sits above spot at
    # the forward. Use the real close; strikes are nominal so `close` is the
    # right column, not `adjusted_close`.
    u = pd.read_parquet(os.path.join(ROOT, "data", "opt_eod",
                                     "SPY_underlying.parquet"),
                        columns=["date", "close"])
    u["date"] = pd.to_datetime(u["date"])
    S = u.drop_duplicates("date").set_index("date")["close"].sort_index()
    print(f"  settlement series: {len(S):,} sessions "
          f"{S.index.min().date()} -> {S.index.max().date()}")

    # Drop sign-corrupt rows: calls must have delta > 0, puts < 0. Only ~0.01%
    # of rows, but they would let pick() return a contract on the wrong side.
    bad = ((d.cp == "c") & (d.delta <= 0)) | ((d.cp == "p") & (d.delta >= 0))
    if bad.any():
        print(f"  dropping {bad.sum():,} sign-corrupt delta rows")
        d = d[~bad]

    rows = []
    for (dt, exp), g in d.groupby(["date", "expiration"]):
        if exp not in S.index:
            continue
        spot_T = S[exp]
        puts, calls = g[g.cp == "p"], g[g.cp == "c"]
        sp, sc = pick(puts, BODY_D), pick(calls, BODY_D)
        lp, lc = pick(puts, WING_D), pick(calls, WING_D)
        if sp is None or sc is None or lp is None or lc is None:
            continue
        if not (lp.strike < sp.strike < sc.strike < lc.strike):
            continue

        credit = sp.bid + sc.bid                      # sold at the bid
        wing_cost = lp.ask + lc.ask                   # bought at the ask
        # payoff at expiry
        sp_pay = max(0.0, sp.strike - spot_T)
        sc_pay = max(0.0, spot_T - sc.strike)
        lp_pay = max(0.0, lp.strike - spot_T)
        lc_pay = max(0.0, spot_T - lc.strike)   # long CALL pays S-K, not K-S

        naked = credit - sp_pay - sc_pay
        hedged = naked - wing_cost + lp_pay + lc_pay
        rows.append(dict(date=dt, exp=exp, spot_T=spot_T,
                         credit=credit, wing_cost=wing_cost,
                         naked=naked, hedged=hedged,
                         wing_payout=lp_pay + lc_pay,
                         width=min(sp.strike - lp.strike, lc.strike - sc.strike)))

    r = pd.DataFrame(rows)
    print(f"  RAW: {len(r):,} trades, wing pays {(r.wing_payout>0).mean()*100:.1f}%,"
          f" mean payout ${r.wing_payout.mean():.3f}")
    # One trade per expiry cycle: overlapping entries share outcomes and inflate t.
    r = r.sort_values("date").drop_duplicates(subset="exp", keep="first")
    print(f"  DEDUP: {len(r):,} trades, wing pays {(r.wing_payout>0).mean()*100:.1f}%,"
          f" mean payout ${r.wing_payout.mean():.3f}")
    print(f"  {len(r):,} non-overlapping trades, "
          f"{r.date.min().date()} -> {r.date.max().date()}\n")

    print("=" * 94)
    print("SAME SHORT BODY, WITH AND WITHOUT WINGS  ($ per structure, x100 = per contract)")
    print("=" * 94)
    print(f"  {'':22s} {'naked strangle':>16s} {'iron condor':>14s} {'difference':>13s}")
    for lab, f in (("mean P&L", np.mean), ("median P&L", np.median),
                   ("std dev", np.std), ("worst", np.min), ("best", np.max)):
        a, b = f(r.naked), f(r.hedged)
        print(f"  {lab:22s} {a:16.2f} {b:14.2f} {b-a:+13.2f}")
    for lab, q in (("5th pctile", 5), ("1st pctile", 1)):
        a, b = np.percentile(r.naked, q), np.percentile(r.hedged, q)
        print(f"  {lab:22s} {a:16.2f} {b:14.2f} {b-a:+13.2f}")
    wr_a, wr_b = (r.naked > 0).mean(), (r.hedged > 0).mean()
    print(f"  {'win rate':22s} {wr_a*100:15.1f}% {wr_b*100:13.1f}% "
          f"{(wr_b-wr_a)*100:+12.1f}pp")
    for lab, x in (("Sharpe (per trade)", None),):
        a = r.naked.mean() / r.naked.std(ddof=1)
        b = r.hedged.mean() / r.hedged.std(ddof=1)
        print(f"  {lab:22s} {a:16.3f} {b:14.3f} {b-a:+13.3f}")
    ta = r.naked.mean() / (r.naked.std(ddof=1) / np.sqrt(len(r)))
    tb = r.hedged.mean() / (r.hedged.std(ddof=1) / np.sqrt(len(r)))
    print(f"  {'t-stat vs zero':22s} {ta:16.2f} {tb:14.2f}")

    print("\n" + "=" * 94)
    print("THE WING LEDGER")
    print("=" * 94)
    paid = r.wing_cost.mean()
    got = r.wing_payout.mean()
    print(f"  average wing premium paid       ${paid:7.3f}")
    print(f"  average wing payout received    ${got:7.3f}")
    print(f"  net cost of carrying wings      ${paid-got:+7.3f} per structure")
    print(f"  wings paid out on               {(r.wing_payout>0).mean()*100:.1f}% "
          f"of trades")
    print(f"  average credit collected        ${r.credit.mean():7.3f}")
    print(f"  wings as share of credit        {paid/r.credit.mean()*100:.1f}%")

    print(f"\n  tail comparison, worst 5% of outcomes:")
    k = max(int(len(r) * 0.05), 1)
    wn = r.nsmallest(k, "naked")
    print(f"    naked mean of worst {k}: ${wn.naked.mean():8.2f}")
    print(f"    same trades hedged     : ${wn.hedged.mean():8.2f}   "
          f"tail saved ${wn.hedged.mean()-wn.naked.mean():+.2f}")

    print("\n" + "=" * 94)
    if paid - got > 0:
        print(f"  The wing costs ${paid-got:.3f} more than it pays. For it to be worth")
        print("  buying anyway, it must buy enough ruin protection to justify that,")
        print("  which is a sizing question rather than an expectancy one.")
    else:
        print(f"  The wing pays ${got-paid:.3f} MORE than it costs -- it improves")
        print("  expectancy outright, which would make premium selling viable.")
    print("=" * 94)


if __name__ == "__main__":
    main()
