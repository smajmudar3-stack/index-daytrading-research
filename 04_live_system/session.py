"""session.py — ONE definition of when the system is awake. Everything else imports this.

Previously each module carried its own copy of a market-hours check, which is how `analyst.py` ended
up with none at all and burned ~190 Fable calls a night. A single source of truth means a new module
cannot quietly miss the gate.

  BOOT   09:20 ET — ten minutes before the bell. Snapshots, the desk read and the master call warm up
                    so the board is current at the open rather than being built during it.
  OPEN   09:30 ET
  CLOSE  16:00 ET — after this nothing that costs money runs until tomorrow.

Note this is the *spend* gate, not the *trade* gate. Entry windows live in risk_gates / rules and are
tighter (10:00 general, 10:30-13:00 for the validated condor).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

BOOT_MIN = 9 * 60 + 20      # 09:20 — warm-up starts
OPEN_MIN = 9 * 60 + 30      # 09:30
CLOSE_MIN = 16 * 60         # 16:00


def now_et():
    return datetime.now(ET)


def _mins(n=None):
    n = n or now_et()
    return n.hour * 60 + n.minute


def is_weekday(n=None):
    return (n or now_et()).weekday() < 5


def awake(n=None):
    """True from 09:20 to 16:00 on a weekday. THE gate for anything that costs money."""
    n = n or now_et()
    return is_weekday(n) and BOOT_MIN <= _mins(n) < CLOSE_MIN


def market_open(n=None):
    """True only during the actual session, 09:30-16:00."""
    n = n or now_et()
    return is_weekday(n) and OPEN_MIN <= _mins(n) < CLOSE_MIN


def phase(n=None):
    n = n or now_et()
    m = _mins(n)
    if not is_weekday(n):
        return "weekend"
    if m < BOOT_MIN:
        return "premarket"
    if m < OPEN_MIN:
        return "warmup"
    if m < CLOSE_MIN:
        return "open"
    return "closed"


def status_line(n=None):
    """Human-readable state for the dashboard header."""
    n = n or now_et()
    p = phase(n)
    m = _mins(n)
    if p == "open":
        left = CLOSE_MIN - m
        return {"phase": p, "open": True,
                "label": f"MARKET OPEN · {left//60}h {left%60}m to the close"}
    if p == "warmup":
        return {"phase": p, "open": False,
                "label": f"WARM-UP · opens in {OPEN_MIN - m} min — board refreshing"}
    # how long until the next boot at 09:20
    if p == "weekend":
        7 - n.weekday()
        nxt = "Monday 09:20 ET"
    elif m >= CLOSE_MIN:
        nxt = "tomorrow 09:20 ET" if n.weekday() < 4 else "Monday 09:20 ET"
    else:
        nxt = "09:20 ET"
    return {"phase": p, "open": False,
            "label": f"MARKET CLOSED · everything wakes at {nxt}"}


if __name__ == "__main__":
    s = status_line()
    print(f"{now_et():%Y-%m-%d %H:%M ET}  phase={s['phase']}  awake={awake()}  open={market_open()}")
    print(" ", s["label"])
