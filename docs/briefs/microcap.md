<!-- research brief, filed 2026-09-23; agent output verbatim -->

# Microcaps, penny stocks and small-cap "runners" as a retail strategy, 2026

**Bottom line:** every leg of this trade loses money for the buyer on average. The pumped-stock
buyer loses to the promoter (literature, not verified this session: Leuz et al.'s German
promotion-scheme sample; verified this session: Renault's Twitter pump-and-dump sample shows a
"sharp price reversal over the next week" following the pump). The gap-up-day buyer loses to the
fade: on 794 clean +20%-day events across 81 real small/micro-cap tickers 2024-2026, the median
next-day return is **-1.08% gross, -2.08% net of realistic costs**, and only 33-35% of next days
are green. The size premium itself — the only piece of this idea with a real, decades-long,
risk-adjusted record — returned **10.8-11.1%/yr (IWC/IWM) against SPY's 14.2%/yr** since 2010, i.e.
small caps did not even beat the market, let alone clear 20%/yr. Nothing in this brief is in range
of $5,000 to $50,000 in five months (58%/month), and nothing in it clears 20%/yr on a risk-adjusted
basis either. This is the same shape as every other finding in this repo: real, small or negative,
and not a five-month plan.

## 1. What was computed and from what

Three separate questions, three separate data sources:

1. **The pump-and-dump buyer's return** — literature only. Fetched: the SEC's investor bulletin on
   microcap fraud (confirmed) and Thomas Renault's abstract on social-media stock manipulation
   (confirmed, SSRN). The Leuz et al. "Wolf of Wall Street" paper on promoted-stock buyer losses
   could not be fetched this session (every URL tried — NBER, Wiley/JoF, SSRN — returned 403/404 or
   the wrong paper); its headline figure is stated from established literature and flagged not
   verified.
2. **The gap-up-day fade** — computed directly with `venv/bin/python3` and `yfinance`. The task
   asked for this on IWM's bottom-100-by-market-cap holdings via the iShares holdings CSV. That CSV
   is not fetchable from a script: `curl` against `ishares.com/.../1467271812596.ajax?fileType=csv`
   returns HTTP 200 with a `content-type: text/csv` header but an HTML bot-challenge page as the
   body (confirmed via `WebFetch` and via `curl -D -` showing the header/body mismatch);
   `stockanalysis.com`'s holdings API is behind a Cloudflare challenge. **Not obtainable this
   session.** Substituted a hand-curated, **not survivorship-free**, basket of 128 tickers matching
   the retail "penny stock / meme runner" profile this brief is actually about (biotech microcaps,
   EV/battery SPAC-era names, crypto miners, meme-stock holdovers) — arguably closer to the product
   being evaluated than IWM's Russell 2000 constituents, which mostly aren't penny stocks. Pulled
   daily bars 2024-01-01 to 2026-09-23; 89 of 128 tickers had usable data (the other 39 delisted or
   returned no series — informative about this cohort's mortality, though picked with hindsight, so
   no delisting *rate* is claimed).
3. **The size premium** — computed directly: IWC (micro-cap), IWM (small-cap), SPY, 2010-01-04 to
   2026-09-21, daily total-return (`auto_adjust=True`) closes, simple (non-excess) CAGR/vol/Sharpe/
   max drawdown. Ken French's "Portfolios Formed on Size" page was fetched and its description
   confirmed (decile portfolios, monthly/daily, with/without dividends,
   `ftp/Portfolios_Formed_on_ME_CSV.zip`), but the CSV was not downloaded and decile-sorted this
   session — the task's stated fallback (IWC/IWM/SPY via yfinance) was used instead.

## 2. What the pumped-stock buyer earns

**Renault (2017/2020), "Market manipulation and suspicious stock recommendations on social
media"** (SSRN 3010850, confirmed via fetch — the initially-tried SSRN ID 3010786 in the task
prompt 403'd; 3010850 is correct and cited by 54). Renault examined millions of Twitter messages
about small-cap companies and found that "abnormally high message activity on social media is
associated with a large price increase on the event day and followed by a sharp price reversal
over the next week," and separately identified coordinated inauthentic activity — "stock
promoters, fake accounts, automatic postings" — consistent with organized pump-and-dump rather
than organic enthusiasm. The buyer who follows the spike is, on Renault's own construction, buying
into a price that mean-reverts within days.

**Leuz, Meyer, Muhn, Soltes & Volkova, "Who Falls Prey to the Wolf of Wall Street? Investor
Participation in Market Manipulation Schemes."** Not independently fetched this session (NBER
w24083 turned out to be an unrelated marriage-economics paper; the Journal of Finance DOI 403'd;
SSRN and search-engine lookups did not resolve a working link within budget). Stated from
established literature, not verified: the paper studies stock promotion/spam campaigns targeting
German retail brokerage clients and finds that investors who buy a promoted stock lose money on
average following the promotion, and that participation skews toward less sophisticated,
higher-turnover accounts — the same mechanism Renault documents from the promoter's side.

**SEC investor bulletin on microcap fraud** (`sec.gov/investor/pubs/microcapstock.htm`, confirmed
via fetch): frames risk disclosure rather than a buyer-return statistic, but corroborates the
mechanism: microcap stocks are "more volatile and less liquid," many issuers file no SEC reports
so there is little to verify a promoter's claims against, "any size of trade can have a large
percentage impact on the price," and promotion channels — unsolicited spam, paid newsletter/
broadcast promoters "posing as independent" without disclosure, cold calling, fabricated press
releases about "sales, acquisitions, revenue projections" — are named explicitly as fraud vectors.
Core advice: never use "unsolicited e-mails, message board postings and company news releases" as
the sole basis for a trade. FINRA's parallel OTC-market-risk page could not be located this
session — every guessed URL on `finra.org` (five attempts) returned 403 or 404; **not verified.**

## 3. The small-cap gap-up fade, computed on real names

Curated universe (n=128; see caveats above), daily bars 2024-01-01 to 2026-09-23. Raw event set:
every day a ticker closed up 20%+ from the prior close, next-day close-to-close return recorded,
minus 100 bp round-trip cost (50 bp/side). Raw set = 1,009 events, 82 tickers — but it contains
obvious data artifacts: names like XELA, BBIG and AMPE did repeated reverse splits while trading
near or below $1, and `yfinance`'s split-adjustment does not clean these up reliably for
delisted-adjacent tickers, producing one-day "returns" of +2,400% to +5,985% that are vendor-feed
noise, not tradeable prices (a real-world version of the same risk: these names also halt and gap
on reverse-split announcements, so a live trader wouldn't get a clean fill either). Restricting to
day-gains of 20-100% (excludes the reverse-split-scale artifacts) leaves a clean set:

| Metric | Clean set (n=794 events, 81 tickers) |
|---|---:|
| Median next-day return, gross | **-1.08%** |
| Median next-day return, net of 100bp round-trip | **-2.08%** |
| Mean next-day return, winsorized 2nd-98th pctile, gross | +0.93% |
| Mean next-day return, winsorized 2nd-98th pctile, net | **-0.07%** |
| Win rate (next day positive), gross | 35.1% |
| Win rate, net | 33.4% |
| Share of events with next-day loss worse than -10% | 23.9% |
| 10th / 90th percentile, next-day gross | -25.3% / +20.9% |

The median and the cost-adjusted winsorized mean both land at or below zero, with a fat left tail
(nearly a quarter of "buy the +20% day, hold overnight" bets lose more than 10% the next day) and
only about a third of trades green at all. This reproduces, on real 2024-2026 small/micro-cap
prints, what the broader "day-one gap-up fade" literature argues from a different angle: a large
one-day gap in a low-float, high-attention name over-extends and mean-reverts on the following
session rather than continuing. The task also asked for an arxiv/SSRN abstract specifically on
this effect; none was located within the tool budget this session (several targeted guesses — one
resolved to an unrelated differential-geometry paper) — **not verified as a separate citation**,
though the direct 2024-2026 computation above stands on its own.

**Caveats stated plainly:** this is not survivorship-free — the 128 tickers were hand-picked from
memory of retail-favorite volatile names, which overweights names already known for large swings
(BBIG 141 events, XELA 83, NVOS 76) and excludes the 39 tickers with no 2024-2026 data (30% of the
list) from the computation rather than counting them as zeros/delistings, which would bias the fade
measurement in either direction. It is also not IWM's actual bottom 100 by market cap, which the
task specified and which was not obtainable this session (Section 1).

## 4. The size premium's post-2010 record

| ETF | CAGR | Ann. vol | Sharpe (rf=0) | Max drawdown |
|---|---:|---:|---:|---:|
| IWC (iShares Micro-Cap) | 11.08% | 23.26% | 0.57 | -47.21% |
| IWM (iShares Russell 2000) | 10.84% | 22.15% | 0.58 | -41.13% |
| SPY (S&P 500) | 14.18% | 17.06% | 0.86 | -33.72% |

2010-01-04 to 2026-09-21, daily total-return closes, `auto_adjust=True`, Sharpe computed on raw
(not excess-of-risk-free) returns, so all three are on the same footing but nominally slightly
overstated versus a true risk-free-adjusted Sharpe. The size premium — small/micro caps
outperforming large caps — is simply **absent** in this window: both small-cap proxies trailed SPY
by roughly 3-3.5 points a year, carried more volatility, and drew down further, arriving at a
materially worse Sharpe (0.57-0.58 vs 0.86). This is consistent with the well-documented
post-2000ish weakening of the size effect in the broader academic literature (not re-verified via
the French decile CSV this session — see Section 1). Micro-caps (IWC) beat small-caps (IWM) by
about 0.24 pts/yr but with more vol and a deeper drawdown — no clean "smaller is better" gradient
inside the small-cap space either; if anything the pattern below the IWM line is what Section 3
measured directly: individual micro/penny names dominated by idiosyncratic blowups, not a
diversified size tilt.

## 5. Verdict

| Question | Finding | vs. $5k→$50k/5mo (58%/mo) | vs. 20%/yr |
|---|---|---|---|
| Pumped-stock buyer's return | Negative / mean-reverts within a week (Renault, confirmed); established literature says promoted-stock buyers lose money on average (Leuz et al., not verified this session) | No | No |
| Small-cap +20%-day, next-day hold | Median -1.08% gross, -2.08% net; only 33-35% win | No | No — negative expectancy |
| Size premium, IWC/IWM vs SPY, 2010-2026 | Small/micro caps trailed SPY by 3-3.5 pts/yr with worse Sharpe and deeper drawdowns | No | No — didn't even beat buy-and-hold, let alone hit 20% |

Judged against $5,000 → $50,000 in five months, nothing here is remotely in range — even the
*most* favorable single event in the clean gap-fade set (the 90th percentile, +20.9% on one
overnight hold) is two orders of magnitude short of the ~58%/month rate the goal requires sustained
for five straight months, and the *median* outcome of that same trade is a loss. Judged against
20%/year, the size premium — the only academically "real" idea in this brief's scope — didn't
clear even the market's own return in this window, and the two hands-on trading rules examined
(buy the pump, buy the gap-up day) both have negative or roughly zero cost-adjusted expected value.
The consistent story: microcap/penny-stock "opportunity" is a liquidity and information asymmetry
that runs against the retail buyer — promoters and early sellers are the ones documented to
profit, and the retail entry point is measurably the wrong side of both trades.

**Not verified this session:** FINRA's OTC-market-risk page (five URL attempts, all 403/404);
Leuz et al.'s exact buyer-loss figure (NBER/JoF/SSRN links all failed; stated from established
literature); a dedicated arxiv/SSRN abstract on small-cap gap-up-day intraday reversal (none
located within budget; the direct 2024-2026 computation in Section 3 was run in its place); the
iShares IWM holdings CSV (bot-blocked; a hand-curated substitute universe was used and its
survivorship limitations stated in Section 3); Ken French's size-decile CSV was not downloaded or
recomputed (description page confirmed; IWC/IWM/SPY used per the task's stated fallback). All
yfinance computations (Sections 3-4) were run directly this session with
`/Users/sahilmajmudar/index-daytrading/venv/bin/python3` and are reproducible from
`microcap_calc.py` (scratchpad; not checked into the repo).
