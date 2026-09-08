"""ai_desk.py — the AI desk strategist (Fable 5, Opus fallback). Reads the WHOLE board — 0DTE regime,
SPX/NDX periscopes, your open positions, the swing regime/rotation/stress, VIX — and produces a
holistic, reasoned synthesis, including the macro/geopolitical judgment the rule-based system can't do.

Not just a narrator: it weighs whether the pieces agree or conflict, names the single thing that matters
most, the real opportunity, and the biggest risk. Honest, no hype. Writes ai_desk_snapshot.json.
Cadence-gated + cached for cost. Falls back to a rule-based synthesis if the API is unavailable.
"""
import json
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import uw_client                     # the shared service-health vocabulary lives there
from idt import keys, paths

ET = ZoneInfo("America/New_York")
OUT = os.path.join(paths.STATE_ROOT, "ai_desk_snapshot.json")
MODEL = "claude-fable-5-1"        # user's choice (most capable); server-side fallback to Opus
FALLBACK = "claude-opus-4-8"
EFFORT = "high"
MAX_TOKENS = 5000        # effort=high thinking shares this budget — too low truncates the brief
DESK_CADENCE_S = 900     # 15 minutes between PAID desk reads; see claim_spend below

SYSTEM = (
    "You are an elite cross-asset + options desk strategist briefing a sharp retail 0DTE/swing trader. "
    "You receive a live snapshot of their whole board: the SPX 0DTE dealer-gamma regime and reconciled "
    "signal, the SPX & NDX gamma periscopes (signal, conviction, gamma flip, call/put walls, real "
    "Unusual Whales flow, condor math), their OPEN option positions, and the swing book's market regime "
    "(risk-on/off), sector rotation (leaders/laggards), and a flight-to-safety stress gauge. "
    "Synthesize it into a tight, high-signal brief. Structure: (1) MACRO BACKDROP — the regime + your own "
    "read of the current macro/geopolitical environment and how it colors today's tape (use your knowledge; "
    "flag if a known catalyst — Fed, CPI, jobs, major geopolitical risk — is near). (2) THE ONE THING that "
    "matters most on the board right now. (3) BEST OPPORTUNITY and (4) BIGGEST RISK, concretely. (5) DO THE "
    "PIECES AGREE? — explicitly note where the 0DTE signal, the flow, the rotation, and their positions align "
    "or CONTRADICT (contradictions are the most important thing to surface). Be brutally honest — if it's a "
    "chop/no-edge tape, say sit out. No hype, no hedging fluff. Reference concrete levels and tickers from the "
    "data. Keep it under ~350 words, punchy, plain text with short labeled sections."
)


# ── the Anthropic key ─────────────────────────────────────────────────────────
# One loader, in idt.keys. The four copies this replaced each searched the
# original author's home directory FIRST, so on any other machine all four fell
# through silently and the failure read as "no credits" instead of "no key".
KILL_SWITCH_ENV = "IDT_NO_LLM"


def anthropic_key():
    """The key, or None. Never raises; callers decide whether absence is fatal."""
    return keys.get("ANTHROPIC_API_KEY")


def llm_disabled():
    """True when paid model calls are switched off. Read every time, not cached
    at import, so a script can turn it on for one run."""
    return os.environ.get(KILL_SWITCH_ENV, "0") != "0"


# ── which failure this is ─────────────────────────────────────────────────────
# A missing key, a rejected key and a dead service are three different problems
# with three different fixes, and all three used to render as one flat line:
# "Fable unavailable... add API credits". That sentence is wrong two times out
# of three, and it is the reason a fresh clone looks like a billing problem.
_LLM_FAILURE = {}            # {module: (state, detail, ts)} — this process only
_FAILURE_WINDOW_S = 900      # after 15 quiet minutes, stop reporting an old failure


def classify_llm_error(exc):
    """(state, one-clause reason) for an exception out of the Anthropic SDK."""
    code = getattr(exc, "status_code", None)
    name = type(exc).__name__
    text = str(exc)[:300].lower()
    if isinstance(exc, ImportError):
        return (uw_client.STATE_OUTAGE,
                "the anthropic package is not installed (pip install -r requirements.txt)")
    if code in (401, 403) or "authentication" in name.lower() or "permissiondenied" in name.lower():
        return uw_client.STATE_AUTH_FAILED, "the API key was rejected"
    if "credit balance" in text or "billing" in text or "quota" in text:
        return uw_client.STATE_AUTH_FAILED, "the key works but the account is out of credit"
    return uw_client.STATE_OUTAGE, f"{name}: {str(exc)[:100]}"


def note_llm_failure(module, exc):
    """Record a failed paid call and SAY so. Returns (state, reason)."""
    state, detail = classify_llm_error(exc)
    _LLM_FAILURE[module] = (state, detail, time.time())
    print(f"{module}: Anthropic call failed — {detail}")
    return state, detail


def note_llm_success(module):
    _LLM_FAILURE.pop(module, None)


def anthropic_status(module):
    """The uniform health row for any module whose outside service is Anthropic.
    Same five keys as uw_client.status(), so a panel can loop over both."""
    svc = (module, "anthropic")
    if llm_disabled():
        return uw_client.service_status(
            *svc, uw_client.STATE_DISABLED,
            f"Paid model calls are switched off ({KILL_SWITCH_ENV}=1). Each module falls back to its "
            "no-model path.")
    if not anthropic_key():
        return uw_client.service_status(
            *svc, uw_client.STATE_NO_KEY,
            "No ANTHROPIC_API_KEY in the environment or in the repo .env. That is a missing key, not a "
            "spent balance. Paid model calls are skipped and each module falls back to its no-model path.")
    fail = _LLM_FAILURE.get(module)
    if fail and time.time() - fail[2] < _FAILURE_WINDOW_S:
        return uw_client.service_status(*svc, fail[0], f"Last call failed: {fail[1]}.")
    return uw_client.service_status(*svc, uw_client.STATE_AVAILABLE,
                                    "Key present and no failed call in this process.")


def anthropic_reason(module):
    """A SHORT clause naming why a paid call is not happening — for an error
    field or a panel header, where the full sentence in anthropic_status()
    ['detail'] would not fit."""
    state = anthropic_status(module)["state"]
    if state == uw_client.STATE_NO_KEY:
        return "no ANTHROPIC_API_KEY set"
    if state == uw_client.STATE_DISABLED:
        return f"paid model calls are off ({KILL_SWITCH_ENV}=1)"
    fail = _LLM_FAILURE.get(module)
    return fail[1] if fail else "available"


def status():
    """This module's health, in the shared shape. See uw_client.STATES."""
    return anthropic_status("ai_desk")


# ── the cost brake ────────────────────────────────────────────────────────────
# scan_all gates the desk read on a 15-minute staleness check; the dashboard's
# /refresh handler does not gate it at all. A gate that lives only in the caller
# protects only that caller, which is how an ungated desk read "burned ~60 calls
# a night reading a board that had not changed since the close". So the brake
# lives here as well, beside the spend.
#
# It has to be on disk: scan_all runs as a NEW PROCESS every cycle, so an
# in-memory timestamp would reset each time and gate nothing. Two processes can
# race for the same slot and both win; the cost of that is one extra call, which
# is cheaper than the locking needed to prevent it.
SPEND_LOG = os.path.join(paths.STATE_ROOT, "llm_spend.json")


def _spend_log():
    try:
        with open(SPEND_LOG, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}                                  # first run, not a fault
    except (OSError, ValueError) as e:
        print(f"ai_desk: spend log unreadable ({type(e).__name__}: {e}) — every cadence gate is open")
        return {}


def claim_spend(name, min_interval_s, force=False):
    """Book the right to make ONE paid call for `name`, or refuse it.

    Returns (True, "") when the caller may spend, else (False, reason). The
    stamp is written BEFORE the call, not after: an API that fails instantly and
    is retried every cycle is exactly how the money goes, so a failed call waits
    out the interval like a successful one."""
    if llm_disabled():
        return False, f"paid model calls are off ({KILL_SWITCH_ENV}=1)"
    if force:
        return True, ""
    log = _spend_log()
    last = 0.0
    try:
        last = float(log.get(name) or 0)
    except (TypeError, ValueError):
        last = 0.0                                 # corrupt stamp: treat as never
    waited = time.time() - last
    if last and waited < min_interval_s:
        return False, (f"last paid {name} call was {int(waited)}s ago; the cadence is "
                       f"{int(min_interval_s)}s")
    log[name] = time.time()
    try:
        with open(paths.state("llm_spend.json"), "w", encoding="utf-8") as fh:
            json.dump(log, fh, indent=2)
    except OSError as e:
        # No stamp means no brake. Refuse rather than spend with nothing holding
        # the cadence, and say why so the panel can show it.
        print(f"ai_desk: cannot write the spend log ({type(e).__name__}: {e}) — refusing the paid call")
        return False, f"the spend log is not writable ({type(e).__name__})"
    return True, ""


def _load(name):
    """A snapshot, or {}. A missing file is the normal first-run state and stays
    quiet; a corrupt or unreadable one is a real fault and says so, because a
    silent {} here reaches the model as 'the board is empty' rather than
    'the board could not be read'."""
    path = os.path.join(paths.STATE_ROOT, name)
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        print(f"ai_desk: cannot read {name} ({type(e).__name__}: {e}) — that section is missing "
              "from the board")
        return {}


def _distill():
    g = _load("gex_snapshot.json"); sw = _load("swing_snapshot.json")
    L = [f"AS OF {datetime.now(ET).strftime('%Y-%m-%d %H:%M ET')}"]
    if g:
        L.append(f"\n== SPX 0DTE MASTER == {g.get('bias')} | conviction {g.get('conviction')}/100 | "
                 f"regime {g.get('regime')} | expected move ±{g.get('exp_oc_pct')}% | SPX {g.get('spx_level')}")
        rec = g.get("reconcile") or {}
        L.append("  reconciled inputs: " + "; ".join(f"{i['src']}={i['bias']}({i['score']:+d})" for i in rec.get("inputs", [])))
        L.append(f"  thesis: {g.get('thesis','')}")
    for sym in ("SPX", "NDX"):
        p = _load(f"periscope_{sym}.json")
        if not p.get("ok"):
            continue
        uw = p.get("uw") or {}; q = p.get("quality") or {}
        L.append(f"\n== {sym} PERISCOPE == {p.get('spot')} | signal: {p.get('signal')} (conv {q.get('conviction')}) | "
                 f"flip {p.get('gamma_flip')} | call wall {p.get('call_wall')} put wall {p.get('put_wall')} | "
                 f"net gamma {p.get('net_gex_musd')}M")
        if uw:
            L.append(f"  UW: {uw.get('overall')} dir-score {uw.get('dir_score')} | "
                     f"intraday tape {(uw.get('intraday') or {}).get('bias')} | implied move ±{(uw.get('implied_move') or {}).get('move_pct')}%")
        if q.get("entry"):
            L.append(f"  entry read: {q.get('entry')}")
    try:
        import positions
        openp = positions.list_open()
        if openp:
            L.append("\n== OPEN POSITIONS ==")
            for x in openp:
                L.append(f"  {x['sym']} {x['strike']:.0f}{x['dir'][0].upper()} entry ${x['entry_prem']} | "
                         f"live: {x.get('cur_action')} ({x.get('cur_reason')}) underlying {x.get('cur_move')}%")
    except Exception as e:
        # This used to be `except: pass`, which handed the model a board with no
        # positions section and no way to tell that from a flat book. An absent
        # section it cannot see is worse than a line saying the section failed.
        print(f"ai_desk: open positions unavailable ({type(e).__name__}: {str(e)[:80]})")
        L.append(f"\n== OPEN POSITIONS == UNAVAILABLE ({type(e).__name__}) — assume nothing about the book")
    ctx = (sw or {}).get("market_context")
    if ctx:
        SN = {"XLK": "Tech", "XLC": "Comm", "XLY": "Discr", "XLF": "Financials", "XLV": "Health",
              "XLE": "Energy", "XLI": "Industrials", "XLP": "Staples", "XLB": "Materials", "XLU": "Utilities", "XLRE": "RealEstate"}
        L.append(f"\n== SWING ENVIRONMENT == regime {ctx.get('regime')} (VIX {ctx.get('vix')}) | "
                 f"leading: {', '.join(SN.get(s,s) for s in ctx.get('leaders',[]))} | "
                 f"lagging: {', '.join(SN.get(s,s) for s in ctx.get('laggards',[]))}")
        L.append(f"  stress: {ctx.get('stress')}")
    sigs = (sw or {}).get("signals", [])[:5]
    if sigs:
        # LAST PRICE IS REQUIRED HERE — without it the agent invents strikes off a guessed spot.
        L.append("  top swing signals (last price given — any strikes you propose MUST be near it): " + "; ".join(
            f"{s['ticker']} @ ${s.get('last')} {s['direction']} conv{s['conviction']}"
            + (f" IV{(s.get('iv') or {}).get('iv')}" if isinstance(s.get("iv"), dict) and (s.get("iv") or {}).get("iv")
               else (f" IV{s.get('iv')}" if s.get("iv") else ""))
            + f" [{s.get('sector','')}/{s.get('rotation','')}]" for s in sigs))
    return "\n".join(L)


def _rule_based(board, reason="no API key"):
    """The free read. `reason` is the honest cause, not a guess: the old text
    always said 'add API credits', which is wrong whenever the real problem is a
    missing key or a service outage."""
    return {"ok": True, "model": "rule-based", "state": status()["state"], "reason": reason, "text":
            f"AI desk unavailable: {reason}. Rule-based: read the master 0DTE bias + the swing "
            "regime/rotation panel above; act only where the 0DTE signal, the UW flow, and the sector "
            "rotation agree, and stand down where they conflict."}




def _load_out():
    """The last brief written, or {}. Same rule as _load: silence for absent,
    a warning for unreadable."""
    try:
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        print(f"ai_desk: cannot read {os.path.basename(OUT)} ({type(e).__name__}: {e})")
        return {}


def _write_out(r):
    """Persist the brief. A write that fails is reported, never swallowed: the
    dashboard reads this file, so losing it silently makes the panel show a
    stale brief with a fresh-looking timestamp."""
    try:
        with open(paths.state("ai_desk_snapshot.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2, default=str)
    except (OSError, TypeError, ValueError) as e:
        print(f"ai_desk: could not write the desk snapshot ({type(e).__name__}: {e})")
    return r

def _market_open():
    """Single source of truth in session.py — 09:20 boot to 16:00 close. Anything that costs money
    checks this. Duplicated per-module copies are how analyst.py ended up with no gate at all."""
    try:
        import session
        return session.awake()
    except Exception as e:
        # Fall back to the same window computed inline, and SAY that the shared
        # gate is missing. Falling back quietly is how a broken import turns
        # into a spend gate nobody knows has gone.
        print(f"ai_desk: session.py unavailable ({type(e).__name__}) — using the inline 09:20-16:00 gate")
        from datetime import datetime as _d
        from zoneinfo import ZoneInfo as _Z
        n = _d.now(_Z("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960

def desk(force=False):
    if not force and not _market_open():
        return {**_load_out(), 'skipped': 'market closed'}
    key = anthropic_key()
    if not key or llm_disabled():
        # Before the cadence brake: with no key and no permission to spend there
        # is nothing to ration, and stamping the log here would gate the first
        # real call once a key is added.
        r = _rule_based(_distill(), anthropic_reason("ai_desk"))
        r["as_of"] = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
        return _write_out(r)
    # THE COST BRAKE. /refresh calls this with no gate of its own, so a user
    # holding down the refresh button would pay for a Fable read at high effort
    # on every click. Refuse and hand back the last brief instead.
    ok_to_spend, why = claim_spend("ai_desk", DESK_CADENCE_S, force=force)
    if not ok_to_spend:
        return {**_load_out(), "skipped": why}
    board = _distill()
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": FALLBACK}],
            output_config={"effort": EFFORT},
            system=SYSTEM,
            messages=[{"role": "user", "content": "Here is the live board. Give me the desk brief:\n\n" + board}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        note_llm_success("ai_desk")
        r = {"ok": True, "text": text, "model": resp.model, "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
             "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
        return _write_out(r)
    except Exception as e:
        # Which failure it was decides what the panel tells the user to do, so
        # classify it instead of printing one "unavailable" for all three.
        state, reason = note_llm_failure("ai_desk", e)
        r = _rule_based(board, reason)
        r["state"] = state
        r["error"] = f"{type(e).__name__}: {str(e)[:100]}"
        r["as_of"] = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
        return _write_out(r)


if __name__ == "__main__":
    st = status()
    print(f"anthropic {st['state']}: {st['detail']}")
    r = desk(force=True)
    print("model:", r.get("model"), "| usage:", r.get("usage"), "| err:", r.get("error"))
    print("\n" + (r.get("text") or ""))
