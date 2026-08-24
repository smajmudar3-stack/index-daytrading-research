"""analyst.py — Fable 5 desk-analyst for the gap-and-go scanner.

Gives the scanner a human-like tactical read of the whole tape (not just mechanical hits):
overall gap environment, a per-candidate note (is momentum confirming since the open? does
the tape contradict the setup?), and an honest trade/sit-out call. Fable 5 with server-side
fallback to Opus; never breaks the scan (any error -> ok:False). Cadence-gated for cost.
"""
import json
import os

import ai_desk                       # the key, the health row and the cost brake live there
from idt import paths

MODEL = "claude-fable-5"    # Anthropic's most capable model (there is no "Opus 5")
FALLBACK = "claude-opus-4-8"
EFFORT = "medium"
MAX_TOKENS = 1100
CADENCE_S = 900             # 15 minutes between PAID reads; see analyze() below
LAST = os.path.join(paths.STATE_ROOT, "analyst_last.json")

SYSTEM = (
    "You are a sharp, honest senior day-trading desk analyst who specializes in gap-and-go "
    "momentum on volatile stocks. You KNOW the backtested edge on this desk: a stock gapping "
    "up >3% on relative volume >1.5x, bought at the open and sold at the close, returns about "
    "+1.25%/trade at a 56% win rate (t=6.6, holds out-of-sample); the mirror is a >4% down-gap "
    "buying an intraday bounce. You also know the volume filter is essential — gaps WITHOUT "
    "volume are noise that fades. Your job: read the LIVE tape and give a concise, no-hype "
    "tactical brief. Be brutally honest: if a candidate is already fading hard since the open, "
    "say the momentum isn't confirming and to be cautious or wait for a reversal. If it's "
    "extending in the setup's direction, say it's confirming. Always remember the edge is a "
    "STATISTICAL average over many trades — any single trade is close to a coin flip — so keep "
    "position sizing and humility front of mind. Never invent news you don't have. "
    "Format: (1) 2-3 sentence read of today's gap environment; (2) one crisp line per candidate "
    "with a confirming/cautious verdict; (3) a one-line 'today: trade it / be selective / sit "
    "out' call. Plain text, tight, no filler."
)


def available():
    """One bit: can this module make a paid call at all. `status()` says which of
    the five states it is in when the answer is no."""
    return status()["ok"]


def status():
    """This module's health, in the shape every outside-service module returns.
    See uw_client.STATES for what each state means."""
    return ai_desk.anthropic_status("analyst")


def _load_last():
    """The last PAID read, so a cadence-gated cycle can show the real brief
    instead of flipping the panel back to the rule-based text every five
    minutes. Missing is normal; unreadable is reported."""
    try:
        with open(LAST, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        print(f"analyst: cannot read {os.path.basename(LAST)} ({type(e).__name__}: {e})")
        return {}


def _save_last(r):
    try:
        with open(paths.state("analyst_last.json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2, default=str)
    except (OSError, TypeError, ValueError) as e:
        print(f"analyst: could not cache the desk read ({type(e).__name__}: {e}) — the next cycle "
              "will fall back to the rule-based text")
    return r


def _distill(snap):
    lines = [f"As of {snap.get('as_of')}. Rule: {snap.get('rule')}."]
    cands = snap.get("candidates", [])
    if cands:
        lines.append("\nCANDIDATES (qualified setups):")
        for c in cands:
            lines.append(f"  {c['ticker']}: {c['setup']} | gap {c['gap_pct']:+.1f}% | RVOL {c['rvol']}x | "
                         f"open ${c['open']} | since-open {c['since_open_pct']:+.1f}%")
    else:
        lines.append("\nNO qualified candidates right now.")
    top = snap.get("all", [])[:8]
    if top:
        lines.append("\nBIGGEST GAPS today (context, incl. ones that DIDN'T qualify — note low RVOL = noise):")
        for r in top:
            lines.append(f"  {r['ticker']}: gap {r['gap_pct']:+.1f}% RVOL {r['rvol']}x since-open {r['since_open_pct']:+.1f}%")
    tr = snap.get("track", {})
    if tr.get("n"):
        lines.append(f"\nLive paper record so far: {tr['n']} trades, {tr.get('win')}% win, avg {tr.get('avg')}%/trade.")
    return "\n".join(lines)


def rule_based(snap):
    """Always-available tactical read (no API needed) — reads whether momentum is confirming
    since the open for each candidate. Used as the fallback when Fable credits are unavailable."""
    cands = snap.get("candidates", [])
    if not cands:
        top = snap.get("all", [])[:5]
        weak = [r for r in top if r["rvol"] < 1.5]
        note = (f"No qualified gap-and-go setups. Biggest gaps ({', '.join(r['ticker'] for r in top[:3])}) "
                f"lack the volume filter (RVOL<1.5) — those are noise gaps that tend to fade. "
                if weak else "No qualified setups right now. ")
        return {"ok": True, "text": note + "Today: SIT OUT — no edge without a volume-confirmed gap. "
                "Patience is the edge; most days have 0-3 setups.", "model": "rule-based"}
    lines = ["Today's gap tape, desk read (rule-based — add API credits for Fable):"]
    confirm = 0
    for c in cands:
        # There was a bare `c["setup"] == "GAP-AND-GO LONG"` here: a comparison whose
        # result went nowhere. Both setups are LONG (see the comment below), so nothing
        # branched on it and removing it changes no behaviour.
        since = c["since_open_pct"]
        # confirming = moving in the trade's favour since the open (both setups are LONG)
        if since > 0.3:
            v = f"CONFIRMING (+{since:.1f}% since open, momentum with you)"; confirm += 1
        elif since < -1.0:
            v = f"NOT confirming ({since:.1f}% since open — fading hard; be cautious / wait for a reversal candle)"
        else:
            v = f"neutral so far ({since:+.1f}% since open)"
        lines.append(f"  • {c['ticker']} ({c['setup']}, gap {c['gap_pct']:+.1f}% on {c['rvol']}x vol): {v}")
    call = ("TRADE IT selectively — some setups confirming." if confirm else
            "BE SELECTIVE / mostly sit out — none confirming yet; wait for momentum to align with the setup.")
    lines.append(f"Today: {call} Size small — the edge is the average over many trades, not any one.")
    return {"ok": True, "text": "\n".join(lines), "model": "rule-based"}


def _market_open():
    """The spend gate. This function is the one the file's own docstring is about:
    when `import session` failed it returned True, so a broken import meant the
    scanner paid for a Fable read around the clock. The fallback now computes the
    same 09:20-16:00 window inline and says the shared gate is gone."""
    try:
        import session
        return session.awake()
    except Exception as e:
        print(f"analyst: session.py unavailable ({type(e).__name__}) — using the inline 09:20-16:00 gate")
        from datetime import datetime as _d
        from zoneinfo import ZoneInfo as _Z
        n = _d.now(_Z("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960


def analyze(snap, force=False):
    # THE LEAK: this is a Fable call and gap_scanner invokes it on EVERY 5-minute cycle. Ungated it
    # ran 288 times a day, ~190 of them overnight on a board that had not changed since the close.
    if not force and not _market_open():
        return {"ok": False, "skipped": "market closed", "text": None}
    # Checked before the cadence brake: with no usable key there is nothing to
    # ration, and stamping the log here would gate the first real call once one
    # is added.
    if not available():
        return {**rule_based(snap), "state": status()["state"],
                "error": f"Fable unavailable: {ai_desk.anthropic_reason('analyst')}"}
    # The market-hours gate alone still leaves ~78 paid reads a session, one per
    # scan cycle, on a tape that moves far less than that. The cadence brake caps
    # it at one every 15 minutes and hands back the last real brief in between,
    # so the panel does not flip between Fable and rule-based text every refresh.
    ok_to_spend, why = ai_desk.claim_spend("analyst", CADENCE_S, force=force)
    if not ok_to_spend:
        cached = _load_last()
        if cached.get("text"):
            return {**cached, "cached": True, "skipped": why}
        return {**rule_based(snap), "skipped": why}
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ai_desk.anthropic_key())
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-06-01"],   # Fable 5: server-side fallback to Opus on refusal
            fallbacks=[{"model": FALLBACK}],
            output_config={"effort": EFFORT},
            system=SYSTEM,
            messages=[{"role": "user", "content": "Read this gap-and-go scan and brief the desk:\n\n" + _distill(snap)}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            # A refusal is not a failure of the service, so it must not trip the
            # health row; it is this one prompt being declined.
            print("analyst: the model refused this prompt — no brief this cycle")
            return {"ok": False, "error": "refused", "text": None}
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        ai_desk.note_llm_success("analyst")
        return _save_last({"ok": True, "text": text, "model": resp.model, "effort": EFFORT,
                           "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}})
    except Exception as e:
        # Say WHICH failure it was. "Add API credits" was printed for a missing
        # key, a rejected key and a dead network alike, and it is the wrong
        # instruction for two of the three.
        state, reason = ai_desk.note_llm_failure("analyst", e)
        r = rule_based(snap)          # the free read still runs, so the panel is never blank
        r["state"] = state
        r["error"] = f"Fable unavailable: {reason}. Using the rule-based read."
        return r
