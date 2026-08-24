"""validate_condor_real.py — the condor edge, priced on REAL SPXW quotes instead of a model.

Every condor number quoted so far (+3.7%/trade, 91% win) came from Black-Scholes with a linear skew
approximation. The bot research found that approximation misprices the wings badly — model credit
9.08% of width against a market 5.77% — implying the true expectancy is nearer +1.2%. That was based
on a single live chain snapshot. This settles it on 1,919 sessions of real bid/ask.

Method: for each session, take the real quote grid at the entry time, place the short strikes at the
requested distance in real moneyness terms, read the actual mid and the actual bid-ask spread, and
settle against the real close. No option pricing model is used anywhere.
"""
import numpy as np
import pandas as pd
from scipy import stats as st

from idt import paths

PATH = "spxw/data_opt.parquet"  # path under DATA_ROOT, resolved at the read site


def load():
    df = pd.read_parquet(paths.require_data(PATH), columns=[
        "quote_date", "quote_time", "option_type", "mnes_rel", "mid", "bas",
        "active_underlying_price", "open_interest", "implied_volatility"])
    df["t"] = df.quote_time.astype(str)
    return df


def condor_day(day, entry_t, short_off, wing_off):
    """Build the condor from REAL quotes. short_off/wing_off are fractional moneyness offsets."""
    e = day[day.t == entry_t]
    if e.empty:
        return None
    spot = e.active_underlying_price.iloc[0]
    calls = e[e.option_type == "C"].set_index("mnes_rel").sort_index()
    puts = e[e.option_type == "P"].set_index("mnes_rel").sort_index()
    if calls.empty or puts.empty:
        return None

    def pick(tbl, target):
        if tbl.empty:
            return None
        i = np.argmin(np.abs(tbl.index.values - target))
        k = tbl.index.values[i]
        if abs(k - target) > 0.004:          # no strike near enough on this grid
            return None
        return k, tbl.iloc[i]

    sc = pick(calls, 1 + short_off)
    lc = pick(calls, 1 + short_off + wing_off)
    sp = pick(puts, 1 - short_off)
    lp = pick(puts, 1 - short_off - wing_off)
    if None in (sc, lc, sp, lp):
        return None
    legs = [sc, lc, sp, lp]
    if any(r[1].mid <= 0 for r in legs):
        return None
    # credit at the mid, minus half the real bid-ask on every leg (we cross to open)
    credit = (sc[1].mid + sp[1].mid) - (lc[1].mid + lp[1].mid)
    cost = sum(r[1].bas for r in legs) / 2.0
    credit_net = credit - cost
    width = max(lc[0] - sc[0], sp[0] - lp[0]) * spot     # in index points
    credit_pts = credit_net * spot
    if width <= 0 or credit_pts <= 0:
        return None
    # settle at the real 16:00 underlying
    fin = day[day.t == "16:00:00"]
    if fin.empty:
        return None
    S1 = fin.active_underlying_price.iloc[0]
    kc, kp = sc[0] * spot, sp[0] * spot
    breach = max(S1 - kc, 0) + max(kp - S1, 0)
    loss = min(breach, width)
    pnl = credit_pts - loss
    risk = width - credit_pts
    if risk <= 0:
        return None
    return dict(date=day.quote_date.iloc[0], ret=pnl / risk, credit_pct=credit_pts / width * 100,
                risk_pts=risk, spot=spot, S1=S1)


def run(entry_t="11:00:00", short_off=0.005, wing_off=0.005):
    df = load()
    out = []
    for date, day in df.groupby("quote_date"):
        r = condor_day(day, entry_t, short_off, wing_off)
        if r:
            out.append(r)
    t = pd.DataFrame(out)
    if t.empty:
        return t
    return t


def main():
    print("CONDOR ON REAL SPXW QUOTES — no pricing model anywhere\n")
    print(f"{'entry':>9}{'short':>8}{'wing':>7}{'n':>6}{'win%':>7}{'avg ret':>10}"
          f"{'credit%w':>10}{'t':>7}")
    print("-" * 64)
    best = None
    for entry_t in ("10:30:00", "11:00:00", "12:00:00", "13:00:00"):
        for so in (0.004, 0.005, 0.007):
            t = run(entry_t, so, 0.005)
            if t.empty or len(t) < 200:
                continue
            r = t.ret.values
            tt, _ = st.ttest_1samp(r, 0)
            print(f"{entry_t[:5]:>9}{so*100:>7.1f}%{0.5:>6.1f}%{len(r):>6}"
                  f"{(r>0).mean()*100:>6.0f}%{r.mean()*100:>+9.2f}%"
                  f"{t.credit_pct.mean():>9.1f}%{tt:>+7.2f}")
            if best is None or r.mean() > best[1].ret.mean():
                best = ((entry_t, so), t)
    if best is None:
        print("\nno viable configuration on the real grid")
        return
    (et, so), t = best
    t["yr"] = pd.to_datetime(t.date).dt.year
    print(f"\nBEST: entry {et[:5]}, shorts {so*100:.1f}% OTM")
    print("  year-by-year (real quotes):")
    for y, g in t.groupby("yr"):
        print(f"    {y}  n={len(g):4d}  win {(g.ret>0).mean()*100:3.0f}%  avg {g.ret.mean()*100:+6.2f}%")
    # honest sizing view
    t2 = t.copy(); t2["mo"] = pd.to_datetime(t2.date).dt.to_period("M")
    for rf in (0.05, 0.12):
        mo = t2.groupby("mo")["ret"].apply(lambda x: np.prod(1 + x * rf) - 1).values
        eq = np.cumprod(1 + mo); pk = np.maximum.accumulate(eq)
        yrs = len(mo) / 12
        print(f"  {rf*100:3.0f}% risk: monthly {mo.mean()*100:+.2f}% | CAGR "
              f"{((eq[-1])**(1/max(yrs,.1))-1)*100:+.1f}% | maxDD -{((pk-eq)/pk).max()*100:.0f}%")


if __name__ == "__main__":
    main()
