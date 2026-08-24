#!/usr/bin/env python3
"""Fetch what can be fetched, and say plainly what cannot.

06_data_guide/DATA.md inventories 16 GB of market data and no script in this repo
acquired a single byte of it. So a fresh clone had an inventory of things it did
not have, no way to get them, and no way to tell which absences mattered. This is
that script.

It is honest about the split, because the split is the point:

  RECONSTRUCTIBLE   the swing panel (yfinance, no key), the EDGAR spinoff dataset
                    (SEC, no key), the DoltHub clones (free, needs the `dolt`
                    binary), the single-stock panel (needs a Tiingo key)
  NOT AVAILABLE     the SPY/QQQ EOD option chains and the SPXW intraday quotes.
                    Those came from a source this bundle does not name and cannot
                    reach. Copy them from a machine that has them, or point
                    IDT_DATA_ROOT at one. No amount of scripting substitutes.

Defaults to a DRY RUN. The full Dolt clone is 14 GB; a tool that starts that
because you typed its name without arguments is a tool you only run once.

Usage
  venv/bin/python scripts/bootstrap_data.py                 report only
  venv/bin/python scripts/bootstrap_data.py --fetch         fetch the small, keyless assets
  venv/bin/python scripts/bootstrap_data.py --fetch --only dolt-options
  venv/bin/python scripts/bootstrap_data.py --list          just the asset names
"""
import argparse
import os
import shutil
import subprocess
import sys
import textwrap

from idt import keys, paths

# Assets, in the order a reader should care about them.
#
#   size    what DATA.md records, so a missing 250 MB file is not mistaken for a
#           missing 250 KB one
#   get     how to obtain it, in the imperative
#   how     "script" (we can run it), "dolt" (we can run it if dolt is installed),
#           "manual" (a human has to fetch it), "copy" (it cannot be rebuilt)
#   big     true if fetching it costs gigabytes; never fetched without --only
ASSETS = [
    dict(key="swing", path=("swing", "panel.parquet"), size="14 MB",
         what="45-ticker daily panel, 1998-2026, the swing research base",
         how="script", script="05_studies/scripts/swing_data.py", needs=None, big=False,
         get="yfinance, no API key"),
    dict(key="spinoffs", path=("spinoffs",), size="1.2 MB",
         what="survivorship-free US spinoff event study from SEC EDGAR",
         how="script", script="05_studies/scripts/spinoff_edgar_harvest.py", needs=None, big=False,
         get="SEC EDGAR, no API key (set SEC_UA to your own name and email)"),
    dict(key="stocks", path=("stocks", "panel.parquet"), size="14 MB",
         what="74 optionable names, daily 2005-2026. Incomplete on purpose: "
              "Tiingo's free tier serves 74 of the 190 requested and no delisted "
              "names at all, so every long-side result off it is biased upward",
         how="script", script="05_studies/scripts/stock_data.py", needs="TIINGO_API_KEY", big=False,
         get="Tiingo daily API, needs TIINGO_API_KEY"),
    dict(key="dolt-options", path=("dolt", "options"), size="7.9 GB",
         what="full EOD option chains with greeks, 2,321 tickers, 2019-02 onward",
         how="dolt", repo="post-no-preference/options", needs=None, big=True,
         get="DoltHub clone, free. The branch is master, not main"),
    dict(key="dolt-stocks", path=("dolt", "stocks"), size="4.4 GB",
         what="daily OHLCV, unadjusted. The split table is ~33% duplicate rows, "
              "which manufactures fake -90% days; see the guard in DATA.md",
         how="dolt", repo="post-no-preference/stocks", needs=None, big=True,
         get="DoltHub clone, free. Same publisher as the options database; only "
             "the options clone is recorded as verified in HANDOFF.md"),
    dict(key="dolt-earnings", path=("dolt", "earnings"), size="1.7 GB",
         what="earnings dates and results",
         how="dolt", repo="post-no-preference/earnings", needs=None, big=True,
         get="DoltHub clone, free. Same caveat as dolt-stocks"),
    dict(key="gex", path=("squeeze_dix_gex.csv",), size="small",
         what="SqueezeMetrics DIX and GEX daily, 15 years. Feeds the gamma gate "
              "that several studies condition on",
         how="manual", needs=None, big=False,
         get="download the free daily CSV from squeezemetrics.com and save it as "
             "squeeze_dix_gex.csv at the root of DATA_ROOT"),
    dict(key="minute", path=("minute",), size="51 MB",
         what="1-minute bars for SPY/QQQ and friends",
         how="manual", needs="POLYGON_API_KEY", big=False,
         get="04_live_system/fetch_minutes.py pulls these from Polygon, but "
             "HANDOFF.md records the key on file as free tier, which serves "
             "reference data only and no historical aggregates. On a free key "
             "this script cannot rebuild them"),
    dict(key="opt_eod", path=("opt_eod",), size="1.1 GB",
         what="real SPY (24.7M rows, 2008-2025) and QQQ EOD chains with bid/ask, "
              "IV and greeks. The file most studies here depend on",
         how="copy", needs=None, big=False,
         get="not reconstructible from any source this repo names. The Dolt "
             "options database starts in 2019, so it cannot fill the 2008-2018 "
             "history. Copy the directory from a machine that has it, or set "
             "IDT_DATA_ROOT to point at one"),
    dict(key="spxw", path=("spxw", "data_opt.parquet"), size="251 MB",
         what="real SPXW intraday quotes, 1,919 sessions 2016-09 to 2024-05 on a "
              "30-minute grid. Every real-quote verdict in 02_findings rests on it",
         how="copy", needs=None, big=False,
         get="not reconstructible. Copy it, or set IDT_DATA_ROOT"),
    dict(key="bigmove", path=("bigmove",), size="357 MB",
         what="tail-move study panels",
         how="derived", needs=None, big=False,
         get="derived: run 05_studies/scripts/bigmove_hunt.py and "
             "smallcap_tails.py once dolt-stocks is cloned"),
    dict(key="scratch", path=("scratch",), size="small",
         what="Cboe benchmark index CSVs (CNDR, BFLY, PUT, WPUT, BXM, CMBO, SPX) "
              "and the Open Source Asset Pricing files the spinoff studies read",
         how="manual", needs=None, big=False,
         get="download the Cboe index CSVs and OSAP PredictorLSretWide.csv by "
             "hand into DATA_ROOT/scratch. Each study names the file it wants"),
]

def wrap(text, indent="      "):
    """Six-space indent, hard wrap. These descriptions are the whole point of the
    script, and an unwrapped 200-column paragraph does not get read."""
    return textwrap.fill(text, width=94, initial_indent=indent, subsequent_indent=indent)


MAX_ENTRIES = 40000     # a Dolt clone is a lot of small files; do not walk it forever


def disk_size(path):
    """Bytes on disk, and whether the walk was cut short. Reporting 'at least X'
    beats spending a minute counting a 14 GB clone nobody asked about."""
    if os.path.isfile(path):
        return os.path.getsize(path), False
    total = seen = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
            seen += 1
            if seen >= MAX_ENTRIES:
                return total, True
    return total, False


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def dolt_status():
    exe = shutil.which("dolt")
    if not exe:
        return None, (
            "MISSING. It is the only way to reach the free DoltHub option and\n"
            "            stock databases. Install it with:\n"
            "              macOS:  brew install dolt\n"
            "              Linux:  curl -L https://github.com/dolthub/dolt/releases/latest"
            "/download/install.sh | sudo bash\n"
            "              other:  https://github.com/dolthub/dolt/releases")
    try:
        v = subprocess.run([exe, "version"], capture_output=True, text=True, timeout=20)
        return exe, v.stdout.strip().splitlines()[0] if v.stdout.strip() else "installed"
    except Exception as e:                                  # noqa: BLE001
        return exe, f"installed, but `dolt version` failed: {e}"


def state(asset):
    p = paths.data(*asset["path"])
    if not os.path.exists(p):
        return "absent", ""
    n, cut = disk_size(p)
    if n == 0:
        # An empty directory is the worst of the three states: it reads as
        # "installed" to every caller and returns no rows to any of them.
        return "EMPTY", "0 B"
    return "present", ("at least " + human(n)) if cut else human(n)


def run_script(rel, args=()):
    p = os.path.join(paths.REPO_ROOT, rel)
    if not os.path.exists(p):
        print(f"      cannot run {rel}: file not found")
        return False
    print(f"      running {rel} {' '.join(args)}")
    r = subprocess.run([sys.executable, p, *args], cwd=paths.REPO_ROOT)
    return r.returncode == 0


def run_dolt(exe, repo, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"      dolt clone {repo} -> {dest}")
    r = subprocess.run([exe, "clone", repo, dest], cwd=os.path.dirname(dest))
    if r.returncode != 0:
        return False
    # The branch is master, not main. Getting this wrong yields an empty database
    # that answers every query with zero rows, which is the failure that wastes a day.
    subprocess.run([exe, "checkout", "master"], cwd=dest)
    return True


def report(rows, dolt_exe, dolt_note, key_state):
    print(f"DATA_ROOT   {paths.DATA_ROOT}")
    print(f"            {'exists' if os.path.isdir(paths.DATA_ROOT) else 'does not exist yet'}"
          "  (override with IDT_DATA_ROOT)")
    print(f"STATE_ROOT  {paths.STATE_ROOT}   (live snapshots; not market data)")
    print()

    print("TOOLS")
    print(f"  dolt      {dolt_note}")
    print()

    print("KEYS       (none are needed to run this script)")
    for name, present in key_state.items():
        print(f"  {'set    ' if present else 'missing'}   {name}")
    print()

    w = max(len(a["key"]) for a in ASSETS)
    print("INVENTORY")
    print(f"  {'asset'.ljust(w)}  {'documented':>10}  {'on disk':>14}  status")
    print(f"  {'-' * w}  {'-' * 10}  {'-' * 14}  {'-' * 8}")
    for a, st, sz in rows:
        print(f"  {a['key'].ljust(w)}  {a['size']:>10}  {sz:>14}  {st}")
    print()

    missing = [(a, st) for a, st, _ in rows if st != "present"]
    if not missing:
        print("Everything in the inventory is present. Nothing to do.")
        return
    print("WHAT TO DO ABOUT EACH ONE THAT IS NOT THERE")
    for a, st in missing:
        print(f"\n  {a['key']}  ({a['size']}, {st})")
        print(wrap(a["what"]))
        print(wrap(a["get"]))
        if a["needs"] and not key_state.get(a["needs"], False):
            print(f"      BLOCKED: needs {a['needs']}. Copy .env.example to .env and fill it in.")
        if a["how"] == "script":
            print(f"      command: venv/bin/python {a['script']}")
        elif a["how"] == "dolt":
            dest = paths.data(*a["path"])
            print(f"      command: dolt clone {a['repo']} {dest} && "
                  f"(cd {dest} && dolt checkout master)")
            if not dolt_exe:
                print("      BLOCKED: dolt is not installed, see TOOLS above.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="bootstrap_data.py",
        description="Report the market-data inventory, and fetch the parts that are fetchable.")
    ap.add_argument("--fetch", action="store_true",
                    help="actually download. Without it this only reports.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only. This is already the default; the flag is for scripts.")
    ap.add_argument("--only", metavar="ASSET", action="append", default=[],
                    help="restrict to one asset key. Repeatable. Required for the "
                         "multi-gigabyte Dolt clones.")
    ap.add_argument("--list", action="store_true", help="print the asset keys and exit")
    args = ap.parse_args(argv)

    if args.list:
        for a in ASSETS:
            print(f"{a['key']:14s} {a['size']:>8}  {a['what'][:70]}")
        return 0

    unknown = [k for k in args.only if k not in {a["key"] for a in ASSETS}]
    if unknown:
        print(f"unknown asset(s): {', '.join(unknown)}. Try --list.")
        return 2

    dolt_exe, dolt_note = dolt_status()
    key_state = dict(keys.status())
    key_state["TIINGO_API_KEY"] = bool(keys.get("TIINGO_API_KEY"))

    rows = []
    for a in ASSETS:
        st, sz = state(a)
        rows.append((a, st, sz or "-"))

    fetching = args.fetch and not args.dry_run
    print("BOOTSTRAP DATA" + ("" if fetching else "   (dry run: nothing will be downloaded)"))
    print()
    report(rows, dolt_exe, dolt_note, key_state)

    if not fetching:
        print("\nThis was a dry run. Add --fetch to download the keyless assets,")
        print("or --fetch --only dolt-options for a specific one.")
        return 0

    print("\nFETCHING")
    ok = skipped = failed = 0
    for a, st, _sz in rows:
        if args.only and a["key"] not in args.only:
            continue
        if st == "present":
            # Never touch data that is already there. A bootstrap that can delete
            # 14 GB is a bootstrap nobody runs twice.
            print(f"  {a['key']}: present, leaving it alone")
            skipped += 1
            continue
        if a["how"] in ("manual", "copy", "derived"):
            print(f"  {a['key']}: this script cannot fetch it.")
            print(wrap(a["get"]))
            skipped += 1
            continue
        if a["big"] and a["key"] not in args.only:
            print(f"  {a['key']}: {a['size']} download, skipped. "
                  f"Ask for it by name: --fetch --only {a['key']}")
            skipped += 1
            continue
        if a["needs"] and not key_state.get(a["needs"], False):
            print(f"  {a['key']}: needs {a['needs']}, which is not set. Skipped.")
            skipped += 1
            continue
        if a["how"] == "dolt" and not dolt_exe:
            print(f"  {a['key']}: dolt is not installed, see TOOLS above. Skipped.")
            skipped += 1
            continue
        print(f"  {a['key']}:")
        good = (run_dolt(dolt_exe, a["repo"], paths.data(*a["path"]))
                if a["how"] == "dolt" else run_script(a["script"]))
        if good:
            ok += 1
        else:
            failed += 1
            print(f"      {a['key']} did not complete. The output above says why.")

    print(f"\n{ok} fetched, {skipped} skipped, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
