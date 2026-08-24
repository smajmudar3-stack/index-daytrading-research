# Real-Chain Options Backtesting: Data Sources and Engine Audit

Sweep date: 2026-08-06. Companion to `RESEARCH_SWING_REPOS.md` and `FINDINGS.md`.

Scope: (1) sources of real historical option chains with **bid AND ask**, beyond the
SPY/QQQ/IWM EOD set already on disk; (2) a code-level audit of the
`lambdaclass/options_portfolio_backtester` engine, since we may reuse rather than rewrite;
(3) whether anyone has done a rigorous real-chain study of **directional long-option**
swing trades, as opposed to the premium-selling work that dominates the space.

Method: every claim about a repo comes from reading its source, not its README. Every
claim about our own data comes from running a query against the parquet on disk. Numbers
computed tonight are marked **[measured]**.

---

## 0. The headline, before the detail

1. **The engine's core is genuinely well-built — the multi-leg presets are not.** Fill
   logic crosses the spread by default, cash-flow and valuation invariants are asserted at
   runtime, and the authors have publicly diagnosed two of their own bug classes. But
   `iron_condor()` **silently ignores its own `short_delta_call`, `short_delta_put` and
   `wing_width` arguments** — all four legs get identical filters. Anyone who calls it gets
   a random 4-leg structure, not a condor. See §2.3. This is the single most important
   finding in this document.
2. **There is no options margin model at all.** Credit strategies are sized by dividing
   capital by the *credit received*, not by max loss. An iron condor is therefore sized
   ~15-20x over-levered by default. See §2.4.
3. **Our chain data is EOD-only, so 0DTE intraday entries are not testable with it** —
   and the `mark` column is corrupt (max deviation from mid: $100,000). Use bid/ask, never
   `mark`. See §1.1.
4. **[measured] Costs on a SPY 0-1DTE 16-delta condor: $4 of spread + $5.20 of commission
   against a $22 median credit — 42% of gross premium gone before any edge.** §1.2.

---

## 1. The data we already have: quality audit

`data/opt_eod/SPY_options.parquet` — 24,681,665 rows, 4,514 trading days,
2008-01-02 → 2025-12-12. All numbers below **[measured]** tonight.

### 1.1 Defects to filter before use

| Issue | Magnitude | Consequence if ignored |
|---|---|---|
| `bid == 0` | 1,758,686 rows (**7.1%**) | Engine will happily "sell" a contract for $0 |
| `ask == 0` | 11,572 rows | Free long options |
| `bid > ask` (crossed) | 2,083 rows | Negative spreads, phantom profit |
| `bid == ask` (locked) | 12,840 rows | Usually stale |
| **`mark` ≠ (bid+ask)/2** | **57.6% of rows**; max deviation **$100,000.49** | `mark` is unusable — do not touch it |

**The provider does no hygiene.** `options_portfolio_backtester/data/providers.py` has no
zero-bid filter, no crossed-quote filter, no staleness check — `apply_filter` only applies
*your* filter. You must add `schema.bid > 0` to every entry filter yourself. Given 7.1%
zero-bid rows this is not optional.

No calendar gaps: zero gaps > 5 calendar days across 18 years. Rows/day grows 2,038 (2008)
→ 9,749 (2025), which is real listing growth, not a coverage break.

### 1.2 Spread cost, measured — the number that kills most premium ideas

Relative spread (ask−bid)/mid on tradeable rows (bid>0), by DTE band:

| DTE band | n | median | p75 | p90 |
|---|---|---|---|---|
| 0-1 | 514,368 | 2.60% | 6.96% | 23.77% |
| 2-7 | 1,589,464 | 1.99% | 8.70% | 40.00% |
| 8-30 | 4,695,170 | 1.80% | 5.13% | 22.22% |
| 31-90 | 4,343,547 | 1.46% | 3.56% | 13.33% |
| 91-180 | 3,670,810 | 1.40% | 3.09% | 10.00% |

By delta, 0-7 DTE — note the far wing is where the cost lives:

| \|delta\| | median mid | median rel spread | median abs spread |
|---|---|---|---|
| 0.00-0.05 | $0.04 | **40.0%** | $0.01 |
| 0.05-0.15 | $0.29 | 4.65% | $0.01 |
| 0.15-0.25 | $0.76 | 2.20% | $0.02 |
| 0.25-0.35 | $1.31 | 1.55% | $0.02 |
| 0.45-0.55 | $2.78 | 1.06% | $0.03 |

**Full 4-leg condor round trip** (16-delta short / 5-delta long, built per day from the
real chain):

| Band | n condors | median width | credit at MID | credit CROSSING | round-trip spread | as % of mid credit |
|---|---|---|---|---|---|---|
| 0-1 DTE | 1,050 | $1 | $0.22 | $0.19 | **$0.04 ($4)** | **18%** |
| 7-10 DTE | 3,397 | $3 | $0.73 | $0.70 | $0.06 ($6) | 8% |
| 30-45 DTE | 3,787 | $5 | $1.37 | $1.31 | $0.09 ($9) | 7% |

Add commissions: 4 legs × 2 sides × $0.65 = **$5.20/condor**. So the 0-1 DTE condor pays
**$9.20 against a $22 median credit — 42% of gross premium**, before any edge. At 30-45 DTE
it is $14.20 against $137, or 10%. **If you test condors, the short-dated end is where cost
dominates, and any backtest filling at mid will overstate 0DTE results by roughly a fifth
of the credit per trade.**

Caveat on these being flattering: this is a single **closing** NBBO snapshot. SPY closing
quotes are among the tightest of the day. Intraday and especially at the open, spreads are
materially wider. Treat the table as a *floor* on cost.

### 1.3 Why this data cannot test 0DTE

DTE=0 rows exist (482,913, on 1,956 distinct dates) but a DTE=0 row is **the closing quote
on expiration day** — one snapshot, at 16:00, of a contract that is already expiring. You
cannot enter at 10:00 and exit at 15:00. Also note 0DTE dates per year: 4 (2008) → 71
(2016) → 250 (2023) → 252 (2024), which just tracks SPY's move to daily expirations in Nov
2022. **Any 0DTE intraday study requires intraday quotes we do not have** (§3).

### 1.4 Known upstream gaps (from `data/DATA_NOTICE.md`)

- QQQ chain begins **2011-03-23** — no GFC.
- IWM `underlying.parquet` ships `adjClose` **entirely NaN**.
- Provenance is **undocumented**. The upstream (`philippdubach/options-data`) deleted both
  its CDN and its GitHub repo in 2026; nobody knows who originally sourced these quotes or
  how they were snapped. The lambdaclass mirror is now the only surviving copy. Treat the
  data as unattributed — it is internally consistent and passes the sanity checks above,
  but it has no chain of custody, and no license (the notice asserts none and offers
  takedown on request).

---

## 2. Engine audit: `lambdaclass/options_portfolio_backtester`

MIT, 256 stars, 46 forks, default branch `master`, active (pushed 2026-07-28). Python +
a required Rust core (`rust/ob_core`) — there is no Python fallback path, so the Rust is
the engine. Audited at commit on `master`, 2026-08-06.

**Verdict: reuse the engine, do not trust the presets, and add a margin model yourself.**

### 2.1 What it gets right (better than most of this space)

- **Fills cross the spread by default.** `rust/ob_core/src/fill_model.rs`, `MarketAtBidAsk`
  is `#[default]`: buys fill at ask, sells at bid. Exits use
  `leg.direction.invert().price_column()`, so a long exits at bid and a short is bought
  back at ask. `MidPrice` exists but you have to ask for it. This is the correct default
  and most repos get it backwards.
- **The profit/loss threshold is sign-general and correct for credit structures.**
  `backtest.rs:1223`: `excess_return = (curr / entry + 1.0) * -entry.signum()`. Because
  exit cost carries the opposite sign from entry cost, this yields +0.5 for "captured half
  the credit" on a short condor *and* +0.5 for "up 50%" on a long put. Verified by hand on
  both signs. Rare to see done right.
- **Runtime invariants, armed during real runs.** Two bug classes are asserted every exit:
  *class A* (cash delta must equal realized P&L net commission, not gross proceeds — the
  original "free puts" bug) and *class B* (an unquoted contract's intrinsic fallback must
  be computed from the **unadjusted** close; using the dividend-adjusted close against raw
  strikes manufactured phantom intrinsic value). Both are real bugs they shipped, found,
  and now guard. See `CHANGELOG.md:119-260`.
- **A fill-rate diagnostic that catches data holes.** `engine.option_fill_rate` /
  `HedgeFillWarning` (`engine/engine.py:49`) warns when the entry filter cannot find a
  tradeable contract. This is how they discovered that 40-45% OTM SPX puts are *not listed*
  before ~2003 — a 46% miss rate with a contiguous 20-month hole straddling the dot-com
  decline (`research/spitznagel_spy/findings/DATA_COVERAGE.md`). Almost no retail repo has
  this, and its absence is how "deep OTM puts printed money" results get manufactured.
- **Honest published nulls.** Their own cross-underlying check
  (`findings/CROSS_UNDERLYING.md`) concludes the tail-hedge result is **window-driven, not
  underlying-driven**: +6.09pp excess on SPY 2008-2024, but **−2.19pp on SPY 2011-2024**,
  −0.37pp on QQQ, and no drawdown improvement on either QQQ (−35.1→−36.3) or IWM
  (−54.9→−55.4). They also document a **+12pp false discovery** they made and retracted —
  an expanding-median threshold on a mislabeled `tobin_q` column that resolved to "the year
  is 2007-2009," i.e. hedge during the one in-sample crash. That is the same conditional-
  selection artefact `FINDINGS.md` keeps finding, independently discovered.

### 2.2 Look-ahead posture

**Same-bar close fill, undocumented and untested.** Entries filter the day's chain
(`entries.rs`) and fill at that same day's bid/ask; exits evaluate the day's quote and fill
at it. With EOD data this means you observe the closing NBBO and simultaneously trade at
it, which is not achievable. For a monthly/bi-monthly rebalance this is a small
idealization; for a daily-exit rule it is not.

Two concrete consequences:

- **Threshold exits are evaluated once a day, at the close.** A "close at 50% profit" rule
  that would have triggered intraday is invisible. For condor management-rule sweeps —
  exactly the thing people want to test — EOD evaluation systematically misses both the
  profit-target touches and the stop touches, and the two do not cancel.
- **There are no look-ahead tests.** Compare `hadan-aslan/quant-edge` (§`RESEARCH_SWING_REPOS.md`
  A1), which re-runs the pipeline on truncated prefixes and demands bit-identical history.
  Nothing equivalent exists here. The ~1,300-test suite tests other things well; it does not
  test this.

### 2.3 **The multi-leg presets are stubs — do not use them**

`options_portfolio_backtester/strategy/presets.py:128`. `iron_condor()` takes
`short_delta_call=0.30`, `short_delta_put=-0.30`, `wing_width=5.0` — and **the function
body never references any of the three**. Verified by extracting the body and grepping: the
only hits are the signature lines. All four legs get the identical filter:

```python
(schema.underlying == underlying) & (schema.dte >= dte_range[0]) & (schema.dte <= dte_range[1])
```

Nothing distinguishes the short call from the long call. No strike ordering, no wing width,
no delta targeting. The docstring claims "a simplified version using strike offsets"; there
are no strike offsets in the code. **Calling `iron_condor()` produces four arbitrary
same-expiry contracts, and it will not error.**

`butterfly()` (line 286) has the same disease: the middle (2x short) leg has no strike
constraint and no `entry_sort`, while the wings sort to the *lowest* and *highest* strike in
the whole DTE band. The result is the widest available structure, not a butterfly. The
docstring says the 2x middle quantity is "handled by the sizer"; nothing in the sizer does
this.

**The tests do not catch this because they only assert leg count, direction and type.**
`tests/strategy/test_presets.py:59-80` checks `len(s.legs) == 4` and that legs 0/2 are SELL
and 1/3 are BUY. No test ever asserts a strike relationship, and no test runs a condor
against data. The large test suite gives false assurance here specifically.

Only the single-leg path (`deep_otm_put`, `near_atm_put_protection`) is exercised by the
published-article reproductions, and only that path should be trusted as-shipped.

**And the leg-combination machinery underneath makes it worse.** In `backtest.rs:1448-1560`,
each leg's candidates are computed *independently* (`compute_leg_entries` per leg), then:

- the candidate lists are truncated to `min_len` and **zipped by positional row index**
  (`for row in 0..min_len` summing `cost` across legs) — there is **no join on expiration**
  and no strike-relationship constraint anywhere;
- then `sel.select_index(leg_df)` is called **per leg, independently**, so each leg picks
  its own row from its own frame with no cross-leg coordination.

Two consequences:

1. **In general**, a multi-leg position is not guaranteed to share an expiration across
   legs. Nothing enforces it. You can be handed a "vertical spread" whose legs expire in
   different months.
2. **For the shipped `iron_condor()` specifically, the structure is degenerate.** All four
   legs have identical filters and no per-leg selector, so all four receive *identical*
   candidate frames, and the default `FirstMatch` selector returns index 0 for each. The
   short call and the long call are therefore **the same contract**; likewise the puts.
   Entry cost = (ask − bid) on the call + (ask − bid) on the put — **you pay exactly the
   bid-ask spread for a position with no payoff structure at all**, plus four commissions,
   and lose it deterministically. No test catches this: grepping the suite for any
   assertion that legs share an expiration or are distinct contracts returns nothing.

Treat every multi-leg preset in this repo as non-functional until you write your own leg
constructor with an explicit expiration join and enforced strike ordering.

### 2.4 **No options margin model — credit strategies are silently over-levered**

`options_portfolio_backtester/execution/sizer.py`, `CapitalBased.size`:

```python
return int(available_capital // abs(cost_per_contract))
```

For a credit structure `cost_per_contract` is the **net credit**. A $100k allocation against
a $1.50 credit sizes 666 condors. If the wings are 5 wide, max loss is $3.50/contract =
**$233k of risk on $100k of capital**. Nothing anywhere checks this: grepping
`margin|buying power|max_loss|collateral` across the options engine returns only a `Margin`
algo that belongs to the *stock-only* `AlgoPipelineBacktester`, plus CSS. The options path
has no buying-power concept at all.

Consequence: **any credit-strategy result from this engine as-shipped is meaningless until
you replace the sizer** with one that divides by max loss (wing width − credit) × 100.

### 2.5 Other gaps

- **No early assignment / exercise modelling whatsoever.** Grepping
  `assign|exercis` across the whole engine returns only Rust's `AddAssign` trait. SPY, QQQ
  and IWM options are **American and pay dividends** — short ITM calls get assigned before
  ex-div, which is the single most common way a real short-call position deviates from its
  backtest. The engine cannot represent this. It is a non-issue for SPX/XSP (European,
  cash-settled), which is an argument for doing index work rather than ETF work here.
- **No expiration auto-close.** There is no `dte <= 0` force-close anywhere in
  `backtest.rs`. Positions exit only via your `exit_filter`, a threshold, or a rebalance
  liquidation. Omit the exit filter and the contract simply vanishes from the chain and gets
  marked at intrinsic indefinitely.
- **Worthless options are NOT silently dropped — this one it gets right.** A common killer
  in this space is filtering the exit chain by `bid > 0`, which deletes expiring-worthless
  contracts and therefore deletes exactly the losing trades, manufacturing a high win rate.
  lambdaclass does not do this: a position whose contract is absent from the day's chain is
  marked at **intrinsic** (`backtest.rs:1281`), i.e. $0 for an OTM expiry, and the loss is
  realised. Losers are retained. (This is why the `bid > 0` hygiene filter of §1.1 belongs on
  *entry* filters only — do not put it on exits, or you reintroduce the bug.)
- **The intrinsic fallback fires on *any* missing quote, not just at expiry.**
  `backtest.rs:1281` — if a contract isn't in today's chain, it's marked at intrinsic from
  the unadjusted spot. That is right at expiration and wrong everywhere else: an illiquid
  strike that drops out of the file for a day gets marked at intrinsic (i.e. $0 for OTM),
  with zero spread cost. The class-B invariant checks the *arithmetic* of this fallback, not
  whether the fallback should have applied. Combined with the 7.1% zero-bid rows in §1.1,
  this is the most likely source of a silently optimistic result.
- **Commission model omits fees.** `cost_model.rs` charges per-contract commission only —
  no exchange fees, no ORF, no SEC/TAF. On SPX/index products these are material
  (roughly $0.15-0.60/contract depending on venue and product).
- **README inaccuracy:** it advertises `IronCondor`, `CoveredCall`, `CashSecuredPut`,
  `Collar`, `Butterfly` as classes; they are functions (`iron_condor`, `butterfly`, …).
  Only `Strangle` is a class. Minor, but it means the README was not run.

### 2.6 Reuse recommendation

Reuse the Rust core, the fill/cost models, the invariants and the fill-rate diagnostic.
Before any credit-strategy result is believable, you must supply: (a) a real condor/butterfly
constructor with delta-targeted strikes and enforced wing ordering, (b) a max-loss-based
sizer, (c) a `bid > 0` hygiene filter on every entry, (d) fees on top of commission. Items
(a) and (b) are the difference between a number and a fantasy.

---

## 2b. The other serious engine: `goldspanlabs/optopsy`

https://github.com/goldspanlabs/optopsy — 1,435 stars, pushed 2026-06-30, MIT. The
most-used library in this space, and the natural alternative to lambdaclass.

**Read of the source, not the README:**

- **Requires real bid/ask.** `op.csv_data(...)` takes explicit `bid=` / `ask=` column
  indices; `evaluated_cols` carries `bid_entry, ask_entry, bid_exit, ask_exit`. There is no
  modelled-price path. Good.
- **Default slippage crosses the full spread.** `optopsy/pricing.py::_calculate_fill_price`
  with the library default `slippage="spread"` sets `ratio = 1.0`, giving
  `mid + half_spread` for longs and `mid − half_spread` for shorts — i.e. buy at ask, sell
  at bid. A `"mid"` mode exists and is *not* the default. Also has `"liquidity"` (widens
  the fill for low-volume contracts) and `"per_leg"` (adds a penalty per extra leg, which
  is the right instinct for 4-leg structures). This is the most thoughtful slippage
  treatment I found in any public options repo.
- **Real commission model.** `_calculate_commission` supports per-contract, base fee and
  minimum fee.
- **Proper multi-leg definitions.** Unlike lambdaclass, optopsy has genuine
  quadruple-leg iron condor / iron butterfly definitions with strike-ordering rules
  enforced in `core.py`. If you want condors, this is the library that actually builds one.

**Limitations:**

- It is a **trade-statistics engine, not a portfolio engine**. No capital, no position
  sizing, no margin, no compounding — it returns per-trade P&L distributions. So it has the
  same margin blind spot as lambdaclass, just more honestly (it never claims to size).
- **Daily quote-date granularity** — entry and exit are keyed on `quote_date_entry` /
  `quote_date_exit`. With EOD data it cannot test intraday 0DTE.
- **No assignment modelling**, and the README says so explicitly: results "do not account
  for … assignment risk."
- Its bundled data path (`optopsy-data download`) uses **EODHD**, which is a paid,
  EOD-only options source.

**Recommendation: use optopsy for condor/butterfly structure research on our EOD chains,
and lambdaclass for capital-path/portfolio-overlay questions.** optopsy's leg construction
is correct where lambdaclass's is a stub; lambdaclass's accounting and invariants are real
where optopsy has none.

---

## 3. Other sources of real option chains

Current holdings: SPY/QQQ/IWM EOD 2008-2025, SPXW intraday 2016-2024. The gap is
**single-stock chains**.

### 3.1 **DoltHub `post-no-preference/options` — the single-stock answer. Free.**

https://www.dolthub.com/repositories/post-no-preference/options

All facts below **[measured]** tonight against the live SQL endpoint, not read off a page.

| Property | Value |
|---|---|
| Universe | **2,321 distinct tickers** (US single stocks + ETFs) |
| Date range | **2019-02-09 → 2026-08-05** — i.e. still updating **daily** |
| Bid / ask | **Yes, both.** Real quotes, not last/mark |
| Greeks | **Yes** — `delta, gamma, theta, vega, rho` |
| IV | Yes (`vol`) |
| Cost | **Free**, no registration |
| Tables | `option_chain`, `volatility_history` |

Schema of `option_chain`:
`date, act_symbol, expiration, strike, call_put, bid, ask, vol, delta, gamma, theta, vega, rho`

Sample row (AAPL, 2026-08-05):
`{date: 2026-08-05, act_symbol: AAPL, expiration: 2026-08-19, strike: 220.00, call_put: Call, bid: 89.20, ask: 92.90, vol: 1.0310, delta: 0.9641, ...}`

**The one big limitation, verified independently.** For AAPL on 2026-08-05 the database
carries only **three expirations** — 2026-08-19, 2026-09-04, 2026-09-18 (14 / 30 / 44 DTE) —
with **54, 48, 48 rows** each and strikes spanning **220-405** against a spot near 309
(roughly ±30%). This confirms the warning in lambdaclass's `DATA_NOTICE.md` ("~3 near-dated
expirations, DTE ≤ ~60, strikes within ±20% of spot"). So:

- **Usable for:** single-stock swing trades out to ~6 weeks, earnings plays, near-the-money
  verticals, covered calls, cash-secured puts, short strangles/condors at normal widths.
- **Not usable for:** LEAPS, anything past ~45-60 DTE, deep-OTM tail structures, far wings.

**Second quality flag: the greeks and IV are model-derived and unstable on wide-spread
contracts.** In the sample above, adjacent deep-ITM AAPL calls carry IVs of **103.1%** (220
strike) and **53.4%** (235 strike). That is an IV solver choking on a wide ITM bid/ask, not a
real vol surface. **Recompute greeks yourself from bid/ask and a spot series**; do not filter
or select on the shipped `vol`/`delta` for ITM contracts. Near-the-money values look sane.

**Survivorship:** the table is append-only by date, so a ticker that delisted in 2021 keeps
its 2019-2021 rows. That is the right property. But the *universe* is whatever the collector
tracked on each date, which is undocumented — do not assume a clean point-in-time universe.

**How to pull it — two routes:**

1. **SQL endpoint, no install** (best for a subset — this is what I used):
   ```
   curl -s --get "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master" \
        --data-urlencode "q=select * from option_chain where date='2026-08-05' and act_symbol='AAPL'"
   ```
   Note the branch is **`master`**, not `main` (`main` returns "branch not found"). Queries
   filtered by `date` **and** `act_symbol` return instantly; unfiltered aggregations
   (`count(distinct ...)`, `min(date)` over the whole table) hit a server-side deadline and
   return an empty row set with `context deadline exceeded`. Page your extraction by date.

2. **Full clone** (`brew install dolt`, not currently installed here):
   ```
   dolt clone post-no-preference/options && cd options && dolt sql
   ```
   Size not published and I could not measure it. Order-of-magnitude estimate from the
   measured row shape: ~150 rows/symbol/day × 2,321 symbols × ~1,880 trading days ≈ **6×10^8
   rows**, so expect **tens of GB**. Given that, prefer route 1 and extract only the tickers
   and dates you need.

### 3.2 OptionsDX — the SPX/single-stock paid-but-cheap route

https://www.optionsdx.com/?post_type=product — free tier after registration, paid tiers
**$0-$50** per product. Products offered: **SPY, SPX, VIX, QQQ, TSLA, AAPL, NVDA, UVXY, SLV**,
plus BTC (Deribit). The site advertises "historical **intraday** quotes … pre-calculated
greeks, IV, and underlying price at up to **minutely** intervals."

- Covers **SPX** (which the free ETF set does not) and a handful of single stocks.
- Coverage starts **2010** — no GFC. lambdaclass flag this explicitly as why they could not
  reproduce their 2008-2009 results from this source.
- Per-user account, so it cannot be fetched headlessly; lambdaclass ships
  `scripts/convert_optionsdx.py` to convert its wide CSV (`C_BID, C_ASK, P_BID, P_ASK, …`)
  into long format, which is a ready-made adapter if you buy it.
- Only ~5 single-stock names, so it does **not** replace DoltHub for breadth.

### 3.3 DeltaNeutral / historicaloptiondata.com — the deep-history SPX route

This is what lambdaclass actually used for their SPX work: `research/spitznagel_spy/experiments/spx_sweep.py`
reads "purchased **DeltaNeutral ALLSPX**, local-only … Licensed — never committed or
redistributed," covering **SPX 1996-2025**. So the deepest SPX history in this ecosystem is a
paid one-time purchase, and it is the only source seen here that predates 2008. Price not
verified in this session.

### 3.4 Not verified this session

Vendor pricing for ThetaData, Polygon.io options, CBOE DataShop, ORATS and Databento was
delegated to background agents that died with the session reset. Given §1.3, the only reason
to revisit these is intraday breadth beyond the SPXW set already held — which is a narrower
need than the single-stock gap that §3.1 now closes for free.

---

## 4. Directional long-option evidence — **incomplete**

This section did not get finished; the two background sweeps assigned to it produced nothing
before the session reset, and DuckDuckGo began serving CAPTCHAs. Recording only what is
actually grounded, so nothing here has to be taken on trust:

- **Option Momentum** — Heston, Jones, Khorram, Li & Mo, *Journal of Finance* 78(6), 2023,
  DOI `10.1111/jofi.13279`; SSRN 4113680; preprint at
  `faculty.marshall.usc.edu/Christopher-Jones/pdf/opmom.pdf`. Options with strong past
  performance keep outperforming over **6-to-36 month** horizons, with no long-run reversal,
  and the authors state trading costs are unrelated to the magnitude of momentum profits.
  **Caveat before anyone gets excited:** this is a cross-sectional, multi-month, largely
  delta-hedged option-return anomaly. It is *not* evidence for a directional long-call swing
  trade at a 2-day-to-8-week horizon, which is the question actually asked.

**Not verified, and therefore not asserted:** the specific numbers in Coval & Shumway (2001),
Bondarenko, Goyal & Saretto (2009), and Broadie-Chernov-Johannes. The prior going in is that
buying options is a negative-expected-return activity gross of costs, and §1.2 shows the cost
layer is 7-42% of premium depending on tenor — but that prior should be checked against the
actual papers before it is used to kill or justify anything.

**Next step for this section:** it is now cheap to test directly rather than read about it.
§3.1 gives free single-stock chains with bid/ask from 2019, which is enough to run our own
long-call swing study on real quotes — and per §1.2 the honest version must cross the spread
on entry *and* exit.

---

## 5. What to do with this

1. **Pull DoltHub single-stock chains** (§3.1), paging by date via the SQL endpoint. This
   closes the largest data gap in the project, for free, today.
2. **Do not use lambdaclass's multi-leg presets** (§2.3). If condors are wanted, use optopsy
   for structure (§2b) or write the leg constructor. If lambdaclass is used for anything
   with a short leg, replace `CapitalBased` with a max-loss sizer first (§2.4).
3. **Filter `bid > 0` on every entry, and never read the `mark` column** (§1.1).
4. **Budget 7-10% of credit for 30-45 DTE and ~42% for 0-1 DTE** as the cost hurdle before
   evaluating any premium-selling result (§1.2).
5. Section 4 is open.
