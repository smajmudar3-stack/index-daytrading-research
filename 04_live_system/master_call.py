"""master_call.py — THE master decision, made by Fable 5, rendered at the top of the dashboard.

The dashboard had a structural problem: several panels each announced their own headline, and they
routinely disagreed — a big green "BUY CALLS" sitting directly above a periscope reading "price is
FALLING" and a desk brief saying "sit out". A trader cannot act on four answers. This module produces
ONE call, and everything else on the page becomes supporting evidence for it.

Fable makes the judgment. It is given the whole board plus the out-of-sample research, and it must
return a concrete, actionable ticket: symbol, structure, entry, exit, stop, thesis, conviction.

Two honesty rules are built into the prompt rather than bolted on afterwards:
  - It must state conviction, and low conviction must mean STAND DOWN rather than a hedged half-answer.
  - If it proposes something the research rejected (buying 0DTE premium, −11%/trade), it must say so
    in a `contradicts_research` field. The tension gets surfaced to the trader, never hidden.

It also watches for BIG RUNS — the outsized-opportunity setups worth a look even when the core 0DTE
rule is standing down — and flags them with a macOS notification.
"""
import os
import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "master_call.json")
SEEN = os.path.join(HERE, "data", "big_runs_seen.json")
MODEL = "claude-fable-5"
FALLBACK = "claude-opus-4-8"

SYSTEM = (
    "You are the head trader for a small, aggressive 0DTE options account. You make THE call — one "
    "decision the trader acts on. No hedging, no 'it depends'. If the honest answer is stand down, say "
    "STAND DOWN with conviction and say why; that is a real answer and it is correct most days.\n\n"
    "You receive the full live board plus out-of-sample research. Return ONLY valid JSON:\n"
    '{"symbol":"SPY|QQQ|SPX|NDX|<ticker>","action":"ENTER|STAND_DOWN","structure":"IRON_CONDOR|'
    'CALL_DEBIT_SPREAD|PUT_DEBIT_SPREAD|LONG_CALL|LONG_PUT|CALL_CREDIT_SPREAD|PUT_CREDIT_SPREAD",'
    '"strikes":"the exact strikes, e.g. buy 768P/sell 770P/sell 774C/buy 776C",'
    '"entry_price":0.00,"take_profit_price":0.00,"stop_price":0.00,'
    '"take_profit_pct":0,"stop_pct":0,'
    '"underlying_target":0.00,"underlying_stop":0.00,'
    '"exit_note":"one line on how to manage it out","thesis":'
    '"2-3 sentences: what is actually happening and why this trade","conviction":0-100,'
    '"contradicts_research":true|false,"contradiction_note":"if true, name what the research says and '
    'why you are overriding it anyway","big_runs":[{"ticker":"","why":"one line","conviction":0-100}],'
    '"secondary":{"action":"ENTER|NONE","symbol":"","structure":"","strikes":"","entry_price":0.00,'
    '"take_profit_price":0.00,"stop_price":0.00,"underlying_target":0.00,"underlying_stop":0.00,'
    '"thesis":"","conviction":0-100,"contradicts_research":true|false},'
    '"headline":"6-10 words, the call at a glance"}\n\n'
    "RULES OF THE DESK:\n"
    "1. THE RANGE TRADE (validated): prior-close dealer gamma > +0.5 z means the day's range is "
    "overpriced — sell it with an iron condor. 853 trades OOS, +3.7%/trade, 91% win. When the gamma "
    "gate is open this is the primary call.\n"
    "2. THE DIRECTIONAL TRADE (enabled by the owner): long calls/puts or debit spreads on 0DTE. The "
    "owner trades this deliberately and wants it called. Be straight about it: the same backtest put "
    "directional 0DTE at −10% to −11% per trade, so set contradicts_research=true whenever you propose "
    "one and give a SPECIFIC reason this setup differs — a real catalyst, a decisive level reclaim on "
    "heavy volume, a trending tape with the flip behind it. 'Momentum looks strong' is not a reason. "
    "Because the expectancy is negative and the payoff is lottery-shaped, only call it when the setup "
    "is genuinely exceptional, and expect to decline most days.\n"
    "   Give BOTH when both are live: if the gamma gate is open AND a real directional setup exists, "
    "lead with the range trade and put the directional one in `secondary`.\n"
    "3. Never propose a trade the account cannot hold. SPX and NDX options are too large; express index "
    "views in SPY or QQQ.\n"
    "4. Conviction below 60 means STAND_DOWN. Do not emit a low-conviction ENTER.\n"
    "5. PRICES MUST BE REAL NUMBERS, not descriptions. Every ENTER needs an option-premium price to get "
    "in at, a premium price to TAKE PROFIT at, and a premium price to STOP OUT at — the actual number the "
    "trader types into the close order — plus the underlying levels that correspond to them.\n"
    "   - DEBIT structures (long calls/puts, debit spreads): entry_price is what you PAY. "
    "take_profit_price and stop_price are what you SELL at. Example: pay 1.20, take profit 1.80, stop 0.60.\n"
    "   - CREDIT structures (condors, credit spreads): entry_price is the credit you RECEIVE. "
    "take_profit_price and stop_price are what it COSTS to buy back. Max risk per contract = "
    "(wing width − credit). The tested stop is −0.5R, so stop_price = credit + 0.5*(width − credit). "
    "Example: credit 0.70 on a 2.00-wide → max risk 1.30 → stop when it costs 1.35 to close.\n"
    "   - For the validated condor the tested rule has NO profit target — it is held to decay and closed "
    "by 15:45 ET because SPY/QQQ are physically settled. In that case set take_profit_price to the price "
    "at which you would de-risk early if you want to (say 25-50% of the credit) and say plainly in "
    "exit_note that the tested rule holds to expiry and that taking profit early degraded it.\n"
    "6. BIG RUNS: separately, scan the board for outsized opportunities — a violent gap with real "
    "relative volume, a genuine squeeze setup, a stock making a decisive move on heavy flow. These are "
    "watch-list flags, not orders. Only flag something you would genuinely stake money on; an empty "
    "list is the right answer on a quiet day."
)


def _notify(title, msg):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
    except Exception:
        pass


def _board():
    import ai_desk
    parts = [ai_desk._distill()]
    for mod, label in (("rules", "VALIDATED RESEARCH"), ("risk_gates", "RISK GATES"),
                       ("sizing", "SIZING"), ("sleeves", "SLEEVES"), ("graduation", "TRACK RECORD")):
        try:
            m = __import__(mod)
            b = m.prompt_block()
            if b:
                parts.append(f"== {label} ==\n{b}")
        except Exception:
            continue
    # gap scanner candidates feed the BIG RUNS scan
    try:
        gap = json.load(open(os.path.join(HERE, "data", "gap_snapshot.json")))
        cands = gap.get("candidates") or []
        if cands:
            parts.append("== GAP / MOMENTUM CANDIDATES ==\n" + "\n".join(
                f"  {c.get('ticker')} gap {c.get('gap_pct')}% rvol {c.get('rvol')}x "
                f"open {c.get('open')} now {c.get('last')} since-open {c.get('since_open_pct')}% "
                f"[{c.get('setup')}]" for c in cands[:12]))
    except Exception:
        pass
    return "\n\n".join(parts)


def _load_seen():
    try:
        d = json.load(open(SEEN))
        if d.get("date") == datetime.now(ET).date().isoformat():
            return set(d.get("tickers", []))
    except Exception:
        pass
    return set()


def _save_seen(s):
    try:
        json.dump({"date": datetime.now(ET).date().isoformat(), "tickers": sorted(s)},
                  open(SEEN, "w"), indent=2)
    except Exception:
        pass




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

def decide(force=False):
    if not force and not _market_open():
        return {**(_load_out() or {}), 'skipped': 'market closed'}
    import ai_desk
    key = ai_desk._key()
    board = _board()
    if not key:
        r = {"ok": False, "error": "no API key", "action": "STAND_DOWN",
             "headline": "Agent offline — no API key",
             "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
        json.dump(r, open(OUT, "w"), indent=2)
        return r
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=6000,
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK}],
            output_config={"effort": "high"}, system=SYSTEM,
            messages=[{"role": "user", "content": "Live board. Make the call (JSON only):\n\n" + board}])
        if resp.stop_reason == "max_tokens":
            raise ValueError("truncated at max_tokens")
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        raw = raw[raw.find("{"): raw.rfind("}") + 1]
        d = json.loads(raw)
        d["model"] = resp.model
    except Exception as e:
        r = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}", "action": "STAND_DOWN",
             "headline": "Master call unavailable",
             "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
        json.dump(r, open(OUT, "w"), indent=2)
        return r

    d["ok"] = True
    d["as_of"] = datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")
    json.dump(d, open(OUT, "w"), indent=2, default=str)

    # notify on a fresh actionable call
    if d.get("action") == "ENTER" and int(d.get("conviction") or 0) >= 60:
        _notify(f"🎯 {d.get('symbol','')} {str(d.get('structure','')).replace('_',' ')} "
                f"· conv {d.get('conviction')}", str(d.get("headline", ""))[:120])
    # notify on NEW big runs only (once per ticker per day)
    seen = _load_seen()
    fresh = [b for b in (d.get("big_runs") or [])
             if b.get("ticker") and b["ticker"] not in seen and int(b.get("conviction") or 0) >= 60]
    for b in fresh[:3]:
        _notify(f"🚀 BIG RUN · {b['ticker']} (conv {b.get('conviction')})", str(b.get("why", ""))[:120])
        seen.add(b["ticker"])
    if fresh:
        _save_seen(seen)
    return d


if __name__ == "__main__":
    d = decide(force=True)
    if not d.get("ok"):
        print("error:", d.get("error"))
        raise SystemExit
    print(f"── MASTER CALL · {d['as_of']} · {d.get('model')}")
    print(f"   {d.get('headline','')}")
    print(f"   {d.get('action')} {d.get('symbol','')} {str(d.get('structure','')).replace('_',' ')} "
          f"· conviction {d.get('conviction')}")
    if d.get("action") == "ENTER":
        print(f"   entry : {d.get('entry')}")
        print(f"   exit  : {d.get('exit')}")
        print(f"   stop  : {d.get('stop')}")
    print(f"   thesis: {d.get('thesis')}")
    if d.get("contradicts_research"):
        print(f"   ⚠ CONTRADICTS RESEARCH: {d.get('contradiction_note')}")
    for b in d.get("big_runs") or []:
        print(f"   🚀 BIG RUN {b.get('ticker')} (conv {b.get('conviction')}) — {b.get('why')}")
