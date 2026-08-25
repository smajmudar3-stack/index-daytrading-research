# 04 — Event-driven options: where IV mis-prices events

**Status:** complete · **Evidence quality:** peer-reviewed, top journals ·
**Relevance:** contains the strongest positive finding in the bank so far — and
directly challenges one of our own results

---

## The headline, and it is not the trade people think

> The one robust "IV underprices" finding is **not buying the event**. It is
> buying vol **into** the event and selling **before** it happens.

## A1 — Pre-announcement vega capture (the strongest positive result)

**Gao, Xing & Zhang (2018), *JFQA* 53(6).** 1996–2013, US equity options.

> "Straddles on individual stocks generally earn negative and significant
> returns. However, average at-the-money straddles **from 3 days before an
> earnings announcement to the announcement date yield a highly significant
> 3.34% return**."

Hold T−3 → T−0 and **exit before the release**. The mechanism is vega, not
gamma — you are paid for the IV ramp, not the move.

**Two problems.** The edge concentrates in "smaller firms… **less trading
volume/higher transaction costs**" — it sits exactly where spreads are worst,
which is a limits-to-arbitrage result rather than a free lunch. And **Milian
(2023) could not replicate GXZ's related signals on 2014–2017**: "this suggests
that the options market has become more efficient in recent years." Treat +3.34%
as a 1996–2013 number that may already be gone.

Corroboration on the equity side: *Management Science* (2025) finds **72% of the
earnings announcement premium is realised before, not after, the release**.

## A2 — The most actionable paper found: AvgEA − Implied

**Milian (2023), *JRFM* 16(5):270** (open access). 2014Q1–2017Q1, 13 quarters,
100–258 announcements per quarter, CBOE Datashop.

Signal computed the day before the announcement, 15 min before the close:
- `AvgEA` = mean |1-day return| over the firm's **previous four** earnings
- `Implied` = ATM weekly straddle ÷ spot (weekly expiring that week)
- `Score = AvgEA − Implied`

| portfolio | quarterly return | significance |
|---|---|---|
| Q1 (implied ≫ historical) — **sell** | **−5.42%** | **1%** |
| Q5 (historical ≫ implied) — buy | +8.78% | p = 0.106 |
| **hedge (Q5 − Q1)** | **+14.20%** | **5%** |

$1 → $4.79 over 13 quarters. Worst quarter −11.1%, max DD −14.9%.

**Three caveats that shrink it hard:** mid-quote prices with **zero transaction
costs**; only **13 quarterly observations**; and **the short leg is the
statistically stronger one** — so even this "IV underprices" paper is, on its
reliable leg, a *sell-premium* finding.

## A3 — Left-tail risk (cleanest underpricing, non-event)

**Chen, Gan & Vasquez (2024), *JFQA*.** "**Crash insurance for high (low)
left-tail risk firms earns positive (negative) returns**, suggesting the downside
protection it provides is not adequately priced." Expressed with **bear spreads**
— defined risk, structurally cheap.

---

## B — The result that closes off the naive thesis

**Alexiou, Goyal, Kostakis & Rompolis (2025), *Review of Finance* 29(4).**

This tested exactly the hypothesis "find events where the market knows a big
binary move is coming," and found the opposite:

> "IV curves… frequently become concave prior to earnings, typically reflecting a
> **bimodal risk-neutral distribution**… Firms with concave IV curves exhibit
> **significantly higher absolute stock returns** on the announcement day…
> **Returns on delta-neutral straddles, delta-neutral strangles, and delta- and
> vega-neutral calendar straddles are negative and significantly lower** in the
> presence of concave IV curves."

The signal **correctly predicts bigger realised moves**, and buying vol on those
names is **worse** than average. Three structures — including the vega-neutral
calendar, the standard "avoid IV crush" workaround — all lose more. **The market
prices the bigger move, and then some.**

## FDA / biotech binaries — the folklore is backwards

**There is no peer-reviewed literature on option returns around FDA binary
events.** OpenAlex and Crossref searched; the intersection is empty. That absence
is itself evidence — nobody has published an edge in a supposedly obvious place.

Unverified commercial data (treat as hypothesis only): 763 PDUFA decisions
2024–26, median decision-day move **±7% micro-cap, ±3% small, ±2% mid, ±1%
large**. 1,752 clinical readouts: **median move 3.8%, 57% land inside ±5%, but
7.6% crash 30%+**.

If roughly right, the folklore ("biotech binaries move 30–50%") is **wrong for
the typical event**, so options priced to folklore are *overpriced* — a sell-side
opportunity. But **the 7.6% crashing 30%+ is exactly the tail that destroys
premium sellers.** A 57%/7.6% structure is the textbook shape of a wonderful win
rate with negative expectancy.

**For the 10x goal, that 7.6% tail is the interesting number** — it is convexity,
and it is the one place in this report where a bounded-downside long position
might be mispriced in our favour.

## Dead — drop these

- **Index rebalancing.** Greenwood & Sammon (*JF* 2024): S&P 500 addition
  abnormal return fell from **7.4% in the 1990s to under 1%** in the last decade,
  deletions to 0.1% — *despite* indexed assets growing.
- **M&A directional options.** ~25% of takeovers show informed pre-announcement
  flow in short-dated OTM calls (Augustin et al., *Mgmt Sci* 2019). You would be
  trading against that flow, and SEC litigates only 8% of it.

---

## Frequency — the constraint that decides compounding

| event type | opportunities/year with liquid options |
|---|---|
| **earnings** | **~2,000–6,000** — the only class with enough cadence |
| PDUFA decisions | ~380 total; far fewer optionable |
| clinical readouts | ~600–900, mostly illiquid micro-caps |
| M&A targets | ~145 |
| S&P 500 additions | ~20–25 — **and the effect is zero** |

Only earnings compounds, and it gives 4 events per name per year — so any book
must be **cross-sectional**, which is exactly how Milian's is built (≥20 firms
per quintile).

## The cost reality

**Bryzgalova, Pavlova & Sikorskaya (2023), *JF*:** quoted spreads on
retail-favoured weeklies average **12.6%**, and retail "lose money on average."

Every result above except merger arb is **gross of transaction costs**. The
highest-value work is not finding another signal — it is an honest fill model.

---

## ⚠️ This report challenges our own earnings finding

Our in-house result: earnings straddles **−35.03%, t = −95.7**.

Milian, on the same conceptual trade: **mean +0.48% (not significant), median
−17.69%.**

The agent's flag, which is fair: on a peaked-at-zero, fat-tailed distribution a
t-stat of −95.7 is implausible unless the sample is enormous *and* the exit
convention is systematically costly. The gap is most likely **holding period,
option tenor, and mid-vs-touch pricing** rather than a disagreement about the
world.

**ACTION ITEM — audit the −35.03% before building on it.** Note the direction of
the discrepancy: our number may be measuring the cost of our own exit convention
as much as the volatility risk premium. Added to the testing queue.

---

## Testable strategies

1. **Milian AvgEA−Implied cross-sectional straddle book.** Long top-quintile
   straddles, short bottom-quintile, ≥20 names per side, hold to weekly expiry.
   **The decisive test:** re-run 2018–2025 with realistic fills, not mid-quotes.
   Pre-registered hypothesis: most of the 14.2% disappears at 12.6% spreads. *If
   the short leg alone survives costs, that is the finding.*
2. **GXZ pre-announcement vega capture.** Buy ATM straddle T−3, exit at close
   T−0, never hold through. Assume decay until proven otherwise.
3. **Sell into concave IV curves** — defined risk only (iron condor/credit
   spread, never naked).
4. **Left-tail bear spreads** on high left-tail-risk firms.
5. **FDA overpricing test** — measure implied vs realised stratified by market
   cap; check whether the 7.6% crash tail exceeds collected premium. **Do not
   trade before measuring.**

## Caveat

Search infrastructure was degraded (web search budget exhausted, OpenAlex budget
exhausted mid-task, SSRN/Cambridge/MDPI Cloudflare-blocked). Full text obtained
on the two most important papers, but **exact table values from Alexiou et al.
were not retrieved** — only the abstract's qualitative claims verbatim. If that
paper becomes load-bearing, retrieve it properly.

## Sources

Gao/Xing/Zhang *JFQA* 2018 (doi:10.1017/s0022109018000285) · Milian *JRFM* 2023
(doi:10.3390/jrfm16050270, open access) · Chen/Gan/Vasquez *JFQA* 2024 ·
Alexiou et al. *Review of Finance* 2025 (doi:10.1093/rof/rfaf016) ·
Kelly/Pástor/Veronesi *JF* 2016 · Greenwood & Sammon *JF* 2024 ·
Mitchell & Pulvino *JF* 2001 · Augustin/Brenner/Subrahmanyam *Mgmt Sci* 2019 ·
Bryzgalova/Pavlova/Sikorskaya *JF* 2023
