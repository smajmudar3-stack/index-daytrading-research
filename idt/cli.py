"""`idt` — the one command. Four verbs, no arguments to remember.

Exists because a fresh clone previously ran nothing: no dependency manifest, no
bootstrap, and a dashboard that returned HTTP 000 because `data/` did not exist.
"""
import argparse
import os
import subprocess
import sys

from . import keys, paths


def _live(script):
    return os.path.join(paths.LIVE_DIR, script)


def _run_live(script, *args):
    """Run a module from 04_live_system with that directory on the path — those
    modules import each other flat (`import rules`), so cwd matters."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [paths.LIVE_DIR, paths.REPO_ROOT, env.get("PYTHONPATH", "")]).strip(os.pathsep)
    return subprocess.run([sys.executable, _live(script), *args],
                          cwd=paths.LIVE_DIR, env=env).returncode


def cmd_bootstrap(_args):
    """Make a fresh clone runnable, and say plainly what is still missing."""
    print("idt bootstrap")
    os.makedirs(paths.STATE_ROOT, exist_ok=True)
    print(f"  state dir   {paths.STATE_ROOT}  (created if absent)")

    have = os.path.isdir(paths.DATA_ROOT)
    print(f"  market data {paths.DATA_ROOT}  {'found' if have else 'NOT INSTALLED'}")
    if not have:
        print("              The 16 GB of market data is not in git, by design.")
        print("              See 06_data_guide/DATA.md. Every backtest in 05_studies/")
        print("              needs it; the live dashboard does not.")
        print("              Point IDT_DATA_ROOT at an existing copy if you have one.")

    print("  api keys")
    for name, present in keys.status().items():
        print(f"              {'set    ' if present else 'MISSING'}  {name}")
    if not all(keys.status().values()):
        print("              Copy .env.example to .env and fill in what you have.")
        print("              None are required to render the dashboard; each one")
        print("              switches on a panel that otherwise says 'unavailable'.")

    print("\n  next:  idt serve   ->  http://127.0.0.1:8094")
    return 0


def cmd_serve(args):
    """The dashboard. `--legacy` serves the pre-Phase-4 single-file page.

    The old one is kept reachable for one release so a number that looks wrong on the
    new page can be checked against the old one, which is the only honest way to
    migrate a page nobody has a test for yet."""
    if getattr(args, "legacy", False):
        return _run_live("gap_dashboard.py")
    return _run_live("dashboard_app.py")


def cmd_refresh(_args):
    return _run_live("scan_all.py")


def cmd_audit(args):
    return _run_live("audit_dash.py", *(["--strict"] if getattr(args, "strict", False) else []))


def main(argv=None):
    p = argparse.ArgumentParser(prog="idt", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in (
            ("bootstrap", cmd_bootstrap, "prepare a fresh clone and report what is missing"),
            ("serve", cmd_serve, "run the dashboard on http://127.0.0.1:8094"),
            ("refresh", cmd_refresh, "run one full signal cycle now"),
            ("audit", cmd_audit, "check every number the dashboard shows (exits non-zero on failure)")):
        s = sub.add_parser(name, help=help_)
        if name == "serve":
            s.add_argument("--legacy", action="store_true",
                           help="serve the pre-Phase-4 single-file dashboard instead")
        if name == "audit":
            s.add_argument("--strict", action="store_true",
                           help="also fail on warnings")
        s.set_defaults(func=fn)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
