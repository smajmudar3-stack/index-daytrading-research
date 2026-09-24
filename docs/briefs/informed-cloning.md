# Informed-money cloning: congressional trades, hedge-fund 13Fs, and this repo's own insider finding

**Question:** does cloning "informed" money — Congress via NANC/KRUZ, hedge funds via
GVIP — deliver anything like $5,000 → $50,000 in 5 months (58%/month, compounding to roughly
+250,000%/year) or even a plain 20%/year? Computed on real total-return series since
inception; literature and vendor methodology fetched and cited by URL below.

## What was computed

`yfinance`, adjusted close (dividends included), 2026-09-23. `KRUZ` was renamed to `GOP` on
Yahoo's feed at some point after launch — same fund, continuous price history back to its
2023-02-07 inception, confirmed by matching NANC's inception date exactly (both funds from
the same sponsor launched the same day).

| Fund | Window | Total return | CAGR | Max drawdown | Ann. tracking error vs SPY | Corr. vs SPY | Beta vs SPY |
|---|---|---:|---:|---:|---:|---:|---:|
| **NANC** (Dem. congress-clone) | 2023-02-07 → 2026-09-21 | +109.5% | +22.7% | −20.9% | 4.9% | 0.958 | 1.07 |
| **KRUZ/GOP** (Rep. congress-clone) | 2023-02-07 → 2026-09-21 | +83.1% | +18.2% | −20.7% | 8.8% | 0.825 | 0.82 |
| **SPY**, same window | 2023-02-07 → 2026-09-21 | +95.3% | +20.3% | −18.8% | — | — | — |
| **GVIP** (Goldman hedge-fund VIP), same window | 2023-02-07 → 2026-09-21 | +124.0% | +25.0% | −23.3% | 8.6% | 0.887 | 1.11 |
| **GVIP**, fund's own full life | 2016-11-11 → 2026-09-21 | +341.0% | +16.2% | −37.1% | — | — | — |

Source data: `yfinance` `download(..., auto_adjust=True)` close series; CAGR from
first-to-last adjusted close; drawdown from the running peak; tracking error is the
annualised standard deviation of daily return minus SPY's daily return over the same window.
Script not checked into the repo (scratch compute, `/tmp/compute_etfs*.py`).

**Reading the numbers.** NANC and GVIP both beat SPY's total return over the identical
3.62-year window (NANC by +14 points cumulative, GVIP by +29 points); KRUZ trailed SPY by
about 12 points. None of the three comes close to clearing its own tracking error by a
margin that would survive fees and taxes, and GVIP's own 9.9-year full-life CAGR (16.2%) is
*below* SPY's 3.6-year-window CAGR (20.3%) — the 2023-2026 window was a strong run for all
four series, index included, not evidence the clone mechanism itself adds return. A fund
82-96% correlated to SPY with 6-9% annual tracking error is a closet-index product with a
side bet, not a vehicle that turns $5,000 into $50,000 in five months. None of NANC, KRUZ, or
GVIP has ever posted anything near a 58%/month gain in this data (checked by eye on the daily
series, not a formal rolling-window scan — **not verified** as an exhaustive search).

## The disclosure-lag problem the clone trade is built on

The STOCK Act requires a Periodic Transaction Report **"by the earlier of ... 30 days from
being made aware of the transaction; or 45 days from the transaction"** —
<https://ethics.house.gov/financial-disclosure> (fetched 2026-09-23; the page also links the
office's PTR calculator). The statutory text (Pub. L. 112-105, §6, amending the Ethics in
Government Act of 1978 §103) sets the same 30/45-day structure —
<https://www.govinfo.gov/content/pkg/PLAW-112publ105/html/PLAW-112publ105.htm> (fetched
2026-09-23). A congress-clone ETF is by construction trading on a disclosure that is, on
average, three-plus weeks stale before the fund can act on it, and up to six-plus weeks stale
in the worst case.

## What the academic literature actually measured

- **Ziobrowski, Cheng, Boyd & Ziobrowski (2004), "Abnormal Returns from Common Stock
  Investments of the U.S. Senate," JFQA** — the paper the whole "Congress beats the market"
  claim traces to. Abstract (via RePEc/IDEAS, fetched 2026-09-23,
  <https://ideas.repec.org/a/cup/jfinqa/v39y2004i04p661-676_00.html>): a portfolio mimicking
  Senate **purchases** beat the market by **+85 bp/month** in 1993-1998; Senate **sales**
  lagged the market by −12 bp/month. This is the original edge NANC/KRUZ are named after, and
  it is a Senator's *own* trade, executed with the information advantage intact — not a
  retail clone reading it 30-45 days later.
- **Eggers & Hainmueller (2013), "Capitol Losses: The Mediocre Performance of Congressional
  Stock Portfolios," AJPS** — direct successor to Ziobrowski; DOI page 403'd on fetch
  (<https://onlinelibrary.wiley.com/doi/10.1111/ajps.12045>) and SSRN/Harvard mirrors also
  failed (403/404). **Not verified by direct fetch this session.** Its title alone signals
  the finding runs opposite to Ziobrowski's — this is the paper to re-fetch before leaning on
  either result.
- **Cohen, Malloy & Pomorski (2012), "Decoding Inside Information," JF** — corporate-insider
  analogue to the same question. Abstract (via RePEc/IDEAS, fetched 2026-09-23,
  <https://ideas.repec.org/a/bla/jfinan/v67y2012i3p1009-1043.html>): splitting insider trades
  into **routine** (essentially zero abnormal return) and **opportunistic** (value-weighted
  **+82 bp/month**) shows almost all predictive power sits in a minority subset that a raw
  trade count cannot isolate — and that opportunistic traders were disproportionately local,
  nonexecutive insiders at poorly governed firms, not the executives a naive clone would
  overweight.
- **Brav, Jiang, Partnoy & Thomas (2008), "Hedge Fund Activism, Corporate Governance, and Firm
  Performance," JF** — the closest academic analogue to GVIP's "clone the hedge fund VIP
  list" thesis. Abstract (via RePEc/IDEAS, fetched 2026-09-23,
  <https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1729-1775.html>): the abnormal return sits
  **around the announcement of activism**, roughly **+7%, with no reversal over the
  subsequent year** — i.e., the edge is in being present at the 13D filing, not in holding a
  quarterly-lagged basket of a fund's *entire* long book (which is what GVIP does; GVIP is
  built off 13F "VIP" holdings, not activist 13Ds, and 13Fs are filed up to 45 days after
  quarter-end, older than the STOCK Act's own window).
- **Ljungqvist & Qian, "How Constraining Are Limits to Arbitrage?"** — candidate short-drift
  companion finding; every NBER/RePEc URL tried 403'd or 404'd, and the one PDF that did
  download came back unreadable binary to the fetch tool. **Not verified this session** —
  a pointer only, not a supported number here.

## Vendor methodology fetched

- **Quiver Quantitative**, congressional trading page (fetched 2026-09-23,
  <https://www.quiverquant.com/congresstrading/>): "We download those disclosures, parse them
  for stock trades, fetch the stock's performance in the time following the transaction, and
  calculate each politician's cumulative return from their trades" — built directly on the
  STOCK Act's 45-day-lagged PTRs, and the site's own disclaimer states "backtested
  performance does not represent actual trading."
- **Capitol Trades** methodology page: `https://www.capitoltrades.com/about` and `/faq` both
  returned HTTP 403 to the fetch tool this session (bot-blocked). **Not verified.**
- **SEC EDGAR full text search** (fetched 2026-09-23, <https://www.sec.gov/edgar/search/>):
  indexes "the full text of electronic filings since 2001," filterable by form type and date
  range; this is the UI in front of the `efts.sec.gov/LATEST/search-index` API this repo's
  own tooling could hit directly for Form 4 / 13F / 13D text search rather than depending on
  a third-party aggregator's parse.

## This repo's own measurement of the same question

`04_live_system/insider_score.py`'s docstring (read in full for this brief) is this repo's
own literature review on exactly this question and reaches the same place as the citations
above: a raw insider-buy **count** conflates routine and opportunistic buying and "dilutes
the signal," citing the same Cohen/Malloy/Pomorski routine-vs-opportunistic split. It also
flags that per-insider track record ("this person's buys have been right before") is a stated
gap — `track_record()` returns a neutral 1.0 "with a stated reason until the ledger has
accumulated enough," deliberately not approximated.

More decisively, `02_findings/uw_flow.md` (current, measured 2026-09-22) already ran the
count-based insider signal on two years of vendor history and got a **measured null**:
`insider net purchases, 30 days` scored **IC −0.004, t −0.1** at the 5-day horizon (52 weeks),
indistinguishable from zero and sign-unstable across halves (−0.023 first half, +0.015
second half). This repo's live voter keeps insider input at a low weight (0.06) specifically
because "the count-based vendor series measured null" — the same failure mode
Cohen/Malloy/Pomorski predict for any insider signal that doesn't isolate the opportunistic
subset, and the same failure mode a congress- or 13F-clone ETF inherits when it clones
*everyone's* trade, undifferentiated, 30-45 days late.

## Verdict

| Claim | What it requires | What the computed/cited evidence shows | Verdict |
|---|---|---|---|
| $5,000 → $50,000 in 5 months (58%/month, ~10x) | A single fund or strategy sustaining ~58%/month compounding | NANC/KRUZ/GVIP: 3.62-yr CAGR of 18-25%, i.e. ~1.4-1.9%/month compounded. No fund in this set has ever approached 58% in a single month, let alone sustained it for five. | **Not achievable by any fund measured here — off by roughly 30-40x on monthly return.** |
| 20%/year from cloning informed money | A repeatable edge net of the disclosure lag, fees, and tracking error | NANC (22.7% CAGR) and GVIP (25.0% CAGR, same window) *did* clear 20%/year in this specific 3.6-year bull run, but so did SPY (20.3%) with far less tracking error and no expense ratio drag; KRUZ (18.2%) did not clear it. GVIP's own 9.9-year full-life CAGR is 16.2%, below SPY's shorter-window number, showing the recent outperformance is window-dependent, not structural. The academic edge these funds are named after (Ziobrowski's +85bp/month, CMP's +82bp/month) belongs to the *original insider transacting in real time*, not a retail vehicle trading a 30-45-day-old disclosure — and this repo's own null result on count-based insider flow (`uw_flow.md`, IC −0.004) is direct evidence that the diluted, lagged version of this signal carries nothing. | **Landed near 20%/year in one specific bull window by coincidence with a rising market, not because the clone mechanism has a demonstrated edge; not a claim to build a plan on.** |

## Bottom line

The compute is real and reproducible (`yfinance`, 2023-02-07 through 2026-09-21 for
NANC/KRUZ, GVIP's own longer history included for context). The literature these products
market themselves on documents an edge that belongs to the original transactor in real time
(Senators, opportunistic insiders, activist hedge funds at the moment of filing) — every
citation above that could be verified this session says so explicitly. The moment that edge
is diluted across an entire chamber or an entire 13F "VIP" list and delayed by the 30-45 days
the STOCK Act and 13F rules both impose, this repo's own measurement of the closest analogue
(insider-buy counts, `uw_flow.md`) already shows it flattens to zero. Two citations
(Eggers & Hainmueller, Ljungqvist & Qian) and one vendor's methodology page (Capitol Trades)
could not be fetched this session — **not verified**, flagged rather than fabricated.
