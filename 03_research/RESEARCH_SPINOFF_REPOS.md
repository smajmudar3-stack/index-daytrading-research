# Corporate Spinoff & Event-Driven Equity — Data, Repos, Mechanics

Research sweep, 2026-08-14. Scope: public GitHub, open-source projects, and above all **data sources**
for corporate spinoff and event-driven equity trading.

**Read this first — the two findings that matter:**

1. **DATA (solved).** SEC EDGAR Form 10-12B, enumerated via the *quarterly form index* (not full-text
   search), is a free, scriptable, **survivorship-bias-free-by-construction** registry of US spinoffs
   back to 1994. I built it and ran it: **741 unique SpinCo registrations, 1994-2026**, in
   `data/spinoffs/`. That is 3-7x the sample of every published attempt I found. A live forward
   calendar falls out of the same pipeline.
2. **EDGE (probably dead).** Two independent, pre-registered studies already ran the spinoff-drift
   test on different data vendors and different benchmarks. Both killed it. One found the small-cap
   spinco tail *underperforms* a size-matched benchmark by ~22% in a 2020-24 holdout. Details in
   §5. Build the dataset if you want to settle it yourself on the 1994-2015 sample nobody has
   touched — but the prior is bad, and worse than Greenblatt-lore suggests.

---

## 1. PRIORITY 1 — DATA

### 1.1 The answer: EDGAR Form 10-12B via the quarterly form index

**Why this is the right source.** Form 10-12B is the registration statement a SpinCo files to register
its shares under Exchange Act §12(b) before being distributed to parent shareholders. Essentially every
US spinoff that will list on an exchange files one. The EDGAR **quarterly form index** enumerates every
filing ever made, of every form type, regardless of what happened to the filer afterwards.

That property is the whole game. A curated "list of spinoffs" is assembled by looking backwards from
today, so it structurally over-represents SpinCos that still exist. The form index was written down
contemporaneously and never revised. **Companies that were acquired, went bankrupt, or delisted are
still in it, at full weight.** Lucent, Payless ShoeSource, and Promus Hotel are all in my output with
`still_listed = False` — that is the tail you need, and it is present.

**The critical detail everyone else missed.** EDGAR full-text search (`efts.sec.gov`) only covers
**2001+**, which is why the published attempts start at 2015 or 2001. Form-type enumeration via
`/Archives/edgar/full-index/` goes back to **1993Q1**. You do not need FTS to enumerate 10-12B filings —
you need the form index, and it roughly triples the sample and covers the pre-2000 era where the
anomaly was originally documented.

**Working implementation:** `scripts/spinoff_edgar_harvest.py` (built and run for this report).

```bash
# Stage 1 -- enumerate every 10-12B / 10-12B/A filing, 1994-present. ~12 min first run,
# seconds thereafter (caches the matched lines per quarter). No API key.
venv/bin/python scripts/spinoff_edgar_harvest.py index

# Stage 2 -- recover ticker / exchange / distribution date / ratio by parsing the
# Information Statement, plus current listing status from data.sec.gov.
venv/bin/python scripts/spinoff_edgar_harvest.py enrich

# Stage 3 -- forward calendar of announced-but-not-completed spinoffs.
venv/bin/python scripts/spinoff_edgar_harvest.py forward
```

The one-liner, if you want to verify the premise before trusting my code:

```bash
curl -s -H "User-Agent: your.email@example.com" \
  "https://www.sec.gov/Archives/edgar/full-index/1996/QTR1/form.idx" | grep '^10-12B'
# -> LUCENT TECHNOLOGIES INC, PAYLESS SHOESOURCE INC, TUPPERWARE CORP, VIVRA INC, ...
```

**Output produced, in `data/spinoffs/`:**

| File | Rows | Contents |
|---|---|---|
| `edgar_10_12b_filings.csv` | 2,546 | Every 10-12B and 10-12B/A filing, 1994-2026 |
| `spinco_registrations.csv` | **741** | One row per SpinCo: CIK, name, registration date, amendment count |
| `spinoffs_enriched.csv` | 741 | + ticker, exchange, distribution date, ratio, current listing status |
| `forward_calendar.csv` | 19 | Live pipeline of registered-but-not-yet-completed spinoffs |
| `stockanalysis_spinoffs.json` | 565 | Cross-check list, ex-date keyed (see §1.3) |
| `ssi_completed.json` | 173 | Cross-check list with **announcement dates** (see §1.3) |

Registrations per year (original 10-12B, deduped to first per CIK):

```
1994   2   1999  26   2004  11   2009  21   2014  37   2019  36   2024  17
1995   4   2000  27   2005  15   2010  18   2015  44   2020  16   2025   8
1996  36   2001  21   2006  18   2011  26   2016  31   2021  20   2026  15
1997  33   2002  18   2007  32   2012  20   2017  10   2022  20
1998  20   2003  26   2008  38   2013  30   2018  25   2023  19
```

1994-95 are thin because EDGAR electronic filing was only phased in over 1993-1996. **Treat 1996 as
the real start of complete coverage.**

### 1.2 Honest limitations of the EDGAR spine

I am flagging these because they are the things that would quietly corrupt a backtest:

- **Registration date ≠ announcement date.** The 10-12B is filed *after* the board announces, typically
  by 2-6 months. It is a hard, public, timestamped, survivorship-free lower bound on "the market knew" —
  but it is not the announcement. If your signal is announcement-driven, join to
  `ssi_completed.json` (§1.3) for true announcement dates, 2017+.
- **Registration date ≠ ex-distribution date.** Median lag from 10-12B to distribution is on the order
  of 2-4 months and varies widely. You must recover the ex-date separately.
- **10-12B is not 100% of spinoffs.** Some are registered on Form S-1 or by foreign private issuers on
  Form 20-F. My year-by-year comparison against stockanalysis.com (§1.3) shows EDGAR finds *more*
  events pre-2012 and *fewer* post-2019 — the two sources are complementary, not redundant. Use both.
- **Not every 10-12B completes.** Some registrations are withdrawn (Hamilton Beach filed in 2007; that
  spinoff was abandoned and refiled a decade later). A withdrawn registration has no ex-date and must be
  dropped — but drop it on evidence, not by assuming.
- **Ticker recovery from 1990s filings is weak.** Modern filings state the symbol in a clean quoted
  phrase and regex cleanly. Pre-1997 plain-text filings often present it as a dot-leader table row
  (`NYSE Symbol.........`) that survives no whitespace normalisation. Payless → `PSS` works;
  Lucent → `LU` does not. **This is the weakest link in the pipeline** and the place to spend effort if
  you take this further.
- **10-12B captures spinoffs, but the form is also used for other §12(b) registrations.** Expect some
  non-spinoff contamination and filter on the Information Statement text.

### 1.3 Complementary sources (use alongside, not instead)

**stockanalysis.com — best free ex-date-keyed list.** 565 events, 1998-2026, free.
Fields: ex-distribution date, parent ticker, spinco ticker, both names. **No ratio, no announcement
date.** Survivorship verified empirically: 246 of 565 spincos (44%) have no live quote page — they are
acquired, delisted, or bankrupt. `SPWRQ`, `FTRCQ`, `HSNI`, `LPS`, `ILG` are all present. Good.

```bash
curl -A "Mozilla/5.0" "https://stockanalysis.com/actions/spinoffs/2008/__data.json"
```
Payload is SvelteKit devalue-encoded — object values are *indices into the same flat array*, so you
must deref recursively. Parser: `scripts/sa_spinoffs.py`.

> **Trap — entity renaming.** Tickers and names are the *current* identity of the CIK lineage, not the
> identity at distribution. The 2008 rows read `WBD→ASCMA` (actually Discovery Holding) and
> `MTCH→TKTM/TREE/ILG/HSNI` (actually IAC/InterActiveCorp). Map through a point-in-time ticker table
> before joining to prices or you will silently mis-join and never notice.

**stockspinoffinvesting.com — the only free ANNOUNCEMENT-DATE source.** 173 completed spinoffs,
2017-2026, free. Fields include **announcement date and first trading day** — i.e. the actual tradeable
window. Survivorship clean (36 of 173 show `#N/A` current price = acquired/delisted; keeps disasters
like VNE −93.4% and KLXE −94.0% at full weight). Server-rendered HTML table, no JS needed:

```bash
curl -sL -A "Mozilla/5.0" "https://stockspinoffinvesting.com/completed/"
```
Announce→completion lags run long: ADIG 2025-06-30 → 2026-08-04 (13 months). Its `/upcoming/` page is a
second forward calendar covering board-announced deals that have no Form 10 yet (JNJ, CMCSA, MCK) —
genuinely complementary to EDGAR, which fires earlier on small caps but later on mega-cap intentions.
**Caveat:** curated by one person, so it under-samples obscure micro-caps. That is inclusion bias, not
survivorship bias, but it still distorts a universe.

**SHARADAR ACTIONS (Nasdaq Data Link) — the only cheap structured source with the RATIO.**
$29/mo bundle (fundamentals-only tier from $19/mo). Coverage 1998→present, <1 day lag.
Fields: `date, action, ticker, name, value, contraticker, contraname` where for `action='spinoff'`
the `value` **is the distribution ratio** and `contraticker` is the spinco. Verified correct against
known deals: `GE→GEV = 0.25`, `MMM→SOLV = 0.25`, `IBM→KD = 0.2`, `MRK→OGN = 0.1`, `PFE→VTRS = 0.12408`.
Vendor states coverage includes delisted securities; empirically confirmed (returns bankrupt `FTRCQ`,
`IDARQ`). **No announcement date — ex-date only.**

```bash
# Free probe WITHOUT a key returns the Dow-30 subset -- validate your parser before paying:
curl "https://data.nasdaq.com/api/v3/datatables/SHARADAR/ACTIONS.json?action=spinoff&qopts.per_page=10000&api_key=INVALID"
```

**CRSP — the gold standard, and the exact recipe if you ever get access.** `DISTCD` is four digits:
(1) event type, (2) payment method, (3) event descriptor, (4) tax status. True spinoffs are
**`3762`** (taxable as dividend), **`3763`** (non-taxable — the classic §355 spinoff, your main
population), **`3764`** (return of capital). `ACPERM` links parent PERMNO → spinco PERMNO.

```sql
SELECT a.permno, a.distcd, a.exdt, a.acperm FROM crsp.msedist AS a
-- strict: WHERE distcd BETWEEN 3762 AND 3764
-- loose:  WHERE acperm > 999
```
**Do not use `5523`** — that is a plain non-taxable stock split, not a spinoff. Also note the Open Source
Asset Pricing project's own comment: the strict `3762-3764` filter "results in a large share of months
with no spinoffs," so they use `acperm > 999` instead. CRSP's digit-3 coding is incomplete.

### 1.4 Sources checked and rejected

| Source | Verdict |
|---|---|
| **yfinance / Yahoo** | **No spinoff data.** `history.py` requests `events="div,splits,capitalGains"` — three types, no spinoff. Yahoo folds spinoffs into the price adjustment factor silently and never labels them. Unusable for discovery. |
| **Polygon.io / massive.com** | Ticker Events endpoint supports **symbol changes only**. No distribution endpoint. |
| **EODHD, Alpha Vantage** | Splits and dividends only. |
| **Tiingo** | `splitFactor` adjusts for distributions but never labels them — detectable as an unexplained factor, not identifiable. |
| **Financial Modeling Prep** | Unprobeable without paying (uniform 401). Public docs list only split/dividend calendars. Low expected value. |
| **DoltHub** | **No spinoff data.** `post-no-preference/stocks` has exactly four tables: `dividend`, `ohlcv`, `split`, `symbol`. `dolthub/corporate-actions` does not exist. Your existing Dolt data does not help here. |
| **Wikipedia** | Prose examples only, no tickers/dates/ratios, and severely survivorship-biased — it names famous survivors. |
| **spinoffresearch.com** | Domain is dead (`ENOTFOUND`). |
| **Academic replication packages** | Dead end, informatively so. CMW (1993), Desai-Jain (1999), McConnell-Ovtchinnikov (2004) all pre-date journal data-availability mandates. **Open Source Asset Pricing carries a `Spinoff` signal credited to CMW 1993 and grades its reproduction quality `4_lack_data` — their worst category.** If the OSAP team could not source it, it is not public. |
| **Kaggle** | Could not determine (JS-rendered search, API needs auth). Prior is low; no well-known spinoff dataset exists there. Settle with `kaggle datasets list -s spinoff` if you have credentials. |

### 1.5 Recommended build

1. **Spine (free):** `spinoff_edgar_harvest.py index` → 741 survivorship-free registrations, 1994-2026.
2. **Ex-dates + tickers (free):** join stockanalysis.com's 565 events; use EDGAR CIK→ticker for the rest.
3. **Announcement dates (free):** join stockspinoffinvesting.com `/completed/` for 2017+. Pre-2017,
   use the 10-12B filing date as an explicit, documented proxy — and never pretend it is the announcement.
4. **Ratios ($29/mo, optional):** SHARADAR ACTIONS. Free alternative: regex the Information Statements.
5. **Forward calendar (free, poll daily):** `spinoff_edgar_harvest.py forward`, diffed against completed.
   Cross-check stockspinoffinvesting `/upcoming/`.

**Survivorship summary: you are in unusually good shape.** The EDGAR spine is bias-free by construction,
and the three curated cross-checks all independently retain delisted spincos (verified empirically, not
taken from marketing copy). The real threats to your backtest are **entity renaming** in the
stockanalysis data and **inclusion bias** in the curated newsletter — not survivorship.

### 1.6 Live forward calendar (as of 2026-08-14)

Straight from the pipeline. `MSGS Spinco` filed **today**.

| CIK | Entity | Form | Filed | Parent |
|---|---|---|---|---|
| 2132873 | MSGS Spinco, Inc. | 10-12B | 2026-08-14 | Madison Square Garden Sports |
| 2128626 | Vylor Inc. | 10-12B/A | 2026-08-14 | Corteva |
| 2089271 | Honeywell Aerospace (HONA) | 10-12B/A | 2026-06-08 | Honeywell |
| 2105139 | ADI Global Distribution (ADIG) | 10-12B/A | 2026-06-04 | Honeywell |
| 2088281 | Midera Food Processing (MFP) | 10-12B/A | 2026-05-27 | — |
| 2090312 | Mobility Global Inc. | 10-12B | 2026-05-07 | — |
| 2083632 | Octave Intelligence plc (OCTV) | 10-12B/A | 2026-04-27 | — |
| 2082247 | FedEx Freight Holding (FDXF) | 10-12B/A | 2026-04-10 | FedEx |
| 2104052 | Enviri II Corp | 10-12B | 2026-03-20 | Enviri |
| 2078008 | Versigent Ltd | 10-12B/A | 2026-03-06 | — |
| 2091349 | First Tracks Biotherapeutics | 10-12B | 2026-03-03 | — |
| 2093101 | Atrium Therapeutics | 10-12B | 2025-12-10 | — |
| 2067876 | Versant Media Group | 10-12B | 2025-09-18 | Comcast |
| 2064953 | Solstice Advanced Materials | 10-12B | 2025-08-21 | Honeywell |

Board-announced but no Form 10 yet (from stockspinoffinvesting `/upcoming/`): MDT (2026 Q3),
CTVA (2026 Q4), KBR, FLEX, GPC (2027 Q1), MCK, CMCSA (2027 Q2), JNJ, TXT (2027 Q3), LBTYA, DINO, ABF.

---

## 2. PRIORITY 2 — REPOS

**Bottom line: there is no usable spinoff *strategy* code on GitHub.** There is excellent EDGAR
plumbing (one repo), and — the genuinely valuable find — two pre-registered studies that already ran
the test and killed it.

### 2.1 The two studies that already ran this

**`JonathanBeck1/falsification-campaign`** — 0 stars, last push 2026-06-18.
Test T42 is spinoff post-event drift. Signal, read from `src/trader/catalysts/spinoff_drift.py`:
universe = distinct Form 10-12B filers 2015-2025 via EDGAR FTS, deduped to earliest filing per CIK;
`t0` = first yfinance trading day; primary window CAR[t0+1, t0+21], market-adjusted with **beta forced
to 1**. Data: EDGAR FTS + yfinance (free). Costs: 20 bps round-trip hardcoded, plus a 2× stress test.
Train/test: pre-registered IS ≤2019 / OOS ≥2020.

Result: N=104. Primary gross CAR **−0.07%**, after-cost −0.27%, **t = −0.03**, win rate 52%. Signs
differ IS vs OOS, both zero. Dropping top-5 contributors makes it worse. **KILL.**

*Good:* pre-registration written before data; `t0+1` entry so cohort membership uses no return inside
the measurement window; placebo tests both same-name and pooled.
*Red flags the author did not catch:* the runner extracts tickers by regex from EDGAR's
`display_names` — the **current** SEC ticker mapping — then filters `if tk`. **Delisted spincos lose that
mapping and are silently dropped at universe construction**, so the "survivorship-safe by construction"
claim is wrong. Pagination also hard-stops at 400/year. N=104 is roughly a 25-30% sample skewed to
survivors. (Bias runs *toward* positive, so the null survives it.)

**`deaki682/pantheon`** — 0 stars, last push 2026-08-14, active.
Methodologically stronger on data: **Sharadar SEP** (paid, retains delisted) with point-in-time ticker
resolution, and a **size-matched small/micro equal-weight benchmark built from the same panel** rather
than SPY — the right control. Explicit delist handling: series ending mid-hold exits at last print and
is kept. IS 2015-19 / holdout 2020-24, 2× costs.

Result: N=227 US spinoffs, 200 priceable.

| | 63d | 126d | 252d |
|---|---|---|---|
| Full set | −1.97% | −1.59% | +1.55% |
| **Small tail** | **−6.81%** | **−9.29%** | **−9.33%** |
| IS 2015-19 | +4.07% | +1.75% | +0.12% |
| **Holdout 2020-24** | **−22.1%** | **−24.8%** | **−22.6%** |

t-stats −4.4 to −2.1 in holdout. **Refuted** — spinoffs *underperform* a size-matched benchmark.
*Fatal red flag:* the 227-event list is **not reproducible** — loaded from an agent scratchpad path
outside the repo and never committed, so it cannot be audited for recall gaps or hallucinated tickers.
Also the −22% holdout magnitude is large enough to suspect the EW small/micro benchmark is itself
distorted by the 2020-21 microcap melt-up.

**Taken together:** two independent designs, different vendors (yfinance vs Sharadar), different
benchmarks (SPY vs size-matched), different universes — both land on "no tradable spinoff drift, and the
small-cap tail is actively bad." **Neither tested pre-2015. Neither tested the parent.** Those are the
two unexplored angles, and the 741-row EDGAR spine in §1 is exactly what you need for the first.

### 2.2 Infrastructure worth adopting

**`dgunning/edgartools`** — **2,586 stars**, 458 forks, pushed daily, MIT. The only EDGAR library worth
using. Verified from source, not README: `edgar/search/efts.py` is a real full-text-search wrapper
returning relevance score, file type, **8-K item numbers**, SIC, state, with client-side filter
chaining. `10-12B` and `10-12B/A` are first-class form types in `edgar/entity/constants.py`. Full 8-K
data object gives `eight_k.items` → `['Item 2.02', ...]` and `eight_k['2.02']` for item text — the best
free 8-K item parser available. Supports `get_filings(range(1994, 2027), form="10-12B")`, i.e. the
form-index path from §1.1.

| Repo | Stars | Last push | Note |
|---|---|---|---|
| `john-friedman/datamule-python` | 552 | 2026-08-14 | Very active; bulk SEC data. Real alternative for bulk work. |
| `sec-edgar/sec-edgar` | 1,411 | 2025-12-09 | Downloader only, no parsing. Maintenance slowing. Apache-2.0. |
| `jadchaar/sec-edgar-downloader` | 714 | 2026-06-22 | Simplest downloader, `10-12B` supported. No parsing. MIT. |
| `alphanome-ai/sec-parser` | 291 | 2026-06-25 | SEC HTML → semantic element tree. Complements edgartools. |
| `lefterisloukas/edgar-crawler` | 540 | 2025-07-18 | 10-K/10-Q item extraction for NLP. **GPL-3.0 — viral, check before embedding.** |
| `bellingcat/EDGAR` | 208 | 2025-05-15 | CLI over EDGAR FTS. Journalism-oriented. Stale. |
| `SEC-API-io/sec-api-python` | 315 | 2026-08-04 | SDK for a **paid** API. You would be renting what edgartools gives free. |

### 2.3 Adjacent event-driven categories

**Index rebalance — `jothamteo/index-rebalance-tracker`** (0 stars, 2026-05-07). Genuinely
well-engineered: `mypy --strict`, CI, Brown-Warner market model, sector-matched controls,
Corwin-Schultz spread, Amihud illiquidity, Kyle's lambda. Cites Petajisto (2011) and
Chen-Noronha-Singal (2004) correctly.
**Disqualifying for trading use:** `DEFAULT_ANNOUNCEMENT_OFFSET = 5` — **the announcement date is
fabricated**, because Wikipedia only carries the effective date. For the S&P index effect the
announcement-to-effective window *is the entire trade*. Also mixes calendar and trading days
(`timedelta(days=...)` against trading-day-documented params), uses current-Wikipedia GICS sectors, and
has no PnL or fills. Use it as a reference implementation of event-study mechanics, nothing more.

**Event study libraries — `LemaireJean-Baptiste/eventstudy`** (69 stars, abandoned 2023-12-22). The
most-starred Python event-study library, and **statistically wrong for clustered events**:

```python
self.var_CAAR = (1/(len(sample)**2)) * np.sum([event.var_CAR for event in sample], axis=0)
self.tstat = self.CAAR / np.sqrt(self.var_CAAR)
```

This assumes **zero cross-sectional correlation between events**. For every S&P add on the same
effective date, or every spinoff in a 2020 wave, it understates SE by roughly `sqrt(1+(N-1)*rho)` and
inflates t-stats — exactly the overlapping-trades trap in your notes. Worse, `sign_test()` and
`rank_test()`, the non-parametric escapes, are **commented out**. Do not use on clustered events. The
falsification-campaign approach — an empirical placebo distribution instead of a parametric SE — is the
correct workaround and costs ~50 lines.

Others (`setzler/eventStudy` 75★ R, `lsun20/EventStudyInteract` 50★ Stata, `JMSLab/eventstudyr` 28★)
are econometrics DiD tools, right for staggered adoption, wrong domain.

**Merger arbitrage — nothing usable.** `marius-stos/merger-arbitrage` (0★) scrapes EDGAR for SC TO-T +
DEFM14A, then computes `p_close` from **hardcoded uncalibrated constants**
(`P_BASE = {cash_tender: 0.93, ...}`, `DOWNSIDE_ON_BREAK = -0.22` fixed for every deal). **There is no
backtest** — not a bad one, none. And a fatal bug: a deal vanishing from the EDGAR scan books the full
spread as profit —

```python
if deal is None:
    return ("SETTLED", "Deal no longer in EDGAR scan — likely closed; collect spread")
```

— but deals also vanish when they *break*, when the date window rolls off, or when EDGAR hiccups. This
systematically manufactures phantom wins. `Keon6/Merger-Arbitrage` (3★, dead 2019) needs SDC
Platinum/Refinitiv (five figures/yr, not included). The other ~10 are spread calculators with a manual
price box or LLM/Kafka demos.

**SPAC arbitrage — does not exist on GitHub.** `gh search repos "SPAC arbitrage"` returns empty;
everything matching "SPAC" is Spacemacs/spaCy/Spacedrive.

**`BaptisteZloch/Stock-Performance-Spin-off-...-ETF`** (0★) — Bloomberg-locked and unrunnable, **but
`data/spinoffs/{SPX,RTY,SXXP,SX5E} Index_spin_offs.xlsx` are committed.** That is free Bloomberg-sourced
spinoff event data for four index universes — useful as an independent cross-check on any
EDGAR-derived universe, which is precisely the audit pantheon's uncommitted list needs.

---

## 3. PRIORITY 3 — MECHANICS

*(See §3 detail below — populated from primary filing text and index-provider rules.)*

### 3.1 When does the spinco actually start trading

Primary source, GE Vernova's Form 10-12B Information Statement (2024), verbatim:

> "We expect, however, that a limited trading market for our common stock, commonly known as a
> **'when-issued' trading market, will develop as early as three days prior to the distribution date**,
> and we expect **'regular-way' trading of our common stock will begin on the first trading day after
> the distribution date**."

So the timeline is: record date → when-issued market opens (~3 days before distribution) → distribution
date → **regular-way trading begins the next trading day**. When-issued trades settle only if the
distribution completes.

Practical retail note: **when-issued markets are thin and many retail brokers do not offer them.** For a
$1,000-3,000 position the realistic entry is regular-way, day 1 or later — which means the
when-issued price discovery window is not yours to trade.

---

## 4. RED FLAGS — the specific traps in this dataset

Named explicitly, since you asked and since I found instances of each in the wild:

1. **Survivorship bias — lethal here, and confirmed present in a published attempt.** A curated spinoff
   list contains the ones that still exist. Worse, the *subtle* version: `falsification-campaign` built
   its universe from EDGAR (bias-free) and then re-introduced the bias by mapping CIK→ticker through
   the **current** SEC ticker file and dropping unmatched rows. Delisted spincos vanish silently at
   universe construction, before any "missing price data" count. **The EDGAR spine only stays bias-free
   if you resolve tickers point-in-time, from the filing text, not from today's mapping.** This is the
   single most important implementation detail in this report.
2. **Look-ahead via date confusion.** Three distinct dates — announcement, 10-12B registration,
   ex-distribution — and they are 2-6 months apart. Using the registration date as the announcement date
   is a look-ahead of months. Using an ex-date-keyed list to define a universe you trade at announcement
   is worse.
3. **Fabricated dates.** `index-rebalance-tracker` synthesises the announcement date as
   effective−5 days because its source lacks it. If a field is not in your data, it is not in your data.
4. **Microcap contamination — and here it is not noise, it is the result.** Pantheon's small/micro tail
   is where all the negative alpha lives (−9.3% at 252d vs −1.6% for the full set). An equal-weighted
   spinoff result is largely a microcap artifact in *either* direction.
5. **Mid-price fills on illiquid new listings.** A newly-spun small cap in week 1 has no meaningful
   mid. Neither published study modelled a spread beyond a flat 20 bps.
6. **Overlapping trades inflating t-stats.** Spinoffs cluster in waves (2014: 37-40 events; 2008: 38).
   Holding 63-252 day windows means heavy overlap and correlated residuals. The most-starred event-study
   library on GitHub gets exactly this wrong. Use a placebo/bootstrap distribution, not a parametric SE.
7. **Entity renaming in curated lists** producing silent mis-joins to price data (§1.3).
8. **Multiple testing.** `Phantomape/ginger` contains a spinoff-completion experiment as one of
   *hundreds* of auto-generated `exp_*` files with no family-wise correction. Any single positive result
   in such a series is noise.

---

## 5. BOTTOM LINE

**On data:** solved, and better than expected. `scripts/spinoff_edgar_harvest.py` gives you a free,
scriptable, survivorship-bias-free-by-construction registry of **741 US SpinCo registrations,
1994-2026**, plus a live forward calendar, with no API key and no subscription. The 1994-2015 portion
is genuinely unexplored — every published attempt starts in 2001 or 2015 because they used full-text
search instead of the form index. Add $29/mo SHARADAR only if you need exact distribution ratios.

**On the edge:** the prior is bad. Two independent pre-registered studies, different data vendors,
different benchmarks, both killed spinoff post-event drift; one found the small-cap tail materially
*negative* against a size-matched benchmark. Neither is airtight — one has a survivorship leak that
biases *toward* positive results and still found nothing, the other has an unauditable universe — but
they fail in the same direction, which is the unhelpful kind of agreement.

**On retail scale, plainly:** the spinoff literature's original effect was documented on 1965-1988 data
and was substantially attributed to a handful of names. The modern tradeable population is
~20-40 events/year, concentrated in small and micro caps with wide first-month spreads. At
$1,000-3,000 per position you can *transact* in most of them — this is not an
institutional-scale-only effect in the capacity sense. **The problem is not size, it is that the
effect appears not to be there.** That is a cheaper answer than it looks: you have the dataset, and the
one honest test nobody has run is the 1996-2015 sample. If that also comes back flat after costs, the
spinoff idea is closed and you spent a day rather than a month.

**One genuine caveat on my own work:** ticker recovery from pre-1997 plain-text filings is the weak
link (§1.2). The EDGAR spine's *enumeration* is complete and bias-free; joining it to prices for the
1990s sample is the part that still needs work, and it is exactly the part where a lazy fix — mapping
through today's ticker file — would silently reintroduce the survivorship bias the whole approach
exists to avoid.
