"""memecoin_factors.py — every factor the launch recorder captured, scored the way the
options and stock studies were: hit rate, payoff, decile spread, by horizon, in time splits,
with the noise bar stated, and then the trades the surviving factors imply at real cost.

Sholo (2026-10-06): "I've started trading memecoins on GMGN. Do the same testing for every
aspect, exactly like the options." Data: `04_live_system/memecoin_recorder.py`, every token
on DexScreener's launch feed since 2026-09-23 at the price a retail wallet first sees it,
re-priced every few minutes for a day (4,343 launches; Solana 92%).

FACTORS known at FIRST SIGHT (t0):
  liq0        liquidity (USD)                       age0      pair age at first sight (min)
  vol24_0     24h volume at first sight              v2l       vol24 / liquidity (turnover)
  chg_m5_0    DexScreener's 5-min change at t0       chg_h1_0  its 1-hour change at t0
  on_curve    still on the pump.fun bonding curve (dex == pumpfun) vs graduated
  chain       solana / bsc / ethereum / base
FACTORS known after the FIRST MARK (t1 ≈ 10–20 min, the recorder's cadence):
  r01         return t0 -> t1 (early momentum)        dliq01   liquidity change t0 -> t1
  dvol01      24h-volume change t0 -> t1              gone1    pair already unpriceable at t1
OUTCOMES: return from the signal's mark to the mark nearest +30m / +1h / +6h / +24h. A
return is measured from the mark AT WHICH the factor was known, never earlier (trap 6). A
pair with no price is a −100%. Returns are capped at +50x per token for the mean columns:
one token's 5,000x re-pricing (a DexScreener pair swap, not a trade anyone made) dominated
the uncapped mean; the median and the hit rate do not care.
COSTS: pump.fun / PumpSwap 1% each way, a 0.5% router fee, price impact order/(liq/2) each
way (constant product), and a slippage sweep 1–5%. Sized at $100 and $500 because the
median pool is $18k and impact is the whole story at $500.
SPLITS: weeks 1 and 2 of recording (A/B), and a noise bar sqrt(2 ln N) for the N
factor-horizon cells scored.
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402

warnings.filterwarnings("ignore")
H = {"30m": 1800, "1h": 3600, "6h": 21600, "24h": 86400}
CAP = 50.0
FEE = 0.01          # pump.fun / PumpSwap per side
ROUTER = 0.005      # GMGN / Jupiter style router fee per side
N_TESTS = 0


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def load():
    c = sqlite3.connect(paths.state("memecoins.db"))
    t = pd.read_sql("SELECT * FROM tokens", c)
    m = pd.read_sql("SELECT ts, chain, address, price, liq, vol24 FROM marks ORDER BY ts", c)
    c.close()
    return t, m


def nearest(mk, when, tol):
    """Price at the mark nearest `when` within tol seconds; -1 (gone) if the nearest mark has
    no price; NaN if no mark within tol."""
    i = np.searchsorted(mk.ts.values, when)
    cands = [j for j in (i - 1, i) if 0 <= j < len(mk)]
    if not cands:
        return np.nan, np.nan, np.nan
    j = min(cands, key=lambda k: abs(mk.ts.values[k] - when))
    if abs(mk.ts.values[j] - when) > tol:
        return np.nan, np.nan, np.nan
    row = mk.iloc[j]
    return (row.price if pd.notna(row.price) else -1.0), row.liq, row.vol24


def build(t, m):
    rows = []
    g = {k: v.reset_index(drop=True) for k, v in m.groupby(["chain", "address"])}
    for r in t.itertuples():
        mk = g.get((r.chain, r.address))
        if mk is None or len(mk) < 2:
            continue
        t0 = r.first_seen
        p0 = r.first_price
        if not p0 or p0 <= 0:
            continue
        # the first mark after t0 (the recorder's next pass)
        later = mk[mk.ts > t0 + 60]
        if later.empty:
            continue
        m1 = later.iloc[0]
        t1 = m1.ts
        p1 = m1.price if pd.notna(m1.price) else -1.0
        d = {"chain": r.chain, "address": r.address, "t0": t0, "dex": r.dex, "on_curve": int(r.dex == "pumpfun"),
             "liq0": r.first_liq, "vol24_0": r.first_vol24, "age0": (t0 - r.pair_created) / 60 if r.pair_created else np.nan,
             "v2l": r.first_vol24 / r.first_liq if r.first_liq else np.nan,
             "t1_min": (t1 - t0) / 60, "gone1": int(p1 < 0),
             "r01": (p1 / p0 - 1) if p1 > 0 else -1.0,
             "dliq01": (m1.liq / r.first_liq - 1) if (r.first_liq and pd.notna(m1.liq)) else np.nan,
             "dvol01": (m1.vol24 / r.first_vol24 - 1) if (r.first_vol24 and pd.notna(m1.vol24)) else np.nan}
        for lab, secs in H.items():
            pk, _, _ = nearest(mk, t0 + secs, max(600, secs * 0.25))
            d[f"ret0_{lab}"] = np.nan if np.isnan(pk) else (-1.0 if pk < 0 else pk / p0 - 1)
            pk1, _, _ = nearest(mk, t1 + secs, max(600, secs * 0.25))
            d[f"ret1_{lab}"] = np.nan if np.isnan(pk1) or p1 <= 0 else (-1.0 if pk1 < 0 else pk1 / p1 - 1)
        # the token's best and worst mark in the first 24h from t0 (what a perfect exit could get)
        w = mk[(mk.ts > t0) & (mk.ts <= t0 + 86400)]
        pr = w.price.dropna()
        d["max24"] = (pr.max() / p0 - 1) if len(pr) else np.nan
        d["min24"] = (pr.min() / p0 - 1) if len(pr) else -1.0
        rows.append(d)
    d = pd.DataFrame(rows)
    chg = m.sort_values("ts").groupby(["chain", "address"]).first()
    first = pd.read_sql("SELECT chain, address, chg_m5, chg_h1 FROM marks WHERE ts IN (SELECT MIN(ts) FROM marks GROUP BY chain, address)",
                        sqlite3.connect(paths.state("memecoins.db")))
    d = d.merge(first.drop_duplicates(["chain", "address"]).rename(columns={"chg_m5": "chg_m5_0", "chg_h1": "chg_h1_0"}),
                on=["chain", "address"], how="left")
    d["week"] = np.where(d.t0 < d.t0.min() + 7 * 86400, "A wk1", "B wk2")
    del chg
    return d


def capped(s):
    return s.clip(upper=CAP)


def table(d, feats, ycol, label, min_n=30):
    """Decile / bucket means of the forward return by factor, with hit rate and payoff."""
    global N_TESTS
    rows = []
    for f, sgn in feats:
        x = d[[f, ycol, "week"]].dropna()
        if len(x) < 200 or x[f].nunique() < 3:
            continue
        if x[f].nunique() <= 4:
            q = x[f]
        else:
            q = pd.qcut(x[f].rank(method="first"), 5, labels=False, duplicates="drop")
        top_lab, bot_lab = q.max(), q.min()
        top, bot = x[q == top_lab], x[q == bot_lab]
        if sgn < 0:
            top, bot = bot, top
        yt = capped(top[ycol])
        win, loss = yt[yt > 0], yt[yt <= 0]
        ic = stats.spearmanr(x[f] * sgn, x[ycol])[0]
        rows.append({"factor": f, "sign": "+" if sgn > 0 else "-", "n": len(x), "IC": ic, "t_ic": ic * np.sqrt(len(x)),
                     "top_hit": (yt > 0).mean(), "top_median%": top[ycol].median() * 100, "top_mean%": yt.mean() * 100,
                     "payoff": (win.mean() / -loss.mean()) if len(loss) and loss.mean() < 0 else np.nan,
                     "top_gone%": (top[ycol] <= -0.999).mean() * 100,
                     "bot_median%": bot[ycol].median() * 100, "spread_med%": (top[ycol].median() - bot[ycol].median()) * 100,
                     "A": capped(top[top.week == "A wk1"][ycol]).mean() * 100, "B": capped(top[top.week == "B wk2"][ycol]).mean() * 100})
        N_TESTS += 1
    tb = pd.DataFrame(rows).sort_values("t_ic", ascending=False)
    print(f"\n  {label} -> {ycol}   (top = best fifth by the factor's expected sign; mean columns capped at {CAP:.0f}x; A/B = recording weeks)")
    print("  " + tb.to_string(index=False, float_format=lambda v: f"{v:8.2f}").replace("\n", "\n  "))
    return tb


def strategy(d, mask, ycol, label, size=100.0, slip=0.02):
    """A rule that buys every token in `mask` at the signal's mark and sells at the horizon,
    net of fees, router, price impact at `size` both ways, and slippage both ways."""
    s = d[mask].dropna(subset=[ycol, "liq0"])
    if len(s) < 20:
        print(f"   {label:62s} n {len(s):4d}  too few")
        return
    gross = capped(s[ycol])
    liq = s.liq0.clip(lower=500)
    impact = size / (liq / 2)
    cost = 2 * (FEE + ROUTER + slip) + 2 * impact.clip(upper=0.5)
    net = (1 + gross) * (1 - cost) - 1
    net = net.where(gross > -0.999, -1.0)
    hit = (net > 0).mean()
    win, loss = net[net > 0], net[net <= 0]
    print(f"   {label:62s} n {len(s):4d}  gross median {gross.median()*100:+7.1f}%  mean {gross.mean()*100:+7.1f}%  | net mean {net.mean()*100:+7.1f}%  "
          f"hit {hit:.2f}  payoff {(win.mean()/-loss.mean()) if len(loss) else np.nan:5.2f}  gone {(gross<=-0.999).mean()*100:4.1f}%  "
          f"| A {net[s.week=='A wk1'].mean()*100:+6.1f}%  B {net[s.week=='B wk2'].mean()*100:+6.1f}%")


def main():
    pd.set_option("display.width", 250)
    t, m = load()
    d = build(t, m)
    d.to_parquet(os.path.join(paths.DATA_ROOT, "memecoin_factor_panel.parquet"), index=False)
    print(f"{len(d):,} launches with marks, {d.t0.min():.0f}..{d.t0.max():.0f}; on-curve {d.on_curve.mean()*100:.0f}%, "
          f"first mark after {d.t1_min.median():.0f} min (median), gone by first mark {d.gone1.mean()*100:.1f}%")
    print(f"median liq ${d.liq0.median():,.0f}; age at first sight median {d.age0.median():.0f} min; "
          f"best mark in 24h: median {d.max24.median()*100:+.0f}%, 25th pct {d.max24.quantile(.25)*100:+.0f}% (what a PERFECT exit could get)")
    print("\nBASE RATES from first sight (uncapped medians; capped means):")
    for lab in H:
        y = d[f"ret0_{lab}"].dropna()
        print(f"   {lab:4s} n {len(y):4d}  median {y.median()*100:+6.1f}%  mean(cap) {capped(y).mean()*100:+7.1f}%  "
              f"up {(y>0).mean()*100:4.1f}%  doubled {(y>=1).mean()*100:4.1f}%  5x {(y>=4).mean()*100:4.1f}%  down>50% {(y<-0.5).mean()*100:4.1f}%  gone {(y<=-0.999).mean()*100:4.1f}%")
    F0 = [("liq0", +1), ("vol24_0", +1), ("v2l", +1), ("age0", -1), ("chg_m5_0", +1), ("chg_h1_0", +1), ("on_curve", -1)]
    F1 = [("r01", +1), ("dliq01", +1), ("dvol01", +1), ("gone1", -1)]
    for lab in ("1h", "6h", "24h"):
        table(d, F0, f"ret0_{lab}", "FIRST-SIGHT factors")
    for lab in ("1h", "6h", "24h"):
        table(d[d.gone1 == 0], F1, f"ret1_{lab}", "EARLY-PATH factors (from the first mark, survivors only)")
    print(f"\nFACTOR CELLS SCORED: {N_TESTS}; noise bar for the largest |t| under the null ~ {np.sqrt(2*np.log(N_TESTS)):.1f}")

    print("\nTRADES, net of 1% + 0.5% each way, 2% slippage each way, and price impact at $100 (then $500):")
    for size in (100.0, 500.0):
        print(f"\n  size ${size:.0f}")
        for lab in ("30m", "1h", "6h", "24h"):
            strategy(d, d.index == d.index, f"ret0_{lab}", f"buy EVERY launch at first sight, sell at {lab}", size)
        for lab in ("1h", "6h"):
            strategy(d, d.liq0 >= 20000, f"ret0_{lab}", f"liquidity >= $20k only, sell at {lab}", size)
            strategy(d, d.on_curve == 0, f"ret0_{lab}", f"graduated (off the curve) only, sell at {lab}", size)
            strategy(d, (d.chg_m5_0 > 20), f"ret0_{lab}", f"already up >20% in the last 5 min at first sight, sell at {lab}", size)
            strategy(d, (d.v2l > d.v2l.quantile(.8)), f"ret0_{lab}", f"top-fifth turnover (vol/liq) at first sight, sell at {lab}", size)
            strategy(d[d.gone1 == 0], d[d.gone1 == 0].r01 > 0.3, f"ret1_{lab}", f"early momentum: up >30% by the first mark, buy THEN, sell at {lab}", size)
            strategy(d[d.gone1 == 0], d[d.gone1 == 0].r01 < -0.3, f"ret1_{lab}", f"dip: down >30% by the first mark, buy THEN, sell at {lab}", size)
            strategy(d[d.gone1 == 0], (d[d.gone1 == 0].dliq01 > 0.5) & (d[d.gone1 == 0].r01 > 0), f"ret1_{lab}", f"liquidity grew >50% AND price up by the first mark, sell at {lab}", size)
    print("\nSLIPPAGE SWEEP on the best-looking rule (liquidity >= $20k, sell at 1h, $100):")
    for slip in (0.0, 0.01, 0.02, 0.03, 0.05):
        strategy(d, d.liq0 >= 20000, "ret0_1h", f"  slippage {slip*100:.0f}% each way", 100.0, slip)
    # take-profit / stop sims need the path: use max24/min24 as bounds
    print("\nEXIT RULES, bounds from the 24h path (a take-profit at X is HIT if max24 >= X; a stop at -Y is hit if min24 <= -Y;")
    print("  when both are hit the stop is assumed first — the pessimistic order, since the recorder cannot see which came first):")
    for tp, sl in ((1.0, 0.5), (0.5, 0.3), (2.0, 0.5), (0.3, 0.2)):
        hit_tp = d.max24 >= tp
        hit_sl = d.min24 <= -sl
        ret = np.where(hit_sl, -sl, np.where(hit_tp, tp, d.ret0_24h.fillna(-1.0)))
        ret = pd.Series(ret, index=d.index)
        cost = 2 * (FEE + ROUTER + 0.02) + 2 * (100 / (d.liq0.clip(lower=500) / 2)).clip(upper=0.5)
        net = (1 + ret) * (1 - cost) - 1
        print(f"   take-profit +{tp*100:.0f}% / stop -{sl*100:.0f}%: tp hit {hit_tp.mean()*100:4.1f}%  stop hit {hit_sl.mean()*100:4.1f}%  "
              f"gross mean {ret.mean()*100:+6.1f}%  net mean (\\$100) {net.mean()*100:+6.1f}%  hit {(net>0).mean():.2f}")


if __name__ == "__main__":
    main()
