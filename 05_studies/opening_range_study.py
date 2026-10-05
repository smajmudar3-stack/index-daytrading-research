"""opening_range_study.py — what the first 15 minutes say about the rest of the day, on the
S&P 500 and Nasdaq-100 through their tradeable proxies (SPY, QQQ), 1-minute bars.

Sholo (2026-10-05): "start testing intraday opening ranges on NDX and SPX, the first 15
minutes of the open, seeing how that affects the day, identifying any patterns or edges."

WHAT WAS ALREADY MEASURED, so it is not repeated: the opening-range BREAKOUT as a trade
(enter on the break of the 5/15/30-minute range, exit at the close, with and without the
taught stop, in R-multiples, with a trend filter): eight tests on these same ~500 sessions,
largest |t| 1.15, nothing distinguishable from noise, and the OR stop cuts the win rate
from 52% to 37% at the same expectancy (02_findings/influencer_report.md, orb_proper.py).
The literature's own number: ORB's edge sits inside 2.2 cents a share of slippage
(INTRADAY_DIRECTION.md).

THIS FILE asks the wider question — how does the SHAPE of the first 15 minutes condition
the rest of the session? — as a small, pre-registered set of conditionals, because two
years of minute bars allow about SEVEN independent configurations before an in-sample
Sharpe of 1 is expected by chance (MinBTL, METHODOLOGY_TRAPS.md trap 14). Everything is
measured from the 09:45 close (the first price available AFTER the range is known, trap 6),
in basis points of excess over nothing (the index itself is the benchmark here), with a
train half (first year) and a test half (second year), and the noise bar sqrt(2 ln N) for
the N conditionals actually run.

Per session, from the 09:30-09:44 bars:
  or_width     (high - low) / 09:45 close, and its percentile against the trailing 20 sessions
  or_dir       09:45 close vs 09:30 open: up / down
  or_pos       where the 09:45 close sits in the range: top third / middle / bottom third
  gap          09:30 open vs prior regular-session close, in bp
  or_volx      first-15-minute volume / its trailing-20-session median
Outcomes, 09:45 -> 16:00:
  rod_ret      rest-of-day return (bp), from the 09:45 close
  rod_range    rest-of-day high-low as % of 09:45 close
  first_break  which side of the range breaks first (high / low / neither), and when
  close_vs_or  close above the OR high / inside / below the OR low
  hi_in_or, lo_in_or   whether the DAY's high (low) was set inside the first 15 minutes
  mfe / mae    best and worst excursion from the 09:45 close, for the sign of or_dir

Pre-registered conditionals (the count is printed and sets the noise bar):
  A  or_dir -> rod_ret                     (continuation vs reversal of the first 15 min)
  B  or_pos -> rod_ret                     (close near the high/low of the range)
  C  gap sign x or_dir -> rod_ret          (gap-and-go vs gap-and-fade, conditioned on the range)
  D  or_width tercile -> rod_range         (does a wide open mean a wide day? volatility, not direction)
  E  or_width tercile -> rod_ret and |rod_ret|
  F  or_volx tercile -> rod_range, rod_ret
  G  first break side -> close_vs_or       (does the first break hold to the close?)
  H  day-structure facts: P(day high or low set in the first 15 min), by or_width tercile
Then the ONE trade any surviving row implies, with a slippage sweep 0 -> 5 bp a side on the
train/test halves. If nothing survives, that is printed as the result.

Data: SPY and QQQ minute bars 2024-07 -> 2026-07 (~500 sessions; quant-factory store), plus
the vendor's 1-minute SPY/QQQ bars 2026-04 -> 2026-10 for the sessions after 2026-07 where
present. Regular session only, 09:30-15:59 ET.
"""
import glob
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

warnings.filterwarnings("ignore")
OR_MIN = 15
TICKERS = {"SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq-100 (QQQ)"}
RT_BP = 2.0                       # shares, round trip, the influencer report's assumption
N_TESTS = 0


def load_minute(tk):
    files = sorted(glob.glob(os.path.join(paths.require_data("minute", tk), "*.parquet")))
    df = pd.concat([pd.read_parquet(f) for f in files])
    df = df[~df.index.duplicated(keep="first")].sort_index()
    df.index = df.index.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:59")[["open", "high", "low", "close", "volume"]]
    # extend with the vendor's bars for sessions after the store ends
    uw = os.path.join(paths.DATA_ROOT, "uw_hist", "ohlc_1m.parquet")
    if os.path.exists(uw):
        u = pd.read_parquet(uw)
        u = u[(u._symbol == tk) & (u.market_time == "r")].copy()
        if len(u):
            u["ts"] = pd.to_datetime(u.start_time, utc=True).dt.tz_convert("America/New_York")
            u = u.set_index("ts").sort_index()[["open", "high", "low", "close", "volume"]].astype(float)
            u = u.between_time("09:30", "15:59")
            u = u[u.index > df.index.max()]
            if len(u):
                df = pd.concat([df, u]).sort_index()
    df["day"] = df.index.date
    return df


def sessions(df):
    rows = []
    cut = (pd.Timestamp("09:30") + pd.Timedelta(minutes=OR_MIN)).strftime("%H:%M")
    prev_close = None
    for day, g in df.groupby("day"):
        if len(g) < 300:
            prev_close = g["close"].iloc[-1] if len(g) else prev_close
            continue
        o = g.between_time("09:30", cut, inclusive="left")
        r = g.between_time(cut, "15:59")
        if len(o) < 10 or len(r) < 200:
            prev_close = g["close"].iloc[-1]
            continue
        hi, lo = o["high"].max(), o["low"].min()
        c945 = r["open"].iloc[0]                                   # first price AFTER the range is known
        op = o["open"].iloc[0]
        close = r["close"].iloc[-1]
        width = (hi - lo) / c945
        rest_hi, rest_lo = r["high"].max(), r["low"].min()
        # first break of the range, and when
        brk_hi = r.index[r["high"] > hi]
        brk_lo = r.index[r["low"] < lo]
        t_hi = brk_hi[0] if len(brk_hi) else None
        t_lo = brk_lo[0] if len(brk_lo) else None
        if t_hi is None and t_lo is None:
            first = "neither"; t_first = None
        elif t_lo is None or (t_hi is not None and t_hi < t_lo):
            first = "high"; t_first = t_hi
        else:
            first = "low"; t_first = t_lo
        day_hi_t = g["high"].idxmax(); day_lo_t = g["low"].idxmin()
        or_end = o.index[-1]
        rows.append({
            "day": pd.Timestamp(day), "open": op, "or_hi": hi, "or_lo": lo, "c945": c945, "close": close,
            "prev_close": prev_close, "or_width": width,
            "or_dir": "up" if o["close"].iloc[-1] > op else "down",
            "or_pos": (o["close"].iloc[-1] - lo) / (hi - lo) if hi > lo else 0.5,
            "or_vol": o["volume"].sum(),
            "gap_bp": (op / prev_close - 1) * 1e4 if prev_close else np.nan,
            "rod_ret": (close / c945 - 1) * 1e4,
            "rod_range": (rest_hi - rest_lo) / c945 * 100,
            "day_range": (g["high"].max() - g["low"].min()) / c945 * 100,
            "first_break": first,
            "t_first_min": (t_first - r.index[0]).total_seconds() / 60 if t_first is not None else np.nan,
            "broke_hi": t_hi is not None, "broke_lo": t_lo is not None,
            "close_vs_or": "above" if close > hi else ("below" if close < lo else "inside"),
            "hi_in_or": day_hi_t <= or_end, "lo_in_or": day_lo_t <= or_end,
            "mfe_up": (rest_hi / c945 - 1) * 1e4, "mae_up": (rest_lo / c945 - 1) * 1e4,
        })
        prev_close = close
    d = pd.DataFrame(rows).set_index("day").sort_index()
    d["or_width_pct"] = d.or_width.rolling(20, min_periods=10).apply(lambda v: (v[:-1] < v[-1]).mean(), raw=True)
    d["or_volx"] = d.or_vol / d.or_vol.rolling(20, min_periods=10).median().shift(1)
    d["pos_b"] = pd.cut(d.or_pos, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["bottom third", "middle", "top third"])
    d["width_b"] = pd.qcut(d.or_width_pct, 3, labels=["narrow", "mid", "wide"], duplicates="drop")
    d["volx_b"] = pd.qcut(d.or_volx, 3, labels=["quiet", "mid", "heavy"], duplicates="drop")
    d["gap_sign"] = np.where(d.gap_bp > 10, "gap up", np.where(d.gap_bp < -10, "gap down", "flat"))
    mid = d.index[len(d) // 2]
    d["half"] = np.where(d.index < mid, "train", "test")
    return d


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def cond(d, by, y, label, sign_col=None):
    """Mean of y by the levels of `by`, with t, win rate, and the two halves. If sign_col is
    given, y is multiplied by +1/-1 so 'continuation' reads positive."""
    global N_TESTS
    yy = d[y].copy()
    if sign_col is not None:
        yy = yy * np.where(d[sign_col] == "up", 1, -1)
    g = d.assign(_y=yy).groupby(by, observed=True)
    rows = []
    for k, s in g:
        tr, te = s[s.half == "train"]._y, s[s.half == "test"]._y
        rows.append({"level": k if not isinstance(k, tuple) else " / ".join(map(str, k)), "n": len(s), "mean": s._y.mean(),
                     "t": _t(s._y), "win": (s._y > 0).mean(), "train": tr.mean(), "t_tr": _t(tr), "test": te.mean(), "t_te": _t(te)})
        N_TESTS += 1
    t = pd.DataFrame(rows)
    print(f"\n  {label}  [{y}{' x sign of first 15 min' if sign_col else ''}]")
    print("  " + t.to_string(index=False, float_format=lambda v: f"{v:8.2f}").replace("\n", "\n  "))
    return t


def facts(d, tk):
    print(f"\n  DAY STRUCTURE, {tk} ({len(d)} sessions)")
    print(f"   day's HIGH set inside the first 15 min: {d.hi_in_or.mean()*100:.0f}%   day's LOW: {d.lo_in_or.mean()*100:.0f}%   "
          f"either: {(d.hi_in_or | d.lo_in_or).mean()*100:.0f}%   (random 15 of 390 minutes would be ~4% each)")
    print(f"   OR high broken by the close: {d.broke_hi.mean()*100:.0f}%   OR low broken: {d.broke_lo.mean()*100:.0f}%   "
          f"BOTH (whipsaw): {(d.broke_hi & d.broke_lo).mean()*100:.0f}%   neither (inside day): {(~d.broke_hi & ~d.broke_lo).mean()*100:.0f}%")
    fb = d.first_break.value_counts(normalize=True).mul(100).round(0).to_dict()
    print(f"   first break: {fb}; median minutes to first break: {d.t_first_min.median():.0f}")
    cv = pd.crosstab(d.first_break, d.close_vs_or, normalize="index").mul(100).round(0)
    print("   close vs the range, given which side broke first (%):\n  " + cv.to_string().replace("\n", "\n  "))
    w = d.groupby("width_b", observed=True).agg(n=("or_width", "size"), or_width_bp=("or_width", lambda v: v.mean() * 1e4),
                                                 rod_range=("rod_range", "mean"), day_range=("day_range", "mean"),
                                                 hi_or_lo_in_or=("hi_in_or", lambda v: (v | d.loc[v.index, "lo_in_or"]).mean() * 100),
                                                 whipsaw=("broke_hi", lambda v: (v & d.loc[v.index, "broke_lo"]).mean() * 100))
    print("   by opening-range width tercile:\n  " + w.to_string(float_format=lambda v: f"{v:7.2f}").replace("\n", "\n  "))


def the_trade(d, tk):
    """The one rule the tables imply if anything survived: fade or follow the first 15 minutes
    from the 09:45 price to the close, by condition, with a slippage sweep."""
    print(f"\n  SLIPPAGE SWEEP, {tk}: follow the first 15 minutes (long if up, short if down) 09:45 -> close")
    sgn = np.where(d.or_dir == "up", 1, -1)
    base = d.rod_ret * sgn
    for cost in (0, 1, 2, 3, 5):
        net = base - cost
        tr, te = net[d.half == "train"], net[d.half == "test"]
        print(f"   {cost} bp/side: all {net.mean():+6.2f} bp (t {_t(net):+.2f}, win {(net>0).mean():.2f}) | "
              f"train {tr.mean():+6.2f} (t {_t(tr):+.2f}) | test {te.mean():+6.2f} (t {_t(te):+.2f})")
    print(f"  and the FADE (the opposite): all {(-base - 2).mean():+6.2f} bp net of 2 bp/side (t {_t(-base-2):+.2f})")


def main():
    pd.set_option("display.width", 220)
    global N_TESTS
    panels = {}
    for tk, name in TICKERS.items():
        df = load_minute(tk)
        d = sessions(df)
        panels[tk] = d
        print(f"\n{'='*150}\n{name}: {len(d)} sessions {d.index.min().date()} .. {d.index.max().date()}; "
              f"median OR width {d.or_width.median()*1e4:.0f} bp, median rest-of-day range {d.rod_range.median():.2f}%, "
              f"mean |rest-of-day return| {d.rod_ret.abs().mean():.0f} bp")
        facts(d, tk)
        cond(d, "or_dir", "rod_ret", "A. first 15 min direction -> rest of day (raw)")
        cond(d, "pos_b", "rod_ret", "B. where the 09:45 close sits in the range -> rest of day (raw)")
        cond(d, ["gap_sign", "or_dir"], "rod_ret", "C. gap x first 15 min -> rest of day (raw)")
        cond(d, "width_b", "rod_range", "D. OR width tercile -> rest-of-day RANGE (%)")
        d["abs_rod"] = d.rod_ret.abs()
        cond(d, "width_b", "abs_rod", "E1. OR width tercile -> |rest-of-day return| (bp)")
        cond(d, "width_b", "rod_ret", "E2. OR width tercile -> rest of day, signed by first 15 min", sign_col="or_dir")
        cond(d, "volx_b", "rod_range", "F1. opening volume tercile -> rest-of-day RANGE (%)")
        cond(d, "volx_b", "rod_ret", "F2. opening volume tercile -> rest of day, signed by first 15 min", sign_col="or_dir")
        # G is measured from the BREAK LEVEL (the OR high or low), never from the 09:45 price: the
        # condition "which side broke first" is only known after the break, and 09:45 -> the level
        # is 9-13 bp of unearnable drift that made the first draft of this cell read t 2.5-2.9
        # (METHODOLOGY_TRAPS.md trap 6, caught again here on 2026-10-05).
        d["rod_vs_break"] = np.where(d.first_break == "high", (d.close / d.or_hi - 1) * 1e4,
                                     np.where(d.first_break == "low", (1 - d.close / d.or_lo) * 1e4, np.nan))
        cond(d, "first_break", "rod_vs_break", "G. first side broken -> break LEVEL to close, in the break's direction (gross)")
        the_trade(d, tk)
    print(f"\n{'='*150}\nCONDITIONAL CELLS TESTED: {N_TESTS} across both proxies; noise bar for the largest |t| under the null "
          f"~ {np.sqrt(2*np.log(N_TESTS)):.1f}. MinBTL for two years of data is ~7 independent configurations.")
    out = pd.concat(panels, names=["tk"]).reset_index()
    out.to_parquet(os.path.join(paths.DATA_ROOT, "opening_range_sessions.parquet"), index=False)


if __name__ == "__main__":
    main()
