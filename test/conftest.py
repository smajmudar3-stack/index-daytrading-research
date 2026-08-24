"""Test fixtures.

Every test here runs OFFLINE and against a temporary state directory. Nothing in
this suite may touch the network, the real 04_live_system/data/, or the 16 GB of
market data. That is not a purity preference: the market data is not in git, so a
suite that needed it would be skipped on every fresh clone, and a skipped test is
not a test.
"""
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, "04_live_system")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

if LIVE not in sys.path:
    sys.path.insert(0, LIVE)


@pytest.fixture
def state(tmp_path, monkeypatch):
    """An empty state directory, pointed at by IDT_STATE_ROOT.

    Returns a helper that copies a named fixture snapshot into place, so a test can
    say `state.put("gex_snapshot.json", "high_gamma")` and read like the scenario it
    is describing.
    """
    d = tmp_path / "state"
    d.mkdir()
    monkeypatch.setenv("IDT_STATE_ROOT", str(d))

    # idt.paths reads the environment at import time, so a test that changes it has
    # to reload the module. Doing it here keeps every test honest about which state
    # directory it is looking at.
    import idt.paths
    import importlib
    importlib.reload(idt.paths)
    for mod in ("panels.today", "panels.views", "panels.markets"):
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])

    class State:
        path = d

        def put(self, name, fixture=None, data=None):
            target = d / name
            if data is not None:
                target.write_text(json.dumps(data), encoding="utf-8")
                return target
            src = os.path.join(FIXTURES, f"{fixture}.json")
            shutil.copy(src, target)
            return target

        def age(self, name, minutes):
            """Backdate a file so a staleness path can actually be exercised."""
            import time
            p = d / name
            t = time.time() - minutes * 60
            os.utime(p, (t, t))

    return State()
