"""Weekly SPY iron condors: NON-OVERLAPPING trades + real path-dependent management.

Fixes the independence problem in the first pass (7,977 overlapping trades on 4,514 dates ->
inflated t-stats) by taking ONE entry per calendar week. Management is priced by re-reading the
SAME four contracts (same strikes, same expiry) from the real EOD chain on each subsequent day,
and charging four more half-spreads on the exit.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats as st

OPT = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_options.parquet"
UND = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_underlying.parquet"
COLS = ["expiration", "strike", "type", "bid", "ask", "delta", "date", "implied_volatility"]

und = pd.read_parquet(UND)
und["date"] = pd.to_datetime(und["date"])
close = und.set_index("date").sort_index()["close"]

f = pq.ParquetFile(OPT)
parts = []
for i in range(f.metadata.num_row_groups):
    t = f.read_row_group(i, columns=COLS).to_pandas()
    t["dte"] = (t.expiration - t.date).dt.days
    parts.append(t[(t.dte >= 0) & (t.dte <= 45) & (t.bid > 0) & (t.ask > t.bid)])
opt = pd.concat(parts, ignore_index=True)
del parts
opt["mid"] = 0.5 * (opt.bid + opt.ask)
opt["half"] = 0.5 * (opt.ask - opt.bid)
opt["adelta"] = opt.delta.abs()
print("rows", len(opt))

# fast lookup: (date, expiration, type, strike) -> mid, half
opt = opt.sort_values(["date", "expiration", "type", "strike"])
LK = opt.set_index(["date", "expiration", "type", "strike"])[["mid", "half"]].sort_index()
LK = LK[~LK.index.duplicated()]
DATES = np.array(sorted(opt.date.unique()))


def chain(dt, dte_lo, dte_hi):
    g = opt[(opt.date == dt) & (opt.dte >= dte_lo) & (opt.dte <= dte_hi)]
    if len(g) == 0:
        return None, None
    exp = g.dte.sub(int(0.5 * (dte_lo + dte_hi))).abs().idxmin()
    e = g.loc[exp, "expiration"]
    return g[g.expiration == e], e


def run(sdelta, wing_pct, dte_lo=5, dte_hi=10, pt=None, sl=None, entry_dow=2):
    ent = [d for d in DATES if pd.Timestamp(d).dayofweek == entry_dow]
    out = []
    for dt in ent:
        dt = pd.Timestamp(dt)
        g, e = chain(dt, dte_lo, dte_hi)
        if g is None or len(g) < 8:
            continue
        S = close.get(dt, np.nan)
        if not np.isfinite(S):
            continue
        w = wing_pct * S
        c = g[g.type == "call"]; p = g[g.type == "put"]
        if len(c) < 4 or len(p) < 4:
            continue
        sc = c.loc[(c.adelta - sdelta).abs().idxmin()]
        sp = p.loc[(p.adelta - sdelta).abs().idxmin()]
        if sc.strike < sp.strike:
            continue
        lc = c.loc[(c.strike - (sc.strike + w)).abs().idxmin()]
        lp = p.loc[(p.strike - (sp.strike - w)).abs().idxmin()]
        if lc.strike <= sc.strike or lp.strike >= sp.strike:
            continue
        credit = (sc.mid + sp.mid) - (lc.mid + lp.mid)
        cost = sc.half + sp.half + lc.half + lp.half
        width = max(lc.strike - sc.strike, sp.strike - lp.strike)
        risk = width - credit
        if credit <= 0 or risk <= 0.15 * width:
            continue
        legs = [(e, "call", sc.strike, +1), (e, "put", sp.strike, +1),
                (e, "call", lc.strike, -1), (e, "put", lp.strike, -1)]
        # walk forward
        pnl, closed, exit_day = None, False, None
        path = DATES[(DATES > np.datetime64(dt)) & (DATES < np.datetime64(e))]
        if pt is not None or sl is not None:
            for d2 in path:
                v, hb, okv = 0.0, 0.0, True
                for (ee, ty, k, sg) in legs:
                    try:
                        r = LK.loc[(pd.Timestamp(d2), ee, ty, k)]
                    except KeyError:
                        okv = False
                        break
                    v += sg * r.mid
                    hb += r.half
                if not okv:
                    continue
                hit = ((pt is not None and v <= (1 - pt) * credit)
                       or (sl is not None and v >= sl * credit))
                if hit:
                    pnl = credit - cost - v - hb
                    closed, exit_day = True, pd.Timestamp(d2)
                    break
        if not closed:
            ST = close.get(pd.Timestamp(e), np.nan)
            if not np.isfinite(ST):
                continue
            pay = (max(0, ST - sc.strike) + max(0, sp.strike - ST)
                   - max(0, ST - lc.strike) - max(0, lp.strike - ST))
            itm = pay > 0
            pnl = credit - cost - pay - (cost if itm else 0.0)   # close only if it finished ITM
        out.append(dict(date=dt, exp=e, credit=credit, cost=cost, width=width, risk=risk,
                        pnl=pnl, r=100 * pnl / risk, closed=closed, iv=0.5 * (sc.implied_volatility + sp.implied_volatility)))
    return pd.DataFrame(out)


def summ(t, label):
    if len(t) < 40:
        return None
    return dict(label=label, n=len(t), cr_pct_w=round(100 * (t.credit / t.width).mean(), 1),
                cost_pct_cr=round(100 * (t.cost / t.credit).median(), 1),
                win=round(100 * (t.pnl > 0).mean(), 1), mean_r=round(t.r.mean(), 2),
                t=round(st.ttest_1samp(t.r, 0).statistic, 2),
                med=round(t.r.median(), 1), worst=round(t.r.min(), 0),
                sd=round(t.r.std(), 1), closed_early=round(100 * t.closed.mean(), 0))


pd.set_option("display.width", 240)
rows = []
tapes = {}
for sd, wp in [(0.10, 0.04), (0.16, 0.04), (0.16, 0.02), (0.30, 0.04)]:
    for pt, sl, lbl in [(None, None, "hold"), (0.50, None, "PT50"), (0.25, None, "PT25"),
                        (None, 2.0, "stop2x"), (0.50, 2.0, "PT50+stop2x")]:
        t = run(sd, wp, pt=pt, sl=sl)
        s = summ(t, f"WEEKLY d={sd} w={wp*100:.0f}% | {lbl}")
        if s:
            rows.append(s)
            tapes[(sd, wp, lbl)] = t
for sd, wp in [(0.10, 0.04), (0.16, 0.04)]:
    t = run(sd, wp, dte_lo=25, dte_hi=40)
    s = summ(t, f"MONTHLY d={sd} w={wp*100:.0f}% | hold")
    if s:
        rows.append(s)
        tapes[(sd, wp, "monthly")] = t
print("NON-OVERLAPPING (one Wednesday entry per week), SPY, real EOD bid/ask, 2008-2025")
print("mean_r = mean % of capital at risk per trade\n")
print(pd.DataFrame(rows).to_string(index=False))

t = tapes.get((0.10, 0.04, "hold"))
if t is not None:
    print("\n--- weekly 10-delta 4%-wing, hold: equity at 5% of account risked per trade ---")
    eq = (1 + 0.05 * t.r.values / 100).cumprod()
    yrs = (t.date.iloc[-1] - t.date.iloc[0]).days / 365.25
    print(f"n={len(t)} over {yrs:.1f}y  final={eq[-1]:.3f}  CAGR={100*(eq[-1]**(1/yrs)-1):.2f}%  "
          f"maxDD={100*(eq/np.maximum.accumulate(eq)-1).min():.1f}%  "
          f"Sharpe={t.r.mean()/t.r.std()*np.sqrt(52):.2f}")
    print("\nby year:")
    print(t.assign(yr=t.date.dt.year).groupby("yr").apply(lambda x: pd.Series(dict(
        n=len(x), win=round(100 * (x.pnl > 0).mean(), 1), mean_r=round(x.r.mean(), 2),
        sum_r=round(x.r.sum() / 100, 2))), include_groups=False).to_string())
