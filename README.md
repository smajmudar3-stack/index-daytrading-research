# index-daytrading-research

An SPX/NDX index-options day-trading system: 26 research sweeps, a local dashboard
and its engines, 117 backtest and hunt harnesses, and a guide to 16 GB of market
data held outside git.

**The value of this repo is the negative results.** Most of what was tested loses
money, and these documents record which parts and by how much. Three things
survived. Read them before anything else.

> **When two documents here disagree, [`docs/VERDICT_LOG.md`](docs/VERDICT_LOG.md)
> wins.** It is the only place a verdict is recorded. The research changed its mind
> twice, and for a while all three answers shipped as if all three were current.

---

## Read in this order

| # | read | why |
|---|---|---|
| 1 | **[02_findings/WHAT_WORKS.md](02_findings/WHAT_WORKS.md)** | The three surviving signals and their measured strength. 89 lines |
| 2 | **[02_findings/METHODOLOGY_TRAPS.md](02_findings/METHODOLOGY_TRAPS.md)** | Twelve ways a backtest lies. **Four produced fake winning strategies here before being caught.** Check any new result against it |
| 3 | **[docs/VERDICT_LOG.md](docs/VERDICT_LOG.md)** | Every claim, its status, the measurement that changed it, and the file that carries the evidence |
| 4 | **[02_findings/WHAT_FAILED.md](02_findings/WHAT_FAILED.md)** | The larger and more useful half of the results |
| 5 | **[01_START_HERE/README.md](01_START_HERE/README.md)** | What the system is, what it can do, and how to run it |

## The one-paragraph summary

Most of what was tested does not work, and the value here is knowing *which* parts.
**Every credit structure tested is negative on real quotes** (|t| up to 24.5 across
147,350 de-duplicated SPY trades, entering at the ask and exiting at the bid).
Far-OTM lottery buying returned **−90% to −48%** across 10,535,928 purchases held
to expiry. Earnings straddles lost **35.03% per trade, t = −95.7**. There is no
reliable intraday directional edge: 56 features and 220 conditions produced **zero**
combinations clearing 55% on both train and validate. And the 0DTE iron condor this
project was built around, once reported at **+3.7% per trade**, is approximately
break-even on 1,919 sessions of real SPXW bid/ask, because its P&L came from a
pricing model rather than from prices.

Three things survived honest testing: **short interest** (IC −0.107 at 63 days, and
the sign is *negative*, the opposite of the squeeze thesis), **VIX backwardation**
(t = +3.9 / +2.8 / +2.1 across all three splits), and **low dealer gamma** as a
regime filter (8 of 8 directional structures pay more there). None of the three is
an options strategy.

## Directory map

| folder | what's in it |
|---|---|
| **[01_START_HERE](01_START_HERE/)** | Entry point, runbook, engine design, session handoff |
| **[02_findings](02_findings/)** | The current verdicts, including everything that failed |
| **[03_research](03_research/)** | 26 literature and repo sweeps. [`INDEX.md`](03_research/INDEX.md) carries a one-line verdict for each, so you can see which produced surviving findings without opening 26 documents |
| **[04_live_system](04_live_system/)** | The dashboard and its engines |
| **[05_studies](05_studies/)** | The backtests and hunts that produced the findings |
| **[06_data_guide](06_data_guide/)** | What is in the 16 GB, and how to query it |
| **[07_superseded](07_superseded/)** | Two retired documents, kept as a record. **Nothing in there is an instruction** |
| **[docs](docs/)** | [VERDICT_LOG.md](docs/VERDICT_LOG.md), the repo [AUDIT.md](docs/AUDIT.md) and the [PLAN.md](docs/PLAN.md) it produced |
| **[MANIFEST.md](MANIFEST.md)** | Every file, with current line counts |

---

## Run it

```bash
python3 -m venv venv && venv/bin/pip install -e .
venv/bin/idt bootstrap     # create the state dir, check API keys, report what is missing
venv/bin/idt serve         # http://127.0.0.1:8094
```

Two more verbs: `idt refresh` runs one full signal cycle, `idt audit` runs the 23
value-level health checks. The CLI is `idt/cli.py`.

**The dashboard is `http.server` from the Python standard library**, bound to
`127.0.0.1:8094`. It is not FastAPI, despite what this file claimed until
2026-08-24, and it has no framework, no build step and no client-side state. Five
tabs, rendered server-side:

| tab | what it decides |
|---|---|
| 0DTE | SPX/NDX same-day structure, gated on the dealer gamma regime |
| Gap & Go | Opening-range continuation |
| Swing | Days-to-two-weeks direction, weighted vote across 6 signals |
| Account & Risk | Sizing, ruin bounds, position limits |
| Black Swan | Far-OTM convexity candidates, only where spread ≤ 20% |

Each tab logs its calls to `scorecard.py`, which tracks hit rate, expectancy and
calibration per tab, so the weights can be re-estimated from live results instead
of staying at their fabricated priors. `signal_weights.py` marks which weights are
measured and which are still priors; that distinction is the best idea in the
codebase and should not be flattened.

**What a fresh clone does not get.** The 16 GB of market data is not in git and
cannot be reconstructed from it. `idt bootstrap` prints what is missing;
[06_data_guide/DATA.md](06_data_guide/DATA.md) inventories it. Every backtest in
`05_studies/` needs it. The dashboard does not, and renders with panels marked
unavailable.

**Nothing here places an order.** `risk_gates.DRY_RUN = True`, `LIVE_AGENT = False`,
and no order-placement code exists anywhere in the repo.

## Verify

```bash
venv/bin/python scripts/verify.py
```

Offline by design: the 16 GB of data is not in git, so a gate that needed it would
be skipped on every fresh clone, and a skipped gate is not a gate.
