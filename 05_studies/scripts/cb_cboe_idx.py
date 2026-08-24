"""Cboe benchmark index forensics: CNDR (iron condor), BFLY (iron butterfly), PUT, WPUT, BXM, SPX.

All series are Cboe's own daily index CSVs (real, tradable-rule indices priced off actual SPX option
markets at the roll -- see methodology note in the report). CNDR/BFLY/PUT/WPUT all hold a T-bill
account plus the short option position, so the T-BILL YIELD IS INSIDE THE INDEX RETURN. The only
honest measure of the option strategy is the EXCESS return over T-bills, computed here.
"""
import pandas as pd
import numpy as np

SP = "/private/tmp/claude-501/-Users-sahilmajmudar/c703fa96-a221-4df1-a82d-b31b1bf84807/scratchpad"
NAMES = ["CNDR", "BFLY", "PUT", "WPUT", "BXM", "CMBO", "SPX"]


def load(n):
    d = pd.read_csv(f"{SP}/{n}.csv")
    d.columns = ["date", n]
    d["date"] = pd.to_datetime(d["date"])
    return d.set_index("date")[n].astype(float).sort_index()


px = pd.concat([load(n) for n in NAMES], axis=1)

# risk-free: 3-month T-bill secondary market rate (FRED DTB3), daily percent
try:
    rf = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3")
    rf.columns = ["date", "rate"]
    rf["date"] = pd.to_datetime(rf["date"])
    rf = rf.set_index("date")["rate"]
    rf = pd.to_numeric(rf, errors="coerce").ffill()
except Exception as e:  # offline fallback
    print("FRED fetch failed:", e)
    rf = None

ret = np.log(px).diff()


def stats(series, rf_series, label):
    s = series.dropna()
    if len(s) < 60:
        return None
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (np.exp(s.sum()) ** (1 / yrs) - 1) * 100
    vol = s.std() * np.sqrt(252) * 100
    if rf_series is not None:
        r = rf_series.reindex(s.index).ffill() / 100 / 252
        ex = s - r
        exann = ex.mean() * 252 * 100
        sharpe = ex.mean() / ex.std() * np.sqrt(252)
    else:
        exann, sharpe = np.nan, np.nan
    eq = np.exp(s.cumsum())
    dd = (eq / eq.cummax() - 1).min() * 100
    worst = s.min() * 100
    return dict(label=label, n_yrs=round(yrs, 1), CAGR=round(cagr, 2), vol=round(vol, 2),
                excess_ann=round(exann, 2), sharpe=round(sharpe, 2), maxDD=round(dd, 1),
                worst_day=round(worst, 1))


WINDOWS = [("full", None, None), ("1986-2009", "1986-01-01", "2009-12-31"),
           ("2010-2019", "2010-01-01", "2019-12-31"), ("2020-2026", "2020-01-01", None),
           ("2010-2026", "2010-01-01", None)]

rows = []
for n in NAMES:
    for wl, a, b in WINDOWS:
        s = ret[n]
        if a:
            s = s[s.index >= a]
        if b:
            s = s[s.index <= b]
        st = stats(s, rf, f"{n} {wl}")
        if st:
            rows.append(st)
out = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(out.to_string(index=False))

print("\n--- calendar-year total returns (%) ---")
yr = (np.exp(ret.groupby(ret.index.year).sum()) - 1) * 100
print(yr.loc[2004:].round(2).to_string())

print("\n--- worst 10 single days for CNDR and BFLY ---")
for n in ["CNDR", "BFLY"]:
    w = (np.exp(ret[n].dropna()) - 1).sort_values().head(10) * 100
    print(f"\n{n}:")
    print(pd.DataFrame({"pct": w.round(2), "SPX_same_day": ((np.exp(ret["SPX"].reindex(w.index)) - 1) * 100).round(2)}).to_string())

print("\n--- specific stress windows, cumulative % ---")
EV = [("Feb2018", "2018-02-01", "2018-02-12"), ("Mar2020", "2020-02-19", "2020-03-23"),
      ("Aug2024", "2024-07-31", "2024-08-07"), ("Apr2025", "2025-03-28", "2025-04-09"),
      ("Dec2018", "2018-12-01", "2018-12-26")]
for lbl, a, b in EV:
    seg = ret.loc[a:b]
    print(lbl, {c: round((np.exp(seg[c].sum()) - 1) * 100, 2) for c in NAMES})
