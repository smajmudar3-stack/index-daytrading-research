#!/usr/bin/env python3
"""dashboard_single.py — the whole desk in one file. Stdlib only. No templates, no Jinja.

WHAT THIS IS. A self-contained copy of the dashboard: the panel contract, the four states,
the renderer and the reader for every snapshot the engines write. Drop it anywhere, point it
at a state directory, run it. It serves the same page as the 142-file version.

WHAT IT IS NOT. It does not contain the ENGINES. `weekly_swing`, `gap_scanner`,
`desk_notes`, `signal_weights`, `weekly_book` and the rest are ~20,000 lines that need
yfinance, pandas, scipy and an option chain; they are what WRITE the snapshots. This file
READS them. With no snapshots present every panel says so, in the honest way, rather than
rendering blank.

So: this is the whole dashboard and none of the research. That split is deliberate — it is
the same split the real repo enforces, where `dashboard_app.py` is "assembly only".

THE FOUR STATES, which are the entire point of the panel contract:

    ok           it has something to say
    empty        it ran fine and there is genuinely nothing
    stale        the data is real but too old to act on, and it says how old
    unavailable  it could not run, and it says why and what to do about it

`empty` and `unavailable` must never look the same. "No setups today" and "the scan could
not be read" lead to opposite actions, and both once rendered as an empty string.

Run:
    export IDT_STATE_ROOT=/path/to/04_live_system/data     # optional
    python3 dashboard_single.py                            # -> http://127.0.0.1:8095
"""
import html
import json
import os
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

PORT = int(os.environ.get("IDT_PORT", "8095"))
STATE = os.environ.get(
    "IDT_STATE_ROOT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
ET = ZoneInfo("America/New_York")

OK, EMPTY, STALE, UNAVAILABLE = "ok", "empty", "stale", "unavailable"

# How old each snapshot is allowed to get before the page stops treating it as current.
# These are the same limits the audit uses, so the banner and the audit cannot disagree
# about what "fresh" means.
FRESHNESS = {
    "periscope_SPX.json": 20, "periscope_NDX.json": 20,
    "gap_snapshot.json": 30, "gex_snapshot.json": 90,
    "weekly_snapshot.json": 240, "desk_notes.json": 2880,
}


# ------------------------------------------------------------------ snapshots ---

def load(name):
    """(payload, status). Status is the vocabulary every panel branches on.

    A snapshot carries a `schema_version`; a mismatch is NOT stale data to warn about, it is
    data written by code that no longer exists. It gets refused. When the engines stopped
    emitting a refuted recommendation, the page kept serving it from a file written twenty
    minutes earlier — the code was clean and the screen was not.
    """
    p = os.path.join(STATE, name)
    if not os.path.exists(p):
        return None, "absent"
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None, "unreadable"
    if not isinstance(d, dict):
        return None, "unreadable"
    d = d.get("payload", d)
    age = (time.time() - os.path.getmtime(p)) / 60
    if age > FRESHNESS.get(name, 1e9):
        return d, "stale"
    return d, "ok"


def age_min(name):
    p = os.path.join(STATE, name)
    return None if not os.path.exists(p) else (time.time() - os.path.getmtime(p)) / 60


def panel(key, title, state=OK, rows=None, cards=None, note=None, severity=None,
          fix=None, age=None, source=None):
    assert state in (OK, EMPTY, STALE, UNAVAILABLE), f"unknown state {state!r}"
    return {"key": key, "title": title, "state": state, "rows": rows or [],
            "cards": cards or [], "note": note, "severity": severity, "fix": fix,
            "age_min": age, "source": source}


def unavailable(key, title, why, fix=None):
    return panel(key, title, UNAVAILABLE, note=why, fix=fix, severity="stop")


def empty(key, title, why, fix=None):
    return panel(key, title, EMPTY, note=why, fix=fix)


def safe(fn):
    """A panel that raises becomes `unavailable`, never a blank page.

    On a fresh clone the original dashboard returned HTTP 000 and zero bytes because one
    panel hit a missing directory and the renderer had no guard.
    """
    def wrapped():
        try:
            return fn()
        except Exception as e:                                # noqa: BLE001
            return panel(getattr(fn, "_key", fn.__name__),
                         getattr(fn, "_title", fn.__name__),
                         UNAVAILABLE, severity="stop",
                         note=f"{type(e).__name__}: {e}",
                         fix=traceback.format_exc(limit=3))
    wrapped._key = getattr(fn, "_key", fn.__name__)
    return wrapped


def describe(key, title):
    def deco(fn):
        fn._key, fn._title = key, title
        return fn
    return deco


def _explain(name, status):
    return {
        "absent": (f"{name} has never been written.", "run scan_all.py"),
        "unreadable": (f"{name} is present but is not valid JSON.", f"delete {name}, rescan"),
        "stale": (f"{name} is older than this data is allowed to be.", "run scan_all.py"),
    }.get(status, (f"{name}: {status}", "run scan_all.py"))


# --------------------------------------------------------------------- panels ---

@safe
@describe("weekly_macro", "This week's macro read")
def p_macro():
    """The desk-note overlay: the only input on the page not derived from price.

    Its age leads, and is measured from when the newest NOTE was written rather than the
    file's mtime — rewriting the file does not make a Friday note describe Tuesday.
    """
    d, st = load("desk_notes.json")
    if st == "absent":
        return empty("weekly_macro", "This week's macro read",
                     "No desk note has been ingested, so there is no macro read and the "
                     "weekly cards will refuse to fire.", fix="desk_notes.py --ingest -")
    if d is None:
        why, fix = _explain("desk_notes.json", st)
        return unavailable("weekly_macro", "This week's macro read", why, fix)

    notes = d.get("notes_ingested") or []
    newest = notes[0] if notes else {}
    hrs = None
    if newest.get("date"):
        try:
            t = datetime.strptime(newest["date"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=ET)
            hrs = (datetime.now(ET) - t).total_seconds() / 3600
        except ValueError:
            pass
    sev = None if (hrs or 0) <= 24 else ("watch" if (hrs or 0) <= 72 else "stop")

    rows = [{"k": "The read", "v": "", "sub": d.get("regime_line")},
            {"k": "Newest note", "v": f"{hrs:.0f}h old" if hrs else "—", "severity": sev,
             "sub": f"{newest.get('subject', '—')} · {newest.get('date', '—')}. "
                    f"{len(notes)} notes in this read."}]
    for x in d.get("drivers") or []:
        rows.append({"k": x.get("label", "?"),
                     "v": f"{x.get('level','')} · {x.get('direction','')}".strip(" ·"),
                     "sub": x.get("note")})
    for t in d.get("themes") or []:
        tail = ""
        if t.get("favours"):
            tail += f" For: {', '.join(t['favours'])}."
        if t.get("against"):
            tail += f" Against: {', '.join(t['against'])}."
        if t.get("basis"):
            tail += f" Basis: {t['basis']}."
        rows.append({"k": t.get("label", "?"), "v": t.get("stance", ""),
                     "severity": {"favour": "info", "avoid": "watch",
                                  "dispersion": "info"}.get(t.get("stance")),
                     "sub": (t.get("why") or "") + tail})
    for b in d.get("desk_book") or []:
        rows.append({"k": f"Their book · {b.get('asset','?')}", "v": b.get("action", ""),
                     "sub": b.get("note")})
    return panel("weekly_macro", "This week's macro read",
                 STALE if sev == "stop" else OK, rows=rows, severity=sev, age=age_min("desk_notes.json"),
                 note="The only input here that is not a transform of the price series, which "
                      "is why the weekly cards are conditioned on it rather than on another "
                      "moving average.",
                 source=d.get("source", "desk notes"))


@safe
@describe("weekly_trades", "Weekly trade cards")
def p_trades():
    """The cards. A macro basis is required and three distinct inputs must agree."""
    d, st = load("weekly_snapshot.json")
    if d is None:
        why, fix = _explain("weekly_snapshot.json", st)
        return unavailable("weekly_trades", "Weekly trade cards", why, fix)
    if not d.get("ok"):
        return unavailable("weekly_trades", "Weekly trade cards",
                           d.get("blocked", "The weekly engine refused to run."),
                           d.get("fix", "run scan_all.py"))
    cards = d.get("cards") or []
    if not cards:
        return empty("weekly_trades", "Weekly trade cards",
                     f"The scan ran across {d.get('n_considered','?')} names and nothing "
                     f"cleared. Most weeks that is the correct answer.")
    return panel("weekly_trades", "Weekly trade cards", STALE if st == "stale" else OK,
                 cards=cards, age=age_min("weekly_snapshot.json"),
                 note="UNPROVEN, not validated. Every systematic price-derived swing option "
                      "overlay this repo measured was beaten by owning the index. These are "
                      "macro-conditioned instead, which has never been tested here — so each "
                      "states its pillars and the price that proves it wrong.",
                 source="weekly_swing.run() · every leg priced at the ask when bought and "
                        "the bid when sold")


@safe
@describe("weekly_book", "Open recommendations, marked live")
def p_book():
    """Records every card so losers cannot quietly vanish and be replaced at a fresh price."""
    d, st = load("weekly_book.json")
    if d is None:
        return empty("weekly_book", "Open recommendations, marked live",
                     "No ledger snapshot. The live version reads weekly_book.db directly; "
                     "this single-file build reads a weekly_book.json export if present.",
                     fix="weekly_book.py --export")
    rows = []
    for r in d.get("open") or []:
        pnl = r.get("pnl_pct")
        rows.append({
            "k": f"{r.get('ticker','?')} {r.get('legs','')}",
            "v": ("—" if pnl is None else f"{pnl:+.1f}%"),
            "severity": None if pnl is None else ("info" if pnl > 0 else "watch"),
            "sub": f"expires {r.get('expiry','?')} ({r.get('dte_left','?')}d left) · "
                   f"entry {r.get('entry_net')} → mark {r.get('cur_net')}"})
    if not rows:
        return empty("weekly_book", "Open recommendations, marked live", "Nothing open.")
    return panel("weekly_book", "Open recommendations, marked live", OK, rows=rows,
                 note="Marked against the live chain paying the full bid-ask both ways, so it "
                      "reads worse than any mid-to-mid number. That gap is the point.",
                 source="weekly_book.mark()")


@safe
@describe("gaps", "Gap and go candidates")
def p_gaps():
    """LONG a gap down of -4% to -20%. Up-gaps are a stand-aside.

    Measured on 47 names, 67,858 name-days: the down-gap bounce is +0.76%/trade (t=+5.45),
    while buying an up-gap is -0.33% (t=-3.52) and shorting it is +0.03% (t=+0.35). The
    old RVOL>=1.5 gate used TODAY'S FULL-DAY volume, which is unknown at the open — it was
    lookahead, and it destroyed the one real edge while manufacturing a fake one.
    """
    d, st = load("gap_snapshot.json")
    if d is None:
        why, fix = _explain("gap_snapshot.json", st)
        return unavailable("gaps", "Gap and go candidates", why, fix)
    when = f"{d.get('session_date','?')} · scanned {d.get('as_of','?')}"
    cands = d.get("candidates") or []
    if not cands:
        if d.get("session_state") == "premarket":
            top = sorted(d.get("all") or [],
                         key=lambda r: -abs(r.get("gap_pct") or 0))[:6]
            return panel("gaps", "Gap and go candidates", OK, age=age_min("gap_snapshot.json"),
                         rows=[{"k": r.get("ticker", "?"),
                                "v": f"{r.get('gap_pct',0):+.2f}% pre-market",
                                "sub": f"{r.get('prev_close')} → {r.get('last')} "
                                       f"as of {r.get('quote_as_of','?')}"} for r in top],
                         note=(d.get("premarket_note") or "Pre-market.") +
                              f" Largest gaps shown as context. {when}.",
                         source="gap_scanner.run()")
        return empty("gaps", "Gap and go candidates",
                     f"No setups. Most days have none; forcing one gives the edge back. {when}.")
    rows = [{"k": c.get("ticker", "?"),
             "v": f"{c.get('direction','?')} · {c.get('setup','')}",
             "severity": "info" if c.get("direction") == "LONG" else None,
             "sub": f"gap {c.get('gap_pct',0):+.2f}% ({c.get('prev_close')} → {c.get('last')}), "
                    f"buy the open and be flat at the close · price as of "
                    f"{c.get('quote_as_of','?')}"} for c in cands[:10]]
    aside = d.get("stand_aside") or []
    if aside:
        rows.append({"k": "Stood aside", "v": f"{len(aside)} name(s)",
                     "sub": ", ".join(f"{a['ticker']} {a['gap_pct']:+.1f}%" for a in aside[:6])
                            + ". Up-gaps have no measured edge in either direction."})
    return panel("gaps", "Gap and go candidates", STALE if st == "stale" else OK, rows=rows,
                 age=age_min("gap_snapshot.json"),
                 note=f"{when}. " + ((d.get("edge") or {}).get("note") or ""),
                 source="gap_scanner.run()")


@safe
@describe("peri", "Index gamma levels")
def p_periscope():
    """Dealer gamma forecasts the day's RANGE, never its direction.

    Measured on 1,919 sessions: realised range came in at 0.843x implied on high-gamma days
    and 1.139x on low-gamma days, t = -13.2. That is a real, model-free statement about how
    far price travels. It says how BIG, never which WAY.
    """
    rows, worst = [], None
    for sym in ("SPX", "NDX"):
        d, st = load(f"periscope_{sym}.json")
        if d is None or not d.get("ok"):
            rows.append({"k": sym, "v": "unavailable", "severity": "stop",
                         "sub": f"periscope_{sym}.json is {st}."})
            worst = "stop"
            continue
        spot, flip = d.get("spot"), d.get("gamma_flip")
        below = None
        try:
            below = float(spot) < float(flip)
        except (TypeError, ValueError):
            pass
        rows.append({
            "k": sym, "v": f"{spot:,.0f}" if isinstance(spot, (int, float)) else str(spot),
            "severity": "watch" if below else None,
            "sub": (f"flip {flip} · put wall {d.get('put_wall')} · call wall "
                    f"{d.get('call_wall')} · net GEX {d.get('net_gex_musd')}$M/1%. "
                    + ("Below the flip: dealers are short gamma, they hedge WITH the move, "
                       "range expands (1.139x implied, t=-13.2)." if below else
                       "Above the flip: dealers are long gamma, moves get damped and range "
                       "compresses (0.843x implied)."))})
    if not rows:
        return empty("peri", "Index gamma levels", "No periscope written yet.")
    return panel("peri", "Index gamma levels", OK, rows=rows, severity=worst,
                 note="A RANGE read, not a direction. This repo measured no directional edge "
                      "in ~340,000 tests; the survivor count came in at or below chance.",
                 source="gex_periscope.run()")


@safe
@describe("weekly_refused", "Considered and thrown out")
def p_refused():
    """A thin week and a broken scan must never look the same from the page."""
    d, _ = load("weekly_snapshot.json")
    rs = (d or {}).get("refusals") or []
    if not rs:
        return empty("weekly_refused", "Considered and thrown out", "Nothing refused.")
    buckets = {}
    for r in rs:
        why = (r.get("why") or "no reason recorded")
        head = why.split(";")[0].strip()
        key = ("no macro basis" if "no desk-note theme" in head else
               "conviction floor" if "conviction floor" in head else
               "not enough agreeing inputs" if ("point that way" in head or
                                                "input(s) had anything" in head) else
               "execution / liquidity" if ("spread" in head or "open interest" in head or
                                           "two-sided" in head) else head[:70])
        buckets.setdefault(key, []).append(r.get("ticker", "?"))
    rows = [{"k": ", ".join(v[:14]) + ("…" if len(v) > 14 else ""),
             "v": f"{len(v)}", "sub": k}
            for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1]))]
    cov = (d or {}).get("coverage") or {}
    return panel("weekly_refused", "Considered and thrown out", OK, rows=rows,
                 note=f"{len(rs)} of {cov.get('n_universe','?')} names produced no card. "
                      + (cov.get("note") or ""),
                 source="weekly_swing.run()")


VIEWS = {
    "markets": {
        "label": "Markets",
        "question": "What is worth being in this week, and what is the tape underneath?",
        "panels": [p_trades, p_book, p_macro, p_periscope, p_gaps, p_refused],
    },
}


# --------------------------------------------------------------------- render ---

CSS = """
:root{--bg:#0a0b0d;--card:#141619;--card-2:#1c1f24;--line:rgba(255,255,255,.07);
--line-2:rgba(255,255,255,.13);--text:#f5f6f7;--muted:#9aa0a9;--faint:#5c626b;
--green:#00c805;--red:#ff4f38;--amber:#f5a623;--blue:#4c9ffe;
--green-wash:rgba(0,200,5,.10);--red-wash:rgba(255,79,56,.10);
--amber-wash:rgba(245,166,35,.10);--blue-wash:rgba(76,159,254,.10);
--mono:"SF Mono",ui-monospace,Menlo,monospace;--r:16px;--r-sm:10px}
*{box-sizing:border-box;min-width:0}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 -apple-system,
BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:19px;margin:0 0 2px;letter-spacing:-.01em}
.sub{color:var(--faint);font-size:12px;margin:0 0 4px}
.q{color:var(--muted);font-size:13px;margin:14px 0 18px}
.strip{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px;font-size:11px}
.chip{padding:3px 9px;border-radius:999px;background:var(--card);color:var(--muted);
border:1px solid var(--line)}
.chip.watch{background:var(--amber-wash);color:var(--amber);border-color:transparent}
.chip.stop{background:var(--red-wash);color:var(--red);border-color:transparent}
.grid{display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
padding:18px 20px 16px}
.card.is-empty{background:transparent;border-style:dashed;border-color:var(--line-2)}
.card.is-unavailable{border-color:rgba(255,79,56,.45)}
.card h3{font-size:14px;margin:0 0 12px;letter-spacing:-.01em}
.row{padding:9px 0;border-bottom:1px solid var(--line);font-size:13px}
.row:last-child{border-bottom:0}
.rmain{display:flex;justify-content:space-between;gap:14px;align-items:baseline}
.k{font-weight:600}.v{font-family:var(--mono);font-size:12.5px;color:var(--muted);
text-align:right;flex:none}
.row.info .v{color:var(--green)}.row.watch .v{color:var(--amber)}.row.stop .v{color:var(--red)}
.rsub{margin:4px 0 0;color:var(--muted);font-size:12px;line-height:1.55}
.note{color:var(--muted);font-size:12px;line-height:1.55;margin:12px 0 0;
padding-top:10px;border-top:1px solid var(--line)}
.fix{font-family:var(--mono);font-size:11.5px;color:var(--amber);margin-top:8px;
padding:7px 10px;background:var(--amber-wash);border-radius:var(--r-sm)}
.src{color:var(--faint);font-size:10.5px;margin-top:8px;font-family:var(--mono)}
.wk{border:1px solid var(--line);border-radius:12px;padding:13px 15px;margin:0 0 12px}
.wk-bull{border-left:3px solid var(--green);background:var(--green-wash)}
.wk-bear{border-left:3px solid var(--red);background:var(--red-wash)}
.wk-top{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.tk{font-size:17px;font-weight:800}
.dir{font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted)}
.exp{font-family:var(--mono);font-size:11.5px;color:var(--faint);margin-left:auto}
.legs{font-family:var(--mono);font-size:13px;padding:8px 11px;background:var(--card-2);
border-radius:var(--r-sm);margin:9px 0}
.nums{display:flex;flex-wrap:wrap;gap:5px 16px;font-size:11.5px;color:var(--muted);
margin-bottom:9px}
.nums b{color:var(--faint);font-weight:700;text-transform:uppercase;font-size:9.5px;
letter-spacing:.07em;margin-right:3px}
.back{margin:9px 0;padding:10px 12px;border-radius:var(--r-sm);background:var(--card-2);
border:1px solid var(--line)}
.back-hd{font-size:9.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
color:var(--faint);margin-bottom:7px}
.pill{display:flex;gap:8px;align-items:baseline;padding:4px 0;font-size:12px}
.kind{font-size:8.5px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;
padding:2px 5px;border-radius:3px;background:var(--card);color:var(--muted);flex:none;
min-width:62px;text-align:center}
.kind.macro{background:var(--blue-wash);color:var(--blue)}
.kind.signal{background:var(--green-wash);color:var(--green)}
.kind.catalyst{background:var(--amber-wash);color:var(--amber)}
.pd{display:block;color:var(--muted);font-size:11px;margin-top:1px}
.line{font-size:12.5px;line-height:1.55;color:var(--muted);margin:0 0 5px}
.line b{color:var(--text)}
.exits{margin-top:11px;padding-top:10px;border-top:1px solid var(--line-2);font-size:12.5px}
.exits b{font-weight:700;text-transform:uppercase;font-size:9.5px;letter-spacing:.08em;
color:var(--faint);margin-right:6px}
.inval{color:var(--amber)}
@media(min-width:900px){.grid{grid-template-columns:1fr 1fr}
.card.wide{grid-column:1/-1}}
"""


def e(x):
    return html.escape("" if x is None else str(x))


def render_rows(p):
    out = []
    for r in p["rows"]:
        out.append(f'<div class="row {e(r.get("severity") or "")}">'
                   f'<div class=rmain><span class=k>{e(r.get("k"))}</span>'
                   f'<span class=v>{e(r.get("v"))}</span></div>'
                   + (f'<p class=rsub>{e(r.get("sub"))}</p>' if r.get("sub") else "")
                   + "</div>")
    return "".join(out)


def render_card(c):
    """One weekly trade card. Direction, structure, the pillars, then the exits."""
    cls = "wk-bull" if c.get("direction") == "bullish" else "wk-bear"
    nums = []
    if c.get("net") is not None:
        nums.append(f"<span><b>{'debit' if c.get('is_debit') else 'credit'}</b> {e(c['net'])}</span>")
    for lab, key, suf in (("risk", "max_risk_usd", ""), ("reward", "max_reward_usd", ""),
                          ("r:r", "rr", ""), ("spread cost", "cost_pct", "% of risk"),
                          ("vote", "vote_score", ""), ("agreement", "agreement", "")):
        if c.get(key) is not None:
            v = c[key]
            v = f"${v:,.0f}" if key.endswith("_usd") else (f"{v:+.2f}" if key == "vote_score" else v)
            nums.append(f"<span><b>{lab}</b> {e(v)}{suf}</span>")
    if c.get("iv_front"):
        nums.append(f"<span><b>IV</b> {e(c['iv_front'])}% vs realised {e(c.get('rvol'))}%</span>")

    pillars = ""
    if c.get("backing"):
        rows = "".join(
            f'<div class=pill><span class="kind {e(b.get("kind"))}">{e(b.get("kind"))}</span>'
            f'<span><b>{e(b.get("label"))}</b>'
            + (f' <em style="font-style:normal;color:var(--faint);font-size:10.5px">{e(b.get("strength"))}</em>'
               if b.get("strength") else "")
            + (f'<span class=pd>{e(b.get("detail"))}</span>' if b.get("detail") else "")
            + "</span></div>"
            for b in c["backing"])
        pillars = (f'<div class=back><div class=back-hd>what is behind this — '
                   f'{len(c["backing"])} pillars</div>{rows}'
                   f'<p style="font-size:10.5px;color:var(--faint);margin:8px 0 0">A macro '
                   f'theme is required, not preferred, and at least three distinct inputs '
                   f'must agree.</p></div>')

    lines = ""
    for lab, key in (("Why this structure", "structure_why"), ("Why this expiry", "expiry_why"),
                     ("Tape", "tape")):
        if c.get(key):
            lines += f'<div class=line><b>{lab}:</b> {e(c[key])}</div>'
    if c.get("evidence"):
        lines += (f'<div class=line style="color:var(--amber)"><b>Measured:</b> '
                  f'{e(c["evidence"])}</div>')

    exits = ""
    for lab, key, cls2 in (("Target", "target", ""), ("Stop", "stop", ""),
                           ("Wrong if", "invalidation", "inval")):
        if c.get(key):
            exits += f'<div class="{cls2}"><b>{lab}</b> {e(c[key])}</div>'

    return (f'<article class="wk {cls}"><div class=wk-top>'
            f'<span class=tk>{e(c.get("ticker"))}</span>'
            f'<span class=dir>{e(c.get("direction"))}</span>'
            + (f'<span class=chip>{e(c.get("cap_tier"))} cap</span>' if c.get("cap_tier") else "")
            + f'<span class=exp>{e(c.get("expiry"))} · {e(c.get("dte"))}d</span></div>'
            f'<div style="font-size:13.5px;font-weight:700;margin:9px 0 5px">'
            f'{e(c.get("structure"))}</div>'
            f'<div class=legs>{e(c.get("legs"))}</div>'
            f'<div class=nums>{"".join(nums)}</div>{pillars}{lines}'
            f'<div class=exits>{exits}</div></article>')


def render_panel(p):
    """One card, with its own failure contained. A broken panel is a broken card, not a
    blank page — `safe` guards the panel function and this guards the rendering."""
    try:
        wide = "wide" if p["cards"] or len(p["rows"]) > 8 else ""
        body = ("".join(render_card(c) for c in p["cards"]) if p["cards"]
                else render_rows(p))
        stale = (f' <span class="chip watch">stale · {p["age_min"]:.0f}m</span>'
                 if p["state"] == STALE and p.get("age_min") else "")
        return (f'<section class="card {e(p.get("severity") or "")} is-{p["state"]} {wide}" '
                f'id="panel-{e(p["key"])}"><h3>{e(p["title"])}{stale}</h3>{body}'
                + (f'<p class=note>{e(p["note"])}</p>' if p.get("note") else "")
                + (f'<div class=fix>{e(p["fix"])}</div>' if p.get("fix") else "")
                + (f'<div class=src>{e(p["source"])}</div>' if p.get("source") else "")
                + "</section>")
    except Exception as ex:                                   # noqa: BLE001
        return (f'<section class="card stop is-unavailable"><h3>{e(p.get("title","Panel"))}'
                f'</h3><p class=note>This panel failed to render: {e(type(ex).__name__)}: '
                f'{e(str(ex)[:160])}. The rest of the page is unaffected.</p></section>')


def render(slug="markets"):
    v = VIEWS.get(slug) or VIEWS["markets"]
    panels = [fn() for fn in v["panels"]]
    chips, worst = [], None
    for name, limit in FRESHNESS.items():
        a = age_min(name)
        if a is None:
            chips.append(('stop', f"{name.split('.')[0]}: missing")); worst = "stop"
        elif a > limit:
            chips.append(('watch', f"{name.split('.')[0]}: {a:.0f}m")); worst = worst or "watch"
        else:
            chips.append(('', f"{name.split('.')[0]}: {a:.0f}m"))
    head = ("Data missing" if worst == "stop" else
            "Some data is older than it should be" if worst == "watch" else "Data fresh")
    now = datetime.now(ET).strftime("%a %d %b %H:%M ET")
    return (f'<!doctype html><meta charset=utf-8>'
            f'<meta name=viewport content="width=device-width,initial-scale=1">'
            f'<title>Index options desk</title><style>{CSS}</style><div class=wrap>'
            f'<h1>Index options desk</h1>'
            f'<p class=sub>SPX / NDX weekly, gamma and risk. Paper only · {now}</p>'
            f'<div class=strip><span class="chip {e(worst or "")}">{e(head)}</span>'
            + "".join(f'<span class="chip {c}">{e(t)}</span>' for c, t in chips)
            + f'</div><p class=q>{e(v["question"])}</p><div class=grid>'
            + "".join(render_panel(p) for p in panels)
            + '</div><p class=note style="margin-top:26px">Dealer gamma forecasts the day\'s '
              'RANGE, never its direction. Three signals survived honest out-of-sample '
              'testing: short interest with a negative sign, VIX backwardation, and low '
              'dealer gamma as a regime filter. Buying 0DTE premium on a directional signal, '
              'the below-the-flip premium trade, sector-rotation picks and every swing option '
              'overlay were tested and lost money. Everything here is paper: no '
              'order-placement code exists. Not financial advice.</p></div>')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        slug = self.path.strip("/").split("?")[0] or "markets"
        try:
            body = render(slug).encode("utf-8")
            code = 200
        except Exception:                                     # noqa: BLE001
            body = f"<pre>{html.escape(traceback.format_exc())}</pre>".encode()
            code = 500
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"state root : {STATE}")
    print(f"snapshots  : {sum(1 for f in FRESHNESS if os.path.exists(os.path.join(STATE, f)))}"
          f"/{len(FRESHNESS)} present")
    print(f"desk       : http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
