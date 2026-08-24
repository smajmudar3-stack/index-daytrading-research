"""hunt_skew.py — intraday IV SKEW and the real GAMMA PROFILE, neither of which has been tested here.

Two genuinely unused dimensions of the SPXW file:

  1. IV SKEW at 30-minute resolution. Every gamma test so far used a prior-close DAILY z-score. The
     quote file carries implied vol across 41 moneyness buckets at every half hour, so the shape of
     the surface and how it MOVES intraday is available and has never been looked at. Risk-reversal
     steepening is a documented positioning signal.

  2. The actual intraday GAMMA PROFILE from open interest — net gamma at spot, and the level where
     net gamma crosses zero (the true intraday flip, not a daily proxy).

Scored the right way this time. The previous hunt was misled by measuring accuracy CONDITIONAL on a
clean move occurring, which is not an expected return — a signal hit 54-62% by that metric and
returned exactly zero when traded. Everything here is scored as the mean forward RETURN of a delta-1
position, across all signal bars, which is what a trade actually earns.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

PATH = "data/spxw/data_opt.parquet"


def build():
    df = pd.read_parquet(PATH, columns=[
        "quote_date", "quote_time", "option_type", "mnes_rel", "implied_volatility",
        "bas", "mid", "active_underlying_price", "open_interest", "trade_volume", "oi_gamma_usd"])
    df["tmin"] = pd.to_datetime(df.quote_time.astype(str)).dt.hour * 60 + \
                 pd.to_datetime(df.quote_time.astype(str)).dt.minute

    key = ["quote_date", "quote_time"]
    base = df.groupby(key).agg(spot=("active_underlying_price", "first"),
                               tmin=("tmin", "first"),
                               spread=("bas", "mean"),
                               oi_tot=("open_interest", "sum"),
                               vol_tot=("trade_volume", "sum")).reset_index()

    # ---- IV surface shape ------------------------------------------------------------
    def iv_at(typ, lo, hi, name):
        m = df[(df.option_type == typ) & (df.mnes_rel >= lo) & (df.mnes_rel <= hi)]
        return m.groupby(key).implied_volatility.mean().rename(name).reset_index()

    for frame in (iv_at("C", 0.999, 1.001, "atm_iv"),
                  iv_at("P", 0.988, 0.992, "otm_put_iv"),     # ~1% OTM put
                  iv_at("C", 1.008, 1.012, "otm_call_iv"),    # ~1% OTM call
                  iv_at("P", 0.978, 0.982, "far_put_iv")):
        base = base.merge(frame, on=key, how="left")

    base["skew"] = base.otm_put_iv - base.otm_call_iv          # risk reversal
    base["put_wing"] = base.far_put_iv - base.otm_put_iv       # tail steepness
    base["iv_level"] = base.atm_iv

    # ---- gamma profile ---------------------------------------------------------------
    gam = df.groupby(key).oi_gamma_usd.sum().rename("net_gamma").reset_index()
    base = base.merge(gam, on=key, how="left")
    # gamma at the money specifically
    gatm = df[(df.mnes_rel > 0.995) & (df.mnes_rel < 1.005)].groupby(
        key).oi_gamma_usd.sum().rename("gamma_atm").reset_index()
    base = base.merge(gatm, on=key, how="left")

    base = base.sort_values(["quote_date", "tmin"]).reset_index(drop=True)
    g = base.groupby("quote_date", group_keys=False)

    # ---- CHANGES (the actual signal candidates) ---------------------------------------
    for c in ("skew", "iv_level", "put_wing", "net_gamma", "spread"):
        base[f"d_{c}"] = g[c].apply(lambda s: s.diff())
        # EXPANDING, past-only z-score. Using groupby.transform("mean") here averages the WHOLE
        # session including bars that have not happened yet — high IV vs the full-day mean
        # mechanically implies the rest of the day was calmer, i.e. the market recovered. That
        # leak produced a spurious +14bp/t=15.6 "edge" on the first run of this script.
        mu = g[c].apply(lambda s: s.expanding(min_periods=3).mean().shift(1))
        sd = g[c].apply(lambda s: s.expanding(min_periods=3).std().shift(1))
        base[f"z_{c}"] = (base[c] - mu) / sd.replace(0, np.nan)
    base["ret"] = g.spot.apply(lambda s: s.pct_change())
    base["cum"] = g.spot.apply(lambda s: s / s.iloc[0] - 1)
    base["gamma_sign"] = np.sign(base.net_gamma)

    # ---- forward RETURN (not conditional accuracy) --------------------------------------
    for h in (1, 2, 3):
        base[f"fwd{h}"] = g.spot.apply(lambda s: s.shift(-h) / s - 1)
    return base


FEATS = ["skew", "put_wing", "iv_level", "net_gamma", "gamma_atm", "spread",
         "d_skew", "d_iv_level", "d_put_wing", "d_net_gamma", "d_spread",
         "z_skew", "z_iv_level", "z_net_gamma", "ret", "cum", "tmin"]


def main():
    b = build()
    print(f"bars {len(b):,} | sessions {b.quote_date.nunique():,}")
    dates = np.sort(b.quote_date.unique())
    a, c = dates[int(len(dates)*.40)], dates[int(len(dates)*.70)]
    parts = [("TR", b.quote_date < a), ("VA", (b.quote_date >= a) & (b.quote_date < c)),
             ("TE", b.quote_date >= c)]
    for hcol, lab in (("fwd1", "30m"), ("fwd2", "60m"), ("fwd3", "90m")):
        d = b[b[hcol].notna()]
        print(f"\n=== forward {lab} — mean RETURN of a long position, in basis points ===")
        print(f"  {'feature':14}{'TRlo':>8}{'TRhi':>8}{'VAlo':>8}{'VAhi':>8}{'TElo':>8}{'TEhi':>8}{'':>5}")
        hits = []
        for f in FEATS:
            s = d[d.quote_date < a][f].replace([np.inf, -np.inf], np.nan)
            if s.notna().sum() < 400:
                continue
            lo, hi = np.nanpercentile(s, [20, 80])
            if not np.isfinite([lo, hi]).all() or lo == hi:
                continue
            row, ok = [], True
            for _, m in parts:
                fr = d[m]
                a1 = fr[fr[f] <= lo][hcol].mean() * 1e4
                a2 = fr[fr[f] >= hi][hcol].mean() * 1e4
                if not np.isfinite([a1, a2]).all() or min(len(fr[fr[f] <= lo]), len(fr[fr[f] >= hi])) < 80:
                    ok = False; break
                row += [a1, a2]
            if not ok:
                continue
            sp = [row[1]-row[0], row[3]-row[2], row[5]-row[4]]
            stable = (np.sign(sp[0]) == np.sign(sp[1]) == np.sign(sp[2])) and min(abs(x) for x in sp) > 3
            print(f"  {f:14}" + "".join(f"{v:>+8.1f}" for v in row) + f"{'  <<' if stable else ''}")
            if stable:
                hits.append((f, lo, hi, sp))
        print(f"  stable spread >3bp, same sign on all three: {[h[0] for h in hits] or 'none'}")
        for f, lo, hi, sp in hits:
            side = 1 if sp[2] > 0 else -1
            sel = d[(d[f] >= hi) if side > 0 else (d[f] <= lo)]
            r = sel[hcol].values * side
            tt, pp = st.ttest_1samp(r, 0)
            print(f"    {f}: trade {'LONG on high' if side>0 else 'LONG on low'} "
                  f"n={len(r)} mean {r.mean()*1e4:+.1f}bp t={tt:+.2f} p={pp:.4f}")


if __name__ == "__main__":
    main()
