"""option_pricer.py — real option quotes and multi-leg structure pricing.

Why this exists: until now the agent's P&L was inferred from the UNDERLYING's move times an assumed
leverage factor. That's a guess. This module prices the agent's actual structures off live bid/ask, so
entry and exit premium — and therefore the track record and the graduation gate — are real numbers.

Guardrail design follows the tasty-agent order-tool contract (RESEARCH_BOTS.md #4):
  - quote-derived MID pricing only (never last-traded, which goes stale and lies on illiquid strikes)
  - a bid/ask sanity check that REFUSES to price an untradeable strike rather than returning a number
  - liquidity floors (open interest / non-zero bid)
  - everything returns None on failure instead of a plausible-looking fabrication
"""
import os
import warnings
from datetime import datetime
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

YF = {"SPX": "^SPX", "NDX": "^NDX", "RUT": "^RUT", "VIX": "^VIX"}

# Liquidity guardrails — a quote failing these is not tradeable, so we refuse to price it.
# The package-spread limit is TIERED because the same number means different things by instrument:
# SPY/QQQ 0DTE price within pennies of mid, while an equity monthly vertical legitimately quotes wide
# and still fills near mid at a real broker. These are PROVISIONAL — gate_log.jsonl records every
# rejection with its actual package spread, so they should be recalibrated from observed data rather
# than left at a guess.
MAX_SPREAD_PCT = 35.0                     # default / liquid ETF + index
MAX_SPREAD_PCT_EQUITY = 60.0              # single-name, longer-dated
LIQUID = {"SPY", "QQQ", "IWM", "SPX", "NDX", "XSP", "RUT"}
MIN_OI = 5

_CACHE = {}
_CACHE_TTL = 90            # seconds — the scan cycle is 5 min, this keeps a cycle internally consistent


def _yf(sym):
    return YF.get((sym or "").upper(), (sym or "").upper())


def _chain(sym, expiry):
    key = (sym, expiry)
    now = datetime.now().timestamp()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    try:
        import yfinance as yf
        ch = yf.Ticker(_yf(sym)).option_chain(expiry)
        _CACHE[key] = (now, ch)
        return ch
    except Exception:
        return None


def expiries(sym):
    try:
        import yfinance as yf
        return list(yf.Ticker(_yf(sym)).options or [])
    except Exception:
        return []


def resolve_expiry(sym, kind):
    """Map the agent's expiry language ('0DTE' / 'weekly' / '~35DTE') to a real expiry date string."""
    exps = expiries(sym)
    if not exps:
        return None
    today = datetime.now(ET).date()
    kind = (kind or "").upper()
    parsed = []
    for e in exps:
        try:
            parsed.append((datetime.strptime(e, "%Y-%m-%d").date(), e))
        except Exception:
            continue
    if not parsed:
        return None
    parsed.sort()
    if kind == "0DTE":
        for d, e in parsed:
            if d == today:
                return e
        return parsed[0][1]
    if kind == "WEEKLY":
        for d, e in parsed:
            if (d - today).days >= 2:
                return e
        return parsed[-1][1]
    # anything else: target the stated DTE, default 35
    target = 35
    digits = "".join(c for c in kind if c.isdigit())
    if digits:
        target = int(digits)
    return min(parsed, key=lambda p: abs((p[0] - today).days - target))[1]


def quote(sym, expiry, strike, right):
    """Live quote for one option. Returns None if it isn't cleanly tradeable."""
    ch = _chain(sym, expiry)
    if ch is None:
        return None
    df = ch.calls if right.upper().startswith("C") else ch.puts
    if df is None or df.empty:
        return None
    try:
        row = df.iloc[(df["strike"] - float(strike)).abs().argmin()]
    except Exception:
        return None
    bid, ask = float(row.get("bid") or 0), float(row.get("ask") or 0)
    oi = int(row.get("openInterest") or 0)
    if bid <= 0 or ask <= 0 or ask < bid:
        return None                                  # no two-sided market — refuse, don't guess
    mid = (bid + ask) / 2
    spread_pct = (ask - bid) / mid * 100 if mid else 999
    # Per-leg we only enforce LIQUIDITY. The spread test is applied to the PACKAGE in price_structure:
    # a vertical's OTM wing is often wide on its own while the net debit prices tightly, and rejecting
    # on the worst leg would refuse most legitimate equity spreads.
    ok = oi >= MIN_OI
    return {"strike": float(row["strike"]), "right": right.upper()[0], "bid": bid, "ask": ask,
            "mid": round(mid, 3), "spread_pct": round(spread_pct, 1), "oi": oi,
            "tradeable": bool(ok),
            "reject": None if ok else f"open interest {oi} < {MIN_OI}"}


def listed_strikes(sym, expiry, right):
    """The strikes that actually EXIST for this expiry/right, sorted.

    The listed grid is not uniform — near the close it can read [765, 766, 770, 772] — so computing
    strikes from an assumed increment silently lands on strikes that don't exist, which then snap onto
    a neighbour and produce a structure nobody intended."""
    ch = _chain(sym, expiry)
    if ch is None:
        return []
    df = ch.calls if right.upper().startswith("C") else ch.puts
    if df is None or df.empty:
        return []
    try:
        return sorted(float(k) for k in df["strike"].tolist())
    except Exception:
        return []


def pick_strike(sym, expiry, right, target, away_from=None, min_distance=0.0):
    """Nearest LISTED strike to `target`. If `away_from` is given, the result must differ from it and
    sit at least `min_distance` further out in the correct direction (used for wings)."""
    ks = listed_strikes(sym, expiry, right)
    if not ks:
        return None
    if away_from is None:
        return min(ks, key=lambda k: abs(k - target))
    if target < away_from:                      # wing below the short strike (put side)
        cand = [k for k in ks if k <= away_from - max(min_distance, 1e-9)]
        return max(cand) if cand else None
    cand = [k for k in ks if k >= away_from + max(min_distance, 1e-9)]
    return min(cand) if cand else None


def price_structure(sym, expiry, legs):
    """Net mid price of a multi-leg structure.

    legs: [{"right":"C","strike":180,"qty":1}, {"right":"C","strike":190,"qty":-1}]
          qty > 0 = long (you pay), qty < 0 = short (you receive)
    Returns {net: +debit / -credit, legs: [...], tradeable: bool, reject: str|None}"""
    out, net, bad = [], 0.0, []
    for lg in legs:
        q = quote(sym, expiry, lg["strike"], lg["right"])
        if q is None:
            bad.append(f"no two-sided market at {lg['strike']}{lg['right']}")
            continue
        if not q["tradeable"]:
            bad.append(f"{lg['strike']}{lg['right']}: {q['reject']}")
        net += q["mid"] * float(lg["qty"])
        out.append({**q, "qty": lg["qty"]})
    if len(out) != len(legs):
        return {"net": None, "legs": out, "tradeable": False, "reject": "; ".join(bad)}
    # Requested strikes snap to the nearest LISTED strike. If two legs of the same right collapse onto
    # the same listed strike, the structure priced is not the structure intended (and nets to ~0) —
    # refuse rather than record a fictitious trade.
    seen = {}
    for lgq in out:
        k = (lgq["right"], lgq["strike"])
        seen[k] = seen.get(k, 0) + 1
        if seen[k] > 1:
            return {"net": None, "legs": out, "tradeable": False,
                    "reject": f"legs collapsed onto the same listed strike ({lgq['strike']}{lgq['right']}) — "
                              "strike increment too wide for the requested width"}
    # PACKAGE-level spread: what you'd actually pay crossing every leg vs. what you'd receive.
    # This is the real slippage cost of the structure, and the number worth gating on.
    worst = sum((lg["ask"] if lg["qty"] > 0 else lg["bid"]) * lg["qty"] for lg in out)
    best = sum((lg["bid"] if lg["qty"] > 0 else lg["ask"]) * lg["qty"] for lg in out)
    pkg_spread_pct = abs(worst - best) / abs(net) * 100 if net else 999
    limit = MAX_SPREAD_PCT if (sym or "").upper() in LIQUID else MAX_SPREAD_PCT_EQUITY
    if pkg_spread_pct > limit:
        bad.append(f"package spread {pkg_spread_pct:.0f}% of net > {limit:.0f}% — slippage eats the edge")
    return {"net": round(net, 3), "legs": out, "tradeable": not bad,
            "reject": "; ".join(bad) if bad else None,
            "pkg_spread_pct": round(pkg_spread_pct, 1),
            "worst_fill": round(worst, 3),
            "max_loss": _max_loss(out, net)}


def _max_loss(legs, net):
    """Defined-risk max loss for the common two-leg vertical; None when it isn't determinable."""
    if len(legs) != 2:
        return None
    a, b = legs
    if a["right"] != b["right"]:
        return None
    width = abs(a["strike"] - b["strike"])
    if net > 0:
        return round(net, 3)                    # debit spread: you can only lose the debit
    return round(width + net, 3)                # credit spread: width minus credit received


def parse_legs(legs_text, structure, spot, strikes=None):
    """Turn a decision into concrete legs. Prefers the agent's structured `strikes` array; falls back
    to parsing the free-text `legs` field.

    Deliberately conservative: if it can't find two unambiguous strikes it returns None rather than
    inventing them — a wrong strike would silently corrupt the track record."""
    import re
    st = (structure or "").upper()
    right = "P" if "PUT" in st else "C"
    nums = []
    if strikes:
        try:
            nums = [float(x) for x in strikes if x is not None]
        except Exception:
            nums = []
    if not nums:
        if not legs_text:
            return None
        # strikes written like 7740C / 315C / 180C, or bare numbers after buy/sell
        tagged = re.findall(r"(\d+(?:\.\d+)?)\s*([CP])\b", legs_text.upper())
        nums = [float(s) for s, _ in tagged]
        if len(nums) < 2:
            nums = [float(x) for x in re.findall(r"(?:buy|sell)\s+(?:1x\s+)?\$?(\d+(?:\.\d+)?)", legs_text.lower())]
    if len(nums) < 2:
        if len(nums) == 1 and st in ("LONG_CALL", "LONG_PUT"):
            return [{"right": right, "strike": nums[0], "qty": 1}]
        return None
    lo, hi = sorted(nums[:2])
    if spot and not (0.5 * spot <= lo <= 2.0 * spot):
        return None                              # strikes nowhere near spot => we parsed the wrong numbers
    if "CALL" in st and "CREDIT" not in st:
        return [{"right": "C", "strike": lo, "qty": 1}, {"right": "C", "strike": hi, "qty": -1}]
    if "PUT" in st and "CREDIT" not in st:
        return [{"right": "P", "strike": hi, "qty": 1}, {"right": "P", "strike": lo, "qty": -1}]
    if st == "CALL_CREDIT_SPREAD":
        return [{"right": "C", "strike": lo, "qty": -1}, {"right": "C", "strike": hi, "qty": 1}]
    if st == "PUT_CREDIT_SPREAD":
        return [{"right": "P", "strike": hi, "qty": -1}, {"right": "P", "strike": lo, "qty": 1}]
    if st in ("LONG_CALL", "LONG_PUT"):
        return [{"right": right, "strike": lo, "qty": 1}]
    return None


def price_trade(trade, spot=None):
    """Price an agent trade row at the CURRENT market. Returns None when it can't be priced honestly."""
    sym = trade.get("sym")
    exp = resolve_expiry(sym, trade.get("expiry"))
    if not exp:
        return None
    legs = parse_legs(trade.get("legs"), trade.get("structure"), spot, trade.get("strikes"))
    if not legs:
        return None
    r = price_structure(sym, exp, legs)
    r["expiry"] = exp
    return r


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "SPY"
    exp = resolve_expiry(sym, "0DTE")
    print(f"{sym} 0DTE expiry -> {exp}")
    import yfinance as yf
    spot = float(yf.Ticker(_yf(sym)).fast_info["lastPrice"])
    print("spot:", round(spot, 2))
    k = round(spot)
    q = quote(sym, exp, k, "C")
    print("ATM call quote:", q)
    r = price_structure(sym, exp, [{"right": "C", "strike": k, "qty": 1},
                                   {"right": "C", "strike": k + max(1, round(spot * 0.005)), "qty": -1}])
    print("call debit spread net:", r.get("net"), "| tradeable:", r.get("tradeable"),
          "| max loss:", r.get("max_loss"), "|", r.get("reject") or "")
