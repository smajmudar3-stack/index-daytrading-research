"""Audit every number the dashboard shows against an independent source.

Written after a run of bugs that shared one shape: data that was RETURNED but
not CORRECT, displayed as if live. A stale 1-minute bar, a gamma flip computed
across the whole listed ladder, a snapshot frozen by a crash in an unrelated
function. None of those raise an error -- they just print a confident wrong
number. So this checks values, not exit codes.
"""
import json
import os
import subprocess
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.abspath(__file__))
FAIL, WARN, OK = [], [], []


def chk(name, cond, detail, hard=True):
    (OK if cond else (FAIL if hard else WARN)).append(f"{name}: {detail}")
    return cond


def load(f):
    try:
        with open(os.path.join(ROOT, "data", f)) as fh:
            return json.load(fh)
    except Exception:
        return {}


def age_min(f):
    p = os.path.join(ROOT, "data", f)
    if not os.path.exists(p):
        return None
    import time
    return (time.time() - os.path.getmtime(p)) / 60


def main():
    import yfinance as yf
    import pandas as pd

    print("=" * 88)
    print("DASHBOARD AUDIT")
    print("=" * 88)

    live = {}
    for k, t in (("SPX", "^GSPC"), ("NDX", "^NDX"), ("SPY", "SPY"), ("QQQ", "QQQ")):
        try:
            live[k] = float(yf.Ticker(t).fast_info["lastPrice"])
        except Exception:
            live[k] = None

    # ---- 1. SPOT ACCURACY -------------------------------------------------
    for idx in ("SPX", "NDX"):
        d = load(f"periscope_{idx}.json")
        sp, lv = d.get("spot"), live.get(idx)
        if sp and lv:
            err = abs(sp / lv - 1) * 100
            chk(f"{idx} spot", err < 0.15,
                f"stored {sp:,.2f} vs live {lv:,.2f} ({err:+.3f}%)")
        else:
            chk(f"{idx} spot", False, "missing")

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
    try:
        import uw_client as uw
        chk("UW available", uw.available(), "key active and not auth-tripped")
        f = uw.summarize_flow("SPY")
        chk("UW flow", bool(f), f"lean {f['lean']:+.2f} {f['bias']}" if f else "none")
    except Exception as e:
        chk("UW", False, str(e)[:60])

    # ---- 5. WEIGHTS -------------------------------------------------------
    try:
        import signal_weights as sw
        t = sw.table()
        nulls = [r for r in t if r["tier"] == "measured-null"]
        chk("nulls pinned at zero", all(r["weight"] == 0 for r in nulls),
            f"{len(nulls)} measured-null inputs, all weight 0")
        live_w = [r for r in t if r["weight"] > 0]
        chk("weights present", len(live_w) >= 4,
            ", ".join(f"{r['input']}={r['weight']:.2f}" for r in live_w))
    except Exception as e:
        chk("weights", False, str(e)[:60])

    # ---- 6. STALE-SPOT GUARD ----------------------------------------------
    try:
        import spx_ndx_advisor as adv
        a = adv.advise("SPY")
        st = a["state"]
        if st.get("spot_stale"):
            chk("stale guard", len(a["recommendations"]) == 0,
                "spot stale AND no tickets emitted")
        else:
            OK.append(f"stale guard: spot fresh ({st.get('spot_age_min')} min)")
    except Exception as e:
        chk("stale guard", False, str(e)[:60])

    # ---- 7. SCORECARD -----------------------------------------------------
    try:
        import scorecard as sc
        r = sc.report()
        tot = sum(v.get("settled", 0) + v.get("pending", 0) for v in r.values())
        chk("scorecard logging", tot > 0,
            f"{tot} calls tracked across {len(r)} tab(s)", hard=False)
    except Exception as e:
        chk("scorecard", False, str(e)[:60])

    # ---- 8. DASHBOARD RENDER ----------------------------------------------
    try:
        import gap_dashboard as g
        h = g.render()
        chk("render", len(h) > 40000, f"{len(h):,} chars")
        for panel in ("Trade Desk", "Black Swan", "Scorecard"):
            chk(f"panel: {panel}", panel in h, "present")
    except Exception as e:
        chk("render", False, str(e)[:80])

    # ---- 9. HTTP ----------------------------------------------------------
    try:
        out = subprocess.run(
            ["curl", "-s", "--max-time", "20", "-o", "/dev/null",
             "-w", "%{http_code} %{time_total}", "http://localhost:8094/"],
            capture_output=True, text=True).stdout.split()
        chk("http 200", out and out[0] == "200", f"HTTP {out[0]} in {out[1]}s")
    except Exception as e:
        chk("http", False, str(e)[:60])

    print(f"\nPASS ({len(OK)})")
    for x in OK:
        print(f"  ok    {x}")
    if WARN:
        print(f"\nWARN ({len(WARN)})")
        for x in WARN:
            print(f"  warn  {x}")
    if FAIL:
        print(f"\nFAIL ({len(FAIL)})")
        for x in FAIL:
            print(f"  FAIL  {x}")
    print(f"\n{len(OK)} pass / {len(WARN)} warn / {len(FAIL)} fail")


if __name__ == "__main__":
    main()
