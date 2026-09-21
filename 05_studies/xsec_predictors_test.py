"""xsec_predictors_test.py — which documented weekly-horizon predictors actually rank
next week's single-stock returns, on seven years of real chains.

Inputs: DATA_ROOT/opt_panel/{features,ohlcv,splits,earnings}.parquet (built by
05_studies/scripts/build_opt_panel.py and 05_studies/xsec_options_panel.py) and
DATA_ROOT/short_interest.parquet (514 names, 2021-06 .. 2026-08, with the borrow fee).

METHOD, and each rule is there because its absence faked a result in this repo before
(02_findings/METHODOLOGY_TRAPS.md):
  * signal known at close t; the position is taken at the OPEN of t+1 and closed at the
    close of t+H. The overnight between t and t+1 is not available and is not counted.
  * ONE observation per name per week (the last session of each ISO week), so 5-day
    forward returns never overlap. 10- and 21-day horizons use every 2nd / 4th week.
  * Spearman rank IC per date, then Fama-MacBeth: mean IC and t = mean/sd*sqrt(n_dates).
  * three consecutive time splits. A sign that flips between them is a period, not a signal.
  * the universe is filtered on things known at t: close >= $10, 20-day median dollar
    volume >= $10m, ATM round-trip spread <= 25% (past-only, no exit-side filtering).
  * ~25 features x 3 horizons = ~75 tests. Expected max |t| under the null is about
    sqrt(2 ln 75) = 2.9. A t below that, on the whole sample, is noise.
  * prices are split-adjusted from the Dolt split table (deduplicated). An unadjusted
    series contains fake -75% days that read as the best short signal in history.

Every feature is signed the way the literature says it should predict, so a POSITIVE IC
means "worked as documented" and a negative IC means the opposite of the paper.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
SPLITS = {"A 2019-21": ("2019-01-01", "2021-12-31"),
          "B 2022-23": ("2022-01-01", "2023-12-31"),
          "C 2024-26": ("2024-01-01", "2026-12-31")}
HORIZONS = (5, 10, 21)

# feature -> (expected sign, source). Sign is applied BEFORE scoring so +IC = "as published".
FEATURES = {
    "cw_spread":     (+1, "Cremers-Weinbaum 2010: call IV > put IV -> up"),
    "smirk":         (-1, "Xing-Zhang-Zhao 2010: steep OTM-put smirk -> down"),
    "rr25":          (+1, "risk reversal (OTM call IV - OTM put IV) -> up"),
    "d_iv_c_5":      (+1, "An et al 2014: call IV rising -> up (5d change)"),
    "d_iv_p_5":      (-1, "An et al 2014: put IV rising -> down (5d change)"),
    "d_iv_c_21":     (+1, "An et al 2014: call IV rising -> up (21d change)"),
    "d_iv_p_21":     (-1, "An et al 2014: put IV rising -> down (21d change)"),
    "atm_iv":        (-1, "high IV names underperform (Ang et al 2006 idio vol)"),
    "ivrv":          (0,  "IV - realised: no directional claim (structure signal)"),
    "term_slope":    (0,  "near IV - far IV: no directional claim (Vasquez: straddle returns)"),
    "straddle_pct":  (-1, "expected move: lottery-like names underperform"),
    "si_float":      (-1, "Boehmer et al: short interest -> down (repo IC -0.107@63d)"),
    "fee_rate":      (-1, "Drechsler & Drechsler 2014: borrow fee -> down"),
    "days_to_cover": (-1, "short interest / volume -> down"),
    "d_si_4w":       (-1, "rising short interest -> down"),
    "ret5":          (-1, "short-term reversal: last week's losers outperform"),
    "ret21":         (-1, "one-month reversal"),
    "ret63":         (+1, "3-month momentum"),
    "mom_12_1":      (+1, "12-1 momentum (Jegadeesh-Titman)"),
    "dist52h":       (+1, "George-Hwang: nearness to 52-week high -> up"),
    "rv21":          (-1, "realised vol: high-vol names underperform"),
    "max5":          (-1, "Bali et al MAX: largest daily gain last month -> down"),
    "pead1":         (+1, "post-earnings drift: sign of the earnings-day move, <=10 sessions old"),
    "dvol_z":        (-1, "abnormal volume (20d z) -> attention -> reversal"),
}


def adjust_splits(px):
    sp = pd.read_parquet(os.path.join(PANEL, "splits.parquet")).drop_duplicates()
    sp["ex_date"] = pd.to_datetime(sp.ex_date)
    sp["ratio"] = sp.for_factor.astype(float) / sp.to_factor.astype(float)
    sp = sp[(sp.ratio > 0) & (sp.ratio != 1)]
    px = px.sort_values(["act_symbol", "date"]).copy()
    px["adj"] = 1.0
    for sym, g in sp.groupby("act_symbol"):
        m = px.act_symbol == sym
        if not m.any():
            continue
        d = px.loc[m, "date"].values
        f = np.ones(len(d))
        for ex, r in zip(g.ex_date.values, g.ratio.values):
            f[d < ex] *= r
        px.loc[m, "adj"] = f
    for c in ("open", "high", "low", "close"):
        px[c] = px[c] * px.adj
    return px


def price_features(px, syms):
    px = px[px.act_symbol.isin(syms)].copy()
    px = adjust_splits(px)
    px = px.sort_values(["act_symbol", "date"])
    g = px.groupby("act_symbol", group_keys=False)
    c = px.close
    px["r1"] = g.close.pct_change(fill_method=None)
    # a single day beyond +/-60% is a corporate action the split table missed, not a move
    px["r1"] = px.r1.mask(px.r1.abs() > 0.60)
    px["ret5"] = g.close.pct_change(5, fill_method=None)
    px["ret21"] = g.close.pct_change(21, fill_method=None)
    px["ret63"] = g.close.pct_change(63, fill_method=None)
    px["mom_12_1"] = g.close.shift(21) / g.close.shift(252) - 1
    px["hi252"] = g.close.transform(lambda s: s.rolling(252, min_periods=120).max())
    px["dist52h"] = c / px.hi252 - 1
    px["rv21"] = g.r1.transform(lambda s: s.rolling(21, min_periods=15).std()) * np.sqrt(252)
    px["max5"] = g.r1.transform(lambda s: s.rolling(21, min_periods=15).max())
    px["dvol"] = px.close * px.volume
    px["adv20"] = g.dvol.transform(lambda s: s.rolling(20, min_periods=10).median())
    px["dvol_z"] = g.dvol.transform(lambda s: (s - s.rolling(20, min_periods=10).mean())
                                    / s.rolling(20, min_periods=10).std())
    # forward returns: open of t+1 to close of t+H
    nxt_open = g.open.shift(-1)
    for h in HORIZONS:
        px[f"fwd{h}"] = g.close.shift(-h) / nxt_open - 1
        px[f"fwd{h}"] = px[f"fwd{h}"].mask(px[f"fwd{h}"].abs() > 1.5)
    px["pos"] = g.cumcount()
    return px


def earnings_features(px):
    e = pd.read_parquet(os.path.join(PANEL, "earnings.parquet"))
    e["date"] = pd.to_datetime(e.date)
    e = e.drop_duplicates(["act_symbol", "date"]).sort_values("date")
    # next earnings date at or after t  (days_to_earn), and the reaction to the last one
    px = px.sort_values("date")
    nxt = pd.merge_asof(px[["date", "act_symbol"]], e.rename(columns={"date": "next_earn"}),
                        left_on="date", right_on="next_earn", by="act_symbol", direction="forward")
    px["days_to_earn"] = (nxt.next_earn.values - px.date.values) / np.timedelta64(1, "D")
    prev = pd.merge_asof(px[["date", "act_symbol"]], e.rename(columns={"date": "prev_earn"}),
                         left_on="date", right_on="prev_earn", by="act_symbol", direction="backward")
    px["days_since_earn"] = (px.date.values - prev.prev_earn.values) / np.timedelta64(1, "D")
    # the earnings-day move: 2-day return spanning the report (after-close reports land next day)
    px = px.sort_values(["act_symbol", "date"])
    g = px.groupby("act_symbol", group_keys=False)
    r2 = g.close.pct_change(2, fill_method=None)
    ev = px[["date", "act_symbol"]].merge(e.assign(is_earn=1), on=["date", "act_symbol"], how="left")
    px["earn_move"] = np.where(ev.is_earn.fillna(0).values == 1, r2.shift(-1).values, np.nan)
    px["earn_move"] = g.earn_move.transform(lambda s: s.ffill(limit=12))
    px["pead1"] = np.where(px.days_since_earn <= 14, px.earn_move, np.nan)
    return px


def short_features(df):
    p = os.path.join(paths.DATA_ROOT, "short_interest.parquet")
    if not os.path.exists(p):
        return df
    si = pd.read_parquet(p)
    si["date"] = pd.to_datetime(si.market_date)
    for c in ("si_float", "days_to_cover", "fee_rate"):
        si[c] = pd.to_numeric(si[c], errors="coerce")
    si = si.rename(columns={"symbol": "act_symbol"}).sort_values("date")
    si["d_si_4w"] = si.groupby("act_symbol").si_float.diff(2)
    # settlement data publishes ~9 days later: lag it so nothing is known before it was public
    si["date"] = si.date + pd.Timedelta(days=10)
    df = df.sort_values("date")
    df = pd.merge_asof(df, si[["date", "act_symbol", "si_float", "days_to_cover", "fee_rate", "d_si_4w"]],
                       on="date", by="act_symbol", direction="backward",
                       tolerance=pd.Timedelta(days=45))
    return df


def build():
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"))
    fe["act_symbol"] = fe.act_symbol.astype(str)
    fe = fe.sort_values(["act_symbol", "date"])
    g = fe.groupby("act_symbol", group_keys=False)
    # IV changes over 5 and 21 sessions of CHAIN data (the chain is not daily in 2019-20,
    # so use calendar-aware asof on the symbol's own series)
    for n in (5, 21):
        fe[f"d_iv_c_{n}"] = g.atm_iv_c.diff(n)
        fe[f"d_iv_p_{n}"] = g.atm_iv_p.diff(n)
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    px = price_features(px, set(fe.act_symbol.unique()))
    px = earnings_features(px)
    df = fe.merge(px.drop(columns=["high", "low", "volume", "hi252", "adj", "dvol", "r1"]),
                  on=["date", "act_symbol"], how="inner")
    df["ivrv"] = df.atm_iv - df.rv21
    df = short_features(df)
    return df


def universe(df):
    m = ((df.close >= 10) & (df.adv20 >= 10e6) & (df.atm_spread <= 0.25) & (df.cw_n >= 3)
         & (df.atm_iv > 0.05) & (df.atm_iv < 2.0))
    return df[m].copy()


def weekly(df, every=1):
    d = df.copy()
    d["wk"] = d.date.dt.to_period("W")
    last = d.groupby("wk").date.transform("max")
    d = d[d.date == last]
    wks = sorted(d.wk.unique())[::every]
    return d[d.wk.isin(wks)]


def ic_table(d, feats, ycol):
    rows = []
    for f, (sgn, src) in feats.items():
        if f not in d:
            continue
        s = sgn if sgn != 0 else 1
        x = d[[f, ycol, "date"]].dropna()
        if x.date.nunique() < 20:
            continue
        ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * s, g[ycol])[0]
                                      if len(g) >= 30 else np.nan).dropna()
        # decile spread per date, in bp
        def spread(g):
            if len(g) < 50:
                return np.nan
            q = pd.qcut(g[f] * s, 10, labels=False, duplicates="drop")
            return (g[ycol][q == q.max()].mean() - g[ycol][q == 0].mean()) * 1e4
        sp = x.groupby("date").apply(spread).dropna()
        out = {"feature": f, "sign": "+" if sgn > 0 else ("-" if sgn < 0 else "0"),
               "n_dates": len(ics), "n_obs": len(x),
               "IC": ics.mean(), "t": ics.mean() / ics.std() * np.sqrt(len(ics)),
               "hit": (ics > 0).mean(), "D10-D1 bp": sp.mean()}
        for k, (a, b) in SPLITS.items():
            sub = ics[(ics.index >= a) & (ics.index <= b)]
            out[k] = (f"{sub.mean():+.3f} (t{sub.mean()/sub.std()*np.sqrt(len(sub)):+.1f})"
                      if len(sub) >= 15 else "—")
        rows.append(out)
    t = pd.DataFrame(rows).sort_values("t", ascending=False)
    return t


def main():
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:,.4f}")
    df = build()
    df.to_parquet(os.path.join(PANEL, "xsec_panel.parquet"), index=False)
    u = universe(df)
    print(f"panel {len(df):,} rows, universe {len(u):,} rows, {u.act_symbol.nunique()} names, "
          f"{u.date.min().date()} .. {u.date.max().date()}")
    for h, every in zip(HORIZONS, (1, 2, 4)):
        w = weekly(u, every)
        print(f"\n===== horizon {h}d, {w.date.nunique()} dates, {len(w):,} obs =====")
        t = ic_table(w, FEATURES, f"fwd{h}")
        print(t.to_string(index=False))
        t.to_csv(os.path.join(PANEL, f"ic_{h}d.csv"), index=False)
    # the same, excluding names with a print inside the window (the engine handles those apart)
    print("\n===== 5d, EXCLUDING names reporting inside the window =====")
    w = weekly(u[(u.days_to_earn.isna()) | (u.days_to_earn > 9)], 1)
    print(ic_table(w, FEATURES, "fwd5").to_string(index=False))
    print(f"\nexpected max |t| under the null for {len(FEATURES)*3} tests: "
          f"{np.sqrt(2*np.log(len(FEATURES)*3)):.2f}")


if __name__ == "__main__":
    main()
