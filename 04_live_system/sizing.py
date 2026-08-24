"""sizing.py — turn a priced structure into an actual contract count for THIS account.

This is the piece that makes the growth plan real rather than aspirational. Everything upstream decides
*what* to trade; this decides *how much*, and it is the single biggest determinant of whether an account
compounds or dies. It is deliberately conservative and deliberately loud when a trade simply does not fit.

Rules, in priority order:
 1. HARD CAP FIRST. Risk per trade may never exceed growth_plan.RISK_CAP['max_risk_per_trade_pct'] of the
    account. This is checked against the structure's real max loss, not a guess.
 2. Conviction and the growth-plan aggression can only SHRINK size from that cap, never grow past it.
    (Being behind the curve is not a reason to risk more — it's a reason to be more selective.)
 3. Contracts round DOWN. A trade that cannot afford one contract is reported as UNAFFORDABLE rather than
    quietly sized to zero — a small account being unable to trade a given instrument is information the
    trader needs, not an edge case to swallow.
"""
import os
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

# option contracts are per-100 shares/index points
MULT = 100

# conviction -> fraction of the hard cap actually used. Never exceeds 1.0.
def _conviction_frac(conv):
    conv = max(0, min(100, int(conv or 0)))
    if conv >= 85:
        return 1.00
    if conv >= 75:
        return 0.80
    if conv >= 66:
        return 0.60
    return 0.35


# growth-plan aggression -> multiplier. PROTECT trims; LEAN-IN does NOT add (by design).
AGGR_MULT = {"PROTECT": 0.6, "ON-TRACK": 1.0, "LEAN-IN": 1.0}


def size_trade(max_loss_per_contract, conviction, account=None, aggression=None, size_hint=None,
               sleeve=None, sleeve_cap_pct=None):
    """max_loss_per_contract: in PREMIUM POINTS (e.g. 9.1 for a $910 spread). Returns a dict.

    When `sleeve` is given, capital and the risk cap come from that sleeve rather than the whole
    account — the whole point of splitting capital is that one strategy cannot spend the other's."""
    try:
        import growth_plan
        aggr = aggression or growth_plan.status()["aggression"]
    except Exception:
        aggr = aggression or "ON-TRACK"
    if sleeve:
        try:
            import sleeves
            b = sleeves.budget(sleeve)
            acct = float(account if account is not None else b["capital"])
            cap_pct = float(sleeve_cap_pct if sleeve_cap_pct is not None else b["max_risk_pct"])
        except Exception:
            acct = float(account or 5000)
            cap_pct = float(sleeve_cap_pct or 12.0)
    else:
        try:
            import growth_plan
            acct = float(account if account is not None else growth_plan.get_account())
            cap_pct = float(sleeve_cap_pct if sleeve_cap_pct is not None
                            else growth_plan.RISK_CAP["max_risk_per_trade_pct"])
        except Exception:
            acct = float(account or 5000)
            cap_pct = float(sleeve_cap_pct or 12.0)

    if not max_loss_per_contract or max_loss_per_contract <= 0:
        return {"contracts": 0, "ok": False, "reason": "no max-loss available — cannot size honestly"}

    risk_per_contract = float(max_loss_per_contract) * MULT
    hard_cap_dollars = acct * cap_pct / 100.0

    frac = _conviction_frac(conviction) * AGGR_MULT.get(aggr, 1.0)
    if (size_hint or "").lower() == "small":
        frac *= 0.5
    frac = min(frac, 1.0)
    budget = hard_cap_dollars * frac

    contracts = int(budget // risk_per_contract)      # round DOWN, always
    afford_one = risk_per_contract <= hard_cap_dollars

    if contracts < 1:
        if not afford_one:
            reason = (f"UNAFFORDABLE — one contract risks ${risk_per_contract:,.0f}, which exceeds the "
                      f"hard cap of ${hard_cap_dollars:,.0f} ({cap_pct:.0f}% of ${acct:,.0f}). "
                      f"This instrument is too large for the account at this width.")
        else:
            reason = (f"sized to zero — one contract (${risk_per_contract:,.0f}) exceeds this trade's "
                      f"conviction-adjusted budget of ${budget:,.0f}. Needs higher conviction or a "
                      f"narrower structure.")
        return {"contracts": 0, "ok": False, "reason": reason,
                "risk_per_contract": round(risk_per_contract), "hard_cap": round(hard_cap_dollars),
                "budget": round(budget), "account": round(acct), "affordable": afford_one}

    total_risk = contracts * risk_per_contract
    return {"contracts": contracts, "ok": True,
            "risk_per_contract": round(risk_per_contract),
            "total_risk": round(total_risk),
            "pct_of_account": round(total_risk / acct * 100, 1),
            "hard_cap": round(hard_cap_dollars), "budget": round(budget),
            "account": round(acct), "aggression": aggr, "affordable": True,
            "reason": f"{contracts}x risking ${total_risk:,.0f} ({total_risk/acct*100:.1f}% of account), "
                      f"within the {cap_pct:.0f}% cap"}


def affordability_report(account=None):
    """Which instruments can this account actually trade? Run at any time for a reality check."""
    try:
        import option_pricer as OP
        import yfinance as yf
    except Exception:
        return []
    import warnings
    warnings.filterwarnings("ignore")
    rows = []
    probes = [("SPX", "0DTE", 25), ("NDX", "0DTE", 100), ("SPY", "0DTE", 2), ("QQQ", "0DTE", 2)]
    for sym, exp_kind, width in probes:
        try:
            spot = float(yf.Ticker(OP._yf(sym)).fast_info["lastPrice"])
            exp = OP.resolve_expiry(sym, exp_kind)
            if not exp:
                continue
            step = 5 if sym in ("SPX",) else (25 if sym == "NDX" else 1)
            k = round(spot / step) * step
            r = OP.price_structure(sym, exp, [{"right": "C", "strike": k, "qty": 1},
                                              {"right": "C", "strike": k + width, "qty": -1}])
            if r.get("net") is None:
                continue
            s = size_trade(r.get("max_loss"), 80, account=account)
            rows.append({"sym": sym, "width": width, "net": r["net"],
                         "risk_per_contract": s.get("risk_per_contract"),
                         "contracts": s.get("contracts"), "ok": s["ok"], "reason": s["reason"]})
        except Exception:
            continue
    return rows


def prompt_block(account=None):
    """Tell the agent, in dollars, what it can actually hold — and which vehicle to use.

    The dealer-gamma board is built on SPX/NDX, but at a small account size a single SPX or NDX spread
    breaches the per-trade risk cap outright. The signal still comes from the index; the EXPRESSION has
    to be the ETF. Without this the agent proposes trades that can never be taken."""
    try:
        import growth_plan
        acct = float(account if account is not None else growth_plan.get_account())
        cap_pct = float(growth_plan.RISK_CAP["max_risk_per_trade_pct"])
    except Exception:
        acct, cap_pct = float(account or 5000), 12.0
    cap = acct * cap_pct / 100.0
    return (
        f"POSITION SIZING REALITY (account ${acct:,.0f}, hard cap {cap_pct:.0f}% = ${cap:,.0f} risk per trade). "
        f"Option contracts are 100x, so max loss per contract = net debit x 100. "
        f"THE 0DTE TRADING UNIVERSE IS SPY AND QQQ ONLY — this is enforced, not advisory. A single SPX "
        f"0DTE condor risks about $2,375 and NDX far more, both beyond the cap, so any 0DTE proposal on "
        f"SPX, NDX or any other symbol is refused outright. "
        f"Read the dealer-gamma board on SPX/NDX as you always have — that stays the SIGNAL source — then "
        f"EXPRESS the trade in the ETF: SPY for the SPX board (SPY ~= SPX/10, so an SPX level of 7740 is "
        f"SPY ~774) and QQQ for the NDX board (QQQ ~= NDX/41). Convert the gamma flip and call/put walls "
        f"to ETF terms the same way. Keep widths tight ($1-$3) so a contract fits the cap. Any proposal "
        f"whose one-contract risk exceeds ${cap:,.0f} is auto-rejected before it reaches the book."
    )


if __name__ == "__main__":
    print(prompt_block())
    print("\n── AFFORDABILITY: what can this account actually trade? ──")
    for r in affordability_report():
        flag = "✓" if r["ok"] else "✗"
        print(f"  {flag} {r['sym']:4s} {r['width']}-wide debit spread: net {r['net']:.2f} "
              f"(${r['risk_per_contract']:,}/contract) -> {r['contracts']} contracts")
        if not r["ok"]:
            print(f"       {r['reason']}")
