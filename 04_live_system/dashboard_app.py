"""The dashboard server. Assembly only: it renders panel dicts through templates.

This replaced a 1,533-line module that held the CSS, the markup, the panel logic and
the HTTP handler in one file, with a single render() returning the entire page as one
f-string. The split is what makes the panels testable, and Phase 5's suite asserts on
the dicts rather than grepping a wall of HTML.

Routes:
  /                  redirect to the default view
  /<view>            a full page
  /<view>?partial=1  just <main>, for the in-place refresh
  /static/<f>        the stylesheet and the refresh script
  /docs              what this system knows, rendered from 02_findings/WHAT_WORKS.md
  /refresh           run a cycle, then return to the view you were on
"""
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402
from markupsafe import Markup  # noqa: E402

from panels import views  # noqa: E402

# Overridable, because 8095 is not free on every machine and a recipient hitting
# "OSError: [Errno 48] Address already in use" has no obvious next move when the number is
# baked into the source. `IDT_PORT=8096 python3 dashboard_app.py` is the escape hatch.
PORT = int(os.environ.get("IDT_PORT", "8095"))
TEMPLATES = os.path.join(HERE, "templates")
STATIC = os.path.join(HERE, "static")

# ---------------------------------------------------------------- refresh
# The old handler did `import scan_all`, which is wrong twice over.
#
#   1. IT ONLY EVER RAN ONCE. Python caches modules in sys.modules, so the
#      second press of "Refresh the desk" and every press after it was a
#      silent no-op that still returned a cheerful 302. That is precisely the
#      reported symptom: pressing refresh did nothing.
#   2. WHEN IT DID RUN, IT BLOCKED THE SERVER. scan_all has no main() and no
#      __main__ guard, so the whole ~3-minute cycle executed inside the request
#      handler of a single-threaded HTTPServer. The page hung until it finished.
#
# Fix: run it as a SUBPROCESS (a fresh interpreter re-executes it every time)
# on a background thread, and report real status instead of guessing.
_refresh = {"state": "idle", "started": None, "finished": None, "error": None}
_refresh_lock = threading.Lock()


def refresh_state():
    """A copy for the template. Includes how long ago, so 'done' cannot mislead."""
    with _refresh_lock:
        d = dict(_refresh)
    for k in ("started", "finished"):
        if d.get(k):
            d[k + "_ago_s"] = int(time.time() - d[k])
    return d


def _run_cycle():
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", os.path.dirname(HERE))
    try:
        r = subprocess.run([sys.executable, "scan_all.py"], cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=900)
        err = None if r.returncode == 0 else (
            (r.stderr or r.stdout or "").strip().splitlines() or ["failed"])[-1][:200]
    except subprocess.TimeoutExpired:
        err = "cycle exceeded 15 minutes and was killed"
    except Exception as e:                                    # noqa: BLE001
        err = f"{type(e).__name__}: {e}"[:200]
    with _refresh_lock:
        _refresh.update(state="failed" if err else "done",
                        finished=time.time(), error=err)


def start_refresh():
    """Kick a cycle off unless one is already running. Returns what happened."""
    with _refresh_lock:
        if _refresh["state"] == "running":
            return "already running"
        _refresh.update(state="running", started=time.time(),
                        finished=None, error=None)
    threading.Thread(target=_run_cycle, daemon=True).start()
    return "started"


# Cache-bust the stylesheet without a build step: the newest mtime under static/.
def asset_version():
    try:
        return str(int(max(os.path.getmtime(os.path.join(STATIC, f))
                           for f in os.listdir(STATIC))))
    except (OSError, ValueError):
        return "0"


env = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

FOOTER = (
    "Dealer gamma forecasts the day's RANGE, never its direction. Three signals survived "
    "honest out-of-sample testing: short interest with a negative sign, VIX backwardation, "
    "and low dealer gamma as a regime filter. The 0DTE condor is approximately break-even "
    "on real quotes and is treated as unproven. Buying 0DTE premium on a directional signal, "
    "the below-the-flip premium trade, sector-rotation swing picks and every swing option "
    "overlay were tested and lost money; see docs/VERDICT_LOG.md. Everything here is paper: "
    "no order-placement code exists in this repo. Not financial advice."
)


def _session_ctx():
    """Market state and the ET clock for the masthead. Never raises into a render."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/New_York"))
    try:
        import session
        awake = bool(session.awake())
    except Exception:                               # noqa: BLE001
        awake = None
    return {"market_open": awake, "now_et": now.strftime("%H:%M")}


def _render_panel(tpl, p):
    """One panel, rendered, with its TEMPLATE failure contained to that card.

    `panels.safe` guards a panel FUNCTION, so a panel that raises becomes an `unavailable`
    card instead of taking the page down. Nothing guarded the template. On 2026-09-03 a
    missing dict key in weekly_book.html raised inside Jinja and `/markets` served ZERO
    BYTES — the exact HTTP-000 failure the panel contract was written to stop, one layer
    lower than the contract reached.

    A broken template is now a broken card that says so, and the other nine still render.
    """
    try:
        return tpl.render(p=p)
    except Exception as e:                                    # noqa: BLE001
        import html as _h
        import traceback
        traceback.print_exc()
        return (f'<section class="card stop is-unavailable" id="panel-{_h.escape(str(p.get("key","?")))}">'
                f'<h3>{_h.escape(str(p.get("title", "Panel")))}</h3>'
                f'<p class=note>This panel\'s template failed to render: '
                f'{_h.escape(type(e).__name__)}: {_h.escape(str(e)[:160])}. '
                f'The rest of the page is unaffected.</p>'
                f'<div class=fix>Fix templates/panels/{_h.escape(str(p.get("key","?")))}.html</div>'
                f'</section>')


def render_view(slug, partial=False):
    panels = views.build(slug)
    v = views.view_by_slug(slug)
    ctx = {
        "title": "Index Options Desk",
        "subtitle": "SPX / NDX 0DTE, swing and risk. Paper only.",
        **_session_ctx(),
        "views": [{"slug": x["slug"], "label": x["label"]} for x in views.VIEWS],
        "view": v["slug"],
        "view_label": v["label"],
        "view_question": v["question"],
        "panels": panels,
        "status": views.status(),
        "footer": FOOTER,
        "asset_version": asset_version(),
    }
    if partial:
        # Only the panels, for the in-place swap.
        out = []
        tpl = env.get_template("panel.html")
        for p in panels:
            out.append(_render_panel(tpl, p))
        return "\n".join(out)
    # Pre-render each card through the guard, so one bad template cannot blank the page.
    tpl = env.get_template("panel.html")
    ctx["rendered_panels"] = [_render_panel(tpl, p) for p in panels]
    return env.get_template("view.html").render(**ctx)


def render_docs():
    """What this system knows, from the CURRENT findings — never a superseded document.

    The old "How it works" button served 01_START_HERE/STRATEGY_0DTE.md, which is the
    refuted document, and it did so from a path that had never existed, so the button
    had been serving nothing at all.
    """
    import html as _html
    import re

    candidates = [
        os.path.join(os.path.dirname(HERE), "02_findings", "WHAT_WORKS.md"),
        os.path.join(os.path.dirname(HERE), "docs", "VERDICT_LOG.md"),
    ]
    src = next((p for p in candidates if os.path.exists(p)), None)
    if not src:
        body = ("<p>Expected <code>02_findings/WHAT_WORKS.md</code> and it is not there. "
                "Nothing is being hidden; the file is missing.</p>")
    else:
        with open(src, encoding="utf-8") as fh:
            text = fh.read()

        def _inline(t):
            t = _html.escape(t)
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
            t = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", t)
            t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
            # Markdown links. A raw [text](file.md) on screen reads as broken, so
            # point .md targets at the docs route (best effort) and leave the rest.
            t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1", t)
            return t

        # Source lines are wrapped at ~90 columns, so one line is NOT one paragraph.
        # The first pass here rendered each line as its own <p>, which shattered every
        # paragraph into single sentences with a blank row between them.
        out = []
        para = []

        def _flush():
            # Inline conversion happens AFTER the join: emphasis can span a source
            # line wrap ("*structure\ntype*"), and per-line conversion misses it.
            if para:
                out.append(f"<p>{_inline(' '.join(para))}</p>")
                para.clear()

        in_table = False
        for line in text.splitlines():
            stripped = line.strip()
            if line.startswith("|"):
                _flush()
                cells = [c.strip() for c in _inline(line).strip("|").split("|")]
                if set("".join(c.replace("&#8212;", "-") for c in cells)) <= set("-: "):
                    continue
                if not in_table:
                    out.append("<table>")
                    in_table = True
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
                continue
            if in_table:
                out.append("</table>")
                in_table = False
            if stripped in ("---", "***", "___"):
                _flush()
                continue
            if line.startswith("### "):
                _flush(); out.append(f"<h3>{_inline(line[4:])}</h3>")
            elif line.startswith("## "):
                _flush(); out.append(f"<h2>{_inline(line[3:])}</h2>")
            elif line.startswith("# "):
                _flush(); out.append(f"<h1>{_inline(line[2:])}</h1>")
            elif not stripped:
                _flush()
            else:
                para.append(line.strip())
        _flush()
        if in_table:
            out.append("</table>")
        body = "\n".join(out)
    return env.get_template("docs.html").render(
        title="Index Options Desk",
        **_session_ctx(),
        subtitle=f"from {os.path.relpath(src, os.path.dirname(HERE))}" if src else "source missing",
        views=[{"slug": x["slug"], "label": x["label"]} for x in views.VIEWS],
        view="docs",
        view_label="Findings",
        view_question="The current findings. Superseded documents live in 07_superseded/.",
        panels=[],
        status=views.status(),
        footer=FOOTER,
        asset_version=asset_version(),
        raw=Markup(body),
    )


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        path = u.path.rstrip("/") or "/"

        if path == "/":
            self.send_response(302)
            self.send_header("Location", f"/{views.DEFAULT_VIEW}")
            self.end_headers()
            return

        if path.startswith("/static/"):
            name = os.path.basename(path)
            fp = os.path.join(STATIC, name)
            if not os.path.exists(fp):
                self._send(f"not found: {name}", "text/plain; charset=utf-8", 404)
                return
            ctype = "text/css" if name.endswith(".css") else "application/javascript"
            with open(fp, "rb") as fh:
                self._send(fh.read(), f"{ctype}; charset=utf-8")
            return

        if path == "/docs":
            self._send(render_docs())
            return

        if path == "/refresh":
            back = q.get("view", views.DEFAULT_VIEW)
            # Returns IMMEDIATELY. The cycle runs on a thread and the page polls
            # /refresh_status, so the button never hangs the browser again.
            start_refresh()
            self.send_response(302)
            self.send_header("Location", f"/{back}")
            self.end_headers()
            return

        # "I took this one" / "I'm out". A GET so a plain link works with no JavaScript and
        # no form plumbing; it changes only a flag in the paper book and places no order.
        # `risk_gates.DRY_RUN` is True and `LIVE_AGENT` is False — a test asserts no
        # order-placement code exists anywhere in this repo, and this does not add any.
        if path in ("/entered", "/exited"):
            import weekly_book
            tk = (q.get("ticker") or "").upper()
            exp = q.get("expiry") or ""
            struct = q.get("structure") or None
            fill = q.get("fill")
            try:
                fill = float(fill) if fill else None
            except ValueError:
                fill = None
            if path == "/entered":
                res = weekly_book.mark_entered(tk, exp, struct, fill)
            else:
                res = weekly_book.mark_exited(tk, exp, struct)
            back = q.get("view", views.DEFAULT_VIEW)
            note = "" if res.get("ok") else (
                "?book_error=" + urllib.parse.quote(str(res.get("why", "failed"))[:120]))
            self.send_response(302)
            self.send_header("Location", f"/{back}{note}#panel-weekly_book")
            self.end_headers()
            return

        if path == "/refresh_status":
            import json as _json
            self._send(_json.dumps(refresh_state()), "application/json")
            return

        slug = path.lstrip("/")
        if slug not in [v["slug"] for v in views.VIEWS]:
            self._send(f"no such view: {slug}", "text/plain; charset=utf-8", 404)
            return

        partial = q.get("partial") == "1" or self.headers.get("X-Partial") == "1"
        self._send(render_view(slug, partial=partial))

    def log_message(self, *a):
        pass


def main():
    print(f"Index options desk -> http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
