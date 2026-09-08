"""The dashboard keeping itself current, without anyone being asked to come and refresh it.

Every asset here has a shelf life, and a stale one is worse than a missing one because it still
answers: an aged universe still returns 1,550 names, an aged calendar still names a CPI date.
Both would be wrong in a way nothing announced. These tests lock the machinery that renews them
and the machinery that says so when renewal has not happened.
"""
import os
import plistlib
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(REPO, "04_live_system")
if LIVE not in sys.path:
    sys.path.insert(0, LIVE)

PLISTS = ["com.daytrading.desknotes.plist", "com.daytrading.calendar.plist"]


def test_every_shipped_plist_is_valid_xml():
    """A double hyphen is ILLEGAL inside an XML comment.

    `com.daytrading.desknotes.plist` carried one for weeks. `plutil -lint` tolerated it and
    reported OK, so it looked installed and healthy, while a strict parser rejected the file
    outright. A scheduled job whose config only parses under one implementation is a latent
    outage, and the failure mode is the worst kind: the ingest silently stops and the overlay
    ages out with nothing saying why.
    """
    for name in PLISTS:
        p = os.path.join(LIVE, name)
        if not os.path.exists(p):
            continue
        with open(p, "rb") as fh:
            d = plistlib.load(fh)          # raises on a `--` inside a comment
        assert d.get("Label"), f"{name} has no Label"
        assert d.get("ProgramArguments"), f"{name} has no ProgramArguments"


def test_every_shipped_shell_job_parses():
    """A scheduled script with a syntax error fails silently at 08:10 on the 2nd."""
    for name in ("refresh_calendar.sh", "ingest_desk_notes.sh", "refresh_cycle.sh"):
        p = os.path.join(LIVE, name)
        if not os.path.exists(p):
            continue
        r = subprocess.run(["zsh", "-n", p], capture_output=True, text=True)
        assert r.returncode == 0, f"{name} does not parse: {r.stderr[:200]}"


def test_the_refresh_cycle_runs_the_maintenance_pass():
    """Renewal only happens if something calls it.

    `universe_builder.REFRESH_AFTER_DAYS` was 30 and nothing called `build()` on any schedule,
    so the roster would have aged past its own threshold and gone on answering.
    """
    with open(os.path.join(LIVE, "refresh_cycle.sh"), encoding="utf-8") as fh:
        body = fh.read()
    assert "maintenance.py" in body, (
        "the 5-minute cycle no longer runs maintenance.py, so nothing renews the universe or "
        "the macro calendar when they age out")


def test_maintenance_reports_an_age_for_every_asset_it_owns():
    import maintenance
    ages = maintenance.asset_ages()
    for k in ("universe", "macro_calendar", "flow_tape"):
        assert k in ages, f"{k} is not being watched for staleness"
    st = maintenance.status()
    assert st["rows"], "the freshness panel would render empty"
    for r in st["rows"]:
        assert r["severity"] in ("info", "watch", "stop")


def test_a_stale_asset_is_reported_not_silently_used():
    """The whole point: staleness must reach the page as a severity, not a shrug."""
    import maintenance
    rows = {r["name"]: r for r in maintenance.status()["rows"]}
    cal = rows["macro_calendar"]
    # `seed` means transcribed and not yet machine-verified. That is an acceptable state to run
    # in, but it must be VISIBLE — never reported as fully current.
    assert cal["state"] in ("ok", "seed", "stale", "unverified", "unreadable")
    if cal["state"] in ("stale", "unreadable"):
        assert cal["severity"] in ("watch", "stop")


def test_a_paper_trade_is_never_booked_on_a_non_trading_day():
    """Twenty trades sat on 371 settle attempts each, all dated Saturdays and Sundays.

    They could never settle — there is no daily bar for a weekend — and every one was excluded
    from the win rate, which is the single number the gap-and-go edge is judged on.
    """
    import gap_scanner
    res = gap_scanner._track(
        [{"ticker": "TEST", "setup": "x", "gap_pct": 1.0, "rvol": 2.0, "open": 10.0}],
        "2026-08-08")                       # a Saturday
    assert res["logged"] == 0, "a weekend paper trade was booked and can never settle"
