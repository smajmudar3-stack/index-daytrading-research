# Start here

**Last true as of 2026-08-24.**

This is an archived research bundle for an SPX/NDX index-options day-trading
system, plus the local dashboard that was built on it. **Its value is the negative
results.** Most of what was tested loses money, and this repo records exactly which
parts and by how much. Almost nothing here is a strategy you should run.

If you read one line, read this one: **when two documents in this repo disagree,
[`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md) wins.** It is the only place a
verdict is recorded.

---

## What survived

Three signals passed honest testing. None of them is an options strategy.

| signal | measurement | note |
|---|---|---|
| **Short interest** | IC −0.107 at 63 days, −0.068 at 21 days, n = 13,219, monotone across every bucket | **The sign is negative.** High short float predicts *lower* forward returns. The squeeze thesis is backwards |
| **VIX backwardation** | t = **+3.9 / +2.8 / +2.1** on train, validate and test | The only signal that held on all three splits. It degrades and never flips |
| **Low dealer gamma** | **8 of 8** directional structures paid more in low gamma than high | A regime filter, not a direction call. It says when directional bets get paid at all |

One further finding is real and deserves its own line, because it is the most
misread thing in the repo:

**Dealer gamma predicts the intraday range.** Realised range as a multiple of the
VIX9D-implied move is **0.843× on high-gamma days against 1.139× on low-gamma**,
t = −13.2, p = 1.3e-37, stable in every four-year sub-period across 15 years.
**And it does not convert into profit at real option prices.** That second sentence
is part of the finding, not a caveat on it. The market has it priced.

Details and the weight registry: [`../02_findings/WHAT_WORKS.md`](../02_findings/WHAT_WORKS.md).

## What did not

| claim | measured |
|---|---|
| Every credit structure, on real quotes | **All negative**, on 147,350 de-duplicated trades, \|t\| up to 24.5 |
| The 0DTE iron condor at +3.7%/trade | Approximately **break-even** on 1,919 sessions of real SPXW bid/ask. The 11:00 entry the live system used: **−1.70%** |
| "Below the gamma flip = buy premium" | **−7.2%** straddle, **−19.1%** strangle per trade |
| Buying 0DTE premium on any directional signal | **−10% to −11%** per trade |
| Any intraday directional edge on SPX or NDX | 56 features, 220 conditions, thousands of combinations: **zero** clear 55% on train and validate |
| Far-OTM lottery buying | **−90% to −48%** on 10,535,928 purchases held to expiry |
| Earnings straddles | **−35.03%** per trade, t = −95.7 |
| Sector rotation, and every swing options overlay | Beaten by simply owning SPY on return, Sharpe **and** drawdown |

Details: [`../02_findings/WHAT_FAILED.md`](../02_findings/WHAT_FAILED.md) and
[`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md).

---

## Where to start reading

In this order. It is short.

1. **[`../02_findings/WHAT_WORKS.md`](../02_findings/WHAT_WORKS.md)**. The three
   surviving signals and their measured strength. 89 lines.
2. **[`../02_findings/METHODOLOGY_TRAPS.md`](../02_findings/METHODOLOGY_TRAPS.md)**.
   Twelve ways a backtest lies. **Four of them produced fake winning strategies in
   this repo before being caught.** Read this before writing any new backtest, and
   check any new result against it before believing it.
3. **[`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md)**. Every claim, its status,
   the measurement that changed it, and the file that carries the evidence.
4. **[`../02_findings/WHAT_FAILED.md`](../02_findings/WHAT_FAILED.md)**. The larger
   and more useful half of the results.
5. **[`../02_findings/FINDINGS.md`](../02_findings/FINDINGS.md)**. The full record
   of the direction hunt, and §1 is the real-quote re-run that killed the condor.

Then, if you are going to touch the code:

- **[`ENGINE.md`](ENGINE.md)**. The agent and its gate stack. The architecture is
  the good part; the strategy it was built to trade is refuted, and the file says so
  at the top.
- **[`RUNBOOK.md`](RUNBOOK.md)**. Day-to-day operations.
- **[`HANDOFF.md`](HANDOFF.md)**. The long session-state document. §3 is the
  147,350-trade premium-selling null, which is one of the load-bearing results here.
- **[`MES_STRATEGY.md`](MES_STRATEGY.md)**. The overnight MES/MNQ drift, in
  **futures or shares, never options**. It is the one positive result in this folder
  that was not refuted, and it is also the one that was never re-tested on real
  quotes the way everything else was. Treat it as unconfirmed rather than validated.

## What is deliberately not here

`STRATEGY_0DTE.md` and `RULES.md` used to live in this folder. They were moved to
[`../07_superseded/`](../07_superseded/) on 2026-08-24 because they were still being
read as instructions after their central claims had been refuted. They are kept as a
record of how the conclusion moved. **Nothing in that directory is an instruction.**

---

## How to run it

Three commands from a fresh clone. The dashboard is a plain `http.server` from the
standard library on `127.0.0.1:8094`.

```bash
python3 -m venv venv && venv/bin/pip install -e .
venv/bin/idt bootstrap     # create the state dir, check API keys, report what is missing
venv/bin/idt serve         # http://127.0.0.1:8094
```

Two more verbs: `idt refresh` runs one full signal cycle, `idt audit` runs the 23
value-level health checks against a live page.

**What you will not get on a fresh clone.** The 16 GB of market data is not in git
and cannot be reconstructed from it. `idt bootstrap` says exactly what is missing;
[`../06_data_guide/DATA.md`](../06_data_guide/DATA.md) inventories it. Every backtest
in `05_studies/` needs it. The dashboard does not, and will render with panels
marked unavailable.

**API keys.** Three are read, none is required to render the page: each one switches
on a panel that otherwise says unavailable. Copy `.env.example` to `.env`. See
`idt/keys.py`.

**Nothing in this repo places an order.** `risk_gates.DRY_RUN = True`,
`LIVE_AGENT = False`, and no order-placement code exists anywhere in it.

## Before you say a change is done

```bash
venv/bin/python scripts/verify.py
```

Offline by design: the 16 GB of data is not in git, so a gate that needed it would
be skipped on every clone, and a skipped gate is not a gate.
