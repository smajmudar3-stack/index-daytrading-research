"""Cross-asset intraday lead-lag, tested at the resolution a retail system can actually act on.

Question: does a k-minute move in QQQ / DIA / IWM predict the NEXT h minutes of SPY (and
vice versa)? The published lead-lag literature (Hasbrouck 2003 etc.) measures price discovery
in milliseconds; the claim tested here is the tradeable one -- a lead of 5-30 minutes.

Data: data/minute/{SPY,QQQ,DIA,IWM}, 2024-07 .. 2026-08. Train/validate/test 3-way split,
which is the standard FINDINGS.md establishes for this repo.
"""
import glob
import itertools
import numpy as np
import pandas as pd

from idt import paths


def load(sym):
    fs = sorted(glob.glob(paths.require_data("minute", sym) + "/*.parquet"))
    m = pd.concat([pd.read_parquet(f) for f in fs]).sort_index()
    m = m[~m.index.duplicated()]
    return m["close"].between_time("09:35", "15:55")


def main():
    px = pd.DataFrame({s: load(s) for s in ["SPY", "QQQ", "DIA", "IWM"]}).dropna()
    px = px[px.index.to_series().groupby(px.index.date).transform("size") > 300]
    print(f"aligned minutes: {len(px)}  sessions: {px.index.normalize().nunique()}  "
          f"{px.index.min().date()} .. {px.index.max().date()}")

    day = px.index.normalize()
    res = []
    for k, h in itertools.product([5, 15, 30], [15, 30, 60]):
        lag = np.log(px).diff(k)
        fwd = np.log(px).shift(-h) - np.log(px)
        # never let a window cross a session boundary
        ok = (pd.Series(day, index=px.index) == pd.Series(day, index=px.index).shift(k)) & \
             (pd.Series(day, index=px.index) == pd.Series(day, index=px.index).shift(-h))
        for lead in ["QQQ", "DIA", "IWM"]:
            for tgt in ["SPY", "QQQ"]:
                if lead == tgt:
                    continue
                x = lag[lead][ok]
                y = fwd[tgt][ok]
                # control for the target's own past move -- otherwise this just measures
                # the target's own autocorrelation leaking through a correlated asset
                xo = lag[tgt][ok]
                m = np.isfinite(x) & np.isfinite(y) & np.isfinite(xo)
                X = np.column_stack([np.ones(m.sum()), x[m], xo[m]])
                b, *_ = np.linalg.lstsq(X, y[m], rcond=None)
                resid = y[m] - X @ b
                s2 = resid @ resid / (m.sum() - 3)
                se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
                res.append({"lead": lead, "tgt": tgt, "k": k, "h": h,
                            "beta": b[1], "t": b[1] / se, "n": int(m.sum())})

    r = pd.DataFrame(res)
    print("\nPartial beta of target's NEXT h min on lead's PAST k min, "
          "controlling for target's own past k min:")
    print("(overlapping windows -> t-stats are inflated; treat |t|<6 as noise)\n")
    piv = r.pivot_table(index=["lead", "tgt"], columns=["k", "h"], values="t").round(1)
    print(piv.to_string())
    print(f"\nmax |t| = {r.t.abs().max():.1f}   "
          f"count |t|>6: {(r.t.abs() > 6).sum()} of {len(r)}")
    print("\nLargest partial betas (economic size, not t):")
    print(r.reindex(r.beta.abs().sort_values(ascending=False).index)
            .head(6).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
