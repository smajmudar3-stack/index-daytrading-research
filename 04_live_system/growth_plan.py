"""growth_plan.py — the account growth curve the agent trades toward, and adaptive aggression.

The target ladder (starts $4k on 2026-08-06). The agent reads where the account IS vs where the curve
says it SHOULD be, and adjusts AGGRESSION — more selective/protective when ahead, leaning into the best
setups when behind — WITHIN fixed hard risk caps (max risk/trade, daily-loss stop) that never move.
Those caps are what let it survive a bad streak long enough to compound. Account value is settable
(data/account.json) or defaults to the start.
"""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
ACCT = os.path.join(HERE, "data", "account.json")

# (date, target $) — weekly milestones toward $100k
MILESTONES = [
    ("2026-08-06", 5000), ("2026-08-20", 10000), ("2026-08-27", 15000), ("2026-09-03", 22000),
    ("2026-09-10", 28000), ("2026-09-17", 34000), ("2026-09-24", 45000), ("2026-10-01", 48000),
    ("2026-10-08", 51000), ("2026-10-15", 60000), ("2026-10-22", 67000), ("2026-10-29", 75000),
    ("2026-11-05", 82000), ("2026-11-12", 90000), ("2026-11-19", 100000),
]
START = 5000

# FIXED hard risk caps — the agent may NOT exceed these no matter how far behind the curve.
RISK_CAP = {"max_risk_per_trade_pct": 12, "max_open": 3, "daily_loss_stop_pct": 25}

# ── THE HONEST CURVE ──────────────────────────────────────────────────────────────
# The MILESTONES ladder above is the STATED AMBITION. Out-of-sample testing (RULES.md §5) says it is
# not reachable: $5k -> $100k in 15 weeks is +21.9%/week, which on the one validated edge would require
# risking 374% of the account per trade. Full Kelly on that edge is already 172% — Kelly itself says the
# required bet exceeds the account. It is arithmetic, not pessimism.
#
# This matters mechanically, not just rhetorically: aggression is derived from distance-to-curve, so
# measuring against an impossible curve would leave the agent permanently "behind" and permanently
# leaning in. That is exactly how accounts die. So AGGRESSION is measured against the EVIDENCE curve
# below, while the ambition stays visible for reference.
#
# Evidence curve: the validated 0DTE sleeve delivers ~1.56 trades/week at +3.75% per trade on the
# amount risked. At 5% risk that is ~+0.29%/week; the hard 12% cap gives ~+0.70%/week.
EVIDENCE_WEEKLY_PCT = 0.70          # at the 12% hard cap — the optimistic end of the honest range
EVIDENCE_START_DATE = "2026-08-06"


def evidence_target(today=None):
    """What the validated edge actually projects for a given date, at the hard risk cap."""
    today = today or datetime.now(ET).date()
    d0 = datetime.strptime(EVIDENCE_START_DATE, "%Y-%m-%d").date()
    weeks = max((today - d0).days, 0) / 7.0
    return round(START * ((1 + EVIDENCE_WEEKLY_PCT / 100.0) ** weeks))


def _milestone_dates():
    return [(datetime.strptime(d, "%Y-%m-%d").date(), v) for d, v in MILESTONES]


def target_for(today=None):
    """Interpolate the curve's target for a given date."""
    today = today or datetime.now(ET).date()
    ms = _milestone_dates()
    if today <= ms[0][0]:
        return ms[0][1]
    if today >= ms[-1][0]:
        return ms[-1][1]
    for (d0, v0), (d1, v1) in zip(ms, ms[1:], strict=False):
        if d0 <= today <= d1:
            span = (d1 - d0).days or 1
            frac = (today - d0).days / span
            return round(v0 + (v1 - v0) * frac)
    return ms[-1][1]


def get_account():
    try:
        return float(json.load(open(ACCT)).get("value", START))
    except Exception:
        return float(START)


def set_account(value):
    json.dump({"value": float(value), "updated": datetime.now(ET).isoformat(timespec="seconds")},
              open(ACCT, "w"), indent=2)


def next_milestone(today=None):
    today = today or datetime.now(ET).date()
    for d, v in _milestone_dates():
        if d >= today:
            return d.isoformat(), v
    return _milestone_dates()[-1][0].isoformat(), _milestone_dates()[-1][1]


def status():
    acct = get_account()
    tgt = target_for()                      # the stated ambition — reported, not steered by
    ev = evidence_target()                  # what the validated edge actually supports
    ambition_pct = (acct / tgt - 1) * 100 if tgt else 0
    # AGGRESSION is measured against the EVIDENCE curve. Measuring it against an unreachable ambition
    # would pin the agent in permanent catch-up mode.
    ahead_pct = (acct / ev - 1) * 100 if ev else 0
    nm_date, nm_val = next_milestone()
    if ahead_pct > 15:
        aggr = "PROTECT"; anote = "ahead of the curve — bank gains, be extra selective, smaller size, defend the lead."
    elif ahead_pct < -15:
        aggr = "LEAN-IN"; anote = "behind the curve — take MORE of the A+ aligned setups (not bigger reckless bets); stay within risk caps."
    else:
        aggr = "ON-TRACK"; anote = "on pace — trade the aligned setups at normal size, stay disciplined."
    return {"account": round(acct), "target_now": tgt, "ahead_pct": round(ahead_pct),
            "evidence_target": ev, "ambition_pct": round(ambition_pct),
            "next_milestone": {"date": nm_date, "value": nm_val}, "aggression": aggr, "aggr_note": anote,
            "risk_cap": RISK_CAP,
            "line": f"${round(acct):,} vs evidence curve ${ev:,} ({'+' if ahead_pct>=0 else ''}{round(ahead_pct)}%) → {aggr}. "
                    f"Stated ambition ${tgt:,} today ({'+' if ambition_pct>=0 else ''}{round(ambition_pct)}%) — "
                    f"not supported by the validated edge."}


def prompt_block():
    s = status()
    return (f"ACCOUNT GROWTH PLAN: account ${s['account']:,}. The EVIDENCE curve — what the one validated "
            f"edge actually supports — says ${s['evidence_target']:,} today ({s['ahead_pct']:+d}%). "
            f"The stated ambition (${s['target_now']:,} today, ${s['next_milestone']['value']:,} by "
            f"{s['next_milestone']['date']}) is NOT reachable with any rule that survived testing: it would "
            f"need ~374% of the account risked per trade. Do not trade toward the ambition — trade the "
            f"evidence curve and let compounding do the work. "
            f"AGGRESSION: {s['aggression']} — {s['aggr_note']} "
            f"HARD CAPS (never exceed): ≤{RISK_CAP['max_risk_per_trade_pct']}% risk per trade, "
            f"≤{RISK_CAP['max_open']} open positions, stop for the day at −{RISK_CAP['daily_loss_stop_pct']}%. "
            "Do NOT chase the target with oversize or by forcing low-conviction trades — that ends the run. "
            "When behind, the answer is MORE aligned A+ setups, never bigger gambles.")


if __name__ == "__main__":
    print(json.dumps(status(), indent=2))
