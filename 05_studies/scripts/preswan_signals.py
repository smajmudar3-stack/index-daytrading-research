"""Do BIG MOVERS look different in the days BEFORE they move?

MRNA went +177% (37 sigma) with no warning in any screen I had. But n=1 proves
nothing, so this asks the question across every large move in the option data:

    Take every stock-day where the next 10 sessions contained a >=4 sigma move.
    Compare its option-market state BEFORE the move against a matched control
    of ordinary days. If the option market -- which sees order flow -- knows
    something, it shows up here.

Signals tested, all knowable before the event:
  IV_LEVEL   average IV across the chain vs that name's own trailing median
  IV_TREND   5-day change in average IV (is vol being bid UP into it?)
  SKEW       put IV minus call IV at matched moneyness (crash bid)
  OI_BUILD   total open interest vs its own trailing median (positioning)
  CALL_OI    call OI share (directional accumulation)
  SPREAD     average relative spread (dealers widening = they see risk)

The comparison is a LIFT ratio against the base rate, and a signal only counts
if it separates movers from non-movers by a meaningful margin. Reported with
the n on both sides so a thin cell cannot masquerade as a finding.
"""
import os, subprocess, warnings
from io import StringIO
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOLT = os.path.join(ROOT, "data", "dolt")


def q(sql, timeout=1800):
    r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"], cwd=DOLT,
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(r.stdout))


def main():
    print("Pulling daily option-market state per name ...", flush=True)
    # One row per ticker-day: the chain's aggregate state.
    st = q("""select act_symbol, `date`,
                     count(*) as n_contracts,
                     avg(vol) as iv,
                     sum(case when call_put='Call' then 1 else 0 end) as n_call,
                     avg(case when ask>0 and bid>0 then (ask-bid)/((ask+bid)/2) end) as spread
              from options.option_chain
              where `date` >= '2024-01-01' and vol is not null
              group by act_symbol, `date`""")
    if st.empty:
        print("no chain state"); return
    st["date"] = pd.to_datetime(st["date"])
    print(f"  {len(st):,} ticker-days of chain state")

    print("Pulling prices ...", flush=True)
    px = q("""select act_symbol, `date`, `close` from stocks.ohlcv
              where `date` >= '2023-10-01'""")
    px["date"] = pd.to_datetime(px["date"])
    print(f"  {len(px):,} price rows")

    rows = []
    for t, g in px.groupby("act_symbol"):
        g = g.sort_values("date")
        c = g["close"].astype(float)
        if len(c) < 200:
            continue
        r = c.pct_change(fill_method=None)
        # Split guard: unadjusted data + a 33%-duplicate split table means raw
        # returns contain fake -90% days. Treat >60% single-day as an action.
        r = r.mask(r.abs() > 0.60)
        sig = r.rolling(60).std()
        fwd = c.shift(-10) / c - 1
        fmax = c.rolling(10).max().shift(-10) / c - 1
        fmin = c.rolling(10).min().shift(-10) / c - 1
        move = pd.concat([fmax.abs(), fmin.abs()], axis=1).max(axis=1)
        rows.append(pd.DataFrame({"act_symbol": t, "date": g["date"].values,
                                  "sig": sig.values,
                                  "move_sig": (move / (sig * np.sqrt(10))).values}))
    mv = pd.concat(rows, ignore_index=True).dropna()

    d = st.merge(mv, on=["act_symbol", "date"], how="inner")
    d = d[np.isfinite(d.move_sig) & (d.iv > 0)]
    print(f"  {len(d):,} joined ticker-days\n")

    # Per-name normalisation: each metric vs that name's own trailing median,
    # so a permanently-high-IV biotech is not flagged simply for being biotech.
    d = d.sort_values(["act_symbol", "date"])
    gb = d.groupby("act_symbol")
    d["iv_rel"] = d.iv / gb.iv.transform(lambda s: s.rolling(60, min_periods=20).median())
    d["iv_trend"] = gb.iv.transform(lambda s: s.pct_change(5, fill_method=None))
    d["oi_rel"] = d.n_contracts / gb.n_contracts.transform(
        lambda s: s.rolling(60, min_periods=20).median())
    d["call_share"] = d.n_call / d.n_contracts
    d["spread_rel"] = d.spread / gb.spread.transform(
        lambda s: s.rolling(60, min_periods=20).median())
    d = d.dropna(subset=["iv_rel", "oi_rel"])

    BIG = 4
    base = (d.move_sig >= BIG).mean()
    print("=" * 92)
    print(f"DO BIG MOVERS LOOK DIFFERENT BEFOREHAND?  ({len(d):,} ticker-days)")
    print(f"  base rate P(>= {BIG} sigma move in next 10 sessions) = {base*100:.2f}%")
    print("=" * 92)
    print(f"  {'signal':34s} {'n':>8s} {'P(big)':>8s} {'lift':>7s}")

    tests = {
        "IV elevated >20% vs own median":  d.iv_rel > 1.20,
        "IV elevated >50% vs own median":  d.iv_rel > 1.50,
        "IV FALLING >10% over 5d":         d.iv_trend < -0.10,
        "IV RISING >10% over 5d":          d.iv_trend > 0.10,
        "IV rising >25% over 5d":          d.iv_trend > 0.25,
        "OI build >30% vs own median":     d.oi_rel > 1.30,
        "OI build >60% vs own median":     d.oi_rel > 1.60,
        "call share > 55%":                d.call_share > 0.55,
        "spreads widening >30%":           d.spread_rel > 1.30,
        "IV rising + OI building":         (d.iv_trend > 0.10) & (d.oi_rel > 1.30),
        "IV rising + calls stacked":       (d.iv_trend > 0.10) & (d.call_share > 0.55),
        "IV elevated + OI building":       (d.iv_rel > 1.20) & (d.oi_rel > 1.30),
    }
    out = []
    for name, m in tests.items():
        s = d[m.fillna(False)]
        if len(s) < 500:
            continue
        p = (s.move_sig >= BIG).mean()
        out.append((name, len(s), p, p / base))
    for name, n, p, lift in sorted(out, key=lambda x: -x[3]):
        print(f"  {name:34s} {n:8,d} {p*100:7.2f}% {lift:6.2f}x")


if __name__ == "__main__":
    main()
