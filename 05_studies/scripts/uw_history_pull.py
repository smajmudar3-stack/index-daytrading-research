"""uw_history_pull.py — pull every Unusual Whales endpoint that returns DATED history, for a
universe of names, into parquet under DATA_ROOT/uw_hist/daily/. Once.

The registry in 04_live_system/uw_endpoints.py says the four paid voters (flow lean, dark
pool share, short float, insider buys) are "same-day only, cannot be backtested". That is
true of the endpoints the LIVE engine calls. It is not true of the API: several per-ticker
endpoints return a year or more of daily rows in ONE call, and those are enough to measure
whether what the subscription pays for predicts anything at a weekly horizon.

Endpoints pulled (one call per ticker each; ~10 calls a name, so a 300-name universe is
~3,000 calls against a 30,000/day quota):

    options-volume            daily call/put volume, premium, bullish/bearish premium
    nope                      net options pricing effect, daily
    greek-exposure            dealer gamma/delta/vanna/charm exposure, daily
    max-pain                  pin level by expiry, daily
    iv-rank                   IV rank / percentile, daily
    volatility/realized       realised vs implied, daily
    volatility/term-structure daily term structure
    historical-risk-reversal-skew   25-delta risk reversal, daily
    shorts/volume-and-ratio   daily off-exchange short volume ratio
    shorts/interest-float/v2  settlement short interest (bi-weekly)
    insider-buy-sells         insider buy/sell counts by filing date

Each response is stored raw (every column the vendor returned) with `_symbol` and
`_endpoint` stamped, so the study decides what a field means, not this file. A 429 stops
the run cleanly and it resumes from where it left off: files already on disk are skipped.
"""
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from idt import paths  # noqa: E402

sys.path.insert(0, paths.STUDIES_DIR)
import live_path  # noqa: E402

live_path.enable()
import uw_client as uw  # noqa: E402

OUT = os.path.join(paths.DATA_ROOT, "uw_hist", "daily")
os.makedirs(OUT, exist_ok=True)

ENDPOINTS = {
    "options_volume": ("/api/stock/{t}/options-volume", {"limit": 500}),
    "nope": ("/api/stock/{t}/nope", {}),
    "greek_exposure": ("/api/stock/{t}/greek-exposure", {}),
    "max_pain": ("/api/stock/{t}/max-pain", {}),
    "iv_rank": ("/api/stock/{t}/iv-rank", {}),
    "realized_vol": ("/api/stock/{t}/volatility/realized", {}),
    "term_structure": ("/api/stock/{t}/volatility/term-structure", {}),
    "rr_skew": ("/api/stock/{t}/historical-risk-reversal-skew", {"delta": 25}),
    "short_volume": ("/api/shorts/{t}/volume-and-ratio", {}),
    "short_interest": ("/api/shorts/{t}/interest-float/v2", {}),
    "insider": ("/api/stock/{t}/insider-buy-sells", {}),
}


def universe(n):
    """The live index universe, ranked by 20-day dollar volume from the Dolt panel."""
    px = pd.read_parquet(os.path.join(paths.DATA_ROOT, "opt_panel", "ohlcv.parquet"))
    px["act_symbol"] = px.act_symbol.astype(str)
    last = px[px.date >= px.date.max() - pd.Timedelta(days=30)]
    dv = (last.close * last.volume).groupby(last.act_symbol).median().sort_values(ascending=False)
    fe = pd.read_parquet(os.path.join(paths.DATA_ROOT, "opt_panel", "features.parquet"), columns=["act_symbol"])
    optionable = set(fe.act_symbol.astype(str).unique())
    return [t for t in dv.index if t in optionable][:n]


def pull(ticker, name, path, params):
    f = os.path.join(OUT, f"{name}__{ticker}.parquet")
    if os.path.exists(f):
        return "cached"
    r = uw._get(path.replace("{t}", ticker), params)
    if r is None:
        return "no-key"
    if isinstance(r, dict) and "_error" in r:
        return r["_error"]
    rows = uw._rows(r)
    if not rows:
        pd.DataFrame({"_empty": [True]}).to_parquet(f, index=False)
        return "empty"
    df = pd.DataFrame(rows)
    df["_symbol"], df["_endpoint"] = ticker, name
    df = df.astype({c: str for c in df.columns if df[c].dtype == object})
    df.to_parquet(f, index=False)
    return f"{len(df)} rows"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    names = universe(n)
    print(f"{len(names)} names, {len(ENDPOINTS)} endpoints", flush=True)
    t0, calls = time.time(), 0
    for i, tk in enumerate(names):
        line = []
        for name, (path, params) in ENDPOINTS.items():
            res = pull(tk, name, path, params)
            if res != "cached":
                calls += 1
            line.append(f"{name}={res}")
            if "429" in res:
                print(f"\n{tk}: rate limited after {calls} calls — stopping; rerun to resume", flush=True)
                return
        print(f"{i:4d} {tk:6s} {time.time()-t0:5.0f}s  " + "  ".join(line), flush=True)


if __name__ == "__main__":
    main()
