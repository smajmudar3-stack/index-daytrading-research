"""Does the FULL gamma picture predict the move better than one quintile?

The structure panel currently keys off a single number, the gamma quintile. The
objection is fair: net GEX level, distance to the flip, where the walls sit and
how concentrated the gamma is are all gamma facts, and a structure choice that
ignores them is using a fraction of what is known.

So this measures each of them against the thing the range read actually claims:
realised range as a fraction of the day's implied move. The range read says that
ratio is 0.843 on high-gamma days and 1.139 on low-gamma days, t = -13.2. If the
richer features carry information the quintile does not, they will beat it here.
If they do not, the panel should keep using the simple one.

FEATURES, all computable at 10:00 from the chain alone:
  net_gamma      signed calls-minus-puts oi_gamma, the quintile's own input
  flip_dist      how far spot sits from the zero-gamma crossing, in percent
  wall_width     call wall minus put wall, as a percent of spot -- the width of
                 the corridor dealer hedging defends
  wall_pos       where spot sits inside that corridor, 0 at the put wall, 1 at
                 the call wall
  concentration  share of total absolute gamma sitting in the top 3 strikes; a
                 tight cluster pins harder than the same gamma spread thin
  next_up/dn     distance to the next significant gamma strike above and below

TARGET: realised high-low range over 10:00 -> 16:00, divided by the ATM straddle
price at 10:00. That is the model-free ratio, and it needs no pricing assumption.
"""
import os
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPXW = os.path.join(ROOT, "data", "spxw", "data_opt.parquet")


def build():
    d = pd.read_parquet(SPXW, columns=[
        "quote_date", "quote_time", "option_type", "mnes_rel", "mid",
        "oi_gamma", "active_underlying_price"])
    d["quote_date"] = pd.to_datetime(d["quote_date"])
    d["px"] = d.mid * d.active_underlying_price
    d["k"] = d.mnes_rel * d.active_underlying_price

    t10 = pd.Timestamp("10:00").time()
    rows = []
    for day, g in d.groupby("quote_date"):
        s = g[g.quote_time == t10]
        if s.empty:
            continue
        spot = float(s.active_underlying_price.median())

        # signed dealer gamma by strike: long calls, short puts
        sgn = np.where(s.option_type.values == "C", 1.0, -1.0)
        prof = (s.assign(dg=s.oi_gamma.values * sgn)
                  .groupby("k")["dg"].sum().sort_index())
        if len(prof) < 8:
            continue
        net = float(prof.sum())

        # zero crossing of cumulative gamma = the flip
        cum = prof.cumsum()
        flip = spot
        sign_change = np.where(np.diff(np.sign(cum.values)) != 0)[0]
        if len(sign_change):
            flip = float(cum.index[sign_change[0]])

        pos_k = prof[prof > 0]
        neg_k = prof[prof < 0]
        call_wall = float(pos_k.idxmax()) if len(pos_k) else spot
        put_wall = float(neg_k.idxmin()) if len(neg_k) else spot
        if call_wall < put_wall:
            call_wall, put_wall = put_wall, call_wall

        absg = prof.abs()
        conc = float(absg.nlargest(3).sum() / absg.sum()) if absg.sum() > 0 else np.nan

        above = prof[prof.index > spot]
        below = prof[prof.index < spot]
        next_up = float(above.abs().idxmax() - spot) / spot if len(above) else np.nan
        next_dn = float(spot - below.abs().idxmax()) / spot if len(below) else np.nan

        # ATM straddle at 10:00 = the day's implied move
        atm = s.iloc[(s.mnes_rel - 1.0).abs().argsort()[:4]]
        c = atm[atm.option_type == "C"].px.mean()
        p = atm[atm.option_type == "P"].px.mean()
        if not np.isfinite(c) or not np.isfinite(p) or (c + p) <= 0:
            continue
        implied = float(c + p)

        rest = g[g.quote_time >= t10]
        rng = float(rest.active_underlying_price.max() - rest.active_underlying_price.min())

        width = (call_wall - put_wall) / spot
        rows.append(dict(
            day=day, ratio=rng / implied,
            net_gamma=net, flip_dist=(spot - flip) / spot,
            wall_width=width,
            wall_pos=((spot - put_wall) / (call_wall - put_wall)
                      if call_wall > put_wall else np.nan),
            concentration=conc, next_up=next_up, next_dn=next_dn,
        ))
    return pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna()


def main():
    f = build()
    print("=" * 92)
    print("DOES THE FULL GAMMA PICTURE PREDICT THE MOVE BETTER THAN ONE QUINTILE?")
    print("=" * 92)
    print(f"  {len(f):,} sessions · target = realised range / implied move at 10:00")
    print(f"  target: mean {f.ratio.mean():.3f}, median {f.ratio.median():.3f}\n")

    feats = ["net_gamma", "flip_dist", "wall_width", "wall_pos",
             "concentration", "next_up", "next_dn"]
    split = int(len(f) * 0.6)
    tr, te = f.iloc[:split], f.iloc[split:]

    print(f"  {'feature':16s} {'IC(train)':>10s} {'IC(test)':>10s} {'t(test)':>9s}  holds?")
    keep = []
    for c in feats:
        ic_tr = stats.spearmanr(tr[c], tr.ratio)[0]
        ic_te, p_te = stats.spearmanr(te[c], te.ratio)
        t = ic_te * np.sqrt((len(te) - 2) / max(1e-9, 1 - ic_te ** 2))
        ok = (np.sign(ic_tr) == np.sign(ic_te)) and abs(t) > 1.96
        keep.append((c, ic_tr, ic_te, t, ok))
        print(f"  {c:16s} {ic_tr:+10.3f} {ic_te:+10.3f} {t:+9.2f}  "
              f"{'YES' if ok else 'no'}")

    print(f"\n  QUINTILE BASELINE — the panel's current single input")
    q = pd.qcut(f.net_gamma, 5, labels=False, duplicates="drop") + 1
    for qi in sorted(q.unique()):
        x = f.ratio[q == qi]
        print(f"    Q{int(qi)}  n={len(x):4d}  realised/implied {x.mean():.3f}")
    ic_q_tr = stats.spearmanr(q[:split], tr.ratio)[0]
    ic_q_te, _ = stats.spearmanr(q[split:], te.ratio)
    print(f"    quintile IC: train {ic_q_tr:+.3f}, test {ic_q_te:+.3f}")

    surv = [k for k in keep if k[4]]
    print("\n" + "=" * 92)
    if not surv:
        print("  NO gamma feature holds out of sample. The panel should keep using")
        print("  the quintile, because nothing richer survives the split.")
    else:
        print(f"  {len(surv)} feature(s) hold out of sample:")
        for c, a, b, t, _ in surv:
            print(f"    {c:16s} IC train {a:+.3f} -> test {b:+.3f}, t {t:+.2f}")
        print("\n  Multivariate check — do they add over the quintile alone?")
        cols = [c for c, *_ in surv]
        X_tr = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in cols])
        beta, *_ = np.linalg.lstsq(X_tr, tr.ratio.values, rcond=None)
        X_te = np.column_stack([np.ones(len(te))] + [te[c].values for c in cols])
        pred = X_te @ beta
        r_multi = stats.spearmanr(pred, te.ratio)[0]
        print(f"    combined IC on test: {r_multi:+.3f}  vs quintile {ic_q_te:+.3f}")
        print(f"    -> {'richer picture wins' if abs(r_multi) > abs(ic_q_te) else 'quintile is as good'}")
    print("=" * 92)


if __name__ == "__main__":
    main()
