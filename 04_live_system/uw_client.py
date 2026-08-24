"""uw_client.py — Unusual Whales integration (READY TO ACTIVATE — just add your API key).

UW gives what a free option-volume proxy CANNOT: real buy-vs-sell classified flow, so we know
whether big money is BUYING calls (bullish) or BUYING puts (bearish) — the strongest direction
signal available. When a key is present this REPLACES the yfinance volume proxy in the periscope.

Activate: put UNUSUALWHALES_API_KEY (or UW_API_KEY) in the environment or in <repo>/.env.
The lookup is `idt.keys`; this module no longer carries its own .env search, because the copy
it used to carry looked in the original author's home directory first and fell through to
nothing on every other machine.

Endpoints are UW's documented REST paths; if any 404 once your key is live, tell me and I'll
pull the current UW API docs and adjust the paths — the scaffolding (auth, parsing, fallback) is done.

This module also carries the SERVICE-HEALTH vocabulary and the HTTP RETRY POLICY that the other
outside-service modules import (ai_desk, analyst, fetch_minutes, committee, master_call). They
live here because this is the module where the three failure states were first told apart: a
missing key, a rejected key and a dead service are not the same thing, and `available()`
reporting one "no" for all three is what let every caller believe UW was live while every
endpoint returned nulls. They are imported, never copied — four copy-pasted `_key()` loaders
are how one machine's home directory ended up hardcoded in four files. Their real home is
`idt/`, next to keys.py, once someone owns that package.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from idt import keys

BASE = "https://api.unusualwhales.com"

# ── service health, shared by every module that talks to an outside service ────
# Five states, one sentence, one shape. A panel loops over status() from each
# module and renders the rows without knowing what any of them do.
#
#   available    the service answered, or has not been asked yet and can be
#   no-key       no credential at all. This is the state that reads to a user as
#                "no credits" or "subscription lapsed" when it is not reported.
#   auth-failed  a credential WAS sent and was REJECTED — lapsed subscription,
#                revoked key, exhausted credit balance. Deliberately separate
#                from no-key: they need opposite fixes.
#   outage       credential fine, the service is unreachable or erroring (5xx,
#                timeout, DNS). Nothing to fix at this end; wait.
#   disabled     switched off on purpose by an environment flag.
STATE_AVAILABLE = "available"
STATE_NO_KEY = "no-key"
STATE_AUTH_FAILED = "auth-failed"
STATE_OUTAGE = "outage"
STATE_DISABLED = "disabled"
STATES = (STATE_AVAILABLE, STATE_NO_KEY, STATE_AUTH_FAILED, STATE_OUTAGE, STATE_DISABLED)


def service_status(module, service, state, detail):
    """The one row shape every status() returns: exactly these five keys, always,
    so the dashboard can loop. `detail` is a sentence meant to be printed as-is."""
    if state not in STATES:
        raise ValueError(f"unknown service state {state!r}; expected one of {STATES}")
    return {"module": module, "service": service, "state": state,
            "ok": state == STATE_AVAILABLE, "detail": detail}


# ── HTTP retry policy, shared with fetch_minutes ──────────────────────────────
# Retry TRANSPORT errors, 5xx and 429 only. A 401 or 403 is a rejected key and
# will be rejected identically on every attempt: retrying it burns the rate
# limit and, worse, delays the honest "auth-failed" the panel needs. The rest of
# 4xx (404 a wrong path, 422 a bad parameter) is a bug at this end and repeating
# it cannot fix it.
#
# The budget is small on purpose. These calls happen inside a page render, so a
# request that keeps failing has to give up in seconds. Two sleeps of 0.4s and
# 0.8s is the whole cost of a retry storm here.
HTTP_TIMEOUT_S = 15.0        # hard per-attempt timeout; no call may hang a render
HTTP_ATTEMPTS = 3
HTTP_BACKOFF_S = 0.4         # first sleep; doubles each attempt
HTTP_BACKOFF_CAP_S = 2.0
HTTP_TOTAL_BUDGET_S = 25.0   # wall clock across all attempts, sleeps included


class Transient(Exception):
    """A failure worth trying again: a timeout, a dropped connection, a 5xx or a
    429. Anything raised that is NOT this is permanent and is re-raised at once."""


def retryable_status(code):
    """True for the HTTP codes that can succeed on a second try. See the comment
    above: 401/403 are excluded deliberately, not by oversight."""
    try:
        code = int(code)
    except (TypeError, ValueError):
        return False
    return code == 429 or 500 <= code <= 599


def with_backoff(attempt, attempts=HTTP_ATTEMPTS, base=HTTP_BACKOFF_S,
                 cap=HTTP_BACKOFF_CAP_S, budget=HTTP_TOTAL_BUDGET_S, label=""):
    """Run `attempt()` with bounded exponential backoff.

    `attempt` raises Transient for the retryable failures and anything else for
    the permanent ones. Returns the attempt's value, or re-raises the last
    Transient once the attempts or the wall-clock budget run out."""
    deadline = time.monotonic() + budget
    last = None
    for i in range(max(1, attempts)):
        try:
            return attempt()
        except Transient as e:
            last = e
            if i == attempts - 1:
                break
            delay = min(cap, base * (2 ** i))
            if time.monotonic() + delay >= deadline:
                break                      # out of budget: fail now, honestly
            time.sleep(delay)
    raise last if last is not None else Transient(f"{label or 'request'}: no attempt was made")

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
    """True only if UW is usable — enabled, key present, and not auth-tripped.
    `status()` says WHICH of those it is; this is the one-bit answer for callers
    that only need to pick between UW and the yfinance proxy."""
    if UW_DISABLED or _AUTH_FAILS["tripped"]:
        return False
    return bool(keys.get("UNUSUALWHALES_API_KEY"))


# Last transport failure, so status() can report an OUTAGE instead of the client
# quietly returning None and the panel showing an empty flow section. Cleared by
# the next healthy call.
_LAST_TRANSPORT_ERROR = {"detail": "", "ts": 0.0, "said": 0.0}
_OUTAGE_WINDOW_S = 300       # after five quiet minutes, stop calling it an outage


def _note_transport_error(detail):
    """Record and SAY a failed request. It used to return {"_error": ...} into a
    caller that dropped it on the floor, so a dead network looked like a quiet
    day with no flow. Printing is rate-limited to one line a minute per message
    so an outage does not bury the log it is supposed to explain."""
    detail = str(detail)[:120]
    now = time.time()
    prev = _LAST_TRANSPORT_ERROR
    if detail != prev["detail"] or now - prev["said"] > 60:
        print(f"uw_client: request failed — {detail}")
        prev["said"] = now
    prev["detail"] = detail
    prev["ts"] = now


def status():
    """Which of the five states UW is in, as one printable row. See STATES."""
    svc = ("uw_client", "unusualwhales")
    if UW_DISABLED:
        return service_status(*svc, STATE_DISABLED,
                              "Unusual Whales is switched off (UW_DISABLED=1). Flow panels use the "
                              "yfinance volume proxy, which cannot tell buying from selling.")
    if _AUTH_FAILS["tripped"]:
        return service_status(*svc, STATE_AUTH_FAILED,
                              f"Unusual Whales rejected the key {_AUTH_FAILS['n']} times in a row. That is "
                              "what a lapsed subscription looks like: the key is present and every call "
                              "returns 401. Disabled for this process; panels use the yfinance proxy.")
    if not keys.get("UNUSUALWHALES_API_KEY"):
        return service_status(*svc, STATE_NO_KEY,
                              "No UNUSUALWHALES_API_KEY in the environment or in the repo .env. Real "
                              "buy-vs-sell flow is off; panels use the yfinance volume proxy.")
    err = _LAST_TRANSPORT_ERROR
    if err["ts"] and time.time() - err["ts"] < _OUTAGE_WINDOW_S:
        return service_status(*svc, STATE_OUTAGE,
                              f"Key accepted, but the last call failed after {HTTP_ATTEMPTS} tries: "
                              f"{err['detail']}. Nothing to fix at this end.")
    return service_status(*svc, STATE_AVAILABLE,
                          "Key present and no failed call in this process.")


_CACHE = {}          # {url: (expiry_ts, payload)} — short TTL to protect the UW rate limit
_TTL = 20            # seconds. Measured quota is 30,000/day with no practical
                     # per-minute cap (x-uw-req-per-minute-remaining: 1000000) and
                     # we use ~130/day, so the old 45s was ~200x too conservative.


def _get(path, params=None):
    # Single chokepoint: every endpoint routes through here, so one guard
    # disables the whole client and saves the network round-trips too.
    if UW_DISABLED or _AUTH_FAILS["tripped"]:
        return None
    key = keys.get("UNUSUALWHALES_API_KEY")
    if not key:
        return None
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    hit = _CACHE.get(url)
    if hit and hit[0] > time.time():
        return hit[1]
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}", "Accept": "application/json",
        "User-Agent": "index-daytrading/1.0"})

    def attempt():
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if retryable_status(e.code):
                raise Transient(f"HTTP {e.code} {e.reason}") from e
            raise                                   # 401/403/404: permanent, stop now
        except urllib.error.URLError as e:          # DNS, refused, TLS, timeout
            raise Transient(f"{type(e).__name__}: {str(e.reason)[:80]}") from e
        except (TimeoutError, OSError) as e:        # socket timeout, connection reset
            raise Transient(f"{type(e).__name__}: {str(e)[:80]}") from e
        except json.JSONDecodeError as e:
            # A 200 carrying non-JSON is almost always a proxy or maintenance
            # page, which clears. Bounded by the attempt count either way.
            raise Transient(f"malformed JSON from {path}: {str(e)[:60]}") from e

    try:
        payload = with_backoff(attempt, label=path)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            # A lapsed subscription drops every x-uw-* header, which is a
            # positive signal rather than an inference from repeated failure.
            headers = getattr(e, "headers", None) or {}
            if not any(str(k).lower().startswith("x-uw-") for k in headers.keys()):
                _AUTH_FAILS["n"] = _AUTH_TRIP_AFTER - 1
            _note_auth_failure()
        else:
            _note_transport_error(f"HTTP {e.code}: {e.reason}")
        return {"_error": f"HTTPError: HTTP Error {e.code}: {e.reason}"}
    except Transient as e:
        _note_transport_error(str(e))
        return {"_error": f"Transient: {str(e)[:80]}"}
    except Exception as e:
        # Not silence: an unexpected type here is a bug worth seeing in the log,
        # and the caller still gets an _error rather than a plausible-looking None.
        _note_transport_error(f"{type(e).__name__}: {str(e)[:80]}")
        return {"_error": f"{type(e).__name__}: {str(e)[:80]}"}
    _CACHE[url] = (time.time() + _TTL, payload)     # cache only successful pulls
    _AUTH_FAILS["n"] = 0                            # healthy call clears the streak
    _LAST_TRANSPORT_ERROR["ts"] = 0.0               # ...and clears the outage flag
    return payload


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
    bad = 0
    for r in rows:
        try:
            k = float(r["strike"]); cg = float(r.get("call_gex", 0)); pg = float(r.get("put_gex", 0))
            pts.append((k, cg + pg, cg, pg))
        except (KeyError, TypeError, ValueError):
            # One malformed strike row is normal; a payload where MOST rows fail
            # is a schema change, and dropping it silently is how a lapsed feed
            # of nulls reached the render looking like a thin ladder.
            bad += 1
            continue
    if bad and bad >= max(1, len(rows) // 2):
        print(f"uw_client: {bad} of {len(rows)} {ticker} strike rows unparseable — check the UW schema")
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
    bad = 0
    for r in rows:
        try:
            exps.append((r["expiry"], float(r["max_pain"]), float(r.get("next_lower_strike", 0)),
                         float(r.get("next_upper_strike", 0))))
        except (KeyError, TypeError, ValueError):
            bad += 1
            continue
    if bad and not exps:
        print(f"uw_client: every {ticker} max-pain row was unparseable ({bad} rows) — returning nothing "
              "rather than a made-up pin level")
    if not exps:
        return None
    exps.sort()
    e = exps[0]
    return {"expiry": e[0], "max_pain": e[1], "lower": e[2], "upper": e[3]}


def implied_move(ticker):
    """The market's own 1-day (0DTE-ish) implied move % from UW's interpolated IV term structure."""
    rows = _rows(_get(f"/api/stock/{ticker}/interpolated-iv"))
    best = None
    bad = 0
    for r in rows:
        try:
            days = int(r.get("days", 0)); mv = float(r.get("implied_move_perc", 0)); vol = float(r.get("volatility", 0))
        except (TypeError, ValueError):
            bad += 1
            continue
        if days >= 1 and (best is None or days < best[0]):
            # if the raw implied_move rounds to 0 (very short dte), derive from vol: vol*sqrt(days/252)
            mvp = mv * 100 if mv > 0 else (vol / (252 ** 0.5) * (days ** 0.5)) * 100
            best = (days, round(mvp, 2), round(vol * 100, 1))
    if best is None and bad:
        print(f"uw_client: {bad} of {len(rows)} {ticker} interpolated-IV rows unparseable — no implied move")
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


def _f(a, *names):
    # `names`, not `keys`: this module imports idt.keys, and a parameter of that
    # name shadows it for anyone who later needs the key inside this function.
    for k in names:
        v = a.get(k)
        if v not in (None, ""):
            try:
                return float(v)
            except (TypeError, ValueError):
                # A single non-numeric premium field is normal in this payload;
                # try the next alias rather than failing the whole alert.
                continue
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
            # No usable volume/OI on this alert. Weight it fully (w stays 1.0)
            # rather than guessing it is closing flow: the opening-vs-closing
            # test is the whole reason this field is read, and a guess here
            # mutes real directional flow.
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
    st = status()
    print(f"UW {st['state']}: {st['detail']}")
    if not available():
        print("Add UNUSUALWHALES_API_KEY to the environment or to the repo .env (see .env.example).")
    else:
        print("UW key found. Testing flow summary for", tk)
        print(json.dumps(summarize_flow(tk), indent=2))
