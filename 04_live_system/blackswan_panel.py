"""Black Swan tab — stocks coiled for a big move, and the cheap convex play on them.

The scan is driven by whatever `scripts/bigmove_hunt.py` found to actually raise
P(large move) above the base rate — the screens are read from that study's
output rather than hardcoded from intuition, so the tab changes when the
evidence does.

Two things are shown together on every candidate and neither is optional:

  LIFT — how much this setup raises the probability of a >=3-sigma move versus
         that name's own base rate. This is the selection claim, quantified.
  SPREAD — the measured bid-ask as a % of premium on the contract being
         suggested. Far-OTM buying is roughly break-even at <=20% spread and
         a bleed above it (measured: all far-OTM -45.6%, spread<=20% +5.6%).
         So the spread filter is not a detail, it IS the strategy.

Contracts are sized to a $100-300 budget across many names, per the intended
use: several small convex bets where one large winner carries the rest.
"""
import json
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
BM = os.path.join(ROOT, "data", "bigmove")
CACHE = os.path.join(ROOT, "data", "blackswan_scan.json")

# Measured on real quotes: buying far-OTM is a bleed at wide spreads and roughly
# a coin flip once execution cost is controlled. This is the single most
# important number on the panel.
SPREAD_OK = 0.20
MAX_SPREAD_SHOWN = 0.35


def _uw_overlay(sym):
    """UW-derived score for a candidate, weighted by measured accuracy.

    The move screens say a name is COILED; this says whether the positioning
    data leans for or against it. Short interest enters negatively because that
    is how it measured (IC -0.068 at 21d), not how it feels.
    """
    try:
        import uw_endpoints as ue, signal_weights as sw
        p = ue.profile(sym)
        if not p:
            return None
        vals = {}
        if p.get("flow_lean") is not None:
            vals["flow_lean"] = max(-1, min(1, float(p["flow_lean"])))
        if p.get("dp_buy_share") is not None:
            vals["dp_buy_share"] = (float(p["dp_buy_share"]) - 0.5) * 2
        if p.get("short_float_pct") is not None:
            vals["short_float_pct"] = min(float(p["short_float_pct"]) / 20.0, 1.0)
        if p.get("insider_open_buys"):
            vals["insider_open_buys"] = min(float(p["insider_open_buys"]) / 3.0, 1.0)
        return sw.combine(vals) if vals else None
    except Exception:
        return None


def _load_screens():
    """Screens that beat the base rate in the study, best lift first."""
    p = os.path.join(BM, "screens.json")
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _panel():
    p = os.path.join(BM, "panel.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else None


def _chain_for(syms):
    """Live chains for the candidates, from the local DoltHub clone.

    Real bid/ask and delta, so the strike shown is the strike that exists and
    the spread shown is the spread that will actually be paid.
    """
    import subprocess
    from io import StringIO
    if not syms:
        return pd.DataFrame()
    dolt = os.path.join(ROOT, "data", "dolt")
    lst = ",".join(f"'{x}'" for x in syms)

    def run(sql, timeout=300):
        r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"], cwd=dolt,
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0 or not r.stdout.strip():
            return pd.DataFrame()
        return pd.read_csv(StringIO(r.stdout))

    try:
        # Resolve the latest date FIRST. Inlining it as a subquery alongside a
        # 24-symbol IN list made the planner scan the full 114M-row table and
        # blow the timeout, which silently returned "no chain" for every name.
        m = run("select max(`date`) as d from options.option_chain")
        if m.empty:
            return pd.DataFrame()
        latest = str(m.iloc[0, 0])
        return run(f"select act_symbol,`date`,expiration,strike,call_put,"
                   f"bid,ask,vol,delta from options.option_chain "
                   f"where `date`='{latest}' and act_symbol in ({lst})")
    except Exception:
        return pd.DataFrame()


def _ticket(ch, sym):
    """The contract the evidence points at: 10-16 delta CALL, ~30-50 DTE.

    That band is where two independent measurements agree the market
    underprices the tail (implied 15.55% vs realised 26.18% ITM) and where the
    unconditional mean was positive (+4.7% at 10-16d, +26.1% at 16-30d) --
    unlike the 1-2 delta contracts, which the market overcharges by ~3x.
    """
    c = ch[(ch.act_symbol == sym) & (ch.call_put == "Call")].copy()
    if c.empty:
        return None
    c["expiration"] = pd.to_datetime(c["expiration"])
    c["dte"] = (c["expiration"] - pd.Timestamp(c["date"].iloc[0])).dt.days
    c = c[(c.dte.between(25, 60)) & c.delta.notna() & (c.bid > 0) & (c.ask > c.bid)]
    if c.empty:
        return None
    # Nearest expiry to the 42-day horizon that tested strongest.
    exp = c.iloc[(c.dte - 42).abs().argsort()].iloc[0].expiration
    c = c[c.expiration == exp]
    band = c[c.delta.between(0.10, 0.16)]
    if band.empty:
        band = c[c.delta.between(0.05, 0.25)]
    if band.empty:
        return None
    row = band.iloc[(band.delta - 0.13).abs().argsort()].iloc[0]
    mid = (float(row.bid) + float(row.ask)) / 2
    if mid <= 0:
        return None
    spread = (float(row.ask) - float(row.bid)) / mid
    return {"strike": float(row.strike), "exp": str(pd.Timestamp(exp).date()),
            "dte": int((pd.Timestamp(exp) - pd.Timestamp(row["date"])).days),
            "delta": round(float(row.delta), 3), "bid": float(row.bid),
            "ask": float(row.ask), "spread": round(spread, 3),
            "cost": round(float(row.ask) * 100, 2),
            "tradeable": spread <= SPREAD_OK}


def scan(force=False):
    """Today's candidates: names whose current state matches a surviving screen."""
    if os.path.exists(CACHE) and not force:
        try:
            with open(CACHE) as f:
                c = json.load(f)
            if c.get("date") == str(date.today()):
                return c
        except Exception:
            pass

    screens = _load_screens()
    d = _panel()
    if d is None or not screens:
        return {"date": str(date.today()), "candidates": [], "screens": screens}

    # Latest row per ticker at the 21-day horizon.
    d = d[d.H == 21].sort_values("date")
    latest = d.groupby("ticker").tail(1)

    cands = []
    for _, r in latest.iterrows():
        hits = []
        for s in screens:
            try:
                if eval(s["expr"], {"x": r, "np": np, "pd": pd}):
                    hits.append(s)
            except Exception:
                continue
        if not hits:
            continue
        best = max(hits, key=lambda s: s.get("lift3", 0))
        cands.append({
            "ticker": r["ticker"],
            "screens": [h["name"] for h in hits],
            "lift": round(float(best.get("lift3", 1)), 2),
            "p3": round(float(best.get("p3", 0)) * 100, 2),
            "base3": round(float(best.get("base3", 0)) * 100, 2),
            "sig": round(float(r.get("sig", 0)) * 100, 2),
            "frm_hi": round(float(r.get("frm_hi", 0)) * 100, 1),
            "rv_pct": round(float(r.get("rv21_pct", 0)) * 100),
        })
    cands.sort(key=lambda c: -c["lift"])
    cands = cands[:24]

    # Attach a real, quotable contract to each candidate.
    ch = _chain_for([c["ticker"] for c in cands])
    for c in cands:
        c["ticket"] = _ticket(ch, c["ticker"]) if not ch.empty else None
        ov = _uw_overlay(c["ticker"])
        if ov:
            c["uw_score"] = ov["score"]
            c["uw_conf"] = ov["confidence"]
    # Tradeable spread first -- it is the difference between +5.6% and -45.6%.
    cands.sort(key=lambda c: (not (c.get("ticket") or {}).get("tradeable", False),
                              -c["lift"]))
    out = {"date": str(date.today()), "candidates": cands, "screens": screens}
    try:
        with open(CACHE, "w") as f:
            json.dump(out, f, indent=1)
    except Exception:
        pass
    return out


def blackswan_panel():
    try:
        s = scan()
    except Exception:
        return ""
    cands, screens = s.get("candidates", []), s.get("screens", [])

    if not screens:
        body = ('<div class="pend">The big-move study has not produced a surviving '
                'screen yet. Until a setup demonstrably raises P(3&sigma;) above the '
                'base rate, this tab shows nothing rather than guessing &mdash; a '
                'random far-OTM basket measured <b>&minus;45.6%</b>.</div>')
        rows = ""
    else:
        top = screens[0]
        body = (f'<div class="lede">Best surviving screen: <b>{top["name"]}</b> '
                f'&mdash; raises P(3&sigma; move in 21d) from '
                f'<b>{top["base3"]*100:.2f}%</b> to <b>{top["p3"]*100:.2f}%</b> '
                f'(<b>{top["lift3"]:.2f}&times;</b> lift).</div>')
        rows = "".join(f"""
      <tr class="{'ok' if (c.get('ticket') or {}).get('tradeable') else 'wide'}">
        <td class="tk">{c['ticker']}</td>
        <td class="tix">{(f"{c['ticket']['strike']:g}C " + c['ticket']['exp']) if c.get('ticket') else '&mdash;'}</td>
        <td class="num">{f"{c['ticket']['dte']}d" if c.get('ticket') else '&mdash;'}</td>
        <td class="num">{f"{c['ticket']['delta']:.2f}" if c.get('ticket') else '&mdash;'}</td>
        <td class="num"><b>{f"${c['ticket']['cost']:,.0f}" if c.get('ticket') else '&mdash;'}</b></td>
        <td class="num {'g' if (c.get('ticket') or {}).get('tradeable') else 'r'}">
          {f"{c['ticket']['spread']*100:.0f}%" if c.get('ticket') else '&mdash;'}</td>
        <td class="num"><b>{c['lift']:.2f}&times;</b></td>
        <td class="num">{c['p3']:.2f}%</td>
        <td class="sc">{', '.join(c['screens'][:2])}</td></tr>""" for c in cands)

    n_ok = sum(1 for c in cands if (c.get("ticket") or {}).get("tradeable"))
    table = "" if not cands else f"""
  <div class="cnt"><b>{n_ok}</b> of {len(cands)} candidates have a spread you can
    actually trade (&le;20%). The rest are shown greyed &mdash; the spread is the
    difference between +5.6% and &minus;45.6%, so a wide one is not a cheap ticket,
    it is a bad one.</div>
  <table>
    <thead><tr><th>ticker</th><th>BUY</th><th>dte</th><th>&delta;</th>
      <th>cost</th><th>spread</th><th>lift</th><th>P(3&sigma;)</th><th>setup</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>"""

    return f"""
<section class="card" id="bswan">
  <h2>Black Swan &mdash; coiled for a move</h2>
  <div class="sub">Names whose current state matches a setup that <b>measurably</b>
    raises the odds of a large move. Screens come from the study, not intuition.</div>
  {body}
  {table}
  <div class="rules">
    <b>Execution rules, from the measurements &mdash; these decide the outcome:</b>
    <ul>
      <li><b>Spread &le; 20% of mid, or skip it.</b> All far-OTM = <b>&minus;45.6%</b>;
        filtered to &le;20% spread = <b>+5.6%</b>. The spread <i>is</i> the strategy.
        70% of far-OTM contracts fail this &mdash; expect to reject most candidates.</li>
      <li><b>10&ndash;16 delta, not 2&ndash;5.</b> Measured mean by bucket:
        ultra&nbsp;&lt;2&delta; &minus;90%, 2&ndash;5&delta; &minus;48%,
        10&ndash;16&delta; <b>+4.7%</b>, 16&ndash;30&delta; <b>+26.1%</b>.
        Cheaper is worse, because spread scales inversely with price.</li>
      <li><b>Calls over puts.</b> Puts were negative in every bucket &mdash; upward
        drift plus a permanently bid put skew.</li>
      <li><b>Do not screen on cheap IV.</b> Every cheapness filter <i>reduced</i> the
        mean. Cheap IV is the market correctly forecasting quiet.</li>
      <li><b>Not through earnings.</b> Straddles into a print measured
        <b>&minus;35.0%</b> (t&nbsp;=&nbsp;&minus;95.7): earnings lift P(2&sigma;)
        but <i>lower</i> P(3&sigma;) &mdash; a 2&sigma; event at a 3&sigma; price.</li>
    </ul>
  </div>
<style>
 #bswan{{--ok:#16a34a;--bad:#dc2626;--ln:rgba(128,128,128,.16);--mut:rgba(128,128,128,.72)}}
 #bswan h2{{font-size:16px;margin:0 0 2px}}
 #bswan .sub{{font-size:12px;color:var(--mut);margin-bottom:10px}}
 #bswan .lede{{font-size:12.5px;padding:9px 11px;border-radius:8px;
   background:rgba(22,163,74,.10);border-left:3px solid var(--ok);margin-bottom:10px}}
 #bswan .pend{{font-size:12px;color:var(--mut);padding:11px 13px;border-radius:8px;
   background:rgba(128,128,128,.09);line-height:1.55}}
 #bswan table{{width:100%;border-collapse:collapse;font-size:12px}}
 #bswan th{{text-align:right;padding:5px 7px;color:var(--mut);font-weight:600;
   border-bottom:1px solid var(--ln)}}
 #bswan th:first-child,#bswan th:last-child{{text-align:left}}
 #bswan td{{padding:4px 7px;text-align:right;font-variant-numeric:tabular-nums;
   border-bottom:1px solid rgba(128,128,128,.07)}}
 #bswan td.tk{{text-align:left;font-weight:700}}
 #bswan td.sc{{text-align:left;font-size:10.5px;color:var(--mut)}}
 #bswan td.tix{{text-align:left;font-family:ui-monospace,Menlo,monospace;font-size:11px;
   font-weight:600}}
 #bswan tr.wide{{opacity:.42}}
 #bswan tr.ok td.tix{{color:var(--ok)}}
 #bswan .g{{color:var(--ok);font-weight:700}} #bswan .r{{color:var(--bad)}}
 #bswan .cnt{{font-size:11.5px;color:var(--mut);margin:8px 0 6px;line-height:1.5}}
 #bswan td.mut{{color:var(--mut)}}
 #bswan .rules{{margin-top:12px;font-size:11.5px;line-height:1.6;padding:10px 12px;
   border-radius:8px;background:rgba(180,83,9,.09);border-left:3px solid #b45309}}
 #bswan .rules ul{{margin:6px 0 0;padding-left:17px}}
 #bswan .rules li{{margin-bottom:4px}}
</style>
</section>"""


if __name__ == "__main__":
    s = scan(force=True)
    print(f"screens: {len(s['screens'])}  candidates: {len(s['candidates'])}")
    for c in s["candidates"][:12]:
        print(f"  {c['ticker']:6s} lift {c['lift']:.2f}x  P3 {c['p3']:.2f}%  "
              f"{', '.join(c['screens'][:2])}")
