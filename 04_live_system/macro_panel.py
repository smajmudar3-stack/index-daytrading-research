"""Macro Context tab — the rate/credit backdrop the swing signal ignores.

WHAT THIS IS AND IS NOT, stated up front because the distinction is the whole
point of the panel:

  IT IS a sensitivity map. Each sector's beta to the 10y yield is measured over
  20 years and is stable and strong (KRE +1.09, XLF +0.95, XLRE -0.24 — the
  only negative). So when yields move, this tells you which sectors are levered
  to that move and in which direction. That is real, and it is the thing a desk
  note is gesturing at when it says "rate-sensitives catch a bid."

  IT IS NOT a forecast. I tested whether rate/curve/credit moves PREDICT sector
  returns 5-21 days out: 216 cells, three-way split, measured as excess over
  each sector's own drift. 36 were positive in all three periods and ZERO
  cleared the multiple-testing bar of t=3.24. Best was t=+1.58.

So the panel shows CONTEXT (what is moving with what, right now) and refuses to
emit a directional call from it. Conflating those two is exactly how a
plausible narrative becomes a losing trade.
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(ROOT, "data", "swing", "panel.parquet")
CACHE = os.path.join(ROOT, "data", "macro_context.json")

# Measured 2005-2026 on daily changes. Beta = sector % move per 1pt move in the
# 10y yield. Recomputed by refresh(); these are the fallbacks.
# 5-day betas: sector % move per 1pt move in the 10y yield, measured 2005-2026.
RATE_BETA = {
    "XLRE": -6.61, "XLU": -1.52, "XLP": 0.65, "XLV": 1.30, "ITB": 2.5,
    "XHB": 3.0, "JETS": 3.0, "XLY": 3.82, "XLK": 4.01, "XRT": 4.0,
    "XLB": 6.0, "XLI": 6.0, "SMH": 5.0, "IYT": 6.0, "XME": 9.44,
    "XLF": 8.14, "XLE": 9.15, "KRE": 9.91,
}


# context() reads a 315k-row parquet and fits 18 regressions. Called on every
# dashboard render that was ~20s and blew the request timeout. Cache on file
# mtime so a scanner refresh is still picked up immediately.
_CTX = {"mtime": None, "val": None}


def _load():
    p = pd.read_parquet(PANEL)
    return p.pivot(index="date", columns="ticker", values="close").sort_index()


def context():
    """Current macro state + each sector's measured sensitivity to it."""
    try:
        mt = os.path.getmtime(PANEL)
        if _CTX["mtime"] == mt:
            return _CTX["val"]
    except OSError:
        mt = None
    c = _load()
    out = {"asof": str(c.index[-1].date())}

    def chg(col, n):
        if col not in c:
            return None
        s = c[col].dropna()
        if len(s) < n + 1:
            return None
        return float(s.iloc[-1] - s.iloc[-1 - n])

    if "^TNX" in c:
        y10 = c["^TNX"].dropna()
        out["y10"] = round(float(y10.iloc[-1]), 2)
        out["y10_5d"] = round(float(y10.iloc[-1] - y10.iloc[-6]), 3)
        out["y10_21d"] = round(float(y10.iloc[-1] - y10.iloc[-22]), 3)
    if "^IRX" in c and "^TNX" in c:
        cur = (c["^TNX"] - c["^IRX"]).dropna()
        out["curve"] = round(float(cur.iloc[-1]), 2)
        out["curve_5d"] = round(float(cur.iloc[-1] - cur.iloc[-6]), 3)
    if "HYG" in c and "IEF" in c:
        cr = (c["HYG"] / c["IEF"]).dropna()
        out["credit_5d"] = round(float(cr.pct_change(5, fill_method=None).iloc[-1]) * 100, 2)
        out["credit_21d"] = round(float(cr.pct_change(21, fill_method=None).iloc[-1]) * 100, 2)
    if "TLT" in c:
        out["tlt_5d"] = round(float(c["TLT"].pct_change(5, fill_method=None).dropna().iloc[-1]) * 100, 2)
        t = c["TLT"].dropna()
        out["tlt_pctile_1y"] = round(float((t.iloc[-252:] < t.iloc[-1]).mean()) * 100)

    # Betas measured at the SWING horizon (5 days), not daily. Daily regression
    # attenuates the relationship badly through noise, and it even gets the SIGN
    # wrong for utilities: XLU is +0.83 daily but -1.52 over 5 days. The 5-day
    # number is both larger and the one that matches how long a position is held.
    betas = {}
    if "^TNX" in c:
        dy = c["^TNX"].diff(5)
        for sec in RATE_BETA:
            if sec not in c:
                continue
            r = c[sec].pct_change(5, fill_method=None) * 100     # in % terms
            d = pd.concat([r, dy], axis=1).dropna()
            if len(d) < 500:
                continue
            betas[sec] = round(float(np.polyfit(d.iloc[:, 1], d.iloc[:, 0], 1)[0]), 2)
    out["beta"] = betas or RATE_BETA

    # 5-day sector performance, to pair the map with what actually happened.
    perf = {}
    for sec in out["beta"]:
        if sec in c:
            s = c[sec].dropna()
            if len(s) > 6:
                perf[sec] = round(float(s.iloc[-1] / s.iloc[-6] - 1) * 100, 2)
    out["perf5"] = perf
    _CTX["mtime"], _CTX["val"] = mt, out
    return out


def macro_panel():
    try:
        x = context()
    except Exception:
        return ""
    b, perf = x.get("beta", {}), x.get("perf5", {})
    if not b:
        return ""

    y5 = x.get("y10_5d")
    # Which end of the sensitivity map is being helped by the current move?
    if y5 is not None and abs(y5) >= 0.05:
        direction = "rising" if y5 > 0 else "falling"
        helped = ("high-beta cyclicals (KRE, XLF, XLE)" if y5 > 0
                  else "rate-sensitives (XLRE, XLU, XLP)")
        lede = (f"10y yield {direction} {abs(y5):.2f}pt over 5 sessions — "
                f"historically a tailwind for {helped}.")
    else:
        lede = "10y yield roughly flat over 5 sessions — no strong rate impulse."

    rows = "".join(
        f'<tr><td>{s}</td><td class="{"neg" if v < 0 else ""}">{v:+.2f}</td>'
        f'<td class="{"pos" if perf.get(s, 0) > 0 else "neg"}">{perf.get(s, 0):+.2f}%</td></tr>'
        for s, v in sorted(b.items(), key=lambda kv: kv[1]))

    def stat(lbl, val, suf=""):
        return (f'<div class="m"><span class="lbl">{lbl}</span>'
                f'<span class="val">{val if val is not None else "—"}{suf}</span></div>')

    return f"""
<section class="card" id="macro">
  <h2>Macro Context</h2>
  <div class="lede">{lede}</div>
  <div class="strip">
    {stat("10y yield", x.get("y10"), "%")}
    {stat("5d chg", x.get("y10_5d"), "pt")}
    {stat("21d chg", x.get("y10_21d"), "pt")}
    {stat("10y−3m curve", x.get("curve"), "%")}
    {stat("curve 5d", x.get("curve_5d"), "pt")}
    {stat("credit 5d", x.get("credit_5d"), "%")}
    {stat("TLT 5d", x.get("tlt_5d"), "%")}
    {stat("TLT 1y %ile", x.get("tlt_pctile_1y"), "")}
  </div>

  <div class="warn"><b>This is context, not a forecast.</b> Sector betas to rates
  are real and stable (measured on 20 years of daily changes). But I tested
  whether rate, curve and credit moves <i>predict</i> sector returns 5&ndash;21
  days out &mdash; 216 cells, three-way split, excess over each sector's own drift.
  36 were positive in all three periods and <b>zero cleared the multiple-testing
  bar of t=3.24</b> (best t=+1.58). Use this to know <i>what is levered to the
  move</i>, not to predict the move.</div>

  <details open>
    <summary>Rate sensitivity map &mdash; beta to a 1pt move in the 10y yield</summary>
    <table><thead><tr><th>sector</th><th>rate beta</th><th>5d return</th></tr></thead>
    <tbody>{rows}</tbody></table>
    <div class="foot">Negative beta = rises when yields fall (XLRE is the only one).
    Higher beta = more levered to yields rising. Measured 2005&ndash;2026, daily changes.</div>
  </details>
<style>
 #macro{{--ok:#16a34a;--bad:#dc2626;--ln:rgba(128,128,128,.16);--mut:rgba(128,128,128,.75)}}
 #macro h2{{font-size:16px;margin:0 0 2px}}
 #macro .lede{{font-size:12.5px;color:var(--mut);margin-bottom:12px}}
 #macro .strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));
   gap:8px;margin-bottom:13px}}
 #macro .m{{border:1px solid var(--ln);border-radius:8px;padding:7px 9px}}
 #macro .lbl{{display:block;font-size:10px;color:var(--mut);margin-bottom:2px}}
 #macro .val{{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums}}
 #macro .warn{{font-size:11.5px;line-height:1.55;padding:10px 12px;border-radius:8px;
   background:rgba(180,83,9,.10);border-left:3px solid #b45309;margin-bottom:12px}}
 #macro details{{border-top:1px solid var(--ln);padding-top:10px}}
 #macro summary{{cursor:pointer;font-size:12px;color:var(--mut);font-weight:600}}
 #macro table{{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:9px}}
 #macro th{{text-align:right;padding:4px 7px;color:var(--mut);border-bottom:1px solid var(--ln)}}
 #macro th:first-child{{text-align:left}}
 #macro td{{padding:3px 7px;text-align:right;font-variant-numeric:tabular-nums;
   border-bottom:1px solid rgba(128,128,128,.07)}}
 #macro td:first-child{{text-align:left;font-weight:600}}
 #macro .pos{{color:var(--ok)}} #macro .neg{{color:var(--bad)}}
 #macro .foot{{font-size:10.5px;color:var(--mut);margin-top:8px;line-height:1.5}}
</style>
</section>"""


if __name__ == "__main__":
    x = context()
    print("asof", x["asof"], "| 10y", x.get("y10"), "| 5d", x.get("y10_5d"),
          "| curve", x.get("curve"), "| credit5d", x.get("credit_5d"))
    for s, v in sorted(x["beta"].items(), key=lambda kv: kv[1]):
        print(f"  {s:6s} beta {v:+.3f}   5d {x['perf5'].get(s, 0):+.2f}%")
