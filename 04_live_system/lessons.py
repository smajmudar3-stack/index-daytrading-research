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
import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "agent_trades.db")
OUT = os.path.join(HERE, "data", "lessons.json")
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
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _closed():
    try:
        c = _con()
        rows = c.execute("SELECT * FROM trades WHERE status='closed' ORDER BY id").fetchall()
        c.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _load():
    try:
        return json.load(open(OUT))
    except Exception:
        return {"lessons": [], "reviewed_at_n": 0, "summary": ""}


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
    except Exception:
        from datetime import datetime as _d
        from zoneinfo import ZoneInfo as _Z
        n = _d.now(_Z("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960

def review(force=False):
    """Re-derive the lesson set from the closed-trade history. Cheap and infrequent by design."""
    if not force and not _market_open():
        return {**_load(), 'skipped': 'market closed'}
    trades = _closed()
    n = len(trades)
    state = _load()
    if not force:
        if n < MIN_TRADES:
            return {**state, "skipped": f"only {n} closed trades (need {MIN_TRADES})"}
        if n - state.get("reviewed_at_n", 0) < REVIEW_EVERY_N:
            return {**state, "skipped": f"only {n - state.get('reviewed_at_n', 0)} new since last review"}

    import ai_desk
    key = ai_desk._key()
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
        return {**state, "error": f"{type(e).__name__}: {str(e)[:120]}"}

    out = {"lessons": (data.get("lessons") or [])[:MAX_LESSONS],
           "summary": data.get("summary", ""),
           "reviewed_at_n": n,
           "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
    json.dump(out, open(OUT, "w"), indent=2, default=str)
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
    r = review(force=True)
    if r.get("skipped"):
        print("skipped:", r["skipped"])
    elif r.get("error"):
        print("error:", r["error"])
    else:
        print("summary:", r.get("summary"))
        for i, x in enumerate(r.get("lessons", []), 1):
            print(f"  {i}. [{x.get('confidence')}] {x.get('text')}\n     evidence: {x.get('evidence')}")
