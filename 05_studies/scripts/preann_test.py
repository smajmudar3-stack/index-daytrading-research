"""Pre-announcement overnight drift — the one live candidate from the literature.

Hu, Pan, Wang & Zhu (JFE 2021) find equities drift UP overnight ahead of major
macro releases: NFP +10.10bps (t=3.63), ISM +9.14 (t=2.10), GDP +7.46 (t=2.08),
against a 0.69bps non-announcement benchmark. It is a risk premium — impact
uncertainty resolves before the print, VIX falls into it — which is why it is
not arbitraged away.

Critically, the FOMC version of this DIED after publication (Gilbert-Kurov-Wolfe:
49bps -> 44bps -> 9bps, t=1.33 from 2016) while the ex-FOMC version survived.

That decay is the SPECIFICATION CHECK. If this code cannot reproduce
"FOMC strong pre-2016, dead after", then the event calendar is wrong and every
other number it produces is meaningless. So the FOMC test runs first and its
result gates whether the rest is worth reading.

Measured on SPY close-to-open, which is exactly the window: ISM releases at
10:00 ET so the 9:30 open is entirely pre-announcement; NFP at 8:30 ET is not,
so NFP here is a WEAKER proxy than the paper's 16:00->08:25 window and should
be expected to underperform their number.
"""
import os
import sys
import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "data", "swing", "panel.parquet")


def first_business_day(y, m):
    d = date(y, m, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def first_friday(y, m):
    d = date(y, m, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


# Real FOMC decision dates (second day of each two-day meeting). Guessing
# "third Wednesday" produced a calendar that failed its own check -- meetings
# are not on a fixed weekday offset, so the shape could never appear.
FOMC = """
2005-02-02 2005-03-22 2005-05-03 2005-06-30 2005-08-09 2005-09-20 2005-11-01 2005-12-13
2006-01-31 2006-03-28 2006-05-10 2006-06-29 2006-08-08 2006-09-20 2006-10-25 2006-12-12
2007-01-31 2007-03-21 2007-05-09 2007-06-28 2007-08-07 2007-09-18 2007-10-31 2007-12-11
2008-01-30 2008-03-18 2008-04-30 2008-06-25 2008-08-05 2008-09-16 2008-10-29 2008-12-16
2009-01-28 2009-03-18 2009-04-29 2009-06-24 2009-08-12 2009-09-23 2009-11-04 2009-12-16
2010-01-27 2010-03-16 2010-04-28 2010-06-23 2010-08-10 2010-09-21 2010-11-03 2010-12-14
2011-01-26 2011-03-15 2011-04-27 2011-06-22 2011-08-09 2011-09-21 2011-11-02 2011-12-13
2012-01-25 2012-03-13 2012-04-25 2012-06-20 2012-08-01 2012-09-13 2012-10-24 2012-12-12
2013-01-30 2013-03-20 2013-05-01 2013-06-19 2013-07-31 2013-09-18 2013-10-30 2013-12-18
2014-01-29 2014-03-19 2014-04-30 2014-06-18 2014-07-30 2014-09-17 2014-10-29 2014-12-17
2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16
2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14
2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01 2017-12-13
2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19
2019-01-30 2019-03-20 2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-03-15 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29
""".split()


def fomc_dates(index):
    return pd.DatetimeIndex([pd.Timestamp(d) for d in FOMC])


def run():
    p = pd.read_parquet(PANEL)
    spy = p[p.ticker == "SPY"].set_index("date").sort_index()
    # The overnight window: previous close -> today's open.
    on = (spy["open"] / spy["close"].shift(1) - 1.0).dropna() * 1e4   # in bps
    idx = on.index

    def align(dates):
        """Snap each event date to the next available trading session."""
        out = []
        for d in dates:
            ts = pd.Timestamp(d)
            hit = idx[idx >= ts]
            if len(hit):
                out.append(hit[0])
        return pd.DatetimeIndex(sorted(set(out)))

    years = range(2005, 2027)
    ism = align([first_business_day(y, m) for y in years for m in range(1, 13)])
    nfp = align([first_friday(y, m) for y in years for m in range(1, 13)])
    fomc = align(fomc_dates(idx))

    def stats(d, lo=None, hi=None):
        s = on.reindex(d).dropna()
        if lo:
            s = s[(s.index >= lo) & (s.index <= hi)]
        if len(s) < 15:
            return None
        return len(s), s.mean(), s.mean() / (s.std() / np.sqrt(len(s)))

    base = on.drop(index=ism.union(nfp).union(fomc), errors="ignore")
    print("=" * 84)
    print("PRE-ANNOUNCEMENT OVERNIGHT DRIFT — SPY close-to-open, bps")
    print("=" * 84)
    print(f"  sample {idx[0].date()} -> {idx[-1].date()}")
    print(f"  NON-ANNOUNCEMENT baseline: n={len(base)}  mean={base.mean():+.2f}bps")
    print(f"  (paper's benchmark: +0.69bps)")

    print("\n" + "-" * 84)
    print("SPECIFICATION CHECK — FOMC must be strong pre-2016 and dead after.")
    print("If this shape does not appear, the calendar is wrong; ignore everything below.")
    print("-" * 84)
    early = stats(fomc, "2005-01-01", "2015-12-31")
    late = stats(fomc, "2016-01-01", "2026-12-31")
    if early and late:
        print(f"  FOMC 2005-2015 : n={early[0]:3d}  mean={early[1]:+7.2f}bps  t={early[2]:+5.2f}")
        print(f"  FOMC 2016-2026 : n={late[0]:3d}  mean={late[1]:+7.2f}bps  t={late[2]:+5.2f}")
        decayed = early[1] > late[1] and early[1] > 5
        print(f"  -> decay reproduced? {'YES' if decayed else 'NO — calendar suspect'}")
    else:
        decayed = False
        print("  insufficient FOMC observations")

    print("\n" + "-" * 84)
    print("THE CANDIDATE — ex-FOMC releases")
    print("-" * 84)
    print(f"  {'event':22s} {'n':>5s} {'mean bps':>10s} {'t':>7s}   paper")
    for lab, d, ref in (("ISM (1st bus. day)", ism, "+9.14 (t 2.10)"),
                        ("NFP (1st Friday)", nfp, "+10.10 (t 3.63)")):
        r = stats(d)
        if r:
            print(f"  {lab:22s} {r[0]:5d} {r[1]:+10.2f} {r[2]:+7.2f}   {ref}")

    print("\n  by period (is it still alive?):")
    for lab, d in (("ISM", ism), ("NFP", nfp)):
        row = f"  {lab:5s}"
        for a, b, nm in (("2005-01-01", "2012-12-31", "05-12"),
                         ("2013-01-01", "2019-12-31", "13-19"),
                         ("2020-01-01", "2026-12-31", "20-26")):
            r = stats(d, a, b)
            row += f"  {nm} {r[1]:+6.2f}bps (t{r[2]:+5.2f})" if r else f"  {nm} n/a"
        print(row)

    print("\n" + "=" * 84)
    if not decayed:
        print("VERDICT: specification check FAILED — the FOMC decay did not reproduce,")
        print("so the event calendar is approximate and these numbers are not reliable.")
    else:
        print("VERDICT: calendar validated by the FOMC decay. Read the ISM/NFP rows above.")
    print("  NOTE: NFP releases 08:30 ET, INSIDE this window, so the NFP number here is")
    print("  a weaker proxy than the paper's 16:00->08:25 window and should underperform.")
    print("  ISM releases 10:00 ET, so the 09:30 open is cleanly pre-announcement.")


if __name__ == "__main__":
    run()
