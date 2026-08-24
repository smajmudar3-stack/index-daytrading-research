"""hunt_conditional.py — push the FADE hit rate from ~53% toward 60%.

The fade edge is established. This asks a narrower question: GIVEN a fade trigger has fired, which
conditions separate the winners from the losers? That is a much cleaner classification problem than
predicting the market cold, and it is where a hit-rate improvement is most likely to come from.

Every trade is tagged with its full feature vector at entry. Conditions are screened on TRAIN and
confirmed on TEST; anything that flips sign between the two is discarded rather than reported.
"""
import numpy as np
import pandas as pd

import bt_options as bo
import hunt_features as HF

SPREAD, FEE, SESSION_MIN = 0.010, 0.05, 390

TAG = ["ret5", "ret15", "ret30", "ret60", "accel", "vwap_dist", "vwap_slope", "rvol", "rvol5",
       "vol_trend", "tr", "atr", "rv30", "rv_ratio", "body", "upper_wick", "lower_wick", "tod",
       "since_open", "range_pos", "range_pct", "or_pos", "or_width", "ext20", "ext60", "rsi",
       "gz", "dz", "conf", "sig_hat", "streak"]


def opt(S, K, ml, iv, call):
    return bo.bs(S, K, max(ml, 0.5) / SESSION_MIN / 252.0, iv, call)


def fade_trades(df, hold=20, tp=1.00, stop=-0.50, min_rvol=1.2):
    """One fade trade per session, tagged with every feature at entry."""
    rows = []
    for date, g in df.groupby("date"):
        iv = float(g.sig_hat.iloc[0]) * bo.SQRT252 if np.isfinite(g.sig_hat.iloc[0]) else np.nan
        if not np.isfinite(iv) or iv <= 0:
            continue
        live = g[(g.mins >= 600) & (g.mins <= 780)]
        ent = None
        for ts, r in live.iterrows():
            if np.isfinite(r.rvol) and r.rvol >= min_rvol:
                ent = r
                break
        if ent is None:
            continue
        call = ent.close < ent.vwap                       # FADE: below vwap -> calls
        S0, m0 = ent.close, ent.mins
        K = round(S0)
        e_mid = opt(S0, K, SESSION_MIN - (m0 - 570), iv, call)
        if e_mid <= 0.05:
            continue
        entry = e_mid * (1 + SPREAD) + FEE / 100.0
        path = g[(g.mins > m0) & (g.mins <= min(m0 + hold, 955))]
        ret = None
        for ts, r in path.iterrows():
            ml = SESSION_MIN - (r.mins - 570)
            adv = r.low if call else r.high
            fav = r.high if call else r.low
            if (opt(adv, K, ml, iv, call) * (1 - SPREAD) - entry) / entry <= stop:
                ret = stop; break
            if (opt(fav, K, ml, iv, call) * (1 - SPREAD) - entry) / entry >= tp:
                ret = tp; break
        if ret is None and len(path):
            last = path.iloc[-1]
            ret = (opt(last.close, K, SESSION_MIN - (last.mins - 570), iv, call) * (1 - SPREAD) - entry) / entry
        if ret is None:
            continue
        rec = {"date": date, "ret": ret, "win": int(ret > 0), "call": int(call)}
        for f in TAG:
            rec[f] = float(ent[f]) if f in ent and np.isfinite(ent[f]) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def screen(tr, te, feats):
    """Terciles on TRAIN; report win rate in low/high tercile on both halves. Keep only sign-stable."""
    print(f"\n{'feature':13}{'TR lo':>8}{'TR hi':>8}{'TE lo':>8}{'TE hi':>8}{'TEspread':>10}{'n te hi':>9}")
    print("-" * 64)
    keep = []
    for f in feats:
        s = tr[f].replace([np.inf, -np.inf], np.nan)
        if s.notna().sum() < 60:
            continue
        lo, hi = np.nanpercentile(s, [33, 67])
        if not np.isfinite([lo, hi]).all() or lo == hi:
            continue
        def wr(d, m):
            x = d[m]
            return (x.win.mean() * 100, len(x)) if len(x) >= 20 else (np.nan, len(x))
        a_lo, _ = wr(tr, tr[f] <= lo); a_hi, _ = wr(tr, tr[f] >= hi)
        b_lo, nl = wr(te, te[f] <= lo); b_hi, nh = wr(te, te[f] >= hi)
        if not np.isfinite([a_lo, a_hi, b_lo, b_hi]).all():
            continue
        sa, sb = a_hi - a_lo, b_hi - b_lo
        stable = (sa > 0) == (sb > 0) and abs(sb) > 4
        print(f"{f:13}{a_lo:>7.0f}%{a_hi:>7.0f}%{b_lo:>7.0f}%{b_hi:>7.0f}%{sb:>+9.0f}{nh:>9}"
              + ("  <-" if stable else ""))
        if stable:
            keep.append((f, lo, hi, sb))
    return keep


def main():
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    df = HF.load(sym); df = HF.add_features(df); df = HF.add_daily(df)
    dates = sorted(df.date.unique()); split = dates[len(dates) // 2]
    t = fade_trades(df)
    t["dt"] = pd.to_datetime(t.date)
    tr, te = t[t.dt < split], t[t.dt >= split]
    print(f"{sym} FADE trades: {len(t)} total | TRAIN {len(tr)} win {tr.win.mean()*100:.1f}% "
          f"| TEST {len(te)} win {te.win.mean()*100:.1f}%")
    keep = screen(tr, te, TAG)
    print(f"\nSIGN-STABLE conditions: {[k[0] for k in keep]}")

    # stack the stable ones and see how far the hit rate moves
    if keep:
        print("\nSTACKING the stable conditions (TEST only):")
        mask_tr = pd.Series(True, index=tr.index)
        mask_te = pd.Series(True, index=te.index)
        for f, lo, hi, sb in sorted(keep, key=lambda k: -abs(k[3])):
            side_hi = sb > 0
            mtr = (tr[f] >= hi) if side_hi else (tr[f] <= lo)
            mte = (te[f] >= hi) if side_hi else (te[f] <= lo)
            mask_tr &= mtr.fillna(False)
            mask_te &= mte.fillna(False)
            a, b = tr[mask_tr], te[mask_te]
            if len(b) < 12:
                print(f"  + {f:12} -> TEST n={len(b)} too small, stopping")
                break
            print(f"  + {f:12} -> TRAIN n={len(a):3d} win {a.win.mean()*100:4.1f}% | "
                  f"TEST n={len(b):3d} win {b.win.mean()*100:4.1f}% avg {b.ret.mean()*100:+.1f}%")


if __name__ == "__main__":
    main()
