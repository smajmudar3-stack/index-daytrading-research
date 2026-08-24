"""ticket.py — turn the validated setup into an exact, ready-to-place order ticket, and record the fill.

WHY THIS EXISTS INSTEAD OF AUTO-EXECUTION
    The validated strategy is a four-leg iron condor. Automated placement is blocked on three separate
    counts, none of which is a matter of preference:
      1. A launchd cron job cannot reach the Robinhood connector at all — that connector lives inside a
         Claude chat session, not in this process.
      2. The only agent-accessible account is a CASH account, and multi-leg orders are not available on
         cash or retirement accounts through that connector — an option-level upgrade does not change this.
      3. The account that can trade spreads is not agent-accessible.

    So the honest design is supervised execution: the engine does every part it can do well — decide,
    price, size, gate — and hands over a ticket precise enough to place in seconds. You place it; you
    tell it what you actually got filled at. That fill is what makes the track record real rather than
    modelled, which is the open question the research flagged as most important.

    Which is why record_fill() refuses quietly-wrong input and never reports success it did not get: a
    fill that fails to record does not just lose one row, it silently keeps the whole track record
    "modelled" while the operator believes it is becoming measured.

This module never places an order and holds no credentials.
"""
import json
import logging
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db, paths

log = logging.getLogger("ticket")

ET = ZoneInfo("America/New_York")
# Under STATE_ROOT, created on demand — the old HERE/"data" join plus a bare sqlite3 handle is how a
# fresh clone hit "unable to open database file".
OUT = paths.state("ticket.json")
DB = paths.state("agent_trades.db")


def _book():
    """The trade book, with its schema ensured.

    The DDL is deliberately duplicated from ai_trader._con() rather than imported. Recording a real
    fill is the one thing in this repo that must work even when the agent stack cannot be imported at
    all, and `import ai_trader` pulls in the whole desk. The two schemas must stay identical; adding a
    column in one means adding it in the other.
    """
    c = db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, sym TEXT,
        action TEXT, structure TEXT, legs TEXT, size TEXT, conviction INT, expiry TEXT, thesis TEXT,
        est_prem REAL, entry_under REAL, status TEXT DEFAULT 'open', exit_under REAL, exit_ts TEXT, pnl_pct REAL)""")
    cols = {r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()}
    for col, ddl in (("peak_fav", "REAL DEFAULT 0"), ("pnl_real_pct", "REAL"), ("exit_prem", "REAL")):
        if col not in cols:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} {ddl}")
    c.commit()
    return c


def _build(sym):
    import rules
    import risk_gates
    sym = sym or rules.PRODUCT
    g = rules.gate_state()
    c = rules.build_condor(sym)
    if not c or not c.get("ok"):
        return {"ready": False, "reason": (c or {}).get("reject", "condor could not be built"),
                "gate": g, "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
    if not g["open"]:
        return {"ready": False, "reason": "; ".join(g["reasons"]), "gate": g, "structure": c,
                "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}
    if not c.get("tradeable"):
        return {"ready": False, "reason": c.get("reject"), "gate": g, "structure": c,
                "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}

    decision = {"sym": sym, "structure": "IRON_CONDOR", "expiry": "0DTE", "conviction": 80}
    ok, blocks, shadow = risk_gates.check_entry(decision, {"n_open": 0, "conv_min": 66})
    if not ok:
        return {"ready": False, "reason": "; ".join(blocks), "gate": g, "structure": c,
                "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}

    import sizing
    sz = sizing.size_trade(c["risk_pts"], 80, sleeve="0dte")
    if not sz.get("ok"):
        return {"ready": False, "reason": sz["reason"], "gate": g, "structure": c,
                "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}

    t = {
        "ready": True,
        "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET"),
        "underlying": sym,
        "spot": c["spot"],
        "expiry": c["expiry"],
        "strategy": "Iron condor (sell the range)",
        "direction": "credit",
        "quantity": sz["contracts"],
        "limit_net_credit": c["credit"],          # price at the MID, never the bid
        "legs": [
            {"action": "BUY  to open", "right": "PUT", "strike": c["long_put"]},
            {"action": "SELL to open", "right": "PUT", "strike": c["short_put"]},
            {"action": "SELL to open", "right": "CALL", "strike": c["short_call"]},
            {"action": "BUY  to open", "right": "CALL", "strike": c["long_call"]},
        ],
        "max_loss_per_contract": round(c["risk_pts"] * 100, 2),
        "total_risk": sz["total_risk"],
        "pct_of_sleeve": sz["pct_of_account"],
        # The actual number to type into the closing order. Credit structure: you are BUYING it back,
        # so the stop is a COST. Max risk per contract = width - credit; the tested stop is -0.5R, which
        # is reached when buying it back costs credit + 0.5 * (width - credit).
        "stop_price": round(c["credit"] + rules.STOP_R * c["risk_pts"], 2),
        "take_profit_price": round(c["credit"] * 0.35, 2),
        "stop": f"buy back at ${round(c['credit'] + rules.STOP_R * c['risk_pts'], 2):.2f} "
                f"(-{int(rules.STOP_R*100)}% of max risk, ~${round(c['risk_pts']*100*rules.STOP_R*sz['contracts']):,} loss)",
        "take_profit": f"optional de-risk at ${round(c['credit']*0.35, 2):.2f} (65% of credit captured) — "
                       f"note the TESTED rule has NO profit target and holds to the time stop; "
                       f"closing early degraded results in backtest",
        "time_stop": "flat by 15:45 ET — SPY/QQQ are physically settled, no assignment risk allowed",
        "note": "Limit at the net mid. Do not chase the ask; if it will not fill near mid, skip the trade.",
    }
    try:
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(t, fh, indent=2, default=str)
    except OSError as e:
        # The dashboard renders this file. A silent write failure leaves a stale ticket on screen next
        # to a fresh one in the terminal, and they disagree about strikes.
        log.error("ticket.build: could not write %s: %s", OUT, e)
        t["write_error"] = f"{type(e).__name__}: {e}"
    return t


def build(sym=None):
    """Produce today's ticket if — and only if — every gate agrees the setup is live.

    Always returns a dict. A gate that throws used to propagate, and the dashboard's panel caught it
    and rendered nothing at all, so a broken pricer looked the same as a quiet market."""
    try:
        return _build(sym)
    except Exception as e:
        log.error("ticket.build: could not evaluate the gates: %s: %s", type(e).__name__, e)
        return {"ready": False,
                "reason": f"ticket unavailable: a gate could not be evaluated ({type(e).__name__}: {str(e)[:120]})",
                "error": f"{type(e).__name__}: {e}",
                "as_of": datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")}


def record_fill(credit, contracts, sym=None, expiry=None, strikes=None):
    """Log an ACTUAL fill so the track record becomes measurement rather than model.

    credit: net credit per contract you actually received (e.g. 0.47).

    Raises rather than returning on a failed write. This row is the difference between a modelled and
    a measured track record, so "it did not save" must never be reachable by not reading the result."""
    try:
        credit_f = float(credit)
        contracts_i = int(contracts)
    except (TypeError, ValueError) as e:
        raise ValueError(f"fill NOT recorded: credit and contracts must be numbers, got "
                         f"credit={credit!r} contracts={contracts!r}") from e
    if not credit_f > 0:
        raise ValueError(f"fill NOT recorded: net credit must be positive (you received it); got {credit_f}")
    if contracts_i < 1:
        raise ValueError(f"fill NOT recorded: contracts must be 1 or more; got {contracts_i}")

    import rules
    sym = sym or rules.PRODUCT

    spot = None
    try:
        import ai_trader
        spot = ai_trader._spot(sym)
    except Exception as e:
        # Not fatal: the fill is the point, the entry spot is context. But an unrecorded entry level
        # means this trade can never be scored against the underlying, so say it out loud.
        log.warning("ticket.record_fill: no entry spot for %s (%s: %s) — the row will have none",
                    sym, type(e).__name__, e)

    c = _book()
    try:
        cur = c.execute("""INSERT INTO trades(ts,sym,action,structure,legs,size,conviction,expiry,thesis,
            est_prem,entry_under,status) VALUES(?,?,?,?,?,?,?,?,?,?,?, 'open')""",
                        (datetime.now(ET).isoformat(timespec="seconds"), sym, "ENTER", "IRON_CONDOR",
                         f"REAL FILL {strikes or ''}", str(contracts_i), 80, expiry or "0DTE",
                         "live fill of the validated condor", -abs(credit_f), spot))
        c.commit()
        tid = cur.lastrowid
        # Read it back. A commit that reported success and left no row is the exact failure this
        # function exists to make impossible.
        row = c.execute("SELECT id FROM trades WHERE id=?", (tid,)).fetchone()
    except sqlite3.Error as e:
        log.error("ticket.record_fill: FILL NOT RECORDED (%s credit %s x%s): %s",
                  sym, credit_f, contracts_i, e)
        raise
    finally:
        c.close()
    if not row:
        log.error("ticket.record_fill: FILL NOT RECORDED (%s credit %s x%s): the row is not in %s "
                  "after commit", sym, credit_f, contracts_i, DB)
        raise RuntimeError(f"fill NOT recorded: no row {tid} in {DB} after commit")
    log.info("ticket.record_fill: recorded trade #%s — %s IRON_CONDOR credit %s x%s",
             tid, sym, credit_f, contracts_i)
    return {"logged": True, "trade_id": tid, "credit": credit_f, "contracts": contracts_i,
            "entry_under": spot, "book": DB}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "fill":
        # usage: ticket.py fill <credit_per_contract> <contracts>
        if len(sys.argv) < 4:
            print("usage: ticket.py fill <credit_per_contract> <contracts>")
            raise SystemExit(2)
        try:
            print(record_fill(sys.argv[2], sys.argv[3]))
        except Exception as e:
            # Exit non-zero and say so plainly. A fill you believe is recorded and is not corrupts
            # every number downstream of it.
            print(f"FILL NOT RECORDED — {type(e).__name__}: {e}")
            raise SystemExit(1) from e
        raise SystemExit

    t = build()
    if not t.get("ready"):
        print(f"NO TICKET — {t.get('reason')}")
        raise SystemExit
    print(f"╔═ ORDER TICKET · {t['as_of']}")
    print(f"║ {t['underlying']} @ {t['spot']:.2f}   exp {t['expiry']}   {t['strategy']}")
    print("║")
    for lg in t["legs"]:
        print(f"║   {lg['action']}   {t['underlying']} {t['expiry']} {lg['strike']:g} {lg['right']}")
    print("║")
    print(f"║ QUANTITY      {t['quantity']} contracts")
    print(f"║ LIMIT         ${t['limit_net_credit']:.2f} net CREDIT (at the mid)")
    print(f"║ MAX LOSS      ${t['max_loss_per_contract']:,.0f}/contract · ${t['total_risk']:,} total "
          f"({t['pct_of_sleeve']}% of the 0DTE sleeve)")
    print(f"║ STOP          {t['stop']}")
    print(f"║ TIME STOP     {t['time_stop']}")
    print(f"╚═ {t['note']}")
    if t.get("write_error"):
        print(f"!! ticket.json was NOT updated: {t['write_error']}")
    print("\nAfter it fills:  venv/bin/python3 ticket.py fill <credit_per_contract> <contracts>")
