"""maintenance.py — the things that go stale, refreshed without being asked.

WHY THIS EXISTS. Every asset this dashboard depends on has a shelf life, and until now three of
them had no way to renew themselves:

    the universe          S&P 500/400/600 membership drifts; `REFRESH_AFTER_DAYS` is 30 and
                          nothing called `build()` on a schedule, so it would have quietly
                          aged past its own threshold and kept serving a stale roster
    the macro calendar    transcribed on 2026-09-06 and stale after 45 days, with `refresh()`
                          needing a FRED key that is not configured
    the flow tape         accumulating, but with nothing watching whether it actually is

A stale asset is worse than a missing one, because it still answers. The universe would still
have returned 1,550 names; the calendar would still have named a CPI date. Both would have been
wrong in a way nothing on the page announced, and the operator would only find out by coming to
ask why the numbers looked odd.

WHAT A SCRIPT CAN AND CANNOT REFRESH
====================================
This runs inside the 5-minute refresh cycle and does everything a plain script is able to do.
One thing it cannot: **BLS returns HTTP 403 to any scripted request**, browser user-agent and
all, so the CPI/PPI/jobs release schedule cannot be fetched from here. That job goes to a
scheduled headless Claude session (`refresh_calendar.sh`), which is the same pattern this repo
already uses for the desk notes -- a page a script cannot read, read by something that can.

Everything here is idempotent and cheap: it checks an age and usually does nothing.
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ET = ZoneInfo("America/New_York")

# How long each asset may go without renewal before the page says so. These are the ages at
# which the DASHBOARD complains, deliberately a little shorter than the age at which the
# module itself refuses, so a warning arrives before a refusal.
WARN_AFTER = {
    "universe": 30,          # index membership drifts slowly
    "macro_calendar": 40,    # transcribed; the module refuses at 45
    "desk_notes": 3,         # sessions, not days — desk_notes owns that check
}


def _today():
    return datetime.now(ET).date()


def refresh_universe(force=False):
    """Rebuild the index-constituent universe when it has aged out. (changed, note)."""
    try:
        import universe_builder
    except Exception as e:                                    # noqa: BLE001
        return False, f"universe_builder unimportable: {type(e).__name__}: {e}"
    meta, status = universe_builder.load()
    if not force and status == "ok":
        return False, f"universe ok ({len(meta)} names)"
    built, note = universe_builder.build()
    if not built:
        # A failed rebuild must NOT shrink the scan. `build()` already refuses to return a
        # short list; this keeps whatever was on disk rather than replacing it with less.
        return False, f"universe rebuild failed, keeping the existing list — {note}"
    universe_builder.save(built, note)
    return True, f"universe rebuilt: {note}"


def refresh_calendar(force=False):
    """Try the FRED path. Returns (changed, note).

    The BLS pages cannot be reached from a script, so this only succeeds with a `FRED_API_KEY`.
    Without one the note says exactly that, and `status()` below surfaces it on the page rather
    than letting the calendar age out in silence.
    """
    try:
        import macro_calendar
    except Exception as e:                                    # noqa: BLE001
        return False, f"macro_calendar unimportable: {type(e).__name__}: {e}"
    _payload, st = macro_calendar.load()
    if not force and st == "ok":
        return False, "macro calendar ok"
    got, note = macro_calendar.refresh()
    return bool(got), note


def asset_ages():
    """Age in days of each self-refreshing asset: {name: (days|None, status, detail)}."""
    out = {}
    try:
        import universe_builder
        meta, st = universe_builder.load()
        d = None
        try:
            import json
            with open(universe_builder._path(), encoding="utf-8") as fh:
                d = (_today() - datetime.strptime(
                    json.load(fh)["built_on"][:10], "%Y-%m-%d").date()).days
        except Exception:                                     # noqa: BLE001
            pass
        out["universe"] = (d, st, f"{len(meta) if meta else 0} names")
    except Exception as e:                                    # noqa: BLE001
        out["universe"] = (None, "unreadable", f"{type(e).__name__}")

    try:
        import macro_calendar
        p, st = macro_calendar.load()
        d = None
        try:
            d = (_today() - datetime.strptime(
                p.get("verified_on", "")[:10], "%Y-%m-%d").date()).days
        except ValueError:
            pass
        n = len(macro_calendar.upcoming(within_days=60, min_importance="medium"))
        out["macro_calendar"] = (d, st, f"{n} dated event(s) in the next 60 days")
    except Exception as e:                                    # noqa: BLE001
        out["macro_calendar"] = (None, "unreadable", f"{type(e).__name__}")

    try:
        import flow_tape
        s = flow_tape.snapshot_summary()
        out["flow_tape"] = (None, "ok" if s["rows"] else "empty",
                            f"{s['sessions']}/{s['min_days']} sessions, {s['rows']} rows")
    except Exception as e:                                    # noqa: BLE001
        out["flow_tape"] = (None, "unreadable", f"{type(e).__name__}")
    return out


def status():
    """A dict for the freshness panel. Never raises."""
    rows, worst = [], None
    for name, (days, st, detail) in asset_ages().items():
        limit = WARN_AFTER.get(name)
        sev = "info"
        if st in ("unreadable", "absent"):
            sev = "stop"
        elif st == "stale" or (limit and days is not None and days > limit):
            sev = "watch"
        if sev == "stop":
            worst = "stop"
        elif sev == "watch" and worst != "stop":
            worst = "watch"
        rows.append({"name": name, "days": days, "state": st,
                     "detail": detail, "severity": sev,
                     "limit": limit})
    return {"rows": rows, "severity": worst or "info"}


def run(force=False):
    """One maintenance pass. Called from the refresh cycle; safe to call every 5 minutes."""
    notes = []
    for fn in (refresh_universe, refresh_calendar):
        try:
            changed, note = fn(force=force)
        except Exception as e:                                # noqa: BLE001
            changed, note = False, f"{fn.__name__} raised {type(e).__name__}: {e}"
        notes.append(("CHANGED " if changed else "") + note)
    return notes


if __name__ == "__main__":
    for n in run(force="--force" in sys.argv):
        print(" ", n)
    print()
    for r in status()["rows"]:
        age = f"{r['days']}d" if r["days"] is not None else "—"
        print(f"  {r['name']:16} {r['state']:10} {age:>5}  {r['detail']}")
