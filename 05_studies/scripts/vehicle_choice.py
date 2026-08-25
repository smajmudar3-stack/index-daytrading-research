"""At a 53% hit rate, which vehicle actually pays: stock, ATM call, OTM, or deep ITM?

The short-interest signal measures IC -0.107 at 63 days, which converts to a hit
rate of about 53.4% (p = 0.5 + arcsin(rho)/pi). Before writing any option ticket
it is worth knowing whether an option is the right instrument at all.

Being directionally right is NOT the same as an option paying. A long call needs
the move to exceed the premium; a 53% signal on a symmetric move distribution can
be right more often than not and still lose to the premium. Deep-ITM options
behave like stock with leverage and pay on the mean shift itself.

Method: real SPY chains at ~60 DTE, held to expiry against the actual close.
Rather than assume a signal, RESAMPLE the real outcomes so the simulated signal
has exactly the measured 53.4% accuracy -- that is, pick the correct direction
53.4% of the time and the wrong one otherwise, then price the real contract.

Entry at the ask (buying), settlement at intrinsic. No exit spread, consistent
with the hold-to-expiry finding.
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT = os.path.join(ROOT, "data", "opt_eod", "SPY_options.parquet")
ACC = 0.534          # implied by IC -0.107 at 63d
SEED = 12345
TRIALS = 400


def main():
    d = pd.read_parquet(OPT, columns=["date", "expiration", "strike", "type",
                                      "bid", "ask", "delta", "open_interest"])
    d["date"] = pd.to_datetime(d["date"])
    d["expiration"] = pd.to_datetime(d["expiration"])
    d["dte"] = (d.expiration - d["date"]).dt.days
    d["cp"] = d.type.str.lower().str[0]
    d = d[(d.dte >= 50) & (d.dte <= 75) & d.delta.notna()]
    d = d[~(((d.cp == "c") & (d.delta <= 0)) | ((d.cp == "p") & (d.delta >= 0)))]

    u = pd.read_parquet(os.path.join(ROOT, "data", "opt_eod",
                                     "SPY_underlying.parquet"),
                        columns=["date", "close"])
    u["date"] = pd.to_datetime(u["date"])
    S = u.drop_duplicates("date").set_index("date")["close"].sort_index()

    def pick(g, target):
        g = g[(g.ask > 0) & (g.ask >= g.bid) & (g.open_interest > 5)]
        if g.empty:
            return None
        i = (g.delta.abs() - target).abs()
        j = i.idxmin()
        return g.loc[j] if i.loc[j] <= 0.06 else None

    VEH = [("stock", None), ("deep ITM 0.85d", 0.85), ("ITM 0.70d", 0.70),
           ("ATM 0.50d", 0.50), ("OTM 0.30d", 0.30), ("far OTM 0.16d", 0.16)]

    rows = []
    for (dt, exp), g in d.groupby(["date", "expiration"]):
        if exp not in S.index or dt not in S.index:
            continue
        s0, sT = S[dt], S[exp]
        rec = dict(date=dt, exp=exp, s0=s0, sT=sT, ret=sT / s0 - 1)
        ok = True
        for nm, tgt in VEH:
            if tgt is None:
                continue
            c = pick(g[g.cp == "c"], tgt)
            p = pick(g[g.cp == "p"], tgt)
            if c is None or p is None:
                ok = False
                break
            rec[f"{nm}|c_cost"] = c.ask
            rec[f"{nm}|c_pay"] = max(0.0, sT - c.strike)
            rec[f"{nm}|p_cost"] = p.ask
            rec[f"{nm}|p_pay"] = max(0.0, p.strike - sT)
        if ok:
            rows.append(rec)

    r = pd.DataFrame(rows).sort_values("date").drop_duplicates("exp", keep="first")
    print(f"  {len(r):,} non-overlapping 50-75 DTE cycles, "
          f"{r.date.min().date()} -> {r.date.max().date()}")
    print(f"  simulating a signal with {ACC*100:.1f}% directional accuracy "
          f"({TRIALS} resamples)\n")

    truth = np.sign(r.ret.values)
    truth[truth == 0] = 1
    rng = np.random.default_rng(SEED)

    print("=" * 88)
    print(f"  {'vehicle':16s} {'mean ret':>10s} {'median':>9s} {'win%':>7s} "
          f"{'t':>7s} {'worst':>9s}  {'verdict'}")
    print("=" * 88)

    for nm, tgt in VEH:
        means, wins, ts = [], [], []
        for _ in range(TRIALS):
            correct = rng.random(len(r)) < ACC
            call = np.where(correct, truth > 0, truth < 0)   # go long when signal says up
            if tgt is None:
                pnl = np.where(call, r.ret.values, -r.ret.values)
            else:
                cost = np.where(call, r[f"{nm}|c_cost"], r[f"{nm}|p_cost"])
                pay = np.where(call, r[f"{nm}|c_pay"], r[f"{nm}|p_pay"])
                pnl = (pay - cost) / cost                    # return on premium
            means.append(pnl.mean())
            wins.append((pnl > 0).mean())
            ts.append(pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl))))
        m, w, t = np.mean(means), np.mean(wins), np.mean(ts)
        worst = np.min(means)
        v = "PAYS" if t > 2 else "marginal" if t > 0 else "LOSES"
        print(f"  {nm:16s} {m*100:+9.2f}% {np.median(means)*100:+8.2f}% "
              f"{w*100:6.1f}% {t:+7.2f} {worst*100:+8.2f}%  {v}")

    print("=" * 88)
    print("  Option rows are return on PREMIUM PAID; stock is return on notional,")
    print("  so they are not directly comparable in magnitude -- only in sign and t.")
    print("  A vehicle that loses here cannot be rescued by a better strike.")


if __name__ == "__main__":
    main()
