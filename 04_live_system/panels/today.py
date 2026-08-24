"""Today — the only view that answers "what should I do right now".

Everything here supports one decision. Nothing here except `answer()` is allowed to
contain an action verb; the rest is evidence for it, and says so.
"""
import json
import os
import time

from idt import paths

from . import OK, STALE, describe, empty, panel, safe, unavailable

ET_FMT = "%Y-%m-%d %H:%M ET"


def _load(name):
    """A snapshot, or None. Distinguishes absent from unreadable for the caller."""
    p = os.path.join(paths.STATE_ROOT, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _age_min(name):
    p = os.path.join(paths.STATE_ROOT, name)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 60


# --------------------------------------------------------------------- answer ---

@safe
@describe("answer", "Today's decision")
def answer():
    """The one decision, its reason, and how much of it is measured.

    Reads master_call.json when the agent has produced one, and falls back to the
    deterministic gate stack when it has not. The fallback matters: the old page had
    no answer at all when the LLM had not run, so the operator filled the gap from
    whichever panel shouted loudest, which is the behaviour this view exists to end.
    """
    gates = _gate_blockers()
    d = _load("master_call.json")

    # The gates are deterministic and they outrank the model. If anything is blocking,
    # the answer is STAND DOWN regardless of what the agent proposed, and the page says
    # which gate. risk_gates would refuse the trade anyway; the UI used to not show it.
    if gates:
        return panel(
            "answer", "Today's decision", state=OK, severity="info",
            body={
                "label": "DECISION",
                "verb": "STAND DOWN",
                "because": ("The deterministic gates are not all open, so no position may be "
                            "entered. This is the expected answer on most days: the validated "
                            "entry window fires on roughly 81 sessions a year."),
                "blockers": gates,
                "trust": _trust_sentence(),
            })

    if not d:
        return panel(
            "answer", "Today's decision", state=OK, severity="info",
            body={
                "label": "DECISION",
                "verb": "STAND DOWN",
                "because": ("Every gate is open, but no proposal has been produced this cycle. "
                            "Run a cycle to get one."),
                "rows": [{"k": "why", "v": "no master_call.json yet"}],
                "trust": _trust_sentence(),
            },
            fix="idt refresh")

    if not d.get("ok"):
        return unavailable(
            "answer", "Today's decision",
            f"The decision engine failed: {d.get('error', 'no reason recorded')}",
            fix="idt refresh, then idt audit to see which input is missing.")

    act = d.get("action", "STAND_DOWN")
    if act != "ENTER":
        return panel(
            "answer", "Today's decision", state=OK, severity="info",
            body={
                "label": f"DECISION · {d.get('as_of', '')}",
                "verb": "STAND DOWN",
                "because": d.get("thesis") or d.get("headline") or
                           "No setup that clears the gates and the sizing rules.",
                "trust": _trust_sentence(),
            })

    struct = str(d.get("structure", "")).replace("_", " ")
    credit = str(d.get("structure", "")).endswith(("CONDOR", "CREDIT_SPREAD"))
    rows = [
        {"k": "structure", "v": f"{d.get('symbol', '')} {struct}"},
        {"k": "strikes", "v": d.get("strikes", "—")},
        {"k": "credit received" if credit else "debit paid", "v": _px(d.get("entry_price"))},
        {"k": "take profit", "v": _px(d.get("take_profit_price"))},
        {"k": "stop", "v": _px(d.get("stop_price")), "severity": "stop"},
    ]
    if d.get("contradicts_research"):
        rows.append({"k": "research", "v": "CONTRADICTS — discretionary override", "severity": "stop"})

    return panel(
        "answer", "Today's decision", state=OK, severity="watch",
        body={
            "label": f"DECISION · {d.get('as_of', '')}",
            "verb": f"{d.get('symbol', '')} {struct}".strip(),
            "because": d.get("thesis") or d.get("headline") or "",
            "rows": rows,
            "trust": _trust_sentence(),
        })


def _px(v):
    try:
        return f"${float(v):.2f}"
    except (TypeError, ValueError):
        return str(v or "—")


def _gate_blockers():
    """Every deterministic reason trading is not permitted right now.

    Sourced from rules.gate_state(), which now also consults the event calendar. A
    gate that cannot evaluate counts as a blocker, not as a pass: seven gates used to
    return "allow" on an exception, including check_entry itself.
    """
    out = []
    try:
        import rules
        g = rules.gate_state()
        if not g.get("open"):
            for r in g.get("reasons", []):
                out.append({"gate": "entry", "reason": r})
    except Exception as e:                          # noqa: BLE001
        out.append({"gate": "entry", "reason": f"gate could not be evaluated: {e}"})

    try:
        import risk_gates
        cal = risk_gates.event_calendar_status()
        if cal.get("state") not in ("ok", "current", None):
            out.append({"gate": "event calendar", "reason": cal.get("reason", cal.get("state"))})
    except Exception as e:                          # noqa: BLE001
        out.append({"gate": "event calendar", "reason": f"could not be read: {e}"})
    return out


def _trust_sentence():
    """How much of the track record behind this decision is real money-shaped.

    This is the number the whole redesign exists to surface. It was computed and then
    buried in a footnote; a 0%-measured track record and a 90%-measured one should not
    read the same, and until now they did.
    """
    try:
        import graduation
        s = graduation.stats()
        pct = s.get("measured_pct")
        if pct is None and s.get("measured_fraction") is not None:
            pct = round(s["measured_fraction"] * 100)
        n = s.get("n") or 0
        if not n:
            return ("No closed trades yet, so there is no track record behind this. "
                    "Every expectancy on this page is modelled.")
        return (f"{pct}% of the {n} closed trades behind this were priced from real option "
                f"premium; the rest are estimates from the underlying's move. "
                f"Treat the modelled share as unproven.")
    except Exception as e:                          # noqa: BLE001
        return f"Track record unavailable ({type(e).__name__}), so trust nothing on this page yet."


# ---------------------------------------------------------------------- gates ---

@safe
@describe("gates", "The gate stack")
def gates():
    """Every deterministic gate and its current state, including the ones that pass."""
    rows = []
    try:
        import risk_gates
        enforced = sorted(getattr(risk_gates, "ENFORCED", []))
        shadow = sorted(getattr(risk_gates, "SHADOW", []))
    except Exception as e:                          # noqa: BLE001
        return unavailable("gates", "The gate stack", f"risk_gates could not be imported: {e}",
                           fix="venv/bin/python -c 'import risk_gates'")

    blockers = {b["reason"]: b for b in _gate_blockers()}
    for g in enforced:
        rows.append({"k": g.replace("_", " "), "v": "enforced"})
    for g in shadow:
        rows.append({"k": g.replace("_", " "), "v": "SHADOW — logged only, not enforced",
                     "severity": "watch"})

    dry = getattr(risk_gates, "DRY_RUN", True)
    live = getattr(risk_gates, "LIVE_AGENT", False)
    rows.append({"k": "DRY_RUN", "v": str(dry), "severity": None if dry else "stop"})
    rows.append({"k": "LIVE_AGENT", "v": str(live), "severity": None if not live else "stop"})

    note = ("Both switches must flip for a real order, and no order-placement code exists "
            "in this repo regardless. Everything here is paper.")
    if blockers:
        note = f"{len(blockers)} reason(s) currently blocking entry. " + note

    return panel("gates", "The gate stack", state=OK, body={"rows": rows}, note=note,
                 source="risk_gates.ENFORCED, rules.gate_state()")


# ------------------------------------------------------------------- regime ---

@safe
@describe("regime", "Dealer gamma — the range read")
def regime():
    """The one finding that survived. A range forecast, never a direction."""
    x = _load("gex_snapshot.json")
    if x is None:
        return empty("regime", "Dealer gamma — the range read",
                     "No gamma snapshot has been written yet.",
                     fix="idt refresh   (writes 04_live_system/data/gex_snapshot.json)")

    age = _age_min("gex_snapshot.json")
    stale = age is not None and age > 90
    rows = [
        {"k": "regime", "v": x.get("regime", "—")},
        {"k": "range expected", "v": x.get("call", "—")},
        {"k": "expected open to close", "v": f"{x.get('exp_oc', '—')}%"},
        {"k": "expected range", "v": f"{x.get('exp_range', '—')}%"},
    ]
    if x.get("gex_z") is not None:
        rows.append({"k": "prior-close GEX z", "v": f"{x['gex_z']:+.2f}"})

    return panel(
        "regime", "Dealer gamma — the range read",
        state=STALE if stale else OK,
        severity="watch" if stale else None,
        age_min=age,
        body={"rows": rows, "text": x.get("note", "")},
        note=("Dealer gamma predicts how BIG the day is, never which way. Realised range "
              "comes in at 0.843x the VIX9D-implied move on high-gamma days against 1.139x "
              "on low, t = -13.2 over fifteen years. It does not convert into a profitable "
              "trade at real prices, which is itself the finding."),
        source=x.get("regime_source") or "SqueezeMetrics prior close")


# ---------------------------------------------------------------- positions ---

@safe
@describe("positions", "Open positions")
def positions():
    try:
        import positions as pos
        rows_raw = pos.list_open()
    except Exception as e:                          # noqa: BLE001
        return unavailable("positions", "Open positions",
                           f"The position book could not be read: {type(e).__name__}: {e}",
                           fix="Check 04_live_system/data/positions.db")

    if not rows_raw:
        return empty("positions", "Open positions",
                     "Nothing open. This is a normal state, not an error.",
                     fix="Positions are recorded when you enter one, from the Markets view.")

    rows = []
    for p in rows_raw:
        label = f"{p.get('sym', '')} {p.get('strike', '')} {p.get('dir', '')}"
        rows.append({"k": label, "v": f"{p.get('qty', 1)} @ ${p.get('prem', '—')}"})
    return panel("positions", "Open positions", state=OK, body={"rows": rows},
                 source="positions.db")
