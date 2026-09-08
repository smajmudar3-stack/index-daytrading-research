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

## Run it

Tested from scratch on a machine that had never seen the project. The steps below are what
actually worked, not what should have.

### You need

| | |
|---|---|
| **Python 3.11+** | macOS ships 3.9 and it is **not enough**. `python3 --version` to check; `brew install python@3.12` if needed. The installer searches for a suitable one, so it need not be your default. |
| **git** | already on most Macs |
| **An Unusual Whales API key** | [unusualwhales.com](https://unusualwhales.com) — required for trade cards, see below |
| *Anthropic API key* | optional; for the desk-note reading and the monthly calendar refresh |
| *FRED API key* | optional and [free](https://fred.stlouisfed.org/docs/api/api_key.html); makes the macro calendar a plain API call |

### Install

```bash
git clone https://github.com/smajmudar3-stack/index-daytrading-research.git
cd index-daytrading-research
./install.sh
```

`install.sh` finds a suitable Python, builds a virtualenv, installs dependencies, creates
your config, runs the verification gates and the full test suite, and installs the scheduled
jobs. Safe to re-run after a pull. **It should end with `0 failure(s)`** — if it does not,
stop, because a failing gate means something is broken rather than merely unconfigured.

Then put your key in the `.env` it created:

```
UNUSUALWHALES_API_KEY=your-key-here
```

and open **http://127.0.0.1:8095/markets** (`IDT_PORT=8096` if 8095 is taken).

### What you see, and when

**Immediately** the page loads and every card states its own condition — *"weekly_snapshot.json
has never been written"*, *"No desk note has been ingested yet"*. That is deliberate: panels
have four states and an empty one always says why, because "no closed trades yet" and "the book
could not be read" lead to opposite actions and both used to render as blank. The macro
calendar and the convexity numbers work from the first second.

**Within five minutes** the scheduled cycle fills in gap candidates, gamma levels and the
market panels.

**The first weekly scan** takes 2–4 minutes: a year of daily history for ~1,550 names in
batches, a $25m-a-day liquidity screen, then the top-ranked 200 analysed in full.

**Trade cards need one thing more.** The engine will not propose a trade it cannot give a
macro reason for, and that reason comes from market commentary read in daily. Without that
feed the book stays **empty by design** — the engine refusing to trade on technical
indicators alone, which is the specific failure the rewrite existed to remove.

### Why the Unusual Whales key is not optional

Four of the seven inputs the engine votes on come from that one vendor, and a card needs at
least three inputs before it will be issued. Measured with the key removed: **0 cards, 32
names refused for "too few inputs"**. Everything else on the page still works without it.

### What will not work

- **The historical backtests.** ~16 GB of market data lives outside the repo and is not in
  git; anything in `05_studies/` that reads it fails on a fresh clone. Expected, not a bug —
  see [`06_data_guide/DATA.md`](06_data_guide/DATA.md). The live dashboard does not touch it.
- **The desk-note ingest** needs a Gmail connection and the Claude CLI.
- **The monthly calendar refresh** needs the Claude CLI, because the BLS schedule pages
  return HTTP 403 to any scripted request. A FRED key removes that dependency. The calendar
  ships with real dates already verified.

### If something breaks

| symptom | cause |
|---|---|
| `python 3.9 is too old` | `brew install python@3.12`, re-run `./install.sh` |
| `Address already in use` | something else holds 8095 — use `IDT_PORT=8096` |
| every card empty | normal before the first scan; wait five minutes |
| no trade cards, ever | check the key is in `.env`, then read the **"Considered and thrown out"** panel — it names every rejected candidate and the reason |
| anything else | `./venv/bin/python3 scripts/verify.py` |

**Nothing here places an order.** `risk_gates.DRY_RUN = True`, `LIVE_AGENT = False`, and a
test asserts no order-placement code has appeared. This is research tooling, not advice.

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

### Key findings

**[02_findings/INTRADAY_DIRECTION.md](02_findings/INTRADAY_DIRECTION.md)** — the
full answer on intraday direction: the ~53% accuracy ceiling, the theta hurdle
that exceeds it, and the one dealer-gamma signal that clears it.

**[02_findings/VOLATILITY.md](02_findings/VOLATILITY.md)** — volatility is 360×
the signal in direction (OOS R² 39.8%), and the market prices it better than we
forecast it. Why an 88.5% win rate still loses money.

**[02_findings/VEHICLE_CHOICE.md](02_findings/VEHICLE_CHOICE.md)** — the same
signal is +3%/yr as stock and −15%/yr as options. A real edge does not make
every vehicle for it profitable.

**[02_findings/WING_ECONOMICS.md](02_findings/WING_ECONOMICS.md)** — can a tail
hedge rescue premium selling? The wing costs more than it pays, and the naked
version is a 150×-your-average-gain ruin machine.

**[02_findings/METHODOLOGY_TRAPS.md](02_findings/METHODOLOGY_TRAPS.md)** — sixteen
ways a backtest lies. Eight of these produced fake winning strategies in this
repo before being caught. Check any new backtest against this list first.

### Where everything lives

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
