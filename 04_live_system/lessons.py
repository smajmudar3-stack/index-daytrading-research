"""lessons.py — the self-improving loop (cobriensr/Options-Strike-Calculator pattern, RESEARCH_BOTS.md).

Periodically, the agent reviews its OWN closed trades and writes down what actually worked and what
didn't. Those curated lessons get injected back into its decision prompt, so the engine gets sharper
from its real track record instead of repeating the same mistake in a different ticker.

Guardrails against the obvious failure mode (an agent inventing flattering lessons from noise):
  - Runs only on a minimum sample of closed trades.
  - The model is shown outcomes ONLY — never told to find a winning story.
  - It is explicitly instructed that "no reliable pattern yet" is a valid and expected answer.
  - Lessons are capped and rotated, so the prompt can't grow into a wall of superstition.
"""
import json
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db, keys, paths

log = logging.getLogger("lessons")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand — the old HERE/"data" join plus a bare sqlite3 handle gave a
# fresh clone "unable to open database file" and no WAL against the writer running in scan_all.
DB = paths.state("agent_trades.db")
OUT = paths.state("lessons.json")
MODEL = "claude-fable-5"
FALLBACK = "claude-opus-4-8"

MIN_TRADES = 12          # below this, any "pattern" is noise
MAX_LESSONS = 6          # keep the injected block short and high-signal
REVIEW_EVERY_N = 5       # re-review after this many new closed trades

SYSTEM = (
    "You are a trading-performance reviewer auditing an autonomous options agent's closed trades. "
    "Your job is to extract only DURABLE, ACTIONABLE lessons that would change a future decision.\n"
    "Rules: (1) Be sceptical — with a small sample most apparent patterns are noise. 'No reliable "
    "pattern yet' is a correct, expected answer; say it rather than inventing one. (2) A lesson must be "
    "specific and checkable at decision time (e.g. 'debit spreads entered after 14:00 ET lost 4 of 5' — "
    "not 'be more disciplined'). (3) Never conclude that the agent should size up or trade more to catch "
    "up to a target. (4) Distinguish process errors (rule was broken) from outcome noise (rule was "
    "followed, trade lost anyway) — only process errors are lessons. "
    "Output ONLY valid JSON: {\"lessons\":[{\"text\":\"...\",\"evidence\":\"...\",\"confidence\":\"low|medium|high\"}],"
    "\"summary\":\"one line\"}"
)


def _con():
    try:
        c = db.connect(DB, readonly=True)
    except sqlite3.Error as e:
        log.error("lessons: cannot open the trade book at %s: %s", DB, e)
        raise
    c.row_factory = sqlite3.Row
    return c


def _closed():
    """Closed trades, oldest first.

    A missing table means the book has never been written and is honestly empty. Any other database
    error is raised: returning [] for both made an unreadable book report as "only 0 closed trades",
    which reads like a young track record rather than a broken one."""
    c = _con()
    try:
        rows = c.execute("SELECT * FROM trades WHERE status='closed' ORDER BY id").fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            return []
        log.error("lessons: cannot read the trade book at %s: %s", DB, e)
        raise
    finally:
        c.close()
    return [dict(r) for r in rows]


def _load():
    try:
        with open(OUT, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {"lessons": [], "reviewed_at_n": 0, "summary": ""}
    except (OSError, json.JSONDecodeError) as e:
        # A corrupt lessons file is not an empty one. Starting from scratch quietly would re-run a
        # paid review every cycle and never say why.
        log.warning("lessons: %s is unreadable (%s) — starting from an empty lesson set", OUT, e)
        return {"lessons": [], "reviewed_at_n": 0, "summary": "", "load_error": f"{type(e).__name__}: {e}"}


def _distill(trades):
    L = []
    for t in trades:
        L.append(
            f"#{t['id']} {t.get('sym')} {t.get('structure')} conv{t.get('conviction')} "
            f"exp={t.get('expiry')} entered {str(t.get('ts'))[:16]} legs={t.get('legs')} | "
            f"underlying move {t.get('pnl_pct')}% | peak favorable {t.get('peak_fav')}% | "
            f"exited {str(t.get('exit_ts'))[:16]} | thesis: {t.get('thesis')}"
        )
    return "\n".join(L)


def _market_open():
    """Single source of truth in session.py — 09:20 boot to 16:00 close. Anything that costs money
    checks this. Duplicated per-module copies are how analyst.py ended up with no gate at all."""
    try:
        import session
        return session.awake()
    except Exception as e:
        # The fallback below is the duplicate this docstring warns about. It is kept so a broken
        # import cannot leave the gate wide open, but using it is now a logged event rather than a
        # silent divergence from the one place the hours are defined.
        log.warning("lessons: session.py unavailable (%s: %s) — falling back to a local copy of the "
                    "market hours, which is exactly the duplication that caused this bug class before",
                    type(e).__name__, e)
        from datetime import datetime as _d
        from zoneinfo import ZoneInfo as _Z
        n = _d.now(_Z("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960


def review(force=False):
    """Re-derive the lesson set from the closed-trade history. Cheap and infrequent by design."""
    if not force and not _market_open():
        return {**_load(), 'skipped': 'market closed'}
    state = _load()
    try:
        trades = _closed()
    except sqlite3.Error as e:
        return {**state, "error": f"trade book unreadable: {type(e).__name__}: {e}"}
    n = len(trades)
    if not force:
        if n < MIN_TRADES:
            return {**state, "skipped": f"only {n} closed trades (need {MIN_TRADES})"}
        if n - state.get("reviewed_at_n", 0) < REVIEW_EVERY_N:
            return {**state, "skipped": f"only {n - state.get('reviewed_at_n', 0)} new since last review"}

    key = keys.get("ANTHROPIC_API_KEY")
    if not key:
        return {**state, "skipped": "no API key"}
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=5000,
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK}],
            output_config={"effort": "high"}, system=SYSTEM,
            messages=[{"role": "user", "content":
                       f"Here are the agent's {n} closed trades. Extract durable lessons (JSON only):\n\n"
                       + _distill(trades)}])
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        if resp.stop_reason == "max_tokens":
            raise ValueError("review truncated at max_tokens — raise the budget")
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(raw)
    except Exception as e:
        log.warning("lessons.review: no lessons this pass (%s: %s)", type(e).__name__, str(e)[:120])
        return {**state, "error": f"{type(e).__name__}: {str(e)[:120]}"}

    out = {"lessons": (data.get("lessons") or [])[:MAX_LESSONS],
           "summary": data.get("summary", ""),
           "reviewed_at_n": n,
           "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
    try:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    except OSError as e:
        # reviewed_at_n lives in this file. If it never lands, the paid review re-runs every cycle
        # and the agent keeps reading yesterday's lessons while thinking they are today's.
        log.error("lessons.review: could not write %s: %s — this review will be repeated next cycle",
                  OUT, e)
        out["write_error"] = f"{type(e).__name__}: {e}"
    return out


def prompt_block():
    s = _load()
    ls = s.get("lessons") or []
    if not ls:
        return ""
    body = " ".join(f"({i+1}) {x.get('text','')} [{x.get('confidence','')}]" for i, x in enumerate(ls))
    return (f"LESSONS FROM YOUR OWN CLOSED TRADES (reviewed at {s.get('reviewed_at_n')} trades): {body} "
            "Apply these where they bear on today's decision; ignore any that don't.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    r = review(force=True)
    if r.get("skipped"):
        print("skipped:", r["skipped"])
    elif r.get("error"):
        print("error:", r["error"])
    else:
        print("summary:", r.get("summary"))
        for i, x in enumerate(r.get("lessons", []), 1):
            print(f"  {i}. [{x.get('confidence')}] {x.get('text')}\n     evidence: {x.get('evidence')}")
