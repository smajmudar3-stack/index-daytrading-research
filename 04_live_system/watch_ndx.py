"""watch_ndx.py — one-off close watcher for the user's NDX condor short call at 29825.
Polls NDX every 30s; pings the Mac if it BREAKS AND HOLDS above 29825 (2 consecutive reads, not a wick).
Also pings the final status at the close. Exits at 4:00pm ET."""
import time
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf

ET = ZoneInfo("America/New_York")
LINE = 29825.0
SPIKE = 29835.0          # decisive break — alert INSTANTLY on the first read (don't wait to confirm)
above = 0
alerted = False
last_px = None
POLL = 12               # seconds — fast, to catch a spike quickly


def ping(title, msg, sound="Glass"):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "{sound}"'],
                       timeout=5, check=False)
    except Exception:
        pass


while True:
    n = datetime.now(ET)
    mins = n.hour * 60 + n.minute
    if n.weekday() >= 5 or mins >= 960:      # 4:00pm ET close
        break
    try:
        last_px = float(yf.Ticker("^NDX").fast_info["lastPrice"])
    except Exception:
        time.sleep(20); continue
    above = above + 1 if last_px > LINE else 0
    if not alerted:
        if last_px >= SPIKE:                 # DECISIVE spike well past the line → alert IMMEDIATELY
            ping("🔴🔴 NDX SPIKING through 29825",
                 f"NDX {last_px:.0f} — shot past your short call. CUT THE CALL SPREAD NOW.", "Sosumi")
            alerted = True
        elif above >= 2:                     # slower grind: 2 reads just above 29825 = a hold
            ping("🔴 NDX broke your line (29825)",
                 f"NDX {last_px:.0f} broke AND holding above 29825 — cut the call spread now.", "Sosumi")
            alerted = True
    if not alerted and mins >= 957 and last_px < LINE:   # ~3 min to close, still safe
        ping("🟢 NDX condor looking safe",
             f"NDX {last_px:.0f} — under 29825 into the close. Call spread on track to expire worthless.")
    time.sleep(POLL)

# final status
if last_px is not None:
    if last_px < LINE:
        ping("🟢 CLOSE: NDX condor survived",
             f"NDX closed ~{last_px:.0f}, below 29825. Call spread expires worthless — you keep the credit.")
    else:
        ping("🔴 CLOSE: NDX above 29825",
             f"NDX ~{last_px:.0f}, above your short call. Manage the call-side loss.")
print(f"watcher done. final NDX ~{last_px}, alerted={alerted}")
