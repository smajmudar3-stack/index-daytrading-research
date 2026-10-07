"""memecoin_pumpfun_score.py — every pump.fun mint at BIRTH, scored: do the factors visible in
the first minute (the dev's own first buy, the creator's history, socials, replies, the
curve's fill rate) separate the few that graduate or pay from the mass that die? Reads
`04_live_system/pumpfun_recorder.py` (curve state read from the Solana RPC at +1, +2, +3,
+5, +10, +15, +30 min, +1, +2, +6, +12, +24 h) joined to `pumpfun_trades_recorder.py`
(the create event: the dev's first buy in SOL).

ENTRY is the +1-minute mark: the first moment a retail wallet that is not in the creation
block can act. Price is the curve's own: vSOL / vTokens. Exits at +5, +10, +30, +60 min
and +6 h. COST on the curve is exact, not assumed: a buy of X SOL into virtual reserves
(vSol, vTok) under constant product fills at an average price of vSol·(1 + X/vSol)/vTok
... i.e. the trader's own order moves the price by X/vSol on the way in and again on the
way out, plus pump.fun's 1% each way and the 0.5% router. At $100 (~0.8 SOL at $120) into
a fresh curve of ~30 vSOL that is ~2.7% a side on impact alone; at $500 it is ~13%.
A mint whose curve returns no account at a mark (closed / migrated / rugged to zero on the
curve) is a −100% unless it `complete`d, in which case the last curve price is kept and
the row is flagged `graduated` (the post-migration path is PumpSwap's, measured elsewhere).

FACTORS at birth: dev_buy_sol (the creator's first buy), has_twitter / telegram / website,
desc_len, reply0, mcap0 (USD), seen_latency, creator_prior_mints / graduated / dead (as
this recorder has seen), fill1 (real SOL on the curve at +1 min: how fast money arrived),
r01 (+1→+2 min return: the first wave), reply1 (replies at +1 min if present).
Scored like every study here: fifths by factor, hit rate, payoff, IC, two halves, the
noise bar for the N cells run; then the trades the surviving cells imply, net of the exact
curve cost at $100 and $500; then P(graduate) by factor, since graduation is the only
'win' the literature measures at scale (0.2–0.6%).
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
FEE_SIDE = 0.015
SOL_USD_FALLBACK = 120.0
H = {"5m": 300, "10m": 600, "30m": 1800, "1h": 3600, "6h": 21600}
CAP = 20.0
N_TESTS = 0


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def load():
    c = sqlite3.connect(paths.state("pumpfun.db"))
    m = pd.read_sql("SELECT * FROM mints", c)
    k = pd.read_sql("SELECT mint, ts, age_s, price_sol, mcap_sol, vsol, rsol, complete, ds_price, ds_liq, buys_m5, sells_m5, vol_m5 FROM marks", c)
    c.close()
    try:
        c2 = sqlite3.connect(paths.state("pumpfun_trades.db"))
        cr = pd.read_sql("SELECT mint, initial_buy_sol, initial_buy_tokens FROM creates", c2)
        c2.close()
    except Exception:                                         # noqa: BLE001
        cr = pd.DataFrame(columns=["mint", "initial_buy_sol", "initial_buy_tokens"])
    return m, k, cr


def nearest_mark(g, age, tol):
    i = (g.age_s - age).abs().idxmin()
    r = g.loc[i]
    return r if abs(r.age_s - age) <= tol else None


def build(m, k, cr):
    rows = []
    kg = {mint: g.sort_values("age_s") for mint, g in k.groupby("mint")}
    cr = cr.drop_duplicates("mint").set_index("mint")
    for r in m.itertuples():
        g = kg.get(r.mint)
        if g is None or len(g) < 2:
            continue
        m1 = nearest_mark(g, 60, 45)
        if m1 is None or not m1.price_sol or m1.price_sol <= 0:
            continue
        p1 = m1.price_sol
        d = {"mint": r.mint, "created": r.created, "seen_latency": r.seen - r.created, "has_twitter": r.has_twitter,
             "has_telegram": r.has_telegram, "has_website": r.has_website, "n_socials": (r.has_twitter or 0) + (r.has_telegram or 0) + (r.has_website or 0),
             "desc_len": r.desc_len, "reply0": r.reply0, "mcap0": r.mcap0, "rsol0": (r.rsol0 or 0) / 1e9,
             "creator_prior_mints": r.creator_prior_mints, "creator_prior_graduated": r.creator_prior_graduated,
             "creator_prior_dead": r.creator_prior_dead, "sol_usd": r.sol_usd0 or SOL_USD_FALLBACK,
             "dev_buy_sol": cr.initial_buy_sol.get(r.mint, np.nan) if len(cr) else np.nan,
             "fill1": (m1.rsol or 0) / 1e9, "vsol1": (m1.vsol or 0) / 1e9, "p1": p1, "mcap1": m1.mcap_sol}
        m2 = nearest_mark(g, 120, 45)
        d["r01"] = (m2.price_sol / p1 - 1) if (m2 is not None and m2.price_sol) else np.nan
        d["p2"] = m2.price_sol if (m2 is not None and m2.price_sol) else np.nan
        d["vsol2"] = (m2.vsol or 0) / 1e9 if m2 is not None else np.nan
        d["fill_rate"] = ((m2.rsol or 0) / 1e9 - d["fill1"]) if m2 is not None else np.nan
        graduated = int((g.complete.fillna(0) > 0).any())
        d["graduated"] = graduated
        last_px = g.price_sol.dropna()
        last_px = last_px.iloc[-1] if len(last_px) else np.nan
        for lab, secs in H.items():
            mk = nearest_mark(g, secs, max(60, secs * 0.25))
            if mk is None:
                d[f"ret_{lab}"] = np.nan
            elif mk.price_sol and mk.price_sol > 0:
                d[f"ret_{lab}"] = mk.price_sol / p1 - 1
            else:
                d[f"ret_{lab}"] = (last_px / p1 - 1) if (graduated and last_px) else -1.0
        pk = g.price_sol.dropna()
        d["max_ret"] = (pk.max() / p1 - 1) if len(pk) else np.nan
        # returns from the +2 MINUTE price, for any rule whose signal is only known at +2
        # (trap 6: the first draft scored the "first wave" rule from the +1 price, which
        # includes the wave itself, and read +13% net; from +2 it is -45%)
        for lab, secs in H.items():
            if secs <= 120:
                continue
            mk = nearest_mark(g, secs, max(60, secs * 0.25))
            if d.get("p2") and mk is not None and mk.price_sol and mk.price_sol > 0:
                d[f"ret2_{lab}"] = mk.price_sol / d["p2"] - 1
            else:
                d[f"ret2_{lab}"] = np.nan
        rows.append(d)
    d = pd.DataFrame(rows)
    mid = d.created.min() + (d.created.max() - d.created.min()) / 2
    d["half"] = np.where(d.created < mid, "A", "B")
    d["dev_buy_usd"] = d.dev_buy_sol * d.sol_usd
    d["serial_creator"] = (d.creator_prior_mints >= 3).astype(float)
    d["first_launch"] = (d.creator_prior_mints == 0).astype(float)
    return d


def curve_cost(usd, vsol, sol_usd):
    """Round-trip cost fraction of a $usd order on a curve with vsol virtual SOL: impact
    both ways under constant product plus 1.5% a side."""
    x = usd / sol_usd
    imp = x / np.maximum(vsol, 1.0)
    return 1 - (1 - FEE_SIDE) ** 2 / ((1 + imp) ** 2)


def table(d, feats, ycol, label, min_n=200):
    global N_TESTS
    rows = []
    for f, sgn in feats:
        x = d[[f, ycol, "half"]].dropna()
        if len(x) < min_n or x[f].nunique() < 2:
            continue
        q = x[f] if x[f].nunique() <= 3 else pd.qcut(x[f].rank(method="first"), 5, labels=False, duplicates="drop")
        top = x[q == q.max()] if sgn > 0 else x[q == q.min()]
        bot = x[q == q.min()] if sgn > 0 else x[q == q.max()]
        yt = top[ycol].clip(upper=CAP)
        win, loss = yt[yt > 0], yt[yt <= 0]
        ic = stats.spearmanr(x[f] * sgn, x[ycol])[0]
        rows.append({"factor": f, "sign": "+" if sgn > 0 else "-", "n": len(x), "IC": ic, "t": ic * np.sqrt(len(x)), "top_hit": (yt > 0).mean(),
                     "top_med%": top[ycol].median() * 100, "top_mean%": yt.mean() * 100,
                     "payoff": (win.mean() / -loss.mean()) if len(loss) and loss.mean() < 0 else np.nan,
                     "top_dead%": (top[ycol] <= -0.999).mean() * 100, "bot_med%": bot[ycol].median() * 100,
                     "A": top[top.half == "A"][ycol].clip(upper=CAP).mean() * 100, "B": top[top.half == "B"][ycol].clip(upper=CAP).mean() * 100})
        N_TESTS += 1
    tb = pd.DataFrame(rows).sort_values("t", ascending=False)
    print(f"\n  {label} -> {ycol}  (top = best fifth by expected sign; means capped at {CAP:.0f}x; A/B = halves of the day)")
    print("  " + tb.to_string(index=False, float_format=lambda v: f"{v:8.2f}").replace("\n", "\n  "))
    return tb


def trade(d, mask, ycol, label, usd=100.0):
    s = d[mask].dropna(subset=[ycol, "vsol1"])
    if len(s) < 50:
        print(f"   {label:70s} n {len(s):5d} too few")
        return
    g = s[ycol].clip(upper=CAP)
    cost = curve_cost(usd, s.vsol1.values, s.sol_usd.values)
    net = pd.Series(np.where(g <= -0.999, -1.0, (1 + g) * (1 - cost) - 1), index=s.index)
    win, loss = net[net > 0], net[net <= 0]
    print(f"   {label:70s} n {len(s):5d} gross med {g.median()*100:+6.1f}% mean {g.mean()*100:+6.1f}% | net mean {net.mean()*100:+6.1f}% hit {(net>0).mean():.2f} "
          f"payoff {(win.mean()/-loss.mean()) if len(loss) else np.nan:4.2f} dead {(g<=-0.999).mean()*100:4.1f}% grad {s.graduated.mean()*100:4.1f}% | A {net[s.half=='A'].mean()*100:+6.1f}% B {net[s.half=='B'].mean()*100:+6.1f}%")


def main():
    pd.set_option("display.width", 250)
    m, k, cr = load()
    d = build(m, k, cr)
    d.to_parquet(os.path.join(paths.DATA_ROOT, "pumpfun_birth_panel.parquet"), index=False)
    print(f"{len(d):,} mints with a +1-minute curve price (of {len(m):,} recorded; seen {d.seen_latency.median():.0f} s after creation); "
          f"dev first buy known for {d.dev_buy_sol.notna().mean()*100:.0f}%; graduated {d.graduated.mean()*100:.2f}%; "
          f"creator seen before: {(d.creator_prior_mints>0).mean()*100:.0f}%; any social {(d.n_socials>0).mean()*100:.0f}%")
    print("\nBASE RATES from the +1-minute curve price (medians uncapped, means capped):")
    for lab in H:
        y = d[f"ret_{lab}"].dropna()
        if len(y):
            print(f"   {lab:4s} n {len(y):5d} median {y.median()*100:+6.1f}% mean {y.clip(upper=CAP).mean()*100:+6.1f}% up {(y>0).mean()*100:4.1f}% "
                  f"doubled {(y>=1).mean()*100:4.1f}% 5x {(y>=4).mean()*100:4.1f}% dead {(y<=-0.999).mean()*100:4.1f}%")
    print(f"   best curve price ever reached vs +1 min: median {d.max_ret.median()*100:+.0f}%, 75th pct {d.max_ret.quantile(.75)*100:+.0f}%, 95th {d.max_ret.quantile(.95)*100:+.0f}%")
    F = [("dev_buy_sol", -1), ("dev_buy_usd", -1), ("has_twitter", +1), ("has_telegram", +1), ("has_website", +1), ("n_socials", +1),
         ("desc_len", +1), ("reply0", +1), ("mcap0", +1), ("fill1", +1), ("fill_rate", +1), ("r01", +1), ("seen_latency", -1),
         ("creator_prior_mints", -1), ("serial_creator", -1), ("first_launch", +1), ("creator_prior_graduated", +1), ("creator_prior_dead", -1)]
    for lab in ("10m", "30m", "1h", "6h"):
        table(d, F, f"ret_{lab}", "BIRTH factors")
    table(d, F, "graduated", "BIRTH factors -> P(graduate)", min_n=500)
    print("\nTRADES from the +1-minute price, exact curve impact + 1.5%/side, $100 then $500:")
    for usd in (100.0, 500.0):
        print(f"\n  ${usd:.0f}")
        for lab in ("10m", "30m", "1h"):
            y = f"ret_{lab}"
            trade(d, d.index == d.index, y, f"every mint, sell at {lab}", usd)
            trade(d, d.first_launch == 1, y, f"creator's FIRST launch only, sell at {lab}", usd)
            trade(d, d.creator_prior_mints >= 3, y, f"serial creator (>=3 prior), sell at {lab}", usd)
            trade(d, (d.dev_buy_sol <= 1) & (d.dev_buy_sol > 0), y, f"dev first buy <= 1 SOL, sell at {lab}", usd)
            trade(d, d.dev_buy_sol > 4, y, f"dev first buy > 4 SOL (orcACR skips these), sell at {lab}", usd)
            trade(d, (d.first_launch == 1) & (d.dev_buy_sol <= 4) & (d.n_socials >= 1), y, f"orcACR-style: first launch, dev buy <= 4 SOL, a social, sell at {lab}", usd)
            trade(d, d.n_socials == 3, y, f"all three socials, sell at {lab}", usd)
            if f"ret2_{lab}" in d:
                trade(d.assign(vsol1=d.vsol2), d.r01 > 0.5, f"ret2_{lab}", f"first wave: +50% from +1 to +2 min, buy AT +2, sell at {lab}", usd)
            trade(d, d.fill1 >= 5, y, f">= 5 real SOL on the curve at +1 min, sell at {lab}", usd)
    print(f"\nCELLS SCORED: {N_TESTS}; noise bar for the largest |t| under the null ~ {np.sqrt(2*np.log(max(N_TESTS,2))):.1f}")


if __name__ == "__main__":
    main()
