"""Plays — the desk's product: a few option swing trades a week, each with its reasoning
stack, its timeline, its expected profit and the confidence it earned.

Four panels, all reading what `plays.py` wrote (the snapshot and the ledger) and never a
vendor: the week's plays and what is being managed; the candidates considered and why the
rest were refused; the scorecard (promised against delivered) with the measured priors every
promise rests on; and the strategy tree the weekly branch hunt grows.

The cards STATE a structure and its legs. They are the one place on the site, with Today's
decision, that is allowed to; everything else is context and says so.
"""
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from idt import paths, snapshots

from . import EMPTY, OK, STALE, describe, panel, safe, unavailable

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TREE = os.path.join(REPO, "docs", "strategy_tree.json")
HUNT_LOG = os.path.join(REPO, "logs", "branch_hunt.out")
RESEARCH_LOG = os.path.join(REPO, "logs", "plays_research.out")

CONF_SEVERITY = {"vetoed": "stop", "negative prior": "stop", "unmeasured": "watch"}


def _age_min(name):
    p = os.path.join(paths.STATE_ROOT, name)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 60


def _today():
    return datetime.now(ET).date()


def _monday():
    t = _today()
    return (t - timedelta(days=t.weekday())).isoformat()


def _conf_sev(label):
    for k, v in CONF_SEVERITY.items():
        if label and label.startswith(k):
            return v
    return "live" if label and label.startswith("measured") else "watch"


def _research():
    """The morning research file, keyed by ticker. Research is context around a play, not
    the promise, so a card shows the latest rather than the copy frozen at issue."""
    try:
        r, st = snapshots.read("plays_research.json")
        return (r or {}).get("names") or {}, (r or {}).get("as_of")
    except Exception:                                         # noqa: BLE001
        return {}, None


def _decorate(r, research=None):
    """A ledger row -> everything a card needs, with the next timeline step picked out."""
    today = _today().isoformat()
    rs = r.get("reasoning") or {}
    if research and r.get("ticker") in research:
        rs["research"] = research[r["ticker"]]
    r["card"] = rs.get("card") or {}
    r["timeline"] = rs.get("timeline") or []
    r["sources_list"] = [s for s in (r.get("sources") or "").split(",") if s]
    r["next"] = next((t for t in r["timeline"] if t["when"] >= today), None)
    try:
        r["days_left"] = (datetime.strptime(r["horizon_end"], "%Y-%m-%d").date() - _today()).days
        r["dte_left"] = (datetime.strptime(r["expiry"], "%Y-%m-%d").date() - _today()).days
    except (TypeError, ValueError):
        r["days_left"] = r["dte_left"] = None
    r["conf_sev"] = _conf_sev(r.get("confidence"))
    r["pnl_class"] = "up" if (r.get("pnl_pct") or 0) > 0 else ("down" if (r.get("pnl_pct") or 0) < 0 else "")
    r["research"] = rs.get("research") or None
    r["macro"] = rs.get("macro") or {}
    r["events"] = rs.get("events") or []
    r["signal"] = rs.get("signal") or {}
    r["structure"] = rs.get("structure") or {}
    r["vetoes"] = rs.get("vetoes") or []
    r["earnings"] = rs.get("earnings")
    return r


def _ledger():
    import plays as eng
    research, _ = _research()
    rows = [_decorate(r, research) for r in eng.open_plays()]
    monday = _monday()
    new = [r for r in rows if r["status"] == "open" and str(r["issued"])[:10] >= monday]
    managing = [r for r in rows if r["status"] == "open" and str(r["issued"])[:10] < monday]
    closed = [r for r in rows if r["status"] == "closed"][:12]
    return new, managing, closed, eng.scorecard()


@safe
@describe("plays", "This week's plays")
def desk():
    """The week's plays with their reasoning, timeline and expected profit, then the open
    plays being managed and the last few closed. The snapshot says what the engine decided;
    the ledger says what every card is worth now."""
    import plays as eng
    title = "This week's plays"
    p, st = snapshots.read(eng.OUT)
    if p is None or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        why, fix = snapshots.explain(eng.OUT, st)
        return unavailable("plays", title, why, fix=fix or "python3 04_live_system/plays.py --force")
    if not p.get("ok"):
        return unavailable("plays", title, p.get("blocked") or "the plays engine did not run", fix="python3 04_live_system/plays.py")
    new, managing, closed, score = _ledger()
    win = p.get("issue_window") or {}
    body = {"new": new, "managing": managing, "closed": closed, "score": score, "window": win,
            "priors_available": p.get("priors_available"), "as_of": p.get("as_of"),
            "considered_n": len(p.get("considered") or []), "refused_n": len(p.get("refused") or []),
            "notes": p.get("notes") or [], "sources": p.get("sources") or {}}
    if not (new or managing):
        if not p.get("priors_available"):
            why = ("no play can be promised yet: the option-structure backtest that prices every promise has not finished "
                   "(05_studies/play_structures_test.py writes opt_panel/play_structures.parquet)")
        elif not p.get("considered"):
            why = "no measured book holds a candidate right now" + (": " + "; ".join(p["notes"]) if p.get("notes") else "")
        elif not win.get("due_today"):
            why = (f"{len(p['considered'])} candidates priced and ranked; new plays issue on "
                   f"{' and '.join(win.get('issue_days') or ['Mon', 'Wed'])} ({win.get('issued_this_week', 0)} of {win.get('cap')} used this week)")
        else:
            why = f"{len(p['considered'])} candidates priced; none cleared with a positive measured expectancy and no veto"
        return panel("plays", title, state=EMPTY, body=body, note=why, age_min=_age_min(eng.OUT),
                     source="plays.issue() daily · ledger plays.db · priors from 05_studies/play_structures_test.py")
    note = (f"{len(new)} new this week, {len(managing)} being managed, {score.get('n_closed', 0)} closed. "
            "Every card is a measured stock signal expressed as the option structure that measured best for its horizon, "
            "priced off the live ladder at the ask and the bid, and recorded the day it was issued. Paper.")
    return panel("plays", title, state=STALE if st == "stale" else OK, body=body, note=note, age_min=_age_min(eng.OUT),
                 severity="watch" if any(r["vetoes"] for r in new + managing) else None,
                 source="plays.issue() daily, plays.mark() every 4h · plays.db · 02_findings/play_structures.md")


@safe
@describe("plays_considered", "Considered this week, and why the rest were refused")
def considered():
    """The ranked candidates the engine priced (what it would issue next) and every name it
    refused with the reason. 'Not judged' and 'rejected' are different facts; both are here."""
    import plays as eng
    title = "Considered this week, and why the rest were refused"
    p, st = snapshots.read(eng.OUT)
    if p is None or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        why, fix = snapshots.explain(eng.OUT, st)
        return unavailable("plays_considered", title, why, fix=fix)
    cons = p.get("considered") or []
    ref = p.get("refused") or []
    for c in cons:
        c["conf_sev"] = _conf_sev(c.get("confidence"))
    groups = {}
    for r in ref:
        key = str(r.get("why") or "").split(":")[0][:60]
        groups.setdefault(key, []).append(r.get("ticker"))
    body = {"considered": cons[:25], "refused": ref, "groups": sorted(groups.items(), key=lambda kv: -len(kv[1])),
            "notes": p.get("notes") or [], "window": p.get("issue_window") or {}}
    if not cons and not ref:
        return panel("plays_considered", title, state=EMPTY, body=body, age_min=_age_min(eng.OUT),
                     note="nothing was considered: " + ("; ".join(p.get("notes") or []) or "no measured book holds a candidate"))
    return panel("plays_considered", title, state=STALE if st == "stale" else OK, body=body, age_min=_age_min(eng.OUT),
                 note=(f"{len(cons)} candidates priced and ranked by measured expectancy per dollar of risk; {len(ref)} refused. "
                       "A refusal names the gate: the ladder, the spread, the expiry window, a veto, or already open."),
                 source="plays_snapshot.json · the ranking is score = mean P&L per $ risk × 1.25 when two books agree, −10 on a veto")


@safe
@describe("plays_scorecard", "Promised against delivered")
def scorecard():
    """What the plays promised when issued, what they delivered, and the measured priors
    every promise rests on (signal × structure, seven years of real chains)."""
    import plays as eng
    title = "Promised against delivered"
    p, st = snapshots.read(eng.OUT)
    if p is None or st in ("absent", "unreadable", "wrong_version", "incomplete"):
        why, fix = snapshots.explain(eng.OUT, st)
        return unavailable("plays_scorecard", title, why, fix=fix)
    score = eng.scorecard()
    pri = p.get("priors_table") or []
    body = {"score": score, "priors": pri, "sources": p.get("sources") or {}}
    if not score.get("n_closed") and not pri:
        return panel("plays_scorecard", title, state=EMPTY, body=body, age_min=_age_min(eng.OUT),
                     note="no play has closed and the structure backtest has not written its table yet")
    note = ((f"{score['n_closed']} closed: hit {score.get('hit')}, average {score.get('avg_pnl_pct')}% of risk, "
             f"delivered minus promised {score.get('promised_vs_delivered')} points. " if score.get("n_closed") else "No play has closed yet. ")
            + (f"The priors table has {len(pri)} signal × structure cells; a play is only issued from a cell that is positive in every split."
               if pri else "The priors table is empty: the structure backtest has not finished."))
    return panel("plays_scorecard", title, state=STALE if st == "stale" else OK, body=body, age_min=_age_min(eng.OUT), note=note,
                 source="plays.db · opt_panel/play_structures.parquet (05_studies/play_structures_test.py)")


# -------------------------------------------------------------- the tree ---

VERDICT_SEV = {"real": "live", "weak": "watch", "null": "faint", "dead": "stop", "not-measurable": "faint"}


def _hunt_log():
    """The last branch-hunt run: when, and whether it finished."""
    if not os.path.exists(HUNT_LOG):
        return None
    try:
        with open(HUNT_LOG, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()[-400:]
    except OSError:
        return None
    started = next((ln for ln in reversed(lines) if ln.startswith("--- branch hunt")), None)
    exit_line = next((ln for ln in reversed(lines) if ln.startswith("claude exit:")), None)
    tail = [ln for ln in lines[-12:] if ln.strip() and not ln.startswith("---")]
    return {"started": started.replace("--- branch hunt", "").strip(" -") if started else None,
            "exit": exit_line, "tail": tail[-6:]}


@safe
@describe("strategy_tree", "The strategy tree: every branch tested, and what grows next")
def tree():
    """docs/strategy_tree.json as the page reads it: one column per department, every node
    with its verdict, and the proposed branches the weekly hunt will take next."""
    title = "The strategy tree: every branch tested, and what grows next"
    try:
        with open(TREE, encoding="utf-8") as fh:
            t = json.load(fh)
    except (OSError, ValueError) as e:
        return unavailable("strategy_tree", title, f"docs/strategy_tree.json could not be read: {type(e).__name__}: {e}",
                           fix="restore docs/strategy_tree.json from git")
    nodes = t.get("nodes") or {}
    root = t.get("root")

    def walk(key, depth=0, seen=None):
        seen = seen if seen is not None else set()
        if key in seen or key not in nodes:
            return []
        seen.add(key)
        n = nodes[key]
        row = {"key": key, "depth": depth, "label": n.get("label"), "status": n.get("status"), "verdict": n.get("verdict"),
               "numbers": n.get("numbers"), "rule": n.get("rule"), "findings": n.get("findings"), "study": n.get("study"),
               "live": n.get("live"), "date": n.get("date"), "sev": VERDICT_SEV.get(n.get("verdict"), "info" if n.get("status") in ("proposed", "untested") else "")}
        out = [row]
        for c in n.get("children") or []:
            out.extend(walk(c, depth + 1, seen))
        return out

    departments = []
    counts = {"measured": 0, "live-paper": 0, "recording": 0, "proposed": 0, "untested": 0}
    verdicts = {"real": 0, "weak": 0, "null": 0, "dead": 0, "not-measurable": 0}
    for dk in (nodes.get(root) or {}).get("children") or []:
        rows = walk(dk)
        if not rows:
            continue
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            if r["verdict"]:
                verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
        departments.append({"key": dk, "label": rows[0]["label"], "verdict": rows[0]["verdict"], "sev": rows[0]["sev"], "rows": rows[1:],
                            "n_proposed": sum(1 for r in rows if r["status"] in ("proposed", "untested"))})
    proposed = [r for d in departments for r in d["rows"] if r["status"] in ("proposed", "untested")]
    body = {"as_of": t.get("as_of"), "departments": departments, "counts": counts, "verdicts": verdicts,
            "proposed": proposed, "hunt": _hunt_log(), "n_nodes": len(nodes)}
    note = (f"{len(nodes)} branches across {len(departments)} departments: {verdicts.get('real', 0)} measured real, {verdicts.get('weak', 0)} weak, "
            f"{verdicts.get('null', 0) + verdicts.get('dead', 0)} null or dead, {counts.get('proposed', 0) + counts.get('untested', 0)} proposed and waiting. "
            "Every Saturday a headless research session takes the most promising waiting branch, measures it the house way, and records the verdict here "
            "with the children it suggests. A dead branch stays on the tree with its numbers so it is never retested by accident.")
    return panel("strategy_tree", title, state=OK, body=body, note=note,
                 source="docs/strategy_tree.json · 04_live_system/branch_hunt.sh (launchd com.daytrading.branch-hunt, Saturdays)")
