"""dashboard.py — SPX/NDX day-trading dashboard (stdlib http, no deps). Port 8091.

Two honest sections:
  1. OVERNIGHT EDGE — the one real backtested strategy + today's action.
  2. LEVELS — objective intraday structure for discretionary trades (not auto signals).
Reads data/snapshot.json (refreshed by build_snapshot.py under launchd).
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

SNAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "snapshot.json")
PORT = 8091


def load():
    try:
        return json.load(open(SNAP))
    except Exception:
        return {"as_of": "no snapshot — run build_snapshot.py", "phase": "-",
                "overnight_action": "-", "overnight": {}, "levels": []}


def lv_row(label, val, hi=False):
    cls = " class=hl" if hi else ""
    return f"<tr{cls}><td>{label}</td><td class=num>{val if val is not None else '—'}</td></tr>"


def levels_card(lv):
    if "error" in lv:
        return f"<div class=card><b>{lv.get('index','?')}</b><div class=mut>data unavailable: {lv['error']}</div></div>"
    price = lv.get("price")
    rows = [lv_row("Price", price, hi=True)]
    if lv.get("phase") == "session":
        pos = f"{lv.get('vs_vwap','')} VWAP · {lv.get('vs_or15','')} opening range"
        rows += [
            lv_row("VWAP", lv.get("vwap")),
            lv_row("VWAP +2σ", lv.get("vwap_up")),
            lv_row("VWAP −2σ", lv.get("vwap_dn")),
            lv_row("Opening range 15m", f"{lv.get('or15_low')} – {lv.get('or15_high')}"),
            lv_row("Opening range 30m", f"{lv.get('or30_low')} – {lv.get('or30_high')}"),
            lv_row("Session H / L", f"{lv.get('sess_high')} / {lv.get('sess_low')}"),
        ]
    else:
        pos = f"{lv.get('phase','')}"
    rows += [
        lv_row("Prior close", lv.get("prior_close")),
        lv_row("Prior day H / L", f"{lv.get('prior_high')} / {lv.get('prior_low')}"),
        lv_row("Opening gap", f"{lv.get('gap_pct')}%"),
    ]
    gt = lv.get("gap_tendency")
    gt_html = (f"<div class=tend>After a gap like today's, this index has historically closed "
               f"the session <b>{'up' if gt['intraday_mean']>0 else 'down'} {abs(gt['intraday_mean']):.2f}%</b> "
               f"on average ({gt['intraday_win']:.0f}% of days, n={gt['n']}).</div>" if gt else "")
    return f"""<div class=card>
      <div class=cardhead><span class=idx>{lv['index']}</span>
        <span class=mut>via {lv['etf']} ×{lv['ratio']}</span></div>
      <div class=pos>{pos}</div>
      <table class=lv>{''.join(rows)}</table>{gt_html}</div>"""


def zero_dte_card(z):
    if not z:
        return ""
    rows = ""
    for p in z["plans"]:
        rows += (f"<div class=plan><div class=plantag>{p['tag']} — shorts ±{p['short_dist_pct']:.2f}%"
                 f" <span class=mut>(win ~{p['win_1130']}% @11:30 · ~{p['win_1330']}% @13:30)</span></div>"
                 f"<div class=legs>Sell <b>{p['short_put']:.0f}P</b> / Buy {p['long_put']:.0f}P"
                 f" &nbsp;+&nbsp; Sell <b>{p['short_call']:.0f}C</b> / Buy {p['long_call']:.0f}C</div>"
                 f"<div class=mut>{z['index']} stays between {p['short_put']:.0f} and {p['short_call']:.0f} → keep credit ·"
                 f" wings {p['wing']:.0f} wide = defined risk</div></div>")
    return f"""<div class=card>
      <div class=cardhead><span class=idx>{z['index']}</span>
        <span class=mut>0DTE exp {z['expiry']} · spot {z['spot']}</span></div>{rows}</div>"""


def render():
    s = load()
    on = s.get("overnight", {})
    ostat = lambda tk: on.get(tk, {})
    q, sp = ostat("QQQ"), ostat("SPY")
    lvls = "".join(levels_card(l) for l in s.get("levels", []))
    zdte = "".join(zero_dte_card(z) for z in s.get("zero_dte", []))
    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<meta http-equiv=refresh content=180>
<title>SPX / NDX Day-Trading</title>
<style>
 body{{background:#0d1117;color:#e6edf3;font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px;max-width:1000px;margin:auto}}
 h1{{font-size:22px;margin:0 0 2px}} h2{{font-size:14px;text-transform:uppercase;letter-spacing:.09em;color:#8b949e;margin:26px 0 10px;border-bottom:1px solid #21262d;padding-bottom:6px}}
 .mut{{color:#8b949e;font-size:13px}} .banner{{background:#161b22;border:1px solid #30363d;border-left:3px solid #d29922;border-radius:8px;padding:12px 16px;margin:14px 0;font-size:13px}}
 .action{{background:#161b22;border:1px solid #30363d;border-left:3px solid #3fb950;border-radius:10px;padding:16px 18px;font-size:17px;font-weight:600}}
 .kpi{{display:inline-block;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:8px 14px;margin:8px 10px 0 0;font-size:13px}} .kpi b{{font-size:16px}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} @media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
 .card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px}}
 .cardhead{{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}} .idx{{font-size:20px;font-weight:700}}
 .pos{{color:#58a6ff;font-size:13px;margin-bottom:8px}}
 table.lv{{width:100%;border-collapse:collapse;font-size:14px}} table.lv td{{padding:5px 4px;border-bottom:1px solid #21262d}} td.num{{text-align:right;font-family:ui-monospace,Menlo,monospace}}
 tr.hl td{{font-weight:700;font-size:16px}} .tend{{margin-top:10px;font-size:12px;color:#8b949e}}
 .plan{{border-top:1px solid #21262d;padding:10px 0 4px}} .plan:first-of-type{{border-top:none}}
 .plantag{{font-weight:600;text-transform:capitalize;margin-bottom:5px}}
 .legs{{font-family:ui-monospace,Menlo,monospace;font-size:14px;background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:8px;margin:4px 0}}
 .danger{{background:#161b22;border:1px solid #30363d;border-left:3px solid #f85149;border-radius:8px;padding:12px 16px;margin:12px 0;font-size:13px}}
 .exec{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin:12px 0;font-size:13px}}
</style></head><body>
<h1>SPX / NDX Day-Trading Dashboard</h1>
<div class=mut>{s.get('as_of')} &middot; phase: {s.get('phase')}</div>

<div class=banner><b>The honest truth first.</b> I backtested every major intraday pattern (opening-range breakout,
gap fade, VWAP reversion & momentum, day-of-week) on 21y daily + 2y minute data. <b>None had a robust,
significant edge net of costs</b> — intraday index direction is a coin flip, which is why most day-traders lose.
So this dashboard does two honest things instead: (1) the ONE real edge — the overnight drift — and (2) objective
<b>levels</b> to structure a discretionary trade. The levels are context and risk points, <b>not</b> buy/sell signals.</div>

<h2>1 · The overnight edge — today's action</h2>
<div class=action>{s.get('overnight_action')}</div>
<div class=exec>
  <b>How to place it (SHARES — this edge is not an options trade):</b>
  {"".join(f"<div class=legs>{e['shares']} shares of <b>{e['etf']}</b> @ ${e['price']} = ${e['cost']:.0f} &middot; BUY at 4:00pm close, SELL at 9:30am open</div>" for e in s.get('overnight_exec', []))}
  <div class=mut>No strikes / no expiration by design: the average overnight move (~0.03%) is far smaller than any option
  bid/ask spread, so selling/buying options to express this would guarantee a loss. Hold the shares overnight, go flat at the open.</div>
</div>
<div style=margin-top:10px>
  <span class=kpi>QQQ overnight &nbsp;Sharpe <b>{q.get('sharpe','—')}</b></span>
  <span class=kpi>CAGR <b>{q.get('cagr','—')}%</b></span>
  <span class=kpi>maxDD <b>{q.get('maxdd','—')}%</b></span>
  <span class=kpi>win <b>{q.get('win','—')}%</b></span>
  <span class=kpi>SPY CAGR <b>{sp.get('cagr','—')}%</b></span>
  <span class=kpi>intraday-only CAGR <b>{q.get('intraday_cagr','—')}%</b> (why day-trading fails)</span>
</div>
<div class=mut style=margin-top:8px>Strategy: buy the index ETF (or MOC) at the 4:00pm close, sell at the 9:30am open, sit out the day.
{q.get('n_years','~22')}y backtest, net of costs. Real but modest — and the opposite of scalping. Size to what a −31% drawdown lets you sleep through.</div>

<h2>2 · 0DTE iron condor — expiration &amp; strikes</h2>
<div class=danger><b>Read before selling a single one.</b> These are DEFINED-RISK condors (max loss = wing width − credit,
capped). The win rates are real and measured on 2y of intraday moves — but a high win rate is NOT the same as profit:
you collect a small credit ~85-94% of the time and lose the FULL wing on the rare trend day. Positive expectancy holds
ONLY if the live credit is fair (I can't verify that without intraday option prices — check the credit when you place it).
Sell LATER in the day (1-2pm) for higher win rates once the range is set. Size so one max-loss can't hurt you. This is the
"pick up pennies in front of a steamroller" trade — respect it.</div>
<div class=grid>{zdte}</div>

<h2>3 · Live levels — structure for a discretionary trade</h2>
<div class=grid>{lvls}</div>
<p class=mut style=margin-top:14px>How to use: these are the objective lines the session pivots around. Longs work better <b>above</b> VWAP &amp; the
opening-range high; shorts <b>below</b>. Prior-day and session extremes are where reversals and breakouts happen. Use them
to place entries and stops with defined risk — the edge is in your risk management, not a prediction. No signal here is
backtested to make money. Educational research, not financial advice.</p>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_response(404); self.end_headers(); return
        b = render().encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"SPX/NDX day-trading dashboard -> http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
