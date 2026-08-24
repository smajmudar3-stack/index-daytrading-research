"""Validate the Baltussen dealer-gamma split on our own SPXW chains.

Baltussen, Da, Lammers & Martens (JFE 142, 2021) report that the rest-of-day
return predicts the last half hour ONLY when dealers are short gamma:

    NGE >= 0 (dealers long gamma)    beta 0.82   t 1.03   R2 0.05%
    NGE <  0 (dealers short gamma)   beta 6.63   t 4.78   R2 3.58%

Their sample ends May 2020, before the 0DTE era that plausibly changed the
mechanism. This tests it on 2016-2024 SPXW data, with 2020-2024 as the
out-of-sample extension.

TWO HONEST DEVIATIONS FROM THE PAPER, both forced by the data:

  1. Their NGE uses the FULL SPX option surface. This panel covers +/-2%
     moneyness on same-day options, so what is computed here is a 0DTE net
     gamma. Gamma is concentrated near the money so the truncation is not
     fatal, but this is a different quantity and is labelled NGE_0DTE
     throughout. It is arguably the more relevant one post-2022, and it is
     exactly what Dim/Eraker/Vilkov study.

  2. Their r_ROD runs from the OPEN. This panel starts at 10:00, so r_ROD is
     10:00 -> 15:30.

NO LOOK-AHEAD: gamma is measured at the 10:00 snapshot, r_ROD ends at 15:30,
and the traded window is 15:30 -> 16:00. Every input precedes the trade.

Sign convention follows the paper: dealers are assumed long calls and short
puts, so NGE = sum(gamma*OI over calls) - sum(gamma*OI over puts).
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")
T1000 = pd.Timestamp("10:00").time()
T1530 = pd.Timestamp("15:30").time()
T1600 = pd.Timestamp("16:00").time()


def build():
    df = pd.read_parquet(SPXW, columns=["quote_date", "quote_time", "option_type",
                                        "oi_gamma", "active_underlying_price"])
    df["quote_date"] = pd.to_datetime(df["quote_date"])

    # --- net gamma at 10:00, signed calls-minus-puts -----------------------
    snap = df[df.quote_time == T1000]
    sgn = np.where(snap.option_type.values == "C", 1.0, -1.0)
    nge = (snap.assign(g=snap.oi_gamma.values * sgn)
               .groupby("quote_date")["g"].sum())

    # --- the price path ----------------------------------------------------
    px = (df.groupby(["quote_date", "quote_time"])["active_underlying_price"]
            .median().unstack())
    need = [T1000, T1530, T1600]
    if not all(t in px.columns for t in need):
        raise SystemExit("missing required snapshot times")
    px = px[need].dropna()

    d = pd.DataFrame({
        "r_rod": px[T1530] / px[T1000] - 1,
        "r_lh":  px[T1600] / px[T1530] - 1,
    })
    d["nge"] = nge.reindex(d.index)
    return d.dropna()


def split_report(tag, d):
    print(f"\n  {tag}   n = {len(d):,}   "
          f"{d.index.min().date()} -> {d.index.max().date()}")
    neg = d[d.nge < 0]
    pos = d[d.nge >= 0]
    print(f"    dealers SHORT gamma on {len(neg):,} days "
          f"({len(neg)/len(d)*100:.1f}%), LONG on {len(pos):,}")

    print(f"    {'regime':28s} {'beta':>8s} {'t':>7s} {'R2':>8s} {'n':>7s}")
    out = {}
    for lab, s in (("NGE >= 0 (dealers long)", pos), ("NGE <  0 (dealers short)", neg)):
        if len(s) < 30:
            print(f"    {lab:28s} {'too few days':>32s}")
            continue
        sl, ic, r, p, se = stats.linregress(s.r_rod, s.r_lh)
        t = sl / se if se > 0 else 0.0
        print(f"    {lab:28s} {sl:8.2f} {t:7.2f} {r*r*100:7.2f}% {len(s):7,d}")
        out[lab] = (sl, t, r * r)

    # The tradeable version: sign-following into the last half hour.
    for lab, s in (("long-gamma days", pos), ("short-gamma days", neg)):
        if len(s) < 30:
            continue
        pnl = np.sign(s.r_rod) * s.r_lh
        tt = pnl.mean() / (pnl.std(ddof=1) / np.sqrt(len(pnl)))
        print(f"    sign-follow, {lab:18s} {pnl.mean()*1e4:+7.2f} bp  "
              f"t = {tt:+5.2f}  hit {(pnl>0).mean()*100:.1f}%")
    return out


def main():
    d = build()
    print("=" * 92)
    print("DEALER-GAMMA CONDITIONED INTRADAY MOMENTUM -- SPXW, our own chains")
    print("=" * 92)
    print("  NGE_0DTE measured at 10:00; r_ROD = 10:00->15:30; traded 15:30->16:00.")
    print(f"  NGE_0DTE: median {d.nge.median():,.0f}   "
          f"negative on {(d.nge < 0).mean()*100:.1f}% of days")

    split_report("FULL SAMPLE", d)
    split_report("BALTUSSEN ERA  (<= 2020-05)", d[d.index <= "2020-05-31"])
    split_report("OUT OF SAMPLE  (>  2020-05)", d[d.index > "2020-05-31"])

    # Continuous interaction, the paper's Table 8 form.
    print("\n" + "=" * 92)
    print("  CONTINUOUS INTERACTION  r_LH ~ r_ROD + NGE*r_ROD")
    print("=" * 92)
    z = (d.nge - d.nge.mean()) / d.nge.std()
    X = np.column_stack([np.ones(len(d)), d.r_rod.values, (z * d.r_rod).values])
    beta, *_ = np.linalg.lstsq(X, d.r_lh.values, rcond=None)
    resid = d.r_lh.values - X @ beta
    s2 = resid @ resid / (len(d) - 3)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    for nm, b, e in zip(["intercept", "r_ROD", "NGE x r_ROD"], beta, se):
        print(f"    {nm:14s} {b:10.3f}   t = {b/e:+6.2f}")
    print("\n  Baltussen predict a NEGATIVE interaction: more negative gamma,")
    print("  stronger momentum. A positive or insignificant term does not replicate.")


if __name__ == "__main__":
    main()
