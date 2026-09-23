"""xsec_diffusion_test.py — information diffusion: does what happened to a stock's PEERS
last month predict what happens to the stock next month?

The literature: Hong & Stein (1999) slow diffusion; Cohen & Frazzini (2008) customer
momentum (+1.55%/month, JF); Menzly & Ozbas (2010) industry links; Moskowitz & Grinblatt
(1999) industry momentum; Ali & Hirshleifer (2020) "connected stocks" via shared analyst
coverage; Parsons, Sabbatucci & Titman (2020) geographic lead-lag. All say the same thing:
news reaches the linked names first and the target name later, so peer returns lead.

Supplier-customer and analyst links are not on this machine. Two proxies are:
  sector_mom    the name's sector ETF's trailing 21-session return (industry momentum)
  peer_mom      the mean trailing-21 return of the name's 20 most-correlated peers, where
                the correlation is computed on the PRIOR 252 sessions of daily returns and
                re-estimated monthly (past-only; statistical peers = the linkage a fund
                would find by co-movement, which is what "connected stocks" measures)
  peer_gap      peer_mom minus the name's own trailing-21 return: the diffusion lag itself
Scored like everything else: one observation per name per month, Spearman IC on the next
21-session return in excess of SPY, three splits, the noise bar stated. If diffusion is
live, peer_gap is positive in every split; the own-return term (reversal) is netted out.
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, adjust_splits  # noqa: E402

PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC"]
N_PEERS = 20


def main():
    pd.set_option("display.width", 200)
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"), columns=["act_symbol"])
    names = set(fe.act_symbol.astype(str)) | set(SECTORS) | {"SPY"}
    px = adjust_splits(px[px.act_symbol.isin(names)])
    close = px.pivot(index="date", columns="act_symbol", values="close").sort_index()
    vol = px.pivot(index="date", columns="act_symbol", values="volume").sort_index()
    ret = close.pct_change(fill_method=None)
    stocks = [c for c in close.columns if c not in SECTORS and c != "SPY"]
    m21 = close / close.shift(21) - 1
    fwd21 = close.shift(-21) / close.shift(-1) - 1                     # next open proxy: close t+1 .. t+21
    dv20 = (close * vol).rolling(20, min_periods=10).median()
    month_ends = close.index.to_series().groupby(close.index.to_period("M")).max().tolist()
    rows = []
    for d in month_ends:
        i = close.index.get_loc(d)
        if i < 260:
            continue
        win = ret.iloc[i - 252:i][stocks].dropna(axis=1, thresh=200)
        if win.shape[1] < 100:
            continue
        c = win.corr().values
        np.fill_diagonal(c, np.nan)
        cols = list(win.columns)
        mom = m21.loc[d, cols]
        # top-N peers by correlation, past-only
        order = np.argsort(-np.nan_to_num(c, nan=-9), axis=1)[:, :N_PEERS]
        peer_mom = np.nanmean(mom.values[order], axis=1)
        # sector momentum via each name's most-correlated sector ETF (the linkage a fund uses)
        sec_ret = ret.iloc[i - 252:i][SECTORS]
        sec_corr = pd.DataFrame({s: win.corrwith(sec_ret[s]) for s in SECTORS})
        best_sec = sec_corr.idxmax(axis=1)
        sector_mom = m21.loc[d, SECTORS].reindex(best_sec.values).values
        df = pd.DataFrame({"date": d, "act_symbol": cols, "own_mom": mom.values, "peer_mom": peer_mom,
                           "sector_mom": sector_mom, "close": close.loc[d, cols].values,
                           "adv20": dv20.loc[d, cols].values, "fwd21": fwd21.loc[d, cols].values,
                           "spy21": fwd21.loc[d, "SPY"]})
        df["peer_gap"] = df.peer_mom - df.own_mom
        df["sector_gap"] = df.sector_mom - df.own_mom
        df = df[(df.close >= 10) & (df.adv20 >= 10e6)]
        rows.append(df)
    u = pd.concat(rows, ignore_index=True)
    u["ex21"] = u.fwd21 - u.spy21
    print(f"{u.date.nunique()} month-ends, {len(u):,} obs, {u.act_symbol.nunique()} names, "
          f"{u.date.min().date()} .. {u.date.max().date()}")
    out = []
    for f, sgn, src in (("peer_mom", +1, "peers' last month -> up (diffusion)"),
                        ("peer_gap", +1, "peers minus own: the lag itself -> up"),
                        ("sector_mom", +1, "sector ETF momentum (Moskowitz-Grinblatt)"),
                        ("sector_gap", +1, "sector minus own -> up"),
                        ("own_mom", -1, "own 1-month: reversal expected")):
        x = u[[f, "ex21", "date"]].dropna()
        ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * sgn, g.ex21)[0] if len(g) >= 50 else np.nan,
                                      include_groups=False).dropna()
        row = {"feature": f, "sign": "+" if sgn > 0 else "-", "months": len(ics), "IC": ics.mean(),
               "t": ics.mean() / ics.std() * np.sqrt(len(ics)), "hit": (ics > 0).mean()}
        for k, (a, b) in SPLITS.items():
            s = ics[(ics.index >= a) & (ics.index <= b)]
            row[k] = f"{s.mean():+.3f} (t{s.mean()/s.std()*np.sqrt(len(s)):+.1f})" if len(s) >= 8 else "—"
        out.append(row)
    t = pd.DataFrame(out).sort_values("t", ascending=False)
    print(t.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    # decile spread of the lag term, in bp/month
    x = u[["peer_gap", "ex21", "date"]].dropna()
    x["dec"] = x.groupby("date").peer_gap.transform(lambda v: pd.qcut(v.rank(method="first"), 10, labels=False))
    sp = x.groupby(["date", "dec"]).ex21.mean().unstack()
    d10 = (sp[9] - sp[0]).dropna()
    print(f"\npeer_gap D10-D1 next-month excess: {d10.mean()*100:+.2f}%/month, t={d10.mean()/d10.std()*np.sqrt(len(d10)):+.2f}, "
          f"months>0 {(d10>0).mean()*100:.0f}%  (5 tests; noise bar ~1.8)")
    u.to_parquet(os.path.join(PANEL, "diffusion_panel.parquet"), index=False)


if __name__ == "__main__":
    main()
