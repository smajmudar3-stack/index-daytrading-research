"""ai_trader.py — the AGENTIC trader. Fable 5 ingests the whole board and outputs concrete trade
decisions (long calls/puts, debit/credit spreads, condors) with strikes + size, logs them, paper-
executes into an accountable P&L, and pings you on every new ENTER/EXIT.

Guardrails baked in (a sound agent, not a gambler): only ENTERs when conviction ≥ threshold AND the
board's signals agree; defined-risk preferred; capped open positions; STAND_DOWN is the default.
Real-order execution is intentionally NOT wired here (the agent decides + paper-trades; live fills
stay a supervised step). Runs on the scan cadence.
"""
import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import ai_desk

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "agent_trades.db")
OUT = os.path.join(HERE, "data", "agent_snapshot.json")
MODEL = "claude-fable-5"
FALLBACK = "claude-opus-4-8"
CONV_MIN = 66          # don't enter below this
MAX_OPEN = 3           # cap concurrent agent positions

SYSTEM = (
    "You are an autonomous, disciplined options-trading agent managing a small account for a trader who "
    "has stepped back — YOU make the calls now. You receive a live board: the SPX 0DTE reconciled signal, "
    "SPX/NDX gamma periscopes (signal, conviction, gamma flip, call/put walls, real Unusual Whales flow, "
    "condor math), current open agent positions, and the swing regime/rotation/stress. "
    "Decide what to DO. Output ONLY valid JSON, no prose, of the form:\n"
    '{"decisions":[{"sym":"SPX|NDX|<ticker>","action":"ENTER|EXIT|STAND_DOWN","structure":"LONG_CALL|'
    'LONG_PUT|CALL_DEBIT_SPREAD|PUT_DEBIT_SPREAD|IRON_CONDOR|CALL_CREDIT_SPREAD|PUT_CREDIT_SPREAD","legs":'
    '"concrete strikes e.g. buy 7740C/sell 7775C","strikes":[7740,7775],"size":"small|normal|full",'
    '"conviction":0-100,"expiry":"0DTE|weekly|~35DTE","thesis":"one tight sentence"}], '
    '"overall":"one-line state of play"}\n'
    "STRIKES ARE REAL, NOT ILLUSTRATIVE. The `strikes` array must contain actual numeric strikes derived "
    "from the CURRENT SPOT given to you for that symbol (it is in the board — use it; never guess a price). "
    "Long leg first, then short leg. They must sit on the real listed strike grid near spot (index: 5-25 pt "
    "increments; equities: $1/$2.50/$5). A structure whose strikes are not tradeable is rejected outright, "
    "so do not emit placeholder or 'e.g.' values.\n"
    "HARD RULES: (1) Only ENTER when conviction ≥ 66 AND the board's independent signals genuinely agree "
    "(regime + flow + price + rotation). If they conflict, STAND_DOWN — that is the correct answer most of "
    "the time. (2) NEVER buy naked premium into a pin/long-gamma regime with a tiny expected move — sell it "
    "(condor/credit spread) or stand down. (3) NEVER buy calls while price is falling or puts while rising. "
    "(4) Prefer DEFINED-RISK (spreads/condors) over naked. (5) Respect the gamma flip as the call/put line. "
    "(6) Size 'small' unless conviction is high and everything aligns. Be selective — a great agent trades "
    "rarely and stands down constantly. Match structure to regime (trend=directional debit; pin=condor/credit).\n"
    "BEFORE you output, run an internal RISK-OFFICER pass on each proposed ENTER and drop any that fails: "
    "would a skeptic call this a real edge or just noise? Is the dealer-gamma read being used as a "
    "risk/regime filter (correct) or smuggled in as a directional forecast (wrong — GEX does not predict "
    "forward returns)? What specifically would have to be true for this to lose, and is that likely today? "
    "If you cannot answer crisply, the answer is STAND_DOWN. Deterministic risk gates run after you and "
    "will hard-reject anything outside the entry window, inside an event blackout, over the daily caps, or "
    "premium-selling in a negative-gamma regime — do not waste a proposal on those."
)


def _con():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, sym TEXT,
        action TEXT, structure TEXT, legs TEXT, size TEXT, conviction INT, expiry TEXT, thesis TEXT,
        est_prem REAL, entry_under REAL, status TEXT DEFAULT 'open', exit_under REAL, exit_ts TEXT, pnl_pct REAL)""")
    # peak favorable excursion — drives the trailing stop that lets winners run without giving it all back
    cols = {r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()}
    if "peak_fav" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN peak_fav REAL DEFAULT 0")
        c.commit()
    # real option-level P&L (premium in vs premium out) — the honest number, when we can price it
    if "pnl_real_pct" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN pnl_real_pct REAL")
        c.execute("ALTER TABLE trades ADD COLUMN exit_prem REAL")
        c.commit()
    c.row_factory = sqlite3.Row
    return c


def _load_snap(name):
    try:
        return json.load(open(os.path.join(HERE, "data", name)))
    except Exception:
        return {}


def _spot(sym):
    import yfinance as yf
    m = {"SPX": "^SPX", "NDX": "^NDX"}
    try:
        return float(yf.Ticker(m.get(sym, sym)).fast_info["lastPrice"])
    except Exception:
        return None


def _open_summary():
    c = _con(); rows = c.execute("SELECT * FROM trades WHERE status='open'").fetchall(); c.close()
    if not rows:
        return "none"
    return "; ".join(f"#{r['id']} {r['sym']} {r['structure']} ({r['legs']}) conv{r['conviction']}" for r in rows)


def _notify(title, msg):
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
    except Exception:
        pass



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
        return {'ok': False, 'skipped': 'market closed', 'decisions': []}
    key = ai_desk._key()
    try:
        import growth_plan
        plan = "\n\n== " + growth_plan.prompt_block()
    except Exception:
        plan = ""
    # The validated research goes FIRST — it outranks every other block in the prompt.
    try:
        import rules
        gates = "\n\n== " + rules.prompt_block()
    except Exception:
        gates = ""
    try:
        import risk_gates
        gates += "\n\n== " + risk_gates.prompt_block()
    except Exception:
        pass
    try:
        import graduation
        gates += "\n\n== " + graduation.prompt_block()
    except Exception:
        pass
    try:
        import sizing
        gates += "\n\n== " + sizing.prompt_block()
    except Exception:
        pass
    try:
        import sleeves
        gates += "\n\n== " + sleeves.prompt_block()
    except Exception:
        pass
    try:
        import lessons
        lb = lessons.prompt_block()
        if lb:
            gates += "\n\n== " + lb
    except Exception:
        pass
    board = (ai_desk._distill() + f"\n\n== CURRENT AGENT POSITIONS ==\n{_open_summary()}\n(max {MAX_OPEN} open)"
             + plan + gates)
    if not key:
        out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
               "error": "no API key", "decisions": [], "overall": "agent offline (no API)"}
        json.dump(out, open(OUT, "w"), indent=2); return out
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=6000,   # effort=high emits a thinking block that shares this budget
            betas=["server-side-fallback-2026-06-01"], fallbacks=[{"model": FALLBACK}],
            output_config={"effort": "high"}, system=SYSTEM,
            messages=[{"role": "user", "content": "Live board. Decide (JSON only):\n\n" + board}])
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        if resp.stop_reason == "max_tokens":
            # effort=high thinking shares the token budget; a truncated reply would parse as invalid
            # JSON and look like an API error. Fail loudly with the real cause instead.
            raise ValueError("agent response truncated at max_tokens — raise the budget")
        raw = raw[raw.find("{"): raw.rfind("}") + 1]         # strip any stray text
        data = json.loads(raw)
        model = resp.model
    except Exception as e:
        out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
               "error": f"{type(e).__name__}: {str(e)[:100]}", "decisions": [], "overall": "agent error"}
        json.dump(out, open(OUT, "w"), indent=2); return out

    decisions = data.get("decisions", [])
    n_open = len(_con().execute("SELECT id FROM trades WHERE status='open'").fetchall())
    try:
        import risk_gates
    except Exception:
        risk_gates = None
    g = _load_snap("gex_snapshot.json")
    acted = []
    for d in decisions:
        act = d.get("action"); conv = int(d.get("conviction", 0) or 0)
        # ── HARD GATE: the LLM proposes, the deterministic gates dispose ──────────────
        if act == "ENTER" and risk_gates is not None:
            ok, blocks, shadow = risk_gates.check_entry(
                d, {"regime": g.get("regime"), "n_open": n_open, "conv_min": CONV_MIN})
            if not ok:
                acted.append({**d, "action": "BLOCKED", "blocked_by": blocks,
                              "thesis": d.get("thesis", "") + f" — REFUSED: {'; '.join(blocks)}"})
                continue
            if shadow:
                d = {**d, "shadow_flags": shadow}
        if act == "ENTER" and conv >= CONV_MIN and n_open < MAX_OPEN:
            sym = d.get("sym", "SPX"); under = _spot(sym)
            # ── PRICE IT FOR REAL: strikes must exist on the live chain and be tradeable ──────────
            prem = None
            try:
                import option_pricer as OP
                pr = OP.price_trade(d, under)
                if pr is None or pr.get("net") is None:
                    acted.append({**d, "action": "BLOCKED",
                                  "blocked_by": [f"unpriceable: {(pr or {}).get('reject', 'strikes not on the live chain')}"],
                                  "thesis": d.get("thesis", "") + " — REFUSED: strikes are not tradeable"})
                    continue
                if not pr.get("tradeable"):
                    # record the measured spread so the provisional thresholds can be calibrated later
                    try:
                        import risk_gates
                        risk_gates._log({"ts": datetime.now(ET).isoformat(timespec="seconds"),
                                         "sym": d.get("sym"), "structure": d.get("structure"),
                                         "strikes": d.get("strikes"), "net": pr.get("net"),
                                         "pkg_spread_pct": pr.get("pkg_spread_pct"),
                                         "allowed": False, "blocks": [pr.get("reject")]})
                    except Exception:
                        pass
                    acted.append({**d, "action": "BLOCKED",
                                  "blocked_by": [f"illiquid: {pr.get('reject')}"],
                                  "thesis": d.get("thesis", "") + f" — REFUSED: {pr.get('reject')}"})
                    continue
                prem = pr.get("net")
                d = {**d, "net_prem": prem, "max_loss": pr.get("max_loss"), "resolved_expiry": pr.get("expiry")}
                # ── AFFORDABILITY: can this account actually hold one contract inside the cap? ──
                try:
                    import sizing, sleeves
                    _sl = sleeves.sleeve_for(d)
                    # sleeve-level concurrency cap (0DTE is 1 at a time per RULES.md)
                    if sleeves.open_count(_sl) >= sleeves.get(_sl).get("max_open", 99):
                        acted.append({**d, "action": "BLOCKED",
                                      "blocked_by": [f"sleeve '{_sl}' already at its max open positions"],
                                      "thesis": d.get("thesis", "") + f" — REFUSED: {_sl} sleeve full"})
                        continue
                    sz = sizing.size_trade(pr.get("max_loss"), conv, size_hint=d.get("size"), sleeve=_sl)
                    d = {**d, "sleeve": _sl}
                    if not sz.get("ok"):
                        acted.append({**d, "action": "BLOCKED", "blocked_by": [f"sizing: {sz['reason']}"],
                                      "thesis": d.get("thesis", "") + f" — REFUSED: {sz['reason']}"})
                        continue
                    d = {**d, "contracts": sz["contracts"], "total_risk": sz["total_risk"],
                         "pct_of_account": sz["pct_of_account"]}
                except Exception:
                    pass
                # ── ADVERSARIAL COMMITTEE: bear advocate + risk-officer veto. Only reached by
                # proposals that already cleared the deterministic gates, so this is rare and cheap.
                try:
                    import committee
                    cv = committee.review(d, board)
                    if cv["verdict"] == "REJECT":
                        acted.append({**d, "action": "BLOCKED",
                                      "blocked_by": [f"risk officer: {cv['reason']}"],
                                      "committee": cv,
                                      "thesis": d.get("thesis", "") + f" — VETOED: {cv['reason']}"})
                        continue
                    if cv["verdict"] == "RESIZE" and cv.get("size_factor", 1.0) < 1.0:
                        newc = max(1, int((d.get("contracts") or 1) * cv["size_factor"]))
                        d = {**d, "contracts": newc, "committee": cv,
                             "thesis": d.get("thesis", "") + f" [resized x{cv['size_factor']}: {cv['reason']}]"}
                    else:
                        d = {**d, "committee": cv}
                except Exception:
                    pass
            except Exception:
                pass                                  # pricer unavailable → fall back to logging unpriced
            c = _con()
            c.execute("""INSERT INTO trades(ts,sym,action,structure,legs,size,conviction,expiry,thesis,
                est_prem,entry_under,status) VALUES(?,?,?,?,?,?,?,?,?,?,?, 'open')""",
                      (datetime.now(ET).isoformat(timespec="seconds"), sym, act, d.get("structure"),
                       (d.get("legs") or "") + (f" | strikes {d.get('strikes')}" if d.get("strikes") else ""),
                       d.get("size"), conv, d.get("expiry"), d.get("thesis"), prem, under))
            c.commit(); c.close(); n_open += 1
            _notify(f"🤖 AGENT ENTER · {sym} {d.get('structure','')}",
                    f"{d.get('legs','')} — conv {conv}. {d.get('thesis','')[:90]}")
            acted.append({**d, "logged": True})
        elif act == "EXIT":
            c = _con()
            r = c.execute("SELECT * FROM trades WHERE status='open' AND sym=? ORDER BY id DESC", (d.get("sym"),)).fetchone()
            if r:
                c.execute("UPDATE trades SET status='closed', exit_under=?, exit_ts=? WHERE id=?",
                          (_spot(d.get("sym")), datetime.now(ET).isoformat(timespec="seconds"), r["id"]))
                c.commit()
                _notify(f"🤖 AGENT EXIT · {d.get('sym')} {r['structure']}", f"{d.get('thesis','')[:90]}")
                acted.append({**d, "closed": r["id"]})
            c.close()
        else:
            acted.append(d)
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": True, "model": model,
           "overall": data.get("overall", ""), "decisions": acted,
           "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
    json.dump(out, open(OUT, "w"), indent=2, default=str)
    return out


def open_trades():
    c = _con(); r = c.execute("SELECT * FROM trades WHERE status='open' ORDER BY id DESC").fetchall(); c.close()
    return [dict(x) for x in r]


def _peri(sym):
    try:
        return json.load(open(os.path.join(HERE, "data", f"periscope_{sym}.json")))
    except Exception:
        return {}


# Peak-trailing stop (milgar/alpaca-options-framework pattern): once a trade has run far enough to be
# worth protecting, trail behind its best level instead of capping it at a fixed target. This is what
# lets a runner run while refusing to hand a won trade back.
TRAIL_ACTIVATE = {"index_0dte": 0.45, "other": 4.0}   # % favorable underlying move that arms the trail
TRAIL_GIVEBACK = 0.40                                  # exit after giving back this fraction of the peak


def manage_open():
    """Rule-based risk management on the agent's OPEN trades — runs every scan cycle (fast, no LLM).
    The whole edge of hitting the curve: CUT LOSERS SMALL (thesis invalidated / stop), LET WINNERS RIDE
    (scale at the wall, then TRAIL the peak, never cap the runner early). Uses the live gamma levels."""
    try:
        import risk_gates
    except Exception:
        risk_gates = None
    for t in open_trades():
        sym = t["sym"]; struct = (t.get("structure") or "").upper()
        spot = _spot(sym)
        if spot is None or not t.get("entry_under"):
            continue
        entry = t["entry_under"]; move = (spot / entry - 1) * 100
        is_0dte = (t.get("expiry") or "").upper() in ("0DTE", "WEEKLY", "")
        bull = "CALL" in struct and "CREDIT" not in struct or struct in ("PUT_CREDIT_SPREAD",)
        bear = ("PUT" in struct and "CREDIT" not in struct) or struct == "CALL_CREDIT_SPREAD"
        p = _peri(sym) if sym in ("SPX", "NDX") else {}
        flip = (p.get("uw") or {}).get("uw_flip") or p.get("gamma_flip")
        cw = p.get("call_wall"); pw = p.get("put_wall")
        # directional-favorable move (positive = in your favor)
        fav = move if bull else -move if bear else 0
        # update peak favorable excursion (the trail rides this, not the current price)
        peak = max(float(t.get("peak_fav") or 0), fav)
        if peak > float(t.get("peak_fav") or 0):
            c = _con(); c.execute("UPDATE trades SET peak_fav=? WHERE id=?", (round(peak, 3), t["id"])); c.commit(); c.close()
        action = reason = None
        # tighter stops for 0DTE directional, wider for swing/stock
        idx0 = is_0dte and sym in ("SPX", "NDX")
        stop = 0.35 if idx0 else 3.0
        arm = TRAIL_ACTIVATE["index_0dte"] if idx0 else TRAIL_ACTIVATE["other"]
        # settlement-aware time stop comes FIRST — assignment risk outranks P&L
        fc = risk_gates.force_close_reason(t) if risk_gates else None
        if fc:
            action, reason = "CUT", fc
        elif struct in ("IRON_CONDOR", "CALL_CREDIT_SPREAD", "PUT_CREDIT_SPREAD"):
            # premium sellers: per-side stop — a breached call side does NOT force-close an untouched
            # put side (MEICAgent pattern), so we only cut the side that actually broke.
            side_done = "[one side closed]" in (t.get("thesis") or "")
            if struct == "IRON_CONDOR" and cw and pw and not side_done:
                if spot > cw:
                    action, reason = "CUT_SIDE", f"call side breached ({cw:.0f}) — close the call spread, leave the put spread working"
                elif spot < pw:
                    action, reason = "CUT_SIDE", f"put side breached ({pw:.0f}) — close the put spread, leave the call spread working"
            elif (struct == "CALL_CREDIT_SPREAD" and cw and spot > cw) or (struct == "PUT_CREDIT_SPREAD" and pw and spot < pw):
                action, reason = "CUT", "short strike breached — close before max loss"
        else:
            # directional: CUT loser on invalidation/stop; RIDE winner, scale at the wall, trail the peak
            if flip and ((bull and spot < flip) or (bear and spot > flip)):
                action, reason = "CUT", f"lost the gamma flip ({flip:.0f}) — thesis invalidated, cut it small"
            elif fav <= -stop:
                action, reason = "CUT", f"stop hit ({fav:+.2f}% against) — cut the loser before it grows"
            elif peak >= arm and fav <= peak * (1 - TRAIL_GIVEBACK):
                action, reason = "CUT", (f"trailing stop — peaked {peak:+.2f}%, gave back to {fav:+.2f}% "
                                         f"({int(TRAIL_GIVEBACK*100)}% giveback). Bank the win.")
            elif bull and cw and spot >= cw and "[scaled half]" not in (t.get("thesis") or ""):
                action, reason = "SCALE", f"hit the call wall {cw:.0f} — bank half, TRAIL the rest (let it ride)"
            elif bear and pw and spot <= pw and "[scaled half]" not in (t.get("thesis") or ""):
                action, reason = "SCALE", f"hit the put wall {pw:.0f} — bank half, trail the rest"
        # Real option-level P&L: re-price the exact structure at the live market. This is what makes
        # the track record a measurement rather than an inference from the underlying's move.
        exit_prem = pnl_real = None
        if action in ("CUT",) and t.get("est_prem"):
            try:
                import option_pricer as OP
                pr = OP.price_trade(t, spot)
                if pr and pr.get("net") is not None:
                    exit_prem = pr["net"]
                    ep = float(t["est_prem"])
                    if ep > 0:                                   # debit: profit when it's worth more
                        pnl_real = (exit_prem - ep) / ep * 100
                    elif ep < 0:                                 # credit: profit when it costs less to close
                        pnl_real = (abs(ep) - abs(exit_prem)) / abs(ep) * 100
            except Exception:
                pass
        if action == "CUT_SIDE":
            c = _con()
            c.execute("UPDATE trades SET thesis=thesis||' [one side closed]' WHERE id=?", (t["id"],))
            c.commit(); c.close()
            _notify(f"🤖 AGENT CUT SIDE · {sym}", reason)
        elif action == "CUT":
            c = _con()
            c.execute("""UPDATE trades SET status='closed', exit_under=?, exit_ts=?, pnl_pct=?,
                         exit_prem=?, pnl_real_pct=? WHERE id=?""",
                      (round(spot, 2), datetime.now(ET).isoformat(timespec="seconds"), round(fav, 2),
                       exit_prem, round(pnl_real, 2) if pnl_real is not None else None, t["id"]))
            c.commit(); c.close()
            _pl = f" · P&L {pnl_real:+.1f}%" if pnl_real is not None else ""
            _notify(f"🤖 AGENT CUT · {sym} {struct.replace('_',' ')}",
                    f"{reason} (underlying {fav:+.2f}%){_pl}")
        elif action == "SCALE":
            c = _con(); c.execute("UPDATE trades SET thesis=thesis||' [scaled half]' WHERE id=?", (t["id"],)); c.commit(); c.close()
            _notify(f"🤖 AGENT SCALE · {sym}", reason)


if __name__ == "__main__":
    o = decide(force=True)
    print("model:", o.get("model"), "| err:", o.get("error"), "| overall:", o.get("overall"))
    for d in o.get("decisions", []):
        print(f"  {d.get('action')} {d.get('sym')} {d.get('structure','')} conv{d.get('conviction')} — {d.get('thesis','')[:70]}")
