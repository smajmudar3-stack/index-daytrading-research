"""Is the signal better than buying a call on a RANDOM day? The decisive test.

An option strategy can show a fine win rate and a fine return purely because
SPY went up 2008-2025 and calls are levered. The only question that matters is
whether the SIGNAL adds anything over the same structure entered
unconditionally.

So every conditional result here is measured against the identical structure
traded on every available date -- same DTE window, same delta, same holding
period, same real bid/ask. If the excess is not positive and stable across
train/validate/test, the signal is decoration on top of beta.

The signal under test is `backward + golden`: VIX above VIX3M (term-structure
backwardation, i.e. a volatility spike) while the 50dma is above the 200dma.
It is the only rule from the earlier sweep whose EXCESS mean return over the
unconditional base rate stayed positive and significant in all three splits;
the dip-buying rules did not, and are excluded here for that reason.
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

SWING = paths.data("swing", "panel.parquet")
OPT = paths.data("opt_eod", "SPY_options.parquet")

SPLITS = {"2008-2013": ("2008-01-01", "2013-12-31"),
          "2014-2019": ("2014-01-01", "2019-12-31"),
          "2020-2025": ("2020-01-01", "2025-12-31")}

DELTAS = [0.80, 0.70, 0.50, 0.30]
HOLDS = [5, 10, 21]
MIN_DTE, MAX_DTE = 30, 70


def build():
    p = pd.read_parquet(paths.require_data(SWING))
    close = p.pivot(index="date", columns="ticker", values="close").sort_index()
    spy = close["SPY"]
    golden = (spy.rolling(50).mean() > spy.rolling(200).mean()).astype(float)
    backward = (close["^VIX"] / close["^VIX3M"] >= 1.0).astype(float)
    sig = ((backward > 0) & (golden > 0)).shift(1).fillna(False)
    return close, spy, sig


def load_all():
    cols = ["date", "expiration", "strike", "type", "bid", "ask", "delta",
            "open_interest"]
    frames = []
    for y in range(2008, 2026):
        t = pq.read_table(paths.require_data(OPT), columns=cols, filters=[
            ("date", ">=", pd.Timestamp(f"{y}-01-01")),
            ("date", "<=", pd.Timestamp(f"{y}-12-31"))]).to_pandas()
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t["date"])
        t["expiration"] = pd.to_datetime(t["expiration"])
        t["dte"] = (t["expiration"] - t["date"]).dt.days
        t = t[(t.type == "call") & (t.dte.between(MIN_DTE, MAX_DTE)) &
              (t.bid > 0.05) & (t.ask > t.bid) & (t.open_interest > 10) &
              (t.delta.between(0.05, 0.95))]
        frames.append(t)
        print(f"  {y} loaded", flush=True)
    return pd.concat(frames, ignore_index=True)


def trade_returns(ch, dates, hold_days, target_delta, all_dates):
    """Buy a call at the ask, sell it `hold_days` sessions later at the bid."""
    by_date = {d: g for d, g in ch.groupby("date")}
    pos = {d: i for i, d in enumerate(all_dates)}
    out = []
    for d0 in dates:
        if d0 not in by_date or d0 not in pos:
            continue
        i = pos[d0] + hold_days
        if i >= len(all_dates):
            continue
        d1 = all_dates[i]
        if d1 not in by_date:
            continue
        day = by_date[d0]
        # One expiry, nearest 45 DTE, then nearest delta inside it.
        exp = day.loc[(day.dte - 45).abs().idxmin(), "expiration"]
        leg = day[day.expiration == exp]
        row = leg.loc[(leg.delta - target_delta).abs().idxmin()]
        ex = by_date[d1]
        m = ex[(ex.strike == row.strike) & (ex.expiration == row.expiration)]
        if m.empty or row.ask <= 0:
            continue
        out.append((d0, (m.iloc[0].bid - row.ask) / row.ask))
    return pd.DataFrame(out, columns=["date", "ret"])


def main():
    close, spy, sig = build()
    print("loading real SPY call chains ...")
    ch = load_all()
    all_dates = sorted(ch.date.unique())
    print(f"  {len(ch):,} call-days over {len(all_dates)} sessions\n")

    sig_dates = [d for d in all_dates if bool(sig.get(d, False))]
    print(f"signal fires on {len(sig_dates)} of {len(all_dates)} sessions "
          f"({len(sig_dates)/len(all_dates):.1%})\n")

    print("=" * 100)
    print("SIGNAL vs UNCONDITIONAL -- identical structure, real bid/ask")
    print("=" * 100)
    print(f"  {'delta':>5s} {'hold':>4s} {'split':10s} "
          f"{'n_sig':>5s} {'sig win':>8s} {'sig avg':>9s} | "
          f"{'base win':>8s} {'base avg':>9s} | {'EXCESS':>9s} {'t':>6s}")

    rows = []
    for td in DELTAS:
        for h in HOLDS:
            base_all = trade_returns(ch, all_dates, h, td, all_dates)
            sig_all = trade_returns(ch, sig_dates, h, td, all_dates)
            if base_all.empty or sig_all.empty:
                continue
            for sname, (a, b) in SPLITS.items():
                bs = base_all[(base_all.date >= a) & (base_all.date <= b)].ret
                ss = sig_all[(sig_all.date >= a) & (sig_all.date <= b)].ret
                if len(ss) < 15 or len(bs) < 100:
                    continue
                exc = ss.mean() - bs.mean()
                se = ss.std() / np.sqrt(len(ss))
                t = exc / se if se > 0 else 0.0
                print(f"  {td:5.2f} {h:4d} {sname:10s} {len(ss):5d} "
                      f"{(ss>0).mean():8.1%} {ss.mean():+9.2%} | "
                      f"{(bs>0).mean():8.1%} {bs.mean():+9.2%} | "
                      f"{exc:+9.2%} {t:+6.2f}")
                rows.append({"delta": td, "hold": h, "split": sname,
                             "n": len(ss), "sig_win": (ss > 0).mean(),
                             "sig_avg": ss.mean(), "base_win": (bs > 0).mean(),
                             "base_avg": bs.mean(), "excess": exc, "t": t})
            print()

    res = pd.DataFrame(rows)
    res.to_parquet(paths.data("swing", "signal_vs_base.parquet"),
                   index=False)

    print("=" * 100)
    print("VERDICT -- configurations with POSITIVE excess in ALL THREE splits")
    print("=" * 100)
    ok = []
    for (td, h), g in res.groupby(["delta", "hold"]):
        if len(g) == 3 and (g.excess > 0).all():
            ok.append((td, h, g.excess.mean(), g.t.min(), g.sig_win.mean(),
                       g.base_win.mean()))
    if not ok:
        print("  NONE. The signal does not beat unconditional entry consistently.")
    else:
        print(f"  {'delta':>5s} {'hold':>4s} {'avg excess':>11s} {'worst t':>8s} "
              f"{'sig win':>8s} {'base win':>9s}")
        for td, h, e, tmin, sw, bw in sorted(ok, key=lambda x: -x[2]):
            print(f"  {td:5.2f} {h:4d} {e:+11.2%} {tmin:+8.2f} {sw:8.1%} {bw:9.1%}")


if __name__ == "__main__":
    main()
