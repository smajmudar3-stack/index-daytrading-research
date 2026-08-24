"""analyst.py — Fable 5 desk-analyst for the gap-and-go scanner.

Gives the scanner a human-like tactical read of the whole tape (not just mechanical hits):
overall gap environment, a per-candidate note (is momentum confirming since the open? does
the tape contradict the setup?), and an honest trade/sit-out call. Fable 5 with server-side
fallback to Opus; never breaks the scan (any error -> ok:False). Cadence-gated for cost.
"""
import os
from anthropic import Anthropic

MODEL = "claude-fable-5"    # Anthropic's most capable model (there is no "Opus 5")
FALLBACK = "claude-opus-4-8"
EFFORT = "medium"
MAX_TOKENS = 1100

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


def _key():
    for p in ("/Users/sahilmajmudar/quant-factory/.env",
              os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("ANTHROPIC_API_KEY")


def available():
    return bool(_key())


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
        go = c["setup"] == "GAP-AND-GO LONG"
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
    try:
        import session
        return session.awake()
    except Exception:
        return True


def analyze(snap, force=False):
    # THE LEAK: this is a Fable call and gap_scanner invokes it on EVERY 5-minute cycle. Ungated it
    # ran 288 times a day, ~190 of them overnight on a board that had not changed since the close.
    if not force and not _market_open():
        return {"ok": False, "skipped": "market closed", "text": None}
    if not available():
        return rule_based(snap)
    try:
        client = Anthropic(api_key=_key())
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            betas=["server-side-fallback-2026-06-01"],   # Fable 5: server-side fallback to Opus on refusal
            fallbacks=[{"model": FALLBACK}],
            output_config={"effort": EFFORT},
            system=SYSTEM,
            messages=[{"role": "user", "content": "Read this gap-and-go scan and brief the desk:\n\n" + _distill(snap)}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            return {"ok": False, "error": "refused", "text": None}
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        return {"ok": True, "text": text, "model": resp.model, "effort": EFFORT,
                "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
    except Exception as e:
        r = rule_based(snap)  # Fable failed (e.g. no credits) -> graceful rule-based read
        r["error"] = f"Fable unavailable ({type(e).__name__}); using rule-based. Add API credits to enable Fable."
        return r
