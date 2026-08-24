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
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402
from markupsafe import Markup  # noqa: E402

from panels import views  # noqa: E402

PORT = 8094
TEMPLATES = os.path.join(HERE, "templates")
STATIC = os.path.join(HERE, "static")

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


def render_view(slug, partial=False):
    panels = views.build(slug)
    v = views.view_by_slug(slug)
    ctx = {
        "title": "Index options desk",
        "subtitle": "SPX / NDX 0DTE, swing and risk. Paper only.",
        "views": [{"slug": x["slug"], "label": x["label"]} for x in views.VIEWS],
        "view": v["slug"],
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
            out.append(tpl.render(p=p))
        return "\n".join(out)
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
        out = []
        for line in text.splitlines():
            e = _html.escape(line)
            e = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", e)
            e = re.sub(r"`(.+?)`", r"<code>\1</code>", e)
            if line.startswith("### "):
                out.append(f"<h3>{e[4:]}</h3>")
            elif line.startswith("## "):
                out.append(f"<h2>{e[3:]}</h2>")
            elif line.startswith("# "):
                out.append(f"<h1>{e[2:]}</h1>")
            elif line.startswith("|"):
                cells = [c.strip() for c in e.strip("|").split("|")]
                if set("".join(cells)) <= set("-: "):
                    continue
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            elif not line.strip():
                out.append("")
            else:
                out.append(f"<p>{e}</p>")
        body = "\n".join(out).replace("<tr>", "<table><tr>", 1)
        if "<table>" in body:
            body += "</table>"
    return env.get_template("docs.html").render(
        title="What this system knows",
        subtitle=f"from {os.path.relpath(src, os.path.dirname(HERE))}" if src else "source missing",
        views=[{"slug": x["slug"], "label": x["label"]} for x in views.VIEWS],
        view="docs",
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
            # A refresh that fails must SAY so. The old handler swallowed every
            # exception and issued an identical 302 either way.
            try:
                import scan_all  # noqa: F401  - running it IS the refresh
                note = ""
            except Exception as e:                  # noqa: BLE001
                note = f"?cycle_error={urllib.parse.quote(str(e)[:120])}"
            self.send_response(302)
            self.send_header("Location", f"/{back}{note}")
            self.end_headers()
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
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
