"""stress_sector_neutral_test.py — is the stress book a NAME trade or a SECTOR trade?

The claim under test (strategy tree node `stress-sector-neutral`): the stress reversal
(buy the 40 biggest losers by the reversal composite while VIX > 25, hold ten sessions;
+2.59%/hold over SPY, `02_findings/stress_reversal.md`) is liquidity provision in single
names (Nagel 2012), so ranking each name AGAINST ITS OWN SECTOR ETF should keep or improve
the edge. The alternative: the book is buying whichever sector was hit hardest (energy in
March 2020, banks in March 2023), the names are incidental, and this repo already measured
sector rotation as null — in which case neutralising the sector removes the edge and the
live book has been a sector bet wearing a stock-picking label.

Data, all on this machine: `opt_panel/signal_panel.parquet` (643,687 name-weeks, 2018-01 →
2026-08, close ≥ $10 and $10m/day, excess over SPY from the NEXT open), `opt_panel/ohlcv.parquet`
for the eleven Select Sector SPDR closes and opens and for re-deriving each name's signals
on its price RELATIVE to its sector ETF (split-adjusted with `opt_panel/splits.parquet`),
`opt_panel/gics.parquet` for the S&P 1500 sector map (1,506 names, current constituents:
a survivorship the study measures rather than ignores, see arm A' below).

Arms, every one the bottom 40 of a composite on a date with VIX > 25, filled at the next
open, held H sessions, non-overlapping dates (one every H/5 weeks), the GICS-covered
universe unless stated:
  A   raw composite (mean rank of 1-month return, 1-week return, 20-day Bollinger position),
      P&L over SPY — the house trade, with the three signals re-derived here on the same
      clean calendar as arm D, so the two arms differ in nothing but the sector adjustment
  A'  the house number AS MEASURED: the panel's own composite on the FULL panel. It differs
      from A in two ways that this study found and states: (1) a current-constituent sector
      map is a survivorship (names that left the S&P 1500 are not in A); (2) the panel's
      rolling features were built on a calendar that includes 2020-02-17, Presidents' Day,
      a session on which ~3,400 symbols carry a stale row and the other ~70% carry none, so
      the panel's `bb_pos`, `vol21` and `rsi14` are NaN for every name without that row for
      the next twenty sessions — the four crash weeks 2020-02-21 → 2020-03-13 — and the
      house stress book on those weeks was chosen from the ~108 names that had the row.
      (Two 2019 sessions, 2019-08-23 and 2019-09-17, are 60% empty and do the same.) The
      calendar here drops a session when fewer than 70% of the names have a row.
  B   raw composite, P&L over the name's OWN SECTOR ETF — how much of A is the sector moving
  C   the SECTOR LEG alone: hold the sector ETFs of A's picks instead of the names, over SPY
  D   SECTOR-RELATIVE composite (the three signals computed on close / sector-ETF close),
      P&L over SPY — the trade a sector-neutral ranker would actually place
  E   sector-relative composite, P&L over the sector ETF — the pure idiosyncratic reversal
  F   raw composite with a per-sector CAP of 8 names (of 40), P&L over SPY — the practical
      version a book can run
  G   raw composite ranked WITHIN sector, the bottom 4 of every sector (44 names), over SPY
Plus the out-of-regime control for A and D, the other three regime definitions at ten
sessions, the sector concentration of A's picks on every regime date, and leave-one-date-
out for A and D (trap 5: one March-2020 week driving a matrix).

Costs: 30 bp a side (spreads widen in a stressed tape; the house's honest row), charged
as full turnover per hold. Splits A 2019-21 / B 2022-23 / C 2024-26. Noise bar: 9 arms ×
3 holds + 2 controls × 3 + 3 extra regimes × 2 arms = 39 cells scored, sqrt(2 ln 39) = 2.71;
a t below that is what noise produces on its best cell. Nothing here places an order.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from idt import paths  # noqa: E402
from xsec_predictors_test import SPLITS, adjust_splits  # noqa: E402

warnings.filterwarnings("ignore")
PANEL = os.path.join(paths.DATA_ROOT, "opt_panel")
COST = 0.0030          # per side
K = 40                 # names in the book
CAP = 8                # arm F: per-sector cap
PER_SECTOR = 4         # arm G: bottom-N of every sector
HOLDS = (5, 10, 21)
SECTOR_ETF = {"Information Technology": "XLK", "Financials": "XLF", "Energy": "XLE", "Health Care": "XLV",
              "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Industrials": "XLI", "Utilities": "XLU",
              "Materials": "XLB", "Real Estate": "XLRE", "Communication Services": "XLC"}
N_CELLS = 39
NOISE_BAR = np.sqrt(2 * np.log(N_CELLS))


def _t(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else np.nan


def sector_map():
    g = pd.read_parquet(os.path.join(PANEL, "gics.parquet"))
    g["etf"] = g.sector.map(SECTOR_ETF)
    return g.dropna(subset=["etf"]).drop_duplicates("ticker").set_index("ticker")[["sector", "etf"]]


def prices(names):
    """Split-adjusted open/close for the named symbols and the sector ETFs, wide by date."""
    px = pd.read_parquet(os.path.join(PANEL, "ohlcv.parquet"), columns=["date", "act_symbol", "open", "close"])
    px["act_symbol"] = px.act_symbol.astype(str)
    want = set(names) | set(SECTOR_ETF.values()) | {"SPY"}
    px = px[px.act_symbol.isin(want)].drop_duplicates(["date", "act_symbol"])
    px = adjust_splits(px.assign(high=np.nan, low=np.nan, volume=np.nan))
    # The calendar is the NAMES' calendar. The file carries rows for ~3,400 symbols (the ETFs,
    # SPY and foreign-listed names among them) on 2020-02-17, Presidents' Day, and on two 2019
    # sessions where 60% of the feed is missing. Left in, those dates are a NaN in every
    # name's 20-day window and the sector-relative Bollinger vanished for the whole universe
    # through March 2020: the first run scored every arm on ONE stock (CRH) for three weeks.
    cnt = px[px.act_symbol.isin(set(names))].groupby("date").size()
    cal = cnt[cnt >= 0.7 * cnt.rolling(21, center=True, min_periods=5).median()].index
    dropped = cnt.index.difference(cal)
    if len(dropped):
        print(f"  calendar: dropped {len(dropped)} phantom session(s): {[d.date() for d in dropped]}")
    px = px[px.date.isin(cal)]
    close = px.pivot(index="date", columns="act_symbol", values="close").sort_index()
    opn = px.pivot(index="date", columns="act_symbol", values="open").sort_index()
    return close, opn


def relative_signals(close, opn, smap):
    """The three reversal signals on close / sector-ETF close, and forward returns of the ETFs
    and SPY from the next open (same construction as the panel's fwd{h})."""
    names = [c for c in close.columns if c in smap.index]
    etf_of = smap.loc[names, "etf"]
    etf_mat = close[etf_of.values].copy()
    etf_mat.columns = names
    rel = close[names] / etf_mat
    own = close[names]
    F = {"rel_rev1w": rel / rel.shift(5) - 1,
         "rel_rev1m": rel / rel.shift(21) - 1,
         "rel_bb": (rel - rel.rolling(20, min_periods=15).mean()) / (2 * rel.rolling(20, min_periods=15).std().replace(0, np.nan)),
         # the raw signals, re-derived on the SAME clean calendar, so arm A and arm D differ in
         # nothing but the sector adjustment (the panel's own bb_pos has the March-2020 hole)
         "own_rev1w": own / own.shift(5) - 1,
         "own_rev1m": own / own.shift(21) - 1,
         "own_bb": (own - own.rolling(20, min_periods=15).mean()) / (2 * own.rolling(20, min_periods=15).std().replace(0, np.nan))}
    bench = {}
    for sym in list(SECTOR_ETF.values()) + ["SPY"]:
        for h in HOLDS:
            bench[(sym, h)] = close[sym].shift(-h) / opn[sym].shift(-1) - 1
    bench = pd.DataFrame(bench)
    bench.columns = pd.MultiIndex.from_tuples(bench.columns, names=["sym", "h"])
    out = pd.DataFrame({k: v.stack(future_stack=True) for k, v in F.items()})
    out.index.names = ["date", "act_symbol"]
    return out.reset_index(), bench


def attach(w, smap, close, opn):
    w = w[w.act_symbol.isin(smap.index)].copy()
    w["sector"] = w.act_symbol.map(smap.sector)
    w["etf"] = w.act_symbol.map(smap.etf)
    sig, bench = relative_signals(close, opn, smap)
    w = w.merge(sig, on=["date", "act_symbol"], how="left")
    for h in HOLDS:
        spy_f = bench[("SPY", h)]
        w[f"spy_fwd{h}"] = w.date.map(spy_f)
        etf_f = bench.xs(h, axis=1, level="h").stack(future_stack=True).rename("etf_fwd")
        etf_f.index.names = ["date", "etf"]
        w = w.merge(etf_f.reset_index().rename(columns={"etf_fwd": f"etf_fwd{h}"}), on=["date", "etf"], how="left")
        w[f"ex_sec{h}"] = w[f"fwd{h}"] - w[f"etf_fwd{h}"]       # the name over its own sector
        w[f"sec_ex{h}"] = w[f"etf_fwd{h}"] - w[f"spy_fwd{h}"]   # the sector over SPY (arm C)
    return w


def composites(w):
    g = w.groupby("date")
    w["raw_panel"] = (g.rev1m.rank(pct=True) + g.rev1w.rank(pct=True) + g.bb_pos.rank(pct=True)) / 3
    if "rel_rev1m" not in w.columns:                          # the full panel carries no sector map
        w["raw"] = w.raw_panel
        return w
    ok = w.dropna(subset=["own_rev1m", "own_rev1w", "own_bb"]).index
    gg = w.loc[ok].groupby("date")
    w.loc[ok, "raw"] = (gg.own_rev1m.rank(pct=True) + gg.own_rev1w.rank(pct=True) + gg.own_bb.rank(pct=True)) / 3
    ok = w.dropna(subset=["rel_rev1m", "rel_rev1w", "rel_bb"]).index
    gg = w.loc[ok].groupby("date")
    w.loc[ok, "rel"] = (gg.rel_rev1m.rank(pct=True) + gg.rel_rev1w.rank(pct=True) + gg.rel_bb.rank(pct=True)) / 3
    return w


def bottom_k(d, score, k=K):
    r = d.groupby("date")[score].rank(method="first")
    return d[r <= k]


def bottom_capped(d, score, k=K, cap=CAP):
    d = d.sort_values(["date", score])
    d = d.assign(_sr=d.groupby(["date", "sector"]).cumcount())
    d = d[d._sr < cap]
    r = d.groupby("date")[score].rank(method="first")
    return d[r <= k].drop(columns="_sr")


def bottom_per_sector(d, score, n=PER_SECTOR):
    r = d.groupby(["date", "sector"])[score].rank(method="first")
    return d[r <= n]


def line(picks, y, h, label, min_dates=8):
    picks = picks.dropna(subset=[y])
    n = picks.groupby("date").size()
    thin = n[n < K // 2].index                                # a date that could not fill half the book is not a book
    if len(thin):
        print(f"  {label:52s} dropped {len(thin)} date(s) with under {K // 2} names: {[d.date() for d in thin][:4]}")
        picks = picks[~picks.date.isin(thin)]
    if picks.date.nunique() < min_dates:
        print(f"  {label:52s} too few dates ({picks.date.nunique()})")
        return None
    s = picks.groupby("date")[y].mean()
    win, loss = picks[picks[y] > 0][y].mean(), picks[picks[y] <= 0][y].mean()
    net = s.mean() - 2 * COST
    splits = " / ".join(f"{s[(s.index >= a) & (s.index <= b)].mean()*100:+.2f}({(s.index >= a).sum() - (s.index > b).sum()})"
                        for a, b in SPLITS.values())
    flag = "*" if abs(_t(s)) >= NOISE_BAR else " "
    print(f"  {label:52s} dates {len(s):3d} names/date {picks.groupby('date').size().median():3.0f} | {s.mean()*100:+.2f}%/hold "
          f"(t {_t(s):+.1f}){flag} hit {(picks[y] > 0).mean():.3f} payoff {win / -loss if loss else np.nan:.2f} date-hit {(s > 0).mean():.2f} "
          f"net {net*100:+.2f}% | A/B/C {splits}")
    return s


def leave_one_out(s, label):
    if s is None or len(s) < 8:
        return
    best, worst = s.idxmax(), s.idxmin()
    print(f"  {label:52s} drop best date {best.date()} ({s.max()*100:+.1f}%): {s.drop(best).mean()*100:+.2f}% (t {_t(s.drop(best)):+.1f}) | "
          f"drop worst {worst.date()} ({s.min()*100:+.1f}%): {s.drop(worst).mean()*100:+.2f}% | median date {s.median()*100:+.2f}%")


def concentration(picks):
    sh = picks.groupby(["date", "sector"]).size().unstack(fill_value=0)
    sh = sh.div(sh.sum(axis=1), axis=0)
    top = sh.max(axis=1)
    hhi = (sh ** 2).sum(axis=1)
    lead = sh.idxmax(axis=1)
    print(f"  largest-sector share of the 40: median {top.median():.2f}, max {top.max():.2f} on {top.idxmax().date()} ({lead[top.idxmax()]}); "
          f"Herfindahl median {hhi.median():.3f} (equal across 11 sectors = {1/11:.3f}); leading sector by count: {lead.value_counts().head(4).to_dict()}")


def main():
    pd.set_option("display.width", 250)
    cols = ["date", "act_symbol", "rev1w", "rev1m", "bb_pos", "close", "adv20", "vix", "vix_rank", "spy_12m"]
    cols += [f"fwd{h}" for h in HOLDS] + [f"ex{h}" for h in HOLDS]
    w_full = pd.read_parquet(os.path.join(PANEL, "signal_panel.parquet"), columns=cols)
    w_full["act_symbol"] = w_full.act_symbol.astype(str)
    smap = sector_map()
    close, opn = prices(w_full.act_symbol.unique())
    for sym in SECTOR_ETF.values():
        s = close[sym].dropna()
        print(f"  {sym}: {s.index.min().date()} .. {s.index.max().date()} ({len(s)} days)")
    w = composites(attach(w_full, smap, close, opn))
    w_full = composites(w_full.copy())
    chk = w[["rev1m", "own_rev1m"]].dropna()
    print(f"\nuniverse: full panel {w_full.act_symbol.nunique()} names / {len(w_full)} rows; GICS-covered {w.act_symbol.nunique()} names / {len(w)} rows; "
          f"sector-relative composite available on {w.rel.notna().mean():.1%} of rows")
    print(f"sanity: re-derived 1-month return vs the panel's, corr {chk.corr().iloc[0, 1]:.4f} (n {len(chk)}); "
          f"panel ex10 vs fwd10 − my SPY fwd10: max |diff| {(w.ex10 - (w.fwd10 - w.spy_fwd10)).abs().max():.4f}")
    spy = close["SPY"]
    ma200 = spy.rolling(200).mean()
    below = w.date.map((spy < ma200).astype(float)) > 0
    regimes = {"VIX > 25": w.vix > 25, "VIX top 30% of year": w.vix_rank > 0.7,
               "SPY < 200-day MA": below, "SPY 12m < 0": w.spy_12m < 0}
    print(f"\nnoise bar for {N_CELLS} cells: |t| {NOISE_BAR:.2f} (a * marks a cell beyond it)")
    for h in HOLDS:
        step = max(1, h // 5)
        dates = np.sort(w.date.unique())[::step]
        d0 = w[w.date.isin(dates)]
        f0 = w_full[w_full.date.isin(dates)]
        on = (d0.vix > 25)
        on_full = (f0.vix > 25)
        y, ys, yc = f"ex{h}", f"ex_sec{h}", f"sec_ex{h}"
        print(f"\n{'='*170}\nHOLD {h} SESSIONS, VIX > 25 at the close of the ranking date, filled at the next open. "
              f"{d0[on].date.nunique()} of {d0.date.nunique()} dates in regime.")
        both = d0[on].dropna(subset=["raw", "rel"])            # same rows for every arm
        A = line(bottom_k(both, "raw"), y, h, "A  raw composite, over SPY")
        line(bottom_k(f0[on_full].dropna(subset=["raw"]), "raw"), y, h, "A' raw composite, FULL panel, over SPY")
        # the panel's own composite on THIS universe: A' − A° is the survivorship of the sector
        # map, A° − A is the panel's phantom-session hole (plus min_periods)
        line(bottom_k(d0[on].dropna(subset=["raw_panel"]), "raw_panel"), y, h, "A° the PANEL's composite, GICS universe, over SPY")
        line(bottom_k(both, "raw"), ys, h, "B  raw composite, over OWN SECTOR ETF")
        line(bottom_k(both, "raw"), yc, h, "C  the sector ETFs of A's picks, over SPY")
        D = line(bottom_k(both, "rel"), y, h, "D  sector-RELATIVE composite, over SPY")
        line(bottom_k(both, "rel"), ys, h, "E  sector-relative composite, over own sector ETF")
        line(bottom_capped(both, "raw"), y, h, f"F  raw composite, cap {CAP} per sector, over SPY")
        line(bottom_per_sector(both, "raw"), y, h, f"G  raw composite, bottom {PER_SECTOR} of EVERY sector, over SPY")
        ra, rd = bottom_k(both, "raw"), bottom_k(both, "rel")
        ov = ra.merge(rd, on=["date", "act_symbol"]).groupby("date").size() / ra.groupby("date").size()
        print(f"  overlap of A and D picks: median {ov.median():.2f} of the 40 names")
        off = d0[~on].dropna(subset=["raw", "rel"])
        line(bottom_k(off, "raw"), y, h, "   control: A out of regime")
        line(bottom_k(off, "rel"), y, h, "   control: D out of regime")
        print("  trap 5, leave one date out:")
        leave_one_out(A, "   A")
        leave_one_out(D, "   D")
        print("  sector concentration of A's picks on regime dates:")
        concentration(ra)
        if h == 10:
            print("\n  the other regime definitions, ten sessions, A against D:")
            for rname, mask in regimes.items():
                if rname == "VIX > 25":
                    continue
                dd = d0[mask.reindex(d0.index).fillna(False)].dropna(subset=["raw", "rel"])
                line(bottom_k(dd, "raw"), y, h, f"   {rname:22s} A raw, over SPY")
                line(bottom_k(dd, "rel"), y, h, f"   {rname:22s} D sector-relative, over SPY")
    # which sectors the raw book bought, in regime, by year
    on = w[(w.vix > 25)]
    ra = bottom_k(on.dropna(subset=["raw"]), "raw")
    tab = ra.groupby([ra.date.dt.year, "sector"]).size().unstack(fill_value=0)
    print("\nSECTOR COUNT OF THE RAW BOOK'S PICKS ON EVERY VIX > 25 WEEK, BY YEAR (overlapping weeks, for the picture):")
    print(tab.to_string())


if __name__ == "__main__":
    main()
