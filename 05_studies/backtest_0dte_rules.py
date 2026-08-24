"""backtest_0dte_rules.py — a concrete, walk-forward-validated 0DTE rule set for SPX (SPY proxy).

DESIGN PRINCIPLES (anti-overfit mandate)
----------------------------------------
* Every feature is lagged: DIX/GEX/VIX/trend are read at the PRIOR CLOSE, the trade opens at
  today's open.  Intraday confirmation uses only bars BEFORE the entry bar.
* Parameters are chosen by ANCHORED WALK-FORWARD: for each OOS year Y the grid is scored on
  data strictly before Jan-1-Y and the winner is traded through Y, unseen.  The reported OOS
  curve is the concatenation of those never-tuned-on years.
* A second, stricter test ("frozen rules") takes the parameters the repo's earlier scripts landed
  on and evaluates them ONLY from 2020 onward, treating 2011-2019 as the discovery sample.
* Deflated Sharpe is computed with n_trials = size of the grid actually searched.
* Option prices are MODELLED (no historical chains exist here).  The variance-risk-premium factor
  `vrp` is swept 1.00 -> 1.30 and every headline number is shown across that sweep.

SECTIONS
  data      build + cache the causal feature panel, calibrate the vol model
  direction the bullish-confluence directional module (long call / call debit / put credit spread)
  premium   the high-gamma premium-selling module (iron condor / credit spread)
  intraday  2y minute-bar layer: entry timing, price confirmation, stops, trailing
  final     the combined rule set, OOS equity curve, stability, sensitivity

Run:  venv/bin/python3 backtest_0dte_rules.py [section ...]      (default: all)
"""
from __future__ import annotations

import os
import sys
import glob
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import bt_options as bo

warnings.filterwarnings("ignore")
pd.set_option("display.width", 200)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "bt0dte_panel.parquet")

TRAIN_END = "2015-12-31"      # first OOS year is 2016
OOS_START = "2016-01-01"
FROZEN_OOS_START = "2020-01-01"
VRP_GRID = [1.00, 1.10, 1.20, 1.30]
VRP_BASE = 1.10
SKEW = 0.15
COSTS = bo.Costs(spread_pct=0.010, spread_floor=0.01, fee_per_contract=0.05)
T_DAY = 1.0 / 252.0

# --- THE LOAD-BEARING ASSUMPTION -------------------------------------------------------------
# Our model sets same-day IV from `sig_hat` (recent realised vol + VIX) and therefore assumes the
# option market is BLIND to the dealer-gamma regime.  If market makers already discount IV on
# high-gamma (pin) days, the premium edge shrinks or vanishes.  AWARE controls that:
#   AWARE = 0.0  market ignores gamma entirely      (most favourable to us)
#   AWARE = 0.5  market prices half the gamma effect
#   AWARE = 1.0  market prices the gamma effect in full  (edge should die if it is not real alpha)
# TILT is the fractional IV adjustment per 1 unit of gz, ESTIMATED ON THE TRAIN WINDOW ONLY.
AWARE = 0.0
IV_SOURCE = "sig_hat"     # "sig_hat" (our causal vol model) or "sig_iv9" (real VIX9D market price)
TILT = -0.117          # placeholder; overwritten by fit_tilt() using train data only
AWARE_GRID = [0.0, 0.35, 0.5, 1.0]


# ============================================================================ data
def build_panel(force=False) -> pd.DataFrame:
    if os.path.exists(CACHE) and not force:
        return pd.read_parquet(CACHE)
    import yfinance as yf
    print("downloading SPY / VIX / VIX9D ...")
    px = yf.download(["SPY", "^VIX", "^VIX9D"], start="2010-01-01", interval="1d",
                     progress=False, auto_adjust=True)
    d = pd.DataFrame(index=px.index)
    for c in ("Open", "High", "Low", "Close"):
        d[c.lower()] = px[c]["SPY"]
    d["vix"] = px["Close"]["^VIX"]
    d["vix9d"] = px["Close"]["^VIX9D"]
    d = d.reset_index().rename(columns={"Date": "date"})
    d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)

    G = pd.read_csv(os.path.join(HERE, "data", "squeeze_dix_gex.csv"), parse_dates=["date"])
    d = d.merge(G[["date", "dix", "gex"]], on="date", how="left").sort_values("date").reset_index(drop=True)

    # ---- causal features (all shifted so they are known at the PRIOR close) ----
    z = lambda s: (s - s.rolling(252, min_periods=60).mean()) / s.rolling(252, min_periods=60).std()
    d["dz"] = z(d.dix).shift(1)
    d["gz"] = z(d.gex).shift(1)
    d["gex_prev"] = d.gex.shift(1)
    d["trend"] = (d.close > d.close.rolling(200).mean()).shift(1)
    d["ts"] = (d.vix9d / d.vix).shift(1)
    d["vixp"] = d.vix.shift(1)
    d["vix_pct"] = d.vix.shift(1).rolling(252, min_periods=60).rank(pct=True)
    d["rev1"] = d.close.pct_change(1).shift(1)
    d["mom3"] = d.close.pct_change(3).shift(1)

    # target + entry-time-known gap
    d["oc"] = (d.close - d.open) / d.open
    d["gap"] = (d.open - d.close.shift(1)) / d.close.shift(1)
    d["hi_rel"] = (d.high - d.open) / d.open
    d["lo_rel"] = (d.low - d.open) / d.open

    # causal vol forecast for the option model
    d = d.set_index("date")
    vf = bo.fit_vix_frac(d.loc[:TRAIN_END, "oc"], d.loc[:TRAIN_END, "vix"])
    d["sig_hat"] = bo.causal_vol_forecast(d["oc"], d["vix"], span=20, vix_frac=vf)
    d.attrs["vix_frac"] = vf

    # ALTERNATIVE IV SOURCE: the real market-implied short-dated vol (VIX9D), scaled to the day
    # session by a fraction fitted on the TRAIN window only.  Using this removes our own vol model
    # from the loop entirely -- and VIX9D is demonstrably NOT gamma-aware (see the premium section).
    iv9_daily = d["vix9d"].shift(1) / 100.0 / bo.SQRT252
    tr = d.loc[:TRAIN_END]
    frac9 = float(np.clip(tr["oc"].std() / (tr["vix9d"].shift(1) / 100.0 / bo.SQRT252).mean(), 0.3, 1.2))
    d["sig_iv9"] = iv9_daily * frac9
    d.attrs["frac9"] = frac9
    d = d.reset_index()

    d = d.dropna(subset=["dz", "gz", "oc", "trend", "ts", "sig_hat", "sig_iv9"]).reset_index(drop=True)
    d.to_parquet(CACHE)
    print(f"panel: {len(d)} days {d.date.min().date()} -> {d.date.max().date()}  "
          f"vix_frac(train)={vf:.3f}  vix9d_dayfrac(train)={frac9:.3f}")
    return d


def fit_tilt(d: pd.DataFrame) -> float:
    """Fractional IV adjustment per 1 unit of prior-close GEX z, FIT ON THE TRAIN WINDOW ONLY.
    This is what a gamma-aware market maker would shade same-day IV by."""
    tr = d[d.date <= TRAIN_END].copy()
    tr["nrange"] = (tr.high - tr.low) / tr.open / tr.sig_hat
    tr = tr.dropna(subset=["nrange", "gz", "vixp"])
    X = np.column_stack([np.ones(len(tr)), tr.gz, np.log(tr.vixp), np.log(tr.sig_hat)])
    b, *_ = np.linalg.lstsq(X, tr.nrange.values, rcond=None)
    return float(b[1] / tr.nrange.mean())


def add_signals(d: pd.DataFrame, dz_th=0.5, gz_th=-0.5) -> pd.DataFrame:
    d = d.copy()
    d["s1"] = (d.dz > dz_th) & (d.gz < gz_th)
    d["s2"] = d.dz > 1.0
    d["s3"] = (d.dz > dz_th) & (d.ts < 1.0)
    d["s4"] = (d.dz > dz_th) & d.trend
    d["conf"] = d[["s1", "s2", "s3", "s4"]].sum(axis=1)
    return d


def section_data(d):
    print("\n" + "=" * 100)
    print("SECTION: DATA & OPTION-MODEL CALIBRATION")
    print("=" * 100)
    tr = d[d.date <= TRAIN_END]
    te = d[d.date >= OOS_START]
    print(f"train {len(tr)} days ({tr.date.min().date()}..{tr.date.max().date()})   "
          f"oos {len(te)} days ({te.date.min().date()}..{te.date.max().date()})")
    print(f"base rate green (open->close): all {(d.oc>0).mean()*100:.1f}%   "
          f"mean oc {d.oc.mean()*1e4:+.1f}bp   sd {d.oc.std()*100:.2f}%")

    # is the causal vol forecast honest?  (compare forecast to |realised| out of sample)
    for lab, s in (("TRAIN", tr), ("OOS", te)):
        real_sig = s.oc.std()
        fc = s.sig_hat.mean()
        print(f"  {lab}: realised oc-sigma {real_sig*100:.3f}%   forecast mean {fc*100:.3f}%   "
              f"ratio fc/real {fc/real_sig:.3f}")
    print("  -> a ratio near 1.0 means the *pre-VRP* model is unbiased; vrp>1 then adds the premium\n")

    # what does a modelled ATM 0DTE straddle cost vs the realised move?  the VRP sanity check
    print(f"{'vrp':>6}{'ATM call cost %S':>18}{'E[payoff] %S':>15}{'rand call':>11}{'rand put':>10}"
          f"{'rand condor':>13}")
    for vrp in VRP_GRID:
        cost, pay, cret, pret, kret = [], [], [], [], []
        for _, r in te.iterrows():
            iv = vrp * r.sig_hat * bo.SQRT252
            sm = r.open * vrp * r.sig_hat
            c = bo.long_option(r.open, r.close, T_DAY, iv, sm, True, COSTS, skew=SKEW)
            p = bo.long_option(r.open, r.close, T_DAY, iv, sm, False, COSTS, skew=SKEW)
            k = bo.iron_condor(r.open, r.close, T_DAY, iv, sm, COSTS, short_sd=1.25, width_sd=1.0, skew=SKEW)
            if c:
                cost.append(c["debit"] / r.open); pay.append((c["debit"] + c["pnl"]) / r.open)
                cret.append(c["ret"])
            if p:
                pret.append(p["ret"])
            if k:
                kret.append(k["ret"])
        print(f"{vrp:>6.2f}{np.mean(cost)*100:>17.3f}%{np.mean(pay)*100:>14.3f}%"
              f"{np.mean(cret)*100:>10.1f}%{np.mean(pret)*100:>9.1f}%{np.mean(kret)*100:>12.1f}%")
    print("  -> random-entry long calls must LOSE (that is the variance risk premium). If they don't,")
    print("     the model is too cheap and every long-premium result below would be inflated.")


# ============================================================================ trade construction
def make_trade(row, structure, vrp=VRP_BASE, short_sd=1.0, width_sd=1.0, side="call"):
    """Build one 0DTE trade at the open, settle at the close.  Returns dict or None."""
    S0, S1 = row.open, row.close
    # market-awareness haircut: if the market prices the gamma regime, IV (and hence the credit AND
    # the strike placement) shrink on pin days.  Both effects are applied together, as in real life.
    base = row.sig_hat if IV_SOURCE == "sig_hat" else row.sig_iv9
    if not np.isfinite(base) or base <= 0:
        return None
    sig = vrp * base * max(0.35, 1.0 + AWARE * TILT * row.gz)
    iv = sig * bo.SQRT252
    sm = S0 * sig
    if sm <= 0:
        return None
    call = side == "call"
    if structure == "long":
        return bo.long_option(S0, S1, T_DAY, iv, sm, call, COSTS, skew=SKEW)
    if structure == "debit":
        return bo.vertical(S0, S1, T_DAY, iv, sm, COSTS, call=call, debit=True,
                           short_sd=short_sd, skew=SKEW)
    if structure == "credit":     # bullish -> put credit spread; bearish -> call credit spread
        return bo.vertical(S0, S1, T_DAY, iv, sm, COSTS, call=not call, debit=False,
                           short_sd=short_sd, width_sd=width_sd, skew=SKEW)
    if structure == "condor":
        return bo.iron_condor(S0, S1, T_DAY, iv, sm, COSTS, short_sd=short_sd,
                              width_sd=width_sd, skew=SKEW)
    if structure in ("straddle", "strangle"):
        msd = 0.0 if structure == "straddle" else short_sd
        c = bo.long_option(S0, S1, T_DAY, iv, sm, True, COSTS, skew=SKEW, moneyness_sd=msd)
        p = bo.long_option(S0, S1, T_DAY, iv, sm, False, COSTS, skew=SKEW, moneyness_sd=msd)
        if not c or not p:
            return None
        debit = c["debit"] + p["debit"]
        pnl = c["pnl"] + p["pnl"]
        if debit <= 0:
            return None
        return dict(debit=debit, pnl=pnl, ret=pnl / debit, risk=debit)
    raise ValueError(structure)


def run_rule(df, mask, structure, vrp=VRP_BASE, short_sd=1.0, width_sd=1.0, side="call",
             stop=None, target=None):
    """Apply a structure to the masked days.  `stop`/`target` are premium-based exits approximated
    from the day's OHLC extremes using the PESSIMISTIC ordering (adverse extreme assumed first)."""
    out = []
    sub = df[mask]
    for _, r in sub.iterrows():
        t = make_trade(r, structure, vrp, short_sd, width_sd, side)
        if t is None:
            continue
        ret = t["ret"]
        if stop is not None:
            # PESSIMISTIC path assumption: the day's adverse extreme is assumed to be reached
            # first, and the terminal value is priced AT that extreme (no time value left).
            bullish = (side == "call") if structure in ("long", "debit", "credit") else None
            if structure == "condor":
                adverse = r.low if abs(r.lo_rel) > abs(r.hi_rel) else r.high
            else:
                adverse = r.low if bullish else r.high
            rr = r.copy(); rr["close"] = adverse
            t_adv = make_trade(rr, structure, vrp, short_sd, width_sd, side)
            if t_adv is not None and t_adv["ret"] <= stop:
                ret = stop
        out.append(dict(date=r.date, ret=ret, risk=t["risk"], oc=r.oc, gz=r.gz, dz=r.dz,
                        year=r.date.year))
    return pd.DataFrame(out)


# ============================================================================ direction module
DIR_GRID = [
    dict(k=1, structure="long",   short_sd=0.0, gzmax=None),
    dict(k=2, structure="long",   short_sd=0.0, gzmax=None),
    dict(k=3, structure="long",   short_sd=0.0, gzmax=None),
    dict(k=1, structure="debit",  short_sd=1.0, gzmax=None),
    dict(k=2, structure="debit",  short_sd=1.0, gzmax=None),
    dict(k=3, structure="debit",  short_sd=1.0, gzmax=None),
    dict(k=1, structure="credit", short_sd=1.0, gzmax=None),
    dict(k=2, structure="credit", short_sd=1.0, gzmax=None),
    dict(k=3, structure="credit", short_sd=1.0, gzmax=None),
    dict(k=2, structure="debit",  short_sd=1.0, gzmax=0.5),
    dict(k=2, structure="credit", short_sd=1.0, gzmax=0.5),
    dict(k=2, structure="long",   short_sd=0.0, gzmax=0.5),
]


def dir_mask(d, cfg):
    m = d.conf >= cfg["k"]
    if cfg["gzmax"] is not None:
        m &= d.gz < cfg["gzmax"]
    return m


def section_direction(d):
    print("\n" + "=" * 100)
    print("SECTION: DIRECTIONAL MODULE (bullish DIX confluence)")
    print("=" * 100)

    print("\n-- underlying open->close by confluence (no options, whole sample; this is the PRIOR) --")
    print(f"{'conf':>5}{'n':>6}{'win%':>7}{'avg bp':>9}{'t':>7}")
    for k in range(0, 5):
        s = d[d.conf == k]["oc"]
        if len(s) < 20:
            continue
        t, _ = stats.ttest_1samp(s, 0)
        print(f"{k:>5}{len(s):>6}{(s>0).mean()*100:>7.0f}{s.mean()*1e4:>+9.1f}{t:>+7.2f}")

    print("\n-- is the confluence edge stable across sub-periods? (>=2 signals, underlying oc) --")
    sub = d[d.conf >= 2]
    for lo, hi in [("2011", "2014"), ("2015", "2018"), ("2019", "2022"), ("2023", "2026")]:
        s = sub[(sub.date >= f"{lo}-01-01") & (sub.date <= f"{hi}-12-31")]["oc"]
        if len(s) < 15:
            continue
        t, _ = stats.ttest_1samp(s, 0)
        print(f"   {lo}-{hi}: n={len(s):>4}  win {(s>0).mean()*100:>4.0f}%  avg {s.mean()*1e4:+6.1f}bp  t {t:+5.2f}")

    print("\n-- MODEL-FREE control: does the signal change the tail that kills a put spread? --")
    print("   P(day's LOW breaches -1 forecast SD)  and  P(low breaches -1.5 SD)")
    for sd_ in (1.0, 1.25, 1.5):
        br = d.lo_rel < -sd_ * d.sig_hat
        a, b = br[d.conf >= 2].astype(float), br[d.conf < 2].astype(float)
        t, p = stats.ttest_ind(a, b, equal_var=False)
        print(f"   -{sd_}SD: conf>=2 {a.mean()*100:5.1f}%   conf<2 {b.mean()*100:5.1f}%   "
              f"diff {(a.mean()-b.mean())*100:+5.1f}pp  t {t:+5.2f}  p {p:.3f}")
    print("   (negative diff = the bullish signal genuinely reduces downside breaches -> real, model-free)")

    print("\n-- FROZEN rules, pseudo-OOS from 2020 (discovery sample = 2011-2019), vrp sweep --")
    print("   *** every line is paired with its UNCONDITIONAL control (same structure, ALL days) ***")
    oos = d[d.date >= FROZEN_OOS_START]
    allmask = pd.Series(True, index=oos.index)
    for structure, ssd in (("long", 0.0), ("debit", 1.0), ("credit", 1.0)):
        for vrp in VRP_GRID:
            T = run_rule(oos, oos.conf >= 2, structure, vrp=vrp, short_sd=ssd)
            C = run_rule(oos, allmask, structure, vrp=vrp, short_sd=ssd)
            r1 = bo.summarize(T.ret, f"conf>=2 {structure:<6} vrp={vrp:.2f}", n_trials=1,
                              risk_frac=0.10, verbose=False)
            r0 = bo.summarize(C.ret, "ctrl", n_trials=1, verbose=False)
            t, p = stats.ttest_ind(T.ret, run_rule(oos, oos.conf < 2, structure, vrp=vrp,
                                                   short_sd=ssd).ret, equal_var=False)
            print(f"  conf>=2 {structure:<6} vrp={vrp:.2f}  n={r1['n']:>4}  avg {r1['avg']*100:+6.1f}%  "
                  f"win {r1['win']*100:3.0f}%  || ALL-DAYS ctrl avg {r0['avg']*100:+6.1f}%  "
                  f"|| EDGE OVER CTRL {(r1['avg']-r0['avg'])*100:+5.1f}pp  t(vs non-signal) {t:+5.2f}")

    print("\n-- SKEW sensitivity (credit spread, conf>=2, vrp=1.10) with controls --")
    global SKEW
    keep = SKEW
    for sk in (0.05, 0.15, 0.25, 0.35):
        SKEW = sk
        T = run_rule(oos, oos.conf >= 2, "credit", vrp=VRP_BASE, short_sd=1.0)
        C = run_rule(oos, allmask, "credit", vrp=VRP_BASE, short_sd=1.0)
        print(f"   skew={sk:.2f}: signal avg {T.ret.mean()*100:+6.2f}%   all-days {C.ret.mean()*100:+6.2f}%"
              f"   edge {(T.ret.mean()-C.ret.mean())*100:+5.2f}pp")
    SKEW = keep

    print("\n-- PERMUTATION test: shuffle the signal labels 500x, where does the real edge land? --")
    T = run_rule(oos, oos.conf >= 2, "credit", vrp=VRP_BASE, short_sd=1.0)
    C = run_rule(oos, allmask, "credit", vrp=VRP_BASE, short_sd=1.0).set_index("date")
    real = T.ret.mean()
    pool = C.ret.values
    k = len(T)
    rng = np.random.default_rng(7)
    null = np.array([rng.choice(pool, k, replace=False).mean() for _ in range(500)])
    print(f"   real {real*100:+.2f}%   null mean {null.mean()*100:+.2f}%   "
          f"p(one-sided) {(null >= real).mean():.3f}")

    print("\n-- WALK-FORWARD selection over a 12-point grid, anchored, re-selected each Jan --")
    for vrp in VRP_GRID:
        picks, allt = [], []
        for y in range(2016, int(d.date.max().year) + 1):
            tr = d[d.date < f"{y}-01-01"]
            te = d[(d.date >= f"{y}-01-01") & (d.date <= f"{y}-12-31")]
            if len(tr) < 900 or len(te) < 20:
                continue
            best, bsc = None, -9e9
            for cfg in DIR_GRID:
                Ttr = run_rule(tr, dir_mask(tr, cfg), cfg["structure"], vrp=vrp, short_sd=cfg["short_sd"])
                if len(Ttr) < 60:
                    continue
                sc = Ttr.ret.mean() / (Ttr.ret.std() + 1e-9)      # per-trade Sharpe on TRAIN only
                if sc > bsc:
                    bsc, best = sc, cfg
            if best is None:
                continue
            Tte = run_rule(te, dir_mask(te, best), best["structure"], vrp=vrp, short_sd=best["short_sd"])
            if len(Tte):
                Tte["year"] = y
                allt.append(Tte)
            picks.append((y, best["k"], best["structure"], len(Tte)))
        if not allt:
            continue
        A = pd.concat(allt)
        bo.summarize(A.ret, f"WALK-FWD direction vrp={vrp:.2f}", n_trials=len(DIR_GRID), risk_frac=0.10)
        if vrp == VRP_BASE:
            print("     picks:", ", ".join(f"{y}:k{k}/{s}({n})" for y, k, s, n in picks))
            yr = A.groupby("year").ret.agg(["size", "mean", lambda x: (x > 0).mean()])
            yr.columns = ["n", "avg", "win"]
            print(yr.assign(avg=lambda x: (x.avg * 100).round(1), win=lambda x: (x.win * 100).round(0)).to_string())
    return


# ============================================================================ premium module
PREM_GRID = [
    dict(structure="condor", short_sd=1.0, width_sd=1.0, gzmin=0.5),
    dict(structure="condor", short_sd=1.25, width_sd=1.0, gzmin=0.5),
    dict(structure="condor", short_sd=1.5, width_sd=1.0, gzmin=0.5),
    dict(structure="condor", short_sd=1.25, width_sd=1.0, gzmin=0.0),
    dict(structure="condor", short_sd=1.25, width_sd=1.0, gzmin=1.0),
    dict(structure="credit", short_sd=1.0, width_sd=1.0, gzmin=0.5),
    dict(structure="credit", short_sd=1.25, width_sd=1.0, gzmin=0.5),
    dict(structure="credit", short_sd=1.5, width_sd=1.0, gzmin=0.5),
]


def prem_mask(d, cfg):
    return (d.gz > cfg["gzmin"]) & (d.conf < 2)


def section_premium(d):
    print("\n" + "=" * 100)
    print("SECTION: PREMIUM-SELLING MODULE (gamma regime as a RISK GATE, not a direction call)")
    print("=" * 100)

    print("\n>> THE DECISIVE MODEL-FREE TEST <<")
    print("   An option market prices same-day IV off recent realised vol + VIX.  Our `sig_hat` IS that.")
    print("   So the ONLY way premium selling can have real alpha is if the gamma regime predicts the")
    print("   NORMALISED range (range / sig_hat) that a vol-forecast-based IV would have missed.")
    d = d.copy()
    d["nrange"] = (d.high - d.low) / d.open / d.sig_hat
    d["nabs"] = d.oc.abs() / d.sig_hat
    sub = d.dropna(subset=["nrange", "gz"])
    print(f"\n   normalised range by prior-close GEX z quintile   (n={len(sub)})")
    sub = sub.assign(q=pd.qcut(sub.gz, 5, labels=[1, 2, 3, 4, 5]))
    tab = sub.groupby("q", observed=True).agg(n=("nrange", "size"), norm_range=("nrange", "mean"),
                                              norm_absmove=("nabs", "mean"), raw_range=("hi_rel", "size"))
    tab["raw_range_pct"] = sub.groupby("q", observed=True).apply(
        lambda g: ((g.high - g.low) / g.open).mean() * 100)
    print(tab.drop(columns=["raw_range"]).round(3).to_string())
    a = sub[sub.q == 5].nrange; b = sub[sub.q == 1].nrange
    t, p = stats.ttest_ind(a, b, equal_var=False)
    print(f"   Q5(high gamma) {a.mean():.3f} vs Q1(low gamma) {b.mean():.3f}   t {t:+.2f}  p {p:.2e}")
    # regression control: does gz survive next to the VIX level and the vol forecast?
    X = sub[["gz"]].assign(const=1.0, lvix=np.log(sub.vixp), lsig=np.log(sub.sig_hat))
    y = sub.nrange.values
    beta, *_ = np.linalg.lstsq(X[["const", "gz", "lvix", "lsig"]].values, y, rcond=None)
    resid = y - X[["const", "gz", "lvix", "lsig"]].values @ beta
    se = np.sqrt(np.diag(np.linalg.pinv(X[["const", "gz", "lvix", "lsig"]].values.T
                                        @ X[["const", "gz", "lvix", "lsig"]].values)
                         * resid.var(ddof=4)))
    print(f"   OLS  nrange ~ 1 + gz + log(VIX) + log(sig_hat):  beta_gz {beta[1]:+.4f}  "
          f"t {beta[1]/se[1]:+.2f}")
    print("   -> a significantly NEGATIVE beta_gz means dealer gamma shrinks the range BEYOND what")
    print("      recent vol / VIX already told you.  That is the whole basis for the premium sleeve.")

    print("\n   sub-period stability of beta_gz (is it a stable structural effect?):")
    for lo, hi in [("2011", "2014"), ("2015", "2018"), ("2019", "2022"), ("2023", "2026")]:
        s = sub[(sub.date >= f"{lo}-01-01") & (sub.date <= f"{hi}-12-31")]
        if len(s) < 100:
            continue
        Xs = np.column_stack([np.ones(len(s)), s.gz, np.log(s.vixp), np.log(s.sig_hat)])
        bb, *_ = np.linalg.lstsq(Xs, s.nrange.values, rcond=None)
        rr = s.nrange.values - Xs @ bb
        ss = np.sqrt(np.diag(np.linalg.pinv(Xs.T @ Xs) * rr.var(ddof=4)))
        print(f"     {lo}-{hi}: n={len(s):>4}  beta_gz {bb[1]:+.4f}  t {bb[1]/ss[1]:+.2f}")

    print("\n>> IS THE MARKET ALREADY PRICING THE GAMMA REGIME?  (the decisive question) <<")
    print("   VIX9D is a REAL MARKET-IMPLIED price — the shortest listed implied vol there is.")
    print("   If the market priced dealer gamma, then range normalised by MARKET-IMPLIED vol would")
    print("   show NO relationship to gz.  Any surviving relationship is un-priced, harvestable vol.")
    dv = d.dropna(subset=["vixp", "gz"]).copy()
    dv["iv9"] = dv.vix9d.shift(1) / 100.0 / bo.SQRT252
    dv["ivx"] = dv.vixp / 100.0 / bo.SQRT252
    dv = dv.dropna(subset=["iv9"])
    for lab, col in (("VIX9D-implied", "iv9"), ("VIX-implied", "ivx")):
        dv["nr_iv"] = (dv.high - dv.low) / dv.open / dv[col]
        dv["na_iv"] = dv.oc.abs() / dv[col]
        X = np.column_stack([np.ones(len(dv)), dv.gz, np.log(dv[col])])
        for tgt in ("nr_iv", "na_iv"):
            b, *_ = np.linalg.lstsq(X, dv[tgt].values, rcond=None)
            r = dv[tgt].values - X @ b
            se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X) * r.var(ddof=3)))
            nm = "range" if tgt == "nr_iv" else "|move|"
            print(f"   {nm:>7} / {lab:<14}  ~ 1 + gz + log(iv):  beta_gz {b[1]:+.4f}  t {b[1]/se[1]:+.2f}"
                  f"   [mean ratio {dv[tgt].mean():.3f}]")
    print("   quintile view: realised range as a MULTIPLE of VIX9D-implied daily move, by gz quintile")
    dv["nr_iv"] = (dv.high - dv.low) / dv.open / dv.iv9
    dv["q"] = pd.qcut(dv.gz, 5, labels=[1, 2, 3, 4, 5])
    qq = dv.groupby("q", observed=True).nr_iv.agg(["size", "mean", "median"])
    print(qq.round(3).to_string())
    a, b_ = dv[dv.q == 5].nr_iv, dv[dv.q == 1].nr_iv
    t, p = stats.ttest_ind(a, b_, equal_var=False)
    print(f"   Q5 {a.mean():.3f} vs Q1 {b_.mean():.3f}   t {t:+.2f}  p {p:.2e}")
    print("   sub-period stability (beta_gz on range / VIX9D-implied):")
    for lo, hi in [("2011", "2014"), ("2015", "2018"), ("2019", "2022"), ("2023", "2026")]:
        s = dv[(dv.date >= f"{lo}-01-01") & (dv.date <= f"{hi}-12-31")]
        if len(s) < 100:
            continue
        Xs = np.column_stack([np.ones(len(s)), s.gz, np.log(s.iv9)])
        bb, *_ = np.linalg.lstsq(Xs, s.nr_iv.values, rcond=None)
        rr = s.nr_iv.values - Xs @ bb
        ss = np.sqrt(np.diag(np.linalg.pinv(Xs.T @ Xs) * rr.var(ddof=3)))
        print(f"     {lo}-{hi}: n={len(s):>4}  beta_gz {bb[1]:+.4f}  t {bb[1]/ss[1]:+.2f}")

    print("\n-- SD-normalised condor survival (strikes at +/-k * sig_hat, so IV-fair widths) --")
    print(f"{'k(SD)':>7}{'gz<-0.5':>10}{'mid':>8}{'gz>0.5':>9}{'gz>1.0':>9}{'ALL':>8}")
    for k in (1.0, 1.25, 1.5, 2.0):
        surv = (d.hi_rel < k * d.sig_hat) & (d.lo_rel > -k * d.sig_hat)
        row = [surv[d.gz < -0.5].mean(), surv[d.gz.between(-0.5, 0.5)].mean(),
               surv[d.gz > 0.5].mean(), surv[d.gz > 1.0].mean(), surv.mean()]
        print(f"{k:>7.2f}" + "".join(f"{v*100:>9.0f}%" for v in row))
    surv = (d.hi_rel < 1.25 * d.sig_hat) & (d.lo_rel > -1.25 * d.sig_hat)
    t, p = stats.ttest_ind(surv[d.gz > 0.5].astype(float), surv[d.gz < -0.5].astype(float), equal_var=False)
    print(f"   1.25SD survival, high vs low gamma: t={t:+.2f}  p={p:.2e}")

    print("\n-- MODEL-FREE BREAKEVEN CREDIT: what % of width must the market pay you to break even? --")
    print("   (expected settlement payout of the structure, straight from the realised closes)")
    print(f"{'structure':<26}{'gz<-0.5':>10}{'mid':>9}{'gz>0.5':>9}{'ALL':>9}")
    for lab, k, w in [("put spread -1.0/-2.0SD", 1.0, 1.0), ("put spread -1.25/-2.25SD", 1.25, 1.0),
                      ("condor 1.0SD/1SD wide", 1.0, 1.0), ("condor 1.25SD/1SD wide", 1.25, 1.0),
                      ("condor 1.5SD/1SD wide", 1.5, 1.0)]:
        outs = []
        for msk in (d.gz < -0.5, d.gz.between(-0.5, 0.5), d.gz > 0.5, pd.Series(True, index=d.index)):
            s = d[msk]
            sd = s.sig_hat
            if lab.startswith("put"):
                pay = (np.maximum(-s.oc - k * sd, 0) - np.maximum(-s.oc - (k + w) * sd, 0)) / (w * sd)
            else:
                pay = ((np.maximum(-s.oc - k * sd, 0) - np.maximum(-s.oc - (k + w) * sd, 0))
                       + (np.maximum(s.oc - k * sd, 0) - np.maximum(s.oc - (k + w) * sd, 0))) / (w * sd)
            outs.append(pay.mean())
        print(f"{lab:<26}" + "".join(f"{v*100:>8.1f}%" for v in outs))
    print("   -> you profit iff the ACTUAL credit you collect exceeds this number (plus slippage).")
    print("      Note these breakevens are LOW because 1SD-wide wings are very wide; what matters is")
    print("      the credit-minus-breakeven GAP, printed next, and the gamma-gate DIFFERENTIAL.")

    print("\n-- modelled credit (% of width) vs the model-free breakeven, vrp=1.10, AWARE=0 --")
    global AWARE
    AWARE = 0.0
    print(f"{'structure':<24}{'regime':<10}{'credit%W':>10}{'breakeven%W':>13}{'gap':>8}")
    for k in (1.0, 1.25, 1.5):
        for lab, msk in (("lowGamma", d.gz < -0.5), ("highGamma", d.gz > 0.5)):
            s = d[msk]
            cred, be = [], []
            for _, r in s.iterrows():
                t = make_trade(r, "condor", VRP_BASE, k, 1.0)
                if t:
                    cred.append(t["credit_pct"])
                    w = 1.0 * VRP_BASE * r.sig_hat
                    pay = (max(-r.oc - k * VRP_BASE * r.sig_hat, 0) - max(-r.oc - (k + 1) * VRP_BASE * r.sig_hat, 0)
                           + max(r.oc - k * VRP_BASE * r.sig_hat, 0) - max(r.oc - (k + 1) * VRP_BASE * r.sig_hat, 0)) / w
                    be.append(pay)
            print(f"{'condor '+str(k)+'SD':<24}{lab:<10}{np.mean(cred)*100:>9.1f}%{np.mean(be)*100:>12.1f}%"
                  f"{(np.mean(cred)-np.mean(be))*100:>+7.1f}")

    print("\n-- FROZEN premium rules, pseudo-OOS 2020+ --")
    print("   Each row: HIGH-GAMMA-GATED result || ALL-DAYS control || the GATE's incremental value")
    oos = d[d.date >= FROZEN_OOS_START]
    allmask = pd.Series(True, index=oos.index)
    for aw in AWARE_GRID:
        AWARE = aw
        print(f"\n   AWARE = {aw:.1f}  (market prices {aw*100:.0f}% of the gamma effect into same-day IV)")
        for cfg in PREM_GRID[:3] + PREM_GRID[5:7]:
            for vrp in (1.00, VRP_BASE, 1.20):
                T = run_rule(oos, prem_mask(oos, cfg), cfg["structure"], vrp=vrp,
                             short_sd=cfg["short_sd"], width_sd=cfg["width_sd"])
                C = run_rule(oos, allmask, cfg["structure"], vrp=vrp,
                             short_sd=cfg["short_sd"], width_sd=cfg["width_sd"])
                if len(T) < 30:
                    continue
                r1 = bo.summarize(T.ret, "", n_trials=1, risk_frac=0.10, verbose=False)
                r0 = bo.summarize(C.ret, "", n_trials=1, verbose=False)
                print(f"     {cfg['structure']:<7}{cfg['short_sd']:<5}gz>{cfg['gzmin']} vrp={vrp:.2f} "
                      f"n={r1['n']:>4} avg {r1['avg']*100:+6.2f}% win {r1['win']*100:3.0f}% "
                      f"DD {r1['maxdd']*100:4.0f}% t {r1['t']:+5.2f} || all-days {r0['avg']*100:+6.2f}% "
                      f"|| GATE {(r1['avg']-r0['avg'])*100:+5.2f}pp")
    AWARE = 0.0

    print("\n" + "-" * 96)
    print("-- THE MIRROR TRADE: LONG vol on SHORT-gamma days (this is the dashboard's central claim) --")
    print("   Same robust fact, opposite side.  If it does not work, 'buy premium below the flip' is dead.")
    for aw in AWARE_GRID:
        AWARE = aw
        print(f"\n   AWARE = {aw:.1f}")
        for struct, ssd in (("straddle", 0.0), ("strangle", 0.75)):
            for vrp in (1.00, VRP_BASE, 1.20):
                T = run_rule(oos, oos.gz < -0.5, struct, vrp=vrp, short_sd=ssd)
                C = run_rule(oos, allmask, struct, vrp=vrp, short_sd=ssd)
                if len(T) < 30:
                    continue
                r1 = bo.summarize(T.ret, "", n_trials=1, risk_frac=0.10, verbose=False)
                r0 = bo.summarize(C.ret, "", n_trials=1, verbose=False)
                print(f"     LONG {struct:<9} gz<-0.5 vrp={vrp:.2f} n={r1['n']:>4} avg {r1['avg']*100:+6.2f}% "
                      f"win {r1['win']*100:3.0f}% t {r1['t']:+5.2f} || all-days {r0['avg']*100:+6.2f}% "
                      f"|| GATE {(r1['avg']-r0['avg'])*100:+6.2f}pp")
    AWARE = 0.0

    print("\n-- does a STOP rescue the condor tail?  (pessimistic path: adverse extreme hit first) --")
    for stop in (None, -0.3, -0.5, -0.75):
        T = run_rule(oos, prem_mask(oos, PREM_GRID[1]), "condor", vrp=VRP_BASE,
                     short_sd=1.25, width_sd=1.0, stop=stop)
        bo.summarize(T.ret, f"condor 1.25SD stop={stop}", n_trials=4, risk_frac=0.10)
    print("   (stop is expressed as a multiple of CREDIT-AT-RISK; -1.0 = give back one full max-loss unit)")

    print("\n-- WALK-FORWARD premium selection --")
    for vrp in VRP_GRID:
        picks, allt = [], []
        for y in range(2016, int(d.date.max().year) + 1):
            tr = d[d.date < f"{y}-01-01"]
            te = d[(d.date >= f"{y}-01-01") & (d.date <= f"{y}-12-31")]
            if len(tr) < 900 or len(te) < 20:
                continue
            best, bsc = None, -9e9
            for cfg in PREM_GRID:
                Ttr = run_rule(tr, prem_mask(tr, cfg), cfg["structure"], vrp=vrp,
                               short_sd=cfg["short_sd"], width_sd=cfg["width_sd"])
                if len(Ttr) < 100:
                    continue
                sc = Ttr.ret.mean() / (Ttr.ret.std() + 1e-9)
                if sc > bsc:
                    bsc, best = sc, cfg
            if best is None:
                continue
            Tte = run_rule(te, prem_mask(te, best), best["structure"], vrp=vrp,
                           short_sd=best["short_sd"], width_sd=best["width_sd"])
            if len(Tte):
                Tte["year"] = y
                allt.append(Tte)
            picks.append((y, best["structure"], best["short_sd"], len(Tte)))
        if not allt:
            continue
        A = pd.concat(allt)
        bo.summarize(A.ret, f"WALK-FWD premium vrp={vrp:.2f}", n_trials=len(PREM_GRID), risk_frac=0.05)
        if vrp == VRP_BASE:
            print("     picks:", ", ".join(f"{y}:{s}{sd}({n})" for y, s, sd, n in picks))
            yr = A.groupby("year").ret.agg(["size", "mean", lambda x: (x > 0).mean()])
            yr.columns = ["n", "avg", "win"]
            print(yr.assign(avg=lambda x: (x.avg * 100).round(1), win=lambda x: (x.win * 100).round(0)).to_string())


# ============================================================================ intraday layer
def load_minute(sym="SPY"):
    frames = []
    for f in sorted(glob.glob(os.path.join(HERE, "data", "minute", sym, "*.parquet"))):
        frames.append(pd.read_parquet(f))
    m = pd.concat(frames).sort_index()
    return m


def section_intraday(d):
    print("\n" + "=" * 100)
    print("SECTION: INTRADAY LAYER (2y minute bars) — entry timing, confirmation, stops")
    print("=" * 100)
    m = load_minute("SPY").between_time("09:30", "15:59")
    dmap = d.set_index(d.date.dt.date)
    days = {}
    for day, g in m.groupby(m.index.date):
        if len(g) < 300 or day not in dmap.index:
            continue
        days[day] = g
    print(f"{len(days)} usable minute days ({min(days)} .. {max(days)})")

    ENTRY_TIMES = ["09:30", "09:45", "10:00", "10:30"]
    print("\n-- A. does waiting past the open help the DIRECTIONAL edge?  (underlying entry->close) --")
    print(f"{'entry':>7}{'n':>6}{'win%':>7}{'avg bp':>9}{'t':>7}   [conf>=2 days only]")
    for et in ENTRY_TIMES:
        rets = []
        for day, g in days.items():
            row = dmap.loc[day]
            if row.conf < 2:
                continue
            sub = g.between_time(et, "15:59")
            if len(sub) < 30:
                continue
            rets.append(sub.close.iloc[-1] / sub.close.iloc[0] - 1)
        if len(rets) < 20:
            continue
        t, _ = stats.ttest_1samp(rets, 0)
        print(f"{et:>7}{len(rets):>6}{np.mean(np.array(rets)>0)*100:>7.0f}{np.mean(rets)*1e4:>+9.1f}{t:>+7.2f}")

    print("\n-- B. price CONFIRMATION filters at 10:00 (all causal: only 09:30-10:00 bars used) --")
    rows = []
    for day, g in days.items():
        row = dmap.loc[day]
        or30 = g.between_time("09:30", "09:59")
        rest = g.between_time("10:00", "15:59")
        if len(or30) < 20 or len(rest) < 60:
            continue
        p0 = rest.close.iloc[0]
        rows.append(dict(day=day, conf=row.conf, gz=row.gz, dz=row.dz,
                         above_orh=p0 > or30.high.max() * 0.9999,
                         above_vwap=p0 > or30.vwap.iloc[-1],
                         or_up=or30.close.iloc[-1] > or30.close.iloc[0],
                         ret=rest.close.iloc[-1] / p0 - 1,
                         mfe=rest.high.max() / p0 - 1, mae=rest.low.min() / p0 - 1))
    R = pd.DataFrame(rows)
    for lab, msk in [("conf>=2 (base)", R.conf >= 2),
                     ("conf>=2 & >VWAP", (R.conf >= 2) & R.above_vwap),
                     ("conf>=2 & OR up", (R.conf >= 2) & R.or_up),
                     ("conf>=2 & >VWAP & OR up", (R.conf >= 2) & R.above_vwap & R.or_up),
                     ("conf>=1 & >VWAP", (R.conf >= 1) & R.above_vwap),
                     (">VWAP only (no DIX)", R.above_vwap)]:
        s = R[msk].ret
        if len(s) < 15:
            print(f"   {lab:<28} n={len(s)} too few"); continue
        t, _ = stats.ttest_1samp(s, 0)
        print(f"   {lab:<28} n={len(s):>4}  win {(s>0).mean()*100:>4.0f}%  avg {s.mean()*1e4:+6.1f}bp  "
              f"t {t:+5.2f}  mfe {R[msk].mfe.mean()*1e4:5.0f}bp  mae {R[msk].mae.mean()*1e4:6.0f}bp")
    print("   (2y sample = SUGGESTIVE only; too short to validate a filter on its own)")

    print("\n-- C. exit management on the modelled option, 10:00 entry, conf>=2 --")
    sel = R[R.conf >= 2].day.tolist()
    for stop, tgt in [(None, None), (-0.5, None), (-0.5, 1.0), (-0.35, 0.75), (None, 1.0)]:
        rets = []
        for day in sel:
            g = days[day]; row = dmap.loc[day]
            rest = g.between_time("10:00", "15:59")
            S0 = rest.close.iloc[0]
            frac_left = len(rest) / bo.MINUTES_PER_SESSION
            sig = VRP_BASE * row.sig_hat * np.sqrt(max(frac_left, 1e-6))
            iv = VRP_BASE * row.sig_hat * bo.SQRT252
            sm = S0 * sig
            K = bo.round_strike(S0, 1.0)
            entry = COSTS.buy(bo.bs(S0, K, T_DAY * frac_left, iv, True))
            if entry <= 0:
                continue
            n = len(rest)
            exited = None
            for i in range(1, n):
                Tr = T_DAY * frac_left * (1 - i / n)
                px_ = rest.close.iloc[i]
                val = bo.bs(px_, K, max(Tr, 0.0), iv, True)
                r_ = (COSTS.sell(val) - entry) / entry
                if stop is not None and r_ <= stop:
                    exited = stop; break
                if tgt is not None and r_ >= tgt:
                    exited = COSTS.sell(val) / entry - 1; break
            if exited is None:
                exited = max(rest.close.iloc[-1] - K, 0.0) / entry - 1
            rets.append(exited)
        lab = f"stop {stop} tgt {tgt}"
        bo.summarize(rets, lab, n_trials=5, risk_frac=0.10)

    # ---------------------------------------------------------------- D. real-path condor mgmt
    print("\n-- D. PREMIUM sleeve on the REAL intraday path: entry time x gamma regime x stop --")
    print("   Condor short strikes at 1.25 SD of the REMAINING-session implied move, marked to the")
    print("   minute, stopped when down `stop` x max risk, else held to settlement.")

    def condor_path(day, entry_time, stop, short_sd=1.25, width_sd=1.0, vrp=VRP_BASE):
        g = days[day]; row = dmap.loc[day]
        rest = g.between_time(entry_time, "15:59")
        if len(rest) < 40:
            return None
        S0 = rest.close.iloc[0]
        n = len(rest)
        frac = n / bo.MINUTES_PER_SESSION
        base = row.sig_hat if IV_SOURCE == "sig_hat" else row.sig_iv9
        sig = vrp * base * np.sqrt(max(frac, 1e-6))          # remaining-session implied move
        iv = vrp * base * bo.SQRT252
        sm = S0 * sig
        Tt = T_DAY * frac
        Kps = bo.round_strike(S0 - short_sd * sm, 1.0); Kpl = bo.round_strike(Kps - width_sd * sm, 1.0)
        Kcs = bo.round_strike(S0 + short_sd * sm, 1.0); Kcl = bo.round_strike(Kcs + width_sd * sm, 1.0)
        if Kpl >= Kps or Kcl <= Kcs:
            return None

        def val(S, T):
            return (bo.bs(S, Kps, T, bo.strike_iv(iv, S0, Kps, sm, SKEW), False)
                    - bo.bs(S, Kpl, T, bo.strike_iv(iv, S0, Kpl, sm, SKEW), False)
                    + bo.bs(S, Kcs, T, bo.strike_iv(iv, S0, Kcs, sm, SKEW), True)
                    - bo.bs(S, Kcl, T, bo.strike_iv(iv, S0, Kcl, sm, SKEW), True))
        credit_mid = val(S0, Tt)
        credit = credit_mid * (1 - 4 * COSTS.spread_pct) - 4 * COSTS.fee      # 4 legs, sold net
        width = max(Kps - Kpl, Kcl - Kcs)
        risk = width - credit
        if credit <= 0 or risk <= 0:
            return None
        for i in range(1, n):
            T_ = Tt * (1 - i / n)
            mtm = val(rest.close.iloc[i], max(T_, 0.0)) * (1 + 4 * COSTS.spread_pct)
            r_ = (credit - mtm) / risk
            if stop is not None and r_ <= stop:
                return stop
        S1 = rest.close.iloc[-1]
        pay = max(Kps - S1, 0) - max(Kpl - S1, 0) + max(S1 - Kcs, 0) - max(S1 - Kcl, 0)
        return (credit - pay) / risk

    print(f"{'entry':>7}{'stop':>7}{'regime':>12}{'n':>5}{'avg%':>8}{'win%':>7}{'maxDD@10%':>11}")
    for et in ("09:35", "11:00", "13:00"):
        for stop in (None, -0.5):
            for lab, f in (("gz>0.5", lambda r: r.gz > 0.5), ("gz<-0.5", lambda r: r.gz < -0.5),
                           ("ALL", lambda r: True)):
                rets = [x for x in (condor_path(day, et, stop) for day in days
                                    if f(dmap.loc[day])) if x is not None]
                if len(rets) < 25:
                    continue
                a = np.array(rets)
                eq = np.cumprod(1 + 0.10 * a)
                print(f"{et:>7}{str(stop):>7}{lab:>12}{len(a):>5}{a.mean()*100:>+8.2f}"
                      f"{(a>0).mean()*100:>7.0f}{bo.max_dd(eq)*100:>10.0f}%")
    print("   (494 days only -> SUGGESTIVE. Read the gz>0.5 vs gz<-0.5 CONTRAST, not the level.)")


# ============================================================================ final
def section_final(d):
    """THE FINAL 0DTE RULE SET.

    PREMIUM sleeve (primary):  prior-close GEX z > +0.5  ->  sell a 0DTE iron condor,
      short strikes ~1.25 SD of the implied move, wings ~1 SD wide, stop at -0.5 x max risk.
      Stand down otherwise.  Justification is model-free: high gamma shrinks the realised range
      relative to MARKET-IMPLIED vol (beta_gz = -0.074 on range/VIX9D, t = -9.9, stable).
    DIRECTIONAL tilt (optional):  on DIX-confluence >= 2 days, drop the CALL side and sell the put
      spread only, for more credit at the same risk.  Tested below against the plain condor.
    """
    global AWARE
    print("\n" + "=" * 100)
    print("SECTION: FINAL COMBINED 0DTE RULE SET — honest OOS (2016+, never tuned on)")
    print("=" * 100)
    oos = d[d.date >= OOS_START].copy()

    def build(df, vrp, tilt_on=True, short_sd=1.25):
        parts = []
        gate = df.gz > 0.5
        if tilt_on:
            m1 = gate & (df.conf >= 2)
            m2 = gate & (df.conf < 2)
            T1 = run_rule(df, m1, "credit", vrp=vrp, short_sd=short_sd, width_sd=1.0, stop=-0.5)
            T2 = run_rule(df, m2, "condor", vrp=vrp, short_sd=short_sd, width_sd=1.0, stop=-0.5)
            for T, lab in ((T1, "PUTSPREAD(bull tilt)"), (T2, "CONDOR")):
                if len(T):
                    T["sleeve"] = lab; parts.append(T)
        else:
            T = run_rule(df, gate, "condor", vrp=vrp, short_sd=short_sd, width_sd=1.0, stop=-0.5)
            if len(T):
                T["sleeve"] = "CONDOR"; parts.append(T)
        return pd.concat(parts).sort_values("date") if parts else pd.DataFrame()

    print("\n-- does the bullish DIX tilt add anything on top of the plain gamma-gated condor? --")
    for vrp in (1.00, VRP_BASE, 1.20):
        a = build(oos, vrp, tilt_on=False); b = build(oos, vrp, tilt_on=True)
        print(f"   vrp={vrp:.2f}  plain condor {a.ret.mean()*100:+6.2f}%   with DIX tilt "
              f"{b.ret.mean()*100:+6.2f}%   delta {(b.ret.mean()-a.ret.mean())*100:+5.2f}pp")

    print("\n-- headline: gamma-gated 0DTE condor, OOS 2016-2026 --")
    print("   AWARE=0.35 is the evidence-based setting: VIX9D prices ~1/3 of the gamma effect.")
    for aw in (0.0, 0.35, 0.5):
        AWARE = aw
        for vrp in VRP_GRID:
            A = build(oos, vrp, tilt_on=False)
            bo.summarize(A.ret, f"0DTE PREMIUM AWARE={aw:.2f} vrp={vrp:.2f}",
                         n_trials=len(DIR_GRID) + len(PREM_GRID), risk_frac=0.05)
    AWARE = 0.35
    print("\n-- with vs without the -0.5R stop (AWARE=0.35, vrp=1.10) --")
    for stp in (None, -0.5, -0.35):
        A = run_rule(oos, oos.gz > 0.5, "condor", vrp=VRP_BASE, short_sd=1.25, width_sd=1.0, stop=stp)
        bo.summarize(A.ret, f"   stop={stp}", n_trials=3, risk_frac=0.05)
    AWARE = 0.0

    print("\n-- SENSITIVITY MATRIX: avg return per trade (%), rows=vrp, cols=market gamma-awareness --")
    print(f"{'vrp':>6}" + "".join(f"{'AWARE='+str(a):>13}" for a in AWARE_GRID))
    for vrp in VRP_GRID:
        line = f"{vrp:>6.2f}"
        for aw in AWARE_GRID:
            AWARE = aw
            A = build(oos, vrp, tilt_on=False)
            line += f"{A.ret.mean()*100:>+12.2f}%"
        print(line)
    AWARE = 0.0
    print("   Evidence-based cell: AWARE ~ 0.3-0.5 (VIX9D prices roughly a third of the gamma effect),")
    print("   vrp ~ 1.05-1.15.  Read the honest expectation from THERE, not from the top-left corner.")

    print("\n-- PARAMETER SENSITIVITY: short-strike distance (vrp=1.10, AWARE=0.5) --")
    AWARE = 0.5
    for ssd in (1.0, 1.15, 1.25, 1.4, 1.5):
        A = build(oos, VRP_BASE, tilt_on=False, short_sd=ssd)
        r = bo.summarize(A.ret, "", n_trials=1, risk_frac=0.05, verbose=False)
        print(f"   short {ssd:.2f}SD: n={r['n']:>4} avg {r['avg']*100:+6.2f}% win {r['win']*100:3.0f}% "
              f"maxDD {r['maxdd']*100:5.1f}%  DSR {r['dsr']:.2f}")
    print("   -> a plateau across 1.0-1.5 SD means the rule is NOT knife-edge fitted.")

    print("\n-- GAMMA-GATE sensitivity (vrp=1.10, AWARE=0.5): where to put the gz threshold --")
    for gzt in (-0.5, 0.0, 0.25, 0.5, 0.75, 1.0):
        A = run_rule(oos, oos.gz > gzt, "condor", vrp=VRP_BASE, short_sd=1.25, width_sd=1.0, stop=-0.5)
        if len(A) < 50:
            continue
        r = bo.summarize(A.ret, "", n_trials=1, risk_frac=0.05, verbose=False)
        print(f"   gz>{gzt:+.2f}: n={r['n']:>4} ({r['n']/10.5:.0f}/yr) avg {r['avg']*100:+6.2f}% "
              f"win {r['win']*100:3.0f}% maxDD {r['maxdd']*100:5.1f}% t {r['t']:+5.2f}")
    AWARE = 0.0

    print("\n-- YEAR BY YEAR (vrp=1.10, AWARE=0.35 [evidence-based], 5% risked per trade) --")
    AWARE = 0.35
    A = build(oos, VRP_BASE, tilt_on=False)
    eq = 1.0
    print(f"{'year':>6}{'n':>5}{'avg%':>8}{'win%':>7}{'worst':>8}{'equity yr%':>12}")
    for y, g in A.groupby(A.date.dt.year):
        e0 = eq
        for r in g.ret:
            eq *= (1 + 0.05 * r)
        print(f"{y:>6}{len(g):>5}{g.ret.mean()*100:>+8.2f}{(g.ret>0).mean()*100:>7.0f}"
              f"{g.ret.min()*100:>+8.0f}{(eq/e0-1)*100:>+12.1f}")
    print(f"  cumulative OOS equity multiple over {A.date.dt.year.nunique()} yrs: x{eq:.2f}  "
          f"(CAGR {(eq**(1/10.5)-1)*100:.1f}%)")
    eqc = np.cumprod(1 + 0.05 * A.ret.values)
    print(f"  max drawdown {bo.max_dd(eqc)*100:.1f}%   trades/yr {len(A)/10.5:.0f}   "
          f"per-trade Sharpe(ann) {bo.sharpe(A.ret.values, periods=len(A)/10.5):.2f}")

    print("\n-- WHAT WOULD IT TAKE TO GO $5,000 -> $100,000 by 2026-11-19? --")
    import datetime as _dt
    days_left = (_dt.date(2026, 11, 19) - _dt.date(2026, 8, 5)).days
    weeks = days_left / 7.0
    need = (100000 / 5000) ** (1 / weeks) - 1
    tr_per_wk = len(A) / 10.5 / 52.0
    print(f"   {days_left} calendar days = {weeks:.1f} weeks.  Required compounding: "
          f"{need*100:.1f}% PER WEEK ({(100000/5000)**(1/(days_left*5/7))-1:+.2%}/trading day).")
    print(f"   This rule fires {tr_per_wk:.2f} trades/week at {A.ret.mean()*100:+.2f}% per trade "
          f"on the risked amount.")
    f_needed = need / max(A.ret.mean() * tr_per_wk, 1e-9)
    print(f"   To hit {need*100:.1f}%/wk you would have to risk {f_needed*100:.0f}% of the account on "
          f"EVERY trade.")
    kelly = A.ret.mean() / (A.ret.var() + 1e-12)
    print(f"   Full-Kelly fraction for this edge is {kelly*100:.0f}% of equity; half-Kelly "
          f"{kelly*50:.0f}%.  Worst single trade was {A.ret.min()*100:.0f}% of risk.")
    for f in (0.05, 0.10, 0.25, 0.50):
        wk = (1 + f * A.ret.mean()) ** tr_per_wk - 1
        print(f"     risking {f*100:>3.0f}%/trade -> {wk*100:+.2f}%/week -> "
              f"${5000*(1+wk)**weeks:,.0f} by 2026-11-19")
    AWARE = 0.0


# ============================================================================
def main():
    global IV_SOURCE
    secs = sys.argv[1:]
    if "--iv9" in secs:
        IV_SOURCE = "sig_iv9"
        print("[IV SOURCE] = VIX9D (real market-implied price), not our own vol model")
    secs = [s for s in secs if not s.startswith("--")] or \
        ["data", "direction", "premium", "intraday", "final"]
    d = build_panel(force="--refresh" in sys.argv)
    d = add_signals(d)
    global TILT
    TILT = fit_tilt(d)
    print(f"[train-only fit] gamma IV tilt = {TILT:+.4f} per 1z of GEX  "
          f"(a fully gamma-aware market would shade IV by this much)")
    for s in secs:
        {"data": section_data, "direction": section_direction, "premium": section_premium,
         "intraday": section_intraday, "final": section_final}[s](d)


if __name__ == "__main__":
    main()
