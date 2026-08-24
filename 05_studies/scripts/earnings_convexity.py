"""Buy convexity before a DATED catalyst — the one version of the idea with
literature behind it.

Gao, Xing & Zhang (JFQA 2018) find delta-neutral straddles earn +2.3% from one
day BEFORE an earnings announcement to the announcement date. The mechanism they
propose is that the market underestimates earnings uncertainty, so implied vol
is too low going in. That is exactly "a big move not priced in" -- except the
move has a KNOWN DATE, which is the part the quiet-stock screen was missing.

Data: DoltHub single-stock chains (real bid/ask + IV + greeks) joined to the
117k-event earnings calendar, both already local.

Design decisions that make this a fair test:

  * BOUGHT AT THE ASK, SOLD AT THE BID. Single-stock far-OTM spreads are wide
    (measured median 4.51%, worst 13.7%), and mid-price fills are what make
    every published version of this look better than it trades.
  * ENTRY the last snapshot BEFORE the announcement, EXIT the first snapshot
    after. For an "After market close" release the announcement date's session
    is still pre-event, so the exit is the NEXT session -- getting this backwards
    inverts the trade, and the `when` field is populated on only ~75% of events.
  * 2024-2026 ONLY. The chain cadence is ~3 snapshots/week before 2024 (only
    0.5% of pairs have a true D-1), so the paper's D-1 specification is simply
    not testable earlier. Reported separately rather than pooled.
  * Expiries must exist in BOTH snapshots -- they roll between dates.
"""
import subprocess
import warnings

import numpy as np
import pandas as pd

from idt import paths

warnings.filterwarnings("ignore")
DOLT = paths.data("dolt")
OUT = paths.data("earnings_convexity.parquet")


def q(sql):
    """Query the local Dolt clones. Run from the parent so all DBs mount."""
    r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"],
                       cwd=DOLT, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not r.stdout.strip():
        return pd.DataFrame()
    from io import StringIO
    return pd.read_csv(StringIO(r.stdout))


def main():
    print("=" * 96)
    print("EARNINGS CONVEXITY — buy the straddle into a dated catalyst")
    print("=" * 96)

    # Events with a known BMO/AMC tag, in the window where the chain is dense.
    ev = q("""select act_symbol, `when`, date from earnings.earnings_calendar
              where date >= '2024-01-01' and date <= '2026-06-30'
                and `when` is not null and `when` != ''""")
    if ev.empty:
        print("  no earnings events returned"); return
    ev["date"] = pd.to_datetime(ev["date"])
    # Some act_symbol values come back non-string (a bare "NA" parses as NaN),
    # which makes the symbol set unsortable. Coerce and drop the unusable ones.
    ev["act_symbol"] = ev["act_symbol"].astype(str)
    ev = ev[ev.act_symbol.str.match(r"^[A-Z][A-Z.\-]*$", na=False)]
    print(f"  {len(ev):,} tagged earnings events 2024-01 -> 2026-06")
    print(f"  timing split: {ev['when'].value_counts().to_dict()}")

    # Trading dates present in the chain, to snap entry/exit onto real snapshots.
    snaps = q("select distinct `date` from options.option_chain "
              "where `date` >= '2023-12-01' order by `date`")
    snaps["date"] = pd.to_datetime(snaps["date"])
    sd = snaps["date"].values
    print(f"  {len(sd):,} chain snapshots available")

    # ONE bulk pull, not one query per event. Spawning a dolt subprocess per
    # event was ~3 queries/sec against thousands of events -- hours. Pulling the
    # ATM band for all symbols at once and joining in pandas is minutes.
    ev = ev.sort_values("date")
    plan = {}
    for e in ev.itertuples():
        amc = "After" in str(e.when)
        pre = sd[sd < np.datetime64(e.date)] if not amc else sd[sd <= np.datetime64(e.date)]
        post = sd[sd > np.datetime64(e.date)]
        if len(pre) == 0 or len(post) == 0:
            continue
        d0, d1 = pd.Timestamp(pre[-1]), pd.Timestamp(post[0])
        if (d1 - d0).days > 6:
            continue
        plan[(e.act_symbol, d0, d1)] = e.when
    print(f"  {len(plan):,} event windows to price")

    want_dates = sorted({d for _, d0, d1 in plan for d in (d0, d1)})
    syms = sorted({s for s, _, _ in plan})
    print(f"  pulling chains: {len(syms):,} symbols x {len(want_dates):,} dates ...",
          flush=True)

    chunks = []
    for i in range(0, len(want_dates), 40):
        blk = want_dates[i:i + 40]
        dl = ",".join(f"'{x.date()}'" for x in blk)
        c = q(f"""select act_symbol,`date`,expiration,strike,call_put,bid,ask,vol,delta
                  from options.option_chain
                  where `date` in ({dl}) and delta is not null""")
        if not c.empty:
            chunks.append(c)
        print(f"    {min(i+40, len(want_dates))}/{len(want_dates)} dates", flush=True)
    if not chunks:
        print("  no chain data"); return
    ch = pd.concat(chunks, ignore_index=True)
    ch["date"] = pd.to_datetime(ch["date"])
    print(f"  {len(ch):,} contract rows loaded")

    by = {(s, d): g for (s, d), g in ch.groupby(["act_symbol", "date"])}

    rows = []
    for (sym, d0, d1), when in plan.items():
        a, b = by.get((sym, d0)), by.get((sym, d1))
        if a is None or b is None:
            continue
        common = set(a.expiration) & set(b.expiration)
        if not common:
            continue
        exp = sorted(common)[0]
        a, b = a[a.expiration == exp], b[b.expiration == exp]
        ac = a[(a.call_put == "Call") & a.delta.notna()]
        if ac.empty:
            continue
        k = ac.iloc[(ac.delta - 0.5).abs().argsort()].iloc[0].strike

        def leg(df, cp):
            m = df[(df.strike == k) & (df.call_put == cp)]
            return None if m.empty else m.iloc[0]

        ac0, ap0, ac1, ap1 = leg(a, "Call"), leg(a, "Put"), leg(b, "Call"), leg(b, "Put")
        if any(x is None for x in (ac0, ap0, ac1, ap1)):
            continue
        cost = float(ac0.ask) + float(ap0.ask)
        proceeds = float(ac1.bid) + float(ap1.bid)
        if cost <= 0.05:
            continue
        rows.append({"sym": sym, "d0": d0, "d1": d1, "when": when,
                     "strike": k, "exp": exp, "cost": cost,
                     "ret": (proceeds - cost) / cost,
                     "iv0": float(ac0.vol) if pd.notna(ac0.vol) else np.nan,
                     "iv1": float(ac1.vol) if pd.notna(ac1.vol) else np.nan})

    d = pd.DataFrame(rows)
    if d.empty:
        print("\n  no tradeable event windows built"); return
    d.to_parquet(OUT, index=False)

    r = d.ret
    t = r.mean() / (r.std() / np.sqrt(len(r)))
    print("\n" + "=" * 96)
    print(f"RESULT — {len(d):,} ATM straddles bought at ask, sold at bid")
    print("=" * 96)
    print(f"  mean {r.mean()*100:+7.2f}%   median {r.median()*100:+7.2f}%   "
          f"win {(r>0).mean()*100:5.1f}%   t = {t:+.2f}")
    print("  paper (delta-neutral, D-1 -> D): +2.3%")
    print(f"  IV change through the event: {(d.iv1-d.iv0).median():+.4f} (median)")
    print("\n  by timing:")
    for w, g in d.groupby("when"):
        if len(g) < 30:
            continue
        tt = g.ret.mean() / (g.ret.std() / np.sqrt(len(g)))
        print(f"    {w:22s} n={len(g):5d}  mean {g.ret.mean()*100:+6.2f}%  "
              f"win {(g.ret>0).mean()*100:5.1f}%  t={tt:+5.2f}")
    print("\n  by cost quartile (is it the cheap ones that pay?):")
    d["q"] = pd.qcut(d.cost, 4, labels=["cheapest", "q2", "q3", "priciest"])
    for lab, g in d.groupby("q"):
        print(f"    {str(lab):10s} n={len(g):5d}  mean {g.ret.mean()*100:+6.2f}%  "
              f"win {(g.ret>0).mean()*100:5.1f}%")


if __name__ == "__main__":
    main()
