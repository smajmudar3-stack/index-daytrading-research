"""The Weekly view: the macro read, the NDX verdict, the cards, and the refusals.

FOUR PANELS, IN THE ORDER YOU SHOULD READ THEM.

  macro()    where the week's view comes from, and how old it is. First, because every
             card below is downstream of it, and a card whose macro is two days stale is
             not a weaker card, it is a different week's card.
  index()    what the macro says about NDX itself. Usually "no directional trade", stated
             out loud rather than left as an empty list.
  trades()   the cards, each with the theme it expresses and the level that kills it.
  refused()  every name considered and thrown out, with the reason. This is not debug
             output. The old swing panel showed eight names and said nothing about the
             ninety it discarded, so a thin week and a broken scan looked identical from
             the page. Here you can tell which one you are looking at.

THE ACTION RULE STILL HOLDS. Only `today.answer()` may tell you to do something. These
panels describe structures and state what would invalidate them; the gates on Today decide
whether anything is put on. A card here is a candidate with its reasoning attached, and
the panel says so in as many words.

WHY THE MACRO PANEL LEADS WITH ITS AGE. The whole point of this view is that the input is
a human macro note rather than another transform of the price series. That input has a
shelf life measured in sessions, and it is the one thing on the page that cannot be
refreshed by re-running a scan. Putting the age anywhere but the top invites reading
Monday's rates view onto Thursday's tape.
"""
import desk_notes
from idt import snapshots

from . import OK, STALE, describe, empty, panel, safe, unavailable
from .today import _age_min

FILE = "weekly_snapshot.json"


def _read():
    """(payload, refusal_panel_kwargs). The refusal carries its own fix."""
    p, st = snapshots.read(FILE)
    if st == "ok":
        return p, None
    why, fix = snapshots.explain(FILE, st)
    if st == "stale":
        return p, {"stale": True, "why": why, "fix": fix}
    return None, {"stale": False, "why": why, "fix": fix}


# ------------------------------------------------------------------- the macro ---

@safe
@describe("weekly_macro", "This week's macro read")
def macro():
    """The desk-note overlay: the one input here that is not derived from price."""
    p, st = desk_notes.overlay()
    if st != "ok":
        why, fix = snapshots.explain(desk_notes.FILE, st)
        if st == "absent":
            return empty("weekly_macro", "This week's macro read",
                         "No desk note has been ingested yet, so there is no macro read "
                         "and the weekly cards below will refuse to fire.",
                         fix="04_live_system/ingest_desk_notes.py  (or pipe a note into "
                             "desk_notes.py --ingest -)")
        return unavailable("weekly_macro", "This week's macro read", why, fix=fix)

    age_h = (desk_notes.age_min(p) or 0) / 60
    fresh_sev = None if age_h <= 24 else ("watch" if age_h <= 48 else "stop")

    rows = [{"k": "The read", "v": "", "sub": p.get("regime_line")}]

    newest = (p.get("notes_ingested") or [{}])[0]
    rows.append({
        "k": "Newest note", "v": f"{age_h:.0f}h old", "severity": fresh_sev,
        "sub": (f"{newest.get('subject', '—')} · {newest.get('date', '—')}. "
                f"{len(p.get('notes_ingested') or [])} notes in this read, from "
                f"{p.get('source', 'the desk notes')}.")})

    for d in p.get("drivers") or []:
        rows.append({"k": d.get("label", "?"),
                     "v": f"{d.get('level', '')} · {d.get('direction', '')}".strip(" ·"),
                     "sub": d.get("note")})

    for t in desk_notes.themes(p):
        fav = ", ".join(t.get("favours") or [])
        ag = ", ".join(t.get("against") or [])
        tail = ""
        if fav:
            tail += f" Names it argues for: {fav}."
        if ag:
            tail += f" Names it argues against: {ag}."
        if t.get("basis"):
            tail += f" Basis: {t['basis']}."
        rows.append({"k": t["label"], "v": t["stance"],
                     "severity": {"favour": "info", "avoid": "watch",
                                  "dispersion": "info"}.get(t["stance"]),
                     "sub": t["why"] + tail})

    for c in desk_notes.catalysts(p, within_days=21):
        rows.append({"k": f"{c['date']} (+{c['days_away']}d)", "v": c.get("label", ""),
                     "severity": "watch" if c["days_away"] <= 3 else None,
                     "sub": c.get("what_it_moves")})

    for b in p.get("desk_book") or []:
        rows.append({"k": f"Their book · {b.get('asset', '?')}", "v": b.get("action", ""),
                     "sub": b.get("note")})

    if p.get("coverage_note"):
        rows.append({"k": "Coverage", "v": "", "sub": p["coverage_note"]})

    return panel("weekly_macro", "This week's macro read",
                 state=STALE if fresh_sev == "stop" else OK,
                 age_min=desk_notes.age_min(p), severity=fresh_sev,
                 body={"rows": rows},
                 note=("This is the only input on the page that is not a transform of the "
                       "price series, which is the entire reason the weekly cards are "
                       "conditioned on it rather than on another moving average."),
                 source=p.get("source", "desk notes"))


# ------------------------------------------------------------------- the index ---

@safe
@describe("weekly_index", "NDX this week")
def index():
    """What the macro says about the index itself — usually that there is no index trade."""
    p, bad = _read()
    if p is None:
        return unavailable("weekly_index", "NDX this week", bad["why"], fix=bad["fix"])
    if not p.get("ok"):
        return unavailable("weekly_index", "NDX this week",
                           p.get("blocked", "The weekly engine refused to run."),
                           fix=p.get("fix", "idt refresh"))
    read = p.get("index_read") or {}
    if not read.get("rows"):
        return empty("weekly_index", "NDX this week",
                     "The engine ran but produced no index read.")
    return panel("weekly_index", "NDX this week",
                 state=STALE if bad else OK,
                 age_min=_age_min(FILE), severity="stop",
                 body={"rows": read["rows"]},
                 note=("The index read is a refusal on purpose. Two real forces point "
                       "opposite ways, so the tradeable expression is in the names, not "
                       "in the index."),
                 source="weekly_swing.index_read()")


# ------------------------------------------------------------------- the cards ---

@safe
@describe("weekly_trades", "Weekly trade cards")
def trades():
    """The cards. Every one carries its macro theme, its expiry reason, and its exits."""
    p, bad = _read()
    if p is None:
        return unavailable("weekly_trades", "Weekly trade cards", bad["why"], fix=bad["fix"])
    if not p.get("ok"):
        return unavailable("weekly_trades", "Weekly trade cards",
                           p.get("blocked", "The weekly engine refused to run."),
                           fix=p.get("fix", "idt refresh"))

    cards = p.get("cards") or []
    if not cards:
        return empty("weekly_trades", "Weekly trade cards",
                     f"The scan ran across {p.get('n_considered', '?')} names and none "
                     f"cleared. Most weeks that is the correct answer; the panel below "
                     f"lists what was thrown out and why.")

    out = []
    for c in cards:
        out.append({
            "ticker": c["ticker"],
            "direction": c["direction"],
            "spot": c["spot"],
            "structure": c["structure"],
            "structure_why": c["structure_why"],
            "legs": c["legs"],
            "expiry": c["expiry"],
            "dte": c["dte"],
            "expiry_why": c["expiry_why"],
            "net": c["net"],
            "is_debit": c["is_debit"],
            "max_risk": c["max_risk_usd"],
            "max_reward": c.get("max_reward_usd"),
            "rr": c.get("rr"),
            "cost_pct": c.get("cost_pct"),
            "iv_front": c.get("iv_front"),
            "iv_back": c.get("iv_back"),
            "term_ratio": c.get("term_ratio"),
            "rvol": c.get("rvol"),
            "implied_move": c.get("implied_move_pct"),
            "themes": c.get("themes") or [],
            "macro_why": c.get("macro_why"),
            "tape": c.get("tape"),
            "target": c.get("target"),
            "stop": c.get("stop"),
            "invalidation": c.get("invalidation"),
            "warn": c.get("warn"),
            "vol_only": c.get("vol_only"),
        })

    return panel("weekly_trades", "Weekly trade cards",
                 state=STALE if bad else OK, age_min=_age_min(FILE),
                 body={"cards": out,
                       "macro_as_of": p.get("macro_as_of"),
                       "macro_age_h": p.get("macro_age_h")},
                 note=("UNPROVEN, not validated. This repo measured every systematic, "
                       "price-derived swing option overlay as worse than owning the index. "
                       "These cards are conditioned on a macro note instead, which has "
                       "never been tested here — so each one states the theme it expresses "
                       "and the price that proves it wrong, and gets scored later."),
                 source="weekly_swing.run() · real chains, every leg priced at the ask "
                        "when bought and the bid when sold")


# ---------------------------------------------------------------- the refusals ---

@safe
@describe("weekly_refused", "Considered and thrown out")
def refused():
    """What did not make it, and why. A thin week and a broken scan must look different."""
    p, bad = _read()
    if p is None or not p.get("ok"):
        return empty("weekly_refused", "Considered and thrown out",
                     "No completed scan to report refusals from.")
    rs = p.get("refusals") or []
    if not rs:
        return empty("weekly_refused", "Considered and thrown out",
                     "Nothing was refused in the last scan.")

    # Group by reason: fifteen rows saying "no theme names this ticker" is one fact.
    buckets = {}
    for r in rs:
        why = r.get("why") or "no reason recorded"
        head = why.split(";")[0].strip()
        key = ("no desk-note theme names this ticker"
               if head.startswith("no desk-note theme") else head)
        buckets.setdefault(key, []).append(r.get("ticker", "?"))

    rows = []
    for why, tks in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        rows.append({"k": ", ".join(tks), "v": "", "sub": why})

    return panel("weekly_refused", "Considered and thrown out",
                 state=OK, age_min=_age_min(FILE), body={"rows": rows},
                 note=(f"{len(rs)} of {p.get('n_considered', '?')} names did not produce a "
                       f"card. A name with no macro theme behind it is deliberately not "
                       f"proposed: that refusal is the fix for a panel that used to rank "
                       f"a hundred names on momentum and always find eight."),
                 source="weekly_swing.run()")
