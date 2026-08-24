"""Structure Edge panel — every structure's REAL backtested evidence, on the board.

Reads the backtest artifacts produced by scripts/structure_lab.py and
scripts/strategy_eval.py (real SPY bid/ask, 2008-2025, 147,350 de-duplicated
trades) and renders a verdict per structure.

Design rule for this panel: **win rate and expectancy are always shown
together, never win rate alone.** That pairing is the whole point. A 75.7% win
rate on a put credit spread sits next to −12.84% per trade, and seeing the two
side by side is what stops the board recommending a structure that wins often
and loses money. The prior dashboard shouted high win rates with no expectancy
attached, which is exactly how the retracted +3.7% condor stayed live for a week.

A structure is only marked TRADE if it clears BOTH gates:
  win rate >= 60%   AND   expectancy > 0 after real bid/ask.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
TRADES = os.path.join(ROOT, "data", "swing", "structure_trades.parquet")
CACHE = os.path.join(ROOT, "data", "structure_edge.json")

# Thesis text per structure — why it should or should not work, in plain terms.
THESIS = {
    "iron condor 30/16":
        "Sells both wings for a credit and wants the market pinned. Crosses 8 spreads "
        "round-trip, which is ~10% of capital at risk before the market does anything. "
        "CBOE's own condor index (CNDR) has lost money since 2010.",
    "iron condor 16/05":
        "The wide, high-win-rate version. Wins ~2 of every 3 trades and still loses money: "
        "the credit collected is smaller than the average loss it eventually takes. This is "
        "the clearest example on the board of win rate and expectancy pointing opposite ways.",
    "iron butterfly ATM":
        "Short straddle with wings. Maximum theta but the body is at the money, so it needs "
        "the market to sit almost exactly still. Loses more than half the time.",
    "jade lizard":
        "Short put plus a short call spread. The advertised feature is 'no upside risk' when "
        "the credit exceeds the call-spread width — true, and irrelevant, because the "
        "downside is naked and that is where the loss lives.",
    "twisted sister":
        "Mirror of the jade lizard: no downside risk, naked upside. Closest to break-even of "
        "the credit family, but the edge is not distinguishable from zero.",
    "broken-wing fly (put)":
        "Butterfly with the far wing pushed out for a credit. The credit does not make one "
        "side riskless — it moves the loss, it does not remove it.",
    "christmas tree call":
        "1-3-2 ratio. Worst performer of everything tested: the 3 short calls carry more risk "
        "than the ratio's profit zone pays for, and it crosses 6 spreads.",
    "put credit 30/16":
        "Bullish credit spread. Needs roughly 67-80% directional accuracy just to break even, "
        "which is above what any signal here delivers.",
    "put credit 16/05":
        "The high-win-rate favourite. 3 of 4 trades win. It still loses, because the 1 in 4 "
        "loses far more than the 3 make.",
    "call credit 30/16":
        "Bearish credit spread. Fights the market's structural upward drift as well as the spread.",
    "short strangle 16d":
        "Naked both sides at 16 delta. Undefined risk, margin-heavy, and the win rate is bought "
        "one-for-one with tail severity — the worst month in the record is −2523% of credit.",
    "short strangle 30d": "Tighter naked strangle. Same trade, more gamma, more often wrong.",
    "short straddle":
        "Pure short volatility at the money. The academic literature says this is the ONE "
        "premium structure with a real edge — but only DELTA-HEDGED. Naked, it is ~80% a bet "
        "on the size of the move, not on volatility.",
    "ZEBRA call 70/50":
        "2 ITM calls against 1 short ATM call — near-zero extrinsic, so it tracks the stock "
        "without paying much time value. This is the structure the research actually supports "
        "for a directional view, because a direction-only signal belongs in a linear payoff.",
    "ZEBRA call 80/50": "Deeper ZEBRA. Same logic, closer to owning shares outright.",
    "call debit 70/30":
        "Buy 0.70 delta, sell 0.30. Highest win rate of any directional structure tested "
        "(67-68%) and the cheapest way to express an up-view without paying full extrinsic.",
    "call debit 50/30": "ATM debit spread. Slightly more return, slightly lower win rate.",
    "long call 0.80d": "Deep ITM call — mostly intrinsic, behaves close to shares.",
    "long call 0.16d":
        "The lottery ticket. Wins under 4 times in 10 and drew down 96-99% in testing. "
        "The most commonly bought structure and the worst.",
}

DIRECTIONAL = {"ZEBRA call 70/50", "ZEBRA call 80/50", "call debit 70/30",
               "call debit 50/30", "long call 0.80d", "long call 0.70d",
               "long call 0.50d", "long call 0.30d", "long call 0.16d"}


def compute(force=False):
    """Aggregate the trade-level backtest into per-structure evidence."""
    if os.path.exists(CACHE) and not force:
        try:
            with open(CACHE) as f:
                return json.load(f)
        except Exception:
            pass
    if not os.path.exists(TRADES):
        return []

    import pandas as pd

    d = pd.read_parquet(TRADES).drop_duplicates(
        subset=["date", "structure", "dte", "hold_frac"])

    out = []
    for name, g in d.groupby("structure"):
        if len(g) < 100:
            continue
        r = g.ret
        se = r.std() / (len(r) ** 0.5)
        out.append({
            "structure": name,
            "n": int(len(r)),
            "win": float((r > 0).mean()),
            "avg": float(r.mean()),
            "med": float(r.median()),
            "t": float(r.mean() / se) if se > 0 else 0.0,
            "worst": float(r.min()),
            "kind": "directional" if name in DIRECTIONAL else "premium",
        })

    out.sort(key=lambda x: -x["avg"])
    try:
        with open(CACHE, "w") as f:
            json.dump(out, f, indent=1)
    except Exception:
        pass
    return out


def _verdict(e):
    """Both gates must pass. Win rate alone never earns a TRADE.

    The mean alone is not enough either. Long-premium structures show a large
    POSITIVE mean driven by a handful of crash payoffs while the median outcome
    is a total loss -- a distribution nobody can actually sit through at retail
    size. So a structure whose median is worse than -50% is flagged LOTTERY
    regardless of its mean.
    """
    if e["med"] < -0.50 and e["avg"] > 0:
        return "LOTTERY", "#7c3aed"   # positive mean, but you lose on most trades
    if e["win"] >= 0.60 and e["avg"] > 0:
        return "TRADE", "#16a34a"
    if e["avg"] > 0:
        return "MARGINAL", "#ca8a04"
    if e["win"] >= 0.60:
        return "TRAP", "#dc2626"      # wins often, loses money
    return "AVOID", "#dc2626"




# ---------------------------------------------------------------------------
# Rendering. Design rule: the panel answers three questions in order —
#   1. Is there a trade right now?   2. What is it?   3. Why should I believe it?
# Anything that never changes (structure evidence, thesis text) is reference,
# not signal, and lives behind one collapsed block at the bottom.
# ---------------------------------------------------------------------------
_CSS = """
<style>
 #desk{--ok:#16a34a;--no:#64748b;--warn:#b45309;--bad:#dc2626;
   --ln:rgba(128,128,128,.16);--mut:rgba(128,128,128,.75)}
 #desk h2{font-size:16px;margin:0 0 2px}
 #desk .lede{font-size:12px;color:var(--mut);margin-bottom:14px}
 #desk .status{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
   padding:13px 15px;border-radius:10px;margin-bottom:16px;
   background:rgba(100,116,139,.10);border-left:3px solid var(--no)}
 #desk .status.live{background:rgba(22,163,74,.11);border-left-color:var(--ok)}
 #desk .status .verdict{font-size:15px;font-weight:700;letter-spacing:-.2px}
 #desk .status .why{font-size:12px;color:var(--mut);line-height:1.5;flex:1;min-width:240px}
 #desk .gate{display:flex;gap:18px;font-size:11.5px;flex-wrap:wrap;margin-top:2px}
 #desk .gate span{white-space:nowrap}
 #desk .gate b{font-variant-numeric:tabular-nums}
 #desk .yes{color:var(--ok);font-weight:700} #desk .nah{color:var(--no);font-weight:700}
 #desk .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(238px,1fr));gap:11px}
 #desk .c{border:1px solid var(--ln);border-radius:10px;padding:12px 13px}
 #desk .c .top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:9px}
 #desk .c .sym{font-size:14px;font-weight:700;letter-spacing:-.2px}
 #desk .c .px{font-size:13px;font-variant-numeric:tabular-nums;color:var(--mut)}
 #desk .c .pill{font-size:9.5px;font-weight:700;letter-spacing:.5px;padding:2px 8px;
   border-radius:20px;color:#fff;background:var(--no)}
 #desk .c.go .pill{background:var(--ok)}
 #desk .tkt{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;
   line-height:1.55;padding:8px 9px;border-radius:7px;background:rgba(128,128,128,.07);
   margin-bottom:8px}
 #desk .meta{display:flex;gap:12px;font-size:11px;color:var(--mut);
   font-variant-numeric:tabular-nums;flex-wrap:wrap}
 #desk .meta b{color:inherit;opacity:.95}
 #desk .idle{font-size:11.5px;color:var(--mut);line-height:1.5}
 #desk .bar{height:3px;border-radius:2px;background:rgba(128,128,128,.18);margin-top:9px}
 #desk .bar i{display:block;height:100%;border-radius:2px;background:var(--ok)}
 #desk .stale{background:var(--warn);color:#fff;font-size:9.5px;font-weight:700;
   padding:1px 6px;border-radius:9px;margin-left:6px}
 #desk details{margin-top:16px;border-top:1px solid var(--ln);padding-top:11px}
 #desk summary{cursor:pointer;font-size:12px;color:var(--mut);font-weight:600}
 #desk table{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:10px}
 #desk th{text-align:right;padding:5px 7px;color:var(--mut);font-weight:600;
   border-bottom:1px solid var(--ln)}
 #desk th:first-child{text-align:left}
 #desk td{padding:4px 7px;border-bottom:1px solid rgba(128,128,128,.07);
   font-variant-numeric:tabular-nums;text-align:right}
 #desk td:first-child{text-align:left;font-weight:600}
 #desk .g{color:var(--ok)} #desk .r{color:var(--bad)}
 @media(max-width:560px){#desk .grid{grid-template-columns:1fr}}
</style>"""


def _card(a):
    """One symbol. Ticket if there is a trade, one plain line if not."""
    recs, sym = a["recommendations"], a["symbol"]
    stale = ('<span class="stale">SIGNAL %dd OLD</span>'
             % a["state"].get("signal_age_days", 0)) if a["state"].get("stale") else ""

    if recs:
        r = recs[0]
        body = (f'<div class="tkt">{r["legs"]}<br>{r["expiry"]} &middot; hold {r["hold"]}</div>'
                f'<div class="meta"><span>risk <b>${r["max_risk"]:,}</b></span>'
                f'<span>win <b>{r["win"]:.0%}</b></span>'
                f'<span>edge <b>{r["exp"]:+.0%}</b></span>'
                f'<span>conv <b>{r["conviction"]}</b></span></div>'
                f'<div class="bar"><i style="width:{r["conviction"]}%"></i></div>')
        cls = "c go"
        pill = "TRADE"
    else:
        best = a.get("below_floor") or []
        nxt = (f' Closest is {best[0]["structure"]} at conviction '
               f'{best[0]["conviction"]}, below the floor of {a["min_conviction"]}.') if best else ""
        body = f'<div class="idle">No setup meets the bar.{nxt}</div>'
        cls, pill = "c", "STAND DOWN"

    return (f'<div class="{cls}"><div class="top"><span class="sym">{sym}{stale}</span>'
            f'<span class="px">{a["spot"]:,.2f}</span>'
            f'<span class="pill">{pill}</span></div>{body}</div>')


def desk_panel():
    """The decision panel — replaces the old advisor + evidence tables."""
    try:
        import spx_ndx_advisor as adv
    except Exception:
        return ""

    cards, states, any_trade = [], [], False
    for sym in adv.SYMBOLS:
        try:
            a = adv.advise(sym)
        except Exception:
            continue
        if a.get("error"):
            continue
        cards.append(_card(a))
        states.append(a)
        any_trade = any_trade or bool(a["recommendations"])
    if not cards:
        return ""

    st = states[0]["state"]
    back, gold = st.get("backwardation"), st.get("golden")
    ratio = st.get("ts_ratio", 0)

    if any_trade:
        verdict, why = "TRADE ON", "Entry condition met. Tickets below are sized to budget."
    else:
        missing = []
        if not back:
            missing.append(f"VIX/VIX3M is {ratio:.3f} (needs ≥ 1.00 — backwardation)")
        if not gold:
            missing.append("50dma is below the 200dma (needs a golden cross)")
        verdict = "STAND DOWN"
        why = ("Waiting on: " + "; ".join(missing) +
               ". This fires on volatility spikes — a handful of times a year, "
               "not weekly. Sitting out is the strategy working, not a fault.")

    gate = (f'<div class="gate">'
            f'<span>VIX <b>{st.get("vix",0):.2f}</b></span>'
            f'<span>VIX3M <b>{st.get("vix3m",0):.2f}</b></span>'
            f'<span>ratio <b>{ratio:.3f}</b> '
            f'<span class="{"yes" if back else "nah"}">{"BACKWARD" if back else "CONTANGO"}</span></span>'
            f'<span>golden cross <span class="{"yes" if gold else "nah"}">'
            f'{"YES" if gold else "NO"}</span></span>'
            f'<span>GEX z <b>{st.get("gex_z")}</b></span>'
            f'<span>DIX z <b>{st.get("dix_z")}</b></span></div>')

    ev = sorted(compute(), key=lambda x: -x["avg"])
    rows = "".join(
        f'<tr><td>{e["structure"]}</td><td>{e["win"]:.0%}</td>'
        f'<td class="{"g" if e["avg"]>0 else "r"}">{e["avg"]:+.1%}</td>'
        f'<td class="{"g" if e["med"]>0 else "r"}">{e["med"]:+.0%}</td>'
        f'<td>{e["t"]:+.0f}</td><td>{_verdict(e)[0]}</td></tr>' for e in ev)

    return f"""
<section class="card" id="desk">
  <h2>Trade Desk</h2>
  <div class="lede">Signal, structure and size &mdash; from 147,350 real-quote trades
    (SPY 2008&ndash;2025, filled at ask, exited at bid). Negative-expectancy structures
    cannot appear here.</div>
  <div class="status{' live' if any_trade else ''}">
    <span class="verdict">{verdict}</span>
    <span class="why">{why}</span>
  </div>
  {gate}
  <div class="grid" style="margin-top:14px">{''.join(cards)}</div>
  <details>
    <summary>Evidence &mdash; every structure tested, and why the blocked ones are blocked</summary>
    <table><thead><tr><th>structure</th><th>win</th><th>mean</th><th>median</th>
      <th>t</th><th>verdict</th></tr></thead><tbody>{rows}</tbody></table>
  </details>
{_CSS}
</section>"""
