"""ONE weighting authority for every tab.

Each panel had been growing its own scoring rules, which meant a signal measured
worthless in one place could still be quietly driving another. This centralises
it: every tab asks the same object what an input is worth, and the answer is set
by measurement.

THE EVIDENCE, all from studies in this repo:

  MEASURED-REAL
    short interest        IC -0.022/-0.038/-0.068/-0.087/-0.107 at 5/10/21/42/63d,
                          n=13,219. Monotone in horizon. SIGN IS NEGATIVE --
                          heavily shorted names underperform. My original prior
                          had this backwards.
    VIX backwardation     +1.3 to +1.8pp excess 21d return, t = +3.9/+2.8/+2.1
    + golden cross        across all three splits. The only signal that beat its
                          base rate in every era.

  MEASURED-WEAK
    insider open buys     IC +0.027 (5d) to +0.042 (63d), but n=1,128 and the
                          sign flips by era.
    rate beta             Sensitivity is stable and real; PREDICTION failed
                          (216 cells, zero cleared the bar). Risk flag only,
                          capped at +/-5 conviction.

  MEASURED-NULL -> weight 0, no exceptions
    IV level / IV trend   lift 1.01x / 0.98-1.02x over 810,300 ticker-days
    OI building           lift 0.76x -- BELOW the base rate
    spreads widening      lift 0.90x
    dealer gamma as       1,001 gated cells, zero positive in all three periods
      direction
    sector rotation       1,512 configs, none beat buy-and-hold
    dip-buying screens    base-rate artifact; below the unconditional rate
    cheap-IV screens      made far-OTM buying WORSE (-95.4% worst cell)

  UNMEASURED (prior, converging forward)
    classified flow       genuinely orthogonal, but UW serves same-day only, so
    dark pool             it cannot be backtested -- only earned forward via
                          uw_calibrate.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
CAL = os.path.join(ROOT, "data", "uw_weights.json")

# (prior weight, tier, sign, evidence)
# ─── PRIORS SET FROM THE LITERATURE, 2026-09-06 ──────────────────────────────────────
# The Unusual Whales inputs cannot be backtested here -- the API serves same-day only, so
# there is no history. Leaving them on round numbers I invented was the weakest part of this
# file. They are now priors taken from published work, chosen on TWO axes: how strong the
# documented effect is, and HOW WELL ITS HORIZON MATCHES A 5-16 DAY HOLD. The second axis is
# what most naive weightings ignore, and it moves these numbers more than the first.
#
#   flow_lean 0.40  STRONGEST horizon match. Johnson & So (2012, JFE) find low put-call
#                   ratios beat high by >40bp the next DAY and >1% over the next WEEK --
#                   which is exactly this book's holding period. Muravyev (2016, JF) and the
#                   option-induced order-imbalance literature find signed option flow
#                   predicts cross-sectional returns, strongest in informationally opaque
#                   names. Raised from 0.35: best-documented effect on the right horizon.
#                   CAVEAT: the academic measure is Lee-Ready-signed volume off full
#                   trade-and-quote data. A vendor's "flow lean" is a proxy for it, not the
#                   thing itself, so the tier stays UNMEASURED.
#
#   short_float 0.22  Robust and international -- Boehmer/Jones/Zhang (2008),
#                   Diether/Lee/Werner (2009), Boehmer/Huszar/Jordan (2010), Boehmer et al
#                   (2022): high short interest predicts LOW returns in the cross section in
#                   most countries. Sign stays NEGATIVE. But LOWERED from 0.30 on horizon:
#                   this repo's own ICs are monotone INCREASING in horizon -- -0.022 at 5d,
#                   -0.038 at 10d, -0.068 at 21d, -0.107 at 63d. A 5-16 day hold sits at the
#                   WEAK end of that curve, not the strong end. Quoting the 63-day number to
#                   justify a weekly trade is the horizon mismatch this comment exists to
#                   stop.
#
#   insider 0.06    Lakonishok & Lee (2001) is the canonical result and it is a TWELVE-MONTH,
#                   SMALL-CAP effect: ~7.4% abnormal over 12 months in small caps, and the
#                   magnitude "shrank considerably" for large caps. This book holds 5-16 days
#                   in a universe that is mostly mega-cap. Both axes are wrong for us, so the
#                   weight drops from 0.10. It is not zero because the effect is real and
#                   because the literature finds it strengthens when MULTIPLE insiders buy,
#                   which is what the count actually measures.
#
#   dp_buy_share 0.10  The WEAKEST of the four, and the literature is explicit about why:
#                   exchange short sales are "significantly more informative than dark pool
#                   short sales" (Reed et al; Boulton et al). Heavily-shorted-in-dark-pool
#                   names underperform by only 0.53% over 20 trading days. Lowered from 0.15
#                   and hard-capped below, because a calibration blend had pushed the served
#                   weight to 0.375 -- making the weakest of the four the STRONGEST input in
#                   the whole vote.
#
#   trend 0.15      Lowered from 0.35 by direct measurement, not by literature.
#                   05_studies/trend_component_ic.py measured the shipped composite on 101
#                   names, 2020-2026: cross-sectional IC +0.0149 at 5d falling to +0.0081 at
#                   21d, max |t| 1.0, and it FLIPS SIGN across three consecutive splits
#                   (+0.0574 -> -0.0229 -> -0.0165). A voter that only works in the first
#                   third of the sample is a period, not a signal. It is not zeroed because
#                   the directional hit-rate claim (~55-60%) is a different question this
#                   test does not settle, and because it is the only voter available when
#                   the vendor is down.
REGISTRY = {
    "short_float_pct":   (0.22, "measured",      -1,
                          "Boehmer et al 2008/2010/2022, Diether et al 2009. Repo IC -0.022@5d "
                          "-> -0.107@63d, n=13,219, monotone; a weekly hold sits at the WEAK end"),
    "flow_lean":         (0.40, "unmeasured",    +1,
                          "Johnson & So 2012 JFE: low put-call beats high by >40bp/day, >1%/week. "
                          "Muravyev 2016 JF. Best horizon match in the vote; vendor proxy, not "
                          "the Lee-Ready measure, so still unmeasured"),
    "dp_buy_share":      (0.10, "unmeasured",    +1,
                          "Reed et al / Boulton et al: dark-pool shorts are significantly LESS "
                          "informative than exchange shorts; 0.53% over 20d. Weakest of the four"),
    "insider_open_buys": (0.06, "measured-weak", +1,
                          "Lakonishok & Lee 2001: ~7.4% over TWELVE months in SMALL caps, shrinks "
                          "considerably in large caps. Wrong horizon and wrong cap tier for a "
                          "5-16 day mega-cap book; kept nonzero as it strengthens on multiple buys"),
    # The Crown Macro Letter read, as a voter. Registered here rather than applied privately
    # inside weekly_swing, because the whole reason this module exists is that a signal
    # applied in one place with its own private weight is a signal nobody can audit.
    #
    # Tier is UNMEASURED and stays that way until it is earned forward. It is a human macro
    # argument that has never been backtested in this repo, so `combine()` counts it toward
    # the unmeasured share and every weekly card prints that share. The prior matches
    # `flow_lean` because the claim for both is the same one: genuinely orthogonal to price,
    # and therefore worth something even untested. It is NOT evidence of being right.
    "desk_macro":        (0.35, "unmeasured",    +1, "human macro read; orthogonal to price, "
                                                     "never backtested here"),
    "vix_backwardation": (0.30, "measured",      +1, "t=+3.9/+2.8/+2.1 all three splits"),
    "trend":             (0.15, "measured-weak", +1,
                          "cross-sectional IC +0.015@5d -> +0.008@21d, max |t| 1.0, and FLIPS "
                          "SIGN across three splits (+0.057/-0.023/-0.017) — "
                          "05_studies/trend_component_ic.py"),
    "rate_beta":         (0.05, "risk-flag",     +1, "sensitivity real, prediction null"),
    # hard zeros
    "iv_rel":            (0.00, "measured-null", 0, "lift 1.01x / 810,300 days"),
    "iv_trend":          (0.00, "measured-null", 0, "lift 0.98-1.02x"),
    "oi_change_net":     (0.00, "measured-null", 0, "lift 0.76x — below base"),
    "spread_rel":        (0.00, "measured-null", 0, "lift 0.90x"),
    "gamma_direction":   (0.00, "measured-null", 0, "1,001 cells, zero survived"),
    "sector_rotation":   (0.00, "measured-null", 0, "1,512 configs, none beat B&H"),
    "dip_screen":        (0.00, "measured-null", 0, "base-rate artifact"),
    "cheap_iv":          (0.00, "measured-null", 0, "made far-OTM worse"),
}

N0 = 100          # shrinkage constant, shared with uw_calibrate


def _calibrated():
    try:
        with open(CAL) as f:
            return json.load(f)
    except Exception:
        return {}


# A cross-sectional information coefficient above this is not a discovery, it is a broken
# calibration. Real equity ICs live at 0.02-0.05; 0.10 would be exceptional and 0.62 would
# be the best signal in the history of the industry. On 2026-09-02 `data/uw_weights.json`
# carried short_float_pct at IC -0.621, flow_lean at -0.267 and oi_change_net at +0.265 --
# the last of which the registry records as a MEASURED NULL (lift 0.76x, below base rate).
# Three impossible numbers in one file is a bug upstream, and a weighting authority that
# believes them is worse than one with no calibration at all.
IC_IMPLAUSIBLE = 0.15

# What counts as a strong, believable IC. Reaching it earns full measured weight.
IC_FULL = 0.05

# How far a calibration may move a weight away from its prior. A same-day forward sample of
# a few thousand rows may ADJUST a prior that came from a 13,219-name multi-era study; it
# may not overwrite it. Without this band the blend saturated and every calibrated input
# came out at 0.99 regardless of its evidence, which is precisely the flattening this whole
# module exists to prevent: insider buys (n=1,128, sign flips by era) were being served at
# the same weight as short interest (n=13,219, monotone in horizon).
CAL_BAND_LO, CAL_BAND_HI = 0.25, 2.5

# A HARD CEILING PER INPUT, above the band. The band is relative to the prior, so a small
# prior with a flattering IC could still be blended into the largest weight in the vote --
# `dp_buy_share` reached 0.375 that way, becoming the biggest input despite the literature
# calling it the weakest of the four. This caps what any single input may ever be served at,
# whatever a calibration file says.
CAL_CEILING = {"dp_buy_share": 0.15, "insider_open_buys": 0.10, "short_float_pct": 0.30,
               "flow_lean": 0.45, "trend": 0.20}


def weight(name):
    """Current weight for an input: prior blended toward measurement by sample.

    Returns (weight, tier, sign). The tier says how the number was arrived at, so a caller
    can show whether a weight rests on measurement or on a prior -- and, now, whether a
    calibration was rejected for being implausible.
    """
    if name not in REGISTRY:
        return 0.0, "unknown", 0
    prior, tier, sign, _ = REGISTRY[name]
    if tier == "measured-null":
        return 0.0, tier, 0            # a null is never revived by a short run
    cal = _calibrated().get("weights", {}).get(name)
    if cal and cal.get("n", 0) > 0 and cal.get("ic") is not None:
        ic = float(cal["ic"])
        if abs(ic) > IC_IMPLAUSIBLE:
            # Do not quietly use it and do not quietly ignore it. The prior stands and the
            # tier says why, so a panel can surface that the calibration is broken rather
            # than showing a confident weight built on an impossible number.
            return prior, f"prior · calibration rejected (|IC| {abs(ic):.2f})", sign
        n = cal["n"]
        k = (n / (n + N0)) ** 0.5
        measured = max(0.0, min(1.0, abs(ic) / IC_FULL))
        blended = (1 - k) * prior + k * measured
        # Banded around the prior: a calibration adjusts, it does not replace.
        lo, hi = prior * CAL_BAND_LO, min(1.0, prior * CAL_BAND_HI)
        hi = min(hi, CAL_CEILING.get(name, 1.0))
        return max(lo, min(hi, blended)), "blended", sign
    return prior, tier, sign


def combine(inputs):
    """Score a set of named inputs, each already normalised to [-1, +1].

    Returns the score plus the share of weight that is still unmeasured, so a
    panel can show how much of a call rests on evidence versus on a prior.
    """
    # ABSTENTIONS DO NOT DILUTE. An input whose value is exactly 0.0 has declined to vote --
    # `vix_backwardation` votes 0.0 whenever the term structure is in contango (most days,
    # weight 0.30), and `insider_open_buys` votes 0.0 when there are no recent opportunistic
    # buys (the normal case). Counting them in the DENOMINATOR while they add nothing to the
    # numerator drags every score toward zero: measured 2026-09-06, dead weight was 24% of
    # the denominator, so a name genuinely at +0.41 was being served as +0.31.
    #
    # That is the same mistake already fixed in `weekly_swing`'s `agreement` calculation, and
    # it was left here. The score is the weighted average AMONG VOTERS THAT EXPRESSED A VIEW.
    #
    # It matters beyond one number: an absolute conviction floor calibrated against one
    # weight distribution silently becomes a different percentile when the weights change.
    # Re-weighting on 2026-09-06 moved a 0.30 floor from the ~93rd percentile to the 98th,
    # and the book went from six cards to one -- not because the market changed.
    num = den = unmeasured = 0.0
    used = {}
    for name, val in inputs.items():
        if val is None:
            continue
        w, tier, sign = weight(name)
        if w <= 0:
            continue
        v = float(val)
        num += w * sign * v
        used[name] = round(w * sign * v, 3)
        if v == 0.0:
            continue                      # abstained: no numerator, no denominator
        den += w
        if tier == "unmeasured":
            unmeasured += w
    if den == 0:
        return {"score": 0.0, "confidence": 0.0, "contrib": {}, "n_inputs": 0}
    return {"score": round(num / den, 3),
            "confidence": round(1 - unmeasured / den, 2),
            "unmeasured_share": round(unmeasured / den, 2),
            "contrib": used, "n_inputs": len(used)}


def table():
    """Display table for the dashboard footer — what counts and why."""
    rows = []
    for k, (_prior, _tier, sign, ev) in REGISTRY.items():
        w, t, s = weight(k)
        rows.append({"input": k, "weight": round(w, 3), "tier": t,
                     "sign": "+" if sign > 0 else ("−" if sign < 0 else "0"),
                     "evidence": ev})
    return sorted(rows, key=lambda r: -r["weight"])


if __name__ == "__main__":
    for r in table():
        print(f"  {r['input']:20s} {r['weight']:5.2f} {r['sign']}  {r['tier']:15s} {r['evidence']}")
    print()
    demo = {"flow_lean": 0.5, "short_float_pct": 0.8, "trend": 0.4,
            "iv_rel": 0.9, "gamma_direction": 1.0}
    print("demo combine (note the nulls contribute nothing):")
    print("  ", combine(demo))
