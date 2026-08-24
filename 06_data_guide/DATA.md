# Data guide

**The 16 GB of market data is deliberately not copied into this bundle.**
Duplicating a 14 GB Dolt clone to make an archive would double disk use for no
benefit. This file inventories what exists and how to query it.

> **Where it lives, corrected 2026-08-24.** The paths below were written as
> `~/index-daytrading/data/`, which is the original author's machine and exists
> nowhere else. Resolve them through `idt.paths` instead: `DATA_ROOT` defaults to
> `<repo>/data` and is overridden by the `IDT_DATA_ROOT` environment variable, so
> pointing at an existing copy is one variable rather than 26 file edits. Run
> `idt bootstrap` to see what is present and what is missing.
>
> **Nothing in git can reconstruct any of this.** `paths.require_data()` raises a
> `FileNotFoundError` that names the fix rather than failing three frames deep
> inside pandas, and `paths.have_data()` lets a caller print an honest "not
> installed" instead. Use them. A silently-created empty directory reads downstream
> as "no rows" rather than "not installed", which is why `paths.data()` deliberately
> creates nothing.

## Inventory

| path | size | what |
|---|---:|---|
| `data/dolt/` | **14 GB** | Dolt clones — the primary source |
| ├─ `options/` | 7.9 GB | Full EOD option chains with greeks |
| ├─ `stocks/` | 4.4 GB | Daily OHLCV, unadjusted |
| └─ `earnings/` | 1.7 GB | Earnings dates and results |
| `data/opt_eod/` | 1.1 GB | SPY/QQQ option parquets |
| `data/bigmove/` | 357 MB | Tail-move study panels |
| `data/spxw/` | 251 MB | SPXW real-quote intraday chains |
| `data/minute/` | 51 MB | Minute bars |
| `data/swing/` | 14 MB | 56-ticker daily panel, 315,385 rows, 1998–2026 |
| `data/stocks/` | 14 MB | Stock feature panel |
| `data/spinoffs/` | 1.2 MB | Spinoff event study |

### Largest individual files

| file | size |
|---|---:|
| `opt_eod/SPY_options.parquet` | 608 MB |
| `opt_eod/QQQ_options.parquet` | 370 MB |
| `spxw/data_opt.parquet` | 251 MB |
| `bigmove/smallcap_panel.parquet` | 250 MB |
| `bigmove/panel.parquet` | 87 MB |

## Querying Dolt

```bash
cd "$(venv/bin/python -c 'from idt import paths; print(paths.data("dolt"))')"
dolt sql -q "select * from options.option_chain limit 5" -r csv
```

From Python, the pattern used throughout `scripts/`:

```python
def dolt(sql, timeout=900):
    r = subprocess.run(["dolt", "sql", "-q", sql, "-r", "csv"], cwd=DOLT,
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        return pd.DataFrame()
    return pd.read_csv(StringIO(r.stdout))
```

## Data quality warnings

These are real defects in the source data that have already corrupted results
once. Handle them in any new study.

**`stocks.ohlcv` is unadjusted, and the split table is ~33% duplicate rows.** A
raw return series therefore contains fake −90% days that look exactly like black
swans. The guard used in `scripts/smallcap_tails.py`:

```python
# Any single day beyond +/-60% is a corporate action, not a move.
r = r.mask(r.abs() > 0.60)
```

**`^SPX` runs up to 15 minutes behind `^GSPC`** for spot, but `^GSPC` has zero
listed expiries — so spot must come from one and the chain from the other. The
live system prefers an Unusual Whales 1-minute bar and rejects any bar older
than 15 minutes.

**`^TNX` is already expressed in percent.** Do not divide by 10.

**Underlying price derived from 0.45–0.55 delta strikes is a proxy, not a
price.** Deriving prices this way once produced the false conclusion that no
optionable stocks trade below $10; there are 46.

**Dark pool prints execute inside the NBBO.** A `price >= ask` test almost never
fires. Classify by position in the spread, and exclude midpoint prints — a dark
pool's purpose is midpoint matching, so a large share carry no directional
information at all.
