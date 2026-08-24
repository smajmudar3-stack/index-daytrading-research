"""mes_dashboard.py — merged MES/MNQ system dashboard (stdlib http). Port 8092.
Overnight signal is the precise headline. '/refresh' re-pulls live data on demand.
Design: token-based, high-signal, responsive, a11y-reviewed. Purpose unchanged."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import mes_signals

SNAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mes_snapshot.json")
PORT = 8093
PH_ACT = {"pre_close": "overnight", "post_close": "overnight", "weekend": "overnight",
          "open": "gap", "pre_open": "gap", "session": "dip"}


def load():
    try:
        return json.load(open(SNAP))
    except Exception:
        return None


def firmness_meter(f):
    """5-dot meter (also labelled in text, so not colour-only)."""
    if f is None:
        return ""
    filled = min(5, max(1, int(f)))
    dots = "".join(f"<span class='dot {'on' if i < filled else ''}'></span>" for i in range(5))
    label = "rock-solid" if f > 3 else ("firm" if f > 1.5 else "marginal — watch the close")
    return f"<div class=firm><span class=meter aria-hidden=true>{dots}</span><span>Firmness {f:.1f} · {label}</span></div>"


def overnight_card(s):
    if "OVERNIGHT" not in s:
        return (f"<article class='card big empty'><div class=idx>{s.get('fut','?')}</div>"
                f"<p class=muted>Data unavailable{': '+s['error'] if s.get('error') else ''}. Press Update.</p></article>")
    hold = s["OVERNIGHT"]
    state = "hold" if hold else "flat"
    pill = f"<span class='pill {state}'>{'●' if hold else '○'} {'HOLD OVERNIGHT' if hold else 'STAY FLAT'}</span>"

    def cond(ok, label, val, note):
        mark = "✓" if ok else "✗"
        return (f"<li class='cond {'pass' if ok else 'fail'}'>"
                f"<span class=cmark aria-hidden=true>{mark}</span>"
                f"<span class=clabel>{label}</span>"
                f"<span class=cval>{val}</span>"
                f"<span class='cnote {'pos' if ok else 'neg'}'>{note}</span></li>")

    conds = (cond(s["above200"], "Above 200-day", f"{s['price']:g} / {s['sma200']:g}", f"{s['sma_margin']:+.1f}%")
             + cond(s["vix_ok"], "VIX calm (&lt;20d·1.2)", f"{s['vix_now']:g} / {s['vix_thr']:g}", f"{s['vix_margin']:+.0f}% room"))
    action = (f"Buy 1 <b>{s['fut']}</b> at the 4:00pm close · sell at the 9:30am open."
              if hold else "Both gates must pass — one is off. No overnight position.")
    return f"""<article class='card big {state}' aria-label='{s['fut']} overnight signal'>
      <header class=cardhead>
        <div><span class=idx>{s['fut']}</span> <span class=sub>{s['name']} · ${s['dollar']:g}/pt</span></div>
        {pill}
      </header>
      <ul class=conds>{conds}</ul>
      {firmness_meter(s['firmness']) if hold else ''}
      <p class='action {state}'>{'→ ' if hold else ''}{action}</p>
    </article>"""


def intraday_card(s):
    if "OVERNIGHT" not in s:
        return ""
    def row(active, label, val, on_txt, off_txt):
        st = "on" if active else "off"
        return (f"<li class='irow {st}'><span class=clabel>{label}</span>"
                f"<span class=cval>{val}</span>"
                f"<span class='tag {st}'>{'●' if active else '○'} {on_txt if active else off_txt}</span></li>")
    return f"""<article class=card aria-label='{s['fut']} intraday overlays'>
      <header class=cardhead><span class=idx>{s['fut']}</span></header>
      <ul class=conds>
        {row(s['GAP_FADE'], 'Gap-fade', f"gap {s['gap']:+.2f}%", 'FADE: buy open→close', 'no down-gap')}
        {row(s['DIP_BUY'], 'RSI-2 dip-buy', f"RSI2 {s['rsi2']:g}", 'BUY dip → exit RSI2&gt;60', 'no dip')}
      </ul>
    </article>"""


def render():
    d = load()
    if not d or not d.get("signals"):
        body = "<div class=hint role=status>No data yet. Press <b>Update</b> to pull live signals.</div>"
        cards_on = cards_id = ""
        as_of, ph, epoch = "—", "-", 0
    else:
        sigs = d["signals"]
        cards_on = "".join(overnight_card(s) for s in sigs)
        cards_id = "".join(intraday_card(s) for s in sigs)
        as_of, ph, epoch = d.get("as_of", "—"), d.get("phase", "-"), d.get("epoch", 0)
        act = PH_ACT.get(ph, "overnight")
        hint = {"overnight": "Act on the <b>OVERNIGHT</b> signal now — decide at ~3:55pm ET.",
                "gap": "Act on <b>GAP-FADE</b> now — at the open.",
                "dip": "Watch <b>DIP-BUY</b> (RSI-2) into the close."}[act]
        body = f"<div class=hint role=status>{hint}</div>"

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<meta http-equiv=refresh content=120>
<title>MES / MNQ System Signals</title>
<style>
 :root{{
   --bg:#0d1117; --surface:#161b22; --surface2:#1c2129; --line:#2a3038; --line2:#21262d;
   --text:#e6edf3; --muted:#9aa4b2; --go:#3fb950; --go-bg:#12261a; --off:#7d8590;
   --warn:#e3b341; --info:#58a6ff; --danger:#f85149;
   --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --r:12px;
   --fs-hero:clamp(20px,4vw,26px); --shadow:0 1px 3px rgba(0,0,0,.4);
 }}
 *{{box-sizing:border-box;min-width:0}}
 html,body{{overflow-x:hidden;max-width:100%}}
 body{{background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;padding:var(--s5);max-width:960px;margin-inline:auto;-webkit-font-smoothing:antialiased}}
 h1{{font-size:var(--fs-hero);margin:0;letter-spacing:-.01em}}
 h2{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:var(--s6) 0 var(--s3);display:flex;align-items:center;gap:var(--s2);flex-wrap:wrap}}
 h2 span{{flex:0 1 auto}} h2::after{{content:'';flex:1 1 40px;height:1px;background:var(--line2)}}
 .cval,.cnote{{overflow-wrap:anywhere}}
 .muted{{color:var(--muted);font-size:13px}}
 /* top bar */
 .top{{display:flex;justify-content:space-between;align-items:center;gap:var(--s3);flex-wrap:wrap}}
 .fresh{{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);margin-top:2px}}
 .fdot{{width:8px;height:8px;border-radius:50%;background:var(--go)}}
 .fdot.stale{{background:var(--warn)}}
 .btn{{background:var(--go);color:#04130a;border:none;border-radius:10px;padding:10px 18px;font-size:14px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px;transition:filter .15s}}
 .btn:hover{{filter:brightness(1.08)}}
 .btn:focus-visible{{outline:3px solid var(--info);outline-offset:2px}}
 .btn.loading{{pointer-events:none;opacity:.7}}
 .spin{{width:14px;height:14px;border:2px solid rgba(4,19,10,.4);border-top-color:#04130a;border-radius:50%;animation:sp .7s linear infinite;display:none}}
 .btn.loading .spin{{display:inline-block}} .btn.loading .btxt{{opacity:.6}}
 @keyframes sp{{to{{transform:rotate(360deg)}}}}
 @media(prefers-reduced-motion:reduce){{.spin{{animation:none}}}}
 /* hint */
 .hint{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--info);border-radius:10px;padding:var(--s3) var(--s4);margin:var(--s4) 0;font-size:13.5px}}
 /* grid + cards */
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:var(--s4)}}
 @media(max-width:680px){{.grid{{grid-template-columns:1fr}}}}
 .card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:var(--s4);box-shadow:var(--shadow)}}
 .card.big{{padding:var(--s5)}}
 .card.big.hold{{border-color:rgba(63,185,80,.5);background:linear-gradient(180deg,var(--go-bg),var(--surface) 60%)}}
 .card.big.flat{{border-color:var(--line)}}
 .card.empty{{opacity:.75}}
 .cardhead{{display:flex;align-items:center;gap:var(--s3);flex-wrap:wrap;margin-bottom:var(--s3)}}
 .idx{{font-size:20px;font-weight:800;letter-spacing:-.01em}} .sub{{color:var(--muted);font-size:12.5px}}
 .pill{{margin-left:auto;font-size:12.5px;font-weight:800;letter-spacing:.02em;padding:5px 13px;border-radius:99px;white-space:nowrap}}
 .pill.hold{{background:var(--go);color:#04130a}} .pill.flat{{background:var(--surface2);color:var(--off);border:1px solid var(--line)}}
 /* condition checklist */
 .conds{{list-style:none;margin:0;padding:0}}
 .cond,.irow{{display:grid;grid-template-columns:auto 1fr auto;gap:var(--s2) var(--s3);align-items:center;padding:9px 0;border-bottom:1px solid var(--line2)}}
 .cond{{grid-template-columns:auto 1fr auto auto}}
 .cond:last-child,.irow:last-child{{border-bottom:none}}
 .cmark{{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:13px;font-weight:800}}
 .cond.pass .cmark{{background:rgba(63,185,80,.18);color:var(--go)}}
 .cond.fail .cmark{{background:rgba(248,81,73,.18);color:var(--danger)}}
 .clabel{{font-size:13.5px}} .cval{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--muted);text-align:right}}
 .cnote{{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;font-weight:700;text-align:right;min-width:74px}}
 .cnote.pos{{color:var(--go)}} .cnote.neg{{color:var(--danger)}}
 .tag{{font-size:11.5px;font-weight:700;padding:3px 9px;border-radius:99px;white-space:nowrap}}
 .tag.on{{background:var(--go);color:#04130a}} .tag.off{{background:var(--surface2);color:var(--off);border:1px solid var(--line)}}
 /* firmness meter */
 /* narrow-screen reflow: stack everything so nothing can force width past the viewport */
 @media(max-width:560px){{
   body{{padding:14px}} .card.big{{padding:var(--s4)}}
   .top{{flex-direction:column;align-items:stretch}} .btn{{justify-content:center}}
   .cardhead{{margin-bottom:var(--s2)}} .pill{{margin-left:0;order:3;flex-basis:100%;text-align:center;white-space:normal}}
   .action{{overflow-wrap:anywhere;font-size:13px}} .card,article,.hint{{max-width:100%}}
   .cond{{grid-template-columns:auto 1fr;row-gap:1px}}
   .cond .clabel,.cond .cval,.cond .cnote{{grid-column:2;text-align:left}}
   .cond .cval{{font-size:11.5px;color:var(--muted)}}
   .irow{{grid-template-columns:1fr}} .irow .cval{{color:var(--muted)}} .irow .tag{{justify-self:start}}
   h2{{font-size:11px;display:block;letter-spacing:.04em}} h2::after{{display:none}}
 }}
 .firm{{display:flex;align-items:center;gap:var(--s2);margin-top:var(--s3);font-size:12.5px;color:var(--muted)}}
 .meter{{display:inline-flex;gap:4px}} .dot{{width:9px;height:9px;border-radius:50%;background:var(--line)}} .dot.on{{background:var(--go)}}
 /* action */
 .action{{margin:var(--s3) 0 0;font-size:14px;font-weight:600}} .action.hold{{color:var(--text)}} .action.flat{{color:var(--muted);font-weight:500}}
 footer{{margin-top:var(--s6);color:var(--muted);font-size:12px;line-height:1.6}}
</style></head><body>
<header class=top>
  <div>
    <h1>MES / MNQ System Signals</h1>
    <div class=fresh><span id=fdot class=fdot></span><span id=freshtxt>updated {as_of}</span> · phase {ph}</div>
  </div>
  <a class=btn id=upd href='/refresh' aria-label='Update signals with live data'>
    <span class=spin aria-hidden=true></span><span class=btxt>🔄 Update now</span>
  </a>
</header>
{body}

<h2><span>Overnight — the anchor · 75% of the system</span></h2>
<div class=grid>{cards_on}</div>
<p class=muted style='margin-top:var(--s3)'>Decide at ~3:55pm ET — <b>both</b> gates must pass (✓). This is the real edge:
Nasdaq Sharpe ~2.2 alone, 22-of-22 positive years merged. Size so a −5% overnight gap survives (1 micro, or unleveraged shares).</p>

<h2><span>Intraday overlays · gap-fade 15% · dip-buy 10%</span></h2>
<div class=grid>{cards_id}</div>

<footer>
  Merged system: MNQ Sharpe 2.30 · CAGR 19.5% · maxDD −7% · 22/22 positive years. Rules &amp; backtest in MES_STRATEGY.md.<br>
  Signals are mechanical (live price + VIX, may lag ~15 min) — verify near the close. Educational research, not financial advice.
</footer>
<script>
 // update-button loading state
 var b=document.getElementById('upd');
 if(b) b.addEventListener('click',function(){{b.classList.add('loading');b.querySelector('.btxt').textContent='Updating…';}});
 // relative freshness + stale flag (client-side, no server round-trip)
 (function(){{
   var epoch={epoch or 0}; if(!epoch) return;
   var dot=document.getElementById('fdot'), txt=document.getElementById('freshtxt');
   function upd(){{
     var age=Math.max(0,(Date.now()/1000)-epoch), m=Math.floor(age/60);
     txt.textContent = age<60?'updated just now':('updated '+m+'m ago');
     if(age>900) dot.classList.add('stale'); else dot.classList.remove('stale');
   }}
   upd(); setInterval(upd,30000);
 }})();
</script>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/refresh"):
            try:
                mes_signals.run()
            except Exception:
                pass
            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
        if self.path not in ("/", "/index.html"):
            self.send_response(404); self.end_headers(); return
        b = render().encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"MES/MNQ system dashboard -> http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
