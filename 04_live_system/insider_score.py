"""insider_score.py — not every insider buy is the same buy.

`weekly_swing` scored insider activity as `tanh(count / 6)`: a COUNT of open-market buys,
every one weighted identically. That throws away almost everything the filing tells you --
who bought, how much relative to what they already held, whether it was a scheduled plan, and
crucially WHEN. A 20-day-old purchase counted exactly as much as this morning's on a book
that holds 5 to 16 days.

THE LITERATURE IS UNUSUALLY CLEAR HERE
======================================
Cohen, Malloy & Pomorski, "Decoding Inside Information" (2012, Journal of Finance) split
insiders into ROUTINE and OPPORTUNISTIC and found:

    opportunistic trades   ~82 bp/month abnormal, value-weighted
    routine trades         essentially zero

All of the predictive power is in the opportunistic subset. Routine buying is noise, and a
count-based score mixes the two together and dilutes the signal with it.

Lakonishok & Lee (2001) adds that the predictive content rises when MULTIPLE insiders buy --
so distinct buyers matter more than total transactions.

ONE COUNTERINTUITIVE FINDING WORTH RESPECTING
=============================================
The obvious move is to weight the CEO above a director. Cohen/Malloy/Pomorski found the
opposite tilt: the most informed opportunistic traders were "local, NONEXECUTIVE insiders from
geographically concentrated, poorly governed firms."

So role gets only a mild adjustment here, and officers are NOT placed above directors. Doing
what feels obvious would have been backwards relative to the one paper that isolated the
informative subset.

WHAT THIS CANNOT DO YET
=======================
Per-insider TRACK RECORD -- "this person's buys have been right before" -- needs a history of
each insider's past purchases scored against realised forward returns. That history does not
exist in this repo yet; UW serves current filings, not a per-person hit rate. `track_record()`
below is the hook and it returns a neutral 1.0 with a stated reason until the ledger has
accumulated enough. It is deliberately NOT approximated by something that sounds similar,
because a fabricated skill score would be indistinguishable from a real one at the call site.
"""
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# A buy is only news while it is still news. The book holds 5-16 days, so a purchase whose
# TRANSACTION date is a month old is describing a decision that has already been priced.
# Half-life in calendar days, applied to the transaction date, not the filing date: Form 4
# allows two business days, so filing date lags the actual decision.
RECENCY_HALFLIFE_DAYS = 12.0
MAX_AGE_DAYS = 45.0          # beyond this it contributes nothing at all

# Officers and directors both count; neither is placed above the other, per CMP above. The
# 10% owner is discounted because a large holder rebalancing is not the same as an insider
# forming a view.
ROLE_MULT = {"officer": 1.05, "director": 1.05, "ten_percent": 0.6, "other": 0.8}

# Conviction: the buy as a fraction of what the insider ALREADY held. Someone adding 40% to
# their own stake is making a statement; someone adding 0.5% is topping up. Capped so a tiny
# prior holding cannot produce an unbounded score.
STAKE_CAP = 0.50


def _parse(d):
    if not d:
        return None
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def recency_weight(transaction_date, now=None):
    """Exponential decay on the age of the DECISION. 1.0 today, ~0.5 at the half-life."""
    d = _parse(transaction_date)
    if d is None:
        return 0.0, "no transaction date"
    today = (now or datetime.now(ET)).date()
    age = (today - d).days
    if age < 0:
        # A transaction date in the future is a filing artifact, not a prediction. Treat it
        # as today rather than rewarding it with a >1 weight.
        age = 0
    if age > MAX_AGE_DAYS:
        return 0.0, f"{age}d old, past the {MAX_AGE_DAYS:.0f}d cutoff"
    return 0.5 ** (age / RECENCY_HALFLIFE_DAYS), f"{age}d old"


def role_of(row):
    if row.get("is_ten_percent_owner"):
        return "ten_percent"
    if row.get("is_officer"):
        return "officer"
    if row.get("is_director"):
        return "director"
    return "other"


def track_record(owner_name):
    """Per-insider skill multiplier. NEUTRAL until there is history to earn it.

    Returns (multiplier, why). The hook exists so the call site is already shaped for it, but
    it returns 1.0 today: scoring an insider's past buys against realised forward returns
    needs a per-person history this repo has not accumulated. Guessing from role, filing
    frequency or firm size would produce a number that LOOKS like a skill estimate and is not
    one, and at the call site the two are indistinguishable.
    """
    return 1.0, "no per-insider history yet — neutral"


def is_routine(row):
    """Routine buys carry no predictive power (CMP 2012), so they are excluded outright.

    `is_10b5_1` is the strong, explicit case: a pre-scheduled plan, which is routine by
    construction. CMP's fuller definition -- an insider who trades the same calendar month
    for three consecutive years -- needs per-insider history and is noted as a gap rather
    than approximated.
    """
    if row.get("is_10b5_1"):
        return True, "10b5-1 scheduled plan"
    code = (row.get("transaction_code") or "").upper()
    if code != "P":
        return True, f"transaction code {code or '?'}, not an open-market purchase (P)"
    return False, None


def score_rows(rows, now=None):
    """Turn raw Form 4 rows into one value in [0, 1], plus a full audit trail.

    The output is deliberately explainable: every included buy, its weight and why, and every
    excluded one with the reason. An insider score you cannot take apart is one you cannot
    argue with when it is wrong.
    """
    included, excluded = [], []
    buyers = set()
    total = 0.0

    for r in rows or []:
        routine, why = is_routine(r)
        if routine:
            excluded.append({"owner": r.get("owner_name"), "why": why})
            continue

        rec, rec_why = recency_weight(r.get("transaction_date"), now=now)
        if rec <= 0:
            excluded.append({"owner": r.get("owner_name"), "why": rec_why})
            continue

        role = role_of(r)
        role_mult = ROLE_MULT.get(role, 0.8)
        skill, skill_why = track_record(r.get("owner_name"))

        # Conviction relative to the insider's own prior stake.
        try:
            before = float(r.get("shares_owned_before") or 0)
            amt = abs(float(r.get("amount") or 0))
            price = float(r.get("price") or 0) or float(r.get("stock_price") or 0)
            shares = (amt / price) if price else 0.0
        except (TypeError, ValueError):
            before = shares = 0.0
        stake = min(shares / before, STAKE_CAP) / STAKE_CAP if before > 0 else 0.35
        # 0.35 when the prior stake is unknown: a mid value, so a missing field neither
        # rewards nor punishes the filing.

        w = rec * role_mult * skill * (0.5 + 0.5 * stake)
        total += w
        buyers.add((r.get("owner_name") or "?").upper())
        included.append({
            "owner": r.get("owner_name"), "role": role, "title": r.get("officer_title"),
            "transaction_date": r.get("transaction_date"),
            "filing_date": r.get("filing_date"),
            "usd": round(abs(float(r.get("amount") or 0)), 0),
            "stake_frac": round(stake * STAKE_CAP, 4) if before > 0 else None,
            "recency": round(rec, 3), "recency_why": rec_why,
            "role_mult": role_mult, "skill": skill, "skill_why": skill_why,
            "weight": round(w, 3),
        })

    # DISTINCT BUYERS, not transaction count. One insider filing six lots is one opinion;
    # six insiders buying is six, and Lakonishok & Lee found the predictive content rises
    # with the number of distinct buyers.
    cluster = math.tanh(len(buyers) / 3.0)
    raw = math.tanh(total / 3.0)
    score = 0.65 * raw + 0.35 * cluster

    return {
        "score": round(min(1.0, max(0.0, score)), 3),
        "n_included": len(included), "n_excluded": len(excluded),
        "n_distinct_buyers": len(buyers),
        "cluster_component": round(cluster, 3),
        "weighted_component": round(raw, 3),
        "included": sorted(included, key=lambda x: -x["weight"])[:8],
        "excluded": excluded[:8],
        "basis": ("Routine and 10b5-1 buys excluded (Cohen/Malloy/Pomorski 2012: routine "
                  "trades carry essentially zero abnormal return, opportunistic ones ~82bp/"
                  "month). Each remaining buy decayed on the age of the TRANSACTION with a "
                  f"{RECENCY_HALFLIFE_DAYS:.0f}-day half-life, scaled by its size against the "
                  "insider's own prior stake, and blended with the count of DISTINCT buyers "
                  "(Lakonishok & Lee 2001). Role is only a mild adjustment and officers are "
                  "NOT ranked above directors — CMP found the most informed opportunistic "
                  "traders were nonexecutive insiders."),
    }


def for_ticker(ticker, lookback_days=60, now=None):
    """Fetch and score one ticker's recent open-market insider buys. Never raises."""
    try:
        import uw_client
        if not uw_client.available():
            return None
        since = ((now or datetime.now(ET)).date() - timedelta(days=lookback_days)).isoformat()
        # THE PARAM IS `ticker_symbol`, NOT `ticker`. Passing `ticker` is silently ignored
        # and the endpoint returns the MARKET-WIDE filing feed instead of this name's -- so a
        # client-side filter on the ticker then removes everything and the score reads 0.0
        # for every name. That failure is indistinguishable from "no insider buys", which is
        # exactly the kind of silent zero this repo keeps getting bitten by.
        r = uw_client._get("/api/insider/transactions",
                           {"ticker_symbol": ticker, "limit": 100,
                            "transaction_codes[]": "P",
                            "min_transaction_date": since})
        rows = uw_client._rows(r)
    except Exception:                                         # noqa: BLE001
        return None
    if not rows:
        return {"score": 0.0, "n_included": 0, "n_excluded": 0, "n_distinct_buyers": 0,
                "included": [], "excluded": [], "basis": "no open-market insider buys in the "
                f"last {lookback_days} days"}
    # Belt and braces: if the endpoint ever ignores the filter again, this catches it rather
    # than scoring another name's filings against this ticker.
    wrong = [r for r in rows if (r.get("ticker") or "").upper() != ticker.upper()]
    rows = [r for r in rows if (r.get("ticker") or "").upper() == ticker.upper()]
    res = score_rows(rows, now=now)
    if wrong and not rows:
        res["warning"] = (f"the endpoint returned {len(wrong)} rows for other tickers and none "
                          f"for {ticker} — check the query parameter name")
    return res


if __name__ == "__main__":
    import sys
    for tk in (sys.argv[1:] or ["NVDA", "MSFT", "DELL"]):
        res = for_ticker(tk)
        if res is None:
            print(f"{tk}: Unusual Whales unavailable")
            continue
        print(f"\n{tk}: score {res['score']:.3f}  "
              f"({res['n_included']} buys from {res['n_distinct_buyers']} distinct insiders, "
              f"{res['n_excluded']} excluded)")
        for x in res["included"][:5]:
            print(f"   {x['owner'][:28]:28} {x['role']:11} {x['transaction_date']} "
                  f"{x['recency_why']:>10}  w={x['weight']:.3f}  ${x['usd']:,.0f}")
        for x in res["excluded"][:3]:
            print(f"   EXCLUDED {str(x['owner'])[:26]:26} {x['why']}")
