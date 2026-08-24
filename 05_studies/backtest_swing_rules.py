"""backtest_swing_rules.py — sector-rotation relative-strength swing options, rigorously validated.

THESIS
------
0DTE cannot monetise a directional edge: the day's expected move is tiny next to the day's option
premium (see backtest_0dte_rules.py).  Swing is the opposite regime — a 1-3% monthly momentum edge
is LARGE relative to a 30-45 DTE option's cost.  So if a directional edge is going to pay for
options anywhere, it pays here.

RULES UNDER TEST
  entry     : monthly (21-trading-day) rebalance; rank a fixed ETF universe by relative strength
              (total return over N days, skipping the last 5 to dodge short-term reversal);
              take the top K.
  regime    : only when SPY is above its 200-day SMA (a well-known, externally-documented filter,
              not something we searched for here).
  IV filter : optionally require the name's realised-vol percentile to be low (cheap options).
  structure : 35-DTE call debit spread (long ~ATM, short ~1 SD out) or a plain ~ATM long call.
  exit      : close after 21 trading days (14 DTE left) — never held into gamma/theta cliff.

ANTI-OVERFIT CONTROLS
  * every signal lagged one day; rebalance prices are the NEXT day's close after the ranking date.
  * anchored walk-forward: parameters chosen on data strictly before each OOS year.
  * three controls printed next to every result: (a) the same option structure on SPY,
    (b) the same structure on a RANDOMLY chosen universe member, (c) equal-weight all names.
  * a permutation test on the ranking.
  * Deflated Sharpe with n_trials = grid size.
  * vrp swept 1.00 -> 1.25; the whole option model is the same one used in the 0DTE study.

Run:  venv/bin/python3 backtest_swing_rules.py [section ...]
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import bt_options as bo

from idt import paths

warnings.filterwarnings("ignore")
pd.set_option("display.width", 220)

# Same as backtest_0dte_rules: the cache pointed inside the source tree, at a
# directory that does not exist, so it was written nowhere and read never.
CACHE = paths.data("cache", "btswing_panel.parquet")

UNIVERSE = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLRE", "XLC",
            "QQQ", "IWM"]
BENCH = "SPY"
START = "1999-01-01"
TRAIN_END = "2009-12-31"
OOS_START = "2010-01-01"

REB = 21            # rebalance / holding period, trading days
DTE_ENTRY = 35      # calendar-ish: modelled as 35/252 years at entry
DTE_EXIT = 14
VRP_GRID = [1.00, 1.05, 1.10, 1.20]
VRP_BASE = 1.10
SKEW = 0.10         # single-name/sector-ETF skew is flatter than SPX
# ETF options are wider than SPY 0DTE: 2% half-spread with a 2c floor, charged BOTH ways
COSTS = bo.Costs(spread_pct=0.020, spread_floor=0.02, fee_per_contract=0.05)


# ============================================================================ data
def build_panel(force=False):
    if os.path.exists(CACHE) and not force:
        return pd.read_parquet(CACHE)
    import yfinance as yf
    tick = UNIVERSE + [BENCH, "^VIX", "^VIX9D"]
    print(f"downloading {len(tick)} series ...")
    px = yf.download(tick, start=START, interval="1d", progress=False, auto_adjust=True)
    close = px["Close"].copy()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.dropna(how="all")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    close.to_parquet(CACHE)
    print(f"panel {close.shape} {close.index.min().date()} -> {close.index.max().date()}")
    return close


def build_features(close: pd.DataFrame):
    """All features are computed from data up to and including day t; trades execute at t+1's close."""
    rets = close[UNIVERSE + [BENCH]].pct_change()
    f = {}
    for n in (63, 126, 252):
        # skip the most recent 5 days (short-term reversal) — a standard, pre-registered choice
        f[f"mom{n}"] = close[UNIVERSE].shift(5) / close[UNIVERSE].shift(n) - 1
        f[f"rs{n}"] = f[f"mom{n}"].sub(close[BENCH].shift(5) / close[BENCH].shift(n) - 1, axis=0)
    # realised vol (causal) for the option model and the IV-rank proxy
    rv = rets[UNIVERSE].rolling(60).std() * bo.SQRT252
    f["rv"] = rv
    f["rv_pct"] = rv.rolling(252, min_periods=120).rank(pct=True)
    f["regime"] = (close[BENCH] > close[BENCH].rolling(200).mean())
    f["vix"] = close["^VIX"]
    f["ts"] = close["^VIX9D"] / close["^VIX"]
    return f


# ============================================================================ underlying-level test
def section_underlying(close, F):
    print("\n" + "=" * 100)
    print("SECTION: UNDERLYING-LEVEL TEST — is there a sector relative-strength edge at all?")
    print("=" * 100)
    print("(no options yet.  if the raw signal has no edge on the ETF itself, nothing downstream matters)")
    fwd = close[UNIVERSE].shift(-REB) / close[UNIVERSE] - 1
    fwd_b = close[BENCH].shift(-REB) / close[BENCH] - 1
    exc = fwd.sub(fwd_b, axis=0)          # forward EXCESS return vs SPY

    dates = close.index[(close.index >= OOS_START)]
    dates = dates[::REB]
    print(f"\n{'lookback':>9}{'topK':>6}{'n':>6}{'avg exc%':>10}{'win%':>7}{'t':>7}{'  (OOS 2010+, 21d holds)'}")
    for n in (63, 126, 252):
        rs = F[f"rs{n}"]
        for K in (1, 2, 3):
            picks = []
            for dt in dates:
                if dt not in rs.index or dt not in exc.index:
                    continue
                r = rs.loc[dt].dropna()
                if len(r) < 6:
                    continue
                top = r.nlargest(K).index
                v = exc.loc[dt, top].dropna()
                if len(v):
                    picks.append(v.mean())
            if len(picks) < 20:
                continue
            t, p = stats.ttest_1samp(picks, 0)
            print(f"{n:>9}{K:>6}{len(picks):>6}{np.mean(picks)*100:>+10.2f}"
                  f"{np.mean(np.array(picks)>0)*100:>7.0f}{t:>+7.2f}")
    print("\n  same, but SPY-above-200d regime filter ON:")
    reg = F["regime"]
    for n in (63, 126, 252):
        rs = F[f"rs{n}"]
        for K in (1, 2, 3):
            picks = []
            for dt in dates:
                if dt not in rs.index or not bool(reg.get(dt, False)):
                    continue
                r = rs.loc[dt].dropna()
                if len(r) < 6:
                    continue
                v = exc.loc[dt, r.nlargest(K).index].dropna()
                if len(v):
                    picks.append(v.mean())
            if len(picks) < 20:
                continue
            t, p = stats.ttest_1samp(picks, 0)
            print(f"{n:>9}{K:>6}{len(picks):>6}{np.mean(picks)*100:>+10.2f}"
                  f"{np.mean(np.array(picks)>0)*100:>7.0f}{t:>+7.2f}")

    print("\n  ABSOLUTE (not excess) forward return of the picks — this is what an option pays on:")
    for n in (63, 126, 252):
        rs = F[f"rs{n}"]
        for K in (1, 2, 3):
            abs_, bench_ = [], []
            for dt in dates:
                if dt not in rs.index or not bool(reg.get(dt, False)):
                    continue
                r = rs.loc[dt].dropna()
                if len(r) < 6:
                    continue
                v = fwd.loc[dt, r.nlargest(K).index].dropna()
                if len(v):
                    abs_.append(v.mean()); bench_.append(fwd_b.get(dt, np.nan))
            if len(abs_) < 20:
                continue
            t, _ = stats.ttest_1samp(abs_, 0)
            print(f"{n:>9}{K:>6}{len(abs_):>6}{np.mean(abs_)*100:>+10.2f}"
                  f"{np.mean(np.array(abs_)>0)*100:>7.0f}{t:>+7.2f}   [SPY same days "
                  f"{np.nanmean(bench_)*100:+.2f}%]")


def section_alternatives(close, F):
    """Sector RS failed at the underlying level.  Before giving up on swing, test the alternatives
    that have real external evidence behind them, with the same rigour."""
    print("\n" + "=" * 100)
    print("SECTION: ALTERNATIVES — what else could pay for a 21-45 day option?")
    print("=" * 100)
    idx = close.index
    reg = F["regime"]
    ts = F["ts"]
    fwd = {s: close[s].shift(-REB) / close[s] - 1 for s in (BENCH, "QQQ")}

    print("\n-- A. did sector RS EVER work here?  (train era vs OOS era — decay check) --")
    excs = {}
    for era, lo, hi in [("1999-2009 (train)", "1999-01-01", "2009-12-31"),
                        ("2010-2017", "2010-01-01", "2017-12-31"),
                        ("2018-2026", "2018-01-01", "2026-12-31")]:
        dts = idx[(idx >= lo) & (idx <= hi)][::REB]
        rs = F["rs126"]
        f = close[UNIVERSE].shift(-REB) / close[UNIVERSE] - 1
        fb = close[BENCH].shift(-REB) / close[BENCH] - 1
        e = f.sub(fb, axis=0)
        v = []
        for dt in dts:
            if dt not in rs.index:
                continue
            r = rs.loc[dt].dropna()
            if len(r) < 6:
                continue
            x = e.loc[dt, r.nlargest(2).index].dropna()
            if len(x):
                v.append(x.mean())
        if len(v) < 15:
            continue
        t, _ = stats.ttest_1samp(v, 0)
        excs[era] = (len(v), np.mean(v), t)
        print(f"   {era:<20} n={len(v):>3}  excess vs SPY {np.mean(v)*100:+6.2f}%  t {t:+5.2f}")

    print("\n-- B. plain index drift: SPY / QQQ 21-day forward return, by regime filter --")
    print(f"{'filter':<34}{'sym':>5}{'n':>6}{'avg%':>8}{'win%':>7}{'t':>7}{'sd%':>8}")
    filters = [("none", lambda dt: True),
               ("SPY > 200d SMA", lambda dt: bool(reg.get(dt, False))),
               ("VIX term contango (9D<30D)", lambda dt: float(ts.get(dt, np.nan)) < 1.0),
               ("SPY>200d AND contango", lambda dt: bool(reg.get(dt, False)) and float(ts.get(dt, 9)) < 1.0)]
    for lab, fn in filters:
        for sym in (BENCH, "QQQ"):
            dts = [dt for dt in idx[idx >= OOS_START][::REB] if fn(dt)]
            v = [fwd[sym].get(dt, np.nan) for dt in dts]
            v = np.array([x for x in v if np.isfinite(x)])
            if len(v) < 20:
                continue
            t, _ = stats.ttest_1samp(v, 0)
            print(f"{lab:<34}{sym:>5}{len(v):>6}{v.mean()*100:>+8.2f}{(v>0).mean()*100:>7.0f}"
                  f"{t:>+7.2f}{v.std()*100:>8.2f}")

    print("\n-- C. can that drift pay for a 35-DTE CALL DEBIT SPREAD on SPY/QQQ? --")
    rv = close.pct_change().rolling(60).std() * bo.SQRT252
    for lab, fn in filters:
        for vrp in (1.00, VRP_BASE, 1.20):
            rets = []
            for sym in (BENCH, "QQQ"):
                for dt in idx[idx >= OOS_START][::REB]:
                    i = idx.get_loc(dt)
                    if i + 1 + REB >= len(idx) or not fn(dt):
                        continue
                    S0, S1 = close[sym].iloc[i + 1], close[sym].iloc[i + 1 + REB]
                    sg = rv[sym].iloc[i]
                    if not np.isfinite(sg) or sg <= 0:
                        continue
                    t_ = swing_trade(S0, S1, sg, "debit", vrp, 1.0)
                    if t_:
                        rets.append(t_["ret"])
            if len(rets) < 30:
                continue
            r = np.array(rets); tt, _ = stats.ttest_1samp(r, 0)
            print(f"   {lab:<30} vrp={vrp:.2f}  n={len(r):>4} avg {r.mean()*100:+7.1f}% "
                  f"win {(r>0).mean()*100:3.0f}% t {tt:+5.2f}")

    print("\n-- D. the VRP route: 35-DTE PUT CREDIT SPREAD on SPY (-1SD short, 1SD wide) --")
    print("   This is the swing analogue of the 0DTE finding.  Controls = no filter.")
    for lab, fn in filters:
        for vrp in (1.00, VRP_BASE, 1.20):
            rets = []
            for dt in idx[idx >= OOS_START][::REB]:
                i = idx.get_loc(dt)
                if i + 1 + REB >= len(idx) or not fn(dt):
                    continue
                S0, S1 = close[BENCH].iloc[i + 1], close[BENCH].iloc[i + 1 + REB]
                sg = rv[BENCH].iloc[i]
                if not np.isfinite(sg) or sg <= 0:
                    continue
                T0, T1 = DTE_ENTRY / 252.0, DTE_EXIT / 252.0
                iv = vrp * sg
                sm = S0 * iv * np.sqrt(T0)
                Ks = bo.round_strike(S0 - sm, 1.0); Kl = bo.round_strike(Ks - sm, 1.0)
                if Kl >= Ks:
                    continue
                cr = (COSTS.sell(bo.price_leg(S0, Ks, T0, iv, sm, False, SKEW))
                      - COSTS.buy(bo.price_leg(S0, Kl, T0, iv, sm, False, SKEW)))
                width = Ks - Kl
                risk = width - cr
                if cr <= 0 or risk <= 0:
                    continue
                out = (COSTS.buy(bo.price_leg(S1, Ks, T1, iv, sm, False, SKEW))
                       - COSTS.sell(bo.price_leg(S1, Kl, T1, iv, sm, False, SKEW)))
                rets.append((cr - out) / risk)
            if len(rets) < 25:
                continue
            r = np.array(rets); tt, _ = stats.ttest_1samp(r, 0)
            eq = np.cumprod(1 + 0.25 * r)
            print(f"   {lab:<30} vrp={vrp:.2f}  n={len(r):>4} avg {r.mean()*100:+6.2f}% "
                  f"win {(r>0).mean()*100:3.0f}% t {tt:+5.2f} worst {r.min()*100:+5.0f}% "
                  f"DD@25% {bo.max_dd(eq)*100:4.0f}%")


# ============================================================================ option overlay
def swing_trade(S0, S1, sigma, structure, vrp, short_sd=1.0):
    """35-DTE entry, exit with 14 DTE left."""
    T0, T1 = DTE_ENTRY / 252.0, DTE_EXIT / 252.0
    iv = vrp * sigma
    sm = S0 * iv * np.sqrt(T0)
    if sm <= 0:
        return None
    inc = 1.0 if S0 > 40 else 0.5
    if structure == "long":
        return bo.long_option(S0, S1, T0, iv, sm, True, COSTS, skew=SKEW, strike_inc=inc, T1=T1)
    if structure == "debit":
        Kl = bo.round_strike(S0, inc)
        Ks = bo.round_strike(S0 + short_sd * sm, inc)
        if Ks <= Kl:
            Ks = Kl + inc
        e = (COSTS.buy(bo.price_leg(S0, Kl, T0, iv, sm, True, SKEW))
             - COSTS.sell(bo.price_leg(S0, Ks, T0, iv, sm, True, SKEW)))
        if e <= 0:
            return None
        x = (COSTS.sell(bo.price_leg(S1, Kl, T1, iv, sm, True, SKEW))
             - COSTS.buy(bo.price_leg(S1, Ks, T1, iv, sm, True, SKEW)))
        x = max(x, 0.0)      # a worthless spread is abandoned, not closed at a negative price
        return dict(debit=e, risk=e, pnl=x - e, ret=(x - e) / e)
    raise ValueError(structure)


def run_swing(close, F, cfg, vrp, start=OOS_START, end=None, seed=None):
    """One configuration -> a trade list.  cfg keys: n, K, regime, structure, short_sd, rvmax, mode."""
    rs = F[f"rs{cfg['n']}"]
    rv = F["rv"]; rvp = F["rv_pct"]; reg = F["regime"]
    idx = close.index
    dates = idx[(idx >= start)]
    if end:
        dates = dates[dates <= end]
    dates = dates[::REB]
    rng = np.random.default_rng(seed if seed is not None else 0)
    out = []
    for dt in dates:
        i = idx.get_loc(dt)
        if i + 1 + REB >= len(idx):
            continue
        if cfg.get("regime", True) and not bool(reg.get(dt, False)):
            continue
        r = rs.loc[dt].dropna()
        if len(r) < 6:
            continue
        mode = cfg.get("mode", "top")
        if mode == "top":
            names = list(r.nlargest(cfg["K"]).index)
        elif mode == "random":
            names = list(rng.choice(r.index, min(cfg["K"], len(r)), replace=False))
        elif mode == "bench":
            names = [BENCH]
        elif mode == "equal":
            names = list(r.index)
        elif mode == "bottom":
            names = list(r.nsmallest(cfg["K"]).index)
        if cfg.get("rvmax") is not None and mode == "top":
            names = [x for x in names if rvp.loc[dt].get(x, 1.0) <= cfg["rvmax"]]
        d_ent, d_exit = idx[i + 1], idx[i + 1 + REB]
        for nm in names:
            S0 = close.loc[d_ent, nm]; S1 = close.loc[d_exit, nm]
            sg = rv.loc[dt].get(nm, np.nan) if nm in rv.columns else \
                close[BENCH].pct_change().rolling(60).std().loc[dt] * bo.SQRT252
            if not np.isfinite(S0) or not np.isfinite(S1) or not np.isfinite(sg) or sg <= 0:
                continue
            t = swing_trade(S0, S1, sg, cfg["structure"], vrp, cfg.get("short_sd", 1.0))
            if t is None:
                continue
            out.append(dict(date=d_ent, name=nm, ret=t["ret"], risk=t["risk"],
                            und=S1 / S0 - 1, year=d_ent.year))
    return pd.DataFrame(out)


def portfolio_returns(T):
    """Equal-weight the trades opened on the same date -> one portfolio return per rebalance."""
    if T.empty:
        return pd.Series(dtype=float)
    return T.groupby("date").ret.mean()


def section_options(close, F):
    print("\n" + "=" * 100)
    print("SECTION: OPTION OVERLAY — does the RS signal pay for 35-DTE calls?")
    print("=" * 100)
    base = dict(n=126, K=2, regime=True, structure="debit", short_sd=1.0)
    print("\n-- structure comparison, OOS 2010+, with the three controls --")
    for structure in ("long", "debit"):
        for vrp in VRP_GRID:
            cfg = dict(base, structure=structure)
            T = run_swing(close, F, cfg, vrp)
            Cb = run_swing(close, F, dict(cfg, mode="bench"), vrp)
            Cr = run_swing(close, F, dict(cfg, mode="random"), vrp, seed=11)
            Ce = run_swing(close, F, dict(cfg, mode="equal"), vrp)
            p = portfolio_returns(T)
            print(f"  {structure:<6} vrp={vrp:.2f}  n={len(T):>4}  avg {T.ret.mean()*100:+7.1f}%  "
                  f"win {(T.ret>0).mean()*100:3.0f}%  || SPY-ctrl {Cb.ret.mean()*100:+7.1f}%  "
                  f"random-ctrl {Cr.ret.mean()*100:+7.1f}%  equalwt-ctrl {Ce.ret.mean()*100:+7.1f}%"
                  f"  || EDGE vs equalwt {(T.ret.mean()-Ce.ret.mean())*100:+6.1f}pp")

    print("\n-- top-vs-bottom spread (the cleanest signal test; both sides pay the same VRP) --")
    for vrp in (1.00, VRP_BASE, 1.20):
        for structure in ("long", "debit"):
            Tt = run_swing(close, F, dict(base, structure=structure, mode="top"), vrp)
            Tb = run_swing(close, F, dict(base, structure=structure, mode="bottom"), vrp)
            t, p = stats.ttest_ind(Tt.ret, Tb.ret, equal_var=False)
            print(f"   {structure:<6} vrp={vrp:.2f}  TOP {Tt.ret.mean()*100:+7.1f}%  "
                  f"BOTTOM {Tb.ret.mean()*100:+7.1f}%  spread {(Tt.ret.mean()-Tb.ret.mean())*100:+6.1f}pp"
                  f"  t {t:+5.2f}  p {p:.3f}")

    print("\n-- IV-structure filter: only buy when the name's realised vol is in the lower X pct --")
    for rvmax in (None, 0.4, 0.6, 0.8):
        T = run_swing(close, F, dict(base, rvmax=rvmax), VRP_BASE)
        if len(T) < 30:
            continue
        r = bo.summarize(T.ret, "", verbose=False)
        print(f"   rv_pct <= {str(rvmax):<5}: n={r['n']:>4} avg {r['avg']*100:+6.1f}% win {r['win']*100:3.0f}%"
              f" t {r['t']:+5.2f}")

    print("\n-- regime filter on/off --")
    for regime in (True, False):
        T = run_swing(close, F, dict(base, regime=regime), VRP_BASE)
        r = bo.summarize(T.ret, "", verbose=False)
        print(f"   SPY>200d filter {str(regime):<5}: n={r['n']:>4} avg {r['avg']*100:+6.1f}% "
              f"win {r['win']*100:3.0f}% t {r['t']:+5.2f}  PF {r['pf']:.2f}")

    print("\n-- PERMUTATION test: shuffle which names get picked, 300x (vrp=1.10, debit) --")
    T = run_swing(close, F, base, VRP_BASE)
    real = T.ret.mean()
    null = []
    for s in range(300):
        C = run_swing(close, F, dict(base, mode="random"), VRP_BASE, seed=1000 + s)
        null.append(C.ret.mean())
    null = np.array(null)
    print(f"   real {real*100:+.2f}%   null mean {null.mean()*100:+.2f}%  sd {null.std()*100:.2f}%   "
          f"p(one-sided) {(null >= real).mean():.3f}")


# ============================================================================ walk-forward
GRID = [dict(n=n, K=K, regime=reg, structure=st, short_sd=1.0)
        for n in (63, 126, 252) for K in (1, 2, 3) for reg in (True, False)
        for st in ("debit",)]


def section_walkforward(close, F):
    print("\n" + "=" * 100)
    print("SECTION: ANCHORED WALK-FORWARD (parameters never see the year they trade)")
    print("=" * 100)
    print(f"grid = {len(GRID)} configs; train = everything before Jan-1 of each OOS year")
    years = range(2010, int(close.index.max().year) + 1)
    for vrp in VRP_GRID:
        allt, picks = [], []
        for y in years:
            best, bsc = None, -9e9
            for cfg in GRID:
                Ttr = run_swing(close, F, cfg, vrp, start="1999-01-01", end=f"{y-1}-12-31")
                p = portfolio_returns(Ttr)
                if len(p) < 30:
                    continue
                sc = p.mean() / (p.std() + 1e-9)
                if sc > bsc:
                    bsc, best = sc, cfg
            if best is None:
                continue
            Tte = run_swing(close, F, best, vrp, start=f"{y}-01-01", end=f"{y}-12-31")
            if len(Tte):
                allt.append(Tte)
            picks.append((y, best["n"], best["K"], best["regime"], len(Tte)))
        if not allt:
            continue
        A = pd.concat(allt)
        p = portfolio_returns(A)
        bo.summarize(A.ret, f"WALK-FWD swing (per-trade) vrp={vrp:.2f}", n_trials=len(GRID),
                     risk_frac=0.20)
        bo.summarize(p.values, "   ... as a PORTFOLIO (per 21d period) ", n_trials=len(GRID),
                     periods=12, risk_frac=0.50)
        if vrp == VRP_BASE:
            print("     picks:", ", ".join(f"{y}:n{n}K{k}{'R' if r else '-'}" for y, n, k, r, _ in picks))
            yr = A.groupby("year").ret.agg(["size", "mean", lambda x: (x > 0).mean()])
            yr.columns = ["n", "avg", "win"]
            print(yr.assign(avg=lambda x: (x.avg * 100).round(1),
                            win=lambda x: (x.win * 100).round(0)).to_string())


INDEX_SYMS = ["SPY", "QQQ"]
IDX_GRID = [dict(structure=st, regime=rg, short_sd=sd)
            for st in ("long", "debit") for rg in (True, False) for sd in (0.75, 1.0, 1.5)]


def index_trades(close, F, cfg, vrp, start=OOS_START, end=None, stride=REB, syms=None):
    """Staggered index option overlay.  stride=21 -> monthly; stride=5 -> weekly overlapping."""
    idx = close.index
    rv = close.pct_change().rolling(60).std() * bo.SQRT252
    reg = F["regime"]
    syms = syms or INDEX_SYMS
    dts = idx[(idx >= start)]
    if end:
        dts = dts[dts <= end]
    out = []
    for dt in dts[::stride]:
        i = idx.get_loc(dt)
        if i + 1 + REB >= len(idx):
            continue
        if cfg.get("regime", True) and not bool(reg.get(dt, False)):
            continue
        for sym in syms:
            S0, S1 = close[sym].iloc[i + 1], close[sym].iloc[i + 1 + REB]
            sg = rv[sym].iloc[i]
            if not (np.isfinite(S0) and np.isfinite(S1) and np.isfinite(sg)) or sg <= 0:
                continue
            t = swing_trade(S0, S1, sg, cfg["structure"], vrp, cfg.get("short_sd", 1.0))
            if t:
                out.append(dict(date=idx[i + 1], name=sym, ret=t["ret"], risk=t["risk"],
                                und=S1 / S0 - 1, year=idx[i + 1].year))
    return pd.DataFrame(out)



def simulate_tranches(T, close, f=0.05, max_exposure=0.25, hold=REB):
    """Realistic overlapping-tranche simulation.

    Weekly (or whatever stride T was built with) we open a new trade risking `f` of CURRENT equity,
    subject to a hard cap on total simultaneous at-risk capital (`max_exposure` of equity).  Because
    a 21-day hold with weekly entries keeps ~4 tranches alive at once, `f` and `max_exposure` are NOT
    interchangeable -- this is exactly the sizing mistake that makes naive backtests look insane.

    Returns (equity_series_on_exit_dates, stats dict).
    """
    if T.empty:
        return pd.Series(dtype=float), {}
    idx = close.index
    T = T.sort_values("date")
    # each row exits `hold` trading days after entry
    pos = []
    for _, r in T.iterrows():
        i = idx.get_loc(r["date"])
        if i + hold >= len(idx):
            continue
        pos.append((r["date"], idx[i + hold], r["ret"]))
    events = sorted({d for p_ in pos for d in (p_[0], p_[1])})
    open_pos, equity, curve, deployed = [], 1.0, [], 0.0
    byentry = {}
    for e, x, rr in pos:
        byentry.setdefault(e, []).append((x, rr))
    for dt in events:
        # settle exits first
        still = []
        for (x, stake, rr) in open_pos:
            if x <= dt:
                equity += stake * rr
                deployed -= stake
            else:
                still.append((x, stake, rr))
        open_pos = still
        # then open new
        for (x, rr) in byentry.get(dt, []):
            stake = f * equity
            if deployed + stake > max_exposure * equity:
                continue
            open_pos.append((x, stake, rr))
            deployed += stake
        curve.append((dt, equity))
    eq = pd.Series([v for _, v in curve], index=[d for d, _ in curve])
    # honest Sharpe: aggregate the equity curve to NON-OVERLAPPING monthly returns
    m = eq.resample("ME").last().dropna()
    mr = m.pct_change().dropna()
    yrs = (eq.index.max() - eq.index.min()).days / 365.25
    st = dict(final=float(eq.iloc[-1]), cagr=float(eq.iloc[-1] ** (1 / yrs) - 1),
              maxdd=bo.max_dd(eq.values), sharpe=bo.sharpe(mr.values, 12), months=len(mr),
              worst_month=float(mr.min()) if len(mr) else np.nan, yrs=yrs)
    return eq, st



def putspread_trades(close, F, vrp=VRP_BASE, short_sd=1.0, width_sd=1.0, stride=5,
                     gate="none", sym=BENCH, start=OOS_START, end=None):
    """35-DTE index put credit spread, closed after 21 trading days (14 DTE left).

    gate: "none" | "regime" (SPY>200d) | "contango" (VIX9D<VIX) | "both"
    This is the swing analogue of the 0DTE premium sleeve: harvest the variance risk premium,
    stand down when the vol term structure says the premium is about to be earned against you.
    """
    idx = close.index
    rv = close.pct_change().rolling(60).std() * bo.SQRT252
    reg = F["regime"]; ts = F["ts"]
    dts = idx[idx >= start]
    if end:
        dts = dts[dts <= end]
    T0, T1 = DTE_ENTRY / 252.0, DTE_EXIT / 252.0
    out = []
    for dt in dts[::stride]:
        i = idx.get_loc(dt)
        if i + 1 + REB >= len(idx):
            continue
        ok_reg = bool(reg.get(dt, False))
        ok_con = float(ts.get(dt, np.nan)) < 1.0
        if gate == "regime" and not ok_reg:
            continue
        if gate == "contango" and not ok_con:
            continue
        if gate == "both" and not (ok_reg and ok_con):
            continue
        S0, S1 = close[sym].iloc[i + 1], close[sym].iloc[i + 1 + REB]
        sg = rv[sym].iloc[i]
        if not (np.isfinite(S0) and np.isfinite(S1) and np.isfinite(sg)) or sg <= 0:
            continue
        iv = vrp * sg
        sm = S0 * iv * np.sqrt(T0)
        Ks = bo.round_strike(S0 - short_sd * sm, 1.0)
        Kl = bo.round_strike(Ks - width_sd * sm, 1.0)
        if Kl >= Ks:
            continue
        cr = (COSTS.sell(bo.price_leg(S0, Ks, T0, iv, sm, False, SKEW))
              - COSTS.buy(bo.price_leg(S0, Kl, T0, iv, sm, False, SKEW)))
        width = Ks - Kl
        risk = width - cr
        if cr <= 0 or risk <= 0:
            continue
        ex = (COSTS.buy(bo.price_leg(S1, Ks, T1, iv, sm, False, SKEW))
              - COSTS.sell(bo.price_leg(S1, Kl, T1, iv, sm, False, SKEW)))
        ex = min(max(ex, 0.0), width)      # bounded by the spread's own payoff limits
        out.append(dict(date=idx[i + 1], name=sym, ret=(cr - ex) / risk, risk=risk,
                        und=S1 / S0 - 1, year=idx[i + 1].year, credit_pct=cr / width))
    return pd.DataFrame(out)


def section_putwrite(close, F):
    print("\n" + "=" * 100)
    print("SECTION: THE SWING VRP SLEEVE — staggered 35-DTE index put credit spreads")
    print("=" * 100)
    print("Long premium lost to plain SPY ownership.  The one swing structure with a structural")
    print("expectancy is the SHORT side of the variance risk premium.  Test it the same way.\n")

    print("-- gate comparison, weekly entries on SPY, OOS 2010+, vrp sweep --")
    print(f"{'gate':<12}{'vrp':>6}{'n':>6}{'avg%':>8}{'win%':>7}{'t':>7}{'worst%':>8}"
          f"{'CAGR@f=8%':>11}{'maxDD':>8}{'Sharpe':>8}")
    for gate in ("none", "regime", "contango", "both"):
        for vrp in (1.00, VRP_BASE, 1.20):
            T = putspread_trades(close, F, vrp=vrp, gate=gate)
            if len(T) < 50:
                continue
            eq, st = simulate_tranches(T, close, f=0.08, max_exposure=0.32)
            t, _ = stats.ttest_1samp(T.ret, 0)
            print(f"{gate:<12}{vrp:>6.2f}{len(T):>6}{T.ret.mean()*100:>+8.2f}"
                  f"{(T.ret>0).mean()*100:>7.0f}{t:>+7.2f}{T.ret.min()*100:>8.0f}"
                  f"{st['cagr']*100:>10.1f}%{st['maxdd']*100:>7.0f}%{st['sharpe']:>8.2f}")

    print("\n-- SPY buy-and-hold benchmark over the same window --")
    spy = close[BENCH].loc[OOS_START:].dropna()
    spym = spy.resample("ME").last().pct_change().dropna()
    yrs = (spy.index.max() - spy.index.min()).days / 365.25
    print(f"   CAGR {((spy.iloc[-1]/spy.iloc[0])**(1/yrs)-1)*100:.1f}%  "
          f"maxDD {bo.max_dd(spy.values)*100:.0f}%  Sharpe(ann) {bo.sharpe(spym.values,12):.2f}")

    print("\n-- STRIKE / WIDTH sensitivity (vrp=1.10, gate=contango) --")
    print(f"{'short_sd':>9}{'width_sd':>10}{'n':>6}{'avg%':>8}{'win%':>7}{'CAGR':>8}{'maxDD':>8}{'Sharpe':>8}")
    for ssd in (0.75, 1.0, 1.25, 1.5):
        for wsd in (0.5, 1.0):
            T = putspread_trades(close, F, short_sd=ssd, width_sd=wsd, gate="contango")
            if len(T) < 50:
                continue
            eq, st = simulate_tranches(T, close, f=0.08, max_exposure=0.32)
            print(f"{ssd:>9.2f}{wsd:>10.2f}{len(T):>6}{T.ret.mean()*100:>+8.2f}"
                  f"{(T.ret>0).mean()*100:>7.0f}{st['cagr']*100:>7.1f}%{st['maxdd']*100:>7.0f}%"
                  f"{st['sharpe']:>8.2f}")

    print("\n-- SUB-PERIOD STABILITY (vrp=1.10, gate=contango, 1.0SD/1.0SD) --")
    T = putspread_trades(close, F, gate="contango")
    for lo, hi in [("2010", "2013"), ("2014", "2017"), ("2018", "2021"), ("2022", "2026")]:
        s2 = T[(T.date >= f"{lo}-01-01") & (T.date <= f"{hi}-12-31")].ret
        if len(s2) < 20:
            continue
        t, _ = stats.ttest_1samp(s2, 0)
        print(f"   {lo}-{hi}: n={len(s2):>4}  avg {s2.mean()*100:+6.2f}%  win {(s2>0).mean()*100:3.0f}%"
              f"  t {t:+5.2f}  worst {s2.min()*100:+5.0f}%")

    print("\n-- SIZING vs the benchmark (vrp=1.10, gate=contango) --")
    print(f"{'f/entry':>8}{'max exp':>9}{'CAGR':>8}{'maxDD':>8}{'Sharpe':>8}{'worst mo':>10}{'x':>8}")
    for f, mx in ((0.05, 0.20), (0.08, 0.32), (0.12, 0.48), (0.20, 0.80), (0.30, 1.00)):
        eq, st = simulate_tranches(T, close, f=f, max_exposure=mx)
        if not st:
            continue
        print(f"{f*100:>7.0f}%{mx*100:>8.0f}%{st['cagr']*100:>7.1f}%{st['maxdd']*100:>7.0f}%"
              f"{st['sharpe']:>8.2f}{st['worst_month']*100:>9.0f}%{st['final']:>7.1f}x")

    print("\n-- YEAR BY YEAR (vrp=1.10, gate=contango, f=8%, max 32% at risk) --")
    eq, st = simulate_tranches(T, close, f=0.08, max_exposure=0.32)
    ann = eq.resample("YE").last(); prev = 1.0
    for dt, v in ann.items():
        print(f"   {dt.year}  equity {v:6.2f}   {(v/prev-1)*100:+7.1f}%")
        prev = v
    print(f"   CAGR {st['cagr']*100:.1f}%  maxDD {st['maxdd']*100:.0f}%  Sharpe {st['sharpe']:.2f}  "
          f"worst month {st['worst_month']*100:.0f}%")
    bo.summarize(T.ret, "per-trade (n_trials=24 grid)", n_trials=24)


def section_final(close, F):
    print("\n" + "=" * 100)
    print("SECTION: FINAL SWING RULE SET — honest OOS")
    print("=" * 100)
    print("Sector relative strength is REJECTED (see the two sections above: picks underperform")
    print("random picks, permutation p=0.87).  What survived is the INDEX overlay: the equity risk")
    print("premium, leveraged by a defined-risk 35-DTE call debit spread.  Test it properly.\n")

    base = dict(structure="debit", regime=True, short_sd=1.0)
    print("-- headline, monthly entries on SPY+QQQ, OOS 2010+ --")
    for structure in ("long", "debit"):
        for vrp in VRP_GRID:
            T = index_trades(close, F, dict(base, structure=structure), vrp)
            p = portfolio_returns(T)
            r = bo.summarize(T.ret, "", verbose=False)
            print(f"   {structure:<6} vrp={vrp:.2f}  n={r['n']:>4} avg {r['avg']*100:+7.1f}% "
                  f"win {r['win']*100:3.0f}% t {r['t']:+5.2f} PF {r['pf']:4.2f} "
                  f"| portfolio Sharpe(ann) {bo.sharpe(p.values, 12):+5.2f} DSR {r['dsr']:.2f}")

    print("\n-- IS IT ALPHA OR JUST LEVERAGED BETA?  compare to holding the underlying --")
    T = index_trades(close, F, base, VRP_BASE)
    p = portfolio_returns(T)
    und = T.groupby("date").und.mean()
    print(f"   option overlay : avg {p.mean()*100:+6.2f}% / 21d   sd {p.std()*100:5.2f}%   "
          f"Sharpe(ann) {bo.sharpe(p.values,12):+5.2f}")
    print(f"   underlying     : avg {und.mean()*100:+6.2f}% / 21d   sd {und.std()*100:5.2f}%   "
          f"Sharpe(ann) {bo.sharpe(und.values,12):+5.2f}")
    print("   -> if the overlay's Sharpe is LOWER, the option adds LEVERAGE, not edge. Say so plainly.")

    print("\n-- entry frequency: monthly vs staggered weekly (matters for compounding) --")
    for stride, lab in ((REB, "monthly"), (10, "biweekly"), (5, "weekly staggered")):
        T2 = index_trades(close, F, base, VRP_BASE, stride=stride)
        p2 = portfolio_returns(T2)
        print(f"   {lab:<18} n={len(T2):>4}  avg {T2.ret.mean()*100:+6.1f}%  "
              f"periods {len(p2):>4}  Sharpe(ann) {bo.sharpe(p2.values, 252/stride):+5.2f}")

    print("\n-- ANCHORED WALK-FORWARD on the index rule (12-config grid, never tuned on the test yr) --")
    for vrp in (1.00, VRP_BASE, 1.20):
        allt, picks = [], []
        for y in range(2010, int(close.index.max().year) + 1):
            best, bsc = None, -9e9
            for cfg in IDX_GRID:
                Ttr = index_trades(close, F, cfg, vrp, start="1999-01-01", end=f"{y-1}-12-31", stride=5)
                pt = portfolio_returns(Ttr)
                if len(pt) < 40:
                    continue
                sc = pt.mean() / (pt.std() + 1e-9)
                if sc > bsc:
                    bsc, best = sc, cfg
            if best is None:
                continue
            Tte = index_trades(close, F, best, vrp, start=f"{y}-01-01", end=f"{y}-12-31", stride=5)
            if len(Tte):
                allt.append(Tte)
            picks.append((y, best["structure"], best["short_sd"], best["regime"]))
        A = pd.concat(allt)
        pa = portfolio_returns(A)
        bo.summarize(A.ret, f"WALK-FWD index swing vrp={vrp:.2f}", n_trials=len(IDX_GRID), risk_frac=0.15)
        print(f"      portfolio: {len(pa)} weekly cohorts  Sharpe(ann) {bo.sharpe(pa.values,52):+5.2f}")
        if vrp == VRP_BASE:
            print("      picks:", ", ".join(f"{y}:{st[:3]}{sd}{'R' if rg else '-'}" for y, st, sd, rg in picks))

    print("\n-- SUB-PERIOD STABILITY (vrp=1.10, debit, weekly staggered) --")
    T = index_trades(close, F, base, VRP_BASE, stride=5)
    for lo, hi in [("2010", "2013"), ("2014", "2017"), ("2018", "2021"), ("2022", "2026")]:
        s = T[(T.date >= f"{lo}-01-01") & (T.date <= f"{hi}-12-31")].ret
        if len(s) < 20:
            continue
        t, _ = stats.ttest_1samp(s, 0)
        print(f"   {lo}-{hi}: n={len(s):>4}  avg {s.mean()*100:+7.1f}%  win {(s>0).mean()*100:3.0f}%  t {t:+5.2f}")

    print("\n-- PARAMETER SENSITIVITY (vrp=1.10, weekly staggered) --")
    print(f"{'short_sd':>10}{'debit avg%':>13}{'long avg%':>12}{'debit t':>10}")
    for sd in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        Td = index_trades(close, F, dict(base, short_sd=sd), VRP_BASE, stride=5)
        Tl = index_trades(close, F, dict(base, structure="long", short_sd=sd), VRP_BASE, stride=5)
        t, _ = stats.ttest_1samp(Td.ret, 0)
        print(f"{sd:>10.2f}{Td.ret.mean()*100:>+12.1f}%{Tl.ret.mean()*100:>+11.1f}%{t:>+10.2f}")
    print(f"{'regime':>10}", end="")
    for rg in (True, False):
        Td = index_trades(close, F, dict(base, regime=rg), VRP_BASE, stride=5)
        print(f"   SPY>200d={rg}: {Td.ret.mean()*100:+6.1f}% (n={len(Td)})", end="")
    print()

    print("\n-- OVERLAP-CORRECTED SHARPE (weekly entries overlap 4-deep; naive sqrt(52) is WRONG) --")
    for lab, stride in (("monthly (non-overlapping)", REB), ("weekly staggered", 5)):
        Tx = index_trades(close, F, base, VRP_BASE, stride=stride)
        eq, st = simulate_tranches(Tx, close, f=0.05, max_exposure=0.25)
        print(f"   {lab:<26} monthly-aggregated Sharpe(ann) {st['sharpe']:+5.2f}   "
              f"CAGR {st['cagr']*100:5.1f}%   maxDD {st['maxdd']*100:4.0f}%")
    print("   (staggering entries diversifies TIMING; it does not multiply the edge)")

    print("\n-- REALISTIC SIZING: f = risk per entry, capped by total simultaneous exposure --")
    T = index_trades(close, F, base, VRP_BASE, stride=5)
    print(f"{'f/entry':>8}{'max exp':>9}{'CAGR':>9}{'maxDD':>8}{'Sharpe':>8}{'worst mo':>10}{'x over 16y':>12}")
    for f, mx in ((0.03, 0.12), (0.05, 0.20), (0.05, 0.25), (0.08, 0.32), (0.12, 0.50), (0.20, 0.80)):
        eq, st = simulate_tranches(T, close, f=f, max_exposure=mx)
        if not st:
            continue
        print(f"{f*100:>7.0f}%{mx*100:>8.0f}%{st['cagr']*100:>8.1f}%{st['maxdd']*100:>7.0f}%"
              f"{st['sharpe']:>8.2f}{st['worst_month']*100:>9.0f}%{st['final']:>11.1f}x")
    print("   -> compare against SPY buy-and-hold over the same window, printed next.")
    spy = close[BENCH].loc[T.date.min():].dropna()
    spy_m = spy.resample("ME").last().pct_change().dropna()
    yrs = (spy.index.max() - spy.index.min()).days / 365.25
    print(f"   SPY buy&hold: CAGR {((spy.iloc[-1]/spy.iloc[0])**(1/yrs)-1)*100:.1f}%  "
          f"maxDD {bo.max_dd(spy.values)*100:.0f}%  Sharpe {bo.sharpe(spy_m.values,12):.2f}")

    print("\n-- YEAR BY YEAR (vrp=1.10, weekly entries, f=5%, max 25% at risk) --")
    eq, st = simulate_tranches(T, close, f=0.05, max_exposure=0.25)
    ann = eq.resample("YE").last()
    prev = 1.0
    print(f"{'year':>6}{'equity':>10}{'year %':>10}")
    for dt, v in ann.items():
        print(f"{dt.year:>6}{v:>10.2f}{(v/prev-1)*100:>+9.1f}%")
        prev = v
    print(f"  CAGR {st['cagr']*100:.1f}%   maxDD {st['maxdd']*100:.0f}%   "
          f"monthly Sharpe(ann) {st['sharpe']:.2f}   worst month {st['worst_month']*100:.0f}%")

    print("\n-- $5,000 -> $100,000 by 2026-11-19, honest arithmetic (swing sleeve) --")
    import datetime as _dt
    days_left = (_dt.date(2026, 11, 19) - _dt.date(2026, 8, 5)).days
    weeks = days_left / 7.0
    need_wk = 20.0 ** (1 / weeks) - 1
    per_entry = T.ret.mean()
    print(f"   {weeks:.1f} weeks left; need {need_wk*100:.1f}%/week compounded, every week, no losses big"
          f" enough to break the chain.")
    print(f"   Rule gives {per_entry*100:+.2f}% per entry on the RISKED amount "
          f"(sd {T.ret.std()*100:.0f}%, worst {T.ret.min()*100:.0f}%, win {(T.ret>0).mean()*100:.0f}%).")
    f_req = need_wk / max(per_entry, 1e-9)
    print(f"   -> requires risking {f_req*100:.0f}% of the account per weekly entry, i.e. "
          f"{f_req*4*100:.0f}% simultaneously at risk. That is >100%: IMPOSSIBLE, not merely risky.")
    print(f"{'f/entry':>9}{'CAGR':>9}{'15.1wk result':>16}{'maxDD hist':>12}")
    for f, mx in ((0.05, 0.25), (0.10, 0.40), (0.15, 0.60), (0.25, 1.00)):
        eq2, st2 = simulate_tranches(T, close, f=f, max_exposure=mx)
        if not st2:
            continue
        wk = (1 + st2["cagr"]) ** (1 / 52) - 1
        print(f"{f*100:>8.0f}%{st2['cagr']*100:>8.1f}%{5000*(1+wk)**weeks:>15,.0f}{st2['maxdd']*100:>11.0f}%")


# ============================================================================
def main():
    secs = [s for s in sys.argv[1:] if not s.startswith("--")] or \
        ["underlying", "alternatives", "options", "walkforward", "putwrite", "final"]
    close = build_panel(force="--refresh" in sys.argv)
    F = build_features(close)
    print(f"universe {len(UNIVERSE)} ETFs + {BENCH}; {close.index.min().date()} -> {close.index.max().date()}")
    for s in secs:
        {"underlying": section_underlying, "alternatives": section_alternatives, "options": section_options,
         "walkforward": section_walkforward, "putwrite": section_putwrite,
         "final": section_final}[s](close, F)


if __name__ == "__main__":
    main()
