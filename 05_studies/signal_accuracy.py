"""signal_accuracy.py — every factor this machine can compute, scored the way a trader
reads a signal: how often the top decile is right, how big the wins are against the losses,
at 1, 2, 4 and 13 weeks, in three time splits, with the noise bar stated.

The brief from Sholo (2026-09-24): stop optimising for the dollar target and get the SIGNAL
right — momentum and market factors, "sometimes after earnings there's a sell-off the next
day", "test every possibility". Either a high hit rate, or a lower one whose wins are large.

So this file builds one weekly panel of ~70 features across six families and reports, for
each, the rank correlation with the forward excess return AND the top- and bottom-decile hit
rate, mean win, mean loss and payoff ratio. Then it fits two walk-forward models on all of
them at once — Fama-MacBeth (linear) and LightGBM (nonlinear, with market state) — trained
only on weeks whose forward return was known at the time, and scores their top decile the
same way, net of 15 bp a side at the turnover they generate.

Families:
  price       1w/1m reversal, 3-1 / 6-1 / 12-1 momentum, 12m, distance to 52w high and low,
              residual momentum (Blitz-Huij-Martens), beta, idiosyncratic vol, realised vol,
              MAX (largest daily gain last month, Bali-Cakici-Whitelaw), skew, Amihud
              illiquidity, dollar-volume trend, crash-of-the-week (<-10% in 5 sessions)
  earnings    the LAST report: surprise (SUE), reaction day (EAR), the day AFTER the
              reaction, the 10-session run-up INTO the print, volume on the print vs normal,
              the move against what the straddle implied, sessions since, drift since, and
              the mismatch flags Sholo named: beat-but-sold-off, miss-but-rallied, gap
              >5% up / down, run-up-then-print
  options     ATM IV, IV minus realised, IV rank (252 sessions), smirk, 25-delta risk
              reversal, Cremers-Weinbaum call-put spread, term slope, straddle-implied move,
              ATM spread (a liquidity proxy)
  fundamentals gross margin, net margin, their yoy change, sales growth, FCF yield, buyback
              yield, net issuance, dividend yield, size (60-day lagged statements)
  market      SPY 12-month and 1-month return, VIX level and 252-session rank — as
              interaction terms for the models and as regime splits for the tables
  event study a daily table of what happens on days 2, 3-5, 6-21 and 22-63 after an
              earnings reaction of each size, and in each surprise x reaction quadrant

Method, unchanged from every other study here: prices split-adjusted, next-open entry,
forward return in excess of SPY, close >= $10 and $10m/day, one observation per name per
week, sampled every h/5 weeks so the 21- and 63-session horizons do not overlap, Spearman
IC by date, three splits, noise bar sqrt(2 ln N) for the N features tested at each horizon.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_fundamentals_test import fundamentals, prices, sue_events  # noqa: E402
from xsec_predictors_test import SPLITS  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
COST = 0.0015
HORIZONS = (5, 10, 21, 63)

# feature -> (published / hypothesised sign, family)
FEATURES = {
    "rev1w": (-1, "price"), "rev1m": (-1, "price"), "mom3_1": (+1, "price"), "mom6_1": (+1, "price"),
    "mom12_1": (+1, "price"), "mom12": (+1, "price"), "hi52": (+1, "price"), "lo52": (-1, "price"),
    "resid_mom": (+1, "price"), "beta63": (-1, "price"), "ivol63": (-1, "price"), "vol21": (-1, "price"),
    "max1m": (-1, "price"), "min1m": (+1, "price"), "skew63": (-1, "price"), "amihud": (+1, "price"),
    "vtrend": (+1, "price"), "crash1w": (+1, "price"), "dd52": (+1, "price"),
    "rsi14": (-1, "pattern"), "ma50_200": (+1, "pattern"), "px_ma50": (+1, "pattern"), "px_ma200": (+1, "pattern"),
    "streak": (-1, "pattern"), "breakout52": (+1, "pattern"), "breakdown52": (-1, "pattern"), "vol_spike": (+1, "pattern"),
    "gap_today": (-1, "pattern"), "dead_cat": (+1, "pattern"), "bb_pos": (-1, "pattern"), "range_pos": (+1, "pattern"),
    "updays20": (+1, "pattern"), "gapfreq": (-1, "pattern"),
    "sue": (+1, "earnings"), "ear": (+1, "earnings"), "day2": (+1, "earnings"), "runup10": (-1, "earnings"),
    "volx": (+1, "earnings"), "implied": (-1, "earnings"), "surprise_ratio": (+1, "earnings"),
    "days_since": (-1, "earnings"), "drift_since": (+1, "earnings"), "beat_sold": (+1, "earnings"),
    "miss_rallied": (-1, "earnings"), "gap_up5": (+1, "earnings"), "gap_dn5": (-1, "earnings"),
    "runup_then_beat": (+1, "earnings"), "sue_x_ear": (+1, "earnings"), "ear_minus_implied": (+1, "earnings"),
    "atm_iv": (-1, "options"), "iv_hv": (-1, "options"), "iv_rank": (-1, "options"), "smirk": (-1, "options"),
    "rr25": (+1, "options"), "cw_spread": (+1, "options"), "term_slope": (+1, "options"),
    "straddle_pct": (-1, "options"), "atm_spread": (-1, "options"),
    "gm": (+1, "fund"), "nm": (+1, "fund"), "d_gm_yoy": (+1, "fund"), "d_nm_yoy": (+1, "fund"),
    "sales_g": (+1, "fund"), "fcf_yield": (+1, "fund"), "buyback_yield": (+1, "fund"), "d_shares_yoy": (-1, "fund"),
    "div_yield": (+1, "fund"), "log_mcap": (-1, "fund"),
}
MARKET = ["spy_12m", "spy_1m", "vix", "vix_rank"]


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def _splits(ics):
    return {k: f"{s.mean():+.3f}(t{_t(s):+.1f})" if len(s := ics[(ics.index >= a) & (ics.index <= b)]) >= 6 else "—"
            for k, (a, b) in SPLITS.items()}


def spy_close():
    s = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), filters=[("act_symbol", "==", "SPY")])
    return s.set_index("date").close.sort_index()


def build():
    px = prices()
    px = px.sort_values(["act_symbol", "date"])
    close = px.drop_duplicates(["date", "act_symbol"]).pivot(index="date", columns="act_symbol", values="close").sort_index()
    volume = px.drop_duplicates(["date", "act_symbol"]).pivot(index="date", columns="act_symbol", values="volume").sort_index()
    spy = spy_close().reindex(close.index).ffill()
    r = close.pct_change(fill_method=None)
    rm = spy.pct_change()
    F = {}
    F["rev1w"] = close / close.shift(5) - 1
    F["rev1m"] = close / close.shift(21) - 1
    F["mom3_1"] = close.shift(21) / close.shift(63) - 1
    F["mom6_1"] = close.shift(21) / close.shift(126) - 1
    F["mom12_1"] = close.shift(21) / close.shift(252) - 1
    F["mom12"] = close / close.shift(252) - 1
    hi = close.rolling(252, min_periods=120).max()
    lo = close.rolling(252, min_periods=120).min()
    F["hi52"] = close / hi
    F["lo52"] = close / lo - 1
    F["dd52"] = close / hi - 1
    F["vol21"] = r.rolling(21).std() * np.sqrt(252)
    F["max1m"] = r.rolling(21).max()
    F["min1m"] = r.rolling(21).min()
    F["skew63"] = r.rolling(63).skew()
    dv = close * volume
    F["amihud"] = (r.abs() / dv.replace(0, np.nan)).rolling(21).mean() * 1e6
    F["vtrend"] = dv.rolling(21).mean() / dv.rolling(126).mean()
    F["crash1w"] = (F["rev1w"] < -0.10).astype(float)
    # classic chart patterns, each a number a scanner would print
    up = r.clip(lower=0).rolling(14).mean()
    dn = (-r.clip(upper=0)).rolling(14).mean()
    F["rsi14"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    F["ma50_200"] = ma50 / ma200 - 1
    F["px_ma50"] = close / ma50 - 1
    F["px_ma200"] = close / ma200 - 1
    sgn = np.sign(r)
    streak = sgn.copy()
    for k in range(1, 8):
        same = (sgn.shift(k) == sgn) & (streak.abs() == k)
        streak = streak.where(~same, streak + sgn)
    F["streak"] = streak
    F["breakout52"] = (close >= hi.shift(1)).astype(float)
    F["breakdown52"] = (close <= lo.shift(1)).astype(float)
    F["vol_spike"] = volume / volume.rolling(20).mean().shift(1)
    opn = px.drop_duplicates(["date", "act_symbol"]).pivot(index="date", columns="act_symbol", values="open").sort_index()
    F["gap_today"] = opn / close.shift(1) - 1
    F["dead_cat"] = ((F["rev1w"] < -0.10) & (F["mom12_1"] > 0)).astype(float)
    sd20 = close.rolling(20).std()
    F["bb_pos"] = (close - close.rolling(20).mean()) / (2 * sd20.replace(0, np.nan))
    hi20, lo20 = close.rolling(20).max(), close.rolling(20).min()
    F["range_pos"] = (close - lo20) / (hi20 - lo20).replace(0, np.nan)
    F["updays20"] = (r > 0).rolling(20).mean()
    F["gapfreq"] = (F["gap_today"].abs() > 0.03).rolling(63).mean()
    # beta, residuals, residual momentum, idiosyncratic vol (all past-only, rolling)
    rmm = pd.DataFrame(np.tile(rm.values[:, None], (1, r.shape[1])), index=r.index, columns=r.columns)
    cov = (r * rmm).rolling(63).mean() - r.rolling(63).mean() * rmm.rolling(63).mean()
    var = rmm.rolling(63).var(ddof=0)
    beta = cov / var
    F["beta63"] = beta
    resid = r - beta.shift(1) * rmm
    F["ivol63"] = resid.rolling(63).std() * np.sqrt(252)
    rs = resid.rolling(231).sum().shift(21)                      # months 2..12 of residuals
    F["resid_mom"] = rs / (resid.rolling(231).std().shift(21) * np.sqrt(231))
    # options-implied
    fe = pd.read_parquet(os.path.join(PANEL, "features.parquet"))
    fe["act_symbol"] = fe.act_symbol.astype(str)
    iv = fe.pivot(index="date", columns="act_symbol", values="atm_iv").reindex(close.index)
    ivmin = iv.rolling(252, min_periods=120).min()
    ivmax = iv.rolling(252, min_periods=120).max()
    F["iv_rank"] = ((iv - ivmin) / (ivmax - ivmin)).reindex(columns=close.columns)
    # weekly sampling
    wk = close.index.to_series().groupby(close.index.to_period("W")).max().values
    cols = {}
    for k, m in F.items():
        cols[k] = m.reindex(wk).stack(future_stack=True)
    w = pd.DataFrame(cols)
    w.index.names = ["date", "act_symbol"]
    w = w.reset_index()
    base = px[["date", "act_symbol", "close", "adv20"] + [f"ex{h}" for h in HORIZONS] + [f"fwd{h}" for h in HORIZONS]]
    w = w.merge(base, on=["date", "act_symbol"], how="inner")
    w = w[(w.close >= 10) & (w.adv20 >= 10e6)].copy()
    w["iv_hv"] = np.nan
    fcols = ["atm_iv", "atm_spread", "straddle_pct", "smirk", "rr25", "cw_spread", "term_slope"]
    w = w.merge(fe[["date", "act_symbol"] + fcols], on=["date", "act_symbol"], how="left")
    w["iv_hv"] = w.atm_iv - w.vol21
    # fundamentals (monthly rows, statements lagged 60 days) carried forward to the week
    m = fundamentals(px)
    fcols2 = ["gm", "nm", "d_gm_yoy", "d_nm_yoy", "sales_g", "fcf_yield", "buyback_yield", "d_shares_yoy", "div_yield", "mcap"]
    m = m[["date", "act_symbol"] + fcols2].sort_values("date")
    w = w.sort_values("date")
    w = pd.merge_asof(w, m, on="date", by="act_symbol", direction="backward", tolerance=pd.Timedelta(days=45))
    w["log_mcap"] = np.log(w.mcap.replace(0, np.nan))
    # earnings: the last report and everything about it
    e = sue_events(px)[["act_symbol", "sig", "sue", "sue_rel"]].dropna(subset=["sue"]).copy()
    e = e[e.sig.isin(close.index)]
    pos = close.index.get_indexer(e.sig)
    ci = close.columns.get_indexer(e.act_symbol)
    ok = (pos > 12) & (ci >= 0) & (pos < len(close.index) - 2)
    e, pos, ci = e[ok].copy(), pos[ok], ci[ok]
    cv, vv = close.values, volume.values
    e["ear"] = cv[pos, ci] / cv[pos - 1, ci] - 1
    e["day2"] = cv[pos + 1, ci] / cv[pos, ci] - 1
    e["runup10"] = cv[pos - 1, ci] / cv[pos - 11, ci] - 1
    vavg = np.nanmean(np.stack([vv[pos - k, ci] for k in range(2, 22)]), axis=0)
    e["volx"] = vv[pos, ci] / vavg
    e["spy_ear"] = spy.values[pos] / spy.values[pos - 1] - 1
    e["ear_x"] = e.ear - e.spy_ear
    imp = fe[["date", "act_symbol", "straddle_pct"]].rename(columns={"date": "sig", "straddle_pct": "implied"}).sort_values("sig")
    e = pd.merge_asof(e.sort_values("sig").assign(sig0=lambda d: d.sig - pd.Timedelta(days=1)),
                      imp, left_on="sig0", right_on="sig", by="act_symbol", direction="backward",
                      tolerance=pd.Timedelta(days=6), suffixes=("", "_imp")).drop(columns=["sig0", "sig_imp"], errors="ignore")
    e["surprise_ratio"] = e.ear.abs() / e.implied.replace(0, np.nan)
    e["ear_minus_implied"] = e.ear.abs() - e.implied
    e["close_sig"] = cv[pos, ci]
    e["beat_sold"] = ((e.sue > 0) & (e.ear_x < -0.02)).astype(float)
    e["miss_rallied"] = ((e.sue < 0) & (e.ear_x > 0.02)).astype(float)
    e["gap_up5"] = (e.ear_x > 0.05).astype(float)
    e["gap_dn5"] = (e.ear_x < -0.05).astype(float)
    e["runup_then_beat"] = ((e.runup10 > 0.05) & (e.sue > 0)).astype(float)
    e["sue_x_ear"] = np.sign(e.sue) * np.sign(e.ear_x) * np.minimum(e.ear_x.abs(), 0.2)
    ecols = ["sue", "ear", "day2", "runup10", "volx", "implied", "surprise_ratio", "ear_minus_implied", "close_sig",
             "beat_sold", "miss_rallied", "gap_up5", "gap_dn5", "runup_then_beat", "sue_x_ear", "sig"]
    w = pd.merge_asof(w.sort_values("date"), e[["act_symbol"] + ecols].rename(columns={"sig": "date"}).assign(sig=lambda d: d.date).sort_values("date"),
                      on="date", by="act_symbol", direction="backward", tolerance=pd.Timedelta(days=130))
    w["days_since"] = (w.date - w.sig).dt.days * 252 / 365
    w["drift_since"] = w.close / w.close_sig - 1
    # market state
    w["spy_12m"] = w.date.map(spy / spy.shift(252) - 1)
    w["spy_1m"] = w.date.map(spy / spy.shift(21) - 1)
    try:
        import yfinance as yf
        vix = yf.download("^VIX", start="2017-01-01", auto_adjust=True, progress=False)["Close"]
        vix = vix.iloc[:, 0] if hasattr(vix, "columns") else vix
        vix.index = pd.to_datetime(vix.index).tz_localize(None)
        w["vix"] = w.date.map(vix.reindex(close.index).ffill())
        w["vix_rank"] = w.date.map(vix.rolling(252).rank(pct=True).reindex(close.index).ffill())
    except Exception:                                         # noqa: BLE001
        w["vix"] = np.nan
        w["vix_rank"] = np.nan
    return w, e, close, spy


def accuracy_table(w, h, feats, label, min_n=50):
    y = f"ex{h}"
    step = max(1, h // 5)
    dates = np.sort(w.date.unique())[::step]
    d = w[w.date.isin(dates)]
    rows = []
    for f, (sgn, fam) in feats.items():
        if f not in d:
            continue
        x = d[["date", f, y]].dropna()
        if x[f].nunique() < 3:
            continue
        ics = x.groupby("date").apply(lambda g: stats.spearmanr(g[f] * sgn, g[y])[0] if len(g) >= min_n else np.nan,
                                      include_groups=False).dropna()
        if len(ics) < 15:
            continue
        # deciles of the sign-adjusted feature; binary flags -> flag on vs off
        if x[f].nunique() <= 2:
            top = x[x[f] * sgn == (x[f] * sgn).max()]
            bot = x[x[f] * sgn == (x[f] * sgn).min()]
        else:
            q = x.groupby("date")[f].transform(lambda v: pd.qcut((v * sgn).rank(method="first"), 10, labels=False, duplicates="drop"))
            top, bot = x[q == 9], x[q == 0]
        def stat(s):
            s = s[y]
            win, loss = s[s > 0], s[s <= 0]
            return {"hit": (s > 0).mean(), "avg": s.mean(), "win": win.mean(), "loss": loss.mean(),
                    "payoff": (win.mean() / -loss.mean()) if len(loss) and loss.mean() < 0 else np.nan, "n": len(s)}
        t, b = stat(top), stat(bot)
        rows.append({"feature": f, "fam": fam, "IC": ics.mean(), "t": _t(ics), "dates": len(ics),
                     "top_hit": t["hit"], "top_avg%": t["avg"] * 100, "top_win%": t["win"] * 100, "top_loss%": t["loss"] * 100,
                     "payoff": t["payoff"], "bot_hit": b["hit"], "bot_avg%": b["avg"] * 100, "spread%": (t["avg"] - b["avg"]) * 100,
                     **_splits(ics)})
    t = pd.DataFrame(rows).sort_values("t", ascending=False)
    n = len(t)
    bar = np.sqrt(2 * np.log(max(n, 2)))
    print(f"\n{'='*140}\n{label}: {h}-session excess return, {n} features, noise bar t ~ {bar:.1f}; "
          f"top decile = best tenth by the feature's expected sign; hit = share of names with positive excess")
    print(t.to_string(index=False, float_format=lambda v: f"{v:7.3f}"))
    print(f"  beyond the noise bar: {', '.join(t[t.t.abs() > bar].feature)} ({(t.t.abs() > bar).sum()} of {n}); "
          f"positive in all three splits: {', '.join(t[(t[list(SPLITS)].apply(lambda c: c.str.startswith('+'))).all(axis=1)].feature)}")
    return t


def event_study(e, close, spy):
    """What happens after an earnings reaction of each size, in raw excess-of-SPY terms."""
    cv = close.values
    pos = close.index.get_indexer(e.sig)
    ci = close.columns.get_indexer(e.act_symbol)
    n = len(close.index)
    out = e[["act_symbol", "sig", "sue", "ear", "ear_x", "runup10", "volx", "surprise_ratio"]].copy()
    for a, b, lab in ((1, 1, "d2"), (2, 5, "d3_5"), (6, 21, "d6_21"), (22, 63, "d22_63")):
        ok = (pos + b) < n
        r = np.full(len(e), np.nan)
        r[ok] = cv[pos[ok] + b, ci[ok]] / cv[pos[ok] + a - 1, ci[ok]] - 1
        s = np.full(len(e), np.nan)
        s[ok] = spy.values[pos[ok] + b] / spy.values[pos[ok] + a - 1] - 1
        out[lab] = r - s
    out["ear_b"] = pd.cut(out.ear_x, [-1, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 1],
                          labels=["<-10%", "-10..-5", "-5..-2", "-2..2", "2..5", "5..10", ">10%"])
    cols = ["d2", "d3_5", "d6_21", "d22_63"]
    print(f"\n{'='*140}\nEVENT STUDY: {len(out):,} earnings reactions, excess over SPY (%), by the size of the reaction day")
    g = out.groupby("ear_b", observed=True)
    tab = pd.concat([g.size().rename("n"), g[cols].mean() * 100, (g.d2.apply(lambda s: (s > 0).mean())).rename("d2_hit"),
                     g.d2.apply(lambda s: s.mean() / s.std() * np.sqrt(len(s))).rename("d2_t")], axis=1)
    print(tab.round(3).to_string())
    out["quad"] = np.select([(out.sue > 0) & (out.ear_x > 0), (out.sue > 0) & (out.ear_x <= 0), (out.sue <= 0) & (out.ear_x > 0)],
                            ["beat+up", "beat+DOWN (sold the news)", "miss+UP", ], "miss+down")
    g = out.groupby("quad")
    print("\nby surprise x reaction quadrant:")
    print(pd.concat([g.size().rename("n"), g[cols].mean() * 100,
                     g.d6_21.apply(lambda s: s.mean() / s.std() * np.sqrt(len(s))).rename("d6_21_t")], axis=1).round(3).to_string())
    out["run_b"] = pd.qcut(out.runup10, 3, labels=["ran down", "flat", "ran up"])
    print("\nbig reactions (|ear| > 5%) by the 10-session run-up INTO the print:")
    big = out[out.ear_x.abs() > 0.05]
    g = big.groupby(["run_b", big.ear_x > 0], observed=True)
    print((pd.concat([g.size().rename("n"), g[cols].mean() * 100], axis=1)).round(3).to_string())
    print("\nby the move against what the straddle implied (ratio = |reaction| / implied move):")
    out["sr_b"] = pd.cut(out.surprise_ratio, [0, 0.5, 1, 2, 100], labels=["<0.5x", "0.5-1x", "1-2x", ">2x"])
    g = out[out.ear_x > 0].groupby("sr_b", observed=True)
    print("  reaction UP:\n" + (pd.concat([g.size().rename("n"), g[cols].mean() * 100], axis=1)).round(3).to_string())
    g = out[out.ear_x < 0].groupby("sr_b", observed=True)
    print("  reaction DOWN:\n" + (pd.concat([g.size().rename("n"), g[cols].mean() * 100], axis=1)).round(3).to_string())
    for k, (a, b) in SPLITS.items():
        s = out[(out.sig >= a) & (out.sig <= b)]
        q = s[s.quad == "beat+DOWN (sold the news)"]
        print(f"  split {k}: beat+DOWN d6_21 {q.d6_21.mean()*100:+.2f}% (n {len(q)}), gap>10% d2 {s[s.ear_x>0.10].d2.mean()*100:+.2f}%, "
              f"gap<-10% d2 {s[s.ear_x<-0.10].d2.mean()*100:+.2f}%")
    return out


def _score_model(p, y, label, hold_w):
    ics = p.groupby("date").apply(lambda g: stats.spearmanr(g.pred, g[y])[0] if len(g) >= 50 else np.nan, include_groups=False).dropna()
    p["dec"] = p.groupby("date").pred.transform(lambda v: pd.qcut(v.rank(method="first"), 10, labels=False, duplicates="drop"))
    top = p[p.dec == 9]
    s = top.groupby("date")[y].mean()
    hit_name = (top[y] > 0).mean()
    win, loss = top[top[y] > 0][y].mean(), top[top[y] <= 0][y].mean()
    sets = {dt: set(g.act_symbol) for dt, g in top.groupby("date")}
    ks = sorted(sets)
    to = np.mean([1 - len(sets[a] & sets[b]) / max(len(sets[b]), 1) for a, b in zip(ks[:-1], ks[1:])]) if len(ks) > 1 else 1.0
    net = s.mean() - 2 * COST * to
    bot = p[p.dec == 0].groupby("date")[y].mean()
    spread = (s - bot).dropna()
    print(f"\n{label}: {len(ics)} dates, IC {ics.mean():+.4f} (t {_t(ics):+.2f}); splits {_splits(ics)}")
    print(f"   TOP DECILE per {hold_w}-week hold: name hit rate {hit_name:.3f}, avg {s.mean()*100:+.3f}%, "
          f"win {win*100:+.2f}% / loss {loss*100:+.2f}% (payoff {win/-loss:.2f}), date hit {(s>0).mean():.2f}, "
          f"turnover {to*100:.0f}%/hold, net of 15 bp/side {net*100:+.3f}% => {net*52/hold_w*100:+.1f}%/yr excess; "
          f"D10-D1 {spread.mean()*100:+.3f}% (t {_t(spread):+.2f})")
    for k, (a, b) in SPLITS.items():
        ss = s[(s.index >= a) & (s.index <= b)]
        if len(ss) > 5:
            tt = top[(top.date >= a) & (top.date <= b)]
            print(f"     {k}: top avg {ss.mean()*100:+.3f}%/hold, name hit {(tt[y]>0).mean():.3f}, net {(ss.mean()-2*COST*to)*52/hold_w*100:+.1f}%/yr")


def fama_macbeth(w, feats, h, window=104):
    y = f"ex{h}"
    step = max(1, h // 5)
    lag = int(np.ceil(h / 5)) + 1
    d = w[["date", "act_symbol", y] + feats].copy()
    for f in feats:
        d[f] = (d.groupby("date")[f].rank(pct=True) - 0.5).fillna(0.0)
    d = d.dropna(subset=[y])
    dates = np.sort(d.date.unique())
    betas = {}
    for dt in dates:
        g = d[d.date == dt]
        if len(g) < 200:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[f].values for f in feats])
        b, *_ = np.linalg.lstsq(X, g[y].values, rcond=None)
        betas[dt] = b[1:]
    bk = sorted(betas)
    preds = []
    for i, dt in enumerate(dates[::step]):
        j = np.searchsorted(dates, dt)
        cutoff = dates[max(0, j - lag)]
        past = [betas[k] for k in bk if k <= cutoff][-window:]
        if len(past) < 52:
            continue
        bbar = np.mean(past, axis=0)
        g = d[d.date == dt].copy()
        g["pred"] = g[feats].values @ bbar
        preds.append(g)
    p = pd.concat(preds)
    _score_model(p, y, f"FAMA-MACBETH walk-forward, {len(feats)} features -> {y}", step)
    return p


def lightgbm_model(w, feats, h, refit_every=26, min_train=104):
    try:
        import lightgbm as lgb
    except ImportError:
        print("lightgbm not installed; skipped")
        return None
    y = f"ex{h}"
    step = max(1, h // 5)
    lag = int(np.ceil(h / 5)) + 1
    d = w[["date", "act_symbol", y] + feats + MARKET].copy()
    for f in feats:
        d[f] = d.groupby("date")[f].rank(pct=True) - 0.5
    d["yr"] = d.groupby("date")[y].rank(pct=True) - 0.5        # rank target: robust to outliers
    d = d.dropna(subset=[y])
    dates = np.sort(d.date.unique())
    X_cols = feats + MARKET
    preds = []
    model = None
    for i in range(0, len(dates), 1):
        dt = dates[i]
        if i % refit_every == 0:
            j = max(0, i - lag)
            train = d[d.date <= dates[j]]
            if train.date.nunique() < min_train:
                continue
            model = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=200,
                                      subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbose=-1)
            model.fit(train[X_cols], train.yr)
        if model is None or (i % step):
            continue
        g = d[d.date == dt].copy()
        g["pred"] = model.predict(g[X_cols])
        preds.append(g)
    if not preds:
        return None
    p = pd.concat(preds)
    _score_model(p, y, f"LIGHTGBM walk-forward (refit every {refit_every} weeks, rank target, market state in), {len(feats)} features -> {y}", step)
    imp = pd.Series(model.feature_importances_, index=X_cols).sort_values(ascending=False)
    print("   last model's top features by split count:", ", ".join(f"{k} {v}" for k, v in imp.head(12).items()))
    return p


def main():
    pd.set_option("display.width", 250)
    w, e, close, spy = build()
    w.to_parquet(os.path.join(PANEL, "signal_panel.parquet"), index=False)
    print(f"panel: {len(w):,} name-weeks, {w.act_symbol.nunique()} names, {w.date.nunique()} weeks, "
          f"{w.date.min().date()}..{w.date.max().date()}; features {len([f for f in FEATURES if f in w])}")
    tables = {}
    for h in HORIZONS:
        tables[h] = accuracy_table(w, h, FEATURES, "ALL FEATURES")
    # regime splits for the market-factor question
    for reg, mask in (("BULL (SPY 12m > 0)", w.spy_12m > 0), ("BEAR (SPY 12m <= 0)", w.spy_12m <= 0),
                      ("HIGH VIX (rank > 0.7)", w.vix_rank > 0.7), ("LOW VIX (rank < 0.3)", w.vix_rank < 0.3)):
        sub = w[mask]
        if sub.date.nunique() > 40:
            accuracy_table(sub, 21, {k: v for k, v in FEATURES.items() if v[1] in ("price", "pattern", "earnings")}, f"REGIME {reg}, price+pattern+earnings")
    ev = event_study(e, close, spy)
    ev.to_parquet(os.path.join(PANEL, "earnings_event_study.parquet"), index=False)
    feats = [f for f in FEATURES if f in w and w[f].notna().mean() > 0.3]
    for h in (5, 21):
        fama_macbeth(w, feats, h)
        lightgbm_model(w, feats, h)
    lightgbm_model(w, feats, 63)


if __name__ == "__main__":
    main()
