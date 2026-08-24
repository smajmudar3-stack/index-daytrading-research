"""0DTE SPX iron butterflies / condors on REAL quotes: management rules and regime conditioning.

Fixes two degeneracies present in the first pass:
  - condor short strikes could invert (delta-selected call strike below put strike) -> max loss
    exceeded the nominal width;
  - near-zero-risk rows (mid credit ~ wing width) made "% of capital at risk" explode.
Guards: kc >= kp + 0.001, and risk >= 0.25 * width. Headline P&L is also reported in
BASIS POINTS OF SPOT, which needs no denominator and cannot blow up.

Management is simulated on the SAME real 30-min quote grid: strikes are carried forward as FIXED
STRIKES (moneyness rescaled by S_entry/S_now), legs re-valued by linear interpolation of the real
mid grid, and the exit pays four more half-spreads.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

PATH = "/Users/sahilmajmudar/index-daytrading/data/spxw/data_opt.parquet"
ALLT = ["10:00:00", "10:30:00", "11:00:00", "11:30:00", "12:00:00", "12:30:00",
        "13:00:00", "13:30:00", "14:00:00", "14:30:00", "15:00:00", "15:30:00"]

df = pd.read_parquet(PATH, columns=["quote_date", "quote_time", "option_type", "mnes_rel",
                                    "mid", "bas", "delta", "implied_volatility", "sret",
                                    "active_underlying_price"])
df["t"] = df.quote_time.astype(str)
df = df[df.t.isin(ALLT) & (df.mid > 0) & (df.bas > 0)]


def wide(field, typ):
    return df[df.option_type == typ].pivot_table(index=["quote_date", "t"], columns="mnes_rel", values=field)


MID = {"C": wide("mid", "C"), "P": wide("mid", "P")}
BAS = {"C": wide("bas", "C"), "P": wide("bas", "P")}
DLT = {"C": wide("delta", "C"), "P": wide("delta", "P")}
SPOT = df.groupby(["quote_date", "t"]).active_underlying_price.first()
SRET = df.groupby(["quote_date", "t"]).sret.first()
IVATM = (df[np.isclose(df.mnes_rel, 1.0) & (df.option_type == "C")]
         .set_index(["quote_date", "t"]).implied_volatility)
GRID = np.array(MID["C"].columns, dtype=float)
DATES = MID["C"].index.get_level_values("quote_date").unique()

# per-time arrays keyed by date
def tarr(tbl, t):
    s = tbl.xs(t, level="t")
    return s.reindex(DATES)


MIDT = {(ty, t): tarr(MID[ty], t).values for ty in "CP" for t in ALLT}
BAST = {(ty, t): tarr(BAS[ty], t).values for ty in "CP" for t in ALLT}
DLTT = {(ty, t): tarr(DLT[ty], t).values for ty in "CP" for t in ALLT}
SPOTT = {t: SPOT.xs(t, level="t").reindex(DATES).values for t in ALLT}
SRETT = {t: SRET.xs(t, level="t").reindex(DATES).values for t in ALLT}
IVT = {t: IVATM.xs(t, level="t").reindex(DATES).values for t in ALLT}
N = len(DATES)


def interp_row(vals, targets):
    """Row-wise linear interpolation of a (N,41) grid at per-row target moneyness."""
    out = np.full(len(targets), np.nan)
    lo = np.clip(np.searchsorted(GRID, targets) - 1, 0, len(GRID) - 2)
    hi = lo + 1
    r = np.arange(len(targets))
    g0, g1 = GRID[lo], GRID[hi]
    v0, v1 = vals[r, lo], vals[r, hi]
    w = (targets - g0) / (g1 - g0)
    out = v0 + w * (v1 - v0)
    inside = (targets >= GRID[0]) & (targets <= GRID[-1])
    return np.where(inside, out, np.nan)


def build(entry_t, kind, wing, sdelta=None):
    """Open the structure at entry_t. Strikes returned as moneyness vs S(entry)."""
    bad_delta = np.zeros(N, bool)
    if kind == "fly":
        kc = np.full(N, 1.0); kp = np.full(N, 1.0)
    else:
        dc = DLTT[("C", entry_t)].copy(); dp = -DLTT[("P", entry_t)].copy()
        dc = np.where((dc > 0.01) & (dc < 0.99), dc, np.nan)
        dp = np.where((dp > 0.01) & (dp < 0.99), dp, np.nan)
        ec = np.abs(dc - sdelta); ep = np.abs(dp - sdelta)
        allc = np.all(~np.isfinite(ec), axis=1); allp = np.all(~np.isfinite(ep), axis=1)
        ec = np.where(np.isfinite(ec), ec, 9e9); ep = np.where(np.isfinite(ep), ep, 9e9)
        jc = np.argmin(ec, axis=1); jp = np.argmin(ep, axis=1)
        kc, kp = GRID[jc].copy(), GRID[jp].copy()
        kc[allc] = np.nan; kp[allp] = np.nan
        kc = np.where(np.isfinite(kc), kc, 1.02); kp = np.where(np.isfinite(kp), kp, 0.98)
        bad_delta = allc | allp
    kcl = np.round(kc + wing, 4); kpl = np.round(kp - wing, 4)
    r = np.arange(N)

    def snap(k):
        return np.clip(np.round((k - GRID[0]) / 0.001).astype(int), 0, 40)

    ic, ip, icl, ipl = snap(kc), snap(kp), snap(kcl), snap(kpl)
    mc = MIDT[("C", entry_t)][r, ic]; mp = MIDT[("P", entry_t)][r, ip]
    mcl = MIDT[("C", entry_t)][r, icl]; mpl = MIDT[("P", entry_t)][r, ipl]
    bc = BAST[("C", entry_t)][r, ic]; bp_ = BAST[("P", entry_t)][r, ip]
    bcl = BAST[("C", entry_t)][r, icl]; bpl = BAST[("P", entry_t)][r, ipl]
    kc, kp, kcl, kpl = GRID[ic], GRID[ip], GRID[icl], GRID[ipl]

    credit = (mc + mp) - (mcl + mpl)
    cost = 0.5 * (bc + bp_ + bcl + bpl)
    width = np.maximum(kcl - kc, kp - kpl)
    risk = width - credit
    inv = kc < kp - 1e-9 if kind == "condor" else np.zeros(N, bool)
    edge = (kcl > GRID[-1] + 1e-9) | (kpl < GRID[0] - 1e-9) | (np.round(kc + wing, 4) > GRID[-1]) | (np.round(kp - wing, 4) < GRID[0])
    ok = (np.isfinite(credit) & np.isfinite(cost) & (credit > 0) & (risk >= 0.25 * width)
          & ~inv & ~edge & ~bad_delta & np.isfinite(SRETT[entry_t]))
    return dict(kc=kc, kp=kp, kcl=kcl, kpl=kpl, credit=credit, cost=cost, width=width,
                risk=risk, ok=ok, iv=IVT[entry_t], sret=SRETT[entry_t], spot=SPOTT[entry_t])


def value_at(b, entry_t, t):
    """Structure mid value at a later time, expressed as a fraction of S(entry)."""
    s0, s1 = b["spot"], SPOTT[t]
    sc = s0 / s1                       # rescale strikes to the new moneyness base
    v = np.zeros(N)
    tot_bas = np.zeros(N)
    for leg, ty, sign in [("kc", "C", +1), ("kp", "P", +1), ("kcl", "C", -1), ("kpl", "P", -1)]:
        m = b[leg] * sc
        val = interp_row(MIDT[(ty, t)], m)
        bs = interp_row(BAST[(ty, t)], m)
        # outside the +-2% grid: deep ITM -> intrinsic, deep OTM -> ~0
        intr = np.maximum(0, 1 - m) if ty == "C" else np.maximum(0, m - 1)
        val = np.where(np.isfinite(val), val, intr)
        bs = np.where(np.isfinite(bs), bs, 0.0)
        v += sign * val
        tot_bas += bs
    return v * (s1 / s0), tot_bas * (s1 / s0)


def settle(b):
    s = b["sret"]
    return (np.maximum(0, s - b["kc"]) + np.maximum(0, b["kp"] - s)
            - np.maximum(0, s - b["kcl"]) - np.maximum(0, b["kpl"] - s))


def simulate(entry_t, kind, wing, sdelta=None, pt=None, stop_mult=None):
    """pt = take profit at pt fraction of the credit captured. stop_mult = close when the
    structure's mid value reaches stop_mult x credit. Both cost 4 extra half-spreads."""
    b = build(entry_t, kind, wing, sdelta)
    later = [t for t in ALLT if t > entry_t]
    pnl = np.full(N, np.nan)
    closed = np.zeros(N, bool)
    for t in later:
        v, bs = value_at(b, entry_t, t)
        exit_cost = 0.5 * bs
        hit_pt = (v <= (1 - pt) * b["credit"]) if pt is not None else np.zeros(N, bool)
        hit_sl = (v >= stop_mult * b["credit"]) if stop_mult is not None else np.zeros(N, bool)
        trig = (~closed) & np.isfinite(v) & (hit_pt | hit_sl)
        pnl = np.where(trig, b["credit"] - b["cost"] - v - exit_cost, pnl)
        closed = closed | trig
    pay = settle(b)
    pnl = np.where(closed, pnl, b["credit"] - b["cost"] - pay)   # cash settled: no exit cost
    ok = b["ok"] & np.isfinite(pnl)
    return pd.DataFrame(dict(date=DATES, pnl=pnl, risk=b["risk"], credit=b["credit"],
                             cost=b["cost"], width=b["width"], iv=b["iv"],
                             closed=closed, sret=b["sret"]))[ok]


def summ(o, label):
    if len(o) < 50:
        return None
    bp = 1e4 * o.pnl
    rr = 100 * o.pnl / o.risk
    return dict(label=label, n=len(o), credit_bp=round(1e4 * o.credit.mean(), 1),
                cost_bp=round(1e4 * o.cost.mean(), 2),
                cost_pct_credit=round(100 * (o.cost / o.credit).median(), 1),
                win=round(100 * (o.pnl > 0).mean(), 1),
                bp=round(bp.mean(), 2), t=round(st.ttest_1samp(bp, 0).statistic, 2),
                pct_risk=round(rr.mean(), 2), worst_bp=round(bp.min(), 1),
                pct_closed=round(100 * o.closed.mean(), 0))


pd.set_option("display.width", 260)

print("=" * 100)
print("A. HOLD-TO-SETTLEMENT, clean guards. P&L in bp of SPOT (net of 4 half-spreads at entry).")
print("=" * 100)
rows = []
for t in ["10:00:00", "10:30:00", "11:00:00", "12:00:00", "13:00:00", "14:00:00"]:
    for w in [0.005, 0.010, 0.020]:
        o = simulate(t, "fly", w)
        s = summ(o, f"FLY {t[:5]} w={w*100:.1f}%")
        if s:
            rows.append(s)
    for sd in [0.10, 0.16, 0.30]:
        o = simulate(t, "condor", 0.010, sdelta=sd)
        s = summ(o, f"CND {t[:5]} d={sd} w=1.0%")
        if s:
            rows.append(s)
print(pd.DataFrame(rows).to_string(index=False))

print("\n" + "=" * 100)
print("B. MANAGEMENT RULES, real quotes. 11:00 entry. Profit target / stop pay 4 more half-spreads.")
print("=" * 100)
rows = []
for kind, wing, sd, nm in [("fly", 0.010, None, "FLY w=1.0%"), ("fly", 0.020, None, "FLY w=2.0%"),
                           ("condor", 0.010, 0.16, "CND d=.16"), ("condor", 0.010, 0.30, "CND d=.30")]:
    for pt, sl, lbl in [(None, None, "hold to expiry"), (0.25, None, "PT 25%"), (0.50, None, "PT 50%"),
                        (None, 2.0, "stop 2x credit"), (0.50, 2.0, "PT50 + stop2x"),
                        (0.25, 2.0, "PT25 + stop2x")]:
        o = simulate("11:00:00", kind, wing, sdelta=sd, pt=pt, stop_mult=sl)
        s = summ(o, f"{nm} | {lbl}")
        if s:
            rows.append(s)
print(pd.DataFrame(rows).to_string(index=False))

print("\n" + "=" * 100)
print("C. REGIME CONDITIONING on entry ATM IV quintile (IV rank proxy), 11:00, hold to settlement")
print("=" * 100)
for kind, wing, sd, nm in [("fly", 0.010, None, "FLY w=1.0%"), ("condor", 0.010, 0.16, "CND d=.16")]:
    o = simulate("11:00:00", kind, wing, sdelta=sd)
    o = o.assign(q=pd.qcut(o.iv, 5, labels=[1, 2, 3, 4, 5]))
    g = o.groupby("q", observed=True).apply(
        lambda x: pd.Series(dict(n=len(x), iv=round(x.iv.mean(), 3),
                                 credit_bp=round(1e4 * x.credit.mean(), 1),
                                 win=round(100 * (x.pnl > 0).mean(), 1),
                                 bp=round(1e4 * x.pnl.mean(), 2),
                                 t=round(st.ttest_1samp(1e4 * x.pnl, 0).statistic, 2))), include_groups=False)
    print(f"\n{nm}\n{g.to_string()}")

print("\n" + "=" * 100)
print("D. TAIL: worst 15 sessions, 11:00 iron butterfly w=1.0%  (P&L in % of capital at risk)")
print("=" * 100)
o = simulate("11:00:00", "fly", 0.010)
o = o.assign(pct_risk=100 * o.pnl / o.risk, move_pct=100 * (o.sret - 1))
print(o.nsmallest(15, "pct_risk")[["date", "move_pct", "credit", "risk", "pct_risk"]]
      .assign(credit_bp=lambda x: (1e4 * x.credit).round(1), risk_bp=lambda x: (1e4 * x.risk).round(1))
      .drop(columns=["credit", "risk"]).round(2).to_string(index=False))
print("\nby calendar year (11:00 fly w=1.0%, hold, net of entry spread):")
o2 = o.assign(yr=o.date.dt.year)
print(o2.groupby("yr").apply(lambda x: pd.Series(dict(
    n=len(x), win=round(100 * (x.pnl > 0).mean(), 1), bp=round(1e4 * x.pnl.mean(), 2),
    t=round(st.ttest_1samp(1e4 * x.pnl, 0).statistic, 2))), include_groups=False).to_string())
