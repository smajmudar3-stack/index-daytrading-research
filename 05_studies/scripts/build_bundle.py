"""Consolidate the whole index-daytrading repo into one self-describing folder.

Copies rather than moves, so the live dashboard keeps running. The 16 GB of
market data is NOT copied -- it is inventoried in 06_data_guide/DATA.md, because
duplicating a 14 GB Dolt clone to make a "bundle" would defeat the point.

Classification is by filename prefix. Anything that backtests, hunts, or
validates is a study; everything else is part of the running system.
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "BUNDLE")

DIRS = ["01_START_HERE", "02_findings", "03_research",
        "04_live_system", "05_studies", "06_data_guide"]

# Docs that orient a reader before any code.
START = ["HANDOFF.md", "RULES.md", "ENGINE.md", "STRATEGY_0DTE.md", "MES_STRATEGY.md"]
FINDINGS = ["FINDINGS.md", "FINDINGS_BLACKSWAN.md"]

STUDY_PREFIX = ("backtest_", "hunt_", "validate_", "bt_", "condor_backtest",
                "scalp_", "momentum_", "vwap_", "intraday_macro",
                "intraday_patterns", "intraday_puts", "mes_overnight",
                "mes_refine", "mes_signals", "merge_optimize", "minute_edges",
                "multi_edge", "orb_proper", "predictability", "dix_direction",
                "dl_ensemble", "fomc_research")


def sizeof(p):
    n = os.path.getsize(p)
    return f"{n/1024:.0f} KB" if n < 1024 * 1024 else f"{n/1048576:.1f} MB"


def lines(p):
    try:
        with open(p, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def main():
    for d in DIRS:
        os.makedirs(os.path.join(B, d), exist_ok=True)

    manifest = []

    def put(src, sub, note=""):
        dst = os.path.join(B, sub, os.path.basename(src))
        shutil.copy2(src, dst)
        manifest.append((sub, os.path.basename(src), lines(src), sizeof(src), note))

    # ---- 01 / 02 : orientation and results ------------------------------
    for f in START:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            put(p, "01_START_HERE")
    for f in FINDINGS:
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            put(p, "02_findings")

    # ---- 03 : every research report -------------------------------------
    research = sorted(f for f in os.listdir(ROOT) if f.startswith("RESEARCH_"))
    for f in research:
        put(os.path.join(ROOT, f), "03_research")

    # ---- 04 / 05 : code split by role -----------------------------------
    live, studies = [], []
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith(".py"):
            continue
        (studies if f.startswith(STUDY_PREFIX) else live).append(f)

    for f in live:
        put(os.path.join(ROOT, f), "04_live_system")
    for f in studies:
        put(os.path.join(ROOT, f), "05_studies")

    # scripts/ is entirely research harnesses
    sdir = os.path.join(B, "05_studies", "scripts")
    os.makedirs(sdir, exist_ok=True)
    for f in sorted(os.listdir(os.path.join(ROOT, "scripts"))):
        if f.endswith(".py"):
            src = os.path.join(ROOT, "scripts", f)
            shutil.copy2(src, os.path.join(sdir, f))
            manifest.append(("05_studies/scripts", f, lines(src), sizeof(src), ""))

    # ---- manifest --------------------------------------------------------
    with open(os.path.join(B, "MANIFEST.md"), "w") as fh:
        fh.write("# Manifest\n\nEvery file in this bundle, with size and line "
                 "count. Copied from `~/index-daytrading` -- the originals are "
                 "untouched and the dashboard still runs from them.\n\n")
        cur = None
        for sub, name, ln, sz, note in sorted(manifest):
            if sub != cur:
                fh.write(f"\n## {sub}\n\n| file | lines | size |\n|---|---:|---:|\n")
                cur = sub
            fh.write(f"| `{name}` | {ln:,} | {sz} |\n")
        fh.write(f"\n\n**{len(manifest)} files total.**\n")

    print(f"live modules   : {len(live)}")
    print(f"study modules  : {len(studies)}")
    print(f"research docs  : {len(research)}")
    print(f"total files    : {len(manifest)}")


if __name__ == "__main__":
    main()
