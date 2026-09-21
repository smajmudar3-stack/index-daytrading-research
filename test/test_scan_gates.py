"""The scan cycle's staleness gates are in SECONDS, and two of them were written in minutes.

`_stale(name, secs)` compares against the file's mtime in seconds. The weekly book's gate
read `240` with a comment saying "4h": four minutes, so the paid 200-name Unusual Whales
scan ran every 5-minute cycle and exhausted the 30,000-a-day quota by late morning. The
swing gate read `1500` ("25h"): twenty-five minutes. Neither failure is visible on the page,
because a throttled vendor looks like a quiet market. This reads the constants back out of
the script so the units cannot silently regress.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "..", "04_live_system", "scan_all.py")


def _const(name):
    src = open(SCAN).read()
    m = re.search(rf"^{name}\s*=\s*([0-9*\s]+)", src, re.M)
    assert m, f"{name} not defined in scan_all.py"
    return eval(m.group(1))  # noqa: S307 — a literal arithmetic expression from our own source


def test_weekly_regeneration_is_hours_not_minutes():
    assert _const("WEEKLY_REGEN_S") >= 2 * 3600
    src = open(SCAN).read()
    assert '_stale("weekly_snapshot.json", WEEKLY_REGEN_S)' in src


def test_swing_regeneration_is_a_day():
    assert _const("SWING_REGEN_S") >= 12 * 3600
    assert '_stale("swing_snapshot.json", SWING_REGEN_S)' in open(SCAN).read()
