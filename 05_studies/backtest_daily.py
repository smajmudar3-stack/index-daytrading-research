"""backtest_daily.py — what does the validated edge actually return DAY BY DAY?

RULES.md reports the edge per TRADE (+3.7%, 91% win). That is not the number you feel. The rule only
fires on ~32% of sessions, so the honest daily figure has to average in every day it stands down, and
the account-level figure has to apply the risk fraction. This script answers, on the out-of-sample
window only:

  - average return on a DAY IT TRADES, and averaged across ALL sessions
  - the full distribution: best day, worst day, percentiles
  - losing streaks, which is what actually ends accounts
  - the equity path for a real starting balance at several risk settings
  - a two-week rolling distribution, so "what could 10 trading days do?" is answered with the
    empirical spread rather than a point estimate

Reuses the validated machinery in backtest_0dte_rules.py / bt_options.py — no new pricing model.
"""
import numpy as np
import pandas as pd

import backtest_0dte_rules as B

OOS_START = "2016-01-01"      # the walk-forward OOS window used in RULES.md
GZ_GATE = 0.5                 # the validated gamma gate
SHORT_SD, WIDTH_SD = 1.25, 1.0
STOP_R = -0.5                 # -0.5 x max risk
START_BALANCE = 2000.0


AWARE_EVIDENCE = 0.35   # the evidence-based cell RULES.md headlines; 0.0 is the market-blind best case


def build(aware=AWARE_EVIDENCE, gate=True, stop=STOP_R):
    """Build the OOS trade set. `aware` sets how much of the gamma effect the option market is assumed
    to already price into same-day IV — the single most important assumption in the whole study."""
    full = B.build_panel()
    full = B.add_signals(full)
    # TILT must be fit on TRAIN data only (pre-OOS), never on the evaluation window
    B.TILT = B.fit_tilt(full[full.date < OOS_START])
    B.AWARE = aware
    d = full[full.date >= OOS_START].copy()
    mask = (d.gz > GZ_GATE) if gate else pd.Series(True, index=d.index)
    tr = B.run_rule(d, mask, "condor", short_sd=SHORT_SD, width_sd=WIDTH_SD, stop=stop)
    return d, tr


def daily_frame(d, tr, risk_frac):
    """One row per SESSION in the OOS window; 0 on days the rule stands down."""
    sess = d[["date"]].copy()
    sess["traded"] = 0
    sess["trade_ret"] = np.nan
    m = dict(zip(tr.date, tr.ret))
    sess["trade_ret"] = sess.date.map(m)
    sess["traded"] = sess.trade_ret.notna().astype(int)
    # account-level daily return = trade return on risked capital x risk fraction
    sess["acct_ret"] = sess.trade_ret.fillna(0.0) * risk_frac
    return sess


def streaks(x):
    """Longest run of consecutive losing TRADES."""
    best = cur = 0
    for v in x:
        if v < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def main():
    d, tr = build()
    n_sess = len(d)
    n_tr = len(tr)
    print(f"OOS window {d.date.min().date()} -> {d.date.max().date()}")
    print(f"sessions {n_sess} | trades {n_tr} ({n_tr/n_sess*100:.0f}% of sessions, "
          f"~{n_tr/(n_sess/252):.0f}/yr)")
    print(f"gate: prior-close GEX z > +{GZ_GATE} | condor {SHORT_SD}SD shorts / {WIDTH_SD}SD wings | stop {STOP_R}R")

    r = tr.ret.values
    print("\n== PER TRADE (on capital at risk) ==")
    print(f"  mean {r.mean()*100:+.2f}%   median {np.median(r)*100:+.2f}%   win rate {(r>0).mean()*100:.0f}%")
    print(f"  best {r.max()*100:+.1f}%   worst {r.min()*100:+.1f}%   longest losing streak {streaks(r)}")

    print("\n== DAILY, AT THE 12% SLEEVE CAP (what the account actually feels) ==")
    for rf, lab in ((0.05, "5% risk (tested)"), (0.12, "12% cap (our sleeve)"), (0.25, "25% aggressive")):
        s = daily_frame(d, tr, rf)
        a = s.acct_ret.values
        td = s[s.traded == 1].acct_ret.values
        eq = np.cumprod(1 + a)
        peak = np.maximum.accumulate(eq)
        mdd = ((peak - eq) / peak).max() * 100
        yrs = n_sess / 252
        cagr = (eq[-1] ** (1 / yrs) - 1) * 100
        print(f"\n  {lab}")
        print(f"    on a day it TRADES : {td.mean()*100:+.2f}%  (best {td.max()*100:+.1f}%, worst {td.min()*100:+.1f}%)")
        print(f"    across ALL sessions: {a.mean()*100:+.3f}%/day")
        print(f"    CAGR {cagr:+.1f}%   max drawdown -{mdd:.1f}%   final x{eq[-1]:.2f}")
        print(f"    ${START_BALANCE:,.0f} -> ${START_BALANCE*eq[-1]:,.0f} over {yrs:.1f} years")

    # the two-week question, answered empirically
    print("\n== TWO WEEKS (10 trading days), 12% sleeve cap — EMPIRICAL DISTRIBUTION ==")
    s = daily_frame(d, tr, 0.12)
    a = s.acct_ret.values
    win = 10
    rolls = np.array([np.prod(1 + a[i:i + win]) for i in range(len(a) - win)])
    pct = lambda q: np.percentile(rolls, q)
    print(f"  windows tested: {len(rolls)}")
    print(f"    worst    {(rolls.min()-1)*100:+.1f}%   ->  ${START_BALANCE*rolls.min():,.0f}")
    print(f"    5th pct  {(pct(5)-1)*100:+.1f}%   ->  ${START_BALANCE*pct(5):,.0f}")
    print(f"    median   {(pct(50)-1)*100:+.1f}%   ->  ${START_BALANCE*pct(50):,.0f}")
    print(f"    95th pct {(pct(95)-1)*100:+.1f}%   ->  ${START_BALANCE*pct(95):,.0f}")
    print(f"    BEST     {(rolls.max()-1)*100:+.1f}%   ->  ${START_BALANCE*rolls.max():,.0f}")
    hit = (rolls >= 5.0).mean() * 100
    print(f"  share of 2-week windows that 5x'd the account: {hit:.2f}%")

    # by year
    print("\n== BY YEAR (12% cap) ==")
    s["year"] = s.date.dt.year
    for y, g in s.groupby("year"):
        eq = np.prod(1 + g.acct_ret.values)
        print(f"  {y}  {(eq-1)*100:+6.1f}%   trades {int(g.traded.sum()):3d}")

    # ---- what each layer we added is actually worth -------------------------------------------
    print("\n== ABLATION: contribution of each deterministic layer we added (12% cap) ==")
    def _line(lbl, dd, tt):
        if tt is None or len(tt) == 0:
            print(f"  {lbl:34s} no trades")
            return
        ss = daily_frame(dd, tt, 0.12)
        aa = ss.acct_ret.values
        eq = np.cumprod(1 + aa)
        peak = np.maximum.accumulate(eq); mdd = ((peak - eq) / peak).max() * 100
        yrs = len(dd) / 252
        print(f"  {lbl:34s} {tt.ret.mean()*100:+5.2f}%/trade  n={len(tt):4d}  "
              f"CAGR {(eq[-1]**(1/yrs)-1)*100:+7.1f}%  maxDD -{mdd:4.1f}%")

    d0, t0 = build(gate=True, stop=STOP_R);   _line("full rule (gate + stop)", d0, t0)
    d1, t1 = build(gate=True, stop=None);     _line("  without the -0.5R stop", d1, t1)
    d2, t2 = build(gate=False, stop=STOP_R);  _line("  without the gamma gate", d2, t2)
    d3, t3 = build(gate=False, stop=None);    _line("  neither (condor every day)", d3, t3)

    # ---- how much the core assumption matters -------------------------------------------------
    print("\n== SENSITIVITY: how much of the gamma effect does the market already price? ==")
    for aw in (0.0, 0.35, 0.5, 1.0):
        dd, tt = build(aware=aw)
        ss = daily_frame(dd, tt, 0.12)
        eq = np.cumprod(1 + ss.acct_ret.values)
        yrs = len(dd) / 252
        tag = "  <- evidence cell" if aw == AWARE_EVIDENCE else ("  <- edge should die here" if aw == 1.0 else "")
        print(f"  AWARE {aw:.2f}  {tt.ret.mean()*100:+5.2f}%/trade  "
              f"CAGR {(eq[-1]**(1/yrs)-1)*100:+7.1f}%   ${START_BALANCE:,.0f} -> ${START_BALANCE*eq[-1]:,.0f}{tag}")


if __name__ == "__main__":
    main()
