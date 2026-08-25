"""How much of each ticket's premium is time value that decays to zero?

The objection is the right instinct: buying options and holding to expiry
usually destroys value, because the extrinsic premium goes to zero no matter
what. That is exactly true for at-the-money and out-of-the-money contracts.

Deep in-the-money is the exception, and this quantifies it rather than asserting
it. For a put, intrinsic = max(0, strike - spot). Whatever is left is extrinsic,
and extrinsic is the only part guaranteed to decay away.

Reports for every live ticket:
  - intrinsic vs extrinsic today
  - extrinsic as a share of premium, which IS the theta bill
  - the breakeven: how far the stock must fall just to cover it
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    import yfinance as yf
    with open(os.path.join(ROOT, "data", "tickets.json")) as f:
        tk = json.load(f)["res"]["tickets"]
    if not tk:
        print("no tickets cached"); return

    syms = [t["ticker"] for t in tk]
    px = yf.download(syms, period="5d", progress=False,
                     auto_adjust=False, threads=False)["Close"]
    spot = {s: float(px[s].dropna().iloc[-1]) for s in syms if s in px.columns}

    print("=" * 100)
    print("TIME VALUE AT RISK -- how much of each premium decays to zero")
    print("=" * 100)
    print(f"  {'tkr':6s} {'spot':>8s} {'strike':>8s} {'paid':>8s} "
          f"{'intrinsic':>10s} {'extrinsic':>10s} {'theta bill':>11s} {'breakeven':>10s}")

    tot_prem = tot_ext = 0.0
    for t in tk:
        s = spot.get(t["ticker"])
        if s is None:
            continue
        paid = t["ask"]
        intr = max(0.0, t["strike"] - s)
        ext = max(0.0, paid - intr)
        share = ext / paid if paid else 0
        # breakeven at expiry: stock must be below strike - premium
        be = t["strike"] - paid
        need = (be / s - 1) * 100
        tot_prem += paid * t["qty"] * 100
        tot_ext += ext * t["qty"] * 100
        print(f"  {t['ticker']:6s} {s:8.2f} {t['strike']:8.2f} {paid:8.2f} "
              f"{intr:10.2f} {ext:10.2f} {share*100:10.1f}% {need:9.1f}%")

    print("\n" + "=" * 100)
    print(f"  basket premium        ${tot_prem:>10,.0f}")
    print(f"  of which time value   ${tot_ext:>10,.0f}   "
          f"({tot_ext/tot_prem*100:.1f}% of the money at risk)")
    print(f"  intrinsic (not decay) ${tot_prem-tot_ext:>10,.0f}   "
          f"({(tot_prem-tot_ext)/tot_prem*100:.1f}%)")
    print("=" * 100)
    print("  The time-value column is the ONLY part guaranteed to decay. The")
    print("  intrinsic part is not decay -- it moves one-for-one with the stock,")
    print("  which is the whole reason the evidence pointed to deep ITM.")
    print("\n  For comparison, an at-the-money put is ~100% extrinsic: every")
    print("  dollar is a bet against the clock.")


if __name__ == "__main__":
    main()
