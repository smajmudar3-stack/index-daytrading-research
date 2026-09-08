"""committee.py — an adversarial second opinion before any trade reaches the book.

Pattern from sbauwow/schwagent (RESEARCH_BOTS.md #2): rather than trusting one model pass, a proposed
entry is argued against by a BEAR ADVOCATE whose only job is to kill it, and then judged by a RISK
OFFICER who holds an explicit veto. A single LLM pass is prone to talking itself into a trade; making
the counter-case a separate, adversarially-prompted call is what catches that.

Cost discipline: this runs ONLY on decisions that already survived the fast pass and the deterministic
gates — which, by design, is rare (most cycles are STAND_DOWN). A quiet day costs nothing extra.
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import ai_desk                        # the key, the health row and the cost brake live there
import uw_client                      # the shared service-health vocabulary
from idt import paths

ET = ZoneInfo("America/New_York")
LOG = os.path.join(paths.STATE_ROOT, "committee_log.jsonl")
BUDGET = os.path.join(paths.STATE_ROOT, "committee_budget.json")
MODEL = "claude-fable-5-1"
FALLBACK = "claude-opus-4-8"

# Two high-effort Fable calls per review. By design this only runs on decisions
# that already cleared the fast pass and the deterministic gates, which is rare,
# so a day that reaches this number is a loop rather than a busy market.
MAX_REVIEWS_PER_DAY = 40

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


def status():
    """This module's health, in the shape every outside-service module returns.
    See uw_client.STATES for what each state means."""
    st = ai_desk.anthropic_status("committee")
    if st["ok"] and _reviews_today() >= MAX_REVIEWS_PER_DAY:
        return uw_client.service_status(
            "committee", "anthropic", uw_client.STATE_DISABLED,
            f"Today's committee budget of {MAX_REVIEWS_PER_DAY} reviews is spent. Further trades are "
            "REJECTED rather than approved unreviewed.")
    return st


def _client():
    key = ai_desk.anthropic_key()
    if not key:
        return None
    from anthropic import Anthropic
    return Anthropic(api_key=key)


def _budget():
    """{date, n} for today, or a fresh counter. Persisted because ai_trader runs
    in a NEW PROCESS every cycle: an in-memory count would reset each time and
    cap nothing."""
    today = datetime.now(ET).date().isoformat()
    try:
        with open(BUDGET, encoding="utf-8") as fh:
            d = json.load(fh)
        if isinstance(d, dict) and d.get("date") == today:
            return {"date": today, "n": int(d.get("n") or 0)}
    except FileNotFoundError:
        pass                                   # first review of the day, not a fault
    except (OSError, ValueError, TypeError) as e:
        print(f"committee: budget file unreadable ({type(e).__name__}: {e}) — counting from zero today")
    return {"date": today, "n": 0}


def _reviews_today():
    return _budget()["n"]


def _spend_review():
    """Count one review. Returns False when today's budget is already spent."""
    b = _budget()
    if b["n"] >= MAX_REVIEWS_PER_DAY:
        return False
    b["n"] += 1
    try:
        with open(paths.state("committee_budget.json"), "w", encoding="utf-8") as fh:
            json.dump(b, fh, indent=2)
    except OSError as e:
        # An uncounted review is an uncapped one. Say so and let it through:
        # this gate protects the bill, and the committee protects the book.
        print(f"committee: cannot write the budget file ({type(e).__name__}: {e}) — review not counted")
    return True


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
    """Returns {verdict, reason, size_factor, bear, ok, state}. Fails OPEN to the original decision on
    error — the deterministic gates have already run, so a committee outage must not silently block
    trading, but it IS recorded so the gap is visible.

    The daily budget is the one exception, and it fails CLOSED: running out of budget means something
    is calling this in a loop, and this module's own risk prompt is the argument for which way to
    fail — missing a trade costs nothing, a bad trade compounds backwards."""
    st = ai_desk.anthropic_status("committee")
    out = {"verdict": "APPROVE", "reason": f"committee unavailable ({st['state']}) — deterministic gates only",
           "size_factor": 1.0, "bear": None, "ok": False, "state": st["state"]}
    if st["state"] in (uw_client.STATE_NO_KEY, uw_client.STATE_DISABLED):
        # Nothing to ration and nothing to try: fail open to the deterministic
        # gates, as before, and record that the review did not happen. An outage
        # deliberately does NOT land here, because the next call may well work
        # and this is a safety check, not a nicety.
        _log(decision, out)
        return out
    if not _spend_review():
        out = {"verdict": "REJECT",
               "reason": f"today's committee budget of {MAX_REVIEWS_PER_DAY} reviews is spent — refusing "
                         "rather than approving an unreviewed trade",
               "size_factor": 0.0, "bear": None, "ok": False, "state": uw_client.STATE_DISABLED}
        _log(decision, out)
        return out
    try:
        client = _client()
        if client is None:
            _log(decision, out)
            return out
        desc = _describe(decision)
        bear = _ask(client, BEAR_SYSTEM, f"PROPOSED TRADE:\n{desc}\n\nLIVE BOARD:\n{board}")
        judge = _ask(client, RISK_SYSTEM,
                     f"PROPOSED TRADE:\n{desc}\n\nBEAR ADVOCATE'S OBJECTION:\n"
                     f"{bear.get('strongest_objection')}\n(fatal: {bear.get('fatal')}; "
                     f"what would have to be true: {bear.get('what_would_have_to_be_true')})\n\n"
                     f"LIVE BOARD:\n{board}")
        ai_desk.note_llm_success("committee")
        out = {"verdict": (judge.get("verdict") or "REJECT").upper(),
               "reason": judge.get("reason", ""),
               "size_factor": float(judge.get("size_factor") or 1.0),
               "bear": bear, "ok": True, "state": uw_client.STATE_AVAILABLE}
    except Exception as e:
        # Name the failure. "committee error (APIStatusError)" told the operator
        # nothing about whether to add a key, add credit, or wait.
        state, reason = ai_desk.note_llm_failure("committee", e)
        out["state"] = state
        out["reason"] = f"committee error: {reason} — deterministic gates only"
    _log(decision, out)
    return out


def _log(decision, out):
    """Append the verdict to the committee log. A failure here is REPORTED: this
    file is the only record that an adversarial review happened at all, and a
    decision that does not outlive its process cannot be audited later."""
    try:
        with open(paths.state("committee_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(ET).isoformat(timespec="seconds"),
                                "sym": decision.get("sym"), "structure": decision.get("structure"),
                                "conviction": decision.get("conviction"), **{k: out[k] for k in
                                ("verdict", "reason", "size_factor", "ok")},
                                "state": out.get("state"),
                                "bear_objection": (out.get("bear") or {}).get("strongest_objection"),
                                "bear_fatal": (out.get("bear") or {}).get("fatal")}, default=str) + "\n")
    except (OSError, TypeError, ValueError) as e:
        print(f"committee: VERDICT NOT LOGGED ({type(e).__name__}: {e}) — {out.get('verdict')} on "
              f"{decision.get('sym')} {decision.get('structure')} is not in {os.path.basename(LOG)}")


if __name__ == "__main__":
    st = status()
    print(f"anthropic {st['state']}: {st['detail']}")
    board = ai_desk._distill()
    demo = {"sym": "SPY", "structure": "CALL_DEBIT_SPREAD", "strikes": [771, 773], "expiry": "0DTE",
            "conviction": 72, "size": "small", "net_prem": 0.83, "max_loss": 0.83,
            "contracts": 5, "total_risk": 412, "pct_of_account": 8.2,
            "thesis": "Long gamma pin above the flip with call wall overhead — buy the drift into the wall."}
    r = review(demo, board)
    print("BEAR:", json.dumps(r.get("bear"), indent=2))
    print(f"\nRISK OFFICER: {r['verdict']} (size x{r['size_factor']}) — {r['reason']}")
