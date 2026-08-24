"""Compute in-sample vs post-publication performance of the OSAP 'Spinoff' predictor.

Data: Chen & Zimmermann Open Source Asset Pricing, monthly long-short returns
      (PredictorLSretWide.csv), Oct 2025 release.
Original paper (OP): Cusatis, Miles & Woolridge (1993 JFE), sample 1965-1988.
"""
import csv, math, statistics as st

from idt import paths

# Under DATA_ROOT/scratch. This was a /private/tmp scratchpad belonging to the
# session that wrote the file, so the open() below failed everywhere, always.
PATH = "scratch/PredictorLSretWide.csv"

def tstat(xs):
    n = len(xs)
    if n < 3:
        return float("nan"), float("nan"), n
    m = st.mean(xs)
    s = st.stdev(xs)
    return m, m / (s / math.sqrt(n)), n

def load():
    with open(paths.require_data(PATH)) as f:
        rows = list(csv.DictReader(f))
    return rows

def series(rows, col):
    out = []
    for r in rows:
        v = r.get(col, "")
        if v not in ("", "NA", "NaN", None):
            try:
                out.append((r["date"], float(v)))
            except ValueError:
                pass
    return out

def window(s, lo, hi):
    return [v for d, v in s if lo <= int(d[:4]) <= hi]

def report(name, s, spans):
    print(f"\n===== {name} =====")
    if s:
        print(f"coverage: {s[0][0]} .. {s[-1][0]}  ({len(s)} monthly obs)")
    for label, lo, hi in spans:
        xs = window(s, lo, hi)
        m, t, n = tstat(xs)
        if n < 3:
            print(f"  {label:<34} n={n:<4} (insufficient)")
            continue
        ann = m * 12
        sharpe = (m / st.stdev(xs)) * math.sqrt(12)
        print(f"  {label:<34} n={n:<4} mean={m:+.3f}%/mo  t={t:+.2f}  ann={ann:+.1f}%  SR={sharpe:+.2f}")

def main():
    rows = load()
    cols = [c for c in rows[0].keys() if c != "date"]
    print(f"OSAP predictors in file: {len(cols)}")

    spans = [
        ("OP in-sample 1965-1988", 1965, 1988),
        ("post-sample pre-pub 1989-1993", 1989, 1993),
        ("post-publication 1994-end", 1994, 2100),
        ("modern 2005-2024", 2005, 2024),
        ("modern 2015-2024", 2015, 2024),
    ]

    sp = series(rows, "Spinoff")
    report("Spinoff (Cusatis-Miles-Woolridge 1993)", sp, spans)

    # Library-wide benchmark: how does Spinoff rank in 2015-2024?
    print("\n===== Library-wide context (2015-2024) =====")
    stats = []
    for c in cols:
        xs = window(series(rows, c), 2015, 2024)
        if len(xs) >= 60:
            m, t, n = tstat(xs)
            stats.append((c, m, t))
    ts = [t for _, _, t in stats]
    print(f"predictors with >=60 obs in 2015-2024: {len(stats)}")
    print(f"  share t>2: {sum(1 for t in ts if t > 2)/len(ts)*100:.1f}%")
    print(f"  share t>3: {sum(1 for t in ts if t > 3)/len(ts)*100:.1f}%")
    print(f"  median t : {st.median(ts):+.2f}")
    print(f"  mean  ret: {st.mean([m for _, m, _ in stats]):+.3f}%/mo")
    rank = sorted(stats, key=lambda x: -x[2])
    pos = [i for i, (c, _, _) in enumerate(rank) if c == "Spinoff"]
    if pos:
        c, m, t = rank[pos[0]]
        print(f"  Spinoff rank by t-stat: {pos[0]+1} of {len(rank)}  (mean={m:+.3f}%/mo, t={t:+.2f})")

    # McLean-Pontiff style decay for Spinoff
    ins = window(sp, 1965, 1988)
    post = window(sp, 1994, 2100)
    if ins and post:
        mi = st.mean(ins); mp = st.mean(post)
        print("\n===== Decay =====")
        print(f"  in-sample mean      : {mi:+.3f}%/mo")
        print(f"  post-pub mean       : {mp:+.3f}%/mo")
        print(f"  decay               : {(1 - mp/mi)*100:.1f}% of in-sample mean")
        pred = -0.122 + 0.61 * mi
        print(f"  OSAP fitted forecast: {pred:+.3f}%/mo  (-0.122 + 0.61 x in-sample)")

if __name__ == "__main__":
    main()
