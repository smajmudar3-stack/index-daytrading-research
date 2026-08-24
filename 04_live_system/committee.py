"""committee.py — an adversarial second opinion before any trade reaches the book.

Pattern from sbauwow/schwagent (RESEARCH_BOTS.md #2): rather than trusting one model pass, a proposed
entry is argued against by a BEAR ADVOCATE whose only job is to kill it, and then judged by a RISK
OFFICER who holds an explicit veto. A single LLM pass is prone to talking itself into a trade; making
the counter-case a separate, adversarially-prompted call is what catches that.

Cost discipline: this runs ONLY on decisions that already survived the fast pass and the deterministic
gates — which, by design, is rare (most cycles are STAND_DOWN). A quiet day costs nothing extra.
"""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "committee_log.jsonl")
MODEL = "claude-fable-5"
FALLBACK = "claude-opus-4-8"

BEAR_SYSTEM = (
    "You are a BEAR ADVOCATE on an options desk. A colleague has proposed the trade below. Your ONLY job "
    "is to make the strongest honest case that it is a BAD trade — find the flaw, the thing they are "
    "pattern-matching instead of verifying, the way the board actually contradicts them, the scenario "
    "that takes it to max loss. Do not be contrarian for its own sake: if the trade is genuinely sound, "
    "say so plainly and say what would have to change for it to break. "
    "Output ONLY JSON, no prose and no markdown fence, with each text field under 60 words: "
    "{\"strongest_objection\":\"...\",\"fatal\":true|false,"
    "\"what_would_have_to_be_true\":\"...\",\"confidence\":0-100}"
)

RISK_SYSTEM = (
    "You are the RISK OFFICER. You hold a veto over every trade and you answer for losses, not for "
    "missed opportunities. You are given a proposed trade, the live board, and a bear advocate's "
    "strongest objection. Decide.\n"
    "Veto (REJECT) if: the board's signals genuinely conflict; the thesis depends on dealer gamma "
    "predicting DIRECTION (it does not — gamma is a volatility/regime gauge only); the bear objection is "
    "fatal and unanswered; the structure is wrong for the regime; or the edge is indistinguishable from "
    "noise. RESIZE if the idea is sound but the risk is too concentrated for the conviction. "
    "APPROVE only when the case is genuinely clean. Missing a trade costs nothing; a bad trade compounds "
    "backwards. When uncertain, REJECT.\n"
    "Output ONLY JSON, no prose and no markdown fence: {\"verdict\":\"APPROVE|RESIZE|REJECT\","
    "\"reason\":\"one tight sentence\",\"size_factor\":0.0-1.0}"
)


def _client():
    import ai_desk
    key = ai_desk._key()
    if not key:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=key)


def _ask(client, system, user, max_tokens=4000):
    # NOTE: with output_config effort=high the model emits a thinking block that draws on the SAME
    # max_tokens budget. Too small a budget truncates the answer mid-JSON and the parse fails, so this
    # is set well above what the JSON itself needs.
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=max_tokens,
        betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK}],
        output_config={"effort": "high"}, system=system,
        messages=[{"role": "user", "content": user}])
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    if resp.stop_reason == "max_tokens":
        raise ValueError(f"response truncated at max_tokens ({max_tokens}) — raise the budget")
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    return json.loads(raw)


def _describe(d):
    return (f"{d.get('sym')} {d.get('structure')} strikes {d.get('strikes')} expiry {d.get('expiry')} "
            f"conviction {d.get('conviction')} size {d.get('size')} | net premium {d.get('net_prem')} "
            f"max loss/contract {d.get('max_loss')} | {d.get('contracts')} contracts risking "
            f"${d.get('total_risk')} ({d.get('pct_of_account')}% of account)\nThesis: {d.get('thesis')}")


def review(decision, board):
    """Returns {verdict, reason, size_factor, bear}. Fails OPEN to the original decision on error —
    the deterministic gates have already run, so a committee outage must not silently block trading,
    but it IS recorded so the gap is visible."""
    out = {"verdict": "APPROVE", "reason": "committee unavailable — deterministic gates only",
           "size_factor": 1.0, "bear": None, "ok": False}
    try:
        client = _client()
        if client is None:
            return out
        desc = _describe(decision)
        bear = _ask(client, BEAR_SYSTEM, f"PROPOSED TRADE:\n{desc}\n\nLIVE BOARD:\n{board}")
        judge = _ask(client, RISK_SYSTEM,
                     f"PROPOSED TRADE:\n{desc}\n\nBEAR ADVOCATE'S OBJECTION:\n"
                     f"{bear.get('strongest_objection')}\n(fatal: {bear.get('fatal')}; "
                     f"what would have to be true: {bear.get('what_would_have_to_be_true')})\n\n"
                     f"LIVE BOARD:\n{board}")
        out = {"verdict": (judge.get("verdict") or "REJECT").upper(),
               "reason": judge.get("reason", ""),
               "size_factor": float(judge.get("size_factor") or 1.0),
               "bear": bear, "ok": True}
    except Exception as e:
        out["reason"] = f"committee error ({type(e).__name__}) — deterministic gates only"
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": datetime.now(ET).isoformat(timespec="seconds"),
                                "sym": decision.get("sym"), "structure": decision.get("structure"),
                                "conviction": decision.get("conviction"), **{k: out[k] for k in
                                ("verdict", "reason", "size_factor", "ok")},
                                "bear_objection": (out.get("bear") or {}).get("strongest_objection"),
                                "bear_fatal": (out.get("bear") or {}).get("fatal")}, default=str) + "\n")
    except Exception:
        pass
    return out


if __name__ == "__main__":
    import ai_desk
    board = ai_desk._distill()
    demo = {"sym": "SPY", "structure": "CALL_DEBIT_SPREAD", "strikes": [771, 773], "expiry": "0DTE",
            "conviction": 72, "size": "small", "net_prem": 0.83, "max_loss": 0.83,
            "contracts": 5, "total_risk": 412, "pct_of_account": 8.2,
            "thesis": "Long gamma pin above the flip with call wall overhead — buy the drift into the wall."}
    r = review(demo, board)
    print("BEAR:", json.dumps(r.get("bear"), indent=2))
    print(f"\nRISK OFFICER: {r['verdict']} (size x{r['size_factor']}) — {r['reason']}")
