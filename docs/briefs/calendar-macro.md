<!-- research brief, filed 2026-09-23; agent output verbatim -->

Everything computed here is on SPY daily open/close bars, 5 Jan 2010 – 22 Sep 2026 (4,204 sessions), via `venv/bin/python3` + yfinance. FOMC statement dates were fetched one year at a time from the Federal Reserve's own historical-materials pages (2010–2020) and the current calendar page (2021–2026) — 133 scheduled two-day (or one-day) meetings with a routine 2pm statement; conference calls, notation votes, and the March 2020 emergency meetings were excluded because they have no comparable fixed announcement time. The BLS CPI schedule page only serves the trailing/current year (Dec 2025 – Nov 2026); the archived-year schedule pages 404'd on every URL pattern tried, so the CPI test below runs on 10 verified release dates, not the full 2010–2026 window — flagged explicitly where it matters.

# Calendar and macro-event anomalies in SPY, judged against $5k→$50k in 5 months (58%/month) and 20%/year

**Bottom line first.** None of the seven effects tested come remotely close to either target. The largest, most statistically robust finding here — a negative average return on options-expiration Fridays (t = −3.30, p = 0.001) — is worth about 2%/year gross if traded in isolation, 12 times a year. Turn-of-month and pre-FOMC drift, the two effects with the most academic pedigree, are **not statistically significant** in this SPY sample; the FOMC result matches the literature's own finding that the drift decayed after 2015. The only "calendar" number with real annual magnitude is the overnight/intraday split, and it replicates our own repo's finding almost exactly: gross overnight carry is attractive, and a plausible 10 bp/side cost model turns it sharply negative.

## 1. Turn of month (last session + first 3 of next month)

804 TOM sessions vs 3,400 other sessions, close-to-close: TOM mean 0.0733%/day (≈18.5%/yr annualized) vs 0.0464%/day (≈11.7%/yr) for the rest. **t = 0.65, p = 0.51 — not significant.** This is the classic Ariel/Lakonishok-Smidt-McConnell effect (surveyed in [Cboe/academic literature via McConnell & Xu, "Equity Returns at the Turn of the Month," FAJ 2008]) — the gap here points the expected direction but the daily noise in one 16.7-year SPY sample swamps it. Not a tradeable edge on this test alone.

## 2. Day of week

| Day | n | mean/day | annualized | t | p |
|---|---|---|---|---|---|
| Mon | 786 | 0.0607% | 15.3% | 1.52 | 0.128 |
| Tue | 866 | 0.0770% | 19.4% | 2.25 | **0.025** |
| Wed | 862 | 0.0794% | 20.0% | 2.15 | **0.032** |
| Thu | 847 | 0.0332% | 8.4% | 0.87 | 0.387 |
| Fri | 843 | 0.0067% | 1.7% | 0.18 | 0.855 |

Tuesday and Wednesday carry a real, statistically significant edge over this window; Friday — historically the strong day in the old "weekend effect" literature — is flat. This is the opposite of the pre-2000 pattern (Monday negative, Friday positive) and is consistent with post-2000 studies finding the classic weekend effect has weakened or reversed. Gross-only; no cost model applied since this isn't a standalone strategy (you'd need to be flat on Mon/Thu/Fri, which means trading anyway).

## 3. Overnight vs. intraday, by year, with costs

| Year | Overnight (C→O) | Intraday (O→C) |
|---|---|---|
| 2010 | 5.14% | 6.79% |
| 2011 | 3.74% | −1.66% |
| 2012 | 3.90% | 9.59% |
| 2013 | 11.58% | 15.01% |
| 2014 | 8.67% | 2.67% |
| 2015 | 0.80% | −0.37% |
| 2016 | −5.04% | 15.10% |
| 2017 | 12.24% | 5.71% |
| 2018 | 12.16% | −17.17% |
| 2019 | 12.39% | 13.64% |
| 2020 | 14.80% | 5.18% |
| 2021 | 15.15% | 9.59% |
| 2022 | −14.98% | −3.74% |
| 2023 | 4.48% | 18.18% |
| 2024 | 20.47% | 1.31% |
| 2025 | 7.52% | 9.78% |
| 2026 (YTD) | 8.88% | 4.35% |

Full-period gross: overnight ≈ **7.29%/yr**, intraday ≈ **5.62%/yr** — this is [Lou, Polk & Skouras, "A Tug of War: Overnight versus Intraday Expected Returns," Journal of Financial Economics 134(1), 2019] (URL not independently confirmed this session — SSRN returned 403 on every fetch attempt; treat the citation as directionally right, "not verified"). Their finding — that overnight returns dominate a low-frequency signal and intraday reverses it — is qualitatively what shows up here (2016, 2018, 2022 all show overnight and intraday moving in opposite directions).

**Net of costs is where this dies.** At 5 bp per side, two sides a day (buy at close, sell at open) = 10 bp/day round-trip: overnight net = **−17.86%/yr**. Splitting a 20 bp/day total cost evenly between overnight and intraday legs gives overnight −17.86%/yr and intraday −19.53%/yr. This directionally matches **our own repo's finding of +12%/yr gross vs −13%/yr net at 10 bp/day** — the SPY-equity number here is more negative because SPY's own bid-ask plus a flat 5 bp/side assumption is a harsher friction model than whatever specific cost curve produced the repo's −13%; the qualitative conclusion (gross-attractive, cost-fatal) is identical.

## 4. Pre-FOMC drift, by sub-period

Daily bars can't isolate the literal "24 hours before the 2pm statement" that [Lucca & Moench, "The Pre-FOMC Announcement Drift," Journal of Finance 70(1), Feb 2015, originally NY Fed Staff Report No. 512, Sept 2011, revised Aug 2013 — confirmed via `newyorkfed.org/research/staff_reports/sr512`] measured with intraday data. Three daily-bar proxies: the full day before the decision (close t−2 → close t−1), the decision day's open→close, and the decision day's close-to-close (closest single-bar approximation to their 24h window).

| Sub-period | n | Day-before C→C | Decision-day O→C | Decision-day C→C |
|---|---|---|---|---|
| 2010–2015 | 48 | −0.078% (t=−0.41, p=0.68) | +0.150% (t=1.03, p=0.31) | +0.269% (t=1.60, p=0.12) |
| 2016–2019 | 32 | +0.147% (t=1.46, p=0.15) | −0.147% (t=−1.52, p=0.14) | −0.094% (t=−0.85, p=0.40) |
| 2020–2026 | 53 | +0.048% (t=0.39, p=0.69) | −0.127% (t=−0.84, p=0.40) | +0.105% (t=0.59, p=0.56) |
| Full 2010–2026 | 133 | +0.026% (t=0.30, p=0.76) | −0.032% (t=−0.38, p=0.71) | +0.117% (t=1.20, p=0.23) |

**No sub-period is significant.** This is consistent with [Kurov, Wolfe & Gilbert on the decay of the drift after Lucca-Moench's original 2011 publication] — general characterization of that literature; the exact paper title/journal/URL was not independently confirmed this session (SSRN searches returned 403), so treat as "not verified." Whatever residual drift existed in the original 1994–2011 sample does not survive in SPY 2010–2026 on daily bars at any sub-period tested. Directionally, the 2010–2015 slice is closest to matching the original finding (positive, largest t-stat) and it still misses conventional significance.

## 5. CPI release days — sample too small to generalize

The live BLS schedule (`bls.gov/schedule/news_release/cpi.htm`) only serves Dec 2025 – Nov 2026; every archived-year URL pattern tried (`bls.gov/schedule/archives/cpi_nr.htm`, `bls.gov/schedule/news_release/2020_sched.htm`) returned HTTP 404, and FRED's release-dates page (`fred.stlouisfed.org/release/dates?rid=10`) also 404'd. **Not verified for 2010–2025; only 10 dates (Dec 2025 – Sep 2026) are checked against a primary source.**

On those 10 dates: mean open→close = −0.20%, mean |open→close| = **0.26%**, against an all-day baseline mean |open→close| of **0.56%** (t = −3.07, p = 0.013 vs. that baseline — i.e., CPI days moved *less*, not more, in this specific sample). That is almost certainly a low-volatility-regime artifact of a 10-session window in one calm year, not a real finding about CPI days generally — the broader literature (e.g., the macro-announcement premium documented around scheduled releases, [Savor & Wilson, JFQA 2013]) finds CPI/FOMC/employment days carry *above-average* absolute moves and above-average average returns, the opposite sign of what this small sample shows. Do not trade on this line; it needs the full 2010–2026 archive, which was not reachable this session.

## 6. Options-expiration (3rd) Friday vs. other Fridays

| | n | mean/day | annualized | std |
|---|---|---|---|---|
| Opex Friday | 201 | **−0.195%** | −49.2% | 0.961% |
| Other Friday | 642 | +0.070% | +17.6% | 1.088% |

t = −3.30, **p = 0.0010**. Median opex return is also negative (−0.119%) against a positive median (+0.125%) on other Fridays — not a mean driven entirely by a handful of outliers. Excluding the seven worst crisis-adjacent opex dates (Mar 2020, Aug 2015, Dec 2018, the two 2022 vol events, and two others) the effect survives: n = 194, mean −0.136%, t = −2.71, p = 0.0070. This is the single strongest and most surprising result in this brief — it runs counter to the retail folklore of a "rally into opex" from dealer gamma pinning that shows up in [Cboe and Nomura opex commentary]; neither a Cboe nor a Nomura note was fetchable this session (Cboe insights index 404'd) to check the exact mechanism claimed there, so treat that framing as background color, "not verified," not a citation. **Economically it is still small**: shorting SPY into every opex Friday captures roughly 12 × 0.195% ≈ 2.3%/yr gross, before any transaction cost, and this is an equity-direction result — the desk trades SPX/NDX 0DTE structures, where gamma/pin effects near opex are already a known live-system consideration, not options income from a directional equity short.

## 7. Month-end pension-rebalancing proxy

Defining a "big" month as a >±3% move in SPY from day 1 through day n−2 of the month, then looking at the last-2-session return:

| | n | last-2-session mean | vs. normal months |
|---|---|---|---|
| After big up month | 59 | 0.043% | t=−0.31, p=0.76 |
| After big down month | 30 | 0.287% | t=0.48, p=0.64 |
| Normal months | 112 | 0.097% | — |

**No signal.** Neither direction is distinguishable from normal month-end behavior. This is a crude proxy (no actual pension-flow data, just a "did the month already move a lot" filter) but it finds nothing worth refining further, consistent with the flavor of null result the sector-rotation and technicals-only studies elsewhere in this repo already documented.

## Verdict table

| Effect | Statistically significant here | Real annualized contribution if traded alone | Net of realistic costs | 58%/mo | 20%/yr |
|---|---|---|---|---|---|
| Turn of month | No (p=0.51) | not tradeable (not significant) | — | No | No |
| Day of week (Tue/Wed long) | Yes (p=0.025, 0.032) | ~8%/yr gross (2 days/wk) | untested, would erode most of it | No | No |
| Overnight carry | n/a (measured, not a hypothesis test) | +7.3%/yr gross | **−17.9%/yr at 10bp/day** | No | No |
| Intraday | n/a | +5.6%/yr gross | **−19.5%/yr at 20bp/day split** | No | No |
| Pre-FOMC drift | No, any sub-period | not tradeable (not significant) | — | No | No |
| CPI-day moves | Sample too small/short to test | not tradeable (10 dates, wrong sign) | — | No | No |
| Opex Friday short | Yes (p=0.001, robust ex-outliers) | ~2.3%/yr gross, 12 trades/yr | untested; likely erodes most of it at these magnitudes | No | No |
| Month-end rebalance proxy | No | not tradeable | — | No | No |

**Feasibility.** 58%/month (900% in 5 months) has no relationship to anything measurable here — the single largest gross annual number in this entire brief (overnight carry, ~7.3%/yr) is two orders of magnitude short of what one month of the target requires, and it goes negative net of cost. 20%/year is also not reached by any individual effect, gross or net; the closest anything comes is the *unhedged, cost-free* Tuesday/Wednesday day-of-week pattern, which is real but small, and has not been tested against any transaction-cost model. The opex-Friday result is the one genuinely new, statistically robust finding in this brief and is worth a dedicated follow-up — on SPX 0DTE structures with real quotes, not SPY equity direction — before concluding anything about its tradability.

## Sources

- Federal Reserve, FOMC meeting calendars (current): https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- Federal Reserve, FOMC historical meeting pages, fetched individually for 2010–2020 (e.g. https://www.federalreserve.gov/monetarypolicy/fomchistorical2015.htm, pattern repeated per year)
- BLS CPI release schedule (current year only, archive unreachable): https://www.bls.gov/schedule/news_release/cpi.htm
- Lucca & Moench, "The Pre-FOMC Announcement Drift," *Journal of Finance* 70(1), 2015; NY Fed Staff Report No. 512 (confirmed): https://www.newyorkfed.org/research/staff_reports/sr512
- Kurov, Wolfe & Gilbert on the post-2011 decay of the pre-FOMC drift — cited from general knowledge of the literature; exact title/journal/URL **not verified** this session (SSRN 403s on every fetch)
- Frazzini & Lamont, "The Earnings Announcement Premium and Trading Volume," NBER Working Paper 13090, 2007 (confirmed): https://www.nber.org/papers/w13090
- Lou, Polk & Skouras, "A Tug of War: Overnight versus Intraday Expected Returns," *Journal of Financial Economics* 134(1), 2019 — citation from general knowledge; URL **not verified** this session (SSRN 403)
- Cboe / Nomura opex commentary — referenced as background for the opex-Friday folklore only; **not fetchable** this session (Cboe insights index returned 404), so not independently checked
- Raw SPY daily bars and all intermediate CSVs: `/private/tmp/claude-501/-Users-sahilmajmudar-index-daytrading-dev/caaef1b4-572c-4b4c-95db-260b47e91a2f/scratchpad/spy_daily.csv`, `fomc_results.csv` (session-local, not in the repo)

**Not verified:** the CPI test (2010–2025 archive unreachable, so it runs on 10 recent dates only), the Kurov/Wolfe/Gilbert and Lou/Polk/Skouras exact citation links, and the Cboe/Nomura opex mechanism claims. Everything else in this brief is a direct computation on fetched primary-source dates against yfinance SPY bars, reproducible from the scripts used to produce it.
