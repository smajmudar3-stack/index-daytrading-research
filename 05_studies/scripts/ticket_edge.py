"""What is the actual expected edge on the ticket basket, over time?

Everything so far established the signal is real and small. This puts numbers on
what that means per 63-day cycle and per year, and nets out what it costs to
express it through options rather than through the stock.

The honest way to compare an option to a stock is per unit of DELTA EXPOSURE,
not per unit of premium. A deep-ITM put with delta -0.85 on an $18.75 stock
controls 0.85 x 100 x 18.75 = $1,594 of short exposure. Both the edge and the
costs are therefore expressed as a percentage of that exposure.

  EDGE     hit rate p = 0.5 + arcsin(IC)/pi = 53.4% at IC -0.107.
           Expected capture = (2p - 1) x E|move| over the horizon.

  THETA    extrinsic / exposure. This is the part the option costs and the
           stock does not. It is paid whether or not the call is right.

  SPREAD   half the quoted bid-ask, relative to exposure. Paid once, because
           the position is held to expiry and settles at intrinsic.

  BORROW   what shorting the stock would cost instead, so the comparison is
           fair -- these are hard-to-borrow names.
"""
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IC = 0.107
HORIZON = 63
BORROW_ANNUAL = 0.05        # 5%/yr, generous for hard-to-borrow small caps


def main():
    import yfinance as yf
    with open(os.path.join(ROOT, "data", "tickets.json")) as f:
        tk = json.load(f)["res"]["tickets"]
    if not tk:
        print("no tickets cached"); return

    syms = [t["ticker"] for t in tk]
    raw = yf.download(syms, period="1y", progress=False,
                      auto_adjust=True, threads=False)
    hist = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
    # Compute spot here rather than trusting the cache: the dashboard's
    # background rebuild can overwrite tickets.json without the decay fields.
    for t in tk:
        if t["ticker"] in hist.columns:
            s_ = float(hist[t["ticker"]].dropna().iloc[-1])
            t["spot"] = s_
            intr = max(0.0, t["strike"] - s_)
            t["extrinsic"] = max(0.0, t["ask"] - intr)

    p = 0.5 + np.arcsin(IC) / np.pi
    print("=" * 102)
    print(f"EXPECTED EDGE PER {HORIZON}-DAY CYCLE, per unit of delta exposure")
    print("=" * 102)
    print(f"  IC {IC:.3f} -> hit rate {p*100:.1f}%  ->  capture = "
          f"(2p-1) = {(2*p-1)*100:.1f}% of the average move\n")
    print(f"  {'tkr':6s} {'ann vol':>8s} {'63d E|mv|':>10s} {'EDGE':>8s} "
          f"{'theta':>8s} {'spread':>8s} {'NET opt':>9s} {'NET stock':>10s}")

    rows = []
    for t in tk:
        s_ = t.get("spot")
        if not s_ or t["ticker"] not in hist.columns:
            continue
        r = np.log(hist[t["ticker"]].dropna()).diff().dropna()
        if len(r) < 60:
            continue
        vol = float(r.std() * np.sqrt(252))
        sig_h = vol * np.sqrt(HORIZON / 252)
        e_move = 0.798 * sig_h                       # E|N(0,s)| = s*sqrt(2/pi)
        edge = (2 * p - 1) * e_move

        expo = abs(t["delta"]) * 100 * s_
        theta = (t.get("extrinsic") or 0) * 100 / expo
        half_sp = (t["ask"] - t["bid"]) / 2 * 100 / expo
        borrow = BORROW_ANNUAL * HORIZON / 252

        net_opt = edge - theta - half_sp
        net_stk = edge - borrow - (0.001)            # ~10bp equity round trip
        rows.append((net_opt, net_stk, edge, theta, half_sp))
        print(f"  {t['ticker']:6s} {vol*100:7.0f}% {e_move*100:9.1f}% "
              f"{edge*100:+7.2f}% {theta*100:7.2f}% {half_sp*100:7.2f}% "
              f"{net_opt*100:+8.2f}% {net_stk*100:+9.2f}%")

    a = np.array(rows)
    no, ns, ed, th, sp = a[:, 0].mean(), a[:, 1].mean(), a[:, 2].mean(), a[:, 3].mean(), a[:, 4].mean()
    cyc = 252 / HORIZON
    print("\n" + "=" * 102)
    print(f"  {'basket average':22s} edge {ed*100:+.2f}%   theta {th*100:.2f}%   "
          f"spread {sp*100:.2f}%")
    print(f"  {'NET per cycle':22s} options {no*100:+.2f}%      "
          f"stock {ns*100:+.2f}%")
    print(f"  {'NET annualised':22s} options {no*cyc*100:+.2f}%      "
          f"stock {ns*cyc*100:+.2f}%   ({cyc:.1f} cycles/yr)")

    # Breadth: correlated names do not give independent bets.
    print("\n" + "=" * 102)
    print("  INFORMATION RATIO (Grinold): IR = IC x sqrt(breadth)")
    print("=" * 102)
    n = len(rows)
    try:
        c = np.log(hist.dropna()).diff().dropna().corr().values
        avg_rho = (c.sum() - n) / (n * (n - 1))
    except Exception:
        avg_rho = 0.5
    eff = n / (1 + (n - 1) * avg_rho)               # effective independent bets
    print(f"  {n} names, average pairwise correlation {avg_rho:.2f}")
    print(f"  -> effective independent bets per cycle: {eff:.1f} (not {n})")
    for label, br in (("naive (assumes independence)", n * cyc),
                      ("correlation-adjusted", eff * cyc)):
        print(f"  {label:32s} breadth {br:5.1f}  ->  IR {IC*np.sqrt(br):.2f}")

    print("\n" + "=" * 102)
    print("  The IR is gross of costs. The NET lines above are what remains after")
    print("  theta and spread, and they are the number that decides the trade.")


if __name__ == "__main__":
    main()
