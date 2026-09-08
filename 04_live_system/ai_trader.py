"""ai_trader.py — the AGENTIC trader. Fable 5 ingests the whole board and outputs concrete trade
decisions (long calls/puts, debit/credit spreads, condors) with strikes + size, logs them, paper-
executes into an accountable P&L, and pings you on every new ENTER/EXIT.

Guardrails baked in (a sound agent, not a gambler): only ENTERs when conviction ≥ threshold AND the
board's signals agree; defined-risk preferred; capped open positions; STAND_DOWN is the default.
Real-order execution is intentionally NOT wired here (the agent decides + paper-trades; live fills
stay a supervised step). Runs on the scan cadence.

Fail-closed, on purpose. Every gate between the model's proposal and the book — risk_gates, the
pricer, sizing — used to be wrapped in `except Exception: pass`, so a gate that could not be imported
disappeared and the trade was logged anyway, indistinguishably from one that passed every check. If a
gate cannot run, the ENTER is REFUSED and says which gate was missing.
"""
import json
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import ai_desk
from idt import db, keys, paths

log = logging.getLogger("ai_trader")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand. The old HERE/"data" join with a bare sqlite3 handle had no
# WAL and a 5-second lock while scan_all wrote the same book, and no directory at all on a clone.
DB = paths.state("agent_trades.db")
OUT = paths.state("agent_snapshot.json")
MODEL = "claude-fable-5-1"
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
    "the time. (2) Buying 0DTE premium on a directional signal is REFUTED in this repo: it measured -10% to "
    "-11% per trade out of sample, and the gamma-flip version of it -7.2% to -19.1%. Do not propose it, and "
    "do not treat the gamma flip as a call/put trigger. Dealer gamma forecasts the day's RANGE, never its "
    "direction. (3) Selling that range is NOT a validated alternative either: the 0DTE condor is roughly "
    "break-even on real SPXW quotes, so size it as unproven. (4) Prefer DEFINED-RISK (spreads/condors) over "
    "naked in every case. (5) A directional lean on the board is CONTEXT, not a setup. (6) Size 'small' "
    "unless conviction is high and everything aligns. Be selective — a great agent trades rarely and stands "
    "down constantly. STAND_DOWN is the expected answer on most cycles.\n"
    "BEFORE you output, run an internal RISK-OFFICER pass on each proposed ENTER and drop any that fails: "
    "would a skeptic call this a real edge or just noise? Is the dealer-gamma read being used as a "
    "risk/regime filter (correct) or smuggled in as a directional forecast (wrong — GEX does not predict "
    "forward returns)? What specifically would have to be true for this to lose, and is that likely today? "
    "If you cannot answer crisply, the answer is STAND_DOWN. Deterministic risk gates run after you and "
    "will hard-reject anything outside the entry window, inside an event blackout, over the daily caps, or "
    "premium-selling in a negative-gamma regime — do not waste a proposal on those."
)


def _con():
    try:
        c = db.connect(DB)
    except sqlite3.Error as e:
        log.error("ai_trader: cannot open the trade book at %s: %s", DB, e)
        raise
    c.execute("""CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, sym TEXT,
        action TEXT, structure TEXT, legs TEXT, size TEXT, conviction INT, expiry TEXT, thesis TEXT,
        est_prem REAL, entry_under REAL, status TEXT DEFAULT 'open', exit_under REAL, exit_ts TEXT, pnl_pct REAL)""")
    # peak favorable excursion — drives the trailing stop that lets winners run without giving it all back
    # pnl_real_pct / exit_prem — real option-level P&L (premium in vs premium out), the honest number
    # when we can price it. ticket.py carries the same DDL on purpose; change both together.
    cols = {r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()}
    for col, ddl in (("peak_fav", "REAL DEFAULT 0"), ("pnl_real_pct", "REAL"), ("exit_prem", "REAL")):
        if col not in cols:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} {ddl}")
    c.commit()
    c.row_factory = sqlite3.Row
    return c


def _load_snap(name):
    """A live snapshot JSON, or {} when it has not been written yet."""
    path = paths.state(name)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}          # first run, or that engine has not produced a snapshot yet
    except (OSError, json.JSONDecodeError) as e:
        # Corrupt is not empty: it means the writer died halfway and the agent is about to decide
        # against a board with a hole in it.
        log.warning("ai_trader: snapshot %s is unreadable (%s) — the agent will decide without it",
                    path, e)
        return {}


def _spot(sym):
    import yfinance as yf
    m = {"SPX": "^SPX", "NDX": "^NDX"}
    try:
        return float(yf.Ticker(m.get(sym, sym)).fast_info["lastPrice"])
    except Exception as e:
        # A missing spot silently skips management of an open position, so it is a warning, not a shrug.
        log.warning("ai_trader: no live quote for %s (%s: %s)", sym, type(e).__name__, e)
        return None


def _count_open():
    c = _con()
    try:
        return c.execute("SELECT COUNT(*) FROM trades WHERE status='open'").fetchone()[0]
    finally:
        c.close()


def _open_summary():
    c = _con()
    try:
        rows = c.execute("SELECT * FROM trades WHERE status='open'").fetchall()
    finally:
        c.close()
    if not rows:
        return "none"
    return "; ".join(f"#{r['id']} {r['sym']} {r['structure']} ({r['legs']}) conv{r['conviction']}" for r in rows)


def _notify(title, msg):
    """Desktop ping. Best effort by design: the book is the record, the ping is a courtesy, and
    osascript does not exist off macOS. Logged at debug so a Linux box is not spammed every cycle,
    but it returns whether it worked rather than swallowing the result."""
    try:
        import subprocess
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
        return True
    except Exception as e:
        log.debug("ai_trader: desktop notification unavailable (%s: %s)", type(e).__name__, e)
        return False


def _write_snapshot(out):
    """Write the agent snapshot the dashboard renders. A failed write leaves the previous decision on
    screen looking current, so it is reported in the returned dict as well as logged."""
    try:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
    except OSError as e:
        log.error("ai_trader: could not write %s: %s", OUT, e)
        out["write_error"] = f"{type(e).__name__}: {e}"
    return out


def _market_open():
    """Single source of truth in session.py — 09:20 boot to 16:00 close. Anything that costs money
    checks this. Duplicated per-module copies are how analyst.py ended up with no gate at all."""
    try:
        import session
        return session.awake()
    except Exception as e:
        # The fallback below is the duplicate this docstring warns about. Kept so a broken import
        # cannot leave the gate open, but reaching it is now logged instead of silent.
        log.warning("ai_trader: session.py unavailable (%s: %s) — falling back to a local copy of the "
                    "market hours, the duplication that caused this bug class before",
                    type(e).__name__, e)
        from datetime import datetime as _d
        from zoneinfo import ZoneInfo as _Z
        n = _d.now(_Z("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960


def _prompt_block(name, gaps):
    """One module's contribution to the agent's prompt.

    These blocks are the agent's RULES — the growth plan, the validated research, the risk gates, its
    own track record, sizing, sleeves, lessons. Losing one used to be an `except Exception: pass`, so
    the model decided without a constraint and nothing anywhere said so. Now the gap is logged and
    carried into the snapshot."""
    try:
        mod = __import__(name)
        text = mod.prompt_block()
    except Exception as e:
        log.warning("ai_trader: prompt block '%s' unavailable (%s: %s) — the agent is deciding "
                    "without it", name, type(e).__name__, e)
        gaps.append({"block": name, "error": f"{type(e).__name__}: {str(e)[:120]}"})
        return ""
    return ("\n\n== " + text) if text else ""


def decide(force=False):
    if not force and not _market_open():
        return {'ok': False, 'skipped': 'market closed', 'decisions': []}
    key = keys.get("ANTHROPIC_API_KEY")
    gaps = []
    # The validated research goes FIRST — it outranks every other block in the prompt.
    plan = _prompt_block("growth_plan", gaps)
    gates = "".join(_prompt_block(n, gaps)
                    for n in ("rules", "risk_gates", "graduation", "sizing", "sleeves", "lessons"))
    try:
        open_now = _open_summary()
    except sqlite3.Error as e:
        # Deciding without knowing what is already open is how the same position gets entered twice.
        # Refuse the pass and say so in the snapshot the dashboard reads, rather than raising into
        # scan_all, which catches everything and leaves yesterday's decision on screen.
        log.error("ai_trader.decide: the trade book could not be read (%s) — no decision this pass", e)
        return _write_snapshot({"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
                                "error": f"trade book unreadable: {type(e).__name__}: {e}",
                                "decisions": [], "prompt_gaps": gaps,
                                "overall": "agent offline (the trade book could not be read)"})
    board = (ai_desk._distill() + f"\n\n== CURRENT AGENT POSITIONS ==\n{open_now}\n(max {MAX_OPEN} open)"
             + plan + gates)
    if not key:
        return _write_snapshot({"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
                                "error": "no API key", "decisions": [], "prompt_gaps": gaps,
                                "overall": "agent offline (no API)"})
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
        log.warning("ai_trader.decide: no decision this pass (%s: %s)", type(e).__name__, str(e)[:120])
        return _write_snapshot({"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
                                "error": f"{type(e).__name__}: {str(e)[:100]}", "decisions": [],
                                "prompt_gaps": gaps, "overall": "agent error"})

    decisions = data.get("decisions", [])
    try:
        n_open = _count_open()
    except sqlite3.Error as e:
        log.error("ai_trader.decide: the trade book could not be read (%s) — the model's decisions "
                  "are being discarded rather than acted on unchecked", e)
        return _write_snapshot({"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": False,
                                "error": f"trade book unreadable: {type(e).__name__}: {e}",
                                "decisions": [], "prompt_gaps": gaps, "model": model,
                                "overall": data.get("overall", "")})
    try:
        import risk_gates
    except Exception as e:
        # Fail closed. The deterministic gates are what make an LLM proposal safe to record; running
        # without them used to be silent, and every ENTER went straight into the book.
        log.error("ai_trader: risk_gates unavailable (%s: %s) — every ENTER this pass will be REFUSED",
                  type(e).__name__, e)
        risk_gates = None
    g = _load_snap("gex_snapshot.json")
    acted = []
    record_errors = []
    for d in decisions:
        act = d.get("action")
        try:
            conv = int(d.get("conviction", 0) or 0)
        except (TypeError, ValueError):
            # A non-numeric conviction used to raise here and discard every remaining decision in the
            # pass. Zero is the fail-closed reading: it is below CONV_MIN, so the trade is not taken.
            log.warning("ai_trader: %s returned a non-numeric conviction %r — treated as 0, which "
                        "refuses the trade", d.get("sym"), d.get("conviction"))
            conv = 0
        # ── HARD GATE: the LLM proposes, the deterministic gates dispose ──────────────
        if act == "ENTER":
            if risk_gates is None:
                acted.append({**d, "action": "BLOCKED",
                              "blocked_by": ["risk gates unavailable, refusing to enter unchecked"],
                              "thesis": d.get("thesis", "") + " — REFUSED: risk gates could not run"})
                continue
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
            try:
                import option_pricer as OP
                pr = OP.price_trade(d, under)
            except Exception as e:
                # This module already refuses a trade it cannot price ("unpriceable" below); an
                # exception is the same answer arriving differently, so it gets the same refusal
                # rather than the old silent fall-through that logged the trade unpriced.
                log.error("ai_trader: pricer unavailable for %s %s (%s: %s) — ENTER refused",
                          sym, d.get("structure"), type(e).__name__, e)
                acted.append({**d, "action": "BLOCKED",
                              "blocked_by": [f"pricer unavailable: {type(e).__name__}: {str(e)[:80]}"],
                              "thesis": d.get("thesis", "") + " — REFUSED: the trade could not be priced"})
                continue
            if pr is None or pr.get("net") is None:
                acted.append({**d, "action": "BLOCKED",
                              "blocked_by": [f"unpriceable: {(pr or {}).get('reject', 'strikes not on the live chain')}"],
                              "thesis": d.get("thesis", "") + " — REFUSED: strikes are not tradeable"})
                continue
            if not pr.get("tradeable"):
                # record the measured spread so the provisional thresholds can be calibrated later
                try:
                    risk_gates._log({"ts": datetime.now(ET).isoformat(timespec="seconds"),
                                     "sym": d.get("sym"), "structure": d.get("structure"),
                                     "strikes": d.get("strikes"), "net": pr.get("net"),
                                     "pkg_spread_pct": pr.get("pkg_spread_pct"),
                                     "allowed": False, "blocks": [pr.get("reject")]})
                except Exception as e:
                    log.warning("ai_trader: could not record the illiquid-package spread for %s (%s: %s) "
                                "— the liquidity thresholds lose a calibration point", sym, type(e).__name__, e)
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
                _sl_max = sleeves.get(_sl).get("max_open", 99)
                _sl_open = sleeves.open_count(_sl)
                sz = sizing.size_trade(pr.get("max_loss"), conv, size_hint=d.get("size"), sleeve=_sl)
            except Exception as e:
                # Fail closed: sizing is the hard per-trade risk cap. It used to be `except: pass`,
                # which logged the trade with no size and no cap check at all.
                log.error("ai_trader: sizing/sleeves unavailable for %s (%s: %s) — ENTER refused",
                          sym, type(e).__name__, e)
                acted.append({**d, "action": "BLOCKED",
                              "blocked_by": [f"sizing unavailable: {type(e).__name__}: {str(e)[:80]}"],
                              "thesis": d.get("thesis", "") + " — REFUSED: the trade could not be sized"})
                continue
            d = {**d, "sleeve": _sl}
            # sleeve-level concurrency cap (0DTE is 1 at a time per RULES.md)
            if _sl_open >= _sl_max:
                acted.append({**d, "action": "BLOCKED",
                              "blocked_by": [f"sleeve '{_sl}' already at its max open positions"],
                              "thesis": d.get("thesis", "") + f" — REFUSED: {_sl} sleeve full"})
                continue
            if not sz.get("ok"):
                acted.append({**d, "action": "BLOCKED", "blocked_by": [f"sizing: {sz['reason']}"],
                              "thesis": d.get("thesis", "") + f" — REFUSED: {sz['reason']}"})
                continue
            d = {**d, "contracts": sz["contracts"], "total_risk": sz["total_risk"],
                 "pct_of_account": sz["pct_of_account"]}
            # ── ADVERSARIAL COMMITTEE: bear advocate + risk-officer veto. Only reached by
            # proposals that already cleared the deterministic gates, so this is rare and cheap.
            try:
                import committee
                cv = committee.review(d, board)
            except Exception as e:
                # The committee is an LLM call sitting AFTER the deterministic gates, so a transient
                # API error does not block the trade. It must not read as a clean bill of health
                # either, so the failure is written into the thesis and lands in the book itself.
                log.warning("ai_trader: committee review did not run for %s (%s: %s)",
                            sym, type(e).__name__, e)
                d = {**d, "committee_error": f"{type(e).__name__}: {str(e)[:80]}",
                     "thesis": d.get("thesis", "") + f" [committee review did not run: {type(e).__name__}]"}
            else:
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
            c = _con()
            try:
                c.execute("""INSERT INTO trades(ts,sym,action,structure,legs,size,conviction,expiry,thesis,
                    est_prem,entry_under,status) VALUES(?,?,?,?,?,?,?,?,?,?,?, 'open')""",
                          (datetime.now(ET).isoformat(timespec="seconds"), sym, act, d.get("structure"),
                           (d.get("legs") or "") + (f" | strikes {d.get('strikes')}" if d.get("strikes") else ""),
                           d.get("size"), conv, d.get("expiry"), d.get("thesis"), prem, under))
                c.commit()
            except sqlite3.Error as e:
                # An unrecorded ENTER is a corrupt track record, and it used to be indistinguishable
                # from a recorded one. No ping either: you must not be told about a trade the book
                # does not have.
                log.error("ai_trader: ENTER %s %s NOT recorded: %s", sym, d.get("structure"), e)
                record_errors.append({"action": "ENTER", "sym": sym, "error": f"{type(e).__name__}: {e}"})
                acted.append({**d, "logged": False, "record_error": f"{type(e).__name__}: {e}"})
                continue
            finally:
                c.close()
            n_open += 1
            _notify(f"🤖 AGENT ENTER · {sym} {d.get('structure','')}",
                    f"{d.get('legs','')} — conv {conv}. {d.get('thesis','')[:90]}")
            acted.append({**d, "logged": True})
        elif act == "EXIT":
            c = _con()
            try:
                r = c.execute("SELECT * FROM trades WHERE status='open' AND sym=? ORDER BY id DESC",
                              (d.get("sym"),)).fetchone()
                if not r:
                    # The agent asked to exit something the book does not have open. Silence here read
                    # as a completed exit in the snapshot.
                    log.warning("ai_trader: EXIT %s ignored — no open trade for that symbol", d.get("sym"))
                    acted.append({**d, "closed": None, "note": "no open trade for that symbol"})
                else:
                    c.execute("UPDATE trades SET status='closed', exit_under=?, exit_ts=? WHERE id=?",
                              (_spot(d.get("sym")), datetime.now(ET).isoformat(timespec="seconds"), r["id"]))
                    c.commit()
                    _notify(f"🤖 AGENT EXIT · {d.get('sym')} {r['structure']}", f"{d.get('thesis','')[:90]}")
                    acted.append({**d, "closed": r["id"]})
            except sqlite3.Error as e:
                log.error("ai_trader: EXIT %s NOT recorded: %s", d.get("sym"), e)
                record_errors.append({"action": "EXIT", "sym": d.get("sym"), "error": f"{type(e).__name__}: {e}"})
                acted.append({**d, "closed": None, "record_error": f"{type(e).__name__}: {e}"})
            finally:
                c.close()
        else:
            acted.append(d)
    out = {"as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"), "ok": not record_errors, "model": model,
           "overall": data.get("overall", ""), "decisions": acted,
           "prompt_gaps": gaps, "record_errors": record_errors,
           "usage": {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens}}
    return _write_snapshot(out)


def open_trades():
    c = _con()
    try:
        r = c.execute("SELECT * FROM trades WHERE status='open' ORDER BY id DESC").fetchall()
    finally:
        c.close()
    return [dict(x) for x in r]


def _peri(sym):
    return _load_snap(f"periscope_{sym}.json")


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
    except Exception as e:
        # Not fatal here (these are already-open trades, and the rule-based exits below still run),
        # but the settlement-aware time stop is what keeps a physically-settled position from being
        # assigned. Losing it quietly is not acceptable.
        log.error("ai_trader.manage_open: risk_gates unavailable (%s: %s) — the settlement time stop "
                  "will NOT run this cycle", type(e).__name__, e)
        risk_gates = None
    try:
        open_now = open_trades()
    except sqlite3.Error as e:
        # This is the exit engine. If it cannot read the book, no stop, no trail and no time stop runs
        # this cycle, and the only thing standing between that and an unmanaged position is this line.
        log.error("ai_trader.manage_open: the trade book could not be read (%s) — NO open trade was "
                  "managed this cycle", e)
        return {"managed": 0, "error": f"{type(e).__name__}: {e}"}
    managed = 0
    for t in open_now:
        sym = t["sym"]; struct = (t.get("structure") or "").upper()
        spot = _spot(sym)
        if spot is None or not t.get("entry_under"):
            log.warning("ai_trader.manage_open: #%s %s not managed this cycle (%s)", t["id"], sym,
                        "no live quote" if spot is None else "no entry level on the row")
            continue
        managed += 1
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
            c = _con()
            try:
                c.execute("UPDATE trades SET peak_fav=? WHERE id=?", (round(peak, 3), t["id"]))
                c.commit()
            except sqlite3.Error as e:
                # The trailing stop reads peak_fav off the row. If it does not persist, the trail
                # silently resets every cycle and a won trade can be handed all the way back.
                log.error("ai_trader.manage_open: #%s peak_fav not saved (%s) — the trailing stop is "
                          "running on a stale peak", t["id"], e)
            finally:
                c.close()
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
                else:
                    log.warning("ai_trader.manage_open: #%s closed WITHOUT a real exit price (%s) — it "
                                "will count as modelled, not measured, in graduation.stats()",
                                t["id"], (pr or {}).get("reject", "no net price"))
            except Exception as e:
                # This is the measured-vs-modelled boundary. Silence here quietly lowers
                # measured_fraction and nobody can tell which trades lost their real P&L.
                log.warning("ai_trader.manage_open: #%s could not be re-priced on exit (%s: %s) — it "
                            "will count as modelled, not measured", t["id"], type(e).__name__, e)
        if action == "CUT_SIDE":
            c = _con()
            try:
                c.execute("UPDATE trades SET thesis=thesis||' [one side closed]' WHERE id=?", (t["id"],))
                c.commit()
            except sqlite3.Error as e:
                log.error("ai_trader.manage_open: #%s CUT_SIDE not recorded (%s) — no ping sent", t["id"], e)
                continue
            finally:
                c.close()
            _notify(f"🤖 AGENT CUT SIDE · {sym}", reason)
        elif action == "CUT":
            c = _con()
            try:
                c.execute("""UPDATE trades SET status='closed', exit_under=?, exit_ts=?, pnl_pct=?,
                             exit_prem=?, pnl_real_pct=? WHERE id=?""",
                          (round(spot, 2), datetime.now(ET).isoformat(timespec="seconds"), round(fav, 2),
                           exit_prem, round(pnl_real, 2) if pnl_real is not None else None, t["id"]))
                c.commit()
            except sqlite3.Error as e:
                # Write first, ping second. A CUT ping on a trade the book still shows open is how a
                # position gets managed twice, or not at all.
                log.error("ai_trader.manage_open: #%s CUT NOT recorded (%s) — the trade is still open "
                          "in the book and no ping was sent", t["id"], e)
                continue
            finally:
                c.close()
            _pl = f" · P&L {pnl_real:+.1f}%" if pnl_real is not None else ""
            _notify(f"🤖 AGENT CUT · {sym} {struct.replace('_',' ')}",
                    f"{reason} (underlying {fav:+.2f}%){_pl}")
        elif action == "SCALE":
            c = _con()
            try:
                c.execute("UPDATE trades SET thesis=thesis||' [scaled half]' WHERE id=?", (t["id"],))
                c.commit()
            except sqlite3.Error as e:
                log.error("ai_trader.manage_open: #%s SCALE not recorded (%s) — no ping sent", t["id"], e)
                continue
            finally:
                c.close()
            _notify(f"🤖 AGENT SCALE · {sym}", reason)
    return {"managed": managed, "open": len(open_now)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    o = decide(force=True)
    print("model:", o.get("model"), "| err:", o.get("error"), "| overall:", o.get("overall"))
    for d in o.get("decisions", []):
        print(f"  {d.get('action')} {d.get('sym')} {d.get('structure','')} conv{d.get('conviction')} — {d.get('thesis','')[:70]}")
    if o.get("prompt_gaps"):
        print("prompt blocks missing:", o["prompt_gaps"])
    if o.get("record_errors"):
        print("NOT RECORDED:", o["record_errors"])
