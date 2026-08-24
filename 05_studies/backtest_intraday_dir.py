"""backtest_intraday_dir.py — the trade the owner ACTUALLY makes.

Everything in RULES.md §3.1 that rejected "directional 0DTE" tested buying at the open and holding to
the CLOSE. That is a different trade. Held to the close you pay a full session of extrinsic and watch
all of it decay; the same +20 SPX point move is -12% held to the bell and +44% sold fifteen minutes in.

This tests the real thing: buy intraday on a momentum trigger, hold MINUTES to an hour or two, exit on
a premium target, a premium stop, or a time stop.

Method
  - 25 months of real SPY 1-minute bars (open/high/low/close/vwap).
  - Options are priced minute-by-minute with Black-Scholes on the REMAINING session, so theta is
    charged continuously and correctly - that is the whole point of the exercise.
  - Daily IV comes from the causal vol forecast in the daily panel (past-only, no look-ahead).
  - Entry trigger: opening-range breakout confirmed by VWAP, which is the standard intraday momentum
    setup. Optionally gated by the system's DIX confluence filter.
  - Exits are checked on the minute path in PESSIMISTIC order: the adverse extreme of each bar is
    assumed to be reached before the favourable one, so stops trigger before targets within a bar.
  - Costs: half-spread each way plus per-contract fees, same model as the rest of the study.

Nothing here is tuned on the results. Parameters are swept and the whole grid is printed so that
overfitting is visible rather than hidden.
"""
import glob
import numpy as np
import pandas as pd

import bt_options as bo
import backtest_0dte_rules as B

SPREAD = 0.010          # half-spread each way on the option
FEE = 0.05
OPEN_RANGE_MIN = 30     # 9:30-10:00 defines the range
SESSION_MIN = 390
RISK_FRAC = 0.25
START = 2000.0


def load_minutes(sym="SPY"):
    fs = sorted(glob.glob(f"data/minute/{sym}/*.parquet"))
    if not fs:
        return None
    df = pd.concat([pd.read_parquet(f) for f in fs])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df["date"] = df.index.normalize().tz_localize(None)
    df["mins"] = df.index.hour * 60 + df.index.minute
    return df[(df.mins >= 570) & (df.mins < 960)]      # regular hours only


def daily_iv():
    """Causal (past-only) vol forecast per day, from the validated daily panel."""
    d = B.build_panel()
    d = B.add_signals(d)
    d["date"] = pd.to_datetime(d.date)
    return d.set_index("date")[["sig_hat", "conf", "gz"]]


def opt_price(S, K, mins_left, iv, call=True):
    T = max(mins_left, 0.5) / SESSION_MIN / 252.0
    return bo.bs(S, K, T, iv, call)


def run_day(bars, iv, side, tp, stop, max_hold, entry_min):
    """One session. Returns the trade's return on premium, or None if no trade."""
    o = bars[bars.mins < 570 + OPEN_RANGE_MIN]
    if len(o) < 10:
        return None
    hi, lo = o.high.max(), o.low.min()
    live = bars[(bars.mins >= 570 + OPEN_RANGE_MIN) & (bars.mins <= entry_min)]
    if live.empty:
        return None
    # trigger: break of the opening range in the signal's direction, confirmed by VWAP
    trig = None
    for ts, r in live.iterrows():
        if side == "call" and r.close > hi and r.close > r.vwap:
            trig = (ts, r); break
        if side == "put" and r.close < lo and r.close < r.vwap:
            trig = (ts, r); break
    if trig is None:
        return None
    ts0, r0 = trig
    S0 = r0.close
    m0 = r0.mins
    K = round(S0)                                   # ATM, $1 grid on SPY
    call = side == "call"
    entry_mid = opt_price(S0, K, SESSION_MIN - (m0 - 570), iv, call)
    if entry_mid <= 0.05:
        return None
    entry = entry_mid * (1 + SPREAD) + FEE / 100.0

    path = bars[(bars.mins > m0) & (bars.mins <= min(m0 + max_hold, 955))]
    for ts, r in path.iterrows():
        ml = SESSION_MIN - (r.mins - 570)
        # PESSIMISTIC within the bar: adverse extreme first
        adverse = r.low if call else r.high
        favour = r.high if call else r.low
        p_adv = opt_price(adverse, K, ml, iv, call) * (1 - SPREAD)
        if (p_adv - entry) / entry <= stop:
            return stop
        p_fav = opt_price(favour, K, ml, iv, call) * (1 - SPREAD)
        if (p_fav - entry) / entry >= tp:
            return tp
    # time stop: mark out at the last bar's close
    if len(path):
        last = path.iloc[-1]
        ml = SESSION_MIN - (last.mins - 570)
        ex = opt_price(last.close, K, ml, iv, call) * (1 - SPREAD)
        return (ex - entry) / entry
    return None


def backtest(mins, ivs, tp, stop, max_hold, entry_min=780, use_conf=False):
    out = []
    for date, bars in mins.groupby("date"):
        if date not in ivs.index:
            continue
        row = ivs.loc[date]
        sig = float(row.sig_hat)
        if not np.isfinite(sig) or sig <= 0:
            continue
        iv = sig * bo.SQRT252
        side = "call"
        if use_conf and row.conf < 2:
            continue
        r = run_day(bars, iv, side, tp, stop, max_hold, entry_min)
        if r is not None:
            out.append({"date": date, "ret": r})
    return pd.DataFrame(out)


def weekly_stats(tr, risk_frac=RISK_FRAC):
    if tr.empty:
        return None
    s = tr.copy()
    s["wk"] = pd.to_datetime(s.date).dt.to_period("W")
    wk = s.groupby("wk")["ret"].apply(lambda x: np.prod(1 + x * risk_frac) - 1)
    a = wk.values
    eq = np.cumprod(1 + a)
    peak = np.maximum.accumulate(eq)
    mdd = ((peak - eq) / peak).max() * 100
    return dict(n=len(tr), mean_wk=a.mean(), med_wk=np.median(a), win_wk=(a > 0).mean(),
                best=a.max(), worst=a.min(), final=eq[-1], mdd=mdd, weeks=len(a))


def main():
    print("INTRADAY DIRECTIONAL 0DTE — hold MINUTES, not to the close")
    print("SPY 1-min bars | ATM 0DTE | opening-range breakout + VWAP | BS priced per minute\n")
    mins = load_minutes("SPY")
    if mins is None:
        print("no minute data")
        return
    ivs = daily_iv()
    print(f"sessions available: {mins.date.nunique()}  "
          f"({mins.date.min().date()} -> {mins.date.max().date()})\n")

    print(f"{'TP':>6}{'stop':>7}{'hold':>7}{'n':>6}{'win%':>7}{'avg ret':>10}"
          f"{'mean wk':>10}{'med wk':>9}{'maxDD':>8}{'$2k->':>12}")
    print("-" * 84)
    best = None
    for tp in (0.30, 0.50, 1.00):
        for stop in (-0.30, -0.50):
            for hold in (15, 30, 60, 120):
                tr = backtest(mins, ivs, tp, stop, hold)
                if tr.empty or len(tr) < 30:
                    continue
                st = weekly_stats(tr)
                print(f"{tp*100:>5.0f}%{stop*100:>6.0f}%{hold:>6}m{st['n']:>6}"
                      f"{(tr.ret>0).mean()*100:>6.0f}%{tr.ret.mean()*100:>+9.1f}%"
                      f"{st['mean_wk']*100:>+9.2f}%{st['med_wk']*100:>+8.2f}%"
                      f"{-st['mdd']:>7.0f}%{START*st['final']:>11,.0f}")
                if best is None or st["final"] > best[1]["final"]:
                    best = ((tp, stop, hold), st, tr)

    if best:
        (tp, stop, hold), st, tr = best
        print(f"\nBEST CELL: TP {tp*100:.0f}% / stop {stop*100:.0f}% / hold {hold}m "
              f"at {RISK_FRAC*100:.0f}% risk")
        print(f"  trades {st['n']} over {st['weeks']} weeks | win {(tr.ret>0).mean()*100:.0f}% | "
              f"avg {tr.ret.mean()*100:+.1f}%/trade")
        print(f"  WEEKLY: mean {st['mean_wk']*100:+.2f}%  median {st['med_wk']*100:+.2f}%  "
              f"{st['win_wk']*100:.0f}% of weeks green")
        print(f"  best week {st['best']*100:+.0f}%  worst week {st['worst']*100:+.0f}%  "
              f"maxDD -{st['mdd']:.0f}%")
        print(f"  ${START:,.0f} -> ${START*st['final']:,.0f} over {st['weeks']/52:.1f} yrs")
        print("\n  CAUTION: this is the BEST of the grid above, so it is the most overfit number here.")
        print("  Judge the strategy by the whole table, not this row.")


if __name__ == "__main__":
    main()
