"""risk_gates.py — the HARD pre-trade risk layer that sits in front of the agent's decisions.

Adapted from the production patterns in RESEARCH_BOTS.md (MEICAgent's 8-gate entry stack, schwagent's
two-layer live gate, milgar's shadow-filter). The principle: the LLM proposes, the gates dispose. Every
gate is a plain deterministic rule — no model call — so a bad LLM turn can never bypass risk control.

Any gate can run in SHADOW mode: it logs what it WOULD have blocked without actually blocking, so a new
gate can be validated against real decisions before it's allowed to veto them.

Honesty note baked into the design: dealer gamma is used here ONLY as a risk/vol-regime gate (which
structures are allowed), never as a directional alpha source — the gex-forward-returns study finds GEX
does not predict forward returns once you condition on VIX/realized vol.

FAIL CLOSED (2026-08-24). Every gate in this file used to answer "allow" when it could not answer at
all: a missing events.json, an unimportable `rules`, an unreadable trade book and a raising gate all
resolved to "no reason to block". That is not a gate, it is a formality that reports as a gate. An
unevaluated gate has not cleared anything, so unknown now blocks and says which unknown it was.
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from idt import db, paths

ET = ZoneInfo("America/New_York")
# Written files go through paths.state(), which creates the directory. A fresh clone has no data/
# dir at all, and "unable to open database file" used to surface three frames deep as a blank page.
DB = paths.state("agent_trades.db")
GATE_LOG = paths.state("gate_log.jsonl")
# Read-only, so this deliberately does NOT create anything: an absent calendar must stay absent and
# be reported, not be quietly conjured as an empty one.
EVENTS = os.path.join(paths.STATE_ROOT, "events.json")

# ── master switches ────────────────────────────────────────────────────────────
# Two-layer live gate (schwagent pattern): the agent paper-trades unless BOTH are flipped.
DRY_RUN = True                 # master switch — no real orders, ever, while True
LIVE_AGENT = False             # per-strategy switch

# Gates that are ENFORCED. Anything listed in SHADOW is logged-only (observe before enforcing).
ENFORCED = {"universe", "time_window", "validated_window", "event_blackout", "regime_gate",
            "daily_caps", "daily_loss_stop", "conviction"}
SHADOW = set()

# Directional 0DTE (long calls/puts and debit spreads).
# Out-of-sample testing put this at -10% to -11% per trade over 853 trades on the best directional
# signal available here. It is enabled at the account owner's explicit direction: the distribution has
# a long right tail, and the owner reports large realised runs from trading it.
# It is NOT blocked, but it IS tracked separately from the condor so the live record can settle the
# question with this account's own fills rather than with a backtest.
ALLOW_DIRECTIONAL_0DTE = True
DIRECTIONAL_MAX_RISK_PCT = 6.0     # half the sleeve cap — the tail cuts both ways
DIRECTIONAL_MAX_PER_DAY = 2

# ── tunables ───────────────────────────────────────────────────────────────────
ENTRY_OPEN_ET = (10, 0)        # no new entries before 10:00 ET (let the open settle)
ENTRY_LAST_0DTE = (14, 30)     # no new 0DTE entries after 14:30 ET (gamma/theta cliff)
ENTRY_LAST_SWING = (15, 30)
FORCE_CLOSE_0DTE = (15, 45)    # settlement-aware: flatten physically-settled 0DTE before the bell
MAX_ENTRIES_PER_DAY = 4        # account-wide, shared across symbols
CASH_SETTLED = {"SPX", "XSP", "NDX", "RUT"}   # may be left to expire; no assignment risk

# Fallbacks for growth_plan's caps, used only when that module will not import. They are the SAME
# numbers growth_plan ships, so the fallback can never loosen a cap — but they can drift, which is
# why using one is a logged warning rather than a silent substitution.
_FALLBACK_DAILY_LOSS_PCT = 25.0
_FALLBACK_MAX_OPEN = 3


class GateUnavailable(RuntimeError):
    """A gate could not be evaluated. check_entry turns this into a BLOCK, never a pass."""


class BookUnavailable(RuntimeError):
    """The trade book exists but could not be read.

    Distinct from an EMPTY book on purpose. Empty means no trades were taken and zero is the true
    answer; unavailable means we do not know the answer, and capping against a number we do not
    know is how a daily cap silently stops existing."""


def _warn(msg):
    """One loud line on stderr. No logging config: this module has to keep working on a clone with
    nothing set up, and a logger that needs a config file is one more thing that fails quietly."""
    print(f"[risk_gates] WARNING: {msg}", file=sys.stderr)


def _now():
    return datetime.now(ET)


def _hm(t):
    return t[0] * 60 + t[1]


def _mins(dt):
    return dt.hour * 60 + dt.minute


# ── event calendar ─────────────────────────────────────────────────────────────
def _nth_weekday(year, month, weekday, n):
    """nth <weekday> of a month (weekday: Mon=0 … Fri=4)."""
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _computable_events(d):
    """Events whose dates are DERIVABLE from the calendar — no hardcoded guesses."""
    out = []
    if d.month in (3, 6, 9, 12) and d == _nth_weekday(d.year, d.month, 4, 3):
        out.append("triple-witching")
    elif d == _nth_weekday(d.year, d.month, 4, 3):
        out.append("monthly-opex")
    if d == _nth_weekday(d.year, d.month, 4, 1):
        out.append("NFP")            # jobs report: first Friday
    return out


# FOMC and CPI dates cannot be derived from a calendar, so they are hand-entered in data/events.json
# (ENGINE.md). That makes this the most neglectable input in the system: nothing writes it, nothing
# refreshes it, and until 2026-08-24 ANY failure to read it returned [] — which event_blackout read
# as "no events today" and passed. The gate is listed in ENFORCED, so the dashboard reported it as
# enforced every single day while it was structurally incapable of blocking anything.
#
# A hand-maintained calendar is worth exactly as much as its last edit, so absence, unreadability and
# staleness are all HARD FAILS of the gate now. Blocking a trade because nobody updated a JSON file
# costs one missed entry. Trading into an FOMC print because nobody updated a JSON file costs the
# account. The asymmetry is not close.
#
# Stale means either of two things and both are checked:
#   1. The newest blackout date in the file has already passed. A forward-looking calendar with no
#      forward dates left has nothing to say about today, whatever its mtime claims.
#   2. Nobody has touched the file in EVENT_CALENDAR_MAX_AGE_DAYS. CPI prints monthly and the FOMC
#      meets roughly every six weeks, so 45 days without an edit has certainly missed a CPI and
#      probably an FOMC. The mtime is the only "a human looked at this" timestamp that exists, which
#      is also the remedy: confirm the dates are still right and `touch data/events.json`. One
#      second of work turns six weeks of neglect into an explicit human confirmation.
EVENT_CALENDAR_MAX_AGE_DAYS = 45
# Soft, non-blocking: warn while there is still time to top the calendar up rather than at the
# moment it runs dry and starts refusing trades.
EVENT_CALENDAR_LOW_LOOKAHEAD_DAYS = 14

_CALENDAR_FIX = (f"add the upcoming FOMC/CPI dates to {EVENTS} as "
                 '{"blackout": ["YYYY-MM-DD", ...], "labels": {"YYYY-MM-DD": "CPI"}} '
                 "then save it, or if the dates are already right just touch the file to confirm "
                 "you checked")


def _parse_iso(s):
    try:
        return date.fromisoformat(str(s).strip())
    except (TypeError, ValueError):
        return None


def _blank_calendar(state, reason, path=EVENTS, age_days=None):
    age_days = None if age_days is None else round(age_days, 2)
    return {"ok": False, "state": state, "reason": reason, "fix": _CALENDAR_FIX, "path": path,
            "exists": state != "missing", "age_days": age_days,
            "age_hours": None if age_days is None else round(age_days * 24, 1),
            "count": 0, "newest": None, "days_until_newest": None, "warning": None,
            "blackout": [], "labels": {}}


def event_calendar_status(today=None):
    """Everything a caller needs to decide whether data/events.json can be trusted.

    Always returns the same keys and never raises, so a panel can render it directly:

      ok                 True only if the file is present, parseable and current
      state              ok | missing | unreadable | malformed | empty | exhausted | stale
      reason             one plain-English line, safe to show a human
      fix                what to do about it
      path / exists      the file it looked at, and whether it was there
      age_days/age_hours how long since anyone touched it
      count / newest     how many blackout dates it holds and the furthest ahead
      days_until_newest  negative once that date has passed
      warning            non-blocking note (calendar running low), or None
      blackout / labels  the parsed dates, empty unless ok
    """
    today = today or _now().date()
    if not os.path.exists(EVENTS):
        return _blank_calendar("missing",
                               "no event calendar at all, so FOMC and CPI dates are unknown")
    try:
        age_days = (datetime.now().timestamp() - os.path.getmtime(EVENTS)) / 86400.0
    except OSError as e:
        return _blank_calendar("unreadable", f"event calendar cannot be stat'ed: {type(e).__name__}: {e}")
    try:
        with open(EVENTS, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except OSError as e:
        return _blank_calendar("unreadable",
                               f"event calendar cannot be read: {type(e).__name__}: {e}",
                               age_days=age_days)
    except ValueError as e:
        return _blank_calendar("malformed", f"event calendar is not valid JSON: {e}", age_days=age_days)
    if not isinstance(cfg, dict):
        return _blank_calendar("malformed",
                               f"event calendar is a {type(cfg).__name__}, expected an object with "
                               '"blackout" and "labels"', age_days=age_days)

    raw = cfg.get("blackout")
    if raw is None:
        raw = []
    if not isinstance(raw, (list, tuple)):
        return _blank_calendar("malformed",
                               f'event calendar "blackout" is a {type(raw).__name__}, expected a list '
                               "of YYYY-MM-DD dates", age_days=age_days)
    parsed, bad = [], []
    for item in raw:
        d = _parse_iso(item)
        (parsed.append(d) if d else bad.append(str(item)))
    if bad:
        # A date the parser cannot read is a date that would never block. Refusing the whole file is
        # the honest response: "some of your blackout dates are silently inert" is worse than "your
        # calendar is broken, here is which line".
        return _blank_calendar("malformed",
                               f"event calendar has {len(bad)} unparseable date(s): "
                               f"{', '.join(bad[:3])}", age_days=age_days)

    labels_raw = cfg.get("labels") or {}
    labels = labels_raw if isinstance(labels_raw, dict) else {}
    if not isinstance(labels_raw, dict):
        _warn(f'events.json "labels" is a {type(labels_raw).__name__}, expected an object; '
              "blackout dates will show as 'scheduled-event'")

    base = {"fix": _CALENDAR_FIX, "path": EVENTS, "exists": True,
            "age_days": round(age_days, 2), "age_hours": round(age_days * 24, 1),
            "count": len(parsed),
            "blackout": [d.isoformat() for d in parsed], "labels": labels}
    if not parsed:
        return {**base, "ok": False, "state": "empty", "newest": None, "days_until_newest": None,
                "warning": None,
                "reason": "event calendar is present but lists no blackout dates, so no FOMC or CPI "
                          "date can ever match"}

    newest = max(parsed)
    ahead = (newest - today).days
    base = {**base, "newest": newest.isoformat(), "days_until_newest": ahead}
    if ahead < 0:
        return {**base, "ok": False, "state": "exhausted", "warning": None,
                "reason": f"event calendar has run out: its newest date {newest.isoformat()} is "
                          f"{-ahead} day(s) in the past, so it cannot be describing today"}
    if age_days > EVENT_CALENDAR_MAX_AGE_DAYS:
        return {**base, "ok": False, "state": "stale", "warning": None,
                "reason": f"nobody has touched the event calendar in {age_days:.0f} days "
                          f"(limit {EVENT_CALENDAR_MAX_AGE_DAYS}), which spans at least one CPI "
                          "print, so its dates cannot be assumed complete"}

    warning = None
    if ahead < EVENT_CALENDAR_LOW_LOOKAHEAD_DAYS:
        warning = (f"event calendar runs out in {ahead} day(s) on {newest.isoformat()}, top it up "
                   "before it starts refusing trades")
    return {**base, "ok": True, "state": "ok", "warning": warning,
            "reason": f"{len(parsed)} blackout date(s), newest {newest.isoformat()} "
                      f"({ahead} day(s) ahead), checked {age_days:.0f} day(s) ago"}


def _custom_events(d):
    """Dates that are NOT derivable (FOMC, CPI) come from data/events.json — never invented here.
    Format: {"blackout": ["2026-08-12", ...], "labels": {"2026-08-12": "CPI"}}

    Returns only events that are really listed for `d`. A broken calendar returns nothing here and
    is blocked by the gate instead: inventing a fake catalyst name would put a lie in the UI and in
    gate_log.jsonl, which is a different bug from the one being fixed, not a fix for it."""
    cal = event_calendar_status(today=d)
    if not cal["ok"]:
        return []
    iso = d.isoformat()
    if iso in cal["blackout"]:
        return [cal["labels"].get(iso, "scheduled-event")]
    return []


def events_today(d=None):
    """Events actually scheduled for today. An empty list means "none listed", which is NOT the same
    as "the calendar works" — ask event_calendar_status() for that."""
    d = d or _now().date()
    return _computable_events(d) + _custom_events(d)


# ── daily state ────────────────────────────────────────────────────────────────
def _con():
    """WAL, synchronous=NORMAL and a 15s busy timeout, via idt.db.

    scan_all writes this same file while the dashboard reads it, and every connect site used to take
    sqlite's default 5-second lock. That surfaced as `database is locked` inside a render."""
    c = db.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _today_iso():
    return _now().date().isoformat()


def _no_such_table(exc):
    """A book that has never been written has no `trades` table. That is genuinely zero trades, not
    an unreadable book, and it is the normal state of a fresh clone."""
    return isinstance(exc, sqlite3.OperationalError) and "no such table" in str(exc).lower()


def _query(sql, args, on_missing):
    """Run a read against the trade book. Returns rows, `on_missing` if the book was never created,
    and raises BookUnavailable for anything else — locked, corrupt, permissions.

    Every one of these readers used to end in `except Exception: return 0`, so a locked or corrupt
    book read as "nothing traded today" and the daily caps, the loss stop and the directional cap
    all quietly stopped existing at the same moment."""
    c = None
    try:
        c = _con()
        return c.execute(sql, args).fetchall()
    except (sqlite3.Error, OSError) as e:
        # OSError is here because opening the book creates its directory first: a read-only or
        # missing parent fails before sqlite is ever reached, and that is still an unreadable book.
        if _no_such_table(e):
            return on_missing
        raise BookUnavailable(f"{DB}: {type(e).__name__}: {e}") from e
    finally:
        if c is not None:
            c.close()


def entries_today():
    """Entries taken today, account-wide. Raises BookUnavailable if the book cannot be read."""
    rows = _query("SELECT COUNT(*) n FROM trades WHERE action='ENTER' AND ts LIKE ?",
                  (_today_iso() + "%",), on_missing=None)
    return 0 if rows is None else int(rows[0]["n"])


DIRECTIONAL_STRUCTS = ("LONG_CALL", "LONG_PUT", "CALL_DEBIT_SPREAD", "PUT_DEBIT_SPREAD")


def directional_today():
    """Count of directional 0DTE entries taken today (its own cap, separate from the condor)."""
    q = ",".join("?" * len(DIRECTIONAL_STRUCTS))
    rows = _query(f"""SELECT COUNT(*) n FROM trades WHERE action='ENTER' AND ts LIKE ?
                      AND expiry='0DTE' AND structure IN ({q})""",
                  (_today_iso() + "%", *DIRECTIONAL_STRUCTS), on_missing=None)
    return 0 if rows is None else int(rows[0]["n"])


def realized_today_pct():
    """Sum of realized underlying-move P&L on trades CLOSED today. Negative = down on the day.
    This is a proxy (we track underlying move, not option premium) — it is deliberately conservative
    for a loss stop, which is the direction you want to be wrong in."""
    rows = _query("SELECT pnl_pct FROM trades WHERE status='closed' AND exit_ts LIKE ?",
                  (_today_iso() + "%",), on_missing=[])
    return round(sum((r["pnl_pct"] or 0) for r in rows), 2)


def book_status():
    """Can the trade book be read at all? For a panel that wants to say "unknown" out loud instead
    of rendering a confident 0."""
    try:
        return {"ok": True, "entries_today": entries_today(),
                "realized_today_pct": realized_today_pct(), "reason": None}
    except BookUnavailable as e:
        return {"ok": False, "entries_today": None, "realized_today_pct": None, "reason": str(e)}


def _daily_loss_limit():
    try:
        import growth_plan
        return float(growth_plan.RISK_CAP["daily_loss_stop_pct"])
    except Exception as e:
        _warn(f"growth_plan unavailable, using the built-in daily loss stop "
              f"{_FALLBACK_DAILY_LOSS_PCT:.0f}%: {type(e).__name__}: {e}")
        return _FALLBACK_DAILY_LOSS_PCT


def _max_open():
    try:
        import growth_plan
        return int(growth_plan.RISK_CAP["max_open"])
    except Exception as e:
        _warn(f"growth_plan unavailable, using the built-in max-open cap {_FALLBACK_MAX_OPEN}: "
              f"{type(e).__name__}: {e}")
        return _FALLBACK_MAX_OPEN


# ── the gate stack ─────────────────────────────────────────────────────────────
def _gate_validated_window(d, ctx):
    """The validated 0DTE condor has its own, tighter window (RULES.md §1.2): 10:30-13:00 ET. Not at the
    open (the opening drive is the least pin-like part of the day) and not late (no credit left)."""
    if (d.get("structure") or "").upper() != "IRON_CONDOR":
        return None
    if (d.get("expiry") or "").upper() != "0DTE":
        return None
    try:
        import rules
    except Exception as e:
        # Used to `return None`, which let a 0DTE condor through at 15:55 on any day the module that
        # DEFINES the window failed to import. Not knowing the window is not the same as being
        # inside it.
        raise GateUnavailable("the validated condor window is unknown because rules will not "
                              f"import: {type(e).__name__}: {e}") from e
    now = _mins(_now())
    start = rules.ENTRY_START[0] * 60 + rules.ENTRY_START[1]
    end = rules.ENTRY_END[0] * 60 + rules.ENTRY_END[1]
    if now < start:
        return f"before the validated {rules.ENTRY_START[0]}:{rules.ENTRY_START[1]:02d} ET condor window"
    if now > end:
        return (f"after the validated {rules.ENTRY_END[0]}:{rules.ENTRY_END[1]:02d} ET condor window — "
                "not enough credit left to pay for the risk")
    return None


def _gate_universe(d, ctx):
    """At this account size the 0DTE universe is SPY/QQQ only.

    The dealer-gamma board is computed on SPX/NDX and that stays the SIGNAL source — but a single SPX
    condor risks ~$2,375 and NDX far more, against a $600 per-trade cap. Expressing an index view in
    the ETF (SPY ~= SPX/10, QQQ ~= NDX/41) is the only way the trade fits, so index symbols are refused
    outright rather than being priced and then rejected on size."""
    if (d.get("expiry") or "").upper() != "0DTE":
        return None
    sym = (d.get("sym") or "").upper()
    try:
        import rules
        allowed = set(rules.UNIVERSE_0DTE)
    except Exception as e:
        # The only fallback in this file that survives the fail-closed sweep, because it is strictly
        # NARROWER than anything rules can define: it can refuse a symbol the real universe would
        # allow, never allow one the real universe would refuse. A fallback that only ever refuses
        # more is safe. It is still logged, because losing rules means something bigger is broken.
        _warn(f"rules.UNIVERSE_0DTE unavailable, falling back to SPY/QQQ: {type(e).__name__}: {e}")
        allowed = {"SPY", "QQQ"}
    if sym not in allowed:
        return (f"{sym} is not in the 0DTE universe ({'/'.join(sorted(allowed))}) — index options exceed "
                f"the per-trade cap at this account size; express the view in the ETF")
    return None


def _gate_time_window(d, ctx):
    now = _mins(_now())
    if now < _hm(ENTRY_OPEN_ET):
        return f"before {ENTRY_OPEN_ET[0]}:{ENTRY_OPEN_ET[1]:02d} ET — opening chop, no new entries"
    is_0dte = (d.get("expiry") or "").upper() == "0DTE"
    last = ENTRY_LAST_0DTE if is_0dte else ENTRY_LAST_SWING
    if now > _hm(last):
        return f"after {last[0]}:{last[1]:02d} ET — too late to open this ({'0DTE' if is_0dte else 'swing'})"
    return None


def _gate_event_blackout(d, ctx):
    """Blocks on a scheduled catalyst, and blocks just as hard when it cannot tell.

    The two reasons are worded differently on purpose. "event blackout (CPI)" means a catalyst is
    listed for today. "event calendar unusable" means nobody knows whether one is, and reading those
    two as the same sentence is what let an absent file look like a clear day."""
    cal = event_calendar_status()
    if not cal["ok"]:
        return (f"event calendar unusable, so a scheduled catalyst cannot be ruled out: "
                f"{cal['reason']}. Fix: {cal['fix']}")
    if cal["warning"]:
        _warn(cal["warning"])
    ev = events_today()
    if ev:
        return f"event blackout ({', '.join(ev)}) — no new risk into a scheduled catalyst"
    return None


def _gate_regime_gate(d, ctx):
    """Gamma regime decides which STRUCTURES are allowed, not which direction to bet.

    The authority here is the PRIOR-CLOSE GEX z-score, because that is the signal that was actually
    validated out-of-sample (RULES.md §1.1: realised/implied range 0.843x on high-gamma vs 1.139x on
    low, t=-13.2). The intraday 'live regime' string is an unvalidated label and must NOT override it —
    the two routinely disagree, and deferring to the label would block the one edge that survived testing.
    """
    struct = (d.get("structure") or "").upper()
    selling = struct in ("IRON_CONDOR", "CALL_CREDIT_SPREAD", "PUT_CREDIT_SPREAD")
    buying_0dte = (struct in ("LONG_CALL", "LONG_PUT", "CALL_DEBIT_SPREAD", "PUT_DEBIT_SPREAD")
                   and (d.get("expiry") or "").upper() == "0DTE")
    if buying_0dte:
        if not ALLOW_DIRECTIONAL_0DTE:
            return ("buying 0DTE premium is disabled (tested at -10% to -11%/trade on the best "
                    "directional signal) — sell the range or stand down")
        # Enabled, but on its own tighter leash: half the risk cap and a hard daily count, because the
        # tested expectancy is negative and the payoff is lottery-shaped.
        if directional_today() >= DIRECTIONAL_MAX_PER_DAY:
            return (f"directional 0DTE daily cap reached ({DIRECTIONAL_MAX_PER_DAY}) — this is the "
                    "sleeve with negative tested expectancy; it does not get unlimited attempts")
        return None
    if not selling:
        return None
    try:
        import rules
        z = rules.gex_z()
    except Exception as e:
        raise GateUnavailable("the prior-close GEX z-score could not be read: "
                              f"{type(e).__name__}: {e}") from e
    if z is None:
        # Unavailable is not permission. The validated rule is "z above +0.5"; a missing z-score means
        # we do not know that it holds, and selling premium without it is the untested trade. This
        # used to defer to the intraday regime LABEL and allow the trade whenever the label was not
        # explicitly negative, so a clone with no gex_snapshot.json sold condors on the strength of a
        # missing file. The label is still reported, because it is evidence; it is just not consent.
        regime = (ctx.get("regime") or "").lower()
        extra = f", live regime reads '{regime}'" if regime else ""
        return ("premium-selling blocked: no prior-close GEX z-score available, so the validated "
                f"range edge cannot be confirmed{extra}. Refresh gex_snapshot.json or stand down")
    if z <= 0.5:
        return (f"premium-selling blocked: prior-close GEX z {z:+.2f} is not above +0.5, so the validated "
                "range edge is absent — stand down")
    return None


def _gate_daily_caps(d, ctx):
    if entries_today() >= MAX_ENTRIES_PER_DAY:
        return f"daily entry cap reached ({MAX_ENTRIES_PER_DAY}) — overtrading is how the day gets away"
    if int(ctx.get("n_open") or 0) >= _max_open():
        return f"max concurrent positions ({_max_open()}) already open"
    return None


def _gate_daily_loss_stop(d, ctx):
    lim = _daily_loss_limit()
    r = realized_today_pct()
    if r <= -lim:
        return f"daily loss stop hit ({r:+.1f}% vs -{lim:.0f}% limit) — done for the day"
    return None


def _gate_conviction(d, ctx):
    conv = int(d.get("conviction") or 0)
    floor = int(ctx.get("conv_min") or 66)
    if conv < floor:
        return f"conviction {conv} below floor {floor}"
    return None


GATES = [
    ("universe", _gate_universe),
    ("time_window", _gate_time_window),
    ("validated_window", _gate_validated_window),
    ("event_blackout", _gate_event_blackout),
    ("regime_gate", _gate_regime_gate),
    ("daily_caps", _gate_daily_caps),
    ("daily_loss_stop", _gate_daily_loss_stop),
    ("conviction", _gate_conviction),
]


def check_entry(decision, ctx=None):
    """Run every gate against a proposed ENTER. Returns (allowed, blocks, shadow_blocks).

    `blocks` are enforced vetoes (entry is refused). `shadow_blocks` are gates in observe-only mode —
    recorded so we can see what they'd have stopped before trusting them with a veto."""
    ctx = ctx or {}
    blocks, shadow_blocks = [], []
    for name, fn in GATES:
        try:
            reason = fn(decision, ctx)
        except Exception as e:
            # A gate that throws now BLOCKS. The old comment here said it must "fail OPEN (never
            # silently veto)" — but the silent part was never the veto, it was the failure: the trade
            # went through and only a line in gate_log.jsonl said why. A gate that could not evaluate
            # has not cleared anything. Shadow gates still only shadow-block, since a gate being
            # observed is by definition not trusted with a veto yet.
            reason = f"gate could not be evaluated ({type(e).__name__}: {e})"
            _warn(f"gate {name} raised: {type(e).__name__}: {e}")
            _log({"ts": _now().isoformat(timespec="seconds"), "gate": name,
                  "error": f"{type(e).__name__}: {e}", "action": "blocked (fail closed)"})
        if not reason:
            continue
        if name in SHADOW or name not in ENFORCED:
            shadow_blocks.append(f"[shadow] {name}: {reason}")
        else:
            blocks.append(f"{name}: {reason}")
    allowed = not blocks
    _log({"ts": _now().isoformat(timespec="seconds"), "sym": decision.get("sym"),
          "structure": decision.get("structure"), "conviction": decision.get("conviction"),
          "allowed": allowed, "blocks": blocks, "shadow": shadow_blocks})
    return allowed, blocks, shadow_blocks


def _log(rec):
    """Append to the gate audit trail.

    Never raises into the caller: losing the log must not also lose the trade decision. But it is no
    longer silent either, because an audit trail that stops being written and says nothing is
    indistinguishable from a day with no decisions in it."""
    try:
        with open(GATE_LOG, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except (OSError, TypeError, ValueError) as e:
        _warn(f"gate log write failed ({GATE_LOG}): {type(e).__name__}: {e}")


# ── settlement-aware force close ───────────────────────────────────────────────
def force_close_reason(trade):
    """Non-None => this open trade must be flattened now, regardless of P&L.
    Cash-settled index 0DTE can be left to expire; anything physically settled must be closed."""
    exp = (trade.get("expiry") or "").upper()
    if exp != "0DTE":
        return None
    now = _mins(_now())
    if now < _hm(FORCE_CLOSE_0DTE):
        return None
    sym = (trade.get("sym") or "").upper()
    if sym in CASH_SETTLED:
        return None
    return f"0DTE time-stop {FORCE_CLOSE_0DTE[0]}:{FORCE_CLOSE_0DTE[1]:02d} ET — {sym} is physically settled, no assignment risk allowed"


def prompt_block(ctx=None):
    """A short summary of the live gate state, fed to the agent so it doesn't waste turns proposing
    trades the gates will refuse."""
    ctx = ctx or {}
    cal = event_calendar_status()
    ev = events_today() if cal["ok"] else []
    book = book_status()
    used = f"{book['entries_today']}" if book["ok"] else "UNKNOWN (trade book unreadable)"
    day_pl = f"{book['realized_today_pct']:+.1f}%" if book["ok"] else "UNKNOWN"
    parts = [
        f"RISK GATES (hard, non-negotiable — proposals violating these are auto-rejected): "
        f"entry window {ENTRY_OPEN_ET[0]}:{ENTRY_OPEN_ET[1]:02d}-{ENTRY_LAST_0DTE[0]}:{ENTRY_LAST_0DTE[1]:02d} ET "
        f"for 0DTE ({ENTRY_LAST_SWING[0]}:{ENTRY_LAST_SWING[1]:02d} swing); "
        f"max {MAX_ENTRIES_PER_DAY} entries/day (used {used}); "
        f"no premium-selling in a negative-gamma regime; "
        f"day P&L {day_pl} vs -{_daily_loss_limit():.0f}% stop.",
    ]
    if not book["ok"]:
        parts.append(f"TRADE BOOK UNREADABLE: {book['reason']} — the daily caps and the loss stop "
                     "cannot be evaluated, so every entry is refused until it is fixed.")
    if not cal["ok"]:
        parts.append(f"EVENT CALENDAR UNUSABLE: {cal['reason']}. Entries are BLOCKED until it is "
                     f"fixed. {cal['fix']}")
    elif ev:
        parts.append(f"EVENT BLACKOUT TODAY: {', '.join(ev)} — no new risk.")
    elif cal["warning"]:
        parts.append(f"EVENT CALENDAR: {cal['warning']}.")
    parts.append("Dealer gamma is a RISK-REGIME gate only — it tells you which STRUCTURE is safe, "
                 "never which DIRECTION to bet. Do not use GEX as a directional forecast.")
    return " ".join(parts)


if __name__ == "__main__":
    print("now:", _now().strftime("%Y-%m-%d %H:%M ET"))
    _cal = event_calendar_status()
    print(f"event calendar: {_cal['state']} — {_cal['reason']}")
    print("events today:", events_today() or "none")
    _book = book_status()
    if _book["ok"]:
        print("entries today:", _book["entries_today"], "| realized today:", _book["realized_today_pct"], "%")
    else:
        print("trade book UNREADABLE:", _book["reason"])
    print("DRY_RUN:", DRY_RUN, "| LIVE_AGENT:", LIVE_AGENT)
    print("\n-- gate check on a sample condor in a short-gamma regime --")
    ok, blocks, shadow = check_entry(
        {"sym": "SPX", "structure": "IRON_CONDOR", "conviction": 70, "expiry": "0DTE"},
        {"regime": "short gamma", "n_open": 0})
    print("allowed:", ok)
    for b in blocks + shadow:
        print("  ✗", b)
    print("\n" + prompt_block())
