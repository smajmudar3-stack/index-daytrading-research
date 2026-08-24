"""Combined runner for the signals dashboard: gap-and-go (+analyst) every call; swing only
when its snapshot is stale (>25 min) since it's a daily-timeframe signal and option pulls
are slow. launchd + /refresh point here."""
import os, time, json
import gap_scanner, swing_signals
import refresh_signal
import uw_calibrate

HERE = os.path.dirname(os.path.abspath(__file__))

def _stale(name, secs):
    p = os.path.join(HERE, "data", name)
    if not os.path.exists(p):
        return True
    try:
        return (time.time() - os.path.getmtime(p)) > secs
    except Exception:
        return True

def _load(name):
    try:
        return json.load(open(os.path.join(HERE, "data", name)))
    except Exception:
        return {}

def _notify(title, msg):
    """Fire a macOS notification (best-effort) so a setup/flip-break reaches the user off-screen."""
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                       timeout=5, check=False)
    except Exception:
        pass

def _mkt_open():
    """09:20 boot -> 16:00 close. See session.py."""
    try:
        import session
        return session.awake()
    except Exception:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        n = datetime.now(ZoneInfo("America/New_York"))
        return n.weekday() < 5 and 560 <= (n.hour * 60 + n.minute) < 960

# 0DTE reconciled regime: refresh every 10 min intraday so it catches live UW-flow shifts
if _stale("gex_snapshot.json", 600):
    _prev = _load("gex_snapshot.json")
    try:
        import gex_signal
        gex_signal.run()
    except Exception:
        pass
    # ALERT on a NEW high-conviction directional setup (so you don't have to keep checking)
    _now = _load("gex_snapshot.json")
    if _mkt_open() and _now.get("master_dir") in ("bullish", "bearish") and _now.get("conviction", 0) >= 58:
        if _prev.get("master_dir") != _now.get("master_dir"):     # only on a fresh transition
            _side = "BUY CALLS" if _now["master_dir"] == "bullish" else "BUY PUTS"
            _notify(f"🎯 SPX setup: {_side} ({_now['conviction']}/100)",
                    f"{_now.get('regime','')} · {_now.get('thesis','')[:120]}")

# live per-strike gamma periscope for the indexes traded (SPX + NDX 0DTE) — refresh every 5-min cycle
if _stale("periscope_SPX.json", 240):
    try:
        import gex_periscope
        for _sym in ("^SPX", "^NDX"):
            _snap = gex_periscope.run(_sym)
            brk = (_snap or {}).get("flip_break")
            if brk and _mkt_open():                      # only alert on live intraday breaks
                _nm = _sym.replace("^", "")
                if brk == "broke_down":
                    _notify(f"⚠️ {_nm} BROKE the gamma flip",
                            f"{_nm} {_snap['spot']} < flip {_snap['gamma_flip']} → SHORT GAMMA. RECOMMENDED: BUY PUTS (downside amplifies).")
                else:
                    _notify(f"{_nm} reclaimed the gamma flip",
                            f"{_nm} back above flip {_snap['gamma_flip']} → pin regime restored. Put trade invalidated.")
    except Exception:
        pass

try:
    import signal_tracker
    signal_tracker.settle()          # settle past SPX 0DTE signals for the running win-rate
except Exception:
    pass

try:
    import positions
    positions.manage()               # evaluate open trades vs live levels; ping SELL/HALF/ADD
except Exception:
    pass

# AI layer (Fable) — cadence-gated for cost
# Desk read every ~15 min — MARKET HOURS ONLY. This is a Fable call at high effort; ungated it fired
# around the clock and burned ~60 calls a night reading a board that had not changed since the close.
if _mkt_open() and _stale("ai_desk_snapshot.json", 900):
    try:
        import ai_desk; ai_desk.desk()
    except Exception:
        pass
try:
    import ai_trader
    ai_trader.manage_open()          # EVERY cycle: cut losers small / scale winners on live levels (fast, no LLM)
except Exception:
    pass
# ── sleeve cadences ────────────────────────────────────────────────────────────────────────────
# 0DTE decides every ~10 min but ONLY inside the validated 10:30-13:00 entry window (outside it the
# answer is always stand-down, so calling the model would just burn tokens to be told no).
# Swing decides hourly. Open 0DTE positions are additionally watched every 60s by monitor.py.
def _in_0dte_window():
    try:
        import rules
        from datetime import datetime as _dt
        from zoneinfo import ZoneInfo as _Z
        n = _dt.now(_Z("America/New_York"))
        m = n.hour * 60 + n.minute
        return (rules.ENTRY_START[0] * 60 + rules.ENTRY_START[1]) <= m <= (rules.ENTRY_END[0] * 60 + rules.ENTRY_END[1])
    except Exception:
        return True

try:
    import sleeves
    _z_cad = sleeves.get("0dte").get("cadence_seconds", 600)
    _s_cad = sleeves.get("swing").get("cadence_seconds", 3600)
except Exception:
    _z_cad, _s_cad = 600, 3600

_due_0dte = _mkt_open() and _in_0dte_window() and _stale("agent_snapshot.json", _z_cad)
_due_swing = _mkt_open() and _stale("swing_decision.json", _s_cad)
if _due_0dte or _due_swing:
    try:
        import ai_trader
        ai_trader.decide()
        if _due_swing:      # stamp the hourly swing pass so it doesn't re-fire every cycle
            import json as _j, time as _t
            _j.dump({"ts": _t.time(), "at": time.strftime("%Y-%m-%d %H:%M")},
                    open(os.path.join(HERE, "data", "swing_decision.json"), "w"))
    except Exception:
        pass
# ORDER-FLOW ARCHIVE: capture UW flow every cycle so it becomes backtestable. The 30-min aggregated
# version of this tested null, but tick-level flow was never testable here for lack of history.
# Collected FORWARD, so it can never be contaminated by hindsight.
if _mkt_open():
    try:
        import uw_archive; uw_archive.run()
    except Exception:
        pass
# VALIDATION: log what the market actually pays for the researched condor (RULES.md §6.1 — the highest
# value next step, since every backtest P&L came from a model). Observe-only; never trades.
if _mkt_open():
    try:
        import rules
        for _p in rules.PRODUCTS:
            rules.log_credit(_p)
    except Exception:
        pass
# affordability: which instruments this account can actually hold inside the risk cap (live chains, slow)
if _mkt_open() and _stale("affordability.json", 1800):
    try:
        import sizing
        json.dump(sizing.affordability_report(), open(os.path.join(HERE, "data", "affordability.json"), "w"), indent=2)
    except Exception:
        pass
# THE MASTER CALL — Fable reads the whole board and makes the one decision shown at the top of the
# dashboard, plus flags any BIG RUNS worth looking at. Every ~10 min during market hours.
if _mkt_open() and _stale("master_call.json", 600):
    try:
        import master_call; master_call.decide()
    except Exception:
        pass
# scorecard: the pre-registered paper->live gate + honest projection vs the growth curve (cheap, no LLM)
if _stale("graduation.json", 900):
    try:
        import graduation; graduation.report()
    except Exception:
        pass
# self-improvement: re-derive lessons from closed trades (LLM, but rare — gated on new closed trades)
if _mkt_open() and _stale("lessons.json", 21600):
    try:
        import lessons; lessons.review()
    except Exception:
        pass

gap_scanner.run()  # intraday + analyst + paper settle; cheap when no candidates
if _stale("swing_snapshot.json", 1500):
    swing_signals.run()

# ---------------------------------------------------------------------------
# SIGNAL FRESHNESS, CALIBRATION AND SCORECARD
# Appended at module level because this file is a script, not a main() — three
# earlier edits targeted a `def main():` that does not exist and silently did
# nothing, which is why the panel kept going stale after I had "fixed" it.
# ---------------------------------------------------------------------------
try:
    refresh_signal.refresh()          # VIX/VIX3M/golden-cross inputs for the swing vote
except Exception as _exc:
    print(f"signal refresh failed: {_exc}")

try:
    import uw_endpoints as _ue
    _uni = ["SPY", "QQQ", "NVDA", "TSLA", "AAPL", "AMD", "PLTR", "MRNA",
            "SOFI", "MARA", "COIN", "GME", "HOOD", "RIOT"]
    uw_calibrate.log_snapshot([_ue.profile(_t) for _t in _uni])
    _cal = uw_calibrate.calibrate()
    if _cal.get("n_settled"):
        print(f"uw calibration: {_cal['n_settled']} settled")
except Exception as _exc:
    print(f"uw calibration skipped: {_exc}")

try:
    import json as _json, scorecard as _sc
    try:
        _gx = _json.load(open(os.path.join(HERE, "data", "gex_snapshot.json")))
        _rc = _gx.get("reconcile") or {}
        _sc.record("0dte", "SPY", _rc.get("master_dir"), _gx.get("conviction"),
                   note="reconciled master")
    except Exception:
        pass
    try:
        _sw = _json.load(open(os.path.join(HERE, "data", "swing_snapshot.json")))
        for _s in (_sw.get("signals") or _sw.get("swings") or [])[:10]:
            _sc.record("swing", _s.get("ticker"), _s.get("direction"),
                       _s.get("conviction"),
                       (_s.get("structure") or {}).get("play"), _s.get("last"))
    except Exception:
        pass
    try:
        _bs = _json.load(open(os.path.join(HERE, "data", "blackswan_scan.json")))
        for _c in (_bs.get("candidates") or [])[:8]:
            if (_c.get("ticket") or {}).get("tradeable"):
                _sc.record("blackswan", _c.get("ticker"), "bullish",
                           _c.get("lift", 1) * 40, note="coiled screen")
    except Exception:
        pass
    _n = _sc.settle()
    if _n:
        print(f"scorecard: settled {_n} call(s)")
except Exception as _exc:
    print(f"scorecard skipped: {_exc}")
