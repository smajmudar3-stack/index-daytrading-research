"""Risk and account — sizing, caps, the graduation bar and the event calendar.

The event calendar panel exists because the blackout gate was ENFORCED but inert: it
returned "no events" on any exception, so a missing or stale data/events.json let
trading through every single day while reporting as enforced. FOMC and CPI dates are
hand-entered, which is exactly the kind of file that goes stale without anyone noticing.
Its age belongs on screen.
"""
from . import OK, describe, empty, panel, safe, unavailable


@safe
@describe("events", "Event calendar")
def events():
    try:
        import risk_gates
        cal = risk_gates.event_calendar_status()
    except Exception as e:                          # noqa: BLE001
        return unavailable("events", "Event calendar",
                           f"risk_gates.event_calendar_status() failed: {type(e).__name__}: {e}")

    state = cal.get("state", "unknown")
    good = state in ("ok", "current")
    rows = [
        {"k": "state", "v": state, "severity": None if good else "stop"},
        {"k": "file age", "v": (f"{cal['age_days']:.0f} days" if cal.get("age_days") is not None
                                else "—")},
        {"k": "newest entry", "v": cal.get("newest") or "—"},
    ]
    if cal.get("days_until_newest") is not None:
        rows.append({"k": "calendar runs out in", "v": f"{cal['days_until_newest']} days",
                     "severity": "watch" if cal["days_until_newest"] < 14 else None})

    note = (cal.get("reason") or "").rstrip(". ")
    if note:
        note += "."
    if not good:
        note = (f"{note} Trading is blocked while this is true. It used to be permitted: "
                "the gate returned 'no events' on any read failure, so an absent calendar "
                "looked identical to a clear day.")
    return panel("events", "Event calendar", state=OK,
                 severity=None if good else "stop",
                 body={"rows": rows}, note=note,
                 fix=None if good else "Add FOMC and CPI dates to 04_live_system/data/events.json",
                 source="risk_gates.event_calendar_status()")


@safe
@describe("account", "Account and sizing")
def account():
    try:
        import growth_plan
        st = growth_plan.status()
    except Exception as e:                          # noqa: BLE001
        return unavailable("account", "Account and sizing",
                           f"growth_plan.status() failed: {type(e).__name__}: {e}")

    rows = []
    for k, label in (("account", "account value"), ("milestone", "next milestone"),
                     ("aggression", "aggression state"), ("risk_cap_pct", "risk cap per trade"),
                     ("max_open", "max concurrent"), ("daily_stop_pct", "daily loss stop")):
        if k in st:
            rows.append({"k": label, "v": str(st[k])})
    if not rows:
        rows = [{"k": k, "v": str(v)} for k, v in list(st.items())[:8]]

    return panel("account", "Account and sizing", state=OK, body={"rows": rows},
                 note=("Being behind the growth curve relaxes selectivity, never these caps. "
                       "Position size for the tail, not the win rate: a 91% win rate with "
                       "losers at half of risk still means twelve consecutive max-losers is a "
                       "45% drawdown at 5% risk."),
                 source="growth_plan.status()")


@safe
@describe("graduation", "The graduation bar")
def graduation():
    """The pre-registered paper-to-live bar. Moving it is a visible code change."""
    try:
        import graduation as grad
        chk = grad.check()
        stats = grad.stats()
    except Exception as e:                          # noqa: BLE001
        return unavailable("graduation", "The graduation bar",
                           f"graduation could not be read: {type(e).__name__}: {e}")

    n = stats.get("n") or 0
    if not n:
        return empty("graduation", "The graduation bar",
                     "No closed trades yet, so there is nothing to measure against the bar.",
                     fix="The bar is pre-registered in graduation.BAR and needs 30 filled condors.")

    rows = []
    for k, v in (chk.get("criteria") or {}).items():
        met = v.get("met") if isinstance(v, dict) else None
        val = v.get("value") if isinstance(v, dict) else v
        rows.append({"k": k.replace("_", " "), "v": str(val),
                     "severity": None if met else "watch"})
    if not rows:
        rows = [{"k": k, "v": str(v)} for k, v in list(chk.items())[:8] if k != "criteria"]

    fp = chk.get("bar_fingerprint")
    return panel("graduation", "The graduation bar", state=OK, body={"rows": rows},
                 note=("The bar is pre-registered. Moving it to make a result pass is a visible "
                       "code change, which is the point."
                       + (f" Fingerprint {fp}." if fp else "")),
                 source="graduation.check()")


@safe
@describe("services", "Service health")
def services():
    """Missing key, rejected key and service outage are three different states.

    They used to be one. A lapsed Unusual Whales subscription returns 401 with a valid
    key still present, which made available() report healthy and then crashed the page
    on None-valued fields.
    """
    rows = []
    for name in ("ai_desk", "analyst", "uw_client", "fetch_minutes", "committee", "master_call"):
        try:
            mod = __import__(name)
            st = mod.status() if hasattr(mod, "status") else {"state": "no status()"}
            state = st.get("state", "unknown") if isinstance(st, dict) else str(st)
            why = st.get("detail") or st.get("why") or "" if isinstance(st, dict) else ""
            sev = None if state in ("available", "ok") else (
                "watch" if state in ("no-key", "disabled") else "stop")
            # The state is the VALUE and the sentence is a sub-line. They were joined
            # into one right-aligned mono string, which set six sentences of amber
            # monospace ragged-left against the card edge and was unreadable.
            rows.append({"k": name, "v": state, "severity": sev, "sub": why})
        except Exception as e:                      # noqa: BLE001
            rows.append({"k": name, "v": "import failed", "severity": "stop",
                         "sub": f"{type(e).__name__}: {e}"})

    return panel("services", "Service health", state=OK, body={"rows": rows},
                 note=("A missing key is not an outage and neither is a rejected one. Each row "
                       "says which, because the fix is different for each."),
                 fix="Copy .env.example to .env and fill in what you have.",
                 source="each module's status()")
