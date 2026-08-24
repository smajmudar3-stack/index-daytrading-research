"""gex_regime.py — Does dealer gamma regime condition INTRADAY 0DTE behavior?

The rigorous prior work (marcusdrewry/gex-forward-returns) proved GEX does NOT predict
DIRECTION on daily forward returns. That's not the 0DTE question. The 0DTE question is a
REGIME question: does the gamma sign predict whether the index CHOPS (condor wins) or
TRENDS/EXPANDS (condor dies, long options / directional win) DURING the session?

Mechanism: dealers long gamma (GEX>0) sell rallies/buy dips -> pin/dampen -> chop.
Dealers short gamma (GEX<0) buy rallies/sell dips -> amplify -> trend + range expansion.

GEX is taken from the PRIOR close (lag 1) so every read is known before today's open = tradeable.
Tests, per regime bucket:
  - intraday range (high-low)/open                      -> vol forecast (report says this works)
  - |close-open|/open                                   -> trend vs chop
  - efficiency = |close-open| / (high-low)              -> 1=pure trend, 0=pure chop
  - iron-condor survival at +/-0.5/0.75/1.0% of open    -> the ACTUAL premium-selling win rate
  - abs move (for a long straddle / directional day)    -> the ACTUAL long-premium payoff proxy
No costs modeled on the condor "win rate" (it's a hit-rate, not P&L) — read direction+robustness.
"""
import numpy as np
import pandas as pd
import yfinance as yf

G = pd.read_csv("data/squeeze_dix_gex.csv", parse_dates=["date"]).sort_values("date")
# SPY daily OHLC — within-day ratios are adjustment-invariant, so auto_adjust is irrelevant here
spy = yf.download("SPY", start="2011-05-01", interval="1d", progress=False,
                  auto_adjust=True, multi_level_index=False).rename(columns=str.lower)
spy = spy.reset_index().rename(columns={"Date": "date", "index": "date"})
spy["date"] = pd.to_datetime(spy["date"]).dt.tz_localize(None)

df = spy.merge(G[["date", "gex", "dix"]], on="date", how="inner").sort_values("date").reset_index(drop=True)

# --- regime from PRIOR close (lag 1) => tradeable at today's open, zero look-ahead ---
df["gex_prev"] = df["gex"].shift(1)
df["gex_z"] = (df["gex_prev"] - df["gex_prev"].rolling(252, min_periods=60).mean()) \
              / df["gex_prev"].rolling(252, min_periods=60).std()          # past-only z
df["neg_gamma"] = df["gex_prev"] < 0                                        # the mechanically special line

# --- intraday character (all within-day, adjustment-invariant) ---
df["rng"] = (df["high"] - df["low"]) / df["open"]                           # range
df["oc"] = (df["close"] - df["open"]).abs() / df["open"]                    # |open->close|
df["eff"] = np.where(df["high"] > df["low"], (df["close"] - df["open"]).abs() / (df["high"] - df["low"]), np.nan)

def condor_survives(row, w):
    """At-open 0DTE iron condor with short strikes at +/-w of the open, held to close (no stop).
    Wins iff the day's HIGH and LOW both stayed inside the short strikes."""
    up = row["open"] * (1 + w); dn = row["open"] * (1 - w)
    return (row["high"] < up) and (row["low"] > dn)

for w in (0.005, 0.0075, 0.010):
    df[f"cond_{int(w*10000)}"] = df.apply(lambda r: condor_survives(r, w), axis=1)

d = df.dropna(subset=["gex_z", "rng", "eff"]).copy()
print(f"sample: {len(d)} days, {d.date.min().date()} -> {d.date.max().date()}")
print(f"negative-gamma days (prior close): {d['neg_gamma'].sum()} ({d['neg_gamma'].mean()*100:.1f}%)\n")

def welch(a, b):
    from scipy import stats
    t, p = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
    return t, p

# ===== 1) GEX SIGN: positive gamma (pin) vs negative gamma (unleash) =====
pos = d[~d["neg_gamma"]]; neg = d[d["neg_gamma"]]
print("═══ 1. GEX SIGN — positive gamma (pin) vs negative gamma (amplify) ═══")
print(f"{'metric':<26}{'POS gamma':>12}{'NEG gamma':>12}{'Welch t':>10}{'p':>9}")
for lab, col in [("intraday range %", "rng"), ("|open->close| %", "oc"), ("efficiency (trend)", "eff")]:
    mp, mn = pos[col].mean(), neg[col].mean()
    t, p = welch(pos[col].dropna(), neg[col].dropna())
    sc = 100 if col != "eff" else 1
    print(f"{lab:<26}{mp*sc:>11.3f}{'%' if sc==100 else '':<1}{mn*sc:>11.3f}{'%' if sc==100 else '':<1}{t:>10.2f}{p:>9.4f}")
print("  condor survival-to-close (higher = premium-selling wins more):")
for w in (0.005, 0.0075, 0.010):
    c = f"cond_{int(w*10000)}"
    print(f"    +/-{w*100:.2f}% condor:   POS {pos[c].mean()*100:>5.1f}% win   NEG {neg[c].mean()*100:>5.1f}% win"
          f"   (gap {(pos[c].mean()-neg[c].mean())*100:+.1f}pp)")

# ===== 2) GEX QUINTILES (z-score) — is it monotone? =====
print("\n═══ 2. GEX z-score QUINTILES (Q1=lowest gamma ... Q5=highest) ═══")
d["q"] = pd.qcut(d["gex_z"], 5, labels=[1, 2, 3, 4, 5])
tab = d.groupby("q", observed=True).agg(n=("rng", "size"), range_pct=("rng", "mean"),
        oc_pct=("oc", "mean"), eff=("eff", "mean"),
        cond50=("cond_50", "mean"), cond75=("cond_75", "mean"), cond100=("cond_100", "mean"))
tab["range_pct"] *= 100; tab["oc_pct"] *= 100
tab[["cond50", "cond75", "cond100"]] *= 100
print(tab.round(2).to_string())

# ===== 3) recent 0DTE era only (2022+) — where the report said effects may be stronger =====
print("\n═══ 3. 2022+ 0DTE era only (SIGN test) ═══")
r = d[d.date >= "2022-01-01"]
rp, rn = r[~r["neg_gamma"]], r[r["neg_gamma"]]
print(f"  n: {len(rp)} pos / {len(rn)} neg")
for w in (0.005, 0.0075, 0.010):
    c = f"cond_{int(w*10000)}"
    t, p = welch(rp[c].astype(float), rn[c].astype(float))
    print(f"    +/-{w*100:.2f}% condor:   POS {rp[c].mean()*100:>5.1f}%   NEG {rn[c].mean()*100:>5.1f}%   (t {t:+.2f}, p {p:.3f})")
t, p = welch(rp["rng"], rn["rng"])
print(f"    intraday range:    POS {rp['rng'].mean()*100:.2f}%   NEG {rn['rng'].mean()*100:.2f}%   (t {t:+.2f}, p {p:.3f})")

d.to_csv("data/gex_regime_daily.csv", index=False)
print("\nwrote data/gex_regime_daily.csv")
