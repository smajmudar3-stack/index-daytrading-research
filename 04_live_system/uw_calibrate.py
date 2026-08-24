"""Let each endpoint EARN its weight from realised accuracy.

The weights in `uw_endpoints.WEIGHTS` started as my judgement about which data
is orthogonal. That is a starting prior, not evidence, and the panel flags it as
"unmeasured". This module replaces the prior with measurement:

    1. LOG   — every scan, record each input's value per ticker (snapshot.jsonl)
    2. SETTLE— once the forward window closes, attach the realised return
    3. SCORE — compute each input's Information Coefficient: the rank
               correlation between what it said and what happened
    4. WEIGHT— set the weight from the IC, SHRUNK for sample size

The shrinkage is the part that matters. An IC of 0.40 on 15 observations is
noise; the same IC on 400 is a signal. So:

    weight  ∝  IC × sqrt(n / (n + N0))          N0 = 100

At n=15 that keeps ~36% of the raw IC; at n=400 it keeps ~89%. An input cannot
earn a large weight simply by getting a few calls right, which is precisely how
every over-fit strategy in this repo began.

Inputs measured NULL elsewhere stay pinned at zero regardless of what a short
run of luck does to their IC — a measured null on 810,300 ticker-days is not
overturned by 30 forward observations.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "data", "uw_signal_log.jsonl")
WEIGHTS_OUT = os.path.join(ROOT, "data", "uw_weights.json")

# Forward window the signals are judged against, in trading days.
HORIZON = 5
# Shrinkage constant: observations needed before an IC is taken near-fully.
N0 = 100
# Pinned to zero by prior measurement; a forward run cannot revive these.
HARD_ZERO = {"iv_rel", "iv_trend", "oi_change_net", "spread_rel"}

SIGNAL_FIELDS = ["flow_lean", "dp_buy_share", "short_float_pct",
                 "insider_open_buys", "oi_change_net"]


def log_snapshot(profiles):
    """Append today's signal values so they can be settled later."""
    ts = datetime.now(timezone.utc).isoformat()
    with open(LOG, "a") as f:
        for p in profiles:
            if not p.get("ticker"):
                continue
            row = {"ts": ts, "ticker": p["ticker"]}
            for k in SIGNAL_FIELDS:
                if p.get(k) is not None:
                    row[k] = p[k]
            if len(row) > 2:
                f.write(json.dumps(row) + "\n")
    return True


def _load_log():
    if not os.path.exists(LOG):
        return pd.DataFrame()
    rows = []
    with open(LOG) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d.ts).dt.tz_localize(None).dt.normalize()
    return d


def settle(price_lookup=None):
    """Attach realised forward returns to logged signals whose window has closed."""
    d = _load_log()
    if d.empty:
        return d
    if price_lookup is None:
        import yfinance as yf
        import warnings
        warnings.filterwarnings("ignore")

        def price_lookup(tks, start):
            px = yf.download(list(tks), start=start, progress=False,
                             auto_adjust=True, threads=False)
            return px["Close"] if "Close" in px else px

    start = (d.date.min() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    px = price_lookup(sorted(d.ticker.unique()), start)
    if isinstance(px, pd.Series):
        px = px.to_frame()

    out = []
    for _, r in d.iterrows():
        t = r["ticker"]
        if t not in px.columns:
            continue
        s = px[t].dropna()
        after = s[s.index > r["date"]]
        if len(after) <= HORIZON:
            continue                     # window still open — not settleable yet
        entry = float(after.iloc[0])
        exit_ = float(after.iloc[HORIZON])
        rec = dict(r)
        rec["fwd_ret"] = (exit_ - entry) / entry
        out.append(rec)
    return pd.DataFrame(out)


def calibrate(min_n=20):
    """Turn realised outcomes into weights.

    Returns the weight table and writes it for the panel to consume.
    """
    s = settle()
    if s.empty:
        return {"status": "no settled observations yet", "weights": {}, "n": 0}

    res = {}
    for k in SIGNAL_FIELDS:
        if k not in s.columns:
            continue
        sub = s[[k, "fwd_ret"]].dropna()
        n = len(sub)
        if n < min_n or sub[k].nunique() < 3:
            res[k] = {"n": n, "ic": None, "weight": 0.0,
                      "status": f"insufficient ({n} < {min_n})"}
            continue
        # Spearman: the signal only has to RANK outcomes, not predict magnitude.
        ic = float(sub[k].corr(sub["fwd_ret"], method="spearman"))
        shrink = np.sqrt(n / (n + N0))
        w = max(0.0, ic) * shrink        # a negative IC earns no weight, not a short
        res[k] = {"n": n, "ic": round(ic, 3), "shrink": round(shrink, 2),
                  "weight_raw": round(w, 4),
                  "status": "measured" if abs(ic) > 0.02 else "no signal"}

    for k in HARD_ZERO:
        if k in res:
            res[k]["weight_raw"] = 0.0
            res[k]["status"] = "pinned zero — measured null on 810,300 ticker-days"

    tot = sum(v.get("weight_raw", 0) for v in res.values())
    for v in res.values():
        v["weight"] = round(v.get("weight_raw", 0) / tot, 3) if tot else 0.0

    out = {"status": "ok", "asof": datetime.now(timezone.utc).isoformat(),
           "n_settled": int(len(s)), "horizon_days": HORIZON, "weights": res}
    with open(WEIGHTS_OUT, "w") as f:
        json.dump(out, f, indent=1)
    return out


def blend(prior_w, measured_ic, n):
    """Bayesian-style blend: start at the prior, move toward measurement as
    evidence accumulates.

    This is what "fabricate the weight and adjust as time goes on" means in
    practice. The prior carries the weight while n is small; the measurement
    takes over as n grows, at the same sqrt(n/(n+N0)) rate used elsewhere so the
    whole system shrinks consistently.

        w = (1 - k) * prior + k * measured,   k = sqrt(n / (n + N0))

    At n=0 the weight is entirely prior; at n=100 it is ~71% measurement; at
    n=400, ~89%. Nothing jumps, and nothing stays fabricated forever.
    """
    if measured_ic is None or n <= 0:
        return prior_w, 0.0
    k = float(np.sqrt(n / (n + N0)))
    # An IC of ~0.05 is a strong cross-sectional signal, so scale to that.
    measured_w = max(0.0, min(1.0, abs(measured_ic) / 0.05))
    return (1 - k) * prior_w + k * measured_w, k


def live_weights():
    """Measured weights if enough data exists, else the documented prior.

    The caller is told WHICH it got, so a prior is never mistaken for evidence.
    """
    import uw_endpoints as ue
    try:
        with open(WEIGHTS_OUT) as f:
            cal = json.load(f)
        w = {k: v["weight"] for k, v in cal.get("weights", {}).items()
             if v.get("weight", 0) > 0}
        if w and cal.get("n_settled", 0) >= 50:
            return {"weights": w, "source": "measured",
                    "n": cal["n_settled"],
                    "detail": cal["weights"]}
    except Exception:
        pass
    return {"weights": {k: v[0] for k, v in ue.WEIGHTS.items() if v[0] > 0},
            "source": "prior (unmeasured)", "n": 0, "detail": {}}


if __name__ == "__main__":
    import uw_endpoints as ue
    print("logging a snapshot ...")
    uni = ["SPY", "QQQ", "NVDA", "TSLA", "MRNA", "AAPL", "AMD", "PLTR",
           "SOFI", "MARA", "RIOT", "GME"]
    profs = [ue.profile(t) for t in uni]
    log_snapshot([p for p in profs if p])
    d = _load_log()
    print(f"  log now holds {len(d)} rows over {d.date.nunique() if not d.empty else 0} day(s)")
    c = calibrate()
    print(f"\ncalibration: {c['status']}  (settled n={c.get('n_settled',0)})")
    lw = live_weights()
    print(f"live weights source: {lw['source']}")
    for k, v in lw["weights"].items():
        print(f"  {k:20s} {v:.3f}")
