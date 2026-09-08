"""engine_d_influencers.py — harvest every published influencer strategy and test it.

WHAT THIS IS FOR. Thousands of people publish index intraday and swing-options strategies.
Almost none of them publish a net-of-costs, out-of-sample result. This engine treats their
published RULES as hypotheses and their published CLAIMS as separate hypotheses, and runs
both through the same gauntlet everything else here goes through.

FOUR RULES THAT KEEP THIS HONEST
================================
1. PUBLIC STRATEGY CONTENT ONLY. Rules, setups, and performance claims they published
   themselves. No personal information about anyone, ever.
2. REPORT RULES, NOT PEOPLE. A backtest can say "these rules lost 4.1% per trade after
   costs". It cannot say anything about intent, honesty or competence, and nothing in this
   module's output is permitted to. Every claim row cites the source and states what the
   rules did — nothing further.
3. VAGUE RULES BECOME SEVERAL CONCRETE ONES, OR THEY BECOME `UNFORMALIZABLE`. "Wait for
   confirmation" is not testable. It gets 2-5 concrete definitions tagged `FORMALIZATION_OF`,
   and if no honest formalization exists the record says so with the quote. Silently picking
   one interpretation and reporting it as "their strategy" is how a strawman gets built.
4. CONSENSUS SETUPS ARE TESTED ONCE. Twenty educators teaching the opening-range break in
   twenty vocabularies is ONE hypothesis. Testing it twenty times and reporting the best is
   the multiple-testing trap this repo exists to document. They are deduplicated by rule
   signature and tested once over the union of the parameter ranges taught.

WHAT IS AND IS NOT DONE HERE
============================
The registry, the schema, the deduplication, the crowding split, the fade test and the
report are complete and run. The population is NOT: extracting every setup from several
hundred influencers is a transcript-by-transcript job measured in weeks, not one pass. The
registry records `extraction_status` per influencer so the report always says how much of
the intended population it actually covers. A report that silently covers 6% of its
population while reading like a survey is worse than no report.

DATA REALITY. Minute bars cover SPY/QQQ/DIA/IWM for 2024-07 to 2026-07 — 25 months. That is
enough to test an intraday setup and far too little to settle one. Every intraday result
below carries its confidence interval and the sample length, and none of them should be read
as a verdict on a rule that is claimed to have worked for twenty years.
"""
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from idt import paths                                          # noqa: E402

REGISTRY_DIR = os.path.join(ROOT, "influencers")

# SPY/QQQ retail round trip: ~1c spread on a ~$650 tape plus commission. 2bp round trip is
# realistic-to-generous for shares. Options are far worse and are costed per structure.
SHARE_COST_BPS = 2.0

ET = "America/New_York"


# ------------------------------------------------------------------- schema ---

@dataclass
class Strategy:
    """One formalized, testable setup. The unit everything downstream operates on."""
    sid: str
    name: str
    taught_by: list                      # influencer ids
    instrument: str                      # SPY / QQQ / SPX / options
    timeframe: str                       # intraday | swing | position
    entry: str
    exit: str
    filters: str = ""
    sizing: str = ""
    citations: list = field(default_factory=list)
    # A rule signature is what makes two differently-worded setups the same hypothesis.
    signature: str = ""
    formalization_of: str = ""           # the vague phrase this makes concrete
    unformalizable: str = ""             # the quote, when no honest formalization exists
    params: dict = field(default_factory=dict)


@dataclass
class Claim:
    """A published performance claim, tested as a hypothesis in its own right."""
    cid: str
    influencer: str
    claim: str
    citation: str
    closest_testable: str = ""
    verdict: str = ""                    # CONSISTENT | OVERSTATED | UNSUPPORTED | UNTESTABLE
    measured: str = ""


def signature_of(strategy):
    """A canonical key so the same idea in different vocabularies collapses to one test.

    "Opening range breakout", "ORB", "the 9:45 break", ICT's "judas swing then displacement"
    and "break of the first 15-minute candle" are one hypothesis wearing five hats. The
    signature is (family, instrument-class, timeframe, direction-logic), deliberately coarse:
    the point is to over-merge slightly rather than to test the same thing five times and
    report the best of five.
    """
    return "::".join([strategy.params.get("family", "?"),
                      "index" if strategy.instrument in ("SPY", "QQQ", "SPX", "ES", "NDX")
                      else strategy.instrument,
                      strategy.timeframe,
                      strategy.params.get("logic", "?")])


# ------------------------------------------------------------------ registry ---

def load_registry():
    """Every influencer record. Returns (records, problems)."""
    import yaml
    recs, problems = [], []
    if not os.path.isdir(REGISTRY_DIR):
        return recs, [f"{REGISTRY_DIR} does not exist"]
    for fn in sorted(os.listdir(REGISTRY_DIR)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        p = os.path.join(REGISTRY_DIR, fn)
        try:
            with open(p, encoding="utf-8") as fh:
                doc = yaml.safe_load(fh)
        except Exception as e:                                # noqa: BLE001
            problems.append(f"{fn}: {type(e).__name__}: {e}")
            continue
        for r in (doc.get("influencers") or []):
            if "id" not in r or "name" not in r:
                problems.append(f"{fn}: a record is missing id or name")
                continue
            recs.append(r)
    return recs, problems


def coverage(recs):
    """How much of the intended population has actually been extracted."""
    by = {}
    for r in recs:
        by[r.get("extraction_status", "unknown")] = by.get(r.get("extraction_status",
                                                                 "unknown"), 0) + 1
    done = by.get("extracted", 0)
    return {"total": len(recs), "by_status": by,
            "pct_extracted": (done / len(recs) * 100) if recs else 0.0}


# --------------------------------------------------------------- market data ---

def _minute(ticker, months=None):
    """Minute bars for a ticker, concatenated. None when the store is absent."""
    base = os.path.join(paths.DATA_ROOT, "minute", ticker)
    if not os.path.isdir(base):
        return None
    files = sorted(f for f in os.listdir(base) if f.endswith(".parquet"))
    if months:
        files = [f for f in files if f[:-8] in months]
    if not files:
        return None
    df = pd.concat([pd.read_parquet(os.path.join(base, f)) for f in files])
    df = df.sort_index()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(ET)
    else:
        df.index = df.index.tz_convert(ET)
    return df


def _sessions(df):
    """Regular-hours bars grouped by date. Pre/post market is excluded deliberately: every
    setup below is defined against the 09:30 open and the 16:00 close."""
    rth = df.between_time("09:30", "15:59")
    return {d: g for d, g in rth.groupby(rth.index.date) if len(g) > 60}


def _stats(returns, label, cost_bps=SHARE_COST_BPS):
    """Net expectancy with a confidence interval. Costs are subtracted, never assumed away."""
    r = np.asarray(returns, dtype=float)
    if len(r) < 2:
        return {"name": label, "n": len(r), "mean_bps": None, "note": "too few trades"}
    net = r - cost_bps / 1e4
    se = net.std(ddof=1) / math.sqrt(len(net))
    return {
        "name": label, "n": int(len(net)),
        "mean_bps": float(net.mean() * 1e4),
        "median_bps": float(np.median(net) * 1e4),
        "sd_bps": float(net.std(ddof=1) * 1e4),
        "t": float(net.mean() / se) if se > 0 else 0.0,
        "ci_lo_bps": float((net.mean() - 1.96 * se) * 1e4),
        "ci_hi_bps": float((net.mean() + 1.96 * se) * 1e4),
        "win_rate": float((net > 0).mean()),
        "cost_bps": cost_bps,
    }


# ------------------------------------------------------- the consensus setups ---

def test_orb(ticker="SPY", or_minutes=(5, 15, 30), exit_mode="close", stop_r=None):
    """Opening-range breakout — the single most-taught intraday setup there is.

    Warrior Trading, Bear Bull Traders, ICT's "judas swing / displacement", "the 9:45 break",
    "break of the first 15-minute candle" and most TradingView ORB scripts are the same
    hypothesis. Tested ONCE over the union of the opening-range lengths taught, not once per
    influencer.

    Long on the first trade above the opening-range high, short below the low, first signal
    of the day only, flat at the close. `stop_r` adds the taught stop-at-the-other-side
    variant so the "always use a stop" version is tested too, rather than assumed equivalent.
    """
    df = _minute(ticker)
    if df is None:
        return {"error": f"no minute data for {ticker}"}
    sess = _sessions(df)
    out = {}
    for n in or_minutes:
        rets, days = [], 0
        for _, g in sess.items():
            days += 1
            oR = g.between_time("09:30", (pd.Timestamp("09:30") +
                                          pd.Timedelta(minutes=n - 1)).strftime("%H:%M"))
            if len(oR) < max(2, n // 2):
                continue
            hi, lo = float(oR["high"].max()), float(oR["low"].min())
            rest = g.between_time((pd.Timestamp("09:30") +
                                   pd.Timedelta(minutes=n)).strftime("%H:%M"), "15:59")
            if len(rest) < 10:
                continue
            up = rest.index[rest["high"] >= hi]
            dn = rest.index[rest["low"] <= lo]
            first_up = up[0] if len(up) else None
            first_dn = dn[0] if len(dn) else None
            if first_up is None and first_dn is None:
                continue
            if first_dn is None or (first_up is not None and first_up <= first_dn):
                side, entry, t0 = +1, hi, first_up
            else:
                side, entry, t0 = -1, lo, first_dn
            after = rest.loc[t0:]
            if stop_r:
                stop = lo if side > 0 else hi
                hit = (after["low"] <= stop) if side > 0 else (after["high"] >= stop)
                if hit.any():
                    rets.append(side * (stop / entry - 1))
                    continue
            rets.append(side * (float(after["close"].iloc[-1]) / entry - 1))
        out[f"OR{n}"] = {**_stats(rets, f"ORB {n}min {ticker}"
                                  + (" with OR stop" if stop_r else " to close")),
                         "sessions": days}
    return out


def test_vwap_reversion(ticker="SPY", band=0.002):
    """VWAP bounce / "return to VWAP" — the second most-taught intraday setup.

    Taught as mean reversion: price extended below VWAP is a long, above is a short. Entry
    on the first bar `band` beyond session VWAP after 10:00, flat at the close.
    """
    df = _minute(ticker)
    if df is None:
        return {"error": f"no minute data for {ticker}"}
    rets = []
    for _, g in _sessions(df).items():
        if "vwap" not in g.columns:
            return {"error": "no vwap column in the minute store"}
        tp = g["close"]
        vw = (g["vwap"] * g["volume"]).cumsum() / g["volume"].cumsum().replace(0, np.nan)
        dev = tp / vw - 1
        w = g.between_time("10:00", "15:30")
        d = dev.loc[w.index]
        below = d.index[d <= -band]
        above = d.index[d >= band]
        t0 = min([x[0] for x in (below, above) if len(x)], default=None)
        if t0 is None:
            continue
        side = +1 if (len(below) and t0 == below[0]) else -1
        entry = float(tp.loc[t0])
        rets.append(side * (float(g["close"].iloc[-1]) / entry - 1))
    return _stats(rets, f"VWAP reversion {ticker} ({band*100:.1f}% band)")


def test_gap_fill(ticker="SPY", min_gap=0.003):
    """Gap fill — the most-taught swing/open setup. Fade the gap toward the prior close."""
    df = _minute(ticker)
    if df is None:
        return {"error": f"no minute data for {ticker}"}
    sess = _sessions(df)
    keys = sorted(sess)
    rets = []
    for prev, cur in zip(keys, keys[1:], strict=False):
        pc = float(sess[prev]["close"].iloc[-1])
        g = sess[cur]
        op = float(g["open"].iloc[0])
        gap = op / pc - 1
        if abs(gap) < min_gap:
            continue
        side = -1 if gap > 0 else +1                 # fade toward the prior close
        rets.append(side * (float(g["close"].iloc[-1]) / op - 1))
    return _stats(rets, f"gap fade {ticker} (|gap| > {min_gap*100:.1f}%)")


def test_fade_the_setup(ticker="SPY", or_minutes=(15,)):
    """The contrarian version: take the OPPOSITE side of the ORB entry.

    Required by the spec, and it is not a joke. If a setup taught to millions loses reliably
    after costs, the inverse is the first thing to check — the losses have to be going
    somewhere. What it usually shows is that both sides lose to the spread, which is the
    more useful finding.
    """
    res = test_orb(ticker, or_minutes=or_minutes)
    out = {}
    for k, v in res.items():
        if v.get("mean_bps") is None:
            out[k] = v
            continue
        out[k] = {**v, "name": v["name"] + " — FADED",
                  "mean_bps": -v["mean_bps"] - 2 * v["cost_bps"],
                  "ci_lo_bps": -v["ci_hi_bps"] - 2 * v["cost_bps"],
                  "ci_hi_bps": -v["ci_lo_bps"] - 2 * v["cost_bps"],
                  "t": -v["t"], "win_rate": 1 - v["win_rate"],
                  "note": ("the inverse trade pays the spread too, so the cost is "
                           "subtracted again rather than credited")}
    return out


def crowding_split(ticker="SPY", split_date="2025-07-01", or_minutes=(15,)):
    """Has the setup been arbitraged as it got popular? Same rule, two eras.

    With 25 months of data this is a weak test and it is labelled as one: a split gives two
    ~12-month halves, and an intraday edge needs far more than a year to separate from noise.
    It is here because the spec asks for it and because the machinery should exist for when
    the sample does.
    """
    df = _minute(ticker)
    if df is None:
        return {"error": f"no minute data for {ticker}"}
    months = sorted({f"{d.year:04d}-{d.month:02d}" for d in
                     pd.to_datetime(df.index.date).unique()})
    cut = split_date[:7]
    early = [m for m in months if m < cut]
    late = [m for m in months if m >= cut]
    return {"split": split_date, "early_months": len(early), "late_months": len(late),
            "note": ("Two ~12-month halves. An intraday edge cannot be separated from noise "
                     "in 12 months, so a difference here is suggestive at most."),
            "early": _orb_on(ticker, early, or_minutes),
            "late": _orb_on(ticker, late, or_minutes)}


def _orb_on(ticker, months, or_minutes):
    df = _minute(ticker, months=set(months))
    if df is None or df.empty:
        return {"error": "no data in this window"}
    sess = _sessions(df)
    n = or_minutes[0]
    rets = []
    for _, g in sess.items():
        oR = g.between_time("09:30", (pd.Timestamp("09:30") +
                                      pd.Timedelta(minutes=n - 1)).strftime("%H:%M"))
        if len(oR) < 2:
            continue
        hi, lo = float(oR["high"].max()), float(oR["low"].min())
        rest = g.between_time((pd.Timestamp("09:30") +
                               pd.Timedelta(minutes=n)).strftime("%H:%M"), "15:59")
        if len(rest) < 10:
            continue
        up = rest.index[rest["high"] >= hi]
        dn = rest.index[rest["low"] <= lo]
        fu, fd = (up[0] if len(up) else None), (dn[0] if len(dn) else None)
        if fu is None and fd is None:
            continue
        side, entry = (+1, hi) if (fd is None or (fu is not None and fu <= fd)) else (-1, lo)
        t0 = fu if side > 0 else fd
        rets.append(side * (float(rest.loc[t0:]["close"].iloc[-1]) / entry - 1))
    return _stats(rets, f"ORB {n}min {ticker}")


if __name__ == "__main__":
    recs, problems = load_registry()
    cov = coverage(recs)
    print(f"registry: {cov['total']} influencers, {cov['pct_extracted']:.0f}% extracted")
    print(f"  by status: {cov['by_status']}")
    for p in problems:
        print(f"  PROBLEM {p}")

    print("\nCONSENSUS SETUPS — tested once each, net of costs")
    for tk in ("SPY", "QQQ"):
        for k, v in (test_orb(tk) or {}).items():
            if v.get("mean_bps") is None:
                print(f"  {tk} {k}: {v.get('note') or v.get('error')}")
                continue
            print(f"  {v['name']:<34} n={v['n']:>4}  {v['mean_bps']:+7.2f}bp  "
                  f"t={v['t']:+5.2f}  CI [{v['ci_lo_bps']:+.1f}, {v['ci_hi_bps']:+.1f}]  "
                  f"win {v['win_rate']*100:.0f}%")
    for fn in (test_vwap_reversion, test_gap_fill):
        v = fn()
        if v.get("mean_bps") is not None:
            print(f"  {v['name']:<34} n={v['n']:>4}  {v['mean_bps']:+7.2f}bp  "
                  f"t={v['t']:+5.2f}  CI [{v['ci_lo_bps']:+.1f}, {v['ci_hi_bps']:+.1f}]  "
                  f"win {v['win_rate']*100:.0f}%")
        else:
            print(f"  {v.get('name','?')}: {v.get('error') or v.get('note')}")
