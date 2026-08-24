"""Portfolio-level detail for the OSAP 'Spinoff' predictor: leg composition and breadth."""
import csv, math, statistics as st
from collections import defaultdict

from idt import paths

# Under DATA_ROOT/scratch. This was a /private/tmp scratchpad belonging to the
# session that wrote the file, so the open() below failed everywhere, always.
SCRATCH = "scratch"


def tstat(xs):
    m = st.mean(xs); s = st.stdev(xs)
    return m, m / (s / math.sqrt(len(xs)))


def main():
    rows = []
    with open(paths.require_data(SCRATCH, "allports.csv")) as f:
        for r in csv.DictReader(f):
            if r["signalname"] == "Spinoff":
                rows.append(r)

    print(f"Spinoff portfolio rows: {len(rows)}")
    ports = sorted({r["port"] for r in rows})
    print(f"portfolios: {ports}")

    by = defaultdict(list)
    for r in rows:
        by[r["port"]].append(r)

    for p in ports:
        rs = sorted(by[p], key=lambda x: x["date"])
        rets = [float(x["ret"]) for x in rs if x["ret"] not in ("", "NA")]
        nl = [float(x["Nlong"]) for x in rs if x["Nlong"] not in ("", "NA")]
        m, t = tstat(rets)
        print(f"\nport {p}: {rs[0]['date']} .. {rs[-1]['date']}  n={len(rets)}")
        print(f"   mean={m:+.3f}%/mo  t={t:+.2f}")
        if nl:
            print(f"   Nlong: median={st.median(nl):.0f}  min={min(nl):.0f}  max={max(nl):.0f}")

    # breadth of the spinoff (long) leg over time by decade
    print("\n===== Breadth of the spinoff leg by decade =====")
    dec = defaultdict(list)
    for r in rows:
        if r["port"] == max(ports):
            try:
                dec[int(r["date"][:4]) // 10 * 10].append(float(r["Nlong"]))
            except (ValueError, KeyError):
                pass
    for d in sorted(dec):
        v = dec[d]
        print(f"  {d}s: median Nlong={st.median(v):.0f}  min={min(v):.0f}  max={max(v):.0f}  months={len(v)}")


if __name__ == "__main__":
    main()
