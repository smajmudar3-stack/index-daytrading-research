"""Part B: REAL-QUOTE hold-to-expiry backtest of straddles and strangles on SPY/QQQ.

Everything below uses actual EOD NBBO bid/ask from the option chain. No pricing
model is used anywhere. Entry at the far touch (buy=ask, sell=bid) is reported
next to mid-to-mid so the cost drag is visible as a separate line.

Monthly expiration cycle only -> ~12 non-overlapping trades/yr, so a simple
t-stat on per-trade returns is valid (no overlap correction needed).
"""
import sys
import numpy as np
import pandas as pd

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
SLICE = f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_monthly_slice.parquet"
UND = f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_underlying.parquet"

df = pd.read_parquet(SLICE)
df = df[(df["bid"] > 0) & (df["ask"] >= df["bid"])].copy()
df["mid"] = (df["bid"] + df["ask"]) / 2
df["adelta"] = df["delta"].abs()

und = pd.read_parquet(UND).copy()
und["date"] = pd.to_datetime(und["date"])
und = und.sort_values("date").reset_index(drop=True)
spot = und.set_index("date")["close"]
df["spot"] = df["date"].map(spot)
df = df.dropna(subset=["spot"])

# realized vol of the underlying (close-to-close), for the VRP diagnostic
und["ret"] = np.log(und["close"]).diff()

# settlement spot for each expiration = close on last trading day <= expiration
dates = und["date"].values
closes = und["close"].values


def settle(exp):
    i = np.searchsorted(dates, np.datetime64(exp), side="right") - 1
    if i < 0:
        return np.nan, pd.NaT
    return closes[i], pd.Timestamp(dates[i])


calls = df[df["type"] == "call"]
puts = df[df["type"] == "put"]


def nearest(g, col, target):
    d = (g[col] - target).abs()
    return g.loc[d == d.min()].head(1)


def legs_for(target_delta, atm=False):
    """returns per (date, expiration) the chosen call and put rows"""
    key = ["date", "expiration"]
    if atm:
        # ATM = strike closest to spot (a straddle is one strike, both legs)
        c = calls.copy()
        c["d_"] = (c["strike"] - c["spot"]).abs()
        idx = c.groupby(key)["d_"].idxmin()
        c = c.loc[idx]
        p = puts.merge(c[key + ["strike"]], on=key + ["strike"], how="inner")
        p = p.drop_duplicates(key)
        m = c.merge(p, on=key + ["dte", "spot", "strike"], suffixes=("_c", "_p"))
        m["strike_c"] = m["strike"]
        m["strike_p"] = m["strike"]
        return m
    c = calls.copy()
    c["d_"] = (c["adelta"] - target_delta).abs()
    c = c.loc[c.groupby(key)["d_"].idxmin()]
    p = puts.copy()
    p["d_"] = (p["adelta"] - target_delta).abs()
    p = p.loc[p.groupby(key)["d_"].idxmin()]
    m = c.merge(p, on=key + ["dte", "spot"], suffixes=("_c", "_p"))
    return m


STRUCTS = {
    "ATM straddle": legs_for(None, atm=True),
    "30d strangle": legs_for(0.30),
    "16d strangle": legs_for(0.16),
}

settle_cache = {}
for name, m in STRUCTS.items():
    m["bid_t"] = m["bid_c"] + m["bid_p"]
    m["ask_t"] = m["ask_c"] + m["ask_p"]
    m["mid_t"] = m["mid_c"] + m["mid_p"]
    st = []
    sd = []
    for e in m["expiration"]:
        if e not in settle_cache:
            settle_cache[e] = settle(e)
        a, b = settle_cache[e]
        st.append(a)
        sd.append(b)
    m["S_T"] = st
    m["settle_date"] = sd
    m["payoff"] = (np.maximum(m["S_T"] - m["strike_c"], 0) +
                   np.maximum(m["strike_p"] - m["S_T"], 0))

# realized vol between entry and settle, annualised
und_idx = und.set_index("date")


def rvol(d0, d1):
    r = und_idx.loc[(und_idx.index > d0) & (und_idx.index <= d1), "ret"]
    if len(r) < 3:
        return np.nan
    return r.std(ddof=1) * np.sqrt(252)


def tstat(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def report(m, label, target_dte, tol=5):
    sel = m[(m["dte"] - target_dte).abs() <= tol].copy()
    # one entry per expiration: the date closest to target dte
    sel["d_"] = (sel["dte"] - target_dte).abs()
    sel = sel.sort_values(["expiration", "d_"]).drop_duplicates("expiration")
    sel = sel.dropna(subset=["S_T"])
    if len(sel) < 10:
        print(f"{label} @{target_dte}DTE: insufficient n={len(sel)}")
        return None
    # returns
    sel["long_mid"] = (sel["payoff"] - sel["mid_t"]) / sel["mid_t"]
    sel["long_ask"] = (sel["payoff"] - sel["ask_t"]) / sel["ask_t"]
    sel["short_mid"] = (sel["mid_t"] - sel["payoff"]) / sel["mid_t"]
    sel["short_bid"] = (sel["bid_t"] - sel["payoff"]) / sel["bid_t"]
    # short return on a Reg-T-style naked margin proxy: 20% of notional
    sel["margin"] = 0.20 * sel["spot"] * 100
    sel["short_bid_on_margin"] = (sel["bid_t"] - sel["payoff"]) * 100 / sel["margin"]
    sel["rv"] = [rvol(a, b) for a, b in zip(sel["date"], sel["settle_date"])]
    sel["iv_atm"] = (sel["implied_volatility_c"] + sel["implied_volatility_p"]) / 2
    rows = []
    for col in ["long_mid", "long_ask", "short_mid", "short_bid", "short_bid_on_margin"]:
        x = sel[col]
        rows.append({
            "leg": col, "n": len(x),
            "mean_%": 100 * x.mean(), "med_%": 100 * x.median(),
            "t": tstat(x), "win_%": 100 * (x > 0).mean(),
            "worst_%": 100 * x.min(), "best_%": 100 * x.max(),
            "sd_%": 100 * x.std(ddof=1),
        })
    out = pd.DataFrame(rows).round(2)
    print(f"\n### {label}  entry ~{target_dte} DTE, held to expiry  "
          f"({sel['date'].min().date()} -> {sel['date'].max().date()})")
    print(f"    median premium ${sel['mid_t'].median():.2f}  "
          f"= {100*(sel['mid_t']/sel['spot']).median():.2f}% of spot;  "
          f"median round-trip spread = {100*((sel['ask_t']-sel['bid_t'])/sel['mid_t']).median():.2f}% of premium")
    print(f"    mean entry IV {100*sel['iv_atm'].mean():.2f}%  vs  mean realized vol over the hold "
          f"{100*sel['rv'].mean():.2f}%   (ratio {sel['iv_atm'].mean()/sel['rv'].mean():.3f})")
    print(out.to_string(index=False))
    return sel


pd.set_option("display.width", 220)
print(f"================ {SYM}: REAL-QUOTE MONTHLY STRADDLE/STRANGLE, HELD TO EXPIRY ================")
print("All prices are actual EOD NBBO. long_ask = bought at the offer (realistic).")
print("short_bid = sold at the bid (realistic). *_mid = midpoint, i.e. zero-cost fantasy.")
print("Returns are per-trade on the premium, except short_bid_on_margin (on 20%-of-notional margin).")

allsel = {}
for name, m in STRUCTS.items():
    for tdte in (45, 30, 21):
        s = report(m, name, tdte)
        if s is not None:
            allsel[(name, tdte)] = s

# yearly breakdown for the headline cell
key = ("ATM straddle", 30)
if key in allsel:
    s = allsel[key].copy()
    s["yr"] = s["date"].dt.year
    print("\n### ATM straddle 30DTE: per-year mean short_bid return on premium (%)")
    yb = s.groupby("yr").agg(n=("short_bid", "size"),
                             short_bid=("short_bid", lambda x: 100 * x.mean()),
                             long_ask=("long_ask", lambda x: 100 * x.mean()),
                             worst_short=("short_bid", lambda x: 100 * x.min())).round(1)
    print(yb.to_string())

# save for later scripts
import pickle
with open(f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_straddle_sel.pkl", "wb") as fh:
    pickle.dump({k: v for k, v in allsel.items()}, fh)
print("\nsaved selections")
