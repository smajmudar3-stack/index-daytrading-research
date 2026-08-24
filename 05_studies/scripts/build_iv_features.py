"""Feasibility check: can we build the index-level constructs the paper sweep needs?
Builds, from SPY EOD chains: ATM IV at 30d and 90d (interpolated), IV term slope,
call-minus-put IV spread at matched |delta|, and 25d risk reversal (skew).
"""
import numpy as np, pandas as pd

B = "/Users/sahilmajmudar/index-daytrading/data/opt_eod"

opt = pd.read_parquet(
    B + "/SPY_options.parquet",
    columns=["date", "expiration", "strike", "type", "bid", "ask",
             "implied_volatility", "delta", "volume", "open_interest"])
u = pd.read_parquet(B + "/SPY_underlying.parquet", columns=["date", "close"])
u["date"] = pd.to_datetime(u["date"])

opt["dte"] = (opt.expiration - opt.date).dt.days
opt = opt[(opt.dte.between(5, 200)) & (opt.bid > 0) & (opt.ask > 0)
          & (opt.implied_volatility > 0.02) & (opt.implied_volatility < 3.0)
          & (opt.delta.abs().between(0.01, 0.99))]
opt = opt.merge(u, on="date", how="left")
opt["mny"] = opt.strike / opt.close
opt["rel_spread"] = (opt.ask - opt.bid) / ((opt.ask + opt.bid) / 2)


def atm_iv(g):
    """ATM IV per (date,expiration): average of nearest-to-50-delta call and put."""
    out = {}
    for t in ("call", "put"):
        s = g[g.type == t]
        if len(s) == 0:
            return np.nan
        i = (s.delta.abs() - 0.5).abs().idxmin()
        out[t] = s.loc[i, "implied_volatility"]
    return (out["call"] + out["put"]) / 2


g = opt.groupby(["date", "expiration", "dte"], sort=False)
atm = g.apply(atm_iv, include_groups=False).rename("atmiv").reset_index()
atm = atm.dropna()
print("ATM IV surface points:", len(atm), "dates:", atm.date.nunique())


def interp_iv(df, target):
    """Interpolate ATM total variance to a target DTE per date."""
    res = []
    for d, s in df.groupby("date", sort=False):
        s = s.sort_values("dte")
        lo = s[s.dte <= target].tail(1)
        hi = s[s.dte >= target].head(1)
        if len(lo) and len(hi) and lo.dte.iloc[0] != hi.dte.iloc[0]:
            w = (target - lo.dte.iloc[0]) / (hi.dte.iloc[0] - lo.dte.iloc[0])
            v = (1 - w) * lo.atmiv.iloc[0] ** 2 * lo.dte.iloc[0] + w * hi.atmiv.iloc[0] ** 2 * hi.dte.iloc[0]
            res.append((d, np.sqrt(v / target)))
        elif len(lo) and len(hi):
            res.append((d, lo.atmiv.iloc[0]))
    return pd.DataFrame(res, columns=["date", "iv"])


iv30 = interp_iv(atm, 30).rename(columns={"iv": "iv30"})
iv90 = interp_iv(atm, 90).rename(columns={"iv": "iv90"})
ts = iv30.merge(iv90, on="date", how="inner")
ts["slope"] = ts.iv90 - ts.iv30

# realized vol (close-to-close, 21d and 252d) from underlying
u = u.sort_values("date").reset_index(drop=True)
u["lr"] = np.log(u.close).diff()
u["rv21"] = u.lr.rolling(21).std() * np.sqrt(252)
u["rv252"] = u.lr.rolling(252).std() * np.sqrt(252)
ts = ts.merge(u[["date", "close", "rv21", "rv252"]], on="date", how="left")
ts["gs_spread"] = ts.iv30 - ts.rv252          # Goyal-Saretto style (index version)
ts["gs_spread21"] = ts.iv30 - ts.rv21

print("\nterm-structure series:", ts.shape, ts.date.min().date(), "->", ts.date.max().date())
print(ts[["iv30", "iv90", "slope", "rv21", "rv252", "gs_spread", "gs_spread21"]].describe().round(4).to_string())
print("\ncoverage by year:\n", ts.groupby(ts.date.dt.year).size().to_string())

# ---- 25-delta risk reversal (skew) and call-put IV spread at ~30d ----
near = opt[opt.dte.between(20, 45)].copy()
rows = []
for (d,), s in near.groupby(["date"], sort=False):
    e = s.dte.sub(30).abs().idxmin()
    exp = s.loc[e, "expiration"]
    s = s[s.expiration == exp]
    c, p = s[s.type == "call"], s[s.type == "put"]
    if len(c) < 5 or len(p) < 5:
        continue
    def pick(x, tgt):
        i = (x.delta.abs() - tgt).abs().idxmin()
        return x.loc[i, "implied_volatility"], abs(x.loc[i, "delta"])
    c25, cd = pick(c, 0.25); p25, pd_ = pick(p, 0.25)
    c50, _ = pick(c, 0.50); p50, _ = pick(p, 0.50)
    if min(abs(cd - .25), abs(pd_ - .25)) > 0.08:
        continue
    rows.append((d, p25 - c25, c50 - p50, p25 - c50))
rr = pd.DataFrame(rows, columns=["date", "rr25", "cp_spread_atm", "smirk"])
print("\nskew series:", rr.shape, rr.date.min().date(), "->", rr.date.max().date())
print(rr[["rr25", "cp_spread_atm", "smirk"]].describe().round(4).to_string())

out = ts.merge(rr, on="date", how="left")
out.to_parquet("/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_ivfeatures.parquet")
print("\nsaved SPY_ivfeatures.parquet", out.shape, list(out.columns))
print("nan frac:\n", out.isna().mean().round(3).to_string())
