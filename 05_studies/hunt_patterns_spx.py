"""hunt_patterns_spx.py — the pattern library on 1,919 sessions of SPX instead of 500 of QQQ.

The SPXW quote file carries the underlying at every 30-minute mark from 2016-09 to 2024-05. That is
~4x the sessions available in the minute archive and it spans several genuinely different regimes
(2018 vol shock, 2020 crash, 2022 bear, 2023-24 grind). A pattern that is real should survive that;
one that only worked on 500 recent QQQ sessions should not.

Also tests the asymmetry directly: clean fast moves are DOWN 54-59% of the time in every split of the
QQQ data. That is the leverage effect and it is the single most stable directional fact found so far.
The question is whether it is exploitable after put skew, or already in the price.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

PATH = "data/spxw/data_opt.parquet"


def spx_series():
    df = pd.read_parquet(PATH, columns=["quote_date", "quote_time", "active_underlying_price"])
    s = df.groupby(["quote_date", "quote_time"]).active_underlying_price.first().reset_index()
    s["dt"] = pd.to_datetime(s.quote_date.astype(str) + " " + s.quote_time.astype(str))
    s = s.sort_values("dt").reset_index(drop=True)
    s = s.rename(columns={"quote_date": "date", "active_underlying_price": "close"})
    s["tmin"] = pd.to_datetime(s.quote_time.astype(str)).dt.hour * 60 + \
                pd.to_datetime(s.quote_time.astype(str)).dt.minute
    return s


def prep(s):
    g = s.groupby("date", group_keys=False)
    s["ret"] = g.close.apply(lambda x: x.pct_change())
    s["ret2"] = g.close.apply(lambda x: x.pct_change(2))
    s["p_ret"] = g.ret.shift(1)
    s["p2_ret"] = g.ret.shift(2)
    s["cum"] = g.close.apply(lambda x: x / x.iloc[0] - 1)
    s["run_hi"] = g.close.cummax()
    s["run_lo"] = g.close.cummin()
    s["at_hi"] = (s.close >= s.run_hi).astype(int)
    s["at_lo"] = (s.close <= s.run_lo).astype(int)
    s["vol"] = g.ret.apply(lambda x: x.rolling(6, min_periods=3).std())
    s["vol_ratio"] = s.ret.abs() / s.vol.replace(0, np.nan)
    s["streak"] = g.ret.apply(lambda x: np.sign(x).groupby(
        (np.sign(x) != np.sign(x).shift()).cumsum()).cumcount() + 1) * np.sign(s.ret)
    return s


def label(s, thr_pct, horizon):
    """Clean one-sided move of thr_pct within `horizon` 30-min bars."""
    out = []
    for date, g in s.groupby("date"):
        c = g.close.values
        n = len(c)
        y = np.zeros(n)
        for i in range(n):
            j = min(i + horizon, n - 1)
            if j <= i:
                y[i] = np.nan; continue
            fwd = c[i+1:j+1]
            up = (fwd.max() / c[i] - 1) * 100
            dn = (fwd.min() / c[i] - 1) * 100
            hu, hd = up >= thr_pct, dn <= -thr_pct
            y[i] = 1 if (hu and not hd) else (-1 if (hd and not hu) else 0)
        out.append(pd.Series(y, index=g.index))
    return pd.concat(out)


def setups(s):
    P = {}
    big = s.vol_ratio > 1.2
    P["momo_up"] = ((s.ret > 0) & (s.p_ret > 0) & big, 1)
    P["momo_dn"] = ((s.ret < 0) & (s.p_ret < 0) & big, -1)
    P["rev_up"] = ((s.ret > 0) & (s.p_ret < 0) & big, 1)
    P["rev_dn"] = ((s.ret < 0) & (s.p_ret > 0) & big, -1)
    P["new_hi"] = ((s.at_hi == 1) & big, 1)
    P["new_lo"] = ((s.at_lo == 1) & big, -1)
    P["fail_hi"] = ((s.at_hi.shift(1) == 1) & (s.ret < 0) & big, -1)
    P["fail_lo"] = ((s.at_lo.shift(1) == 1) & (s.ret > 0) & big, 1)
    P["exhaust_up"] = ((s.streak >= 3) & big, -1)
    P["exhaust_dn"] = ((s.streak <= -3) & big, 1)
    P["gap_up_fade"] = ((s.cum > 0.004) & (s.tmin <= 690), -1)
    P["gap_dn_fade"] = ((s.cum < -0.004) & (s.tmin <= 690), 1)
    P["vol_spike"] = (s.vol_ratio > 2.0, -1)
    P["quiet"] = (s.vol_ratio < 0.5, 1)
    P["late_up"] = ((s.tmin >= 870) & (s.cum > 0), 1)
    P["late_dn"] = ((s.tmin >= 870) & (s.cum < 0), -1)
    P["always_put"] = (pd.Series(True, index=s.index), -1)     # the raw asymmetry
    P["always_call"] = (pd.Series(True, index=s.index), 1)
    return P


def main():
    import sys
    thr = float(sys.argv[1]) if len(sys.argv) > 1 else 0.32     # % move (25 SPX pts ~ 0.32%)
    hz = int(sys.argv[2]) if len(sys.argv) > 2 else 2           # 30-min bars ahead
    s = prep(spx_series())
    s["y"] = label(s, thr, hz)
    s = s[s.y.notna()]
    dates = np.sort(s.date.unique())
    a, b = dates[int(len(dates)*.40)], dates[int(len(dates)*.70)]
    parts = {"TR": s.date < a, "VA": (s.date >= a) & (s.date < b), "TE": s.date >= b}
    moved = s.y != 0
    print(f"SPX 30-min | target {thr}% within {hz} bars ({hz*30}m) | sessions {s.date.nunique():,}")
    for nm, m in parts.items():
        x = s[m & moved]
        print(f"  {nm}: {len(x):,} moved ({(x.y==1).mean()*100:.1f}% up)  of {m.sum():,} bars "
              f"[move rate {len(x)/max(m.sum(),1)*100:.1f}%]")
    print(f"\n{'setup':16}{'dir':>4}{'TRn':>7}{'TRedge':>8}{'VAn':>7}{'VAedge':>8}{'TEn':>7}{'TEedge':>8}")
    print("-" * 68)
    hits = []
    for nm, (mask, dr) in setups(s).items():
        mask = mask.fillna(False)
        row, ok = [], True
        for _, m in parts.items():
            sel = s[mask & m & moved]
            allm = s[m & moved]
            if len(sel) < 40:
                ok = False; row += [len(sel), np.nan]; continue
            acc = (sel.y == dr).mean() * 100
            base = (allm.y == dr).mean() * 100
            row += [len(sel), acc - base]
        if not ok:
            continue
        stable = min(row[1], row[3], row[5]) >= 3.0
        print(f"{nm:16}{dr:>4}{row[0]:>7}{row[1]:>+7.1f}{row[2]:>7}{row[3]:>+7.1f}"
              f"{row[4]:>7}{row[5]:>+7.1f}{'  <<' if stable else ''}")
        if stable:
            hits.append(nm)
    print(f"\nstable (>=+3pp edge over base on all three): {hits or 'none'}")
    # the asymmetry itself
    for nm, m in parts.items():
        x = s[m & moved]
        print(f"  {nm} raw down-rate: {(x.y==-1).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
