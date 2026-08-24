"""uw_client.py — Unusual Whales integration (READY TO ACTIVATE — just add your API key).

UW gives what a free option-volume proxy CANNOT: real buy-vs-sell classified flow, so we know
whether big money is BUYING calls (bullish) or BUYING puts (bearish) — the strongest direction
signal available. When a key is present this REPLACES the yfinance volume proxy in the periscope.

Activate: put your key in ~/quant-factory/.env or ~/index-daytrading/.env as:
    UNUSUALWHALES_API_KEY=your_token_here
(or export UNUSUALWHALES_API_KEY / UW_API_KEY in the environment)

Endpoints are UW's documented REST paths; if any 404 once your key is live, tell me and I'll
pull the current UW API docs and adjust the paths — the scaffolding (auth, parsing, fallback) is done.
"""
import json
import os
import urllib.request
import urllib.parse

BASE = "https://api.unusualwhales.com"


def _key():
    for p in ("/Users/sahilmajmudar/quant-factory/.env",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
        if os.path.exists(p):
            for line in open(p):
                for name in ("UNUSUALWHALES_API_KEY", "UW_API_KEY"):
                    if line.startswith(name + "="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("UNUSUALWHALES_API_KEY") or os.environ.get("UW_API_KEY")


# Master switch. The UW subscription is lapsed: the key is still present in
# .env but every endpoint returns nulls, which propagated into the dashboard as
# None-valued fields and crashed the render. A missing key and a dead
# subscription are different failures, and available() could not tell them
# apart, so every caller believed UW was live.
#
# UW is ENABLED (subscription restored 2026-08-11, key rotated). Set
# UW_DISABLED=1 in the environment to force it off again.
UW_DISABLED = os.environ.get("UW_DISABLED", "0") != "0"

# Auto-trip. A lapsed subscription returns 401 on every call while the key is
# still present — the exact case that made available() lie and crashed the
# dashboard on None-valued fields. After this many consecutive auth failures
# the client disables itself for the life of the process and callers fall back
# to yfinance, instead of every endpoint returning nulls forever.
_AUTH_FAILS = {"n": 0, "tripped": False}
_AUTH_TRIP_AFTER = 3


def _note_auth_failure():
    _AUTH_FAILS["n"] += 1
    if _AUTH_FAILS["n"] >= _AUTH_TRIP_AFTER and not _AUTH_FAILS["tripped"]:
        _AUTH_FAILS["tripped"] = True
        print("uw_client: %d consecutive auth failures — disabling UW for this "
              "process; falling back to yfinance." % _AUTH_FAILS["n"])


def available():
    """True only if UW is usable — enabled, key present, and not auth-tripped."""
    if UW_DISABLED or _AUTH_FAILS["tripped"]:
        return False
    return bool(_key())


_CACHE = {}          # {url: (expiry_ts, payload)} — short TTL to protect the UW rate limit
_TTL = 20            # seconds. Measured quota is 30,000/day with no practical
                     # per-minute cap (x-uw-req-per-minute-remaining: 1000000) and
                     # we use ~130/day, so the old 45s was ~200x too conservative.


def _get(path, params=None):
    # Single chokepoint: every endpoint routes through here, so one guard
    # disables the whole client and saves the network round-trips too.
    if UW_DISABLED or _AUTH_FAILS["tripped"]:
        return None
    key = _key()
    if not key:
        return None
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    import time as _t
    hit = _CACHE.get(url)
    if hit and hit[0] > _t.time():
        return hit[1]
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}", "Accept": "application/json",
        "User-Agent": "index-daytrading/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode())
        _CACHE[url] = (_t.time() + _TTL, payload)      # cache only successful pulls
        _AUTH_FAILS["n"] = 0                            # healthy call clears the streak
        return payload
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            # A lapsed subscription drops every x-uw-* header, which is a
            # positive signal rather than an inference from repeated failure.
            try:
                if not any(k.lower().startswith("x-uw-") for k in e.headers.keys()):
                    _AUTH_FAILS["n"] = _AUTH_TRIP_AFTER - 1
            except Exception:
                pass
            _note_auth_failure()
        return {"_error": f"HTTPError: HTTP Error {e.code}: {e.reason}"}
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:80]}"}


def flow_alerts(ticker):
    """Recent classified option-flow alerts for ONE ticker (buy/sell side, premium, call/put).
    Uses the per-ticker endpoint so results are actually filtered to `ticker`."""
    # /api/stock/{t}/flow-alerts is DEPRECATED and slated for removal. The
    # option-trades path is supported and additionally returns
    # all_opening_trades / has_sweep / volume_oi_ratio, which is what separates
    # "opening bullish" from "closing bearish" -- a distinction the alert-level
    # premium fields genuinely cannot make.
    r = _get("/api/option-trades/flow-alerts",
             {"ticker_symbol": ticker, "limit": 200})
    if r and not (isinstance(r, dict) and "_error" in r):
        return r
    return _get(f"/api/stock/{ticker}/flow-alerts", {"limit": 100})


def greek_exposure(ticker):
    """Dealer greek (gamma/delta) exposure by strike — UW's own GEX, to cross-check the periscope."""
    return _get(f"/api/stock/{ticker}/greek-exposure")


def gex_by_strike(ticker, spot=None):
    """UW's professional per-strike dealer GEX -> gamma flip (zero-gamma level), call/put walls, net.
    call_gex>0 (dealers long calls), put_gex<0 (short puts); net per strike = call_gex+put_gex."""
    rows = _rows(_get(f"/api/stock/{ticker}/greek-exposure/strike"))
    pts = []
    for r in rows:
        try:
            k = float(r["strike"]); cg = float(r.get("call_gex", 0)); pg = float(r.get("put_gex", 0))
            pts.append((k, cg + pg, cg, pg))
        except Exception:
            continue
    if not pts:
        return None
    pts.sort()

    # RESTRICT TO A BAND AROUND SPOT BEFORE ANYTHING ELSE.
    # UW returns the whole listed ladder -- 787 strikes spanning 200 to 20000 for
    # SPX, 610 spanning 4000 to 50000 for NDX. Walking cumulative gamma across
    # all of it puts the zero-crossing wherever the far tails happen to cancel,
    # which is how SPX reported a flip of 8800 against a spot of 7687, and NDX
    # reported 8000 on a 29,326 index. Those strikes carry negligible gamma and
    # exist only as ladder padding.
    if spot:
        band = [p for p in pts if 0.85 * spot <= p[0] <= 1.15 * spot]
        if len(band) >= 10:
            pts = band

    strikes = [p[0] for p in pts]; nets = [p[1] for p in pts]
    net_total = sum(nets)
    call_wall = max(pts, key=lambda p: p[2])[0]          # biggest positive call gamma = magnet
    put_wall = min(pts, key=lambda p: p[3])[0]           # most negative put gamma = support
    # gamma flip = zero-gamma level: strike where CUMULATIVE net gamma crosses zero (nearest spot)
    cum = 0.0; crosses = []
    prev = None
    for k, n, _, _ in pts:
        cum2 = cum + n
        if prev is not None and (cum < 0 <= cum2 or cum > 0 >= cum2):
            crosses.append(k)
        cum = cum2; prev = k
    flip = None
    if crosses:
        flip = min(crosses, key=lambda k: abs(k - (spot or strikes[len(strikes)//2])))
    # top strikes by |net| for a profile near spot
    ref = spot or (call_wall + put_wall) / 2
    near = sorted([p for p in pts if abs(p[0] - ref) / ref < 0.03], key=lambda p: -abs(p[1]))[:8]
    profile = [{"strike": p[0], "dgex": round(p[1], 4)} for p in sorted(near)]
    return {"net_gex": round(net_total, 3), "gamma_flip": flip, "call_wall": call_wall,
            "put_wall": put_wall, "profile": profile}


def max_pain(ticker):
    """Nearest-expiry max pain = the pin magnet target for 0DTE."""
    rows = _rows(_get(f"/api/stock/{ticker}/max-pain"))
    exps = []
    for r in rows:
        try:
            exps.append((r["expiry"], float(r["max_pain"]), float(r.get("next_lower_strike", 0)),
                         float(r.get("next_upper_strike", 0))))
        except Exception:
            continue
    if not exps:
        return None
    exps.sort()
    e = exps[0]
    return {"expiry": e[0], "max_pain": e[1], "lower": e[2], "upper": e[3]}


def implied_move(ticker):
    """The market's own 1-day (0DTE-ish) implied move % from UW's interpolated IV term structure."""
    rows = _rows(_get(f"/api/stock/{ticker}/interpolated-iv"))
    best = None
    for r in rows:
        try:
            days = int(r.get("days", 0)); mv = float(r.get("implied_move_perc", 0)); vol = float(r.get("volatility", 0))
        except Exception:
            continue
        if days >= 1 and (best is None or days < best[0]):
            # if the raw implied_move rounds to 0 (very short dte), derive from vol: vol*sqrt(days/252)
            mvp = mv * 100 if mv > 0 else (vol / (252 ** 0.5) * (days ** 0.5)) * 100
            best = (days, round(mvp, 2), round(vol * 100, 1))
    return {"days": best[0], "move_pct": best[1], "iv": best[2]} if best else None


def intraday_flow(ticker):
    """Cumulative intraday net options flow (net premium + delta) = live directional pressure."""
    rows = _rows(_get(f"/api/stock/{ticker}/net-prem-ticks"))
    ncp = npp = ndelta = 0.0
    for r in rows:
        ncp += _f(r, "net_call_premium"); npp += _f(r, "net_put_premium"); ndelta += _f(r, "net_delta")
    net_dir = ncp - npp                        # net call buying minus net put buying
    bias = "bullish" if (ndelta > 0 and net_dir > 0) else "bearish" if (ndelta < 0 and net_dir < 0) else "mixed"
    return {"net_call_prem": round(ncp), "net_put_prem": round(npp), "net_delta": round(ndelta),
            "bias": bias, "detail": f"intraday net delta {ndelta:+,.0f}, net call−put prem ${net_dir/1e6:+.1f}M"}


def full_read(ticker, spot=None):
    """One consolidated UW read for the decision-maker: gamma levels + flow + max pain + implied move.
    Combines the classified flow, intraday tick flow, and OI positioning into an overall bias/score."""
    if not available():
        return None
    gex = gex_by_strike(ticker, spot)
    fa = summarize_flow(ticker)          # classified sweep/block flow (calls vs puts bought)
    inf = intraday_flow(ticker)          # cumulative intraday tick flow
    mp = max_pain(ticker)
    im = implied_move(ticker)
    # combine the two flow reads into an overall direction score (-100..+100)
    votes = []
    if fa:
        votes.append(fa["lean"])                 # -1..1
    if inf and inf["bias"] != "mixed":
        votes.append(0.5 if inf["bias"] == "bullish" else -0.5)
    score = sum(votes) / len(votes) if votes else 0
    overall = "bullish" if score > 0.12 else "bearish" if score < -0.12 else "neutral"
    return {"gex": gex, "flow": fa, "intraday": inf, "max_pain": mp, "implied_move": im,
            "overall_bias": overall, "dir_score": round(score * 100)}


def _rows(payload):
    if isinstance(payload, dict):
        for k in ("data", "flow_alerts", "results", "alerts"):
            if isinstance(payload.get(k), list):
                return payload[k]
    return payload if isinstance(payload, list) else []


def _is_call(a):
    """Call vs put from the OCC symbol (…{YYMMDD}{C|P}{strike}) or any type-ish field."""
    import re
    oc = str(a.get("option_chain") or a.get("option_symbol") or "")
    m = re.search(r"[CP](\d{8})$", oc)
    if m:
        return oc[m.start()] == "C"
    typ = str(a.get("type") or a.get("option_type") or a.get("put_call") or "").lower()
    return "call" in typ or typ == "c"


def _f(a, *keys):
    for k in keys:
        v = a.get(k)
        if v not in (None, ""):
            try:
                return float(v)
            except Exception:
                pass
    return 0.0


def summarize_flow(ticker):
    """Real directional flow from UW: aggressive BUYS at the ask vs SELLS at the bid, by call/put.
      bullish premium = calls bought (ask) + puts sold (bid)
      bearish premium = puts bought (ask) + calls sold (bid)
    Returns bias/lean/detail, or None if unavailable."""
    payload = flow_alerts(ticker)
    if not payload or (isinstance(payload, dict) and payload.get("_error")):
        return None
    rows = _rows(payload)
    if not rows:
        return None
    call_ask = call_bid = put_ask = put_bid = 0.0
    skipped_multileg = closing = 0
    for a in rows:
        if not isinstance(a, dict):
            continue
        # A VERTICAL is one trade with a bought leg and a sold leg. Counting its
        # legs independently registers it as both bullish and bearish premium,
        # which quietly pushes `lean` toward zero and mutes real directional
        # flow. Multi-leg trades need their own treatment, so exclude them here
        # rather than double-count them.
        if a.get("has_multileg") or a.get("is_multileg") or a.get("multi_leg"):
            skipped_multileg += 1
            continue
        # OPENING vs CLOSING. `all_opening_trades` looks like the field for this
        # but is a boolean meaning "were ALL legs opening", which is almost
        # never true -- filtering on it discarded 200 of 200 rows and zeroed the
        # signal. The workable test is VOLUME vs OPEN INTEREST: you cannot close
        # more contracts than exist, so volume > OI means new positions are
        # being opened. Weight opening flow fully and closing flow at a third,
        # rather than discarding it.
        w = 1.0
        try:
            vor = float(a.get("volume_oi_ratio") or 0)
            if vor and vor < 1.0:
                w = 0.33
                closing += 1
        except (TypeError, ValueError):
            pass
        ask = _f(a, "total_ask_side_prem", "ask_side_prem")      # premium hitting the ASK = buyers
        bid = _f(a, "total_bid_side_prem", "bid_side_prem")      # premium hitting the BID = sellers
        if not (ask or bid):                                     # fall back to total premium as "buy"
            ask = _f(a, "total_premium", "premium")
        ask *= w; bid *= w
        if _is_call(a):
            call_ask += ask; call_bid += bid
        else:
            put_ask += ask; put_bid += bid
    bullish = call_ask + put_bid            # calls bought + puts sold
    bearish = put_ask + call_bid            # puts bought + calls sold
    tot = bullish + bearish or 1
    lean = (bullish - bearish) / tot                              # -1..+1
    bias = "bullish" if lean > 0.15 else "bearish" if lean < -0.15 else "neutral"
    return {"bias": bias, "lean": round(lean, 2),
            "n_multileg_skipped": skipped_multileg, "n_closing_skipped": closing,
            "bullish_prem": round(bullish), "bearish_prem": round(bearish),
            "call_bought": round(call_ask), "put_bought": round(put_ask),
            "detail": (f"UW real flow: ${call_ask/1e6:.1f}M calls bought / ${put_ask/1e6:.1f}M puts bought "
                       f"→ {bias} (lean {lean:+.2f})"),
            "source": "unusualwhales", "n_alerts": len(rows)}


if __name__ == "__main__":
    import sys
    tk = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    if not available():
        print("No UW key found. Add UNUSUALWHALES_API_KEY to ~/quant-factory/.env or ~/index-daytrading/.env")
    else:
        print("UW key found. Testing flow summary for", tk)
        print(json.dumps(summarize_flow(tk), indent=2))
