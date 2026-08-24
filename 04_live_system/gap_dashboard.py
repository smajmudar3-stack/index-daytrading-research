"""gap_dashboard.py — unified Day + Swing signal-giver. Port 8094.
Sections: (1) desk analyst read (Fable, rule-based fallback), (2) intraday gap-and-go + paper
tracker, (3) swing-trade signals with options structures + thesis. '/refresh' runs scan_all."""
import json
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer
import edge_panel
import blackswan_panel
import scorecard

ET = ZoneInfo("America/New_York")

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = os.path.join(HERE, "data", "gap_snapshot.json")
SWING = os.path.join(HERE, "data", "swing_snapshot.json")
GEX = os.path.join(HERE, "data", "gex_snapshot.json")
PERI_SPX = os.path.join(HERE, "data", "periscope_SPX.json")
PERI_NDX = os.path.join(HERE, "data", "periscope_NDX.json")
PORT = 8094


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def _market_open():
    n = datetime.now(ET)
    return n.weekday() < 5 and (n.hour * 60 + n.minute) >= 570 and (n.hour * 60 + n.minute) < 960  # 9:30-16:00 ET


def freshness_banner():
    """Show the age of each live data source; warn RED if stale during market hours."""
    now = time.time()
    src = [("periscope", PERI_SPX, 6), ("gap scan", GAP, 8), ("gamma regime", GEX, 90), ("swing", SWING, 40)]
    parts = []
    worst = "ok"
    for label, path, limit_min in src:
        if not os.path.exists(path):
            parts.append(f"<span class='fchip bad'>{label}: missing</span>"); worst = "bad"; continue
        age = (now - os.path.getmtime(path)) / 60
        stale = _market_open() and age > limit_min
        cls = "bad" if stale else "ok"
        if stale:
            worst = "bad"
        parts.append(f"<span class='fchip {cls}'>{label}: {age:.0f}m</span>")
    mkt = "MARKET OPEN" if _market_open() else "market closed"
    head = ("🟢 LIVE" if worst == "ok" else "🔴 STALE — hit Update")
    # Explicit, unmissable session state. When closed, nothing that costs money is running and the
    # numbers below are last session's — the banner has to say so rather than looking merely quiet.
    try:
        import session as _S
        st = _S.status_line()
        if not st["open"]:
            tone = "warm" if st["phase"] == "warmup" else "shut"
            return (f"<div class='fbar closed {tone}'><b>{st['label']}</b>"
                    f"<div class=fsub>All Fable calls are paused until the 09:20 ET warm-up — the board "
                    f"below is last session's. Ages: {''.join(parts)}</div></div>")
        return (f"<div class='fbar {worst}'><b>{head}</b> · {st['label']} · scanner every 5 min "
                f"{''.join(parts)}</div>")
    except Exception:
        pass
    if not _market_open():
        head = "⚪ " + mkt + " — data refreshes next session"
    return (f"<div class='fbar {worst}'><b>{head}</b> · scanner runs every 5 min · "
            f"<span class=fmkt>{mkt}</span> {''.join(parts)}</div>")


def cand_card(c):
    go = c["setup"] == "GAP-AND-GO LONG"; col = "go" if go else "info"
    return f"""<article class='card cand {col}'>
      <header class=chead><span class=tk>{c['ticker']}</span><span class='pill {col}'>{c['setup']}</span></header>
      <div class=metrics>
        <div><span class=k>Gap</span><span class='v {'g' if c['gap_pct']>0 else 'r'}'>{c['gap_pct']:+.1f}%</span></div>
        <div><span class=k>Rel Vol</span><span class=v>{c['rvol']}×</span></div>
        <div><span class=k>Open</span><span class=v>${c['open']:g}</span></div>
        <div><span class=k>Since open</span><span class='v {'g' if c['since_open_pct']>0 else 'r'}'>{c['since_open_pct']:+.1f}%</span></div>
      </div><div class=play>▶ Buy at open · sell at close (paper first)</div>
      <div class=optplay>📄 {c.get('option_play','')}</div></article>"""


def swing_card(s):
    dcol = {"bullish": "go", "bearish": "red", "neutral": "mut"}[s["direction"]]
    st = s.get("structure", {})
    iv = s.get("iv")
    ivtxt = f"IV {iv['iv']:.0f}% vs RV {s['rvol']:.0f}%" if iv else "IV n/a"
    conv = s["conviction"]
    bar = f"<div class=convbar><span style='width:{conv}%' class='cfill {dcol}'></span></div>"
    return f"""<article class='card swing {dcol}'>
      <header class=chead><span class=tk>{s['ticker']}</span>
        <span class='pill {dcol}'>{s['direction'].upper()}</span>
        <span class=conv>conv {conv}/100</span></header>
      {bar}
      <div class=meta>{s['timeframe']} · mom {s['m60']:+.0f}%/3mo · RSI {s['rsi']:.0f} · {s['frm_hi']:+.0f}% frm hi · {ivtxt}</div>
      <div class=stru><b>{st.get('play','—')}</b></div>
      <div class=legs>{st.get('legs','—')}<span class=exp> · {st.get('exp','')}</span></div>
      <div class=thesis>{s.get('thesis','')}</div>
      {f"<div class=macroline>⚑ {s['macro_note']}</div>" if s.get('macro_note') else ''}
      </article>"""


def macro_strip():
    """Rate/credit backdrop, rendered INSIDE the swing section.

    Deliberately not its own tab: the macro read is only useful next to the
    positions it applies to. On its own it is a news ticker; beside a swing
    card it tells you what that position is levered to.
    """
    try:
        import macro_panel
        x = macro_panel.context()
    except Exception:
        return ""
    if not x.get("y10"):
        return ""
    y5 = x.get("y10_5d") or 0
    b = x.get("beta") or {}
    tail = sorted(b.items(), key=lambda kv: kv[1] * (1 if y5 > 0 else -1),
                  reverse=True)[:3]
    head = sorted(b.items(), key=lambda kv: kv[1] * (1 if y5 > 0 else -1))[:3]

    if abs(y5) < 0.04:
        read = ("10y flat over 5 sessions — no rate impulse, so rate exposure "
                "is not currently tilting any name.")
        lists = ""
    else:
        read = (f"10y {'rose' if y5 > 0 else 'fell'} {abs(y5):.2f}pt over 5 sessions.")
        lists = (f"<span class=tail>tailwind: {', '.join(k for k, _ in tail)}</span>"
                 f"<span class=head>headwind: {', '.join(k for k, _ in head)}</span>")

    return f"""
<div class=macrostrip>
  <div class=mrow>
    <span class=mi><b>10y</b> {x.get('y10')}%</span>
    <span class=mi><b>5d</b> {y5:+.2f}pt</span>
    <span class=mi><b>curve</b> {x.get('curve')}%</span>
    <span class=mi><b>credit 5d</b> {x.get('credit_5d')}%</span>
    <span class=mi><b>TLT 5d</b> {x.get('tlt_5d')}%</span>
  </div>
  <div class=mread>{read} {lists}</div>
  <div class=mnote>Rate exposure adjusts conviction by at most &plusmn;5. Sector
    betas are measured over 20 years at the 5-day horizon and are real — but rate
    moves did <b>not</b> predict sector returns in testing (216 cells, zero cleared
    the multiple-testing bar), so this flags what a position is levered to rather
    than forecasting direction.</div>
</div>
<style>
 .macrostrip{{border:1px solid rgba(128,128,128,.18);border-radius:9px;padding:10px 12px;
   margin:8px 0 14px}}
 .macrostrip .mrow{{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;
   font-variant-numeric:tabular-nums}}
 .macrostrip .mi b{{opacity:.6;font-weight:600;margin-right:3px}}
 .macrostrip .mread{{font-size:11.5px;opacity:.8;margin-top:6px}}
 .macrostrip .tail{{color:#16a34a;margin-left:10px}}
 .macrostrip .head{{color:#dc2626;margin-left:10px}}
 .macrostrip .mnote{{font-size:10.5px;opacity:.6;margin-top:6px;line-height:1.5}}
 .swing .macroline{{font-size:10.5px;opacity:.72;margin-top:5px;padding-top:5px;
   border-top:1px solid rgba(128,128,128,.12)}}
</style>"""


def _regime_src(x):
    src = x.get("regime_source", "")
    live = "SAME-DAY" in src
    base = x.get("baseline") or {}
    if live:
        u = x.get("uw_live") or {}
        # .get(key, default) does NOT protect against a key that exists with a
        # None value — which is what UW returns when the flip is unresolved.
        # Formatting None with ':+' raises and took the whole dashboard down.
        fd = u.get("flip_dist_pct")
        fd_txt = f"{fd:+}% away" if isinstance(fd, (int, float)) else "distance n/a"
        em = x.get("exp_oc_pct")
        em_txt = f"±{em}%" if em is not None else "n/a"
        return (f"<div class=gexsub><span class=livebadge>🟢 LIVE · real-time</span> "
                f"UW same-day gamma · flip {u.get('flip') or '—'} ({fd_txt}) · "
                f"expected move {em_txt} (mkt-implied)<br>"
                f"<span class=basel>15-yr baseline (SqueezeMetrics prior close): {base.get('regime','—')}, ~{base.get('exp_range','—')}% range</span></div>")
    return f"<div class=gexsub>for the <b>{x.get('applies_to','next session')}</b> · <span class=basel>{src}</span></div>"


def session_phase(peri):
    """Time-of-day 0DTE guidance. Charm (delta decay) accelerates into the afternoon → pinning toward the
    biggest-gamma strike intensifies in the last 2 hrs. Morning = direction; power hour = pin/fade."""
    n = datetime.now(ET); mins = n.hour * 60 + n.minute
    if n.weekday() >= 5 or mins < 570 or mins >= 960:
        return ""
    p = peri or {}
    cw = p.get("call_wall"); mp = (p.get("uw") or {}).get("max_pain", {}) or {}
    pin = cw or mp.get("max_pain")
    pin_txt = f" toward the call wall/pin (~{pin:.0f})" if pin else ""
    if mins < 660:            # 9:30–11:00
        ph = "OPENING DRIVE (9:30–11:00)"; col = "info"
        g = ("Pinning is weakest now, so the widest part of the day's range usually lands in this window. "
             "That is a statement about range, not direction: 56 features and 220 conditions produced zero "
             "intraday direction rules that held out of sample, at any hour.")
    elif mins < 810:          # 11:00–13:30
        ph = "MIDDAY CHOP (11:00–13:30)"; col = "mut"
        g = ("Lowest-energy window — ranges compress, breakouts fail. Be patient; avoid buying premium into the "
             "lunch lull unless a catalyst hits.")
    else:                     # 13:30–16:00
        ph = "POWER HOUR (13:30–16:00)"; col = "warn"
        g = (f"Charm/gamma pinning intensifies{pin_txt}. Breakouts tend to fade back to the pin; premium SELLERS "
             "(condors) are favored, and long premium decays fast. If directional, take profits quickly.")
    return f"<div class='phase {col}'><b>⏱ {ph}</b> — {g}</div>"


def scalp_setup(p):
    """Small/quick play — MOMENTUM breakout on TREND (low-gamma) days only. Backtest verdict:
    fading the walls LOSES every regime (t=-14 on pins); going WITH a vol-band breakout on low/short-
    gamma trend days is +8bps/trade (34% win, winners run) — matches the Zarattini paper (17-yr,
    Sharpe~1), locally suggestive not yet significant. PIN days = no scalp edge → sit out."""
    if not p or not p.get("ok") or not p.get("spot"):
        return None
    spot = p["spot"]
    flip = (p.get("uw") or {}).get("uw_flip") or p.get("gamma_flip")
    long_gamma = (p.get("net_gex_musd") or 0) > 0 or (flip and spot >= flip)
    tgt = round(spot * 0.0012)                       # ~25-50 tick / small target in index points
    if long_gamma:
        return {"dir": "SIT OUT", "why": "PIN regime (long gamma) — no scalp edge: fading the walls backtests "
                "NEGATIVE (t=−14) and momentum fails on pins too.",
                "entry": "no scalp — chop eats round-trips", "target": "—", "stop": "—",
                "note": "Save it for a trend day. (The master play above may still be valid separately.)", "col": "mut"}
    down = bool(flip and spot < flip)
    return {"dir": "SHORT breakout" if down else "LONG breakout",
            "why": (f"below the gamma flip {flip:.0f} → short gamma → moves accelerate DOWN" if down
                    else "low/short gamma = TREND regime → breakouts extend, don't fade"),
            "entry": ("short a break below the day's low / vol-band" if down else "long a break above the day's high / vol-band"),
            "target": f"{'−' if down else '+'}{tgt} pts, then TRAIL (let it run — trend days pay asymmetric)",
            "stop": (f"back above {flip:.0f}" if flip else "back inside the band"),
            "note": "Momentum, NOT fade. ~34% win but winners run big — trail, don't cap early. Thin on the "
                    "underlying; 0DTE leverage makes it worth it. Suggestive, not yet locally significant.",
            "col": "red" if down else "go"}


def scalp_side(peri_spx, peri_ndx):
    """Slide-out side tab (pure-CSS toggle) with the small/scalp plays for NDX + SPX.
    Prefers the LIVE 60s scalp_snapshot (morning window); falls back to periscope-derived setups."""
    live = load(os.path.join(HERE, "data", "scalp_snapshot.json"))
    fresh = False
    if live and live.get("plays"):
        try:
            fresh = (time.time() - os.path.getmtime(os.path.join(HERE, "data", "scalp_snapshot.json"))) < 180
        except Exception:
            fresh = False
    cards = ""
    stamp = ""
    if fresh and live.get("plays"):
        stamp = f"<div class=scstamp>🟢 live {live.get('as_of','')[-12:]}</div>"
        for s in live["plays"]:                   # NDX then SPX, live price + breakout status
            lv = f" · {s.get('day_low','')}–{s.get('day_high','')}" if s.get("day_high") else ""
            cards += (f"<div class='scard {s['col']}'><div class=sctop><b>{s['symbol']} {s.get('last','')}</b>"
                      f"<span class='pill {s['col']}'>{s['dir']}</span></div>"
                      f"<div class=scwhy>{s['why']}</div>"
                      f"<div class=scrow><span>▶ {s['entry']}</span></div>"
                      f"<div class=scrow><span>🎯 {s['target']}</span><span>⛔ {s['stop']}</span></div>"
                      f"<div class=scnote>session{lv} · {s['note']}</div></div>")
    else:
        for p in (peri_ndx, peri_spx):
            s = scalp_setup(p)
            if not s:
                continue
            sym = str((p or {}).get("symbol", "")).replace("^", "")
            cards += (f"<div class='scard {s['col']}'><div class=sctop><b>{sym} {(p or {}).get('spot','')}</b>"
                      f"<span class='pill {s['col']}'>{s['dir']}</span></div>"
                      f"<div class=scwhy>{s['why']}</div>"
                      f"<div class=scrow><span>▶ {s['entry']}</span></div>"
                      f"<div class=scrow><span>🎯 {s['target']}</span><span>⛔ {s['stop']}</span></div>"
                      f"<div class=scnote>{s['note']}</div></div>")
    if not cards:
        cards = "<div class=scnote>Scalp setups appear once live gamma levels load.</div>"
    return f"""<input type=checkbox id=scalptoggle class=scalptoggle>
<label for=scalptoggle class=scalptab><span>⚡ SCALP</span></label>
<aside class=scalppanel>
  <div class=schead>⚡ Small plays · scalp
    <label for=scalptoggle class=scclose>✕</label></div>
  <div class=scsub>Backtested: fading the walls LOSES (t=−14). The edge is MOMENTUM breakouts on TREND (low-gamma) days — go with the break, trail winners. On PIN days, sit out. Master play above = the bigger directional trade.</div>
  {stamp}
  {cards}
</aside>"""


def tracker_panel():
    try:
        import signal_tracker
        r = signal_tracker.record()
    except Exception:
        return ""
    if not r or not r.get("n"):
        return ""
    def _row(x):
        opt = f"{x['opt_pnl']:+.0f}%" if x.get("opt_pnl") is not None else "—"
        hit = "✅" if x["win"] == 1 else "❌" if x["win"] == 0 else "—"
        return (f"<tr><td>{x['session']}</td><td>{x['direction']}</td><td class=num>{x['conviction']}</td>"
                f"<td class='num {'g' if (x['ret'] or 0)>0 else 'r'}'>{x['ret']:+.2f}%</td>"
                f"<td class='num {'g' if (x.get('opt_pnl') or 0)>0 else 'r'}'>{opt}</td><td>{hit}</td></tr>")
    rows = "".join(_row(x) for x in r.get("recent", []))
    hi = (f"<span class=kpi>high-conv <b>{r['hi_conv_win']}%</b></span>" if r.get("hi_conv_win") is not None else "")
    optkpi = (f"<span class=kpi>opt win <b>{r['opt_win']}%</b></span><span class=kpi>opt avg <b>{r['opt_avg']:+.0f}%</b></span>"
              f"<span class=kpi>opt total <b>{r['opt_total']:+.0f}%</b></span>" if r.get("opt_win") is not None else "")
    head = f"📊 Track record — {r.get('opt_win','—')}% option-win / {r['win']}% directional on {r['n']} calls"
    return f"""<details class='card track'><summary>{head}</summary>
  <div class=kpis><span class=kpi>directional <b>{r['n']}</b></span><span class=kpi>dir win <b>{r['win']}%</b></span>{hi}
    {optkpi}<span class=kpi>stood down <b>{r['stood_down']}</b></span></div>
  <div class=hint>Option P&L = the recommended ATM 0DTE modeled with real gamma leverage (delta~0.5) + a +50% take-profit (how it's traded), not held-to-expiry. Regime-filtered seed (only buys premium on big-range days); conflict/neutral = stood down. Estimated — log real fills to make it exact. Small sample; read the trend.</div>
  <table><tr><th>session</th><th>call</th><th>conv</th><th>SPX o→c</th><th>opt P&L</th><th>hit</th></tr>{rows}</table>
</details>"""


def master_panel():
    """THE call, from Fable, at the top of the page.

    This exists because the dashboard used to shout several conflicting headlines at once — a green
    buy-the-calls headline above a periscope reading 'price is FALLING' above a desk brief saying
    'sit out'. One decision goes here; everything below it is evidence."""
    d = load(os.path.join(HERE, "data", "master_call.json"))
    if not d:
        return ""
    if not d.get("ok"):
        return (f"<div class='tldr mut'><div class=tlrow><div class=tlleft>"
                f"<div class=tllabel>MASTER CALL</div><div class=tlverb>UNAVAILABLE</div>"
                f"<div class=tltrig>{d.get('error','')}</div></div></div></div>")
    act = d.get("action", "STAND_DOWN")
    conv = int(d.get("conviction") or 0)
    enter = act == "ENTER"
    col = "go" if enter else "mut"
    struct = str(d.get("structure", "")).replace("_", " ")
    verb = f"{d.get('symbol','')} {struct}" if enter else "STAND DOWN"
    detail = ""
    if enter:
        def _px(v):
            try:
                return f"${float(v):.2f}"
            except Exception:
                return str(v or "—")
        credit = str(d.get("structure", "")).endswith(("CONDOR", "CREDIT_SPREAD"))
        in_word = "credit received" if credit else "debit paid"
        out_word = "buy back at" if credit else "sell at"
        rows = [("strikes", d.get("strikes", "")),
                (f"ENTRY · {in_word}", _px(d.get("entry_price"))),
                (f"TAKE PROFIT · {out_word}", _px(d.get("take_profit_price"))
                 + (f" <span class=mut>({d.get('take_profit_pct')}%)</span>" if d.get("take_profit_pct") else "")),
                (f"STOP · {out_word}", _px(d.get("stop_price"))
                 + (f" <span class=mut>({d.get('stop_pct')}%)</span>" if d.get("stop_pct") else ""))]
        if d.get("underlying_target") or d.get("underlying_stop"):
            rows.append(("underlying target / stop",
                         f"{d.get('underlying_target','—')} / {d.get('underlying_stop','—')}"))
        detail = "".join(
            f"<div class=growrow><span class=k>{lab}</span><span class=v><b>{val}</b></span></div>"
            for lab, val in rows)
        if d.get("exit_note"):
            detail += f"<div class=hint>{d['exit_note']}</div>"
    warn = ""
    if d.get("contradicts_research"):
        warn = (f"<div class=hint><b class=red>⚠ CONTRADICTS THE RESEARCH</b> — {d.get('contradiction_note','')}"
                f"<br>Treat this as a discretionary override, not a validated setup.</div>")
    # SECONDARY play — the directional 0DTE call, when Fable sees one worth taking
    sec = d.get("secondary") or {}
    sec_html = ""
    if str(sec.get("action", "")).upper() == "ENTER":
        def _p(v):
            try:
                return f"${float(v):.2f}"
            except Exception:
                return str(v or "—")
        badge = ("<span class='pill red'>vs research</span>"
                 if sec.get("contradicts_research") else "<span class='pill mut'>secondary</span>")
        sec_html = (
            f"<div class=hint style='margin-top:10px'><b>ALSO — DIRECTIONAL 0DTE</b> {badge}</div>"
            f"<div class=growrow><span class=k>{sec.get('symbol','')} "
            f"{str(sec.get('structure','')).replace('_',' ')}</span>"
            f"<span class=v><b>{sec.get('strikes','')}</b> · conv {sec.get('conviction','')}</span></div>"
            f"<div class=growrow><span class=k>ENTRY · debit paid</span><span class=v><b>{_p(sec.get('entry_price'))}</b></span></div>"
            f"<div class=growrow><span class=k>TAKE PROFIT · sell at</span><span class=v><b>{_p(sec.get('take_profit_price'))}</b></span></div>"
            f"<div class=growrow><span class=k>STOP · sell at</span><span class=v><b class=red>{_p(sec.get('stop_price'))}</b></span></div>"
            f"<div class=hint>{sec.get('thesis','')}</div>")
    runs = ""
    for b in (d.get("big_runs") or [])[:4]:
        runs += (f"<div class=growrow><span class=k>🚀 {b.get('ticker','')}</span>"
                 f"<span class=v>conv {b.get('conviction','')} · {b.get('why','')}</span></div>")
    if runs:
        runs = f"<div class=hint style='margin-top:8px'><b>BIG RUNS to look at</b></div>{runs}"
    return f"""<div class='tldr {col}'>
  <div class=tlrow>
    <div class=tlleft><div class=tllabel>MASTER CALL · Fable 5 · {d.get('as_of','')}</div>
      <div class=tlverb>{verb}</div>
      <div class=tltrig>{d.get('headline','')}</div></div>
    <div class=tlconv><div class=tlcnum>{conv}</div><div class=tlclab>/100 conviction</div>
      <div class=tlbar><span class='tlfill {col}' style='width:{conv}%'></span></div></div>
  </div>
  {detail}
  <div class=hint style='margin-top:8px'>{d.get('thesis','')}</div>
  {warn}
  {sec_html}
  {runs}
</div>"""


def gex_panel(x):
    if not x:
        return ""
    stance = x.get("stance", "selective")
    scol = {"buy_premium": "go", "sell_premium": "red", "selective": "info"}.get(stance, "info")
    pm = x.get("condor_survival", {})
    # The playbook and the thesis are engine prose and still carry the retired instruction
    # ("buy puts on a decisive break BELOW the gamma flip"). Same gate as the periscope: keep the
    # reasoning, drop the order, and drop an item that was nothing but the order. When something is
    # cut, SAY so: a silently shortened sentence reads like the engine had less to say, which is a
    # different lie from the one being fixed.
    play = "".join(f"<li>{_no_advice(p)}</li>" for p in x.get("direction_playbook", []) if _no_advice(p))
    thesis = str(x.get("thesis") or "").strip()
    thesis_txt = _no_advice(thesis)
    if thesis_txt != thesis:
        thesis_txt += ("<span class=mut> [the engine's trade instruction was cut here: it is the "
                       "retired directional read, measured at −10% to −11%/trade]</span>")
    bc = x.get("backcheck") or {}
    bc_html = (f"<div class=gexbc><b>Last session ({bc.get('date','')}):</b> predicted ~{bc.get('predicted_range','—')}% "
               f"range · realized <b>{bc.get('realized_range','—')}%</b> — {bc.get('verdict','')}</div>" if bc else "")
    dix = x.get("dix_tilt", "")
    conv = x.get("conviction", 0)
    b = x.get("bias", "")
    # The engine writes the lean and the order together ("BULLISH — favor CALLS"). Keep the lean,
    # which is what the inputs actually voted; drop the order, which is the retired trade.
    bias_txt = re.sub(r"\s*[\u2014-]\s*favou?rs?\s+(?:calls|puts)\s*$", "", str(b), flags=re.I)
    bcol = "red" if "BEARISH" in b or "CONFLICT" in b else "go" if "BULLISH" in b else "mut"
    rec = x.get("reconcile") or {}
    rec_html = ""
    for i in (rec.get("inputs") or []):
        ic = "go" if i["bias"] == "bullish" else "red" if i["bias"] == "bearish" else "mut"
        rec_html += f"<li>{i['src']}: <b class={ic}>{str(i['bias']).upper()}</b> ({i['score']:+d})</li>"
    if rec.get("conflict"):
        rec_html += "<li class=r>⚔️ inputs disagree → conviction cut, stand down</li>"
    rec_html = rec_html or "<li class=mut>no directional inputs firing</li>"
    lvl = x.get("spx_level", "")
    return f"""<div class='card gex {scol}'>
  <div class=gexhead>🔭 SPX · 0DTE dealer-gamma regime <span class=basel>({lvl})</span>
    <span class='pill {scol}'>{x.get('call','')}</span></div>
  <div class=gexbig>{x.get('regime','')}</div>
  {_regime_src(x)}
  <div class='gexthesis {bcol}'>
    <div class=thlabel>📋 REGIME READ · {bias_txt} · conviction {conv}/100</div>
    <div class=hint style='margin:4px 0 8px'><b class=red>The RANGE read is validated on real quotes (t=−13.2). The directional read below is not.</b> Buying 0DTE premium on this signal was tested at −10% to −11%/trade, and on real SPXW quotes the directional edge measures +0.00% (t=+0.24). Dealer gamma says how far the day is likely to travel, not which way. Read the direction lines as context, not as a signal.</div>
    <div class=convbar><span class='cfill {bcol}' style='width:{conv}%'></span></div>
    <div class=thtext>{thesis_txt}</div>
    <div class=thsig>Signals reconciled (all inputs voting):<ul>{rec_html}</ul></div>
  </div>
  <div class=gexnote>{x.get('note','')}</div>
  <div class=gexstats>
    <div><span class=k>GEX @ {x.get('gex_date','')} close</span><span class=v>{x.get('gex_bn','—')}bn · z{x.get('gex_z','')}</span></div>
    <div><span class=k>DIX (dark-pool buying)</span><span class=v>{x.get('dix','—')} · z{x.get('dix_z','')}</span></div>
    <div><span class=k>expected range</span><span class=v>~{x.get('exp_range_pct','—')}% · ±{x.get('exp_move_pts','—')}pt</span></div>
    <div><span class=k>expected open→close</span><span class=v>~{x.get('exp_oc_pct','—')}%</span></div>
    <div><span class=k>condor survival ±0.5/.75/1%</span><span class=v>{pm.get('pm0_5','—')}/{pm.get('pm0_75','—')}/{pm.get('pm1_0','—')}%</span></div>
  </div>
  {bc_html}
  <div class=gexcav>⚠️ {x.get('caveat','')}</div>
  <details class=gexplay><summary>Which side? (GEX = size, DIX = tilt, trigger = confirm)</summary><ol>{play}</ol></details>
  <div class=gexfoot>updated {x.get('as_of','—')} · SqueezeMetrics · range edge 15-yr, measured against VIX9D-implied vol (t=−13.2) · DIX direction is real on the underlying (+12.8bp, t=+3.0) but was not monetisable in 0DTE options, and as a premium-selling filter it tested as noise (p=0.49)</div>
</div>"""


# The 0DTE engines still write the retired directional trade into their snapshots as prose:
# gex_periscope's `signal` is a verb and its `signal_why` ends in an order ("... / put debit
# spread, trail to the put wall"), and gex_signal's `thesis` can read "IDEAL naked-CALL day. Buy a
# naked CALL". Out-of-sample testing measured that read at −10% to −11% per trade, and the "below
# the flip = buy premium" version at −7.2% to −19.1% (docs/VERDICT_LOG.md).
#
# So this pattern matches the SHAPES that instruction takes, not one fixed string, and the panels
# drop whole sentences that match while keeping the ones that explain the mechanism. The gate lives
# in the renderer on purpose: gex_signal.py and gex_periscope.py both need the same correction at
# source, and until they get it the page still has to be safe to read. It is a filter, not a
# guarantee: prose has more shapes than a regex, which is why the panels also carry the measured
# result in red next to anything directional.
_RETIRED_ADVICE = re.compile(
    r"buy\s+(?:a|an|the)?\s*(?:naked\s+|atm\s+|otm\s+|itm\s+|0dte\s+)*(?:call|put)"  # buy a naked CALL
    r"|(?:call|put)[\s/-]+debit\s+spread"                                            # call debit spread
    r"|naked[\s-](?:call|put)"                                                       # naked-CALL day
    r"|go\s+naked|naked\s+only|naked\s+is\s+fine"                                    # go naked on a break
    r"|(?:call|put)\s+on\s+a\s+(?:hold|decisive|break|clean)"                        # CALL on a hold above
    r"|=\s*(?:puts|calls)",                                                          # below flip = puts
    re.I)


def _is_retired_signal(sig):
    """True when the engine handed us one of the retired directional verbs."""
    return str(sig or "").startswith("BUY ")


def _periscope_read(sig):
    """Report the engine's verb as the lean it is, rather than reprinting it as an order."""
    s = str(sig or "")
    if not _is_retired_signal(s):
        return s
    return ("bullish lean" if "CALL" in s else "bearish lean") + " · retired read, not a signal"


def _no_advice(text):
    """Drop whole sentences that instruct the retired trade; keep the ones that explain why."""
    kept = [s for s in re.split(r"(?<=[.!?])\s+", str(text or ""))
            if not _RETIRED_ADVICE.search(s)]
    return " ".join(kept).strip()


def peri_panel(p):
    if not p or not p.get("ok"):
        return ""
    flip = p.get("gamma_flip"); dist = p.get("flip_dist_pct")
    net_pos = (p.get("net_gex_musd") or 0) > 0
    long_gamma = (dist is not None and dist > 0) or (dist is None and net_pos)
    fcol = "red" if long_gamma else "go"     # long gamma = pin (bad for naked longs) = red
    flip_str = f"{flip} ({dist:+.2f}% away)" if (flip and dist is not None) else "none within ±10% (deep pin)"
    bars = ""
    prof = p.get("profile", [])
    mx = max((abs(r["dgex_musd"]) for r in prof), default=1) or 1
    for r in sorted(prof, key=lambda r: -r["strike"]):
        w = abs(r["dgex_musd"]) / mx * 100
        pos = r["dgex_musd"] > 0
        mark = " ◄ call wall" if r["strike"] == p.get("call_wall") else (" ◄ put wall" if r["strike"] == p.get("put_wall") else "")
        bars += (f"<div class=pbar><span class=ps>{r['strike']:.0f}</span>"
                 f"<span class=ptrack><span class='pfill {'pp' if pos else 'pn'}' style='width:{w:.0f}%'></span></span>"
                 f"<span class=pv>{r['dgex_musd']:+.0f}M{mark}</span></div>")
    sig = p.get("signal", ""); sigcol = p.get("signal_col", "mut"); why = p.get("signal_why", "")
    brk = p.get("flip_break")
    brk_html = ""
    if brk == "broke_down":
        brk_html = ("<div class='brkbanner down'>⚠️ FLIP BREAK · price broke BELOW the gamma flip → short-gamma "
                    "regime. Dealer hedging now goes WITH the move, so the day's range tends to widen.</div>")
    elif brk == "reclaimed_up":
        brk_html = ("<div class='brkbanner up'>↑ Reclaimed the gamma flip → long-gamma pin regime restored. "
                    "Ranges tend to compress.</div>")
    retired = _is_retired_signal(sig)
    if retired:
        sigcol = "mut"      # a green or red box is an instruction too; a retired read gets neither
    why = _no_advice(why)
    retired_html = ("<div class=sigwhy><b class=red>Not a recommendation.</b> Buying 0DTE premium on this read was "
                    "tested at −10% to −11% per trade, and the same read taken below the flip lost "
                    "7.2% to 19.1% per trade. It is shown as context.</div>" if retired else "")
    order = _option_order(sig, p)
    order_html = f"<div class=sigorder>🎫 {order}</div>" if order else ""
    q = p.get("quality") or {}
    conv = q.get("conviction", 0)
    conv_html = ""
    if conv and retired:
        ccol = "go" if conv >= 60 else "warn" if conv >= 40 else "red"
        conv_html = (f"<div class=sigconv><span class=convlabel>conviction {conv}/100</span>"
                     f"<div class=convbar><span class='cfill {ccol}' style='width:{conv}%'></span></div>"
                     f"<div class='sigentry {q.get('entry_col','mut')}'>{q.get('entry','')}</div></div>")
    return f"""<div class='card peri {fcol}'>
  <div class=gexhead>🛰️ Live gamma periscope · {str(p.get('symbol','')).replace('^','')} {p.get('spot','')}
    <span class='pill {fcol}'>{'PIN regime' if long_gamma else 'TREND regime'}</span></div>
  {brk_html}
  <div class='sigbox {sigcol}'><span class=siglabel>PERISCOPE READ</span>
    <span class=sigval>{_periscope_read(sig)}</span><div class=sigwhy>{why}</div>{retired_html}{conv_html}{order_html}</div>
  <div class=perilevels>
    <div><span class=k>gamma flip</span><span class=v>{flip_str}</span></div>
    <div><span class=k>call wall (resistance/magnet)</span><span class=v>{p.get('call_wall','—')}</span></div>
    <div><span class=k>put wall (support)</span><span class=v>{p.get('put_wall','—')}</span></div>
    <div><span class=k>net dealer GEX</span><span class=v>{p.get('net_gex_musd','—')}M</span></div>
  </div>
  {track_form(str(p.get('symbol','')).replace('^',''), p.get('spot'))}
  <div class=perinote>{p.get('regime','')}</div>
  {_pin_risk(p)}
  {_flow_html(p.get('flow')) if not p.get('uw') else ""}
  {_uw_html(p.get('uw'))}
  {condor_card(p)}
  <div class=pbars>{bars}</div>
  <div class=gexfoot>live option chain · {p.get('as_of','')} · flip = intraday regime line; walls = magnets/support</div>
</div>"""


def _pin_risk(p):
    """Pinning is strongest when price sits within ~0.5% of a big-gamma wall (magnet). Actionable:
    high pin risk → breakouts fade back, premium sellers favored, don't chase directional."""
    spot = p.get("spot"); cw = p.get("call_wall"); pw = p.get("put_wall")
    if not spot:
        return ""
    walls = [w for w in (cw, pw) if w]
    if not walls:
        return ""
    nearest = min(walls, key=lambda w: abs(w - spot))
    dist = abs(nearest - spot) / spot * 100
    which = "call wall" if nearest == cw else "put wall"
    if dist < 0.5:
        return (f"<div class='pin high'>📌 Pin risk HIGH — price {dist:.2f}% from the {nearest:.0f} {which} "
                f"(strong magnet). Breakouts tend to fade back; favor premium selling, don't chase directional.</div>")
    if dist < 1.0:
        return f"<div class='pin mod'>📌 Pin risk moderate — {dist:.2f}% from the {nearest:.0f} {which}.</div>"
    return ""


def track_form(sym, spot):
    """Compact 'I bought this' form on a periscope — pre-fills the symbol."""
    return f"""<form action=/track method=get class=trackform>
  <input type=hidden name=sym value={sym}>
  <select name=dir><option value=call>📈 Call</option><option value=put>📉 Put</option></select>
  <input name=strike type=number step=any placeholder=strike value={round(spot) if spot else ''}>
  <input name=prem type=number step=any placeholder='premium $'>
  <input name=qty type=number value=1 style='width:48px'>
  <button type=submit>+ Track trade</button>
</form>"""


def sleeve_rows():
    """Capital split, each sleeve's risk budget, and its cadence."""
    try:
        import sleeves
    except Exception:
        return ""
    out = ""
    for name, label in (("0dte", "0DTE sleeve"), ("swing", "swing sleeve")):
        try:
            b = sleeves.budget(name)
            s = sleeves.get(name)
            n_open = sleeves.open_count(name)
            cad = s.get("cadence_seconds", 0)
            cadence = f"{cad//60}m" if cad < 3600 else f"{cad//3600}h"
            extra = ""
            if name == "0dte":
                extra = f" · monitored {s.get('monitor_seconds',60)}s while open"
            else:
                extra = f" · mode <b>{s.get('mode','index')}</b>"
            out += (f"<div class=growrow><span class=k>{label}</span><span class=v>"
                    f"${b['capital']:,.0f} · ≤${b['max_risk_dollars']:,.0f}/trade · "
                    f"{n_open}/{b['max_open']} open · every {cadence}{extra}</span></div>")
        except Exception:
            continue
    try:
        import sleeves as _sl
        if _sl.get("swing").get("mode") == "index":
            out += ("<div class=hint><b class=red>Swing sleeve is in 'index' mode</b> — out-of-sample testing rejected "
                    "every swing options structure (sector rotation worse than random p=0.87; long index spreads and "
                    "35-DTE put credit spreads both beaten by owning SPY on return, Sharpe and drawdown). The agent will "
                    "not propose swing option trades in this mode. Switch to 'options' in data/sleeves.json only if you "
                    "want the least-bad tested program as a diversifier — it is not an edge.</div>")
    except Exception:
        pass
    return out


def growth_panel():
    try:
        import growth_plan
        s = growth_plan.status()
    except Exception:
        return ""
    acol = {"PROTECT": "go", "LEAN-IN": "warn", "ON-TRACK": "info"}.get(s["aggression"], "mut")
    pct = min(100, max(0, round(s["account"] / s["next_milestone"]["value"] * 100)))
    ahead = s["ahead_pct"]
    acol2 = "go" if ahead >= 0 else "red"
    ev = s.get("evidence_target", s["account"])
    return f"""<div class='card growth'><div class=ahead>🎯 Growth plan
    <span class='pill {acol}'>{s['aggression']}</span></div>
  <div class=growrow><span class=k>account</span><span class=v>${s['account']:,}</span></div>
  {sleeve_rows()}
  <div class=growrow><span class=k>evidence curve (today)</span><span class=v>${ev:,} · <b class={acol2}>{ahead:+d}%</b></span></div>
  <div class=growrow><span class=k>stated ambition (today)</span><span class=v>${s['target_now']:,} · <span class=mut>{s.get('ambition_pct',0):+d}%</span></span></div>
  <div class=growbar><span class='growfill {acol}' style='width:{pct}%'></span></div>
  <div class=hint><b class=red>The $100k-by-Nov-19 ladder is not reachable</b> with any rule that survived out-of-sample testing —
  it would require risking ~374% of the account per trade (full Kelly on the strongest edge ever measured here is already 172%).
  Honest range for the remaining weeks is roughly $5,200–$7,800. Aggression is measured against the <b>evidence</b> curve so the
  agent is never pushed into permanent catch-up. See 07_superseded/RULES.md §5 for the sizing maths.<br>{s['aggr_note']} · Hard caps: ≤{s['risk_cap']['max_risk_per_trade_pct']}%/trade, ≤{s['risk_cap']['max_open']} open, −{s['risk_cap']['daily_loss_stop_pct']}% daily stop.
  <form action=/setacct method=get style='display:inline-flex;gap:5px;margin-left:8px'><input name=value type=number step=any placeholder='update $' style='width:90px;background:#0d1117;color:var(--text);border:1px solid var(--line2);border-radius:6px;padding:4px 7px;font-size:12px'><button style='background:var(--info);color:#04130a;border:none;border-radius:6px;padding:4px 10px;font-weight:700;cursor:pointer;font-size:12px'>set</button></form></div>
</div>"""


def agent_panel():
    a = load(os.path.join(HERE, "data", "agent_snapshot.json"))
    if not a:
        return ""
    try:
        import ai_trader
        opent = ai_trader.open_trades()
    except Exception:
        opent = []
    decs = ""
    for d in a.get("decisions", []):
        act = d.get("action", "")
        ac = {"ENTER": "go", "EXIT": "red", "STAND_DOWN": "mut", "BLOCKED": "red"}.get(act, "mut")
        al = {"ENTER": "🟢 ENTER", "EXIT": "🔴 EXIT", "STAND_DOWN": "⏸ STAND DOWN",
              "BLOCKED": "🛑 REFUSED BY RISK GATE"}.get(act, act)
        # sizing + real premium, when the trade got far enough to be priced
        econ = ""
        if d.get("contracts"):
            econ = (f"<div class=agentleg>{d['contracts']}x · net ${d.get('net_prem')} · "
                    f"risk ${d.get('total_risk')} ({d.get('pct_of_account')}% of account)</div>")
        # the adversarial committee's case against — shown whether it approved or vetoed
        cm = d.get("committee") or {}
        bear = (cm.get("bear") or {}).get("strongest_objection")
        cmhtml = ""
        if cm.get("verdict"):
            vc = {"APPROVE": "go", "RESIZE": "mut", "REJECT": "red"}.get(cm["verdict"], "mut")
            cmhtml = (f"<div class=agentthesis><span class='pill {vc}'>risk officer: {cm['verdict']}</span> "
                      f"{cm.get('reason','')}" + (f"<br><i>bear case:</i> {bear}" if bear else "") + "</div>")
        decs += (f"<div class=agentdec><span class='pill {ac}'>{al}</span> <b>{d.get('sym','')}</b> "
                 f"{d.get('structure','').replace('_',' ')} <span class=conv>conv {d.get('conviction','')}</span>"
                 f"<div class=agentleg>{d.get('legs','')}" + (f" · {d.get('expiry','')}" if d.get('expiry') else "")
                 + f"</div>{econ}<div class=agentthesis>{d.get('thesis','')}</div>{cmhtml}</div>")
    opent_html = ""
    if opent:
        opent_html = "<div class=agentopen><b>Agent open trades:</b> " + " · ".join(
            f"{t['sym']} {t['structure'].replace('_',' ')} ({t['legs']})" for t in opent) + "</div>"
    err = f"<span class=warn>{a['error']}</span>" if a.get("error") else ""
    return f"""<div class='card agentmgr'><div class=ahead>🤖 Autonomous agent {err}
    <span class=aistamp>{a.get('as_of','')}</span></div>
  <div class=agentover>{a.get('overall','')}</div>
  {decs or '<div class=scnote>No decisions yet — the agent evaluates every ~10 min in market hours.</div>'}
  {opent_html}
  <div class=hint>Fable 5 reads the whole board + your growth plan and decides calls/puts/spreads/condors. Paper-tracked with hard risk caps. Live-order execution stays a supervised step — the agent proposes, it doesn't auto-fire real orders.</div>
</div>"""


def rules_panel():
    """The 0DTE condor, its live gate state, and the real-quote evidence accumulating against it.

    This panel used to be titled 'Validated rule' while its own body said to size the trade as
    unproven. The title was the retired claim: the +3.7%/trade figure came from a pricing model and
    real SPXW quotes put the structure at roughly break-even. The badge now matches the body."""
    try:
        import rules
        g = rules.gate_state()
        ev = rules.credit_evidence()
    except Exception:
        return ""
    z = g.get("gex_z")
    zs = f"{z:+.2f}" if z is not None else "n/a"
    if g["open"]:
        state = "<span class='pill mut'>GATE OPEN · conditions met, edge unproven</span>"
        why = ""
    else:
        state = "<span class='pill mut'>STAND DOWN</span>"
        why = f"<div class=hint>{'; '.join(g['reasons'])}</div>"
    cond = ""
    try:
        c = rules.build_condor()
        if c and c.get("ok"):
            cond = (f"<div class=growrow><span class=k>today's structure</span><span class=v>"
                    f"{c['short_put']-c['wing']}/{c['short_put']}P · {c['short_call']}/{c['short_call']+c['wing']}C "
                    f"({c['sym']})</span></div>"
                    f"<div class=growrow><span class=k>credit</span><span class=v>{c['credit']} on {c['wing']}-wide "
                    f"= {c['credit_pct_of_width']}% of width</span></div>")
    except Exception:
        cond = ""
    n = ev.get("n", 0)
    evline = (f"<div class=growrow><span class=k>live-quote evidence</span><span class=v>{n} sessions logged · "
              f"{ev.get('sessions_needed', 60)} to go</span></div>")
    if ev.get("avg_credit_pct_high_gamma") is not None:
        evline += (f"<div class=growrow><span class=k>avg credit (high γ)</span><span class=v>"
                   f"{ev['avg_credit_pct_high_gamma']}% of width over {ev.get('n_high_gamma')} sessions</span></div>")
    return f"""<div class='card growth'><div class=ahead>📐 0DTE condor · unproven {state}</div>
  <div class=growrow><span class=k>prior-close GEX z</span><span class=v>{zs} · gate fires above +{rules.GEX_Z_GATE}</span></div>
  {cond}
  {evline}
  {why}
  <div class=hint><b class=red>⚠ CORRECTED 2026-08-05:</b> the +3.7%/trade figure came from a pricing MODEL. Re-run on
  <b>1,919 sessions of real SPXW bid/ask</b> (no model), this structure is approximately <b>break-even</b> — best cell +0.95%/trade
  (t=+0.82), and the 11:00 entry we use is −1.70%. The model overstated the credit by mispricing the wings. The underlying
  <i>range</i> finding (realised/implied 0.843× on high-γ vs 1.139× on low, t=−13.2) still holds — but it does not convert into a
  profitable condor at real prices. Size this as unproven, not as a validated edge.
  <b>Rejected and now hard-blocked:</b> buying 0DTE premium (−10%/trade), "below the flip = buy premium" (−7.2%), DIX as a selling
  filter (p=0.49), sector-rotation swing picks (worse than random, p=0.87), swing option overlays (all beaten by owning SPY).
  Every backtest P&amp;L was <b>modelled</b> — the credit log above is accumulating real quotes to confirm or kill it.
  Dated verdicts live in docs/VERDICT_LOG.md.</div>
</div>"""


def ticket_panel():
    """The ready-to-place order ticket, when every gate agrees. Supervised execution: the engine does
    the deciding, pricing, sizing and gating; you place it and report the fill."""
    try:
        import ticket
        t = ticket.build()
    except Exception:
        return ""
    if not t.get("ready"):
        return (f"<div class='card growth'><div class=ahead>🎟️ Order ticket "
                f"<span class='pill mut'>none</span></div>"
                f"<div class=hint>No ticket right now — {t.get('reason','')}. A ticket only appears when the "
                f"gamma gate, the 10:30–13:00 window, the risk gates, liquidity and sleeve sizing all agree.</div></div>")
    rows = ""
    for lg in t["legs"]:
        col = "go" if lg["action"].startswith("BUY") else "red"
        rows += (f"<div class=growrow><span class=k><span class='pill {col}'>{lg['action'].strip()}</span></span>"
                 f"<span class=v>{t['underlying']} {t['expiry']} {lg['strike']:g} {lg['right']}</span></div>")
    return f"""<div class='card growth'><div class=ahead>🎟️ Order ticket <span class='pill go'>READY</span>
    <span class=aistamp>{t['as_of']}</span></div>
  {rows}
  <div class=growrow><span class=k>quantity</span><span class=v>{t['quantity']} contracts</span></div>
  <div class=growrow><span class=k>limit</span><span class=v>${t['limit_net_credit']:.2f} net CREDIT (at the mid)</span></div>
  <div class=growrow><span class=k>max loss</span><span class=v>${t['max_loss_per_contract']:,.0f}/contract · ${t['total_risk']:,} total ({t['pct_of_sleeve']}% of sleeve)</span></div>
  <div class=growrow><span class=k>STOP · buy back at</span><span class=v><b class=red>${t.get('stop_price',0):.2f}</b> — hard, no discretion</span></div>
  <div class=growrow><span class=k>take profit · buy back at</span><span class=v><b>${t.get('take_profit_price',0):.2f}</b> (optional)</span></div>
  <div class=hint>{t.get('take_profit','')}</div>
  <div class=hint>{t['note']} · {t['time_stop']}<br>
  After it fills, record the real credit so the track record becomes measurement rather than model:
  <code>venv/bin/python3 ticket.py fill &lt;credit&gt; &lt;contracts&gt;</code></div>
</div>"""


def risk_panel():
    """The hard risk layer + the pre-registered scorecard. This panel exists to tell the truth about
    whether the agent has a measurable edge — including when the answer is 'not yet'."""
    try:
        import risk_gates, graduation
    except Exception:
        return ""
    try:
        g = graduation.check()
        proj = graduation.projection()
        s = g.get("stats") or {}
    except Exception:
        return ""
    ev = risk_gates.events_today()
    gate_bits = [
        f"entry window {risk_gates.ENTRY_OPEN_ET[0]}:{risk_gates.ENTRY_OPEN_ET[1]:02d}–"
        f"{risk_gates.ENTRY_LAST_0DTE[0]}:{risk_gates.ENTRY_LAST_0DTE[1]:02d} ET",
        f"{risk_gates.entries_today()}/{risk_gates.MAX_ENTRIES_PER_DAY} entries used",
        f"day P&amp;L {risk_gates.realized_today_pct():+.1f}%",
    ]
    evhtml = (f"<span class='pill red'>BLACKOUT · {', '.join(ev)}</span>" if ev
              else "<span class='pill go'>no event blackout</span>")
    if not s.get("n"):
        score = ("<div class=scnote>No closed trades yet — the scorecard starts once the agent "
                 "closes its first trades. Until then it is unproven, by definition.</div>")
    else:
        rows = ""
        for c in g.get("criteria", []):
            rows += (f"<div class=growrow><span class=k>{'✓' if c['pass'] else '✗'} {c['name']}</span>"
                     f"<span class=v>{c['detail']}</span></div>")
        vcol = "go" if g["verdict"].startswith("GRADUATED") else "mut"
        score = (f"<div class=growrow><span class=k>verdict</span><span class=v>"
                 f"<span class='pill {vcol}'>{g['verdict']}</span> {g['passed']}/{g['total']}</span></div>{rows}")
    # What can this account actually hold? Cached on disk — the probe hits live chains and is slow.
    afford = ""
    try:
        ap = os.path.join(HERE, "data", "affordability.json")
        if os.path.exists(ap) and (time.time() - os.path.getmtime(ap)) < 3600:
            rows = json.load(open(ap))
            bits = []
            for r in rows:
                mark = "go" if r.get("ok") else "red"
                bits.append(f"<span class='pill {mark}'>{r['sym']} {r.get('contracts',0)}x</span>")
            blocked = [r for r in rows if not r.get("ok")]
            afford = (f"<div class=growrow><span class=k>tradeable now</span><span class=v>{' '.join(bits)}</span></div>"
                      + (f"<div class=hint>{blocked[0]['reason']}</div>" if blocked else ""))
    except Exception:
        afford = ""
    # RANGE vs DIRECTIONAL scoreboard — which business is actually paying
    split = ""
    try:
        bs = graduation.by_strategy()
        rows = ""
        for lab, key in (("range (condor)", "range"), ("directional (calls/puts)", "directional")):
            st = bs.get(key) or {}
            if not st.get("n"):
                rows += (f"<div class=growrow><span class=k>{lab}</span>"
                         f"<span class=v class=mut>no closed trades yet</span></div>")
                continue
            c = "go" if st["expectancy_pct"] > 0 else "red"
            rows += (f"<div class=growrow><span class=k>{lab}</span><span class=v>"
                     f"n={st['n']} · win {st['win_rate']*100:.0f}% · "
                     f"<b class={c}>{st['expectancy_pct']:+.1f}%/trade</b> · "
                     f"PF {st.get('profit_factor')} · best {st['best_pct']:+.0f}% · "
                     f"total {st['total_return_pct']:+.0f}%</span></div>")
        split = ("<div class=hint style='margin-top:6px'><b>RANGE vs DIRECTIONAL — your own fills</b></div>"
                 + rows +
                 "<div class=hint>The modelled backtest said range +3.7%/trade, corrected on real SPXW quotes to "
                 "roughly break-even, and directional −10 to −11%/trade. "
                 "These are opposite payoff shapes — the condor wins small and often, directional loses "
                 "small and often then occasionally pays for everything — so a blended win rate would "
                 "hide which one is working. This settles it with real fills.</div>")
    except Exception:
        split = ""
    pj = ""
    if proj and proj.get("verdict"):
        pcol = "go" if "reachable" in proj["verdict"] and "NOT" not in proj["verdict"] else "red"
        pj = (f"<div class=growrow><span class=k>vs the curve</span><span class=v>"
              f"${proj.get('account',0):,.0f} → ${proj.get('target',0):,} by {proj.get('target_date','')} "
              f"({proj.get('need_x')}x in {proj.get('days')}d)</span></div>"
              f"<div class=hint><b class={pcol}>{proj['verdict']}</b></div>")
    return f"""<div class='card growth'><div class=ahead>🛡️ Risk gates &amp; scorecard {evhtml}</div>
  <div class=hint>{' · '.join(gate_bits)} · premium-selling blocked in negative gamma · dry-run {risk_gates.DRY_RUN}</div>
  {afford}
  {split}
  {score}
  {pj}
  <div class=hint>Pre-registered paper→live bar: ≥{graduation.BAR['min_trades']} trades, ≥{int(graduation.BAR['min_win_rate']*100)}% win rate,
  positive expectancy, profit factor {graduation.BAR['min_profit_factor']}–{graduation.BAR['max_profit_factor']}, drawdown ≤{int(graduation.BAR['max_drawdown_pct'])}%.
  {int((s.get('measured_fraction') or 0)*100)}% of closed trades are priced from real option quotes (premium in vs premium out); the rest fall back to an
  underlying-move × leverage ESTIMATE. All figures net of {graduation.COST_PCT}% friction — a directional read on the edge, not a broker statement.</div>
</div>"""


def ai_desk_panel():
    import html as _html
    d = load(os.path.join(HERE, "data", "ai_desk_snapshot.json"))
    if not d or not d.get("text"):
        return ""
    model = d.get("model", "")
    badge = "Fable 5" if model.startswith("claude-fable") else ("Opus" if model.startswith("claude-opus") else "rule-based")
    err = f" · <span class=warn>{d['error']}</span>" if d.get("error") else ""
    body = _html.escape(d["text"])
    # bold the SECTION LABELS (all-caps lines) and preserve line breaks
    import re as _re
    body = _re.sub(r"(?m)^([A-Z][A-Z ?/&]{3,}|VERDICT[^\n]*)$", r"<b class=aisec>\1</b>", body)
    body = body.replace("\n", "<br>")
    return f"""<div class='card aidesk'><div class=ahead>🧠 AI Desk <span class=abadge>{badge}</span>
    <span class=aistamp>{d.get('as_of','')}</span>{err}</div>
  <div class=aitext>{body}</div></div>"""


def positions_panel():
    try:
        import positions as _pos
        openp = _pos.list_open(); pnl = _pos.pnl_summary()
    except Exception:
        return ""
    cards = ""
    for p in openp:
        act = p.get("cur_action") or "HOLD"
        acol = {"SELL": "red", "SELL_HALF": "warn", "ADD": "go", "HOLD": "info"}.get(act, "mut")
        actlabel = {"SELL": "🔴 SELL NOW", "SELL_HALF": "🟡 SELL HALF", "ADD": "🟢 ADD OK", "HOLD": "⏳ HOLD"}.get(act, act)
        opt = p.get("cur_optpnl")
        opts = f" · est <b class={'g' if (opt or 0)>=0 else 'r'}>{opt:+.0f}%</b>" if opt is not None else ""
        half = " · ½ sold" if p.get("half_sold") else ""
        cards += f"""<div class='poscard {acol}'>
  <div class=poshd><b>{p['sym']} {p['strike']:.0f}{p['dir'][0].upper()}</b> · entry ${p['entry_prem']:.0f} ×{p['qty']}{half}
    <span class='pill {acol}'>{actlabel}</span></div>
  <div class=posreason>{p.get('cur_reason') or 'tracking… (updates on the next scan cycle)'}</div>
  <div class=posrow>underlying {(p.get('cur_move') or 0):+.2f}% since entry{opts}</div>
  <form action=/close method=get class=closeform><input type=hidden name=pid value={p['id']}>
    <input name=exitprem type=number step=any placeholder='exit $'><button>Close</button></form>
  <a class=halflink href='/soldhalf?pid={p['id']}'>mark ½ sold</a></div>"""
    pnls = ""
    if pnl.get("n"):
        pnls = (f"<div class=posrealized>💰 Realized: <b>{pnl['n']}</b> trades · win <b>{pnl['win']}%</b> · "
                f"avg <b>{pnl['avg_pct']:+.0f}%</b> · net <b class={'g' if pnl['total_dollar']>=0 else 'r'}>${pnl['total_dollar']:+,}</b></div>")
    return f"""<div class='card posmgr'><div class=ahead>📌 My positions (live-managed)</div>
  {cards or '<div class=scnote>No open positions. Use “+ Track trade” on a periscope when you buy.</div>'}
  {pnls}
  <div class=hint>Tracks vs live gamma levels + flow, pings you to SELL / SELL HALF / ADD. Enter exit $ to close → real P&L logs here.</div>
</div>"""


def condor_card(p):
    """Premium-selling plays (iron condor + call credit spread) — only when the gamma regime + time
    of day make survival high. Strikes matched to spot/walls, backtested survival shown."""
    if not p or not p.get("ok") or not p.get("spot"):
        return ""
    import condor as _cond
    spot = p["spot"]; net = p.get("net_gex_musd") or 0
    flip = (p.get("uw") or {}).get("uw_flip") or p.get("gamma_flip")
    sym = str(p.get("symbol", "")).replace("^", "")
    rnd = 25 if sym == "NDX" else 5
    if net > 0 and (not flip or spot >= flip):
        regime = "pin" if net > 8000 else "mid"          # deep positive gamma = pin
    elif flip and spot < flip:
        regime = "low"
    else:
        regime = "mid"
    iv = ((p.get("uw") or {}).get("implied_move") or {}).get("iv")   # UW IV in %
    ivd = (iv / 100) if iv else None
    c = _cond.play(spot, regime, p.get("call_wall"), p.get("put_wall"), rnd=rnd, iv=ivd)
    if not c.get("go"):
        rr = f" (best case only 1:{c['rr']}, EV −${abs(c['ev'])})" if c.get("rr") else ""
        return (f"<div class='ccard mut'><div class=ccht>💤 {sym} — no condor worth the risk{rr}</div>"
                f"<div class=scnote>{c.get('why','')}</div></div>")
    flowbias = (p.get("uw") or {}).get("overall") or (p.get("flow") or {}).get("bias")
    skew = ("Flow BULLISH → skew up (widen call side)." if flowbias == "bullish"
            else "Flow BEARISH → skew down (widen put side)." if flowbias == "bearish" else "Flow balanced → symmetric ok.")
    return f"""<div class='ccard red'>
  <div class=ccht>🦅 {sym} iron condor <span class='pill go'>1:{c['rr']} R:R · +${c['ev']} EV</span></div>
  <div class=ccleg>Sell {c['short_put']:.0f}P / {c['short_call']:.0f}C · buy wings {c['long_put']:.0f}P / {c['long_call']:.0f}C (±{c['width']}%)</div>
  <div class=ccrow>💵 <b>${c['credit']} credit</b> / <b>${c['max_loss']} max loss</b> · survival {c['survival']}% vs breakeven {c['breakeven_surv']}% → +EV</div>
  <div class=ccrow><b>Timing:</b> {c['timing']} · {skew}</div>
  <div class=scnote>⚠️ Short-vol tail risk (a news break loses a wing) — size small. Only shows when the credit clears your risk:reward; skips the thin-credit traps.</div>
</div>"""


def _option_order(sig, p):
    """Turn a signal + live levels into a concrete order, for the structures still on the table.

    The two directional branches this used to have (long ATM 0DTE calls or puts off the periscope
    verb) were deleted in the 2026-08-24 retirement pass. That trade is the one out-of-sample
    testing measured at −10% to −11% per trade, and at −7.2% to −19.1% when taken
    below the gamma flip. Printing strikes and a trail plan for it made a rejected strategy look
    like a desk ticket."""
    spot = p.get("spot"); cw = p.get("call_wall"); pw = p.get("put_wall")
    if not spot:
        return ""
    if "SELL PREMIUM" in sig and cw and pw:
        return (f"<b>Sell an iron condor:</b> short {pw:.0f}P / {cw:.0f}C, buy wings ~1% wider (defined risk).<br>"
                f"<b>Exit:</b> take 50% of max credit; <b>stop</b> if either short strike breaks (that's a flip/trend day).")
    return ""      # every other read, including both retired directional verbs → no order


def _uw_html(u):
    if not u:
        return ""
    im = u.get("implied_move") or {}; mp = u.get("max_pain") or {}; inf = u.get("intraday") or {}
    score = u.get("dir_score")
    scol = "go" if (score or 0) > 12 else "red" if (score or 0) < -12 else "info"
    proxy = u.get("proxy")
    hdr = f"🐳 Unusual Whales — real flow decision layer" + (f" <span class=basel>(via {proxy} proxy)</span>" if proxy else "")
    rows = [
        f"<div><span class=k>sweep/block flow</span><span class=v>{(u.get('flow') or {}).get('detail','—')[:60]}</span></div>",
        f"<div><span class=k>intraday tape flow</span><span class=v>{inf.get('bias','—')} · {inf.get('detail','')[:44]}</span></div>",
        f"<div><span class=k>implied move (mkt's own)</span><span class=v>±{im.get('move_pct','—')}% · IV {im.get('iv','—')}%</span></div>",
    ]
    # absolute price levels only when NOT a cross-scale proxy (QQQ max-pain would confuse next to NDX)
    if not proxy:
        rows.append(f"<div><span class=k>max pain ({mp.get('expiry','—')})</span><span class=v>{mp.get('max_pain','—')}</span></div>")
        rows.append(f"<div><span class=k>UW zero-gamma flip</span><span class=v>{u.get('uw_flip','—')}</span></div>")
    return f"<div class=uwbox><div class=uwhead>{hdr}<span class='uwscore {scol}'>{u.get('overall','').upper()} {score:+d}</span></div><div class=uwgrid>{''.join(rows)}</div></div>"


def _flow_html(f):
    if not f:
        return ""
    fcol = {"bullish": "go", "bearish": "red"}.get(f.get("bias"), "info")
    return (f"<div class='gexdix {fcol}' style='margin:0 0 10px'>🌊 Live flow: <b>{f.get('bias','').upper()}</b> — "
            f"{f.get('note','')} · PCR {f.get('pcr','—')} "
            f"<span style='color:var(--muted);font-weight:400'>(from option volume; layer your Unusual Whales / "
            f"Market Chameleon buy-vs-sell read on top for the strongest conviction)</span></div>")


def render():
    g = load(GAP); sw = load(SWING); gx = load(GEX)
    peri_spx = load(PERI_SPX); peri_ndx = load(PERI_NDX)
    ai = (g or {}).get("ai") or {}
    ai_model = ai.get("model", "")
    ai_text = (ai.get("text") or "").replace("\n", "<br>")
    ai_badge = ("Fable 5" if ai_model.startswith("claude-fable") else
                ("Opus (fallback)" if ai_model.startswith("claude-opus") else "rule-based"))
    ai_note = (f" · <span class=warn>{ai['error']}</span>" if ai.get("error") else "")
    ai_panel = (f"<div class='card analyst'><div class=ahead>🧠 Desk analyst "
                f"<span class=abadge>{ai_badge}</span>{ai_note}</div><div class=atext>{ai_text}</div></div>"
                if ai_text else "")

    gaps = (g or {}).get("candidates", [])
    gap_cards = "".join(cand_card(c) for c in gaps) or \
        "<div class=empty>No gap-and-go setups now. Most days have 0-3 — forcing trades gives the edge back.</div>"
    tr = (g or {}).get("track", {}) or {}
    n = tr.get("n", 0)
    track = (f"<div class=kpis><span class=kpi>trades <b>{n}</b></span><span class=kpi>win <b>{tr.get('win','—')}%</b></span>"
             f"<span class=kpi>avg <b>{tr.get('avg','—')}%</b></span><span class=kpi>cumulative <b>{tr.get('total','—')}%</b></span></div>"
             if n else "<div class=hint>Paper record builds as candidates settle daily (backtest: ~56% win, +1.25%/trade).</div>")
    trrows = "".join(f"<tr><td>{r['date']}</td><td><b>{r['ticker']}</b></td><td>{r['setup'].split()[0]}</td>"
                     f"<td class='num {'g' if (r['ret'] or 0)>0 else 'r'}'>{r['ret']:+.2f}%</td></tr>" for r in tr.get("recent", [])) \
             or "<tr><td colspan=4 class=mut>no settled paper trades yet</td></tr>"

    swings = (sw or {}).get("signals", [])
    swing_cards = "".join(swing_card(s) for s in swings) or "<div class=empty>No swing signals.</div>"
    ctx = (sw or {}).get("market_context")
    swing_ctx = ""
    if ctx:
        rc = {"RISK-ON": "go", "RISK-OFF": "red", "NEUTRAL": "warn"}.get(ctx.get("regime"), "mut")
        SN = {"XLK":"Tech","XLC":"Comm","XLY":"Discretionary","XLF":"Financials","XLV":"Health","XLE":"Energy","XLI":"Industrials","XLP":"Staples","XLB":"Materials","XLU":"Utilities","XLRE":"Real Estate"}
        lead = " · ".join(SN.get(s, s) for s in ctx.get("leaders", []))
        lag = " · ".join(SN.get(s, s) for s in ctx.get("laggards", []))
        scol = "red" if (ctx.get("stress_score", 0) >= 3) else "warn" if ctx.get("stress_score", 0) >= 2 else "mut"
        swing_ctx = f"""<div class='card swingctx {rc}'>
  <div class=ahead>🌐 Market environment <span class='pill {rc}'>{ctx.get('regime','')}</span></div>
  <div class=ctxnote>{ctx.get('regime_note','')} (VIX {ctx.get('vix','')})</div>
  <div class=ctxrow><b>🟢 Money rotating INTO:</b> {lead}</div>
  <div class=ctxrow><b>🔴 Money rotating OUT of:</b> {lag}</div>
  <div class='ctxstress {scol}'>⚠️ Geopolitical/stress gauge: {ctx.get('stress','')}</div>
  <div class=hint>Picks below are conviction-adjusted for this — bullish names in leading sectors get boosted, bullish into laggards trimmed, longs cut in risk-off. Updates as rotation shifts.</div>
</div>"""
    gas = (g or {}).get("as_of", "—"); sas = (sw or {}).get("as_of", "—")

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'><meta http-equiv=refresh content=60>
<title>Day + Swing Signals</title>
<style>
 :root{{--bg:#0d1117;--surface:#161b22;--line:#2a3038;--line2:#21262d;--text:#e6edf3;--muted:#9aa4b2;
  --go:#3fb950;--go-bg:#12261a;--info:#58a6ff;--red:#f85149;--red-bg:#26120f;--warn:#e3b341;--r:12px}}
 *{{box-sizing:border-box;min-width:0}} html,body{{overflow-x:clip;max-width:100%}}
 .card,table,.pbars,.tldr{{max-width:100%}} .legs,.thesis{{overflow-wrap:anywhere}}
 body{{background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:20px;max-width:920px;margin-inline:auto}}
 h1{{font-size:21px;margin:0}} h2{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:24px 0 10px;display:flex;gap:8px;align-items:center}}
 h2::after{{content:'';flex:1;height:1px;background:var(--line2)}}
 .top{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}
 .fresh{{color:var(--muted);font-size:12px;margin-top:2px}}
 .fbar{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;border-radius:10px;padding:9px 13px;margin:14px 0 4px;border:1px solid var(--line)}}
 .fbar.ok{{background:var(--go-bg);border-color:rgba(63,185,80,.4)}} .fbar.bad{{background:var(--red-bg);border-color:rgba(248,81,73,.5)}}
 .fmkt{{color:var(--muted)}}
 .fchip{{font-family:ui-monospace,Menlo,monospace;font-size:11px;padding:2px 7px;border-radius:6px;border:1px solid var(--line2)}}
 .fchip.ok{{color:var(--go)}} .fchip.bad{{color:var(--red);border-color:rgba(248,81,73,.5)}}
 .tldr{{border-radius:16px;padding:18px 20px;margin:14px 0 6px;border:1px solid var(--line);background:linear-gradient(135deg,#12161d,#0d1117)}}
 .tldr.go{{border-color:rgba(63,185,80,.55);box-shadow:0 0 0 1px rgba(63,185,80,.15)}}
 .tldr.red{{border-color:rgba(248,81,73,.55);box-shadow:0 0 0 1px rgba(248,81,73,.15)}}
 .tldr.warn{{border-color:rgba(227,179,65,.5)}} .tldr.mut{{border-color:var(--line)}}
 .tlrow{{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}}
 .tllabel{{font-size:11px;font-weight:800;letter-spacing:.1em;color:var(--muted)}}
 .tlverb{{font-size:34px;font-weight:900;line-height:1.05;margin:3px 0}}
 .tldr.go .tlverb{{color:var(--go)}} .tldr.red .tlverb{{color:var(--red)}} .tldr.warn .tlverb{{color:var(--warn)}}
 .tltrig{{font-size:13px;color:var(--muted)}}
 .tlconv{{text-align:center;min-width:120px}} .tlcnum{{font-size:30px;font-weight:900;line-height:1}}
 .tlclab{{font-size:10px;color:var(--muted);letter-spacing:.05em}}
 .tlbar{{height:6px;background:var(--line2);border-radius:9px;overflow:hidden;margin-top:6px}}
 .tlfill{{display:block;height:100%}} .tlfill.go{{background:var(--go)}} .tlfill.red{{background:var(--red)}} .tlfill.warn{{background:var(--warn)}} .tlfill.mut{{background:var(--muted)}}
 .tllevels{{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:13px;border-top:1px solid var(--line2)}}
 .tlv{{font-size:11.5px;color:var(--muted);background:#0d1117;border:1px solid var(--line2);border-radius:7px;padding:5px 10px;font-family:ui-monospace,Menlo,monospace}}
 .tlv b{{color:var(--text);margin-right:4px}}
 .tlsize{{font-size:10.5px;color:var(--muted);margin-top:5px}} .tlsize b{{color:var(--text)}}
 .tltgt{{margin-top:11px;padding-top:11px;border-top:1px solid var(--line2);font-size:12px;color:var(--muted);display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
 .tlt{{background:#0d1117;border:1px solid var(--line2);border-radius:7px;padding:4px 9px}} .tlt b{{color:var(--text)}} .tlt i{{color:var(--muted);font-style:normal;font-size:10.5px}}
 .tlmacro{{margin-top:10px;font-size:11.5px;color:var(--muted);display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}}
 .mchip{{font-size:10.5px;font-weight:800;padding:2px 8px;border-radius:99px;white-space:nowrap}}
 .mchip.go{{background:rgba(63,185,80,.2);color:var(--go)}} .mchip.warn{{background:rgba(227,179,65,.2);color:var(--warn)}} .mchip.red{{background:rgba(248,81,73,.2);color:var(--red)}}
 .mnote{{line-height:1.45}}
 .phase{{font-size:12.5px;line-height:1.5;border-radius:10px;padding:9px 13px;margin:6px 0;border:1px solid var(--line2)}}
 .phase.info{{background:rgba(88,166,255,.08);border-color:rgba(88,166,255,.3)}}
 .phase.warn{{background:rgba(227,179,65,.08);border-color:rgba(227,179,65,.35)}}
 .phase.mut{{background:var(--surface)}}
 .btn{{background:var(--go);color:#04130a;border:none;border-radius:10px;padding:10px 18px;font-weight:700;text-decoration:none;font-size:14px}}
 .btn:focus-visible{{outline:3px solid var(--info);outline-offset:2px}}
 .btn2{{background:var(--surface);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px 15px;font-weight:600;text-decoration:none;font-size:13px}}
 .hint,.empty{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--info);border-radius:10px;padding:11px 14px;margin:8px 0;font-size:13px;color:var(--muted)}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:13px}} @media(max-width:640px){{.grid{{grid-template-columns:1fr}}}}
 .card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:15px}}
 .analyst{{border-left:3px solid var(--info)}} .ahead{{font-weight:700;font-size:14px;margin-bottom:8px}}
 .posmgr{{border-left:3px solid var(--warn)}}
 .aidesk{{border:1px solid rgba(88,166,255,.4);border-left:4px solid var(--info);background:linear-gradient(180deg,rgba(88,166,255,.06),var(--surface) 55%)}}
 .abadge{{font-size:11px;background:rgba(88,166,255,.2);color:var(--info);padding:2px 9px;border-radius:99px;margin-left:6px}}
 .aistamp{{font-size:11px;color:var(--muted);margin-left:8px}}
 .aitext{{font-size:13.5px;line-height:1.62}} .aisec{{color:var(--info);letter-spacing:.03em;display:inline-block;margin-top:8px}}
 .growth{{border-left:4px solid var(--go)}} .growrow{{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}}
 .growbar{{height:8px;background:var(--line2);border-radius:9px;overflow:hidden;margin:8px 0}} .growfill{{display:block;height:100%}} .growfill.go{{background:var(--go)}} .growfill.warn{{background:var(--warn)}} .growfill.info{{background:var(--info)}} .growfill.mut{{background:var(--muted)}}
 .agentmgr{{border:1px solid rgba(227,179,65,.4);border-left:4px solid var(--warn);background:linear-gradient(180deg,rgba(227,179,65,.05),var(--surface) 55%)}}
 .agentover{{font-size:13px;font-weight:600;margin-bottom:10px;line-height:1.5}}
 .agentdec{{background:#0d1117;border:1px solid var(--line2);border-radius:9px;padding:10px;margin-bottom:8px}}
 .agentdec .pill{{position:static;margin:0 6px 0 0}} .conv{{font-size:11px;color:var(--muted)}}
 .agentleg{{font-family:ui-monospace,Menlo,monospace;font-size:12px;margin:5px 0}} .agentthesis{{font-size:12px;color:var(--muted);line-height:1.5}}
 .agentopen{{font-size:12px;margin-top:8px;padding-top:8px;border-top:1px solid var(--line2)}}
 .swingctx.go{{border-left:3px solid var(--go)}} .swingctx.red{{border-left:3px solid var(--red)}} .swingctx.warn{{border-left:3px solid var(--warn)}}
 .ctxnote{{font-size:12.5px;color:var(--muted);margin-bottom:8px}} .ctxrow{{font-size:13px;margin:4px 0}}
 .ctxstress{{font-size:12px;margin-top:8px;padding:7px 10px;border-radius:8px;line-height:1.5}} .ctxstress.red{{background:var(--red-bg);color:var(--red)}} .ctxstress.warn{{background:rgba(227,179,65,.1);color:var(--warn)}} .ctxstress.mut{{color:var(--muted)}}
 .trackform{{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:10px 0;font-size:12px}}
 .trackform select,.trackform input{{background:#0d1117;color:var(--text);border:1px solid var(--line2);border-radius:7px;padding:6px 8px;font-size:12px}}
 .trackform input{{width:92px}} .trackform button{{background:var(--warn);color:#04130a;border:none;border-radius:7px;padding:6px 12px;font-weight:700;cursor:pointer}}
 .poscard{{background:#0d1117;border:1px solid var(--line2);border-radius:10px;padding:11px;margin-bottom:9px}}
 .poscard.red{{border-left:3px solid var(--red)}} .poscard.warn{{border-left:3px solid var(--warn)}} .poscard.go{{border-left:3px solid var(--go)}} .poscard.info{{border-left:3px solid var(--info)}}
 .poshd{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13px}} .poshd .pill{{position:static;margin-left:auto}}
 .posreason{{font-size:12px;color:var(--muted);margin:5px 0;line-height:1.5}} .posrow{{font-size:12px;font-family:ui-monospace,Menlo,monospace}}
 .closeform{{display:inline-flex;gap:6px;margin-top:8px}} .closeform input{{width:80px;background:#0d1117;color:var(--text);border:1px solid var(--line2);border-radius:6px;padding:5px 7px;font-size:12px}}
 .closeform button{{background:var(--red);color:#fff;border:none;border-radius:6px;padding:5px 12px;font-weight:700;cursor:pointer;font-size:12px}}
 .halflink{{font-size:11px;color:var(--muted);margin-left:10px}} .posrealized{{font-size:12.5px;margin-top:6px}}
 .gex.go{{border-left:4px solid var(--go);background:linear-gradient(180deg,var(--go-bg),var(--surface) 60%)}}
 .gex.red{{border-left:4px solid var(--red);background:linear-gradient(180deg,var(--red-bg),var(--surface) 60%)}}
 .gex.info{{border-left:4px solid var(--info)}}
 .gexhead{{display:flex;align-items:center;gap:10px;font-weight:700;font-size:14px;flex-wrap:wrap}}
 .gexhead .pill{{position:static;margin-left:auto}}
 .gexbig{{font-size:22px;font-weight:800;margin:8px 0 2px}}
 .gexsub{{font-size:12px;color:var(--muted);margin-bottom:8px;line-height:1.6}}
 .livebadge{{font-size:10.5px;font-weight:800;background:var(--go);color:#04130a;padding:2px 8px;border-radius:99px}}
 .basel{{color:var(--muted);font-size:11px;opacity:.85}}
 .gexnote{{font-size:13px;color:var(--muted);line-height:1.55;margin-bottom:9px}}
 .gexdix{{font-size:13px;font-weight:600;background:rgba(88,166,255,.1);border:1px solid rgba(88,166,255,.3);border-radius:8px;padding:8px 11px;margin-bottom:10px;line-height:1.5}}
 .gexthesis{{border:1px solid var(--line);border-radius:10px;padding:11px 13px;margin-bottom:11px;background:#0d1117}}
 .gexthesis.go{{border-color:rgba(63,185,80,.45)}}
 .thlabel{{font-size:12px;font-weight:800;letter-spacing:.03em;margin-bottom:6px}}
 .thtext{{font-size:13px;line-height:1.6;margin:8px 0}}
 .thsig{{font-size:12px;color:var(--muted)}} .thsig ul{{margin:4px 0 0;padding-left:17px;line-height:1.55}}
 .track summary{{cursor:pointer;font-weight:700;font-size:14px}} .track summary::marker{{color:var(--muted)}}
 .track table{{margin-top:8px}}
 .glossary{{font-size:13px}} .glossary summary{{cursor:pointer;font-weight:700;color:var(--info);padding:4px 0}}
 .glossary dl{{margin:8px 0 0;font-size:12.5px;line-height:1.55}} .glossary dt{{font-weight:700;margin-top:9px}} .glossary dd{{margin:2px 0 0;color:var(--muted)}}
 .gexbc{{font-size:12px;color:var(--muted);background:#0d1117;border:1px solid var(--line2);border-radius:8px;padding:7px 10px;margin-top:9px}}
 .gexcav{{font-size:11.5px;color:var(--warn);line-height:1.5;margin-top:9px}}
 .gexstats{{display:grid;grid-template-columns:1fr 1fr;gap:5px 14px}} @media(max-width:560px){{.gexstats{{grid-template-columns:1fr}}}}
 .gexstats>div{{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line2);padding:5px 0}}
 .gexplay{{margin-top:11px;font-size:13px}} .gexplay summary{{cursor:pointer;font-weight:600;color:var(--info)}}
 .gexplay ol{{margin:8px 0 0;padding-left:18px;color:var(--muted);font-size:12.5px;line-height:1.6}}
 .gexplay li{{margin-bottom:4px}}
 .gexfoot{{margin-top:10px;font-size:11px;color:var(--muted);border-top:1px solid var(--line2);padding-top:8px}}
 .peri.go{{border-left:4px solid var(--go)}} .peri.red{{border-left:4px solid var(--red)}}
 .sigbox{{border-radius:10px;padding:11px 13px;margin:10px 0;border:1px solid var(--line)}}
 .sigbox.go{{background:var(--go-bg);border-color:rgba(63,185,80,.5)}} .sigbox.red{{background:var(--red-bg);border-color:rgba(248,81,73,.55)}}
 .sigbox.info{{background:rgba(88,166,255,.08);border-color:rgba(88,166,255,.4)}} .sigbox.mut{{background:#0d1117}}
 .siglabel{{font-size:10px;font-weight:800;letter-spacing:.1em;color:var(--muted)}}
 .sigval{{display:block;font-size:20px;font-weight:800;margin:2px 0 5px}}
 .sigbox.go .sigval{{color:var(--go)}} .sigbox.red .sigval{{color:var(--red)}}
 .sigwhy{{font-size:12.5px;color:var(--muted);line-height:1.55}}
 .sigorder{{font-size:12.5px;font-weight:600;margin-top:8px;padding:8px 10px;background:#0d1117;border:1px solid var(--line2);border-radius:8px;line-height:1.5}}
 .sigconv{{margin-top:8px}} .convlabel{{font-size:11px;color:var(--muted);font-weight:700}}
 .sigentry{{font-size:12px;margin-top:5px;line-height:1.5;font-weight:600}} .sigentry.go{{color:var(--go)}} .sigentry.warn{{color:var(--warn)}} .sigentry.red{{color:var(--red)}} .sigentry.mut{{color:var(--muted)}}
 .brkbanner{{font-size:13px;font-weight:700;border-radius:9px;padding:9px 12px;margin:10px 0}}
 .brkbanner.down{{background:var(--red);color:#fff}} .brkbanner.up{{background:var(--go);color:#04130a}}
 .perilevels{{display:grid;grid-template-columns:1fr 1fr;gap:5px 14px;margin:10px 0}} @media(max-width:560px){{.perilevels{{grid-template-columns:1fr}}}}
 .perilevels>div{{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--line2);padding:5px 0}}
 .perinote{{font-size:12.5px;color:var(--muted);line-height:1.5;margin-bottom:10px}}
 .pbars{{display:flex;flex-direction:column;gap:3px;font-family:ui-monospace,Menlo,monospace;font-size:11px}}
 .pbar{{display:grid;grid-template-columns:44px 1fr 96px;align-items:center;gap:7px}}
 .ps{{color:var(--muted);text-align:right}} .ptrack{{background:var(--line2);border-radius:4px;height:12px;overflow:hidden}}
 .pfill{{display:block;height:100%}} .pfill.pp{{background:var(--red)}} .pfill.pn{{background:var(--go)}}
 .pv{{color:var(--muted);font-size:10.5px}}
 .pin{{font-size:12px;line-height:1.5;border-radius:8px;padding:8px 11px;margin-bottom:10px}}
 .pin.high{{background:rgba(227,179,65,.1);border:1px solid rgba(227,179,65,.4);color:var(--warn)}}
 .pin.mod{{background:var(--surface);border:1px solid var(--line2);color:var(--muted)}}
 .uwbox{{background:#0d1117;border:1px solid var(--line2);border-radius:9px;padding:10px 12px;margin-bottom:10px}}
 .uwhead{{font-size:12.5px;font-weight:700;margin-bottom:7px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
 .uwscore{{font-size:11px;font-weight:800;padding:2px 8px;border-radius:99px;margin-left:auto}}
 .uwscore.go{{background:var(--go);color:#04130a}} .uwscore.red{{background:var(--red);color:#fff}} .uwscore.info{{background:rgba(88,166,255,.2);color:var(--info)}}
 .uwgrid{{display:grid;grid-template-columns:1fr;gap:3px}} .uwgrid>div{{display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--line2);padding:4px 0;font-size:11.5px}}
 .uwgrid .v{{font-size:11px;text-align:right}}
 .ccard{{border-radius:9px;padding:11px;margin-bottom:10px;border:1px solid var(--line2);background:#0d1117}}
 .ccard.red{{border-left:3px solid var(--red)}} .ccard.mut{{border-left:3px solid var(--muted)}}
 .ccht{{font-size:13px;font-weight:700;display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:7px}}
 .ccht .pill{{position:static;margin:0}} .pill.warn{{background:var(--warn);color:#04130a}}
 .ccleg{{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;background:var(--surface);border:1px solid var(--line2);border-radius:7px;padding:7px 9px;margin-bottom:7px}}
 .ccrow{{font-size:12px;margin:4px 0;line-height:1.5}}
 .abadge{{font-size:11px;background:rgba(88,166,255,.18);color:var(--info);padding:2px 8px;border-radius:99px;margin-left:6px}}
 .warn{{color:var(--warn);font-size:11.5px}} .atext{{font-size:13.5px;line-height:1.6}}
 .cand.go,.swing.go{{border-color:rgba(63,185,80,.5);background:linear-gradient(180deg,var(--go-bg),var(--surface) 72%)}}
 .cand.info{{border-color:rgba(88,166,255,.4)}} .swing.red{{border-color:rgba(248,81,73,.45);background:linear-gradient(180deg,var(--red-bg),var(--surface) 72%)}}
 .swing.mut{{opacity:.72}}
 .chead{{display:flex;align-items:center;gap:9px;margin-bottom:8px}} .tk{{font-size:20px;font-weight:800}}
 .pill{{font-size:11px;font-weight:800;padding:3px 10px;border-radius:99px;margin-left:auto}}
 .pill.go{{background:var(--go);color:#04130a}} .pill.red{{background:var(--red);color:#fff}} .pill.info{{background:rgba(88,166,255,.2);color:var(--info)}} .pill.mut{{background:var(--line);color:var(--muted);margin-left:auto}}
 .conv{{font-size:11px;color:var(--muted)}}
 .convbar{{height:5px;background:var(--line2);border-radius:9px;overflow:hidden;margin:2px 0 8px}} .cfill{{display:block;height:100%}} .cfill.go{{background:var(--go)}} .cfill.red{{background:var(--red)}} .cfill.mut{{background:var(--muted)}}
 .metrics{{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}} .metrics>div{{display:flex;justify-content:space-between;border-bottom:1px solid var(--line2);padding:4px 0}}
 .k{{color:var(--muted);font-size:12px}} .v{{font-family:ui-monospace,Menlo,monospace;font-weight:700;font-size:12.5px}} .g{{color:var(--go)}} .r{{color:var(--red)}}
 .play{{margin-top:9px;font-weight:600;font-size:13px}}
 .optplay{{margin-top:6px;font-size:12px;color:var(--muted);background:#0d1117;border:1px solid var(--line2);border-radius:7px;padding:7px 9px;line-height:1.5}}
 .meta{{font-size:11.5px;color:var(--muted);margin-bottom:8px}} .stru{{font-size:14px;margin-bottom:3px}}
 .legs{{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;background:#0d1117;border:1px solid var(--line2);border-radius:7px;padding:7px;margin-bottom:8px}} .exp{{color:var(--muted)}}
 .thesis{{font-size:12.5px;color:var(--muted);line-height:1.55}}
 .kpis{{display:flex;gap:9px;flex-wrap:wrap;margin:6px 0}} .kpi{{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font-size:12.5px}} .kpi b{{font-size:15px}}
 table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}} th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line2)}} .num{{text-align:right;font-family:ui-monospace,Menlo,monospace}} th{{color:var(--muted)}} .mut{{color:var(--muted)}}
 footer{{margin-top:26px;color:var(--muted);font-size:11.5px;line-height:1.6}}
 .scalptoggle{{position:fixed;opacity:0;pointer-events:none}}
 .scalptab{{position:fixed;right:0;top:38%;z-index:40;background:var(--info);color:#04130a;font-weight:800;font-size:13px;
   padding:16px 7px;border-radius:10px 0 0 10px;cursor:pointer;writing-mode:vertical-rl;text-orientation:mixed;box-shadow:-2px 2px 10px rgba(0,0,0,.4)}}
 .scalppanel{{position:fixed;right:0;top:0;height:100vh;width:340px;max-width:88vw;z-index:41;background:var(--bg);border-left:1px solid var(--line);
   box-shadow:-6px 0 24px rgba(0,0,0,.5);padding:16px;overflow-y:auto;transform:translateX(100%);transition:transform .22s ease}}
 .scalptoggle:checked ~ .scalppanel{{transform:translateX(0)}}
 .scalptoggle:checked ~ .scalptab{{right:340px}}
 @media(max-width:560px){{.scalptoggle:checked ~ .scalptab{{right:88vw}}}}
 .schead{{display:flex;justify-content:space-between;align-items:center;font-size:15px;font-weight:800;margin-bottom:4px}}
 .scclose{{cursor:pointer;color:var(--muted);font-size:18px;padding:0 6px}}
 .scsub{{font-size:11.5px;color:var(--muted);line-height:1.5;margin-bottom:12px}}
 .scard{{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:12px;margin-bottom:11px}}
 .scard.go{{border-left:3px solid var(--go)}} .scard.red{{border-left:3px solid var(--red)}} .scard.mut{{border-left:3px solid var(--muted)}}
 .sctop{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}} .sctop .pill{{position:static;margin:0}}
 .scwhy{{font-size:12px;color:var(--muted);line-height:1.5;margin-bottom:8px}}
 .scrow{{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;font-weight:600;margin:3px 0}}
 .scnote{{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.45}}
 .scstamp{{font-size:11px;color:var(--go);font-weight:700;margin-bottom:8px}}
 .thtext,.tltrig,.sigwhy,.perinote,.gexnote,.gexsub,.sigorder,.phase,.gexcav{{overflow-wrap:anywhere}}
 .pill{{white-space:nowrap}}
 @media(max-width:560px){{
   body{{padding:13px}}
   h2{{display:block}} h2::after{{display:none}}
   h2 span{{display:block;margin-top:2px}}
   .tlrow{{flex-direction:column;align-items:stretch}}
   .tlverb{{font-size:27px}} .tlconv{{text-align:left;min-width:0}} .tlbar{{max-width:200px}}
   .gexbig{{font-size:19px}} .tlcnum{{font-size:26px}}
   .gexhead,.uwhead{{align-items:flex-start}}
   .gexhead .pill,.uwscore,.sigbox .pill{{margin-left:0}}
   .uwgrid>div,.gexstats>div,.perilevels>div,.gexbc{{flex-wrap:wrap}}
   .uwgrid .v,.gexstats .v,.perilevels .v{{text-align:left}}
   table{{font-size:11px}} th,td{{padding:4px 5px}}
   .pbar{{grid-template-columns:34px 1fr auto}} .pv{{white-space:normal;font-size:10px}}
   .fbar{{font-size:11px}} .fchip{{font-size:10px}}
   .tlv{{font-size:11px}} .tllevels{{gap:6px}}
   .top{{gap:8px}} h1{{font-size:19px}}
   .metrics{{grid-template-columns:1fr}}
 }}

 /* ---- tabs: CSS-only, radios must precede the panes for the ~ selector ---- */
 .tabin{{position:absolute;opacity:0;pointer-events:none}}
 .tabs{{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0 14px;border-bottom:1px solid var(--line)}}
 .tabs label{{cursor:pointer;padding:9px 16px;font-size:13.5px;font-weight:700;color:var(--muted);
   border:1px solid transparent;border-bottom:none;border-radius:9px 9px 0 0;margin-bottom:-1px;user-select:none}}
 .tabs label:hover{{color:var(--text)}}
 .pane{{display:none}}
 #tb0:checked ~ .tabs label[for=tb0],#tb1:checked ~ .tabs label[for=tb1],
 #tb2:checked ~ .tabs label[for=tb2],#tb3:checked ~ .tabs label[for=tb3],
 #tb4:checked ~ .tabs label[for=tb4]{{
   color:var(--text);background:var(--surface);border-color:var(--line);border-bottom:1px solid var(--bg)}}
 #tb0:checked ~ .pane0,#tb1:checked ~ .pane1,#tb2:checked ~ .pane2,
 #tb3:checked ~ .pane3,#tb4:checked ~ .pane4{{display:block}}
 @media(max-width:560px){{.tabs label{{padding:8px 11px;font-size:12.5px}}}}

 .fbar.closed{{background:rgba(139,148,158,.10);border:1px solid var(--line2);color:var(--muted);
   border-radius:11px;padding:13px 15px;font-size:14px;font-weight:800;letter-spacing:.02em}}
 .fbar.closed.warm{{background:rgba(227,179,65,.12);border-color:rgba(227,179,65,.45);color:var(--warn)}}
 .fbar .fsub{{font-weight:500;font-size:11.5px;margin-top:6px;line-height:1.55;letter-spacing:0}}
</style></head><body>
<header class=top>
  <div><h1>Day + Swing Signals</h1><div class=fresh>gap {gas} · swing {sas}</div></div>
  <div style='display:flex;gap:8px;flex-wrap:wrap'>
    <a class=btn2 href='/strategy'>📖 How it works</a>
    <a class=btn href='/refresh'>🔄 Update</a>
  </div>
</header>
{scalp_side(peri_spx, peri_ndx)}
{freshness_banner()}
{master_panel()}
{edge_panel.desk_panel()}
{scorecard.panel()}

<input type=radio name=tb id=tb0 class=tabin checked>
<input type=radio name=tb id=tb1 class=tabin>
<input type=radio name=tb id=tb2 class=tabin>
<input type=radio name=tb id=tb3 class=tabin>
<input type=radio name=tb id=tb4 class=tabin>
<nav class=tabs>
  <label for=tb0>⚡ 0DTE &amp; Gamma</label>
  <label for=tb1>🚀 Gap &amp; Go</label>
  <label for=tb2>📅 Swing</label>
  <label for=tb3>🛡️ Account &amp; Risk</label>
  <label for=tb4>🦢 Black Swan</label>
</nav>

<section class="pane pane0">
{ticket_panel()}
{rules_panel()}
{session_phase(peri_spx)}
<h2>SPX 0DTE · dealer gamma, DIX &amp; implied move <span style='color:var(--muted);font-weight:400;text-transform:none;letter-spacing:0'>(the range read · validated on real quotes, t=−13.2)</span></h2>
{gex_panel(gx)}
{peri_panel(peri_spx)}
{peri_panel(peri_ndx)}
{positions_panel()}
{tracker_panel()}
<details class='card glossary'><summary>📖 What the terms mean (plain English)</summary><dl>
<dt>Dealer gamma / GEX</dt><dd>How much the big option market-makers must hedge. When they're "long gamma" they trade AGAINST moves → the market gets pinned and chops (small range). When "short gamma" (negative) they trade WITH moves → the market gets pushed further → big trending days. This is set by yesterday's close, so you know it before the open.</dd>
<dt>Gamma flip</dt><dd>The price line that separates the two worlds above. Above it dealers damp moves, so the day's range tends to be small. Below it they push moves along, so the range tends to be big. That is the whole claim: dealer gamma predicts the SIZE of the day's move, never its direction. The reading this glossary used to give, "below the flip = buy premium", was measured on real option quotes and lost 7.2% per trade as a straddle and 19.1% as a strangle. It is retired. Use the flip to judge how far the day is likely to travel, not which way.</dd>
<dt>Call wall / Put wall</dt><dd>The strikes with the most dealer gamma. Call wall acts like a ceiling/magnet (price gets stuck under it); put wall acts like a floor/support. Great profit-taking and stop levels.</dd>
<dt>DIX (Dark Index)</dt><dd>How aggressively institutions are BUYING in dark pools (off-exchange). High DIX = big money accumulating = bullish tilt. Over 15 years that tilt is real but small: +12.8bp open to close on the underlying, t=+3.0. It did not survive being expressed as a 0DTE option trade, and as a premium-selling filter it tested as noise (p=0.49). Context, not a trigger.</dd>
<dt>Expected range / open→close</dt><dd>How much the market is likely to move, based on today's regime. This is the one 0DTE number with 15 years of evidence behind it: realised versus implied move is 0.843× on high-gamma days against 1.139× on low, t=−13.2, measured against VIX9D-implied vol. It tells you which structures are even plausible today. It does not tell you a side, and buying premium because the number is big was tested and lost.</dd>
<dt>Condor survival</dt><dd>If you SOLD a defined-risk iron condor at these strikes, how often it would expire safe. Highest on pin days. Survival is not profit: on 1,919 sessions of real SPXW bid/ask the same structure came out roughly break-even, so read this as a risk number rather than an edge.</dd>
<dt>VIX term structure (backwardation)</dt><dd>When near-term fear (VIX9D) is higher than a bit further out (VIX). Backwardation is one of only three signals that survived out-of-sample testing here, holding on all three splits (t=+3.9/+2.8/+2.1), on a days-to-weeks horizon. The older "high DIX plus backwardation = a bullish buy-the-stress day" version was never confirmed.</dd>
<dt>Conviction</dt><dd>How many of the page's inputs point the same way at once, and how strongly. It is a tally of agreement, not a probability. Nothing in this repo's intraday direction hunt cleared 55% on both train and validate, so a high number means the inputs agree, not that they are right. Capped at 75.</dd>
</dl></details>
</section>

<section class="pane pane1">
<h2>Intraday · gap-and-go <span style='color:var(--muted);font-weight:400;text-transform:none;letter-spacing:0'>(+1.25%/trade, 56% win, t=6.6 · from its own backtest, no entry in 02_findings yet)</span></h2>
{ai_panel}
<div class=grid>{gap_cards}</div>
{track}
<table><tr><th>date</th><th>ticker</th><th>setup</th><th>open→close</th></tr>{trrows}</table>
</section>

<section class="pane pane2">
<h2>Swing · days-to-weeks <span style='color:var(--muted);font-weight:400;text-transform:none;letter-spacing:0'>(regime + rotation + momentum + IV)</span></h2>
{swing_ctx}
{macro_strip()}
<div class=grid>{swing_cards}</div>
</section>

<section class="pane pane3">
{risk_panel()}
{growth_panel()}
{agent_panel()}
{ai_desk_panel()}
</section>

<section class="pane pane4">
{blackswan_panel.blackswan_panel()}
</section>

<footer><b>What this page is.</b> A local read-out of one research system: the dealer-gamma regime, live option levels, a gap-and-go
scanner, a swing screen, and the risk gates sitting in front of all of it. It proposes, prices and records. It never places an order.
<b>What survived testing.</b> Dealer gamma predicts the day's RANGE, not its direction: realised versus implied move is 0.843× on
high-gamma days against 1.139× on low, t=−13.2 over 15 years. Short interest predicts LOWER forward returns, the opposite of the
squeeze story (IC −0.107 at 63 days). VIX backwardation held on all three splits (t=+3.9/+2.8/+2.1). Those three, in
02_findings/WHAT_WORKS.md.
<b>What is unproven.</b> The 0DTE iron condor. Its +3.7%/trade came from a pricing model; on 1,919 sessions of real SPXW bid/ask it
is roughly break-even, and the credit log on the 0DTE tab is collecting live quotes to settle it. The gap-and-go and swing figures
quoted above come from their own backtests and have no entry in 02_findings yet.
<b>What is retired.</b> Buying 0DTE premium on a directional read (−10% to −11% per trade), and its "below the gamma
flip = buy premium" form (−7.2% as a straddle, −19.1% as a strangle). Neither is a recommendation on this page any more. Dated
verdicts: docs/VERDICT_LOG.md. Superseded documents: 07_superseded/.
<b>Not financial advice.</b> Paper-trade first. Every number here is a measurement with an error bar, not an instruction.</footer>
<script>var ep={(g or {}).get('epoch',0)};if(ep){{var f=document.querySelector('.fresh');}}</script>
</body></html>"""


# "📖 How it works" used to serve 01_START_HERE/STRATEGY_0DTE.md. That document says at line 3 that
# the "below the flip = buy premium" rule is wrong and retired, then teaches it again at line 38, and
# it was the only long-form explanation the dashboard offered. It now serves the current verdicts.
# One constant so the next move is a one-line change instead of a hunt.
DOC_PAGE = ("02_findings", "WHAT_WORKS.md")


def _repo_path(*parts):
    """A path inside the repo, resolved through idt.paths so a moved doc still resolves."""
    try:
        from idt.paths import REPO_ROOT as _root
    except Exception:          # idt not installed, e.g. a bare `python3 gap_dashboard.py`
        _root = os.path.dirname(HERE)
    return os.path.join(_root, *parts)


def strategy_page():
    """Serve the current findings doc (DOC_PAGE) rendered with a minimal markdown converter."""
    import html as _html
    import re
    path = _repo_path(*DOC_PAGE)
    try:
        md = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as exc:
        # A missing file used to render a page reading "Strategy doc not found" and nothing else,
        # which tells you neither which file nor where it was expected. Name both, and never let
        # this raise: the handler has no error page, so an exception here is a dead connection.
        md = ("# That document is missing\n\n"
              f"This page serves `{os.path.join(*DOC_PAGE)}`, the current research verdicts.\n\n"
              f"Expected it at `{path}` and got "
              f"`{exc.__class__.__name__}: {getattr(exc, 'strerror', None) or exc}`.\n\n"
              "If the file moved, change `DOC_PAGE` in `04_live_system/gap_dashboard.py`. Dated "
              "verdicts are in `docs/VERDICT_LOG.md` and the superseded strategy documents are in "
              "`07_superseded/`.\n")
    def _inline(t):
        t = _html.escape(t)
        # Markdown links keep their words and, when it adds something, their target. None becomes
        # an <a>: the targets are repo-relative and would 404 against this server.
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                   lambda m: m.group(1) if m.group(1) == m.group(2) else f"{m.group(1)} ({m.group(2)})", t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return re.sub(r"`(.+?)`", r"<code>\1</code>", t)

    # join hard-wrapped list-item continuations (indented 2+ spaces) into their parent line
    joined = []
    for ln in md.split("\n"):
        if re.match(r"^  +\S", ln) and joined and joined[-1].strip():
            joined[-1] = joined[-1].rstrip() + " " + ln.strip()
        else:
            joined.append(ln)

    out, in_ul, in_tbl, buf = [], False, False, []

    def _flush_p():
        if buf:
            out.append(f"<p>{_inline(' '.join(buf))}</p>"); buf.clear()

    def _flush_ul():
        nonlocal in_ul
        if in_ul: out.append("</ul>"); in_ul = False

    def _flush_tbl():
        # 02_findings/ is table-heavy: without this every result table rendered as one long
        # run-on paragraph of pipes, which is how a reader stops trusting the page.
        nonlocal in_tbl
        if in_tbl: out.append("</table>"); in_tbl = False

    for ln in joined:
        s = ln.rstrip()
        if not s.strip():
            _flush_p(); _flush_ul(); _flush_tbl(); continue
        if s.lstrip().startswith("|"):
            _flush_p(); _flush_ul()
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if all(c and set(c) <= set("-: ") for c in cells):
                continue                      # the |---|:--:| alignment row
            tag = "td" if in_tbl else "th"
            if not in_tbl:
                out.append("<table>"); in_tbl = True
            out.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        _flush_tbl()
        if s.startswith(("#", "-", "---")) or re.match(r"^\d+\. ", s):
            _flush_p()                        # a block starts → close any open paragraph
        if s.startswith("### "):
            _flush_ul(); out.append(f"<h3>{_inline(s[4:])}</h3>")
        elif s.startswith("## "):
            _flush_ul(); out.append(f"<h2>{_inline(s[3:])}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{_inline(s[2:])}</h1>")
        elif s.startswith("---"):
            _flush_ul(); out.append("<hr>")
        elif re.match(r"^\d+\. ", s):
            if not in_ul: out.append("<ol>"); in_ul = True
            out.append(f"<li>{_inline(re.sub(r'^[0-9]+[.] ', '', s))}</li>")
        elif s.lstrip().startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{_inline(s.lstrip()[2:])}</li>")
        else:
            buf.append(s.strip())             # accumulate wrapped paragraph lines
    _flush_p(); _flush_ul(); _flush_tbl()
    body = "\n".join(out)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'><title>What survived testing</title>
<style>
 body{{background:#0d1117;color:#e6edf3;font:16px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:26px;max-width:820px;margin-inline:auto}}
 a{{color:#58a6ff}} h1{{font-size:26px}} h2{{font-size:19px;margin-top:28px;border-bottom:1px solid #21262d;padding-bottom:5px}} h3{{font-size:16px;margin-top:20px;color:#58a6ff}}
 code{{background:#161b22;border:1px solid #21262d;border-radius:5px;padding:1px 6px;font-size:13px}} hr{{border:0;border-top:1px solid #21262d;margin:22px 0}}
 li{{margin:5px 0}} b{{color:#fff}} p{{color:#c9d1d9}} ul,ol{{padding-left:22px}}
 table{{border-collapse:collapse;margin:14px 0;font-size:14px;width:100%}}
 th,td{{border:1px solid #21262d;padding:5px 9px;text-align:left;color:#c9d1d9}}
 th{{color:#9aa4b2;font-weight:700;background:#161b22}}
 .back{{display:inline-block;margin-bottom:16px;font-weight:700;text-decoration:none}}
</style></head><body>
<a class=back href='/'>← back to dashboard</a>
{body}
<p style='margin-top:30px;color:#6e7681;font-size:13px'>Not financial advice. Paper-trade first.</p>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def _position_action(self):
        import urllib.parse
        u = urllib.parse.urlparse(self.path); q = dict(urllib.parse.parse_qsl(u.query))
        try:
            import positions as _pos, json as _json
            if u.path.startswith("/track") and q.get("strike") and q.get("prem"):
                sym = q.get("sym", "SPX")
                try:
                    under = _json.load(open(os.path.join(HERE, "data", f"periscope_{sym}.json"))).get("spot")
                except Exception:
                    under = None
                _pos.add(sym, q.get("dir", "call"), q["strike"], q["prem"], q.get("qty", 1) or 1, under)
            elif u.path.startswith("/close") and q.get("pid") and q.get("exitprem"):
                try:
                    under = _json.load(open(os.path.join(HERE, "data", "periscope_SPX.json"))).get("spot")
                except Exception:
                    under = None
                _pos.close(int(q["pid"]), q["exitprem"], under)
            elif u.path.startswith("/soldhalf") and q.get("pid"):
                _pos.mark_half(int(q["pid"]))
        except Exception:
            pass
        self.send_response(302); self.send_header("Location", "/"); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/refresh"):
            try:
                import gap_scanner, swing_signals, gex_signal, gex_periscope
                gex_signal.run()      # pull today's dealer-gamma regime (the 0DTE headline)
                for _s in ("^SPX", "^NDX"):
                    try:
                        gex_periscope.run(_s)   # live per-strike gamma levels, indexes traded
                    except Exception:
                        pass
                gap_scanner.run()
                swing_signals.run()   # manual refresh = fresh all three
                try:
                    import ai_desk; ai_desk.desk()          # refresh the AI desk brain
                except Exception:
                    pass
                try:
                    import ai_trader; ai_trader.decide()    # let the agent re-decide
                except Exception:
                    pass
            except Exception:
                pass
            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
        if self.path.startswith("/strategy"):
            b = strategy_page().encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path.startswith(("/track", "/close", "/soldhalf")):
            self._position_action(); return
        if self.path.startswith("/setacct"):
            import urllib.parse
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            try:
                if q.get("value"):
                    import growth_plan; growth_plan.set_account(q["value"])
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
    print(f"Day+Swing signals -> http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
