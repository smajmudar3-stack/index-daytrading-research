"""desk_notes.py — the macro overlay, built from the Crown Macro Letter desk notes.

WHY THIS EXISTS. `swing_signals.py` had exactly one non-price input to its direction
call: `macro_tilt`, worth +/-5 conviction points off a measured 10y sector beta.
Everything else -- the moving-average stack, RSI, 20/60/120-day momentum -- is a
transform of the same price series. So when the Unusual Whales votes were missing or
thin, the whole call collapsed onto technicals, which is precisely the complaint.

The desk notes are the missing orthogonal input. They are not price. They carry the
level of the 10y, where Brent is, what the Fed reaction function looks like this week,
which earnings actually converted AI capex into revenue, and what the author is doing
with his own book. None of that is derivable from a chart.

WHAT THIS MODULE IS NOT. It is not a signal. Nothing here has been backtested and this
file makes no claim that it has -- see `02_findings/WHAT_WORKS.md` for what has. It is a
CONDITIONING layer: it decides which trades are allowed to be proposed at all, and it
attaches a stated reason to each one. A pick that cannot name the macro theme it is
expressing does not get made.

THE OVERLAY IS A FILE, NOT A FEED. `data/desk_notes.json` is written two ways:

    1. In a Claude Code session with the Gmail connector, by reading the notes and
       writing the overlay directly. That is how the current one was built.
    2. `python3 desk_notes.py --ingest <file|->` pipes a raw note through Fable, which
       returns the same structure, and merges it in.

Both paths write the same schema and stamp `notes_ingested`, so you can always see
which notes a given read was built from, and how old the newest one is.

FAILS CLOSED. An overlay older than `MAX_AGE_MIN` is refused, not shown faded. A macro
read from last week applied to this week's tape is worse than no macro read, because it
looks exactly like information. `weekly_swing` stands down rather than guess.
"""
import json
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from idt import snapshots

ET = ZoneInfo("America/New_York")
FILE = "desk_notes.json"

# Desk notes land most weekday mornings and again after the close. Two full sessions
# without one means the macro read is no longer describing this tape.
MAX_AGE_MIN = 2880

MODEL = "claude-fable-5"
FALLBACK = "claude-opus-4-8"

# ---------------------------------------------------------------- the schema ---
# Every theme is a STANCE plus the names it argues for and against, plus the reason.
# `weekly_swing` reads nothing else: if a theme cannot name what it favours and why,
# it cannot move a trade.
REQUIRED_THEME_KEYS = ("key", "label", "stance", "why")

STANCES = ("favour", "avoid", "dispersion", "watch")


def _now_et():
    return datetime.now(ET)


# ------------------------------------------------------------------- reading ---

def overlay():
    """(payload, status). Status is snapshots' vocabulary, so a panel can `explain` it."""
    return snapshots.read(FILE)


def age_min(payload):
    """How old the NEWEST ingested note is, in minutes. None when unknowable.

    Deliberately measured from the note's own date, not the file's mtime. Rewriting
    the file does not make a Monday note describe Thursday.
    """
    if not payload:
        return None
    stamps = []
    for n in payload.get("notes_ingested") or []:
        ts = _parse_stamp(n.get("date"))
        if ts is not None:
            stamps.append(ts)
    if not stamps:
        ts = _parse_stamp(payload.get("as_of"))
        if ts is None:
            return None
        stamps = [ts]
    newest = max(stamps)
    return (datetime.now(timezone.utc).timestamp() - newest) / 60


def _parse_stamp(s):
    """Epoch seconds from the stamps this repo actually writes. None if unparseable."""
    if not s:
        return None
    s = str(s).strip().replace(" ET", "")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=ET).timestamp()
        except ValueError:
            continue
    return None


def themes(payload, stance=None):
    """The overlay's themes, optionally filtered to one stance. Never raises."""
    out = []
    for t in (payload or {}).get("themes") or []:
        if not isinstance(t, dict):
            continue
        if any(k not in t for k in REQUIRED_THEME_KEYS):
            continue
        if t.get("stance") not in STANCES:
            continue
        if stance and t["stance"] != stance:
            continue
        out.append(t)
    return out


def theme_for(payload, ticker):
    """Every theme that names this ticker, and on which side.

    Returns [(theme, +1|-1)], where +1 means the theme argues FOR upside in the name
    and -1 against. A name appearing on both sides of two themes is not an error --
    that is a genuine conflict, and `weekly_swing` stands the name down for it.
    """
    tk = (ticker or "").upper()
    hits = []
    for t in themes(payload):
        if tk in [x.upper() for x in (t.get("favours") or [])]:
            hits.append((t, +1))
        if tk in [x.upper() for x in (t.get("against") or [])]:
            hits.append((t, -1))
    return hits


def catalysts(payload, within_days=None):
    """Dated catalysts, soonest first. `within_days` filters to the near window."""
    today = _now_et().date()
    out = []
    for c in (payload or {}).get("catalysts") or []:
        if not isinstance(c, dict) or not c.get("date"):
            continue
        try:
            d = datetime.strptime(str(c["date"])[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (d - today).days
        if days < 0:
            continue
        if within_days is not None and days > within_days:
            continue
        out.append({**c, "days_away": days, "date_obj": d})
    out.sort(key=lambda c: c["days_away"])
    return out


def driver(payload, name):
    """One named macro driver (`us10y`, `brent`, ...) or None."""
    for d in (payload or {}).get("drivers") or []:
        if isinstance(d, dict) and d.get("key") == name:
            return d
    return None


# ------------------------------------------------------------------- writing ---

def write(payload):
    """Stamp and write the overlay. Adds `as_of` if the caller did not."""
    payload = dict(payload)
    payload.setdefault("as_of", _now_et().strftime("%Y-%m-%d %H:%M ET"))
    payload.setdefault("ok", True)
    return snapshots.write(FILE, payload)


def merge_note(payload, parsed, subject, date):
    """Fold one parsed note into the overlay.

    Themes merge BY KEY -- a new note updates the stance and reasoning of a theme it
    revisits rather than appending a second copy of it. Catalysts dedupe on
    (date, label). Notes already ingested are not ingested twice.
    """
    out = dict(payload or {})
    out.setdefault("themes", [])
    out.setdefault("catalysts", [])
    out.setdefault("drivers", [])
    out.setdefault("desk_book", [])
    out.setdefault("notes_ingested", [])

    if any(n.get("subject") == subject and n.get("date") == date
           for n in out["notes_ingested"]):
        return out, False

    by_key = {t.get("key"): i for i, t in enumerate(out["themes"]) if isinstance(t, dict)}
    for t in parsed.get("themes") or []:
        if not isinstance(t, dict) or "key" not in t:
            continue
        if t["key"] in by_key:
            out["themes"][by_key[t["key"]]].update(t)
        else:
            out["themes"].append(t)

    by_dkey = {d.get("key"): i for i, d in enumerate(out["drivers"]) if isinstance(d, dict)}
    for d in parsed.get("drivers") or []:
        if not isinstance(d, dict) or "key" not in d:
            continue
        if d["key"] in by_dkey:
            out["drivers"][by_dkey[d["key"]]].update(d)
        else:
            out["drivers"].append(d)

    seen = {(c.get("date"), c.get("label")) for c in out["catalysts"] if isinstance(c, dict)}
    for c in parsed.get("catalysts") or []:
        if isinstance(c, dict) and (c.get("date"), c.get("label")) not in seen:
            out["catalysts"].append(c)

    if parsed.get("desk_book"):
        out["desk_book"] = parsed["desk_book"]
    if parsed.get("regime_line"):
        out["regime_line"] = parsed["regime_line"]

    out["notes_ingested"].insert(0, {"date": date, "subject": subject})
    out["notes_ingested"] = out["notes_ingested"][:30]
    out["as_of"] = _now_et().strftime("%Y-%m-%d %H:%M ET")

    # Drop catalysts that have already happened. A stale calendar is how a weekly
    # trade ends up sized for an event that passed on Tuesday.
    today = _now_et().date()
    keep = []
    for c in out["catalysts"]:
        try:
            if datetime.strptime(str(c.get("date"))[:10], "%Y-%m-%d").date() >= today:
                keep.append(c)
        except (ValueError, TypeError):
            continue
    out["catalysts"] = keep
    return out, True


# --------------------------------------------------------------- Fable parse ---

PARSE_SYSTEM = """You convert one macro desk note into a strict JSON object. You are \
feeding a trading dashboard, so precision matters more than completeness: omit a field \
rather than infer one.

Return ONLY JSON, no prose, with this shape:

{
  "regime_line": "one sentence: what is actually driving equity prices right now",
  "drivers": [{"key":"us10y","label":"US 10y","level":"4.80%","direction":"rising",
               "note":"why it matters this week"}],
  "themes": [{"key":"duration_pressure","label":"Long-duration multiple compression",
              "stance":"avoid","favours":["XLE"],"against":["XLRE","XHB"],
              "why":"one sentence, citing the note's own reasoning"}],
  "catalysts": [{"date":"2026-09-04","label":"August payrolls",
                 "what_it_moves":"front-end rates, then equity multiples"}],
  "desk_book": [{"asset":"GLD","action":"reduced 0.25 unit","note":"ran into catalysts"}]
}

Rules:
- "stance" is exactly one of: favour, avoid, dispersion, watch.
- "favours"/"against" hold TICKERS only (equities, ETFs). Never a sector word. Omit the
  key entirely if the note names none. Do not invent tickers the note does not imply.
- "key" is a stable snake_case slug so the same theme merges across notes.
- Dates are YYYY-MM-DD. Only include a catalyst the note actually dates or clearly
  places in a named week.
- Levels are quoted verbatim from the note ("4.80%", "$95"). Never round or update them.
- If the note is a single-position update with no macro content, return the desk_book
  entry and empty lists for everything else."""


def parse_with_fable(text, api_key=None):
    """Structure one raw note. Returns (parsed_dict, error_string)."""
    try:
        import ai_desk
    except ImportError:
        ai_desk = None
    key = api_key or (ai_desk.anthropic_key() if ai_desk else None)
    if not key:
        return None, ("No ANTHROPIC_API_KEY. Paste the note into a Claude Code session "
                      "with the Gmail connector instead, or set the key in .env.")
    try:
        from anthropic import Anthropic
    except ImportError:
        return None, "the anthropic package is not installed (pip install -r requirements.txt)"

    body = _strip_boilerplate(text)
    try:
        client = Anthropic(api_key=key)
        r = client.messages.create(
            model=MODEL, max_tokens=3000, system=PARSE_SYSTEM,
            messages=[{"role": "user", "content": body}])
        raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    except Exception as e:                                    # noqa: BLE001
        if ai_desk:
            ai_desk.note_llm_failure("desk_notes", e)
        return None, f"{type(e).__name__}: {str(e)[:160]}"

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        raw = raw[4:] if raw.startswith("json") else raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Fable did not return JSON: {e}"
    if not isinstance(parsed, dict):
        return None, "Fable returned JSON that is not an object"
    if ai_desk:
        ai_desk.note_llm_success("desk_notes")
    return parsed, None


# The disclaimer block is ~60% of every note by length and none of it is information.
# Left in, it is the bulk of what the model reads.
_CUTS = ("Nicholas Crown is Founder", "*Disclaimer:", "Disclaimer:",
         "*Performance Disclosure:", "Update your email preferences")


def _strip_boilerplate(text):
    body = text
    for c in _CUTS:
        i = body.find(c)
        if i > 200:                      # never cut so early that the note vanishes
            body = body[:i]
    return body.strip()[:20000]


# ----------------------------------------------------------------------- CLI ---

def _cli(argv):
    if "--show" in argv or not argv:
        payload, status = overlay()
        if status != "ok":
            why, fix = snapshots.explain(FILE, status)
            print(f"overlay {status}: {why}\n  fix: {fix}")
            return 1
        a = age_min(payload)
        print(f"as_of {payload.get('as_of')}  newest note {a/60:.1f}h old"
              if a else f"as_of {payload.get('as_of')}")
        print(f"\n{payload.get('regime_line')}\n")
        for d in payload.get("drivers") or []:
            print(f"  {d.get('label','?'):22} {str(d.get('level','')):10} {d.get('direction','')}")
        print()
        for t in themes(payload):
            fav = ", ".join(t.get("favours") or []) or "—"
            ag = ", ".join(t.get("against") or []) or "—"
            print(f"  [{t['stance']:10}] {t['label']}\n      for: {fav}\n      against: {ag}")
        print()
        for c in catalysts(payload, within_days=14):
            print(f"  {c['date']}  (+{c['days_away']}d)  {c.get('label')}")
        return 0

    if "--merge-json" in argv:
        # The path a scheduled Claude Code session uses. That session has already read the
        # note through the Gmail connector, so it structures it itself and merges the
        # result -- no second model call to re-read text the session is already holding.
        i = argv.index("--merge-json")
        src = argv[i + 1] if len(argv) > i + 1 else "-"
        parsed = json.loads(sys.stdin.read() if src == "-"
                            else open(src, encoding="utf-8").read())
        subject = _flag(argv, "--subject") or parsed.pop("_subject", "note")
        date = _flag(argv, "--date") or parsed.pop("_date", _now_et().strftime("%Y-%m-%d %H:%M"))
        payload, _ = overlay()
        merged, added = merge_note(payload or {}, parsed, subject, date)
        if not added:
            print(f"already ingested: {subject} ({date})")
            return 0
        write(merged)
        print(f"merged {subject!r} ({date}) — {len(merged.get('themes') or [])} themes, "
              f"{len(merged.get('catalysts') or [])} catalysts, "
              f"{len(merged.get('notes_ingested') or [])} notes in the read")
        return 0

    if "--last-ingested" in argv:
        # What the scheduler asks before it searches: everything after this date is new.
        payload, _ = overlay()
        notes = (payload or {}).get("notes_ingested") or []
        print(notes[0]["date"] if notes else "")
        return 0

    if "--ingest" in argv:
        i = argv.index("--ingest")
        src = argv[i + 1] if len(argv) > i + 1 else "-"
        text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
        subject = _flag(argv, "--subject") or "pasted note"
        date = _flag(argv, "--date") or _now_et().strftime("%Y-%m-%d %H:%M")
        parsed, err = parse_with_fable(text)
        if err:
            print(f"ingest failed: {err}", file=sys.stderr)
            return 1
        payload, _ = overlay()
        merged, added = merge_note(payload or {}, parsed, subject, date)
        if not added:
            print(f"already ingested: {subject} ({date})")
            return 0
        write(merged)
        print(f"ingested {subject!r} ({date}) — "
              f"{len(merged.get('themes') or [])} themes, "
              f"{len(merged.get('catalysts') or [])} catalysts")
        return 0

    print(__doc__)
    return 0


def _flag(argv, name):
    return argv[argv.index(name) + 1] if name in argv and len(argv) > argv.index(name) + 1 else None


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
