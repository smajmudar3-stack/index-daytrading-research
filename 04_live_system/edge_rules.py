"""edge_rules.py — the four things that survived testing, with live state.

Everything here is measured, not asserted, and each row carries the evidence that
earned it a place. Two are live signals with current state; two are standing
execution rules that apply to every trade regardless of setup.

Deliberately compact. The dashboard already carries too much prose that never
changes, so this shows the rule, the number behind it, and where applicable what
it says right now -- nothing else. Full derivations live in
BUNDLE/02_findings/.

Every function degrades to a safe value rather than raising: a stale VIX or a
missing file must never take the render down.
"""
import json
import os
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "data", "edge_state.json")
TTL = 900          # 15 min; term structure does not move fast enough to matter


# ---------------------------------------------------------------- live state
def _cached():
    try:
        with open(CACHE) as f:
            c = json.load(f)
        if time.time() - c.get("ts", 0) < TTL:
            return c
    except (OSError, ValueError):
        pass
    return None


def vix_term():
    """VIX vs VIX3M. Backwardation (spot above 3-month) is the measured signal.

    Returns (state, ratio, note) with state in {'BACKWARDATION','CONTANGO',None}.
    """
    c = _cached()
    if c and c.get("vix") is not None:
        return c["vix_state"], c["vix_ratio"], c["vix_note"]
    try:
        import yfinance as yf
        d = yf.download(["^VIX", "^VIX3M"], period="5d", progress=False,
                        auto_adjust=False)["Close"].dropna()
        if d.empty:
            return None, None, "no VIX data"
        spot = float(d["^VIX"].iloc[-1])
        three = float(d["^VIX3M"].iloc[-1])
        ratio = spot / three if three else None
        if ratio is None:
            return None, None, "no VIX3M"
        back = ratio > 1.0
        state = "BACKWARDATION" if back else "CONTANGO"
        note = (f"VIX {spot:.1f} over VIX3M {three:.1f} — stress, signal ON"
                if back else
                f"VIX {spot:.1f} under VIX3M {three:.1f} — calm, signal OFF")
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with open(CACHE, "w") as f:
                json.dump({"ts": time.time(), "vix": spot, "vix_ratio": ratio,
                           "vix_state": state, "vix_note": note}, f)
        except OSError:
            pass
        return state, ratio, note
    except Exception as e:                       # never break the dashboard
        return None, None, f"unavailable ({type(e).__name__})"


def short_weight():
    """Live weight and direction of the short-interest signal, from the registry."""
    try:
        import signal_weights as sw
        w, tier = sw.weight("short_float_pct")[:2]
        return w, tier
    except Exception:
        return None, None


# ---------------------------------------------------------------- the edges
def edges():
    """The four survivors. `live` rows carry current state; `rule` rows always apply."""
    vstate, vratio, vnote = vix_term()
    w, tier = short_weight()

    on = vstate == "BACKWARDATION"
    return [
        dict(kind="live", name="Short interest",
             rule="High short float predicts LOWER returns — short it, don't squeeze it",
             evidence="IC −0.107 @63d · n=13,219 · monotone across every bucket",
             state=("ACTIVE" if w else "OFFLINE"),
             tone=("go" if w else "mut"),
             now=(f"weight {w:.2f} in the swing vote, direction NEGATIVE ({tier})"
                  if w else "signal registry unavailable"),
             horizon="multi-week"),
        dict(kind="live", name="VIX backwardation",
             rule="Spot VIX above VIX3M — the only signal that held across all three splits",
             evidence="t +3.9 / +2.8 / +2.1 on train / validate / test",
             state=("FIRING" if on else "QUIET" if vstate else "NO DATA"),
             tone=("go" if on else "mut"),
             now=vnote,
             horizon="multi-week"),
        dict(kind="rule", name="Hold credit structures to expiry",
             rule="Never close early — expiry settles at intrinsic and pays the spread ONCE",
             evidence="closing early pays it twice: +$63/contract held vs negative closed (t=2.88, n=1,240)",
             state="STANDING", tone="info",
             now="applies to every condor, strangle and spread on this dashboard",
             horizon="all"),
        dict(kind="rule", name="Far-OTM: execution beats selection",
             rule="Filter spread ≤20% and use 16–30Δ — never the far tail",
             evidence="spread filter: −45.6% → +5.6% · delta band: −90% at the tail → +26.1% at 16–30Δ",
             state="STANDING", tone="info",
             now="gates the Black Swan tab; which contract matters more than why you bought it",
             horizon="all"),
    ]


DEAD = [
    ("Intraday direction", "ceiling 52.9% vs a 69.3% cost hurdle — theta, not signal"),
    ("Candlestick / chart patterns", "significant on 4,152 stocks, Cohen's d 0.026 — smaller than the spread"),
    ("Dealer-gamma momentum", "did not replicate: β −0.02 here vs +6.63 published"),
    ("Opening-range breakout", "+1.18bp (t 0.34) entered at the break; edge lives inside the spread"),
    ("Credit structures closed early", "negative at |t| > 9 across 147,350 real-quote trades"),
    ("Far-OTM lottery buying", "−90% to −48% over 10.5M purchases held to expiry"),
    ("Earnings straddles", "−35.03% per trade, t = −95.7"),
    ("Sector rotation", "IC ≈ 0 — pinned to a hard zero in the registry"),
]


# ---------------------------------------------------------------- rendering
def panel():
    """Compact HTML for the dashboard. Returns '' on any failure."""
    try:
        rows = edges()
    except Exception:
        return ""

    def row(e):
        return (
            f"<div class='edge {e['tone']}'>"
            f"<div class=ehead><span class=ename>{e['name']}</span>"
            f"<span class='pill {e['tone']}'>{e['state']}</span>"
            f"<span class=ehz>{e['horizon']}</span></div>"
            f"<div class=erule>{e['rule']}</div>"
            f"<div class=enow>{e['now']}</div>"
            f"<div class=eev>{e['evidence']}</div></div>")

    live = "".join(row(e) for e in rows if e["kind"] == "live")
    rule = "".join(row(e) for e in rows if e["kind"] == "rule")
    dead = "".join(f"<div class=deadrow><b>{n}</b><span>{w}</span></div>"
                   for n, w in DEAD)

    return f"""<div class='card edges'>
  <div class=ahead>🎯 The edge — what survived testing</div>
  <div class=esub>Four findings from five research sweeps and ~15 in-house tests on real quotes.
    Two are live signals; two are standing execution rules.</div>
  <div class=egroup>SIGNALS · traded on the swing book</div>
  {live}
  <div class=egroup>EXECUTION RULES · apply to every trade</div>
  {rule}
  <details class=deadwrap><summary>Tested and dead — {len(DEAD)} strategies, do not retry</summary>
    <div class=deadlist>{dead}</div>
    <div class=hint>Nothing here supports outsized weekly returns. The measured signals are
      information coefficients around 0.1 — real, and small. Full derivations in BUNDLE/02_findings/.</div>
  </details>
</div>"""


CSS = """
 .edges{border:1px solid var(--line);border-radius:var(--r);background:var(--surface);padding:16px 18px;margin:10px 0}
 .esub{font-size:12px;color:var(--muted);margin:-2px 0 14px;line-height:1.5}
 .egroup{font-size:10px;font-weight:800;letter-spacing:.1em;color:var(--muted);margin:14px 0 8px;
   padding-bottom:5px;border-bottom:1px solid var(--line2)}
 .egroup:first-of-type{margin-top:0}
 .edge{border-left:3px solid var(--line);padding:9px 0 9px 12px;margin:9px 0}
 .edge.go{border-left-color:var(--go)} .edge.info{border-left-color:var(--info)}
 .edge.mut{border-left-color:var(--muted)} .edge.warn{border-left-color:var(--warn)}
 .ehead{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
 .ename{font-weight:700;font-size:14.5px}
 .ehz{font-size:10.5px;color:var(--muted);margin-left:auto;font-family:ui-monospace,Menlo,monospace}
 .erule{font-size:13px;line-height:1.5;margin-top:3px}
 .enow{font-size:12px;color:var(--info);margin-top:4px;line-height:1.45}
 .eev{font-size:11px;color:var(--muted);margin-top:4px;font-family:ui-monospace,Menlo,monospace;
   overflow-wrap:anywhere}
 .deadwrap{margin-top:16px;padding-top:12px;border-top:1px solid var(--line2)}
 .deadwrap summary{font-size:12px;color:var(--muted);cursor:pointer;user-select:none}
 .deadwrap summary:hover{color:var(--text)}
 .deadlist{margin-top:10px}
 .deadrow{display:flex;gap:12px;font-size:11.5px;padding:5px 0;border-bottom:1px solid var(--line2);
   align-items:baseline;flex-wrap:wrap}
 .deadrow b{min-width:210px;color:var(--text);font-weight:600}
 .deadrow span{color:var(--muted);flex:1;font-family:ui-monospace,Menlo,monospace;font-size:10.5px}
"""
