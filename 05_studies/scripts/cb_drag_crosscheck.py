"""Independent cross-check of the 8-crossing spread drag, expressed as % of CAPITAL AT RISK.

The coordinator's own SPY run (entries at ask, exits at bid = FULL spread on every leg, both
ways) puts the drag at ~10% of capital at risk, where capital = width - credit. This script
reproduces that denominator on two independent datasets and both fill conventions:

  half-spread convention : 0.5 * (ask-bid) per leg  -> 8 half-spreads round trip
  full-spread convention : (ask-bid) per leg        -> 8 full spreads round trip  (= coordinator's)

so the two studies can be compared like for like.
"""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

pd.set_option("display.width", 200)

# ---------------------------------------------------------------- 0DTE SPX
SPXW = "/Users/sahilmajmudar/index-daytrading/data/spxw/data_opt.parquet"
df = pd.read_parquet(SPXW, columns=["quote_date", "quote_time", "option_type", "mnes_rel",
                                    "mid", "bas", "delta"])
df["t"] = df.quote_time.astype(str)
df = df[(df.mid > 0) & (df.bas > 0)]
MID = {ty: df[df.option_type == ty].pivot_table(index=["quote_date", "t"], columns="mnes_rel", values="mid") for ty in "CP"}
BAS = {ty: df[df.option_type == ty].pivot_table(index=["quote_date", "t"], columns="mnes_rel", values="bas") for ty in "CP"}
DLT = {ty: df[df.option_type == ty].pivot_table(index=["quote_date", "t"], columns="mnes_rel", values="delta") for ty in "CP"}
G = np.array(MID["C"].columns, dtype=float)
idx = MID["C"].index


def spx_cell(t, kind, wing, sd=None):
    m = idx.get_level_values("t") == t
    r = np.where(m)[0]
    if kind == "fly":
        jc = jp = np.full(len(r), int(np.argmin(np.abs(G - 1.0))))
    else:
        dc = DLT["C"].values[r]; dp = -DLT["P"].values[r]
        dc = np.where((dc > .01) & (dc < .99), dc, 9e9); dp = np.where((dp > .01) & (dp < .99), dp, 9e9)
        jc = np.argmin(np.abs(dc - sd), axis=1); jp = np.argmin(np.abs(dp - sd), axis=1)
    kc, kp = G[jc], G[jp]
    jcl = np.clip(jc + int(round(wing / 0.001)), 0, 40)
    jpl = np.clip(jp - int(round(wing / 0.001)), 0, 40)
    a = np.arange(len(r))
    mc = MID["C"].values[r][a, jc]; mp = MID["P"].values[r][a, jp]
    mcl = MID["C"].values[r][a, jcl]; mpl = MID["P"].values[r][a, jpl]
    bs = (BAS["C"].values[r][a, jc] + BAS["P"].values[r][a, jp]
          + BAS["C"].values[r][a, jcl] + BAS["P"].values[r][a, jpl])
    credit = (mc + mp) - (mcl + mpl)
    width = np.maximum(G[jcl] - kc, kp - G[jpl])
    risk = width - credit
    ok = np.isfinite(credit) & (credit > 0) & (risk >= 0.25 * width) & np.isfinite(bs) & (kc >= kp)
    credit, risk, bs, width = credit[ok], risk[ok], bs[ok], width[ok]
    return dict(n=len(credit), credit_pct_width=100 * np.median(credit / width),
                half_rt_pct_credit=100 * np.median(bs / credit),
                full_rt_pct_credit=100 * np.median(2 * bs / credit),
                half_rt_pct_RISK=100 * np.median(bs / risk),
                FULL_rt_pct_RISK=100 * np.median(2 * bs / risk))


rows = []
for t in ["10:00:00", "11:00:00", "12:00:00", "14:00:00"]:
    for lbl, kind, wing, sd in [("fly w=0.5%", "fly", 0.005, None), ("fly w=1.0%", "fly", 0.010, None),
                                ("fly w=2.0%", "fly", 0.020, None),
                                ("condor 30d w=1%", "condor", 0.010, 0.30),
                                ("condor 16d w=1%", "condor", 0.010, 0.16),
                                ("condor 10d w=1%", "condor", 0.010, 0.10)]:
        rows.append(dict(entry=t[:5], structure=lbl, **spx_cell(t, kind, wing, sd)))
print("=" * 105)
print("SPX 0DTE (real SPXW quotes): round-trip 8-crossing drag, both fill conventions")
print("half = 0.5*(ask-bid)/leg   FULL = (ask-bid)/leg  [= entries at ask, exits at bid]")
print("=" * 105)
print(pd.DataFrame(rows).round(2).to_string(index=False))

# ---------------------------------------------------------------- SPY weekly / monthly
OPT = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_options.parquet"
UND = "/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_underlying.parquet"
und = pd.read_parquet(UND)
und["date"] = pd.to_datetime(und["date"])
close = und.set_index("date").sort_index()["close"]
f = pq.ParquetFile(OPT)
parts = []
for i in range(f.metadata.num_row_groups):
    t = f.read_row_group(i, columns=["expiration", "strike", "type", "bid", "ask", "delta", "date"]).to_pandas()
    t["dte"] = (t.expiration - t.date).dt.days
    parts.append(t[(t.dte >= 5) & (t.dte <= 40) & (t.bid > 0) & (t.ask > t.bid)])
o = pd.concat(parts, ignore_index=True)
del parts
o["mid"] = .5 * (o.bid + o.ask); o["sp"] = o.ask - o.bid; o["ad"] = o.delta.abs()
o["S"] = close.reindex(o.date).values
o = o.dropna(subset=["S"])

rows = []
for tag, lo, hi in [("weekly 5-10d", 5, 10), ("monthly 25-40d", 25, 40)]:
    sub = o[(o.dte >= lo) & (o.dte <= hi)]
    for sd, wp, lbl in [(0.10, 0.04, "10d w=4%"), (0.16, 0.04, "16d w=4%"),
                        (0.16, 0.02, "16d w=2%"), (0.30, 0.04, "30d w=4%"),
                        (None, 0.04, "IRON FLY w=4%")]:
        acc = []
        for (dt, exp), g in sub.groupby(["date", "expiration"], sort=False):
            S = g.S.iloc[0]; w = wp * S
            c = g[g.type == "call"]; p = g[g.type == "put"]
            if len(c) < 4 or len(p) < 4:
                continue
            if sd is None:
                sc = c.loc[(c.strike - S).abs().idxmin()]; sp_ = p.loc[(p.strike - S).abs().idxmin()]
            else:
                sc = c.loc[(c.ad - sd).abs().idxmin()]; sp_ = p.loc[(p.ad - sd).abs().idxmin()]
            if sc.strike < sp_.strike:
                continue
            lc = c.loc[(c.strike - (sc.strike + w)).abs().idxmin()]
            lp = p.loc[(p.strike - (sp_.strike - w)).abs().idxmin()]
            if lc.strike <= sc.strike or lp.strike >= sp_.strike:
                continue
            cr = (sc.mid + sp_.mid) - (lc.mid + lp.mid)
            spr = sc.sp + sp_.sp + lc.sp + lp.sp
            wd = max(lc.strike - sc.strike, sp_.strike - lp.strike)
            rk = wd - cr
            if cr <= 0 or rk <= 0.15 * wd:
                continue
            acc.append((cr, spr, wd, rk))
        if len(acc) < 100:
            continue
        A = np.array(acc)
        cr, spr, wd, rk = A[:, 0], A[:, 1], A[:, 2], A[:, 3]
        rows.append(dict(tenor=tag, structure=lbl, n=len(A),
                         credit_pct_width=round(100 * np.median(cr / wd), 2),
                         half_rt_pct_credit=round(100 * np.median(spr / cr), 2),
                         full_rt_pct_credit=round(100 * np.median(2 * spr / cr), 2),
                         half_rt_pct_RISK=round(100 * np.median(spr / rk), 2),
                         FULL_rt_pct_RISK=round(100 * np.median(2 * spr / rk), 2)))
print("\n" + "=" * 105)
print("SPY (real EOD bid/ask): round-trip 8-crossing drag, both fill conventions")
print("=" * 105)
print(pd.DataFrame(rows).to_string(index=False))
