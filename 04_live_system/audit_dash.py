"""Audit every number the dashboard shows against an independent source.

Written after a run of bugs that shared one shape: data that was RETURNED but
not CORRECT, displayed as if live. A stale 1-minute bar, a gamma flip computed
across the whole listed ladder, a snapshot frozen by a crash in an unrelated
function. None of those raise an error -- they just print a confident wrong
number. So this checks values, not exit codes.

IT NOW HAS AN EXIT CODE, AND THAT WAS THE POINT ALL ALONG. Until 2026-08-24
main() had no sys.exit, so 23 value-level checks could all fail and the process
still returned 0. Every cron, launchd job and CI step gating on this file passed
while the dashboard was broken -- which is precisely the failure mode described
in the paragraph above, committed by the tool written to catch it.

  exit 0   nothing failed
  exit 1   at least one hard FAIL, or at least one check that COULD NOT RUN
  exit 1   with --strict, also when anything WARNed

THREE OUTCOMES, NOT TWO. A check that fails and a check that could not run are
different problems with different owners: "SPX spot is 0.4% off" is a data bug,
"no reference quote to compare against" is a network or install problem and says
nothing about the data. They used to be a single FAIL line, so the operator could
not tell which one he had. They are counted and printed separately now.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import warnings

from idt import paths

warnings.filterwarnings("ignore")
DATA = paths.STATE_ROOT

OK, WARN, FAIL, ERROR = [], [], [], []
_LOADED = {}


def chk(name, cond, detail, hard=True):
    """A value-level assertion that actually RAN. True, or a hard/soft failure."""
    (OK if cond else (FAIL if hard else WARN)).append(f"{name}: {detail}")
    return cond


def err(name, detail):
    """The check COULD NOT RUN. Not a pass, not quite a fail: nothing was verified.

    Counted as a failure for the exit code, because an unrun check has confirmed
    nothing and reporting it as green is the exact bug this file exists to catch.
    Kept in its own bucket so the operator can see at a glance whether he has a
    broken dashboard or a broken laptop."""
    ERROR.append(f"{name}: {detail}")
    return False


def load(f):
    """Snapshot contents, or {} if the engine has never written it.

    Absent and CORRUPT used to be the same `except Exception: return {}` here.
    They are not the same: absent means the engine has not run, corrupt means it
    ran and wrote garbage, and a confidently wrong number written by a half-failed
    engine is the whole reason this file exists."""
    if f in _LOADED:
        return _LOADED[f]          # every snapshot is read by two sections; report a bad one once
    p = os.path.join(DATA, f)
    if not os.path.exists(p):
        _LOADED[f] = {}
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            _LOADED[f] = json.load(fh)
    except (OSError, ValueError) as e:
        chk(f"{f} readable", False, f"{type(e).__name__}: {str(e)[:80]}")
        _LOADED[f] = {}
    return _LOADED[f]


def age_min(f):
    p = os.path.join(DATA, f)
    if not os.path.exists(p):
        return None
    return (time.time() - os.path.getmtime(p)) / 60


def _live_quotes():
    """Independent reference prices. Returns (values, errors) so a failed fetch can
    be reported as "could not check" rather than as "the stored spot is wrong"."""
    live, errors = {}, {}
    tickers = (("SPX", "^GSPC"), ("NDX", "^NDX"), ("SPY", "SPY"), ("QQQ", "QQQ"))
    try:
        import yfinance as yf
    except Exception as e:
        return {}, {k: f"yfinance will not import: {type(e).__name__}: {str(e)[:50]}"
                    for k, _ in tickers}
    for k, t in tickers:
        try:
            live[k] = float(yf.Ticker(t).fast_info["lastPrice"])
        except Exception as e:
            errors[k] = f"{type(e).__name__}: {str(e)[:60]}"
    return live, errors


def run_checks():
    print("=" * 88)
    print("DASHBOARD AUDIT")
    print("=" * 88)

    live, live_err = _live_quotes()

    # ---- 1. SPOT ACCURACY -------------------------------------------------
    for idx in ("SPX", "NDX"):
        d = load(f"periscope_{idx}.json")
        sp, lv = d.get("spot"), live.get(idx)
        if sp and lv:
            drift = abs(sp / lv - 1) * 100
            chk(f"{idx} spot", drift < 0.15,
                f"stored {sp:,.2f} vs live {lv:,.2f} ({drift:+.3f}%)")
        elif not sp:
            chk(f"{idx} spot", False,
                f"no spot in periscope_{idx}.json (the periscope engine has not written one)")
        else:
            err(f"{idx} spot", f"no reference quote to compare against: "
                               f"{live_err.get(idx, 'unknown')}")

    # ---- 2. FRESHNESS -----------------------------------------------------
    for f, lim in (("periscope_SPX.json", 20), ("periscope_NDX.json", 20),
                   ("gex_snapshot.json", 90), ("swing_snapshot.json", 1500)):
        a = age_min(f)
        chk(f"{f} age", a is not None and a < lim,
            f"{a:.0f} min old (limit {lim})" if a is not None else "missing",
            hard=(a is None or a > lim * 3))

    # ---- 3. GAMMA SANITY --------------------------------------------------
    # Levels must bracket spot sensibly. A flip far from spot, or walls on the
    # wrong side of it, means the level was computed over the wrong strike set.
    for idx in ("SPX", "NDX"):
        d = load(f"periscope_{idx}.json")
        sp = d.get("spot")
        if not sp:
            continue
        fl, cw, pw = d.get("gamma_flip"), d.get("call_wall"), d.get("put_wall")
        if fl:
            chk(f"{idx} gamma flip", abs(fl / sp - 1) < 0.05,
                f"flip {fl:,.0f} is {(fl/sp-1)*100:+.1f}% from spot {sp:,.0f}")
        if cw and pw:
            chk(f"{idx} walls bracket spot", pw < sp < cw or abs(cw - pw) > 1e-9,
                f"put {pw:,.0f} / spot {sp:,.0f} / call {cw:,.0f}")
            chk(f"{idx} walls distinct", abs(cw - pw) > 1e-9,
                f"call wall {cw:,.0f} vs put wall {pw:,.0f}")

    # ---- 4. UW HEALTH -----------------------------------------------------
    # The split below is the pattern for every remaining section: an IMPORT that
    # fails means the check could not run, while the module answering wrongly is
    # a real failure. Lumping them together is what made "UW: No module named
    # uw_client" and "UW: key expired" look like the same problem.
    try:
        import uw_client as uw
    except Exception as e:
        err("UW available", f"uw_client will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            # The detail has to describe what was FOUND, not what was hoped for. It
            # used to read "key active and not auth-tripped" either way, so a failing
            # line said the opposite of what it meant.
            up = uw.available()
            chk("UW available", up,
                "key active and not auth-tripped" if up
                else "no key, or the client has auth-tripped and stopped calling")
            f = uw.summarize_flow("SPY")
            chk("UW flow", bool(f), f"lean {f['lean']:+.2f} {f['bias']}" if f else "none")
        except Exception as e:
            chk("UW flow", False, f"summarize_flow raised {type(e).__name__}: {str(e)[:60]}")

    # ---- 5. WEIGHTS -------------------------------------------------------
    try:
        import signal_weights as sw
    except Exception as e:
        err("weights", f"signal_weights will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            t = sw.table()
        except Exception as e:
            chk("weights", False, f"table() raised {type(e).__name__}: {str(e)[:60]}")
        else:
            nulls = [r for r in t if r["tier"] == "measured-null"]
            chk("nulls pinned at zero", all(r["weight"] == 0 for r in nulls),
                f"{len(nulls)} measured-null inputs, all weight 0")
            live_w = [r for r in t if r["weight"] > 0]
            chk("weights present", len(live_w) >= 4,
                ", ".join(f"{r['input']}={r['weight']:.2f}" for r in live_w))

    # ---- 6. STALE-SPOT GUARD ----------------------------------------------
    try:
        import spx_ndx_advisor as adv
    except Exception as e:
        err("stale guard", f"spx_ndx_advisor will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            a = adv.advise("SPY")
            st = a["state"]
        except Exception as e:
            # advise() needs live quotes, so this can be a network problem rather
            # than a logic one. The exception TYPE is printed for exactly that
            # reason: it is the operator's only clue which of the two he has.
            chk("stale guard", False, f"advise() raised {type(e).__name__}: {str(e)[:60]}")
        else:
            if st.get("spot_stale"):
                chk("stale guard", len(a["recommendations"]) == 0,
                    "spot stale AND no tickets emitted")
            else:
                OK.append(f"stale guard: spot fresh ({st.get('spot_age_min')} min)")

    # ---- 7. SCORECARD -----------------------------------------------------
    try:
        import scorecard as sc
    except Exception as e:
        err("scorecard", f"scorecard will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            r = sc.report()
        except Exception as e:
            # ScorecardUnavailable means the track record cannot be read at all.
            # That is a real failure, not a "could not run": the file is right
            # there and it is broken.
            chk("scorecard logging", False, f"{type(e).__name__}: {str(e)[:70]}")
        else:
            tot = sum(v.get("settled", 0) + v.get("pending", 0) for v in r.values())
            chk("scorecard logging", tot > 0,
                f"{tot} calls tracked across {len(r)} tab(s)", hard=False)

    # ---- 8. RISK GATES ----------------------------------------------------
    # The event calendar is hand-entered, nothing refreshes it, and a gate that
    # cannot read it now blocks trading rather than passing. That makes its state
    # an operational number the dashboard depends on, so it gets audited like one.
    try:
        import risk_gates as rg
    except Exception as e:
        err("risk gates", f"risk_gates will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            cal = rg.event_calendar_status()
        except Exception as e:
            chk("event calendar", False, f"{type(e).__name__}: {str(e)[:70]}")
        else:
            chk("event calendar", cal["ok"], f"{cal['state']}: {cal['reason']}")
            if cal["ok"] and cal.get("warning"):
                chk("event calendar lookahead", False, cal["warning"], hard=False)
        book = rg.book_status()
        chk("trade book readable", book["ok"],
            f"{book['entries_today']} entries today" if book["ok"] else book["reason"])

    # ---- 9. DASHBOARD RENDER ----------------------------------------------
    try:
        import gap_dashboard as g
    except Exception as e:
        err("render", f"gap_dashboard will not import: {type(e).__name__}: {str(e)[:60]}")
    else:
        try:
            h = g.render()
        except Exception as e:
            # render() raising IS the failure being audited: it is what returned
            # HTTP 000 and zero bytes on a fresh clone.
            chk("render", False, f"render() raised {type(e).__name__}: {str(e)[:70]}")
        else:
            chk("render", len(h) > 40000, f"{len(h):,} chars")
            for panel in ("Trade Desk", "Black Swan", "Scorecard"):
                found = panel in h
                chk(f"panel: {panel}", found,
                    "present" if found else "missing from the rendered page")

    # ---- 10. HTTP ---------------------------------------------------------
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-o", "/dev/null",
             "-w", "%{http_code} %{time_total}", "http://localhost:8094/"],
            capture_output=True, text=True).stdout.split()
    except (OSError, subprocess.SubprocessError) as e:
        err("http 200", f"curl could not be run: {type(e).__name__}: {str(e)[:60]}")
    else:
        # An empty split() used to blow up inside the f-string that formatted the
        # detail, so a server that was simply down surfaced as an IndexError.
        if not out:
            chk("http 200", False, "no response from http://localhost:8094/ (server not running?)")
        else:
            took = out[1] if len(out) > 1 else "?"
            chk("http 200", out[0] == "200", f"HTTP {out[0]} in {took}s")


def summarise(strict):
    print(f"\nPASS ({len(OK)})")
    for x in OK:
        print(f"  ok    {x}")
    if WARN:
        print(f"\nWARN ({len(WARN)})")
        for x in WARN:
            print(f"  warn  {x}")
    if ERROR:
        print(f"\nCOULD NOT RUN ({len(ERROR)})")
        for x in ERROR:
            print(f"  ERR   {x}")
    if FAIL:
        print(f"\nFAIL ({len(FAIL)})")
        for x in FAIL:
            print(f"  FAIL  {x}")
    print(f"\n{len(OK)} pass / {len(WARN)} warn / {len(ERROR)} could-not-run / {len(FAIL)} fail")

    # WARN does not fail the run by default, and that is a considered choice rather
    # than a soft one. The only soft checks here are freshness still inside 3x its
    # limit, a scorecard with nothing settled yet, and an event calendar that is
    # valid but running low -- every one of which is the NORMAL state at 06:00, at
    # the weekend, or on a clone that has not run yet. A gate that paged every
    # Saturday would be muted inside a week, and a muted gate is how this file came
    # to always exit 0 in the first place. --strict promotes warnings to failures
    # for CI, where "it is the weekend" is not an excuse anyone is awake to hear.
    if FAIL or ERROR:
        why = " and ".join(filter(None, [f"{len(FAIL)} failure(s)" if FAIL else "",
                                         f"{len(ERROR)} check(s) that could not run" if ERROR else ""]))
        print(f"exit 1: {why}")
        return 1
    if strict and WARN:
        print(f"exit 1: {len(WARN)} warning(s), --strict")
        return 1
    if WARN:
        print("exit 0: warnings only (use --strict to fail on these)")
    else:
        print("exit 0: all checks passed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--strict", action="store_true",
                    help="also exit 1 on warnings (for CI, where nobody is watching the output)")
    args = ap.parse_args(argv)
    run_checks()
    return summarise(args.strict)


if __name__ == "__main__":
    sys.exit(main())
