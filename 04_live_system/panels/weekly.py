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
            "no_macro_basis": c.get("no_macro_basis"),
            "backing": c.get("backing") or [],
            "n_backing": c.get("n_backing"),
            "theme_inherited": c.get("theme_inherited"),
            "cap_tier": c.get("cap_tier"),
            "trend": c.get("trend") or {},
            # The evidence-weighted vote, shown in full. A card built almost entirely on
            # inputs that have never been backtested must SAY so on its face.
            "vote_score": c.get("vote_score"),
            "vote_confidence": c.get("vote_confidence"),
            "unmeasured_share": c.get("unmeasured_share"),
            "vote_detail": c.get("vote_detail") or [],
            "insider_open_buys": c.get("insider_open_buys"),
            "short_float_pct": c.get("short_float_pct"),
            "move_view": c.get("move_view"),
            "move_why": c.get("move_why"),
            "sector": c.get("sector"),
            "evidence": c.get("evidence"),
            "breakevens": c.get("breakevens") or [],
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


# ------------------------------------------------------------ the live book ---

@safe
@describe("weekly_book", "Open recommendations, marked live")
def book():
    """Every card that was issued, marked against the chain since it was issued.

    THIS IS THE PANEL THAT MAKES THE OTHERS HONEST. `weekly_swing` rebuilds its cards from
    scratch every cycle, so without a ledger a losing recommendation simply vanishes and is
    replaced by a fresh one at a fresh price. The page would then show healthy suggestions
    forever. Here the entry price is the one from the moment the card was first issued and
    is never rewritten, so a trade that is down stays visibly down.

    The marks pay the full bid-ask twice, in and out. They will read worse than any
    mid-to-mid number, and that gap is the point.
    """
    import weekly_book as wb

    rows_open = wb.open_book()
    owned = wb.owned_book()
    hist = wb.history(8)
    summary = wb.record_summary()

    if not rows_open and not hist and not owned:
        return empty("weekly_book", "Open recommendations, marked live",
                     "No card has been recorded yet. The book fills the first time the "
                     "weekly scan produces a card during market hours.",
                     fix="04_live_system/weekly_book.py")

    live = wb._market_open() is True
    return panel("weekly_book", "Open recommendations, marked live",
                 state=OK,
                 severity=None if live else "watch",
                 body={"open": rows_open, "owned": owned, "closed": hist,
                       "summary": summary, "live": live},
                 note=("Marked against the live chain, paying the full bid-ask both ways. "
                       + ("" if live else
                          "The market is shut, so these marks are INDICATIVE: quotes widen "
                          "after the bell and a spread priced on them reads far worse than "
                          "it would trade. Nothing is closed on a mark like this.")),
                 source="weekly_book.mark() · entry price frozen at the moment of issue")


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


@safe
def calendar():
    """The dated macro prints, and what the open book is exposed to.

    ON THE PAGE BECAUSE IT WAS INVISIBLE. `_pick_weekly` and `weekly_book.exit_verdict` both
    consume this calendar, so the engine acts on it correctly — but nothing SHOWED it, and the
    day it was added it turned out 28 of 36 open positions expired on CPI morning. A control
    the operator cannot see is one they cannot sanity-check.
    """
    import macro_calendar

    ev = macro_calendar.upcoming(within_days=45, min_importance="medium")
    _payload, status = macro_calendar.load()
    if not ev:
        return empty("weekly_calendar", "Macro calendar",
                     "No dated macro release in the next 45 days, which is unusual enough to "
                     "be worth checking rather than trusting.",
                     fix="04_live_system/macro_calendar.py --refresh")

    rows, worst = [], None
    for e in ev:
        sev = "stop" if (e["importance"] == "high" and e["days_away"] <= 5) else (
            "watch" if e["importance"] == "high" else "info")
        if sev == "stop":
            worst = "stop"
        rows.append({"k": f"{e['date']} {e.get('time') or ''}".strip(),
                     "v": e["label"],
                     "sub": f"in {e['days_away']}d — {e['what_it_moves']}",
                     "severity": sev})

    # What the OPEN BOOK is actually exposed to, which is the part that costs money.
    exposed = []
    try:
        import weekly_book
        from collections import Counter
        byexp = Counter(r.get("expiry") for r in weekly_book.open_book())
        for expiry, n in sorted(byexp.items()):
            hits = [c for c in macro_calendar.collisions(expiry)
                    if c.get("importance") == "high"]
            if hits:
                worst = "stop"
                exposed.append({
                    "k": f"{n} position(s) expiring {expiry}",
                    "v": hits[0]["label"],
                    "sub": ("lands ON that expiry — no session left to recover, so close "
                            "before it rather than through it"
                            if hits[0].get("on_expiry_day")
                            else f"{hits[0]['days_left_after']}d of room afterwards"),
                    "severity": "stop" if hits[0].get("on_expiry_day") else "watch"})
    except Exception:                                         # noqa: BLE001
        exposed = []

    note = ("Dates come from the BLS and Federal Reserve release schedules, not from the desk "
            "notes — the desk described the August CPI print three times without ever dating "
            "it, so the engine could not see the event it was most exposed to.")
    return panel("weekly_calendar", "Macro calendar", state=OK,
                 body={"rows": rows, "exposed": exposed},
                 note=note, severity=worst or "info",
                 source=f"BLS / Federal Reserve schedules ({status})")


@safe
def earnings_vol():
    """Names reporting inside the window, and whether their options are dear or cheap.

    The one Unusual Whales input in this repo with a measurement behind it rather than a
    literature prior. It is a statement about the SIZE of a move and never about its
    direction, and the panel says so, because every place this repo has blurred those two has
    cost it money.
    """
    # READ FROM THE SNAPSHOT, NEVER LIVE.
    #
    # The first version of this panel called `earnings_vol.scan()` directly, which makes a
    # string of Unusual Whales requests. That is the wrong layer: every other panel in this
    # repo reads a snapshot, and it is why the page renders in milliseconds and survives a
    # dead vendor. Doing the network work here hung the test suite for ten minutes and would
    # have hung the page the same way under rate limiting. The scan computes it; the panel
    # displays it.
    p, bad = _read()
    if bad and not p:
        return unavailable("weekly_earnings_vol", "Earnings volatility",
                           bad["why"], fix=bad.get("fix"))
    rows_raw = (p or {}).get("earnings_vol") or []
    if not rows_raw:
        return empty("weekly_earnings_vol", "Earnings volatility",
                     "No company with listed options reports inside the expiry window, or "
                     "Unusual Whales was unavailable when the scan last ran.")

    rows = []
    for r in rows_raw:
        v = r.get("vrp") or {}
        verdict = v.get("verdict")
        rows.append({
            "k": r["ticker"],
            "v": {"rich": "SELL the event", "cheap": "BUY the event",
                  "fair": "no vol view"}.get(verdict, "no vol history"),
            "sub": (f"reports {r['date']} (+{r['days_away']}d, {r['when']})"
                    + (f" · premium at the {v['pctile']:.0%} percentile of its own year"
                       if v.get("pctile") is not None else "")
                    + (f" · market pricing a {r['expected_move_pct']:.1f}% move"
                       if r.get("expected_move_pct") else "")),
            # Colour is severity, never direction: a rich premium is an opportunity, not a
            # warning, so nothing here goes above "watch".
            "severity": "watch" if verdict in ("rich", "cheap") else "info"})

    return panel("weekly_earnings_vol", "Earnings volatility", state=OK,
                 body={"rows": rows}, severity="info",
                 note=("Measured, not assumed: across 266 events, rich-percentile premiums "
                       "showed a +3.63pt seller edge against -4.30pt for cheap ones, monotone "
                       "and holding in all three period splits. Implied is flat across the "
                       "buckets while realised falls, so it forecasts the move rather than "
                       "labelling dear prices. It picks the STRUCTURE, never the direction."),
                 source="Unusual Whales variance risk premium · 02_findings/earnings_vrp.md")


@safe
def data_lake():
    """How much flow history has accumulated, and how much is still needed.

    Four of the seven voters are Unusual Whales inputs with no history, so their weights are
    literature priors rather than measurements. This is the counter that will eventually let
    them be measured, and it is on the page so the wait is visible instead of forgotten.
    """
    import flow_tape

    s = flow_tape.snapshot_summary()
    pct = min(100, int(100 * s["sessions"] / max(1, s["min_days"])))
    rows = [
        {"k": "Sessions recorded", "v": f"{s['sessions']} of {s['min_days']}",
         "sub": f"{pct}% of the way to a testable sample"},
        {"k": "Rows", "v": f"{s['rows']:,}", "sub": f"across {s['names']} names"},
    ]
    if s.get("first"):
        rows.append({"k": "Span", "v": f"{s['first']} → {s['last']}", "sub": None})

    return panel("weekly_data_lake", "Flow history", state=OK,
                 body={"rows": rows, "ready": s["ready"]},
                 severity="info",
                 note=("Recording only. Nothing is fitted to this yet and a guard refuses any "
                       "study until 60 sessions exist. Flow, dark pool, short float and "
                       "insider buys carry literature priors because the endpoints keep no "
                       "history; this is how they eventually get measured instead. The "
                       "threshold was set before there was a result to be tempted by."),
                 source="flow_tape.db — raw endpoint readings, never the vote")


@safe
def freshness():
    """Which self-refreshing assets are current, and which have aged out.

    THE PANEL THAT EXISTS SO NOBODY HAS TO ASK. Every asset here has a shelf life, and a stale
    one is worse than a missing one because it still answers: an aged universe still returns
    1,550 names, an aged calendar still names a CPI date. Both would be wrong in a way nothing
    announced. This is the page saying so on its own.
    """
    import maintenance

    st = maintenance.status()
    rows = []
    for r in st["rows"]:
        age = f"{r['days']}d old" if r["days"] is not None else "live"
        limit = f" (renews after {r['limit']}d)" if r.get("limit") else ""
        rows.append({"k": r["name"].replace("_", " "),
                     "v": r["state"],
                     "sub": f"{age}{limit} — {r['detail']}",
                     "severity": r["severity"]})
    return panel("weekly_freshness", "Data freshness", state=OK,
                 body={"rows": rows}, severity=st["severity"],
                 note=("Checked every five minutes; the universe and the calendar renew "
                       "themselves when they age out. The BLS pages return 403 to any script, "
                       "so the macro calendar is refreshed monthly by a scheduled Claude "
                       "session instead — a `seed` state means it is still on the "
                       "transcription and has not yet been machine-verified."),
                 source="maintenance.py — ages read from each asset's own stamp")
