"""Part C: DELTA-HEDGED vs NAKED straddles on real SPY/QQQ EOD quotes.

The academic VRP literature (Bakshi-Kapadia 2003, Broadie-Chernov-Johannes 2009)
tests DELTA-HEDGED positions, which isolate the variance premium. Retail trades
NAKED ones, which carry a large directional component. This script measures both
on identical trades so the difference is attributable, not asserted.

Also runs managed exits (close at 21 DTE, take-profit at 50%) on the same trades.
All option prices are real EOD NBBO. Stock hedge costs 1bp per traded notional.
"""
import sys
import numpy as np
import pandas as pd

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
FULL = f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_monthly_full.parquet"
UND = f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_underlying.parquet"
STOCK_BPS = 1.0  # SPY/QQQ round-trip stock spread, basis points of traded notional

df = pd.read_parquet(FULL)
df["mid"] = (df["bid"] + df["ask"]) / 2
und = pd.read_parquet(UND).copy()
und["date"] = pd.to_datetime(und["date"])
und = und.sort_values("date").reset_index(drop=True)
spot = und.set_index("date")["close"]
df["spot"] = df["date"].map(spot)
df = df.dropna(subset=["spot"])
df = df[df["ask"] > 0]

# index for fast path lookup
df = df.sort_values(["expiration", "strike", "type", "date"])
paths = {k: v for k, v in df.groupby(["expiration", "strike", "type"], observed=True)}

# entry selection: for each monthly expiration, the trading day closest to TARGET_DTE
TARGET_DTE = int(sys.argv[2]) if len(sys.argv) > 2 else 45
entries = []
for exp, g in df.groupby("expiration", observed=True):
    g2 = g[(g["dte"] - TARGET_DTE).abs() <= 5]
    if len(g2) == 0:
        continue
    d0 = g2.loc[(g2["dte"] - TARGET_DTE).abs().idxmin(), "date"]
    day = g[g["date"] == d0]
    if len(day) == 0:
        continue
    s0 = day["spot"].iloc[0]
    cal = day[(day["type"] == "call") & (day["bid"] > 0)]
    if len(cal) == 0:
        continue
    k = cal.loc[(cal["strike"] - s0).abs().idxmin(), "strike"]
    entries.append((exp, d0, k, s0))

rows = []
for exp, d0, k, s0 in entries:
    try:
        pc = paths[(exp, k, "call")]
        pp = paths[(exp, k, "put")]
    except KeyError:
        continue
    pc = pc[pc["date"] >= d0].set_index("date")
    pp = pp[pp["date"] >= d0].set_index("date")
    idx = pc.index.intersection(pp.index).sort_values()
    if len(idx) < 5:
        continue
    pc = pc.loc[idx]
    pp = pp.loc[idx]
    S = pc["spot"].values
    V = (pc["mid"] + pp["mid"]).values           # straddle mid value path
    Vbid = (pc["bid"] + pp["bid"]).values
    Vask = (pc["ask"] + pp["ask"]).values
    D = (pc["delta"] + pp["delta"]).values        # net straddle delta (per 1 share)
    dtes = pc["dte"].values
    n = len(idx)
    if np.isnan(V).any() or Vask[0] <= 0:
        continue

    # ---- naked long straddle held to last available quote (expiry) ----
    # settlement: use intrinsic on the last trading day
    S_T = S[-1]
    payoff = max(S_T - k, 0) + max(k - S_T, 0)

    # ---- delta-hedged long straddle, daily rehedge at the close ----
    # position: long 1 straddle (100 sh equiv), short D*100 shares
    pnl_opt = payoff - V[0]          # per 1 share-equivalent, mid entry
    pnl_hedge = 0.0
    hedge_cost = 0.0
    prev_h = D[0]                    # shares shorted per 1 straddle
    hedge_cost += abs(prev_h) * S[0] * STOCK_BPS / 1e4
    for i in range(1, n):
        pnl_hedge += -prev_h * (S[i] - S[i - 1])
        h = D[i]
        if not np.isnan(h):
            hedge_cost += abs(h - prev_h) * S[i] * STOCK_BPS / 1e4
            prev_h = h
    # final unwind of the hedge
    hedge_cost += abs(prev_h) * S[-1] * STOCK_BPS / 1e4
    dh_gain = pnl_opt + pnl_hedge - hedge_cost

    # ---- managed exits on the naked straddle ----
    # close at 21 DTE
    i21 = np.argmax(dtes <= 21) if (dtes <= 21).any() else n - 1
    exit21_bid = Vbid[i21]
    exit21_ask = Vask[i21]
    # take profit: short side buys back at 50% of credit
    tp_i = None
    for i in range(1, n):
        if Vask[i] <= 0.5 * Vbid[0]:
            tp_i = i
            break

    r = {
        "exp": exp, "entry": d0, "K": k, "S0": s0, "S_T": S_T, "dte0": dtes[0],
        "days": n, "prem_mid": V[0], "prem_bid": Vbid[0], "prem_ask": Vask[0],
        "payoff": payoff,
        "iv0": (pc["implied_volatility"].iloc[0] + pp["implied_volatility"].iloc[0]) / 2,
        "vega0": (pc["vega"].iloc[0] + pp["vega"].iloc[0]),
        "delta0": D[0],
        # naked, real fills
        "long_naked": (payoff - Vask[0]) / Vask[0],
        "short_naked": (Vbid[0] - payoff) / Vbid[0],
        # delta-hedged (mid entry/exit, incl. stock hedge cost)
        "dh_gain_$": dh_gain,
        "dh_pct_prem": dh_gain / V[0],
        "dh_pct_spot": dh_gain / s0,
        "opt_only_$": pnl_opt,
        "hedge_$": pnl_hedge,
        "hedgecost_$": hedge_cost,
        # managed
        "short_close21": (Vbid[0] - exit21_ask) / Vbid[0],
        "long_close21": (exit21_bid - Vask[0]) / Vask[0],
        "tp_hit": tp_i is not None,
        "short_tp50": (0.5 if tp_i is not None else (Vbid[0] - payoff) / Vbid[0]),
        "abs_move_pct": abs(S_T / s0 - 1),
    }
    rows.append(r)

t = pd.DataFrame(rows)


def stats(x, label):
    x = pd.Series(x).dropna()
    return {"strategy": label, "n": len(x), "mean_%": 100 * x.mean(),
            "med_%": 100 * x.median(),
            "t": x.mean() / (x.std(ddof=1) / np.sqrt(len(x))),
            "win_%": 100 * (x > 0).mean(), "worst_%": 100 * x.min(),
            "sd_%": 100 * x.std(ddof=1)}


pd.set_option("display.width", 220)
print(f"======== {SYM} ATM straddle, entry ~{TARGET_DTE} DTE, monthly cycle, REAL EOD NBBO ========")
print(f"n = {len(t)} non-overlapping trades, {t['entry'].min().date()} -> {t['entry'].max().date()}")
print(f"median premium ${t['prem_mid'].median():.2f} = {100*(t['prem_mid']/t['S0']).median():.2f}% of spot")
print(f"median entry |net delta| of the straddle = {t['delta0'].abs().median():.3f} "
      f"(so a NAKED straddle is NOT delta neutral; that residual is the directional bet)\n")

res = pd.DataFrame([
    stats(t["long_naked"], "LONG naked straddle, bought at ASK, held to expiry (% of premium)"),
    stats(t["short_naked"], "SHORT naked straddle, sold at BID, held to expiry (% of premium)"),
    stats(t["dh_pct_prem"], "LONG DELTA-HEDGED straddle, daily rehedge, mid (% of premium)"),
    stats(-t["dh_pct_prem"], "SHORT DELTA-HEDGED straddle, daily rehedge, mid (% of premium)"),
    stats(t["long_close21"], "LONG naked, closed at 21 DTE (bid), % of premium"),
    stats(t["short_close21"], "SHORT naked, closed at 21 DTE (ask), % of premium"),
    stats(t["short_tp50"], "SHORT naked, take-profit 50% of credit else expiry, % of credit"),
]).round(2)
print(res.to_string(index=False))

print(f"\nTake-profit-50% hit rate: {100*t['tp_hit'].mean():.1f}% of trades")
print(f"\nDelta-hedged gain as % of SPOT (Bakshi-Kapadia normalisation): "
      f"mean {100*t['dh_pct_spot'].mean():.4f}%  t={t['dh_pct_spot'].mean()/(t['dh_pct_spot'].std(ddof=1)/np.sqrt(len(t))):.2f}")
print(f"  mean option-only P&L ${t['opt_only_$'].mean():.3f}, mean hedge P&L ${t['hedge_$'].mean():.3f}, "
      f"mean stock hedging cost ${t['hedgecost_$'].mean():.3f} "
      f"({100*t['hedgecost_$'].mean()/t['prem_mid'].mean():.2f}% of premium)")

# how much of naked short straddle variance is directional?
import numpy.linalg as la
und_ret = (t["S_T"] / t["S0"] - 1)
c = np.corrcoef(t["short_naked"], und_ret.abs())[0, 1]
print(f"\ncorr(short naked straddle return, |underlying move|) = {c:.3f}")
c2 = np.corrcoef(t["dh_pct_prem"], und_ret.abs())[0, 1]
print(f"corr(delta-hedged straddle return, |underlying move|) = {c2:.3f}")

# sub-period stability of the delta-hedged (i.e. pure vol) trade
t["yr"] = t["entry"].dt.year
t["era"] = pd.cut(t["yr"], [2007, 2011, 2015, 2019, 2026],
                  labels=["2008-11", "2012-15", "2016-19", "2020-25"])
print("\n--- SHORT DELTA-HEDGED straddle by era (% of premium) ---")
print(t.groupby("era", observed=True).apply(lambda g: pd.Series({
    "n": len(g), "mean_%": -100 * g["dh_pct_prem"].mean(),
    "t": -g["dh_pct_prem"].mean() / (g["dh_pct_prem"].std(ddof=1) / np.sqrt(len(g))),
    "win_%": 100 * (g["dh_pct_prem"] < 0).mean()}), include_groups=False).round(2).to_string())

print("\n--- SHORT NAKED straddle by era (% of premium) ---")
print(t.groupby("era", observed=True).apply(lambda g: pd.Series({
    "n": len(g), "mean_%": 100 * g["short_naked"].mean(),
    "t": g["short_naked"].mean() / (g["short_naked"].std(ddof=1) / np.sqrt(len(g))),
    "win_%": 100 * (g["short_naked"] > 0).mean(),
    "worst_%": 100 * g["short_naked"].min()}), include_groups=False).round(2).to_string())

t.to_parquet(f"/Users/sahilmajmudar/index-daytrading/data/opt_eod/{SYM}_hedged_{TARGET_DTE}.parquet")
print("\nsaved trade table")
