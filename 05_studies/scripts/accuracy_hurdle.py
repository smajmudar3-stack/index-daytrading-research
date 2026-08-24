"""What directional accuracy would we actually NEED to profit from 0DTE options?

Everything so far has asked "is there a signal." That is the wrong question to
stop on. The decision-relevant question is whether the accuracy that is even
theoretically available clears the cost hurdle of the instrument we would trade
it with. If the hurdle is above the ceiling, the search is over regardless of
how clever the signal is.

Two numbers, both measured rather than assumed:

  CEILING   from the literature and from our own correlations, converted with
            hit_rate = 0.5 + arcsin(rho)/pi

  HURDLE    from real SPXW quotes: buy at ask, sell at bid, so the round trip
            costs the full spread. Break-even accuracy for a directional option
            trade is

                p* = 0.5 + spread / (2 * delta * move)

            where delta*move is the premium actually captured when right.

The gap between them is the answer.
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")


def rho_to_hit(rho):
    """Directional hit rate implied by a signal-return correlation."""
    return 0.5 + np.arcsin(np.clip(rho, -1, 1)) / np.pi


def main():
    print("=" * 96)
    print("PART 1 -- THE CEILING: what accuracy is even available?")
    print("=" * 96)
    print(f"  {'source':52s} {'rho':>7s} {'R2':>8s} {'hit rate':>10s}")
    rows = [
        ("our SPY r_first vs r_last (measured today)", 0.0325),
        ("our QQQ r_first vs r_last", 0.0381),
        ("our best SPXW bucket pair, out of sample", 0.023),
        ("Jane St Kaggle 2025 top-1% (R2 0.0064)", np.sqrt(0.0064)),
        ("Jane St Kaggle 2025 + online learning (R2 0.0084)", np.sqrt(0.0084)),
        ("Gu-Kelly-Xiu best monthly OOS (R2 0.0040)", np.sqrt(0.0040)),
        ("hypothetical R2 = 1%", 0.10),
        ("hypothetical R2 = 2.5%  (= '55% win rate' claim)", 0.16),
        ("hypothetical R2 = 9%    (= '60% win rate' claim)", 0.30),
    ]
    for name, r in rows:
        print(f"  {name:52s} {r:7.3f} {r*r*100:7.2f}% {rho_to_hit(r)*100:9.1f}%")

    print("\n  Cont/Cucuringu/Zhang: multi-level OFI gives 83.8% CONTEMPORANEOUS R2")
    print("  and NEGATIVE R2 one minute ahead. Explaining the move that just")
    print("  happened is not the same problem as predicting the next one.\n")

    print("=" * 96)
    print("PART 2 -- THE HURDLE: real SPXW 0DTE spreads")
    print("=" * 96)
    df = pd.read_parquet(SPXW, columns=["quote_date", "quote_time", "option_type",
                                        "mnes_rel", "mid", "bas",
                                        "active_underlying_price"])
    # SCHEMA NOTE: in this dataset `mid` and `bas` are expressed as FRACTIONS OF
    # SPOT, not dollars (median mid 0.0016 against a ~3750 index). The `delta`
    # column ranges to +/-1.9, so it is not a standard delta and is not used;
    # an at-the-money option is taken at delta 0.50 by definition.
    atm = df[(df.mnes_rel.between(0.995, 1.005)) & (df.mid > 0)].dropna(
        subset=["mid", "bas", "active_underlying_price"])
    print(f"  {len(atm):,} at-the-money quotes (moneyness within 0.5%)")
    print(f"  coverage is +/-2% moneyness only -- this is an ATM dataset")

    spot = atm.active_underlying_price.median()
    prem_pts = atm.mid * atm.active_underlying_price
    sp_pts = atm.bas * atm.active_underlying_price
    rel = (atm.bas / atm.mid)

    print(f"\n  reference spot           {spot:,.0f}")
    print(f"  ATM premium (index pts)  median {prem_pts.median():7.2f}"
          f"   p25 {prem_pts.quantile(.25):6.2f}  p75 {prem_pts.quantile(.75):6.2f}")
    print(f"  bid-ask   (index pts)    median {sp_pts.median():7.2f}"
          f"   p75 {sp_pts.quantile(.75):6.2f}  p90 {sp_pts.quantile(.90):6.2f}")
    print(f"  spread as %% of premium   median {rel.median()*100:6.2f}%%"
          f"   p75 {rel.quantile(.75)*100:5.2f}%%  p90 {rel.quantile(.90)*100:5.2f}%%")

    delta = 0.50
    med_sp, p90_sp = sp_pts.median(), sp_pts.quantile(0.90)

    print("\n" + "=" * 96)
    print("PART 3 -- BREAK-EVEN ACCURACY  p* = 0.5 + spread / (2 * delta * move)")
    print("=" * 96)
    print(f"  {'move':>10s} {'% of spot':>11s} {'captured @0.5d':>16s} "
          f"{'p* median spread':>18s} {'p* p90 spread':>15s}")
    for mv_pct in (0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00):
        mv = spot * mv_pct / 100
        cap = delta * mv
        a = 0.5 + med_sp / (2 * cap)
        b = 0.5 + p90_sp / (2 * cap)
        fa = f"{a*100:.1f}%" if a < 1 else "impossible"
        fb = f"{b*100:.1f}%" if b < 1 else "impossible"
        print(f"  {mv:9.1f}p {mv_pct:10.2f}% {cap:15.1f}p {fa:>18s} {fb:>15s}")
    print("\n  Spread is paid once entering and once exiting; delta 0.50 is the")
    print("  ATM value. Theta and gamma are ignored, which FAVOURS the trade.")

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    ceiling = rho_to_hit(np.sqrt(0.0084))
    print(f"  Best documented accuracy on real production data: {ceiling*100:.1f}%")
    print(f"  (Jane Street 2025, 3,757 teams, R2 0.0084 with online learning.)")
    typical = spot * 0.50 / 100
    need = 0.5 + med_sp / (2 * delta * typical)
    print(f"  Break-even on a typical 0.50% SPX move at median spread: {need*100:.1f}%")
    if need > ceiling:
        print(f"\n  HURDLE EXCEEDS CEILING by {(need-ceiling)*100:.1f} points.")
        print("  A directional 0DTE options trade is not payable at the best")
        print("  accuracy anyone has demonstrated. The binding constraint is the")
        print("  spread, not the signal -- so more signal research cannot fix it.")
    else:
        print(f"\n  Ceiling clears the hurdle by {(ceiling-need)*100:.1f} points -- "
              "worth pursuing.")


if __name__ == "__main__":
    main()
