"""ai_desk.py — the AI desk strategist (Fable 5, Opus fallback). Reads the WHOLE board — 0DTE regime,
SPX/NDX periscopes, your open positions, the swing regime/rotation/stress, VIX — and produces a
holistic, reasoned synthesis, including the macro/geopolitical judgment the rule-based system can't do.

Not just a narrator: it weighs whether the pieces agree or conflict, names the single thing that matters
most, the real opportunity, and the biggest risk. Honest, no hype. Writes ai_desk_snapshot.json.
Cadence-gated + cached for cost. Falls back to a rule-based synthesis if the API is unavailable.
"""
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "ai_desk_snapshot.json")
MODEL = "claude-fable-5"        # user's choice (most capable); server-side fallback to Opus
FALLBACK = "claude-opus-4-8"
EFFORT = "high"
MAX_TOKENS = 5000        # effort=high thinking shares this budget — too low truncates the brief

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


def _key():
    for p in ("/Users/sahilmajmudar/quant-factory/.env",
              os.path.join(HERE, ".env")):
        if os.path.exists(p):
            for line in open(p):
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("ANTHROPIC_API_KEY")


def _load(name):
    try:
        return json.load(open(os.path.join(HERE, "data", name)))
    except Exception:
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
    except Exception:
        pass
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


def _rule_based(board):
    return {"ok": True, "model": "rule-based", "text":
            "AI desk unavailable (no API). Rule-based: read the master 0DTE bias + the swing regime/rotation "
            "panel above; act only where the 0DTE signal, the UW flow, and the sector rotation agree, and "
            "stand down where they conflict. Add API credits to enable the Fable desk read."}




def _load_out():
    try:
        return json.load(open(OUT))
    except Exception:
        return {}

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

def desk(force=False):
    if not force and not _market_open():
        return {**_load_out(), 'skipped': 'market closed'}
    board = _distill()
    key = _key()
    if not key:
        r = _rule_based(board); r["as_of"] = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
        json.dump(r, open(OUT, "w"), indent=2); return r
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
        r = {"ok": True, "text": text, "model": resp.model, "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
             "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
        json.dump(r, open(OUT, "w"), indent=2, default=str)
        return r
    except Exception as e:
        r = _rule_based(board); r["error"] = f"{type(e).__name__}: {str(e)[:100]}"
        r["as_of"] = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
        json.dump(r, open(OUT, "w"), indent=2); return r


if __name__ == "__main__":
    r = desk(force=True)
    print("model:", r.get("model"), "| usage:", r.get("usage"), "| err:", r.get("error"))
    print("\n" + (r.get("text") or ""))
