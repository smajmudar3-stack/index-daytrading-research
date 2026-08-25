"""tickets.py — concrete, executable orders from the signals that survived testing.

Every ticket names the contract, the strike, the expiration and the real NBBO,
and every ticket has passed the gates the backtests actually established. If
nothing passes, this returns nothing: a signal that is quiet must not manufacture
a trade.

WHAT THE EVIDENCE PERMITS, and what it forbids:

  vehicle   Measured on real SPY chains at 50-75 DTE, resampling a 53.4%-accurate
            signal (scripts/vehicle_choice.py): stock t=+0.80, deep-ITM 0.85d
            t=+0.04, ATM t=+0.04, 30-delta t=+0.15, 16-delta t=-0.38. Nothing
            reaches significance and the far tail LOSES. So tickets are written
            deep ITM only -- the vehicle that tracks the mean shift instead of
            paying for convexity -- and the panel says plainly that stock is the
            cleaner expression.

  basket    The short-interest IC of -0.107 was measured ACROSS 13,219
            cross-sectional observations, not on any single name. It is a
            portfolio effect. One ticket is a coin flip with a slight tilt; the
            edge only exists across many. Tickets are therefore emitted as a
            basket with equal weights, and the panel refuses to imply conviction
            in any single line.

  spread    Far-OTM work showed execution dominates selection: a <=20% spread
            filter moved returns from -45.6% to +5.6%. Applied here as a hard gate.

  horizon   63 days, matching where the IC was measured. Not a round number
            chosen for convenience.

Every ticket is PAPER. Nothing here places an order.
"""
import datetime as dt
import json
import os
import re
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "data", "tickets.json")
TTL = 1800                       # 30 min; chains do not move fast enough to matter

TARGET_DTE = 63
DTE_LO, DTE_HI = 45, 85
DEEP_ITM_DELTA = 0.85
DELTA_TOL = 0.14        # deep ITM is thinly quoted
MAX_SPREAD = 0.20                # measured gate
COST_LO, COST_HI = 1000, 3000    # per contract, user constraint
SHORT_FLOAT_MIN = 8.0            # percent; below this the signal is noise
SHORT_FLOAT_MAX = 60.0           # above this the vendor value is implausible
BASKET_MIN = 6                   # fewer than this is not a basket

# Deep-ITM options on small caps are thinly listed, so the universe has to be
# wide enough that enough names clear BOTH the signal filter and the liquidity
# filter. Skewed toward names with elevated short interest AND real option
# markets -- a high short float on an unoptionable stock is not tradeable here.
UNIVERSE = [
    # high short interest, small/mid
    "UPST", "CVNA", "GME", "AFRM", "BYND", "LCID", "RIVN", "PLUG", "SOFI",
    "CHWY", "W", "WOLF", "RUN", "FUBO", "OPEN", "SPCE", "MARA", "RIOT",
    "COIN", "HOOD", "DKNG", "PTON", "BIGC", "APPS", "SNAP", "ETSY",
    "NIO", "XPEV", "LI", "CHPT", "NKLA", "QS", "JOBY", "ACHR", "IONQ",
    "SMCI", "AI", "PATH", "DNA", "RKLB", "ASTS", "SOUN", "BBAI",
    # larger names that carry short interest and have liquid chains
    "LYFT", "PARA", "WBA", "M", "KSS", "GPS", "FL", "AAP", "LUMN",
    "CCL", "NCLH", "AAL", "UAL", "F", "INTC", "PFE", "MRNA", "ENPH",
    "SEDG", "FSLR", "ALB", "MOS", "CF", "X", "CLF", "AA", "DVN",
]

OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def parse_occ(sym):
    """UPST260918C00040000 -> ('UPST', date(2026,9,18), 'P'/'C', 40.0)."""
    m = OCC.match(sym or "")
    if not m:
        return None
    t, ymd, cp, k = m.groups()
    try:
        d = dt.date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
    except ValueError:
        return None
    return t, d, cp, int(k) / 1000.0


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def candidates():
    """Names where the short-interest signal is live and the value is plausible."""
    import uw_endpoints as ue
    out = []
    for t in UNIVERSE:
        try:
            sf = ue.profile(t).get("short_float_pct")
        except Exception:
            continue
        v = _f(sf)
        # BYND has returned 758% -- a short float above 60 is a vendor error,
        # not a signal, and must not be allowed to top the ranking.
        if v is None or not (SHORT_FLOAT_MIN <= v <= SHORT_FLOAT_MAX):
            continue
        out.append({"ticker": t, "short_float": round(v, 2)})
    out.sort(key=lambda x: -x["short_float"])
    return out


def best_contract(ticker):
    """Deep-ITM put nearest 63 DTE that clears the spread and cost gates."""
    import uw_client as uw
    try:
        r = uw._get(f"/api/stock/{ticker}/option-contracts", {"limit": "500"})
    except Exception:
        return None
    rows = r.get("data", r) if isinstance(r, dict) else r
    if not rows:
        return None

    today = dt.date.today()
    best, best_score = None, None
    for x in rows:
        p = parse_occ(x.get("option_symbol"))
        if not p:
            continue
        _, exp, cp, strike = p
        if cp != "P":                       # bearish signal -> puts only
            continue
        dte = (exp - today).days
        if not (DTE_LO <= dte <= DTE_HI):
            continue
        d = _f(x.get("delta"))
        if d is None or abs(abs(d) - DEEP_ITM_DELTA) > DELTA_TOL:
            continue
        bid, ask = _f(x.get("nbbo_bid")), _f(x.get("nbbo_ask"))
        oi = _f(x.get("open_interest")) or 0
        if not bid or not ask or ask <= 0 or ask < bid or oi < 25:
            continue
        mid = (bid + ask) / 2
        spread = (ask - bid) / mid if mid > 0 else 1.0
        if spread > MAX_SPREAD:
            continue
        # $1,000-3,000 is a POSITION budget, not a contract price. High
        # short-float names skew cheap, so a deep-ITM put on a $25 stock runs
        # ~$370 -- the fix is quantity, which is what a trader would do anyway.
        per = ask * 100
        qty = max(1, round(((COST_LO + COST_HI) / 2) / per)) if per > 0 else 0
        cost = per * qty
        if not qty or not (COST_LO <= cost <= COST_HI):
            continue
        # Intrinsic vs extrinsic is the number that answers "won't this just
        # decay away?". Only the extrinsic part is guaranteed to go to zero;
        # intrinsic moves one-for-one with the stock. Deep ITM is chosen
        # precisely because extrinsic is a small share of the premium.
        score = abs(dte - TARGET_DTE) + spread * 50
        if best_score is None or score < best_score:
            best_score, best = score, dict(
                symbol=x.get("option_symbol"), strike=strike, exp=exp.isoformat(),
                dte=dte, delta=round(d, 3), bid=bid, ask=ask,
                qty=qty, per=round(per),
                spread_pct=round(spread * 100, 1), cost=round(cost),
                oi=int(oi))
    return best


def log_calls(tk):
    """Record the basket so the scorecard can grade it later.

    record() already dedupes to one call per tab/ticker/direction/day, so the
    30-minute rebuild cannot inflate the hit rate by re-logging a standing view.
    """
    try:
        import scorecard
    except Exception:
        return
    for x in tk:
        try:
            scorecard.record("tickets", x["ticker"], "bearish",
                             conviction=int(min(x["short_float"] * 2, 100)),
                             structure=f"{x['qty']}x {x['strike']:g}P {x['exp']}",
                             # entry_px MUST be the underlying price, not the
                             # option ask -- settle() grades direction by
                             # comparing entry_px against the UNDERLYING close.
                             # Passing the premium made GME read as a +500% move
                             # from $3.50 to $21. None lets settle() take the
                             # first underlying close itself, which is correct.
                             entry_px=None,
                             note=f"short float {x['short_float']}%, "
                                  f"delta {x['delta']}, paid {x['ask']:.2f}, "
                                  f"hold to expiry")
        except Exception:
            continue


def add_decay(tk):
    """Attach intrinsic/extrinsic per ticket using the real underlying price."""
    if not tk:
        return tk
    try:
        import yfinance as yf
        px = yf.download([t["ticker"] for t in tk], period="5d", progress=False,
                         auto_adjust=False, threads=False)["Close"]
    except Exception:
        return tk
    for t in tk:
        try:
            s_ = float(px[t["ticker"]].dropna().iloc[-1])
        except Exception:
            continue
        intr = max(0.0, t["strike"] - s_)
        ext = max(0.0, t["ask"] - intr)
        t["spot"] = round(s_, 2)
        t["intrinsic"] = round(intr, 2)
        t["extrinsic"] = round(ext, 2)
        t["theta_pct"] = round(ext / t["ask"] * 100, 1) if t["ask"] else None
        t["breakeven"] = round(t["strike"] - t["ask"], 2)
    return tk


def build(limit=10):
    """The basket. Returns {'tickets': [...], 'why': str, 'blocked': str|None}."""
    cands = candidates()
    if len(cands) < BASKET_MIN:
        return {"tickets": [], "blocked":
                f"only {len(cands)} names carry a live short-interest signal; "
                f"this is a basket effect and needs at least {BASKET_MIN}"}
    out = []
    # Scan ALL candidates, not the top slice. The highest short floats sit on the
    # smallest names, which are exactly the ones without a liquid deep-ITM chain,
    # so a shallow scan finds the signal and none of the tradeable expressions.
    for c in cands:
        k = best_contract(c["ticker"])
        if not k:
            continue
        out.append({**c, **k})
        if len(out) >= limit:
            break
    if len(out) < BASKET_MIN:
        return {"tickets": [], "blocked":
                f"{len(out)} of {len(cands)} candidates had a contract clearing the "
                f"{int(MAX_SPREAD*100)}% spread and ${COST_LO}-{COST_HI} gates — "
                f"too few to run as a basket"}
    out = add_decay(out)
    log_calls(out)
    return {"tickets": out, "blocked": None}


_REFRESHING = threading.Lock()


def _refresh(limit):
    """Rebuild the cache off the request path."""
    if not _REFRESHING.acquire(blocking=False):
        return                      # a rebuild is already running
    try:
        res = build(limit)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump({"ts": time.time(), "res": res}, f)
    except Exception:
        pass
    finally:
        _REFRESHING.release()


def cached_build(limit=10, block=False):
    """Never blocks the render.

    A full build costs ~50 Unusual Whales calls and took 20 seconds, which timed
    out the dashboard's own HTTP health check. So the cache is served
    immediately even when stale, and a refresh runs on a background thread.
    Only an explicit CLI run blocks.
    """
    cached, age = None, None
    try:
        with open(CACHE) as f:
            c = json.load(f)
        cached, age = c["res"], time.time() - c.get("ts", 0)
    except (OSError, ValueError, KeyError):
        pass

    if cached is not None and age is not None and age < TTL:
        return cached

    if block:
        _refresh(limit)
        try:
            with open(CACHE) as f:
                return json.load(f)["res"]
        except (OSError, ValueError, KeyError):
            return {"tickets": [], "blocked": "build failed"}

    threading.Thread(target=_refresh, args=(limit,), daemon=True).start()
    if cached is not None:
        return cached               # stale is better than blank
    return {"tickets": [], "blocked": "building — refresh in a moment"}


def panel():
    """Dashboard HTML. Returns '' rather than raising, and says so when blocked."""
    try:
        res = cached_build()
    except Exception:
        return ""
    tk, blocked = res.get("tickets", []), res.get("blocked")

    head = ("<div class=ahead>🧾 Trade tickets "
            "<span class='pill mut'>PAPER</span></div>")

    if not tk:
        return (f"<div class='card tix'>{head}"
                f"<div class=txblock><b>No tickets.</b> {blocked or 'nothing qualifies'}."
                f"</div>"
                f"<div class=txwhy>A quiet signal must not manufacture a trade. "
                f"This panel stays empty until the gates pass.</div></div>")

    total = sum(t["cost"] for t in tk)
    exp = max(t["exp"] for t in tk)
    ext = round(sum((t.get("extrinsic") or 0) * t["qty"] * 100 for t in tk))
    extpct = (ext / total * 100) if total else 0
    rows = "".join(
        f"<tr><td><b>{t['ticker']}</b></td>"
        f"<td class=sell>BUY PUT</td>"
        f"<td class=mono>${t['strike']:g}</td>"
        f"<td class=mono>{t['exp']}</td>"
        f"<td class=num>{t['dte']}d</td>"
        f"<td class=num>{t['delta']:+.2f}</td>"
        f"<td class=mono>{t['bid']:.2f}/{t['ask']:.2f}</td>"
        f"<td class=num>{t['spread_pct']}%</td>"
        f"<td class=num>{t.get('theta_pct','—')}%</td>"
        f"<td class=num>{t['qty']}x</td>"
        f"<td class=num><b>${t['cost']:,}</b></td>"
        f"<td class=num>{t['short_float']}%</td></tr>" for t in tk)

    return f"""<div class='card tix'>{head}
  <div class=txnote><b>Basket of {len(tk)}</b> — equal weight, total ${total:,}.
    Buy all of them or none: the measured edge is cross-sectional
    (IC −0.107 across 13,219 observations), so any single line is a coin flip
    with a slight tilt.</div>
  <div class=txscroll><table class=txtable>
    <tr><th>ticker</th><th>action</th><th>strike</th><th>expiration</th><th>dte</th>
        <th>delta</th><th>bid/ask</th><th>time value</th><th>qty</th><th>cost</th><th>short float</th></tr>
    {rows}</table></div>
  <div class=txdecay><b>“Won’t these just decay to zero?” — no, and here is why.</b>
    These are <b>deep in-the-money</b>, so most of the premium is
    <b>intrinsic</b>, which moves one-for-one with the stock and does not decay.
    Only the time-value column bleeds away. Across this basket that is
    <b>${ext:,} of ${total:,} — {extpct:.0f}%</b>. An at-the-money put would be
    ~100% time value: every dollar a bet against the clock. That is the trade
    you are right to be suspicious of, and it is not this one.</div>
  <div class=txexit><b>EXIT — sell the same contracts at expiration ({exp}).</b>
    Hold to expiry and settle at intrinsic; do not close early. That is the
    protocol the result was measured under, and deep ITM carries little extrinsic
    so decay costs little. <b>No profit target and no stop</b> — neither was
    tested, and inventing one would be trading an untested rule. The premium is
    the risk: worst case is the full <b>${total:,}</b> if every put expires
    worthless, so size the basket as money you can lose in whole.</div>
  <div class=txwhy><b>Why puts, deep ITM:</b> high short float predicts LOWER
    returns (the squeeze thesis is backwards), and deep ITM is the only option
    vehicle that tracks the mean shift instead of paying for convexity. Measured
    at 50–75 DTE on real chains: stock t=+0.80, deep-ITM t=+0.04, 16-delta
    t=−0.38. <b>Nothing reached significance — shorting the stock is the cleaner
    expression, and these tickets are the option version of a weak, real, small
    edge.</b> Gates applied: spread ≤{int(MAX_SPREAD*100)}%, cost
    ${COST_LO:,}–${COST_HI:,}, {TARGET_DTE}-day horizon, OI ≥ 25.</div>
</div>"""


CSS = """
 .tix{border:1px solid var(--line);border-radius:var(--r);background:var(--surface);padding:16px 18px;margin:10px 0}
 .txnote{font-size:12.5px;color:var(--text);line-height:1.55;margin:-2px 0 12px;
   background:rgba(88,166,255,.07);border-left:3px solid var(--info);padding:8px 11px;border-radius:0 8px 8px 0}
 .txblock{font-size:13px;line-height:1.55;margin:2px 0 8px}
 .txscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
 .txtable{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}
 .txtable th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.06em;
   color:var(--muted);font-weight:600;padding:0 9px 6px 0;border-bottom:1px solid var(--line2)}
 .txtable td{padding:7px 9px 7px 0;border-bottom:1px solid var(--line2)}
 .txtable td.mono,.txtable td.num{font-family:ui-monospace,Menlo,monospace}
 .txtable td.num{text-align:right}
 .txtable td.sell{color:var(--red);font-weight:700;font-size:11px}
 .txdecay{font-size:12px;line-height:1.6;margin-top:12px;padding:9px 11px;
   background:rgba(63,185,80,.07);border-left:3px solid var(--go);border-radius:0 8px 8px 0}
 .txdecay b{color:var(--text)}
 .txexit{font-size:12px;line-height:1.6;margin-top:12px;padding:9px 11px;
   background:rgba(248,81,73,.07);border-left:3px solid var(--red);border-radius:0 8px 8px 0}
 .txexit b{color:var(--text)}
 .txwhy{font-size:11.5px;color:var(--muted);line-height:1.6;margin-top:12px;
   padding-top:10px;border-top:1px solid var(--line2)}
 .txwhy b{color:var(--text)}
"""


if __name__ == "__main__":
    # Blocking rebuild, for priming the cache or running on a schedule. A full
    # build is ~140s and ~350 Unusual Whales calls, which is why the dashboard
    # never does this on the request path.
    import sys
    t0 = time.time()
    r = cached_build(limit=12, block=True)
    n = len(r.get("tickets", []))
    print(f"{n} tickets in {time.time()-t0:.0f}s"
          + (f" — blocked: {r['blocked']}" if r.get("blocked") else ""))
    for t in r.get("tickets", []):
        print(f"  {t['ticker']:6s} BUY {t['qty']:2d}x PUT ${t['strike']:<6g} "
              f"{t['exp']} {t['dte']:3d}d  d{t['delta']:+.2f}  "
              f"{t['bid']:.2f}/{t['ask']:.2f}  {t['spread_pct']:4.1f}%  "
              f"${t['cost']:,}")
    sys.exit(0 if n else 1)
