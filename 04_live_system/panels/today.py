"""Today — the only view that answers "what should I do right now".

Everything here supports one decision. Nothing here except `answer()` is allowed to
contain an action verb; the rest is evidence for it, and says so.
"""
import json
import os
import time

from idt import paths, snapshots

from . import OK, STALE, describe, empty, panel, safe, unavailable


def _snapshot(filename):
    """A snapshot plus a ready-made panel if it cannot be used.

    Returns (payload, bad_panel_kwargs). If bad_panel_kwargs is not None the caller
    must render it instead of the data: a wrong-version snapshot in particular is not
    old data to warn about, it is data written by code that no longer exists.
    """
    payload, status = snapshots.read(filename)
    if status == "ok":
        return payload, None
    why, fix = snapshots.explain(filename, status)
    if status == "absent":
        return None, {"kind": "empty", "why": why, "fix": fix}
    if status == "stale":
        return payload, {"kind": "stale", "why": why, "fix": fix}
    return None, {"kind": "unavailable", "why": why, "fix": fix}

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
                "because": "Deterministic gates are closed. Standing down is the expected state.",
                "detail": ("The validated entry window fires on roughly 81 sessions a year; "
                           "every other day this page should say exactly this."),
                "blockers": gates,
                "tiles": _decision_tiles(gates),
                "trust": _trust_sentence(),
            })

    if not d:
        return panel(
            "answer", "Today's decision", state=OK, severity="info",
            body={
                "label": "DECISION",
                "verb": "STAND DOWN",
                "because": "Every gate is open, but no proposal has been produced this cycle.",
                "tiles": _decision_tiles([]),
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
                "because": d.get("headline") or "No setup clears the gates and sizing rules.",
                "detail": d.get("thesis") or "",
                "tiles": _decision_tiles([], d.get("conviction")),
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
            "because": d.get("headline") or "",
            "detail": d.get("thesis") or "",
            "rows": rows,
            "tiles": _decision_tiles([], d.get("conviction")),
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


def _trust():
    """(pct, n, sentence): how much of the track record is real money-shaped.

    The number rides in a tile on the decision strip; the sentence folds behind it.
    A 0%-measured record and a 90%-measured one must not read the same.
    """
    try:
        import graduation
        s = graduation.stats()
        pct = s.get("measured_pct")
        if pct is None and s.get("measured_fraction") is not None:
            pct = round(s["measured_fraction"] * 100)
        n = s.get("n") or 0
        if not n:
            return 0, 0, ("No closed trades yet, so there is no track record behind this. "
                          "Every expectancy on this page is modelled.")
        return pct or 0, n, (f"{pct}% of the {n} closed trades were priced from real option "
                             f"premium; the rest are estimates from the underlying's move. "
                             f"Treat the modelled share as unproven.")
    except Exception as e:                          # noqa: BLE001
        return None, None, f"Track record unavailable ({type(e).__name__})."


def _trust_sentence():
    return _trust()[2]


def _decision_tiles(blockers, conviction=None):
    """The strip of instruments beside the verb: gates, trust, conviction."""
    pct, n, _ = _trust()
    tiles = [{"n": str(len(blockers)) if blockers else "0",
              "l": "gates blocking", "severity": "stop" if blockers else "live"}]
    if conviction is not None:
        tiles.append({"n": f"{conviction}", "l": "conviction /100",
                      "severity": "watch" if conviction < 66 else None})
    tiles.append({"n": f"{pct if pct is not None else '—'}%",
                  "l": f"of {n or 0} trades measured",
                  "severity": "watch" if not pct else None})
    return tiles


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

    # Drawn, not listed: each enforced gate is a chip, the two master switches are
    # switches. A wall of "enforced / enforced / enforced" rows said nothing the
    # chips do not say at a glance.
    blocked = set()
    for b in blockers.values():
        r = (b.get("reason") or "").lower()
        if "calendar" in r or "fomc" in r or "event" in r:
            blocked.add("event_blackout")
        if "et" in r.split() or "window" in r or ":" in r:
            blocked.add("time_window")
        if "gex" in r or "z-score" in r or "regime" in r:
            blocked.add("regime_gate")
    tags = [{"k": g.replace("_", " "),
             "state": "armed",
             "severity": "stop" if g in blocked else None}
            for g in enforced]
    tags += [{"k": g.replace("_", " "), "state": "shadow", "severity": "watch"}
             for g in shadow]
    switches = [
        {"k": "dry run", "v": "ON" if dry else "OFF", "safe": bool(dry)},
        {"k": "live agent", "v": "OFF" if not live else "ON", "safe": not live},
    ]

    note = ("Every chip is a deterministic veto the model cannot talk past. Both switches "
            "must flip for a real order, and no order-placement code exists in this repo "
            "regardless.")
    if blockers:
        note = f"{len(blockers)} gate(s) currently blocking entry. " + note

    return panel("gates", "The gate stack", state=OK,
                 body={"rows": rows, "tags": tags, "switches": switches}, note=note,
                 source="risk_gates.ENFORCED, rules.gate_state()")


# ------------------------------------------------------------------- regime ---

@safe
@describe("regime", "Dealer gamma — the range read")
def regime():
    """The one finding that survived. A range forecast, never a direction."""
    x, bad = _snapshot("gex_snapshot.json")
    if bad and bad["kind"] == "empty":
        return empty("regime", "Dealer gamma — the range read", bad["why"], fix=bad["fix"])
    if bad and bad["kind"] == "unavailable":
        return unavailable("regime", "Dealer gamma — the range read", bad["why"], fix=bad["fix"])

    age = _age_min("gex_snapshot.json")
    stale = bool(bad and bad["kind"] == "stale")
    rows = [
        {"k": "regime", "v": x.get("regime", "—")},
        {"k": "range expected", "v": x.get("call", "—")},
        {"k": "expected open to close", "v": f"{x.get('exp_oc', '—')}%"},
        {"k": "expected range", "v": f"{x.get('exp_range', '—')}%"},
    ]
    if x.get("gex_z") is not None:
        rows.append({"k": "prior-close GEX z", "v": f"{x['gex_z']:+.2f}"})

    # The gauge: prior-close GEX z on a −2.5..+2.5 band, the marker at today's
    # value, the condor gate line at +0.5. One glance answers "which regime, and
    # how deep into it" — the thing four rows of text made the reader assemble.
    gauge = None
    z = x.get("gex_z")
    if z is not None:
        lo, hi = -2.5, 2.5
        clamped = max(lo, min(hi, float(z)))
        pct = (clamped - lo) / (hi - lo) * 100
        gauge = {
            "pct": round(pct, 1),
            "readout": f"{z:+.2f}",
            "caption": "prior-close GEX z",
            "left": "short gamma · range expands",
            "right": "long gamma · pins",
            "severity": None,
            "ticks": [{"pct": round((v - lo) / (hi - lo) * 100, 1), "label": f"{v:+g}"}
                      for v in (-2, -1, 0, 0.5, 1, 2)],
        }

    stats = []
    if x.get("exp_oc") is not None:
        stats.append({"n": f"±{x['exp_oc']}%", "l": "expected open→close"})
    if x.get("exp_range") is not None:
        stats.append({"n": f"{x['exp_range']}%", "l": "expected range"})
    if x.get("quintile"):
        stats.append({"n": f"Q{x['quintile']}/5", "l": "gamma quintile"})

    return panel(
        "regime", "Dealer gamma — the range read",
        state=STALE if stale else OK,
        severity="watch" if stale else None,
        age_min=age,
        body={"rows": rows, "text": x.get("note", ""), "gauge": gauge, "stats": stats},
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
