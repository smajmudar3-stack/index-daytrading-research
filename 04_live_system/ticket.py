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

This module never places an order and holds no credentials.
"""
import os
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "ticket.json")
DB = os.path.join(HERE, "data", "agent_trades.db")


def build(sym=None):
    """Produce today's ticket if — and only if — every gate agrees the setup is live."""
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
        json.dump(t, open(OUT, "w"), indent=2, default=str)
    except Exception:
        pass
    return t


def record_fill(credit, contracts, sym=None, expiry=None, strikes=None):
    """Log an ACTUAL fill so the track record becomes measurement rather than model.

    credit: net credit per contract you actually received (e.g. 0.47)."""
    import rules
    sym = sym or rules.PRODUCT
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, sym TEXT,
        action TEXT, structure TEXT, legs TEXT, size TEXT, conviction INT, expiry TEXT, thesis TEXT,
        est_prem REAL, entry_under REAL, status TEXT DEFAULT 'open', exit_under REAL, exit_ts TEXT, pnl_pct REAL)""")
    cols = {r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()}
    for col, ddl in (("peak_fav", "REAL DEFAULT 0"), ("pnl_real_pct", "REAL"), ("exit_prem", "REAL")):
        if col not in cols:
            c.execute(f"ALTER TABLE trades ADD COLUMN {col} {ddl}")
    spot = None
    try:
        import ai_trader
        spot = ai_trader._spot(sym)
    except Exception:
        pass
    c.execute("""INSERT INTO trades(ts,sym,action,structure,legs,size,conviction,expiry,thesis,
        est_prem,entry_under,status) VALUES(?,?,?,?,?,?,?,?,?,?,?, 'open')""",
              (datetime.now(ET).isoformat(timespec="seconds"), sym, "ENTER", "IRON_CONDOR",
               f"REAL FILL {strikes or ''}", str(contracts), 80, "0DTE",
               "live fill of the validated condor", -abs(float(credit)), spot))
    c.commit()
    tid = c.execute("SELECT last_insert_rowid() id").fetchone()[0]
    c.close()
    return {"logged": True, "trade_id": tid, "credit": credit, "contracts": contracts}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fill":
        # usage: ticket.py fill <credit_per_contract> <contracts>
        print(record_fill(float(sys.argv[2]), int(sys.argv[3])))
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
    print("\nAfter it fills:  venv/bin/python3 ticket.py fill <credit_per_contract> <contracts>")
