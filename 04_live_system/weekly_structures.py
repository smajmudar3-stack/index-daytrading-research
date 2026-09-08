"""weekly_structures.py — the whole structure menu, and which situation each one fits.

`weekly_swing` decides the VIEW (which way, how far, how expensive the vol is). This module
turns a view into a TRADE. Separating them is the point: the view is an argument about the
world, the structure is an engineering question about how to express it for the least money
at defined risk, and mixing the two is how a directional opinion ends up expressed as a
short strangle.

WHY A GENERIC PAYOFF ENGINE RATHER THAN A FORMULA PER STRUCTURE
===============================================================
Max risk on a vertical is (width - credit). On a condor it is (widest wing - credit). On a
butterfly, (wing - credit). On a backspread it is the loss at the short strike, which is
not a closed form you want to hand-derive. Nine structures times a bespoke risk formula is
nine chances to be silently wrong about how much money is on the table, and the failure is
invisible until it costs you.

So every structure here is built as a list of priced legs and then EVALUATED: build the
expiry payoff, walk it across a grid of every strike plus the tails, and read max risk and
max reward straight off the curve. One implementation, correct for structures nobody has
written yet.

WHAT THIS REPO ACTUALLY MEASURED, AND WHY IT IS ATTACHED TO EVERY CARD
=====================================================================
Four of these structures have a measured expectancy in `02_findings/`, all of them on real
SPXW bid/ask, and all four are NEGATIVE:

    iron condor      -0.25%/trade   t = -0.47   74.8% win rate
    iron butterfly   -0.35%/trade   t = -0.56   57.0% win rate
    long straddle    -5.69%/trade   t = -4.75   significantly negative
    long strangle   -11.54%/trade   median -100%, most expire worthless

Those are 0DTE index measurements and do not transfer directly to a weekly single-name
trade. They are attached to the card anyway, because the honest thing to do with a number
that says "this shape lost money when we measured it" is to put it next to the shape. A
74.8% win rate with a negative expectancy is the single most seductive result in the repo,
and the condor is exactly the structure a low-move read wants to reach for.

THE ONE PIECE OF CONDITIONING THAT SURVIVED
===========================================
Dealer gamma forecasts RANGE, never direction. Measured on 1,919 sessions: realised range
came in at 0.843x implied on high-gamma days and 1.139x on low-gamma days, t = -13.2. That
is why a range-selling structure is refused outright when the index is below its gamma
flip. It is not a preference, it is the only conditioning here with a t-statistic.

DEFINED RISK ONLY. No naked short options are ever constructed, on any path. Every short
leg is paired with a long further out. This is a paper book and it stays one that could not
blow up if it were not.
"""
import math

# ---------------------------------------------------------------- the evidence ---
# Measured expectancy per structure, quoted so no card can read as a green light.
# Keys are the machine names used by `menu()`.
EVIDENCE = {
    "iron_condor": "MEASURED −0.25%/trade on 4,310 real-quote 0DTE trades, t = −0.47. "
                   "Win rate 74.8% — a high win rate with a negative expectancy, which is "
                   "the most seductive shape of losing trade there is.",
    "iron_butterfly": "MEASURED −0.35%/trade on 4,310 trades, t = −0.56, 57.0% win rate.",
    "long_straddle": "MEASURED −5.69%/trade on 4,305 trades, t = −4.75. Significantly "
                     "negative, not merely unprofitable.",
    "long_strangle": "MEASURED −11.54%/trade, median −100%. Most expire worthless.",
    "call_debit": "No direct measurement. The nearest is the vertical hurdle study: paying "
                  "theta measured −11.12%/trade across 230,884 real-fill SPXW trades, "
                  "against −1.27% for collecting it. Structure orientation is worth about "
                  "10 points a trade; it does not manufacture a signal.",
    "put_debit": "See call debit spread: paying theta measured −11.12%/trade on 230,884 "
                 "real-fill trades.",
    "put_credit": "Collecting theta measured −1.27%/trade on 230,884 real-fill SPXW trades "
                  "— the better side of the theta trade, and still negative unconditionally.",
    "call_credit": "Collecting theta measured −1.27%/trade on 230,884 real-fill trades.",
    "calendar": "Not measured in this repo. The term-structure logic is the desk's own, "
                "from its NVDA note: sell the expensive event week, own the cheaper month.",
    "diagonal": "Not measured in this repo. A calendar with a directional tilt; carries the "
                "calendar's unmeasured status and adds strike risk on top.",
    "call_backspread": "Not measured in this repo. Long more contracts than short, so it "
                       "wants a LARGE move and bleeds if nothing happens.",
    "put_backspread": "Not measured in this repo. Long more contracts than short, so it "
                      "wants a LARGE move and bleeds if nothing happens.",
    "reverse_condor": "Not measured directly. It is the long-vol mirror of the condor, "
                      "whose measured −0.25% is a statement about the SHORT side; do not "
                      "read that as +0.25% here, because both sides pay the spread.",
}

# Human labels.
LABEL = {
    "iron_condor": "Iron condor — range, defined risk",
    "iron_butterfly": "Iron butterfly — tight range, pinned",
    "long_straddle": "Long straddle — big move, no direction",
    "long_strangle": "Long strangle — bigger move, cheaper",
    "reverse_condor": "Reverse iron condor — big move, capped cost",
    "call_debit": "Call debit spread",
    "put_debit": "Put debit spread",
    "put_credit": "Put credit spread (bullish)",
    "call_credit": "Call credit spread (bearish)",
    "calendar": "Calendar — sell the event week, own the month",
    "diagonal": "Diagonal — directional, financed by the front week",
    "call_backspread": "Call backspread — pays for a large move up",
    "put_backspread": "Put backspread — pays for a large move down",
}

# Structures that SELL range. Refused outright when the index is short gamma, because that
# is the one dealer-gamma result with a t-statistic behind it.
RANGE_SELLING = {"iron_condor", "iron_butterfly", "put_credit", "call_credit"}

# Structures whose risk climbs sharply into expiry and that should be closed early rather
# than held to settlement. The number is days before expiry.
CLOSE_EARLY_DTE = {"iron_condor": 2, "iron_butterfly": 2,
                   "put_credit": 2, "call_credit": 2}


# ------------------------------------------------------------- the payoff engine ---

def payoff_at(legs, spot):
    """P&L per share at expiry, for a list of priced legs. The whole risk engine.

    A leg is {right: 'C'|'P', strike, price, buying, qty}. `price` is what it actually
    filled at: the ask when bought, the bid when sold.
    """
    total = 0.0
    for lg in legs:
        if lg["right"] == "C":
            intrinsic = max(0.0, spot - lg["strike"])
        else:
            intrinsic = max(0.0, lg["strike"] - spot)
        sign = 1.0 if lg["buying"] else -1.0
        total += sign * lg["qty"] * (intrinsic - lg["price"])
    return total


def evaluate(legs):
    """(max_risk, max_reward, net) per share, read off the expiry curve.

    The grid is every strike, the midpoint of every adjacent pair (a butterfly's peak sits
    exactly on a strike, but a backspread's worst point can sit between two), and both
    tails well beyond the wings. Anything defined-risk has its extremes on that grid.
    """
    ks = sorted({lg["strike"] for lg in legs})
    lo, hi = ks[0], ks[-1]
    span = max(hi - lo, hi * 0.25) or 1.0
    grid = [max(0.01, lo - span), lo - span * 0.5]
    for a, b in zip(ks, ks[1:], strict=False):
        grid += [a, (a + b) / 2.0]
    grid += [hi, hi + span * 0.5, hi + span]
    vals = [payoff_at(legs, s) for s in grid]

    net = 0.0
    for lg in legs:
        net += (1.0 if lg["buying"] else -1.0) * lg["qty"] * lg["price"]

    return -min(vals), max(vals), net


def is_defined_risk(legs, tol=1e-6):
    """True when no naked short survives: within each right, longs at least match shorts.

    THE STRIKE ORDER DOES NOT MATTER, only the quantities, and getting that wrong is what
    the first version did. It demanded that a short call be covered by a long call at a
    HIGHER strike, which rejected every ordinary call debit spread -- long 165C / short
    172.5C -- as "naked". It is not naked: above 172.5 the short's losses are matched
    one-for-one by the long's gains and the loss is capped at the debit. Both orderings are
    bounded; a bull call spread caps at the debit and a bear call spread at (width - credit).

    What actually creates unbounded risk is being NET short a right: more short calls than
    long calls leaves the upside open, more short puts than long puts leaves the downside
    open. That, and only that, is the test.
    """
    for right in ("C", "P"):
        short_qty = sum(lg["qty"] for lg in legs
                        if lg["right"] == right and not lg["buying"])
        long_qty = sum(lg["qty"] for lg in legs
                       if lg["right"] == right and lg["buying"])
        if long_qty + tol < short_qty:
            return False
    return True


# ---------------------------------------------------------------- leg assembly ---

def assemble(name, spec, quote, max_cost_pct, direction=None, extra=None):
    """Price a leg spec and turn it into a card-ready structure, or refuse it.

    `spec` is [(right, strike, buying, qty)]. `quote(right, strike, buying)` returns
    (leg_dict, error) and owns every liquidity rule. Nothing here reprices anything.
    """
    legs, worst_spread, half = [], 0.0, 0.0
    for right, strike, buying, qty in spec:
        if strike is None:
            return None, f"{name}: a strike could not be placed on the listed ladder"
        lg, err = quote(right, strike, buying)
        if err:
            return None, f"{name}: {err}"
        lg = {**lg, "right": right, "qty": qty, "buying": buying}
        legs.append(lg)
        worst_spread = max(worst_spread, lg["spread_pct"])
        half += lg["half_spread"] * qty

    # Two legs that snapped to the same contract are not a spread. This is the guard that
    # would have stopped "Buy 14P / Sell 14P" from ever being printed.
    seen = set()
    for lg in legs:
        key = (lg["right"], lg["strike"])
        if key in seen:
            return None, (f"{name}: two legs snapped to the same contract "
                          f"({lg['strike']:g}{lg['right']}) — no structure exists here")
        seen.add(key)

    if not is_defined_risk(legs):
        return None, f"{name}: would leave a naked short leg, which is never constructed"

    max_risk, max_reward, net = evaluate(legs)
    if max_risk <= 0:
        return None, f"{name}: priced with no money at risk, which means the quotes are stale"
    if not math.isfinite(max_reward) or max_reward <= 0:
        return None, f"{name}: priced with no upside on real fills"

    cost = 2 * half                                   # in AND out, every leg
    cost_pct = cost / max_risk * 100
    if cost_pct > max_cost_pct:
        return None, (f"{name}: round-trip spread costs {cost_pct:.0f}% of the "
                      f"${max_risk*100:.0f} at risk (limit {max_cost_pct:.0f}%) — "
                      f"the execution eats the trade")

    # WIDTH, WHERE ONE EXISTS. A two-leg single-right spread with matched quantities has a
    # single width, and `_exits` manages those at 60% of it. Everything else -- condors and
    # flies with two wings, straddles with none, backspreads with unmatched quantities --
    # gets None and is managed on its own premium instead. The first version omitted this
    # field entirely, so every vertical fell through to the premium rule.
    width = None
    if len(legs) == 2 and legs[0]["right"] == legs[1]["right"] \
            and legs[0]["qty"] == legs[1]["qty"]:
        width = round(abs(legs[0]["strike"] - legs[1]["strike"]), 2)

    return {
        "name": name,
        "label": LABEL.get(name, name),
        "width": width,
        "evidence": EVIDENCE.get(name),
        "legs": legs,
        "legs_text": _legs_text(legs),
        "net": round(net, 2),
        "is_debit": net > 0,
        "max_risk": round(max_risk * 100, 0),
        "max_reward": round(max_reward * 100, 0),
        "rr": round(max_reward / max_risk, 2) if max_risk > 0 else None,
        "cost_pct": round(cost_pct, 1),
        "worst_spread_pct": round(worst_spread, 1),
        "breakevens": breakevens(legs),
        "close_early_dte": CLOSE_EARLY_DTE.get(name),
        "sells_range": name in RANGE_SELLING,
        **(extra or {}),
    }, None


def _legs_text(legs):
    """The order ticket, longs first so it reads the way you would enter it."""
    parts = []
    for lg in sorted(legs, key=lambda x: (not x["buying"], x["right"], x["strike"])):
        q = f"{lg['qty']}x " if lg["qty"] != 1 else ""
        parts.append(f"{'Buy' if lg['buying'] else 'Sell'} {q}{lg['strike']:g}{lg['right']}")
    return " / ".join(parts)


def breakevens(legs, steps=2000):
    """Where the expiry curve crosses zero. Scanned, so it works for any shape."""
    ks = sorted({lg["strike"] for lg in legs})
    lo, hi = ks[0], ks[-1]
    span = max(hi - lo, hi * 0.3) or 1.0
    a, b = max(0.01, lo - span), hi + span
    out, prev_s, prev_v = [], a, payoff_at(legs, a)
    for i in range(1, steps + 1):
        s = a + (b - a) * i / steps
        v = payoff_at(legs, s)
        if prev_v == 0 or (prev_v < 0) != (v < 0):
            out.append(round(prev_s + (s - prev_s) * abs(prev_v) / (abs(prev_v) + abs(v) or 1), 2))
        prev_s, prev_v = s, v
    # Collapse near-duplicates from the scan resolution.
    dedup = []
    for x in out:
        if not dedup or abs(x - dedup[-1]) > (hi - lo) * 0.01 + 0.01:
            dedup.append(x)
    return dedup[:4]


# ------------------------------------------------------------- the menu itself ---

def menu(direction, move, iv_band, term_rich, covers_own_catalyst):
    """Which structures to try, in order, for this situation.

    `direction` bullish | bearish | neutral
    `move`      compress | expand | normal   — the magnitude view, separate from direction
    `iv_band`   rich | cheap | fair          — front-week IV against realised
    `term_rich` bool                         — front week much richer than the back month
    `covers_own_catalyst` bool               — the expiry contains this name's own event

    The ordering is the argument. Where the evidence says a shape loses, it sits lower even
    when it fits the read, and it never appears at all when it is on the wrong side of the
    one measured conditioning.
    """
    # An event with a steep term structure is a term-structure trade first, whatever the
    # direction view is. This is the desk's own NVDA reasoning: the premium is concentrated
    # in the week that contains the print, so sell that and own the cheaper month.
    if term_rich and covers_own_catalyst:
        head = ["calendar"] if direction == "neutral" else ["diagonal", "calendar"]
    else:
        head = []

    if direction == "neutral":
        if move == "compress":
            body = ["iron_condor", "iron_butterfly", "calendar"]
        elif move == "expand":
            # Long premium with no directional view. Every one of these is measured
            # negative, so the capped-cost version leads and the naked-long versions follow.
            body = ["reverse_condor", "long_strangle", "long_straddle"]
        else:
            body = ["calendar", "iron_condor"]
    elif direction == "bullish":
        if move == "expand":
            # Expecting a big move and paying a rich premium for it are different trades. A
            # backspread is long MORE contracts than it is short and is financed by that short
            # leg, so it is the cheaper way to be long a move when vol is already dear. Plain
            # debit only when the vol being bought is not rich.
            body = (["call_backspread", "diagonal", "call_debit"] if iv_band == "rich"
                    else ["call_debit", "call_backspread", "diagonal"])
        elif move == "compress":
            body = ["put_credit", "call_debit"]
        else:
            # DEBIT ONLY WHEN VOL IS ACTUALLY CHEAP. The previous rule led with a debit
            # unless IV was "rich" (>= 1.15x realised), a bar most names never clear, so
            # every fair-IV name became a call debit spread and the book was almost all
            # long calls. That is the wrong side of the largest structural effect this repo
            # measured: paying theta ran -11.12%/trade across 230,884 real-fill SPXW trades
            # against -1.27% for collecting it. Buying premium has to be justified by cheap
            # vol; it is not the default.
            body = (["call_debit", "put_credit"] if iv_band == "cheap"
                    else ["put_credit", "call_debit"])
    else:                                                  # bearish
        if move == "expand":
            body = (["put_backspread", "diagonal", "put_debit"] if iv_band == "rich"
                    else ["put_debit", "put_backspread", "diagonal"])
        elif move == "compress":
            body = ["call_credit", "put_debit"]
        else:
            body = (["put_debit", "call_credit"] if iv_band == "cheap"
                    else ["call_credit", "put_debit"])

    seen, out = set(), []
    for n in head + body:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out
