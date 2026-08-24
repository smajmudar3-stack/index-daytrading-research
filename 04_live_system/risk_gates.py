"""risk_gates.py — the HARD pre-trade risk layer that sits in front of the agent's decisions.

Adapted from the production patterns in RESEARCH_BOTS.md (MEICAgent's 8-gate entry stack, schwagent's
two-layer live gate, milgar's shadow-filter). The principle: the LLM proposes, the gates dispose. Every
gate is a plain deterministic rule — no model call — so a bad LLM turn can never bypass risk control.

Any gate can run in SHADOW mode: it logs what it WOULD have blocked without actually blocking, so a new
gate can be validated against real decisions before it's allowed to veto them.

Honesty note baked into the design: dealer gamma is used here ONLY as a risk/vol-regime gate (which
structures are allowed), never as a directional alpha source — the gex-forward-returns study finds GEX
does not predict forward returns once you condition on VIX/realized vol.
"""
import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "agent_trades.db")
EVENTS = os.path.join(HERE, "data", "events.json")
GATE_LOG = os.path.join(HERE, "data", "gate_log.jsonl")

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


def _custom_events(d):
    """Dates that are NOT derivable (FOMC, CPI) come from data/events.json — never invented here.
    Format: {"blackout": ["2026-08-12", ...], "labels": {"2026-08-12": "CPI"}}"""
    try:
        cfg = json.load(open(EVENTS))
    except Exception:
        return []
    iso = d.isoformat()
    if iso in (cfg.get("blackout") or []):
        return [(cfg.get("labels") or {}).get(iso, "scheduled-event")]
    return []


def events_today(d=None):
    d = d or _now().date()
    return _computable_events(d) + _custom_events(d)


# ── daily state ────────────────────────────────────────────────────────────────
def _con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _today_iso():
    return _now().date().isoformat()


def entries_today():
    try:
        c = _con()
        n = c.execute("SELECT COUNT(*) n FROM trades WHERE action='ENTER' AND ts LIKE ?",
                      (_today_iso() + "%",)).fetchone()["n"]
        c.close()
        return int(n)
    except Exception:
        return 0


DIRECTIONAL_STRUCTS = ("LONG_CALL", "LONG_PUT", "CALL_DEBIT_SPREAD", "PUT_DEBIT_SPREAD")


def directional_today():
    """Count of directional 0DTE entries taken today (its own cap, separate from the condor)."""
    try:
        c = _con()
        q = ",".join("?" * len(DIRECTIONAL_STRUCTS))
        n = c.execute(f"""SELECT COUNT(*) n FROM trades WHERE action='ENTER' AND ts LIKE ?
                          AND expiry='0DTE' AND structure IN ({q})""",
                      (_today_iso() + "%", *DIRECTIONAL_STRUCTS)).fetchone()["n"]
        c.close()
        return int(n)
    except Exception:
        return 0


def realized_today_pct():
    """Sum of realized underlying-move P&L on trades CLOSED today. Negative = down on the day.
    This is a proxy (we track underlying move, not option premium) — it is deliberately conservative
    for a loss stop, which is the direction you want to be wrong in."""
    try:
        c = _con()
        rows = c.execute("SELECT pnl_pct FROM trades WHERE status='closed' AND exit_ts LIKE ?",
                         (_today_iso() + "%",)).fetchall()
        c.close()
        return round(sum((r["pnl_pct"] or 0) for r in rows), 2)
    except Exception:
        return 0.0


def _daily_loss_limit():
    try:
        import growth_plan
        return float(growth_plan.RISK_CAP["daily_loss_stop_pct"])
    except Exception:
        return 25.0


def _max_open():
    try:
        import growth_plan
        return int(growth_plan.RISK_CAP["max_open"])
    except Exception:
        return 3


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
    except Exception:
        return None
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
        allowed = rules.UNIVERSE_0DTE
    except Exception:
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
    except Exception:
        z = None
    if z is None:
        regime = (ctx.get("regime") or "").lower()
        if "short" in regime or "negative" in regime:
            return "premium-selling blocked: no GEX z available and the live regime reads negative gamma"
        return None
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
            # A gate that throws must fail OPEN (never silently veto) but must be loud in the log.
            reason = None
            _log({"ts": _now().isoformat(timespec="seconds"), "gate": name,
                  "error": f"{type(e).__name__}: {e}"})
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
    try:
        with open(GATE_LOG, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    except Exception:
        pass


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
    ev = events_today()
    parts = [
        f"RISK GATES (hard, non-negotiable — proposals violating these are auto-rejected): "
        f"entry window {ENTRY_OPEN_ET[0]}:{ENTRY_OPEN_ET[1]:02d}-{ENTRY_LAST_0DTE[0]}:{ENTRY_LAST_0DTE[1]:02d} ET "
        f"for 0DTE ({ENTRY_LAST_SWING[0]}:{ENTRY_LAST_SWING[1]:02d} swing); "
        f"max {MAX_ENTRIES_PER_DAY} entries/day (used {entries_today()}); "
        f"no premium-selling in a negative-gamma regime; "
        f"day P&L {realized_today_pct():+.1f}% vs -{_daily_loss_limit():.0f}% stop.",
    ]
    if ev:
        parts.append(f"EVENT BLACKOUT TODAY: {', '.join(ev)} — no new risk.")
    parts.append("Dealer gamma is a RISK-REGIME gate only — it tells you which STRUCTURE is safe, "
                 "never which DIRECTION to bet. Do not use GEX as a directional forecast.")
    return " ".join(parts)


if __name__ == "__main__":
    print("now:", _now().strftime("%Y-%m-%d %H:%M ET"))
    print("events today:", events_today() or "none")
    print("entries today:", entries_today(), "| realized today:", realized_today_pct(), "%")
    print("DRY_RUN:", DRY_RUN, "| LIVE_AGENT:", LIVE_AGENT)
    print("\n-- gate check on a sample condor in a short-gamma regime --")
    ok, blocks, shadow = check_entry(
        {"sym": "SPX", "structure": "IRON_CONDOR", "conviction": 70, "expiry": "0DTE"},
        {"regime": "short gamma", "n_open": 0})
    print("allowed:", ok)
    for b in blocks + shadow:
        print("  ✗", b)
    print("\n" + prompt_block())
