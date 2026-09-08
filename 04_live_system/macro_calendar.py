"""macro_calendar.py — the dated macro events, found rather than typed in.

WHY THIS EXISTS, AND THE LIVE PROBLEM IT CAUGHT. `desk_notes` only carries a catalyst when a
desk note happens to date one. The August CPI print was described in three separate notes as
the thing the September Fed decision turns on, and not one of them gave the date -- so the
overlay carried it as prose and the engine could not see it.

The consequence was concrete. CPI releases 2026-09-11 at 08:30, and on 2026-09-06 every one
of the six live cards expired 2026-09-11. The whole book was set to expire INTO the print it
was most exposed to, with no session left to recover, in direct violation of the rule this
engine already enforces for payrolls: a macro print is a hazard the position must SURVIVE, so
the expiry belongs at least `MACRO_BUFFER_DAYS` past it.

That rule had been correct and unenforceable, because nothing knew the date.

WHERE THE DATES COME FROM
=========================
Official primary sources, in order:

  CPI, PPI, jobs   BLS publishes its release schedule at bls.gov/schedule/news_release/
  FOMC             federalreserve.gov/monetarypolicy/fomccalendars.htm
  FRED (optional)  a `FRED_API_KEY` unlocks /fred/releases/dates, which returns SCHEDULED
                   future release dates for every series the Fed tracks -- the same data,
                   machine-readable, and it covers far more than the four series below.
                   Free key, issued instantly at fred.stlouisfed.org/docs/api/api_key.html.

The seed table below is transcribed from those two pages on 2026-09-06 so the engine works
with no key at all. It carries a `verified_on` date and `refresh()` re-reads the live sources;
anything past `STALE_AFTER_DAYS` without a refresh is reported as stale rather than trusted,
because a wrong catalyst DATE is worse than no catalyst -- it moves every expiry in the book.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from idt import paths                                          # noqa: E402

ET = ZoneInfo("America/New_York")
FILE = "macro_calendar.json"
STALE_AFTER_DAYS = 45

# Transcribed 2026-09-06 from bls.gov and federalreserve.gov. `moves` is what the engine needs
# to reason about: which part of the curve or tape the print actually hits.
SEED = {
    "verified_on": "2026-09-06",
    "sources": ["https://www.bls.gov/schedule/news_release/cpi.htm",
                "https://www.bls.gov/schedule/news_release/ppi.htm",
                "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"],
    "events": [
        {"date": "2026-09-11", "time": "08:30", "label": "August CPI",
         "kind": "inflation", "importance": "high",
         "moves": "front-end rates first, then every equity multiple through the 10y. The "
                  "desk calls the September Fed decision hostage to this print."},
        {"date": "2026-09-16", "time": "14:00", "label": "FOMC decision + projections",
         "kind": "fed", "importance": "high",
         "moves": "the whole curve, and a Summary of Economic Projections meeting carries a "
                  "dot plot on top of the statement."},
        {"date": "2026-10-14", "time": "08:30", "label": "September CPI",
         "kind": "inflation", "importance": "high", "moves": "front-end rates, then multiples"},
        {"date": "2026-10-15", "time": "08:30", "label": "September PPI",
         "kind": "inflation", "importance": "medium", "moves": "input costs, refiner margins"},
        {"date": "2026-10-28", "time": "14:00", "label": "FOMC decision",
         "kind": "fed", "importance": "high", "moves": "the whole curve"},
        {"date": "2026-11-10", "time": "08:30", "label": "October CPI",
         "kind": "inflation", "importance": "high", "moves": "front-end rates, then multiples"},
        {"date": "2026-11-13", "time": "08:30", "label": "October PPI",
         "kind": "inflation", "importance": "medium", "moves": "input costs"},
        {"date": "2026-12-09", "time": "14:00", "label": "FOMC decision + projections",
         "kind": "fed", "importance": "high", "moves": "the whole curve, plus a dot plot"},
        {"date": "2026-12-10", "time": "08:30", "label": "November CPI",
         "kind": "inflation", "importance": "high", "moves": "front-end rates, then multiples"},
        {"date": "2026-12-15", "time": "08:30", "label": "November PPI",
         "kind": "inflation", "importance": "medium", "moves": "input costs"},
    ],
}


def _now():
    return datetime.now(ET)


def _path():
    return os.path.join(paths.STATE_ROOT, FILE)


def load():
    """The calendar and its verdict: (payload, status). Never raises."""
    p = _path()
    if not os.path.exists(p):
        return dict(SEED), "seed"
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return dict(SEED), "seed"
    try:
        v = datetime.strptime(d.get("verified_on", "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return d, "unverified"
    age = (_now().date() - v).days
    return d, ("stale" if age > STALE_AFTER_DAYS else "ok")


def save(payload):
    payload = dict(payload)
    payload.setdefault("verified_on", _now().strftime("%Y-%m-%d"))
    os.makedirs(paths.STATE_ROOT, exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    os.replace(tmp, _path())
    return _path()


def upcoming(within_days=30, min_importance="medium", now=None):
    """Dated events between today and `within_days`, soonest first.

    Shaped exactly like a `desk_notes` catalyst so `weekly_swing` consumes both through one
    path -- the engine should not care whether a date came from a newsletter or from BLS.
    """
    d, status = load()
    today = (now or _now()).date()
    rank = {"low": 0, "medium": 1, "high": 2}
    floor = rank.get(min_importance, 1)
    out = []
    for e in d.get("events") or []:
        try:
            dt = datetime.strptime(str(e["date"])[:10], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        days = (dt - today).days
        if days < 0 or days > within_days:
            continue
        if rank.get(e.get("importance", "medium"), 1) < floor:
            continue
        out.append({
            "date": e["date"], "label": e["label"], "days_away": days,
            "what_it_moves": e.get("moves", ""), "kind": e.get("kind"),
            "importance": e.get("importance"), "time": e.get("time"),
            "source": "macro_calendar", "calendar_status": status,
            # No `tickers` key on purpose: these are TAPE-WIDE events. `_pick_weekly` treats
            # a catalyst with no tickers as a hazard to clear rather than an event to own,
            # which is the correct handling for a CPI print.
        })
    out.sort(key=lambda x: x["days_away"])
    return out


def collisions(expiry, now=None):
    """Macro prints landing on or before an expiry, with too little room after.

    The check the engine was missing on 2026-09-06, when six cards all expired on CPI day.
    """
    try:
        exp = datetime.strptime(str(expiry)[:10], "%Y-%m-%d").date()
    except ValueError:
        return []
    today = (now or _now()).date()
    hits = []
    for e in upcoming(within_days=60, now=now):
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= d <= exp:
            left = (exp - d).days
            hits.append({**e, "days_left_after": left,
                         "on_expiry_day": d == exp})
    return hits


def refresh():
    """Re-read the official schedules. Returns (payload, note).

    Deliberately NOT automatic parsing of three government HTML pages on a five-minute cycle:
    those pages change layout, and a mis-parsed CPI date silently moves every expiry in the
    book. `idt calendar --refresh` runs it, a Claude Code session can re-read the sources and
    call `save()`, and a FRED key makes the whole thing machine-readable and reliable.
    """
    key = None
    try:
        from idt import keys
        key = keys.get("FRED_API_KEY")
    except Exception:                                         # noqa: BLE001
        pass
    if not key:
        return None, ("no FRED_API_KEY. The seed calendar stands. A free key from "
                      "fred.stlouisfed.org/docs/api/api_key.html unlocks "
                      "/fred/releases/dates, which returns scheduled future release dates "
                      "for every series the Fed tracks — machine-readable, so this stops "
                      "depending on a transcription.")
    try:
        import urllib.parse
        import urllib.request
        today = _now().date()
        q = urllib.parse.urlencode({
            "api_key": key, "file_type": "json",
            "realtime_start": today.isoformat(),
            "realtime_end": (today + timedelta(days=120)).isoformat(),
            "include_release_dates_with_no_data": "true", "limit": 500,
        })
        with urllib.request.urlopen(
                f"https://api.stlouisfed.org/fred/releases/dates?{q}", timeout=20) as r:
            data = json.loads(r.read().decode())
    except Exception as e:                                    # noqa: BLE001
        return None, f"FRED call failed ({type(e).__name__}: {str(e)[:90]}); seed stands"

    WANT = {"Consumer Price Index": ("inflation", "high"),
            "Producer Price Index": ("inflation", "medium"),
            "Employment Situation": ("jobs", "high"),
            "Personal Income and Outlays": ("inflation", "high"),
            "Gross Domestic Product": ("growth", "medium")}
    events = []
    for row in data.get("release_dates") or []:
        name = row.get("release_name") or ""
        for want, (kind, imp) in WANT.items():
            if want.lower() in name.lower():
                events.append({"date": row.get("date"), "time": "08:30", "label": name,
                               "kind": kind, "importance": imp,
                               "moves": "front-end rates first, then equity multiples"})
                break
    if not events:
        return None, "FRED returned no matching releases; seed stands"
    # FOMC is not a FRED release; keep those from the seed.
    events += [e for e in SEED["events"] if e.get("kind") == "fed"]
    payload = {"verified_on": _now().strftime("%Y-%m-%d"),
               "sources": ["FRED /fred/releases/dates"] + SEED["sources"],
               "events": sorted(events, key=lambda e: e["date"])}
    save(payload)
    return payload, f"refreshed from FRED: {len(events)} dated events"


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        _p, note = refresh()
        print(note)
    d, status = load()
    print(f"calendar {status}, verified {d.get('verified_on')}\n")
    for e in upcoming(within_days=45, min_importance="medium"):
        flag = "  <-- HIGH" if e["importance"] == "high" else ""
        print(f"  {e['date']} {e.get('time','')}  (+{e['days_away']:>2}d)  "
              f"{e['label']}{flag}")
    print("\ncollision check against a 2026-09-11 expiry:")
    for c in collisions("2026-09-11"):
        where = "ON EXPIRY DAY" if c["on_expiry_day"] else f"{c['days_left_after']}d before"
        print(f"  {c['label']} on {c['date']} — {where}")
