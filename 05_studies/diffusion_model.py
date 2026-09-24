"""diffusion_model.py — information diffusion, every channel this machine can measure, at the
WEEKLY horizon the swing book trades and the MONTHLY horizon the literature reports.

The claim being tested: news reaches some stocks before others, so what happened to the
LINKED names last week tells you what happens to a name next week. The literature says the
links that carry it are the industry (Hou 2007, RFS: big firms lead small firms in the same
industry, at a WEEKLY horizon), the customer (Cohen-Frazzini 2008, JF: +1.55%/month),
technology (Lee-Sun-Wang-Zhang 2019, JFE), shared analysts (Ali-Hirshleifer 2020, JFE, which
argues all of the others are one effect), geography (Parsons-Sabbatucci-Titman 2020, RFS),
early earnings announcers (Thomas-Zhang 2008, JAR: peers OVERreact to an early reporter's
news and give it back when they report), industries leading the whole market (Hong-Torous-
Valkanov 2007, JFE), and cross-asset links (oil to energy names, rates to banks).

Links on this machine: GICS sector and sub-industry for the S&P 1500 (155 sub-industries),
the earnings calendar with consensus and reported EPS (SUE), daily prices 2018-2026 for
1,845 optionable names, and public daily series for oil, copper, gold, the 10-year, the
dollar, high-yield credit and VIX. Not on this machine: customer-supplier links, analyst
coverage, patents, headquarters. Those are stated as not measured, not assumed away.

Channels, one observation per name per week, forward 5- and 21-session return in EXCESS of
SPY from the NEXT open, Spearman IC by week, three time splits, noise bar sqrt(2 ln N):

  A  industry lead-lag       big-peer / all-peer past-week return in the same sub-industry
                             (excluding the name), the gap to the name's own return, and the
                             sector version; Hou's test is the IC on the SMALL half only
  B  earnings transfer       ADV-weighted SUE and announcement-day reaction of same-sub-
                             industry names that reported THIS week, for names that did not
  C  statistical peers       the 20 most-correlated names on the prior 252 sessions (refit
                             monthly, past-only), their past-week return and the gap
  D  cross-asset             last week's move in oil/copper/gold/10y/USD/HY/VIX against
                             next week's sector-ETF excess return, 2010-2026
  E  industries lead market  each sector ETF's past month against SPY's next month
  F  combined model          Fama-MacBeth walk-forward: at each week, the average of the
                             past 104 weeks' cross-sectional coefficients on A+B+C (weeks
                             whose forward return is already realised), applied to this
                             week's features. IC and decile spread, gross and net of 10 bp
                             a side at the turnover actually generated.

Costs, splits and the noise bar are the same as every other study in this folder. The
number that matters for the swing book is F's net weekly decile spread; anything under the
round trip is a null whatever the t-stat says.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_fundamentals_test import prices, sue_events  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
SECTOR_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Energy": "XLE", "Health Care": "XLV",
              "Industrials": "XLI", "Consumer Discretionary": "XLY", "Consumer Staples": "XLP",
              "Utilities": "XLU", "Materials": "XLB", "Real Estate": "XLRE", "Communication Services": "XLC"}
ASSETS = {"oil": "CL=F", "copper": "HG=F", "gold": "GC=F", "tnx": "^TNX", "usd": "DX-Y.NYB", "hyg": "HYG",
          "ief": "IEF", "vix": "^VIX"}
N_PEERS = 20
FM_WINDOW = 104
COST = 0.0010  # 10 bp a side


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def _split_str(ics):
    out = {}
    for k, (a, b) in SPLITS.items():
        s = ics[(ics.index >= a) & (ics.index <= b)]
        out[k] = f"{s.mean():+.3f} (t{_t(s):+.1f})" if len(s) >= 8 else "—"
    return out


def ic_table(d, feats, ycol, min_n=50, label=""):
    rows = []
    for f, sgn in feats:
        x = d[[f, ycol, "date"]].dropna()
        ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * sgn, g[ycol])[0] if len(g) >= min_n else np.nan,
                                      include_groups=False).dropna()
        if len(ics) < 20:
            continue
        rows.append({"feature": f, "sign": "+" if sgn > 0 else "-", "weeks": len(ics), "IC": ics.mean(),
                     "t": _t(ics), "hit": (ics > 0).mean(), **_split_str(ics)})
    t = pd.DataFrame(rows).sort_values("t", ascending=False)
    n = len(feats)
    print(f"\n{label} -> {ycol}: {n} tests, noise bar t ~ {np.sqrt(2*np.log(max(n,2))):.1f}")
    print(t.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    return t


def weekly_panel():
    px = prices()
    g = pd.read_parquet(os.path.join(PANEL, "gics.parquet")).drop_duplicates("ticker")
    px = px.merge(g[["ticker", "sector", "sub_industry"]].rename(columns={"ticker": "act_symbol"}), on="act_symbol", how="inner")
    px = px.sort_values(["act_symbol", "date"])
    grp = px.groupby("act_symbol", group_keys=False)
    px["ret1w"] = grp.close.pct_change(5)
    px["ret1m"] = grp.close.pct_change(21)
    px["ret1d"] = grp.close.pct_change()
    # weekly sampling: the last session of each ISO week
    wk = px.date.dt.to_period("W")
    last = px.groupby(wk).date.transform("max")
    w = px[px.date == last].copy()
    w = w[(w.close >= 10) & (w.adv20 >= 10e6)]
    return px, w


def channel_industry(w):
    """A. Peer returns in the same sub-industry and sector, excluding the name itself."""
    for key, tag in (("sub_industry", "ind"), ("sector", "sec")):
        g = w.groupby(["date", key])
        n = g.ret1w.transform("size")
        s = g.ret1w.transform("sum")
        w[f"{tag}_all_1w"] = ((s - w.ret1w) / (n - 1)).where(n >= 3)
        wt = w.adv20
        ws = g.apply(lambda d: (d.ret1w * d.adv20).sum(), include_groups=False)
        wsum = g.adv20.transform("sum")
        w[f"{tag}_vw_1w"] = ((w.set_index(["date", key]).index.map(ws) - w.ret1w * wt) / (wsum - wt)).where(n >= 3)
        w[f"{tag}_gap"] = w[f"{tag}_all_1w"] - w.ret1w
    # Hou: BIG peers (top tercile by ADV within sub-industry) excluding self
    g = w.groupby(["date", "sub_industry"])
    cut = g.adv20.transform(lambda v: v.quantile(0.67))
    w["big"] = w.adv20 >= cut
    w["small"] = w.adv20 <= g.adv20.transform(lambda v: v.quantile(0.5))
    bigret = (w.ret1w * w.big)
    nb = g.big.transform("sum")
    sb = bigret.groupby([w.date, w.sub_industry]).transform("sum")
    own = np.where(w.big, w.ret1w, 0.0)
    w["ind_big_1w"] = ((sb - own) / (nb - w.big.astype(int))).where((nb - w.big.astype(int)) >= 1)
    w["ind_big_gap"] = w.ind_big_1w - w.ret1w
    return w


def channel_earnings(px, w):
    """B. This week's same-sub-industry announcers: their SUE and announcement-day reaction,
    assigned to the names in the industry that did NOT report this week or next."""
    e = sue_events(px)
    px = px.sort_values(["act_symbol", "date"])
    prev = px.groupby("act_symbol").close.shift(1)
    day = (px.close / prev - 1).rename("ear")
    r1 = pd.concat([px[["act_symbol", "date"]], day], axis=1)
    e = e.merge(r1.rename(columns={"date": "sig"}), on=["act_symbol", "sig"], how="left")
    g = pd.read_parquet(os.path.join(PANEL, "gics.parquet")).drop_duplicates("ticker")
    e = e.merge(g[["ticker", "sub_industry"]].rename(columns={"ticker": "act_symbol"}), on="act_symbol", how="inner")
    wk_dates = np.sort(w.date.unique())
    idx = np.searchsorted(wk_dates, e.sig.values, side="left")
    e = e[idx < len(wk_dates)].copy()
    e["date"] = wk_dates[np.searchsorted(wk_dates, e.sig.values, side="left")]
    e["w"] = e.adv20
    agg = e.groupby(["date", "sub_industry"]).apply(
        lambda d: pd.Series({"peer_sue": np.average(d.sue, weights=d.w), "peer_ear": np.average(d.ear.fillna(0), weights=d.w),
                             "n_ann": len(d)}), include_groups=False).reset_index()
    w = w.merge(agg, on=["date", "sub_industry"], how="left")
    own = e[["act_symbol", "date"]].drop_duplicates().assign(own_ann=1)
    # names that announced this week or announce next week are excluded from B
    nxt = own.copy()
    pos = np.searchsorted(wk_dates, nxt.date.values) - 1
    nxt = nxt[pos >= 0].copy()
    nxt["date"] = wk_dates[pos[pos >= 0]]
    own = pd.concat([own, nxt]).drop_duplicates()
    w = w.merge(own, on=["act_symbol", "date"], how="left")
    mask = w.own_ann.isna() & w.n_ann.notna()
    for c in ("peer_sue", "peer_ear"):
        w[c] = w[c].where(mask)
    w["peer_sue_pos"] = np.sign(w.peer_sue)
    return w


def channel_statpeers(px, w):
    """C. Top-N most-correlated peers on the prior 252 sessions, refit monthly, past-only."""
    close = px.drop_duplicates(["date", "act_symbol"]).pivot(index="date", columns="act_symbol", values="close").sort_index()
    ret = close.pct_change(fill_method=None)
    ret1w = close / close.shift(5) - 1
    months = close.index.to_series().groupby(close.index.to_period("M")).max().tolist()
    peers = {}
    for d in months:
        i = close.index.get_loc(d)
        if i < 260:
            continue
        win = ret.iloc[i - 252:i].dropna(axis=1, thresh=200)
        if win.shape[1] < 100:
            continue
        c = win.corr().values
        np.fill_diagonal(c, np.nan)
        order = np.argsort(-np.nan_to_num(c, nan=-9), axis=1)[:, :N_PEERS]
        peers[d] = (list(win.columns), order)
    mkeys = sorted(peers)
    out = []
    for d in np.sort(w.date.unique()):
        d = pd.Timestamp(d)
        j = np.searchsorted(mkeys, d, side="right") - 1      # the last refit strictly before this week
        if j < 0 or mkeys[j] >= d:
            continue
        cols, order = peers[mkeys[j]]
        r = ret1w.loc[d, cols].values
        pm = np.nanmean(r[order], axis=1)
        out.append(pd.DataFrame({"date": d, "act_symbol": cols, "peer_1w": pm}))
    p = pd.concat(out, ignore_index=True)
    w = w.merge(p, on=["date", "act_symbol"], how="left")
    w["peer_gap"] = w.peer_1w - w.ret1w
    return w


def channel_cross_asset():
    """D and E on public weekly series, 2010-2026."""
    import yfinance as yf
    syms = list(ASSETS.values()) + list(SECTOR_ETF.values()) + ["SPY"]
    px = yf.download(syms, start="2009-06-01", auto_adjust=True, progress=False)["Close"]
    wk = px.resample("W-FRI").last()
    r = wk.pct_change(fill_method=None)
    r["tnx"] = wk["^TNX"].diff()                      # yield change in points, not a return
    r["hy_spread"] = r["HYG"] - r["IEF"]
    r["vix"] = wk["^VIX"].pct_change()
    feats = {"oil": r["CL=F"], "copper": r["HG=F"], "gold": r["GC=F"], "tnx": r["tnx"], "usd": r["DX-Y.NYB"],
             "hy_spread": r["hy_spread"], "vix": r["vix"]}
    rows = []
    for a, x in feats.items():
        for sec, etf in SECTOR_ETF.items():
            y = (r[etf] - r["SPY"]).shift(-1)
            d = pd.concat([x, y], axis=1, keys=["x", "y"]).dropna()
            if len(d) < 100:
                continue
            row = {"asset": a, "sector": etf, "n": len(d), "corr": d.x.corr(d.y), "t": d.x.corr(d.y) * np.sqrt(len(d))}
            for k, (lo, hi) in SPLITS.items():
                s = d[(d.index >= lo) & (d.index <= hi)]
                row[k] = f"{s.x.corr(s.y):+.3f}" if len(s) > 30 else "—"
            rows.append(row)
    t = pd.DataFrame(rows).sort_values("t", key=abs, ascending=False)
    n = len(t)
    print(f"\nD. CROSS-ASSET -> next-week sector excess (weekly, {r.index.min().date()}..{r.index.max().date()}): "
          f"{n} tests, noise bar t ~ {np.sqrt(2*np.log(n)):.1f}")
    print(t.head(12).to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    print(f"  |t| > noise bar: {(t.t.abs() > np.sqrt(2*np.log(n))).sum()} of {n}")
    # E. industries lead the market: sector past month -> SPY next month (and week -> week)
    m = px.resample("ME").last().pct_change(fill_method=None)
    rows = []
    for sec, etf in SECTOR_ETF.items():
        for lab, rr, h in (("month", m, 1), ("week", r, 1)):
            x = (rr[etf] - rr["SPY"]) if lab == "week" else rr[etf]
            y = rr["SPY"].shift(-h)
            d = pd.concat([x, y], axis=1, keys=["x", "y"]).dropna()
            rows.append({"sector": etf, "horizon": lab, "n": len(d), "corr": d.x.corr(d.y), "t": d.x.corr(d.y) * np.sqrt(len(d))})
    t = pd.DataFrame(rows).sort_values("t", key=abs, ascending=False)
    print(f"\nE. INDUSTRIES LEAD THE MARKET (Hong-Torous-Valkanov): {len(t)} tests, noise bar t ~ {np.sqrt(2*np.log(len(t))):.1f}")
    print(t.head(8).to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    print(f"  |t| > noise bar: {(t.t.abs() > np.sqrt(2*np.log(len(t)))).sum()} of {len(t)}")


def combined(w, feats, ycol="ex5"):
    """F. Fama-MacBeth walk-forward. Cross-sectional ranks each week; coefficients from weeks
    whose forward return is realised (>= 2 weeks back for ex5); average of the past FM_WINDOW."""
    d = w[["date", "act_symbol", ycol] + feats].copy()
    for f in feats:
        d[f] = d.groupby("date")[f].rank(pct=True) - 0.5
        d[f] = d[f].fillna(0.0)
    d = d.dropna(subset=[ycol])
    dates = np.sort(d.date.unique())
    betas = {}
    for dt in dates:
        g = d[d.date == dt]
        if len(g) < 100:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[f].values for f in feats])
        b, *_ = np.linalg.lstsq(X, g[ycol].values, rcond=None)
        betas[dt] = b[1:]
    bk = sorted(betas)
    lag = 2 if ycol == "ex5" else 5
    preds = []
    for i, dt in enumerate(dates):
        past = [betas[k] for k in bk if k <= dates[max(0, i - lag)] and k < dt][-FM_WINDOW:]
        if len(past) < 52:
            continue
        bbar = np.mean(past, axis=0)
        g = d[d.date == dt].copy()
        g["pred"] = g[feats].values @ bbar
        preds.append(g)
    p = pd.concat(preds)
    ics = p.groupby("date").apply(lambda g: stats.spearmanr(g.pred, g[ycol])[0] if len(g) >= 50 else np.nan,
                                  include_groups=False).dropna()
    print(f"\nF. COMBINED walk-forward ({', '.join(feats)}) -> {ycol}: {len(ics)} weeks, "
          f"IC {ics.mean():+.4f} (t {_t(ics):+.2f}), hit {(ics>0).mean():.2f}; splits {_split_str(ics)}")
    p["dec"] = p.groupby("date").pred.transform(lambda v: pd.qcut(v.rank(method="first"), 10, labels=False, duplicates="drop"))
    top = p[p.dec == 9].groupby("date")
    bot = p[p.dec == 0].groupby("date")
    spread = (top[ycol].mean() - bot[ycol].mean()).dropna()
    # turnover of the long decile week to week
    sets = {dt: set(g.act_symbol) for dt, g in top}
    ks = sorted(sets)
    to = np.mean([1 - len(sets[a] & sets[b]) / max(len(sets[b]), 1) for a, b in zip(ks[:-1], ks[1:])])
    hold_w = 1 if ycol == "ex5" else 4
    net = spread.mean() - 2 * COST * 2 * to / hold_w     # both legs, each traded at turnover `to` per hold
    print(f"   D10-D1 per {hold_w}-week hold: gross {spread.mean()*100:+.3f}% (t {_t(spread):+.2f}), "
          f"long-decile turnover {to*100:.0f}%/week, net of 10 bp/side {net*100:+.3f}% "
          f"=> {net*52/hold_w*100:+.1f}%/yr; months>0 {(spread>0).mean()*100:.0f}%")
    return ics


def main():
    pd.set_option("display.width", 220)
    px, w = weekly_panel()
    print(f"weekly panel: {len(w):,} name-weeks, {w.act_symbol.nunique()} names, {w.date.nunique()} weeks, "
          f"{w.sub_industry.nunique()} sub-industries, {w.date.min().date()}..{w.date.max().date()}")
    w = channel_industry(w)
    w = channel_earnings(px, w)
    w = channel_statpeers(px, w)
    A = [("ind_all_1w", +1), ("ind_vw_1w", +1), ("ind_big_1w", +1), ("ind_gap", +1), ("ind_big_gap", +1),
         ("sec_all_1w", +1), ("sec_vw_1w", +1), ("sec_gap", +1), ("ret1w", -1)]
    for y in ("ex5", "ex21"):
        ic_table(w, A, y, label="A. INDUSTRY LEAD-LAG, all names")
        ic_table(w[w.small], A, y, label="A. INDUSTRY LEAD-LAG, SMALL half only (Hou)")
    B = [("peer_sue", +1), ("peer_ear", +1), ("peer_sue_pos", +1)]
    nb = w.peer_sue.notna().sum()
    print(f"\nB. names with a same-industry announcer this week and none of their own: {nb:,} name-weeks")
    for y in ("ex5", "ex21"):
        ic_table(w, B, y, min_n=30, label="B. EARNINGS TRANSFER (Thomas-Zhang: negative = overreaction)")
    C = [("peer_1w", +1), ("peer_gap", +1)]
    for y in ("ex5", "ex21"):
        ic_table(w, C, y, label="C. STATISTICAL PEERS")
    try:
        channel_cross_asset()
    except Exception as ex:                                  # noqa: BLE001
        print(f"\nD/E skipped: {ex}")
    feats = ["ind_all_1w", "ind_big_1w", "ind_gap", "sec_all_1w", "peer_1w", "peer_gap", "ret1w"]
    w["peer_sue_f"] = w.peer_sue.fillna(0.0)
    combined(w, feats, "ex5")
    combined(w, feats + ["peer_sue_f"], "ex5")
    combined(w, feats, "ex21")
    w.to_parquet(os.path.join(PANEL, "diffusion_weekly.parquet"), index=False)


if __name__ == "__main__":
    main()
