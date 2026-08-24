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
REGISTRY = {
    "short_float_pct":   (0.30, "measured",      -1, "IC -0.068 @21d, n=13,219, monotone"),
    "flow_lean":         (0.35, "unmeasured",    +1, "orthogonal; same-day only"),
    "dp_buy_share":      (0.15, "unmeasured",    +1, "orthogonal; same-day only"),
    "insider_open_buys": (0.10, "measured-weak", +1, "IC +0.027-0.042, n=1,128, era-unstable"),
    "vix_backwardation": (0.30, "measured",      +1, "t=+3.9/+2.8/+2.1 all three splits"),
    "trend":             (0.35, "measured-weak", +1, "momentum ~55-60% hit rate"),
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


def weight(name):
    """Current weight for an input: prior blended toward measurement by sample."""
    if name not in REGISTRY:
        return 0.0, "unknown", 0
    prior, tier, sign, _ = REGISTRY[name]
    if tier == "measured-null":
        return 0.0, tier, 0            # a null is never revived by a short run
    cal = _calibrated().get("weights", {}).get(name)
    if cal and cal.get("n", 0) > 0 and cal.get("ic") is not None:
        n = cal["n"]
        k = (n / (n + N0)) ** 0.5
        measured = max(0.0, min(1.0, abs(cal["ic"]) / 0.05))
        return (1 - k) * prior + k * measured, "blended", sign
    return prior, tier, sign


def combine(inputs):
    """Score a set of named inputs, each already normalised to [-1, +1].

    Returns the score plus the share of weight that is still unmeasured, so a
    panel can show how much of a call rests on evidence versus on a prior.
    """
    num = den = unmeasured = 0.0
    used = {}
    for name, val in inputs.items():
        if val is None:
            continue
        w, tier, sign = weight(name)
        if w <= 0:
            continue
        num += w * sign * float(val)
        den += w
        used[name] = round(w * sign * float(val), 3)
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
