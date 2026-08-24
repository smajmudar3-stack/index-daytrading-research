# Short-Volatility / Short-Premium Blowups — Sourced Record and Loss Sizing

Compiled 2026-08-06. Every number below carries a source URL and the date/period it refers to.
Sources that are selling a strategy, trading education, or litigation services are flagged **[INTERESTED PARTY]**.

Price/index data throughout is taken from the index owner's own published history files:

- Cboe VIX daily OHLC — https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv
- Cboe SPX daily close — https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv
- Cboe PUT / BXM / CNDR strategy indices — same path, `PUT_History.csv`, `BXM_History.csv`, `CNDR_History.csv`
- Nikkei 225 daily OHLC — https://indexes.nikkei.co.jp/nkave/historical/nikkei_stock_average_daily_en.csv
- Henry Hub / WTI front-month futures settlements — EIA (from NYMEX): https://www.eia.gov/dnav/ng/hist_xls/RNGC1d.xls , https://www.eia.gov/dnav/pet/hist_xls/RCLC1d.xls

---

## PART 1 — THE ACTIONABLE PART: loss as a multiple of credit collected

This is the framing that matters for a $2,000–$5,000 account. "Vol spiked" is not sizing information.

### 1.1 Undefined-risk short premium (short strangle) — model estimate

Short 16-delta SPX strangle, 30 calendar DTE at entry, marked to the crash.
Black-Scholes, S = Cboe SPX close, ATM vol = Cboe VIX close, linear SPX put skew.
**This is a model estimate, not a quoted price.** Real losses were worse, because skew steepened far more
than a linear skew model allows and bid/ask blew out exactly when you needed to close.

| Episode | Entry | Credit | Worst mark | Sessions to worst | **Loss ÷ credit** |
|---|---|---|---|---|---|
| Feb 2018 Volmageddon | 2018-01-26, SPX 2872.87, VIX 11.08 | 0.61% of spot | 2018-02-08 | 9 | **10.1×** |
| Mar 2020 COVID | 2020-02-19, SPX 3386.15, VIX 14.38 | 0.79% of spot | 2020-03-23 | 23 | **35.5×** |
| Aug 2024 yen carry | 2024-07-31, SPX 5522.30, VIX 16.36 | 0.90% of spot | 2024-08-05 | 3 | **4.0×** |
| Oct–Nov 2008 (context) | 2008-09-19, SPX 1255.08, VIX 32.07 | 1.75% of spot | 2008-11-20 | 44 | **15.8×** |

Intermediate marks for Mar 2020 (same position): **9.8× by 2020-02-28 (7 sessions)**, 16.6× by 03-09,
26.5× by 03-12, 30.0× by 03-16. You do not get to wait it out — margin arrives first.

### 1.2 Single-session / 0DTE short strangle — model estimate

Sold at the prior close, marked at the next close. ATM vol = VIX, which *overstates* the credit for a
1-day option in calm markets, so the true multiples are **higher** than shown.

| Session | Prev VIX | SPX move | **Loss ÷ credit** |
|---|---|---|---|
| 2018-02-05 | 17.31 | −4.10% | **19.4×** |
| 2020-03-12 | 53.90 | −9.51% | 12.8× |
| 2020-03-16 | 57.83 | −11.98% | 16.2× |
| **2024-08-05** | 23.39 | −3.00% | **7.3×** |
| 2025-04-04 | 30.02 | −5.97% | 15.2× |
| 2008-10-15 | 55.13 | −9.03% | 11.4× |

Note 2018-02-05: a **−4.10% day** produced a **19× credit** loss on a 1-day strangle. The single-session
multiple is *worse* than the 30-day multiple for the same event, because the credit is tiny relative to gap risk.

### 1.3 Defined-risk (credit spreads / iron condors) — structural, not episode-dependent

Max loss per position is fixed by construction: `max loss ÷ credit = (width − credit) ÷ credit`.

| Credit as % of width | Max loss ÷ credit |
|---|---|
| **7.2%** | **12.9×** ← the case under discussion |
| 10% | 9.0× |
| 15% | 5.7× |
| 20% | 4.0× |
| 25% | 3.0× |
| 33% | 2.0× |
| 50% | 1.0× |

**This is the single most important line for a $2k–$5k account.** Defined risk converts an unbounded
10–35× tail into a known 3–9×. The blowup risk that remains is (a) holding many correlated positions that
all max out on the same day, and (b) position sizing that lets one max-loss day cost many months of credit.

### 1.3b How often does a 6.4%-OTM monthly spread actually reach max loss?

**Claim under test:** five episodes since 2007 (2008, Feb 2018, Mar 2020, Aug 2024, Apr 2025) took a
6.4%-OTM monthly spread to max loss ≈ **one every 3.8 years**; and Feb 2018 and Aug 2024 needed only
**−10.2%** and **−8.5%** moves, not crashes.

**The move sizes: CONFIRMED exactly.** Cboe SPX closes, peak-to-trough:

| Episode | Peak | Trough | Move | Sessions |
|---|---|---|---|---|
| Feb 2018 | 2018-01-26 2872.87 | 2018-02-08 2581.00 | **−10.16%** | 9 |
| Aug 2024 | 2024-07-16 5667.20 | 2024-08-05 5186.33 | **−8.49%** | 14 |
| Mar 2020 | 2020-02-19 3386.15 | 2020-03-23 2237.40 | −33.92% | 23 |
| Apr 2025 | 2025-02-19 6144.15 | 2025-04-08 4982.77 | −18.90% | 34 |

**The frequency: REFUTED — it is roughly 3× more often than one every 3.8 years.**

Counting every trading day 1990–2026 where SPX fell more than 6.4% within the next 21 sessions
(minimum close in the window vs. entry close), and grouping runs into distinct episodes (90-day gap rule):

> **18 distinct episodes since 2007-01-01 over 19.6 years = one every ~1.1 years.**

The full list since 2007 — the ten in bold are the ones the five-episode count misses:

2008-09, **2009-06 (−7.1%)**, **2010-04 (−12.0%)**, **2011-02 (−6.4%)**, **2011-07 (−16.8%)**,
**2012-05 (−8.9%)**, **2012-10 (−7.4%)**, **2014-09 (−7.4%)**, **2015-07 (−11.4%)**, **2015-12 (−10.5%)**,
2018-01 (−10.2%), **2018-12 (−15.7%)**, **2019-05 (−6.8%)**, 2020-02 (−33.0%), **2022-08 (−13.0%)**,
2024-07 (−8.5%), 2025-03 (−13.7%), **2026-03 (−7.8%)**.

**Sizing implication:** at 12.9× credit and roughly one max-loss event every **1.1** years rather than every
3.8 years, the strategy needs ~13 clean winning cycles between hits just to break even, and it is getting
about 13 of them — before costs. The margin of safety the 3.8-year assumption implies does not exist.

**And a second, sharper finding — "touched" vs "settled" is the whole game.**

| Episode | Worst *settled* 21-session return | Worst *touched* (min close in window) |
|---|---|---|
| Feb 2018 | **−6.19%** (did NOT breach 6.4%) | **−10.16%** (breached) |
| Aug 2024 | −6.84% (barely breached) | −8.49% (breached) |

**A 6.4%-OTM monthly spread held blindly to expiry would have survived February 2018.** It only lost because
the position was marked, margined, or closed at the touch. This is the mechanism that converts a survivable
strategy into a blown-up account, and it is entirely a function of position size and margin, not of forecasting.
It also means backtests that only check the settlement price systematically understate the loss rate.

### 1.4 Real, sourced drawdowns — Cboe strategy indices (not models)

These are option-*writing* benchmarks, fully collateralized, no leverage. They are the floor, not the ceiling,
of what a leveraged retail seller experiences.

| Episode | PUT (ATM put-write) | BXM (ATM buy-write) | CNDR (iron condor) |
|---|---|---|---|
| Feb 2018 (01-26 → 02-08) | −7.64% | −7.72% | −4.71% |
| Mar 2020 (02-19 → 03-23) | **−28.92%** | **−30.23%** | −10.88% (trough 04-21) |
| Aug 2024 (07-31 → 08-05) | −4.84% | −4.96% | −3.23% (trough 08-07) |
| 2008–09 (05-19-08 → 03-09-09) | **−37.09%** | **−40.02%** | −5.62% |

Expressed in **months of collected credit** (median winning month: PUT +1.58%, CNDR +1.43%):

| Episode | PUT | CNDR |
|---|---|---|
| Feb 2018 | 4.9 months | 3.3 months |
| Mar 2020 | **18.4 months** | 7.6 months |
| Aug 2024 | 3.1 months | 2.3 months |
| 2008–09 | **23.5 months** | 3.9 months |

Worst single month, full history: PUT −17.65% (Oct 2008); BXM −15.01% (Oct 2008); CNDR −9.91% (Oct 1987).

### 1.5 Speed: how fast calm becomes maximum loss

| Episode | From | To | Sessions | SPX | VIX |
|---|---|---|---|---|---|
| Feb 2018 | 2018-01-26 (VIX 11.08) | 2018-02-08 (VIX 33.46) | **9** | −10.16% | ×3.02 |
| Feb 2018 (VIX peak) | 2018-01-31 (VIX 13.54) | 2018-02-06 (intraday 50.30) | **4** | −4.56% | ×2.21 |
| Mar 2020 | 2020-02-19 (VIX 14.38) | 2020-03-23 (VIX 61.59) | **23** | −33.92% | ×4.28 |
| Mar 2020 (VIX peak) | 2020-02-19 | 2020-03-16 (VIX 82.69) | **18** | −29.53% | ×5.75 |
| Aug 2024 | 2024-07-31 (VIX 16.36) | 2024-08-05 (intraday 65.73) | **3** | −6.08% | ×2.36 |
| 2008 | 2008-08-28 (VIX 19.43) | 2008-11-20 (VIX 80.86) | **59** | −42.15% | ×4.16 |

---

## PART 2 — Does a low VIX protect the seller? (the claim under test)

**Claim as received:** the ten worst IV-minus-realized inversions in 36 years all began with VIX in the
**14–17 range** — i.e. the tail hits when things look calmest, which would destroy the
"only sell premium when calm" heuristic.

**Short answer: the clustering is real and the conclusion survives, but the "all ten from VIX 14–17" part is
not what the data says — four of the ten began with VIX between 25 and 32.** The heuristic is destroyed anyway,
for a better reason: the tail multiple turns out to be roughly the same in every VIX regime (§ table 2 below).
Do not publish "all ten began at VIX 14–17"; it is checkable and wrong.

**Test.** For every trading day 1990-01-02 → 2026-08-05, compare the VIX close at entry against the
*subsequent* 21-trading-day annualized close-to-close realized volatility of SPX. Rank by (realized − implied).
Data: Cboe VIX_History.csv and Cboe SPX_History.csv.

### Result: CONFIRMED in part, REFUTED in part

**CONFIRMED — the clustering.** All ten of the ten worst 21-day inversions since 1990 have entry dates
between **2020-02-13 and 2020-03-04**. Not nine of ten. Ten of ten.

| Rank | Entry | VIX at entry | VIX percentile | Fwd 21d realized | RV − IV | RV ÷ IV |
|---|---|---|---|---|---|---|
| 1 | 2020-02-19 | 14.38 | 27.6th | 84.27 | +69.89 | 5.86× |
| 2 | 2020-02-14 | 13.68 | 22.9th | 83.28 | +69.60 | 6.09× |
| 3 | 2020-02-18 | 14.83 | 30.8th | 84.27 | +69.44 | 5.68× |
| 4 | 2020-02-20 | 15.56 | 35.6th | 84.69 | +69.13 | 5.44× |
| 5 | 2020-02-26 | 27.56 | 88.2nd | 95.87 | +68.31 | 3.48× |
| 6 | 2020-02-21 | 17.08 | 46.9th | 84.73 | +67.65 | 4.96× |
| 7 | 2020-02-24 | 25.03 | 82.8th | 92.46 | +67.43 | 3.69× |
| 8 | 2020-02-13 | 14.15 | 26.1st | 79.33 | +65.18 | 5.61× |
| 9 | 2020-02-25 | 27.85 | 88.8th | 92.60 | +64.75 | 3.33× |
| 10 | 2020-03-04 | 31.99 | 94.3rd | 94.28 | +62.29 | 2.95× |

Ranks 18–20 are 2008-09-12, 2008-09-16, 2008-09-25 (Lehman). Nothing else comes close.

**REFUTED — the "14–17" part, as stated.** Only **six** of the ten started from VIX 13.68–17.08. The other
four started from VIX **25.03–31.99**, i.e. the 83rd–94th percentile — already-panicking markets that then
got very much worse. The accurate statement is: *the six worst entries were from a VIX of 13.7–17.1, in the
23rd–47th percentile of history — squarely "calm" — and the remainder were from an already-elevated VIX.*

**The stronger, and more useful, finding — the heuristic fails in BOTH directions.** Conditioning the
forward 21-day inversion on the VIX quintile at entry:

| VIX quintile at entry | n | mean RV−IV | p99 RV−IV | worst RV−IV | worst RV÷IV |
|---|---|---|---|---|---|
| Q1  9.14–13.33 | 1838 | −2.64 | +13.54 | +18.72 | 2.53× |
| Q2 13.33–16.15 | 1838 | −3.14 | +15.84 | **+69.89** | **6.09×** |
| Q3 16.15–19.46 | 1838 | −4.46 | +13.27 | +67.65 | 4.96× |
| Q4 19.47–24.20 | 1838 | −4.41 | +24.56 | +36.09 | 2.67× |
| Q5 24.20–82.69 | 1838 | −5.61 | +44.66 | +68.31 | 3.69× |

As a **ratio** — which is what actually drives a fixed-credit seller's payout multiple:

| VIX quintile at entry | mean RV÷IV | p95 | p99 | max |
|---|---|---|---|---|
| Q1  9.14–13.33 | 0.78 | 1.27 | 2.16 | 2.53 |
| Q2 13.33–16.15 | 0.79 | 1.23 | 2.09 | **6.09** |
| Q3 16.15–19.46 | 0.75 | 1.17 | 1.81 | 4.96 |
| Q4 19.47–24.20 | 0.80 | 1.34 | 2.09 | 2.67 |
| Q5 24.20–82.69 | 0.81 | 1.27 | 2.31 | 3.69 |

Three things follow, and they are the operative conclusions:

1. **The variance risk premium is positive in every regime.** Mean RV−IV is negative (−2.6 to −5.6 vol points)
   in all five quintiles. Sellers get paid on average whether VIX is 10 or 40. So "wait for high VIX to sell"
   does not improve your average edge either.
2. **In ratio terms the tail is essentially regime-independent.** Mean RV÷IV is 0.75–0.81 across all five
   quintiles and p99 is 1.8–2.3× across all five. **The VIX level tells you almost nothing about your
   worst-case multiple of credit.** This destroys both heuristics — "only sell when calm" *and*
   "only sell when vol is rich."
3. **The very lowest quintile is not where the catastrophe lives — the second and third are.** Q1's worst
   outcome in 36 years is 2.53×; Q2's is 6.09× and Q3's is 4.96×. **Caveat: this is driven entirely by a
   single episode (Feb 2020), so the quintile ranking of the maximum is n=1 and should not be over-read.**
   The defensible version: a VIX in the low-to-mid teens has produced the worst realized-vol shock on record,
   and offers no observable protection relative to a VIX of 25.

**Practical translation.** You cannot time your way out of this with a VIX filter. The only controls that
survive the data are (a) defined risk, which caps the multiple at 3–13×, and (b) position size such that a
simultaneous max-loss across every open position is survivable.

**Consistent with the measured spread data.** The finding that SPY option spreads widen only ~1.15× going from
VIX<15 to VIX>40 fits this record and I would state it as mutually corroborating: the damage in every episode
here came from the **gap**, not from liquidity evaporating. Evidence — on 2018-02-05 SPX fell 4.10% in a single
session and a 1-day strangle lost ~19× credit; on 2024-08-05 a 3.00% session cost ~7.3×. Neither number needs
any spread widening to arise; they are pure repricing. The one place liquidity genuinely did vanish was the
VIX-futures complex in the last 5 minutes of 2018-02-05 (BIS: 115,862 VIX futures traded in the single minute
at 16:08, "roughly one quarter of the entire market" — https://www.bis.org/publ/qtrpdf/r_qt1803t.htm), which
is a different market from listed SPX/SPY options, where Cboe reported trading stayed orderly.

### Corroborating: CNDR has been a long-running loser — CONFIRMED

Cboe S&P 500 Iron Condor Index, from Cboe's own history file:

- **2009-12-31: 774.79 → 2019-12-31: 720.17 = −0.73%/yr over 10.0 years.** (Claim received was −0.70%/yr; the
  small difference is endpoint convention. Confirmed.)
- Over the same decade SPX price-only returned +11.23%/yr (1115.10 → 3230.78).
- Longer window: 2005-12-30 601.11 → 2026-08-05 800.06 = +1.40%/yr over 20.6 years.
- Max drawdown: −19.82% (1987-07-28 → 1987-10-19).

By contrast Cboe PUT returned +7.33%/yr over 2010–2019 — so the loser is specifically the *condor*
(short both wings, defined risk, small credit), not short premium generally.

---

## PART 3 — The episodes, with sources

### 3.1 February 5, 2018 "Volmageddon"

**VIX** (Cboe VIX_History.csv):

| Date | Open | High | Low | Close |
|---|---|---|---|---|
| 2018-01-31 | 14.23 | 14.44 | 13.41 | 13.54 |
| 2018-02-02 | 13.64 | 17.86 | 13.64 | **17.31** |
| 2018-02-05 | 18.44 | **38.80** | 16.80 | **37.32** |
| 2018-02-06 | 37.32 | **50.30** | 22.42 | 29.98 |

- **2018-02-02 → 2018-02-05: 17.31 → 37.32 = +20.01 points, +115.60%.**
- **Still the largest one-day percentage rise in VIX history** as of 2026-08-05. Next largest:
  2024-12-18 +74.04%; 2024-08-05 +64.90%; 2007-02-27 +64.22%.
- Prior all-time closing low: **9.14 on 2017-11-03**.

**SPX** (Cboe SPX_History.csv): 2018-02-02 2762.13 → 2018-02-05 **2648.94 = −113.19 points, −4.10%**.
Prior all-time closing high 2872.87 on 2018-01-26; trough 2581.00 on 2018-02-08 = **−10.16% in 9 sessions**.
Dow −1,175.21 points on 2018-02-05, then the largest point drop in history — https://www.npr.org/sections/thetwo-way/2018/02/05/583325123/

**XIV (Credit Suisse VelocityShares Daily Inverse VIX Short-Term ETN, CUSIP 22542D795):**

Primary — Credit Suisse media release, 2018-02-06, filed as Exhibit 99.1 to Form 6-K:
https://www.sec.gov/Archives/edgar/data/1053092/000095010318001572/dp86358_ex9901.htm

> "Because the intraday indicative value of XIV on February 5, 2018 was equal to or less than twenty percent
> of the prior day's closing indicative value, an acceleration event has occurred."

- Closing indicative value **2018-02-02: $108.3681** (stated in the release).
- Accelerated valuation date **2018-02-15**; acceleration date **2018-02-21**; last trading day expected 2018-02-20.
- Follow-up release 2018-02-14 (Nasdaq suspension/delisting):
  https://www.sec.gov/Archives/edgar/data/1053092/000095010318002069/dp86855_ex9901.htm
  Nasdaq suspended trading after the close on 2018-02-15 under Listing Rule 5710(k)(iv)(C)(2)(c).
- **Final cash payment: $5.99 per ETN**, based on the closing indicative value on 2018-02-15.
- Closing indicative value 2018-02-05: **$4.2217** (Credit Suisse's revised figure) — i.e. **−96.10%** in one day.

Prospectus acceleration language, January 29, 2018 Pricing Supplement, PS-28:

> "If the **price of the underlying futures contracts** increases by more than 80% in a day, it is extremely
> likely that the Inverse ETNs will depreciate to an Intraday Indicative Value or Closing Indicative Value
> equal to or less than 20% of the prior day's Closing Indicative Value and will be subject to acceleration…"

Source for the CIV/prospectus detail and the after-hours trading analysis: Securities Litigation & Consulting
Group, "Material Misrepresentations in XIV's Prospectus Led to $700 Million in Losses," 2018-03-12 —
https://www.slcg.com/files/research-papers/Material%20Misrepresentations%20in%20XIV%20Prospectus%20Led%20to%20$700%20Million%20in%20Losses.pdf
**[INTERESTED PARTY — SLCG is a securities-litigation consulting firm that works for plaintiffs.]**
Its factual tables (VIX futures settlements 2/2 vs 2/5: Feb contract $15.625 → $33.225, Mar $14.975 → $27.975,
weighted average $15.2025 → $29.8125 = **+96.1%**) are reconcilable against Cboe settlement data.
Its damages claims (investors paid ~$823.6M for 28.8M shares after 4:15pm at an average $28.60, transferring
~$700M) are litigation positions, not findings.

**Conflicting figures on XIV's loss — note the difference:**
- **−96.1%** = closing indicative value 2/2 → 2/5. This is the economically correct number.
- **−84%** = BIS Quarterly Review, March 2018 — https://www.bis.org/publ/qtrpdf/r_qt1803t.htm ("XIV fell 84%
  and the product was subsequently terminated"). This appears to be a market-price measure.
- XIV's regular-session close on 2018-02-05 was ~$99, so headline "close-to-close" figures understate it badly.
  The collapse happened between 16:00 and 17:11.

**XIV assets:** BIS puts leveraged and inverse volatility ETPs at **"about $4 billion at end-2017"**
(https://www.bis.org/publ/qtrpdf/r_qt1803t.htm). A DGV Solutions note hosted by Cboe puts short-volatility ETP
assets at **$3.7bn on 2018-01-31 falling to ~$525M by 2018-02-06**, with XIV alone at roughly $1.9bn on
2018-01-31 (chart, sourced to Bloomberg). **UNRESOLVED to the dollar** — I could not find a Credit Suisse
filing stating XIV's notes outstanding on 2018-02-02.

**SVXY (ProShares Short VIX Short-Term Futures ETF):**

Primary — ProShares 8-K Exhibit 99.1, 2018-02-26:
https://www.sec.gov/Archives/edgar/data/1415311/000119312518059052/d503117dex991.htm

> "ProShares Short VIX Short-Term Futures ETF (NYSE Arca: SVXY) will change its investment objective to seek
> results (before fees and expenses) that correspond to one-half the inverse (-0.5x) of the Index for a single
> day. The Fund's investment objective currently is to seek results … that correspond to the inverse (-1x)…"

- Announced **2018-02-26**, effective **close of business 2018-02-27**. UVXY simultaneously cut 2x → 1.5x.
- Confirmed in ProShares Trust II Form 10-K for FY2018:
  https://www.sec.gov/Archives/edgar/data/1415311/000119312519060564/d611404d10k.htm
- Same 10-K: SVXY per-Share NAV **2018 high $552.74 on 2018-01-11**, **2018 low $15.85 on 2018-02-05**
  (both retroactively adjusted for the 1-for-4 reverse split effective 2018-09-18) — **−97.1% high-to-low**.
  Full-year 2018 per-Share NAV change −91.7%.
- SVXY units held by non-affiliates as of 2018-06-30: **$525,972,000**.
- **CONFLICT / UNRESOLVED: the exact one-day NAV loss on 2018-02-05.** Press accounts give −89% to −91%;
  the 10-K's split-adjusted 2018 low implies worse. I could not source a ProShares statement of the
  2018-02-02 and 2018-02-05 struck NAVs. Do not quote a precise one-day SVXY figure without that.

**Regulatory response:**
- **SEC, 2020-11-13, Press Release 2020-282** — https://www.sec.gov/newsroom/press-releases/2020-282 —
  settled actions against American Portfolios Financial Services/American Portfolios Advisors, Benjamin F.
  Edwards & Company, Royal Alliance Associates, Securities America Advisors, and Summit Financial Group for
  unsuitable sales of **volatility-linked ETPs** between January 2016 and April 2020; **>$3 million** returned.
  First cases from the Enforcement Division's Exchange-Traded Products Initiative.
- No SEC or CFTC enforcement action was brought against Credit Suisse or ProShares over the February 2018 event.
- Private litigation: *Set Capital LLC v. Credit Suisse Group AG*, S.D.N.Y.; the Second Circuit vacated dismissal
  on 2021-04-27 and revived market-manipulation claims. Plaintiffs allege CS earned $475M–$542M.
  **[INTERESTED PARTY — the accessible write-ups are from Cohen Milstein, plaintiffs' counsel:
  https://www.cohenmilstein.com/case-study/chahal-v-credit-suisse-group-ag-et-al/ ]** Allegations only.

**Documented retail losses:** the widely-repeated story of a former Target manager who made millions shorting
volatility was published by Business Insider in mid-2017 (i.e. *before* the blowup) and is referenced in the
DGV/Cboe note below. **UNRESOLVED** — I did not verify a news-of-record account of his February 2018 losses.

**Flagged source used above:** "After the Volpocalypse," DGV Solutions LP, 2018-02-12, hosted at
https://cdn.cboe.com/resources/education/research_publications/after-the-volpocalypse-market-observation.pdf
**[INTERESTED PARTY — DGV Solutions sells option-writing strategies; the note's conclusion is that the episode
"sets up well for option writing strategies going forward."]** Its factual content (VIX +115.6%; XIV/SVXY short
~280,000 VIX futures ≈ $280M vega on 2018-02-02; XIV $6.51 at end-2011 → $134.44 at end-2017; Cboe BXM −4.66%
and PUT −4.76% in the week of Feb 5 vs SPX −5.10%) is checkable; its recommendations are marketing.

### 3.2 LJM Preservation & Growth Fund (LJMIX / LJMAX / LJMCX)

Strategy: writing out-of-the-money puts and calls on **S&P 500 futures**.

**Primary — SEC Form N-Q, portfolio as of 2018-01-31**, filed 2018-04-02:
https://www.sec.gov/Archives/edgar/data/1552947/000158064218001814/ljmnq.htm

- **NET ASSETS 2018-01-31: $805,194,558.**
- Written options: puts premiums received $73,886,601 (fair value $46,559,725); calls premiums received
  $21,308,326 (fair value $15,084,000). Total written-option premiums received **$95,194,926**.
- Written put strikes ran from 2160 to 2680 on Feb/Mar/Jun 2018 S&P 500 futures — deep OTM against an SPX of
  ~2820 at the time. Notional across written puts was in the tens of billions.

**Liquidation — primary, Form 497 supplements:**
- 2018-02-07: fund **closed to all new investments** effective 2018-02-07 —
  https://www.sec.gov/Archives/edgar/data/1552947/000158064218000690/ljmpresgrwth497s.htm
- 2018-02-27: Board approved a Plan of Liquidation; fund **"liquidated and dissolved on or about March 29, 2018"** —
  https://www.sec.gov/Archives/edgar/data/1552947/000158064218001068/ljm497.htm

**SEC enforcement — primary:**
- **Press Release 2021-89, 2021-05-27** — https://www.sec.gov/newsroom/press-releases/2021-89
- **Complaint**: *SEC v. Anthony Caine, Anish Parvataneni, LJM Funds Management Ltd. and LJM Partners Ltd.*,
  **No. 1:21-cv-02859 (N.D. Ill., filed 2021-05-27)** —
  https://www.sec.gov/files/litigation/complaints/2021/comp-pr2021-89.pdf
- **Litigation Release No. 26338, 2025-07-01** —
  https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26338

Allegations, quoting the complaint:
- ¶111: "In early February 2018, over two consecutive trading days, Friday, February 2nd and Monday, February 5th,
  the S&P 500 Index fell more than 6%. During the same period of time, **VIX increased 177%**."
- ¶112: "At the close of trading on Monday, February 5, 2018, the futures commission merchant for the P&G Fund
  and the Private Funds **ordered the liquidation of all remaining positions** in order to meet margin
  requirements… trading losses of **more than $1 billion, or approximately 80% of their value**."
- ¶43: AUM grew "from around $450 million in February 2016 to approximately **$1.3 billion in February 2018** —
  including **more than $800 million in the P&G Fund**."
- ¶116–119: Caine received >$15M in distributions during 2017–2018 and **extracted more than $5 million after
  the losses**, including a $2,425,000 dividend from LJM Management and $1,550,000 from LJM Partners on
  **2018-02-16**, one week after investors were wiped out.

**Outcome (Litigation Release 26338):** final judgments by consent entered **2025-06-30**, no admissions.
- LJMFM and Caine, jointly and severally: disgorgement **$1,720,317** + prejudgment interest **$699,129**
- LJM Partners and Caine, jointly and severally: disgorgement **$1,567,713** + prejudgment interest **$637,112**
- Parvataneni: disgorgement **$512,724** + prejudgment interest **$208,368**
- Civil penalties: **Caine $500,000**, **Parvataneni $200,000**
- Caine enjoined 3 years, Parvataneni 1 year, from managing/advising third-party securities investments.
- Separately settled: CRO **Arjuna Ariathurai** — associational bar with right to reapply after 3 years,
  disgorgement + interest **$97,444**, civil penalty **$150,000** (Press Release 2021-89).
- **Parallel CFTC actions** against LJM, Caine, Parvataneni and Ariathurai were announced the same day
  (2021-05-27). **UNRESOLVED** — I could not retrieve the CFTC release/case numbers this session.

**NAV per share, Feb 2018 — UNRESOLVED.** The reported "−56% over two days / −80%+ total, $10.34 → $1.94"
figures trace to investor-recovery law firm blogs **[INTERESTED PARTY]**, e.g.
https://www.investorlawyers.com/blog/ljm-preservation-growth-fund-losses/ . The SEC complaint's
"**more than $1 billion, or approximately 80% of their value**, over two trading days" is the sourced statement.
Also reported (same interested sources): AUM fell to ~$9.8M by early March 2018.

### 3.3 OptionSellers.com / James Cordier — November 2018

Strategy: **naked short call options on natural gas futures** (plus short puts on crude), in individually
managed customer accounts cleared at INTL FCStone.

**The price move — primary, EIA (NYMEX front-month settlements):**

Henry Hub natural gas, contract 1 (https://www.eia.gov/dnav/ng/hist_xls/RNGC1d.xls):

| Date | Settle |
|---|---|
| 2018-10-31 | $3.261 |
| 2018-11-12 | $3.788 |
| **2018-11-13** | **$4.101** |
| **2018-11-14** | **$4.837** |
| 2018-11-15 | $4.038 |
| 2018-11-19 | $4.700 |

- **2018-11-14: +$0.736 = +17.95% in one session** (matches the "18%" in contemporaneous reporting).
- 2018-11-12 → 2018-11-14: **+27.7%**. 2018-10-31 → 2018-11-14: **+48.3%**.
- Then −16.5% on 2018-11-15 — the whipsaw that finished the accounts.

Simultaneously WTI front-month (https://www.eia.gov/dnav/pet/hist_xls/RCLC1d.xls) fell
**2018-11-12 $59.93 → 2018-11-13 $55.69 = −7.08% in one session**, and 2018-10-30 $66.18 → 2018-11-13 = −15.9%.
Short calls on gas and short puts on crude blew up in the same 48 hours.

**The losses:**
- **290 clients.** CNBC, 2018-11-21 —
  https://www.cnbc.com/2018/11/21/a-risky-natural-gas-bet-gone-awry-leads-to-weepy-youtube-confessional.html
  ("a money manager named James Cordier tells his 290 clients…"). Confirmed independently by Institutional
  Investor, 2020-05-13 ("OptionSellers.com managed money for 290 individuals").
- **2018-11-15: OptionSellers emailed customers under the subject "Catastrophic Loss Event"**, saying all their
  money was lost and they could owe more to INTL FCStone (CNBC, above).
- **Clients owed debit balances — they lost more than 100%.** Institutional Investor, 2020-05-13, quoting
  attorney John Chapman: *"Not only did everybody lose 100 percent of their investment, they were also hit with
  margin debt calls equal to about a third of their investment"* — i.e. roughly **−133% of capital**.
  https://www.institutionalinvestor.com/article/2bsx4k0wcflzwsbz26i9s/culture/remember-wall-streets-viral-laughingstock-optionseller-com
- **Total losses "exceed $100 million"** per Chapman (same article). **[Chapman is plaintiffs' counsel —
  INTERESTED PARTY.]** The widely-circulated **"$150 million"** figure traces to
  https://beststockstrategy.com/optionsellers/ **[INTERESTED PARTY — a trading-education seller]** and
  **I could not corroborate $150M from any news of record.** Use ">$100M, per plaintiffs' counsel."
- INTL FCStone's own statement (CNBC, 2018-11-21): *"Although well collateralized, accounts managed by a
  Commodities Trading Advisor, Optionsellers.com, had to be liquidated as a result of these moves. Liquidation
  of these accounts was in accordance with our customer agreements and our obligations under market regulation
  and standards."*

**The apology video:** posted circa 2018-11-19 (Bloomberg's story ran 2018-11-19; CNBC's 2018-11-21),
~10 minutes, "rogue wave" / "I'm sorry for not managing our ship and keeping her afloat." Viewed >500,000 times.

**Regulatory / legal outcome:**
- **UNRESOLVED — I found no CFTC or NFA enforcement action against James Cordier or OptionSellers.com Inc.**
  NFA BASIC and CFTC SIRT were not machine-accessible this session. Do not assert a case number.
- What is documented: clients pursued **NFA arbitration** against INTL FCStone, which counterclaimed for the
  debit balances plus interest and attorney's fees (Institutional Investor, 2020-05-13). Chapman's firm alone
  represented ~110 former investors. At least one claimant died before restitution. Cordier did not declare
  bankruptcy.

### 3.4 March 2020 — COVID

**VIX** (Cboe VIX_History.csv):

| Date | Open | High | Low | Close |
|---|---|---|---|---|
| 2020-02-19 | 14.66 | 14.74 | 14.21 | 14.38 |
| 2020-03-12 | 61.46 | 76.83 | 59.91 | 75.47 |
| **2020-03-16** | 57.83 | 83.56 | 57.83 | **82.69** |
| 2020-03-17 | 82.69 | 84.83 | 70.37 | 75.91 |
| 2020-03-18 | 69.37 | **85.47** | 69.37 | 76.45 |

- **82.69 on 2020-03-16 is the highest VIX close in history** (verified against the full 1990–2026 file).
- **But the all-time intraday high is 89.53 on 2008-10-24**, not a 2020 print. March 2020's intraday max was
  85.47 on 2020-03-18. Sources that call 2020 "the highest VIX ever" without qualifying close-vs-intraday are wrong.

**SPX** (Cboe SPX_History.csv): closing peak **3386.15 on 2020-02-19** → closing trough **2237.40 on 2020-03-23**
= **−33.92% in 23 trading sessions**. Single sessions: −9.51% (2020-03-12), −11.98% (2020-03-16).

**Allianz Global Investors U.S. — Structured Alpha (the big one). Primary:**
- **SEC Press Release 2022-84, 2022-05-17** — https://www.sec.gov/newsroom/press-releases/2022-84
- **Settled order against AGI US: Exchange Act Rel. No. 34-94927 / Advisers Act Rel. No. IA-6027,
  Admin. Proc. File No. 3-20855, 2022-05-17** — https://www.sec.gov/litigation/admin/2022/34-94927.pdf
- Companion orders 34-94925 (Taylor, AP 3-20853) and 34-94926 (Bond-Nelson).
- Complaint (S.D.N.Y.) — https://www.sec.gov/litigation/complaints/2022/comp-pr2022-84.pdf

From the settled order, which AGI US **admitted** (§III):
- **17 unregistered private funds**, **approximately 114 institutional investors**, **~$11 billion AUM as of
  December 2019**. Strategy: "purchase and sell options principally on the S&P 500 Index."
- "The Structured Alpha Funds performed well until the COVID-related market volatility in March 2020 when they
  suffered catastrophic losses, **including losses in excess of 90% in certain funds**."
- AGI US received **$550.3 million in fees**; **$146.6M** in revenue-share/direct costs; **net profit $403.7M**
  (most recent 5 years: $315.2M).
- Marketed capacity limit of **$9 billion** was exceeded by **over $3 billion** (>$12bn utilization at Dec 2019).

From Press Release 2022-84:
- Investors **lost over $5 billion**; AGI US and Allianz SE paid **over $5 billion in restitution**, plus
  **more than $1 billion to settle SEC charges**: **$315.2M disgorgement + $34M prejudgment interest +
  $675M civil penalty** (disgorgement/interest deemed satisfied by DOJ payments).
- The falsified-risk-report examples: a market-crash loss changed from **−42.1505489755747% to
  −4.1505489755747%** (dropping the digit "2"), and a daily loss from **−18.2607085709004% to
  −9.2607085709004%** (halving the "18").
- **Parallel DOJ criminal case, U.S. Attorney SDNY, 2022-05-17. AGI US, Taylor and Bond-Nelson pleaded guilty.**
  AGI US automatically disqualified from advising US registered funds for 10 years.
- *United States v. Tournant*, S.D.N.Y., filed 2022-05-16 (confirmed via CourtListener docket).
  Gregoire Tournant **pleaded guilty on 2024-06-07**; DOJ release:
  justice.gov/usao-sdny/pr/chief-investment-officer-allianz-global-investors-us-pleads-guilty-investment-adviser
  (justice.gov blocked automated retrieval this session; the URL and date are from search metadata —
  **verify the sentence imposed before quoting it**).
- The widely-cited **"$7 billion"** loss figure is *not* what the SEC says. The SEC's numbers are
  "**over $5 billion**" lost and "**over $5 billion**" in restitution. Prefer the SEC's.

**Ronin Capital LLC — CME clearing member failure. Primary:**
CME Group Form 8-K dated 2020-03-20, filed 2020-03-24 —
https://www.sec.gov/Archives/edgar/data/1156375/000119312520083311/d885506d8k.htm and Ex-99.1
https://www.sec.gov/Archives/edgar/data/1156375/000119312520083311/d885506dex991.htm

> "On March 20, 2020 … CME Clearing completed an auction of portfolios of Ronin Capital, LLC ('Ronin').
> Though Ronin was a direct clearing member, it did not handle customer business. … there was **no impact to
> the guaranty fund** of Chicago Mercantile Exchange Inc. nor were there any customers or clearing members
> impacted." Press release: "**The firm was unable to meet its capital requirements going forward.**"

Ronin was widely reported to have been short volatility. The 8-K does not say so — it only states the capital
failure. **Do not attribute the cause to short vol on the strength of the CME filing.**

**Infinity Q — primary:**
- **SEC Press Release 2022-29, 2022-02-17** — https://www.sec.gov/newsroom/press-releases/2022-29 —
  charged James Velissaris (CIO/founder, Infinity Q Capital Management) with **overvaluing assets by more than
  $1 billion** from at least 2017 through February 2021 by "altering inputs and manipulating the code of a
  third-party pricing service." Collected **>$26 million** in profit distributions.
- "at times during the pandemic, the funds' **actual values were half of what investors were told**."
- Redemptions in the Infinity Q Diversified Alpha mutual fund were suspended by SEC order
  **Investment Company Act Rel. No. 34198 (2021-02-22)**. Parallel SDNY criminal and CFTC actions.
- Note: this is a **valuation fraud** on a variance-swap/options book, not a clean short-vol margin blowup.

**Malachite Capital Management — UNRESOLVED.** Malachite (a New York short-volatility/options fund) was
reported to have closed after March 2020 losses. I found **no SEC enforcement action, no EDGAR filing, and no
federal court docket** for it, and Bloomberg/Reuters/FT were not retrievable this session.
**Do not publish a loss figure or a closure date for Malachite without a Bloomberg or Reuters citation.**

**Retail brokerage / tastytrade / Robinhood reporting on option-seller losses in March 2020 — UNRESOLVED.**
Not sourced this session.

### 3.5 August 5, 2024 — yen carry unwind

**VIX** (Cboe VIX_History.csv):

| Date | Open | High | Low | Close |
|---|---|---|---|---|
| 2024-08-01 | 16.20 | 19.48 | 15.95 | 18.59 |
| 2024-08-02 | 20.52 | 29.66 | 20.01 | **23.39** |
| **2024-08-05** | 23.39 | **65.73** | 23.39 | **38.57** |
| 2024-08-06 | 33.71 | 34.77 | 24.02 | 27.71 |

- **Intraday high 65.73 vs prior close 23.39 — a ×2.81 intraday spike.**
- **Close 38.57 = +64.90% vs 2024-08-02**, the **third-largest one-day VIX rise on record** (after
  2018-02-05 +115.60% and 2024-12-18 +74.04%).
- **The 65.73 print is substantially a quote artifact.** Note the printed open of exactly 23.39 — identical to
  the prior close — which is the signature of a stale/rolled-over opening value; the 65.73 occurred in the
  first minutes when a large fraction of SPX option series had not opened and VIX was being computed from wide,
  one-sided, and in some cases stale quotes. The gap between the 65.73 intraday high and the 38.57 close, with
  no corresponding SPX move (SPX fell only 3.00% that day), is the evidence. **Flag: I am characterizing the
  mechanism from the data pattern; I did not retrieve a Cboe statement to that effect this session.**
  Treat 65.73 as a quoted index value, not as tradable 30-day implied vol.

**SPX** (Cboe SPX_History.csv): 2024-08-02 5346.56 → 2024-08-05 **5186.33 = −160.23 points, −3.00%**.
From 2024-07-31 (5522.30): −6.08% in 3 sessions.

**Nikkei 225** (Nikkei Inc. daily history file):

| Date | Close | High | Low |
|---|---|---|---|
| 2024-08-01 | 38,126.33 | 38,781.56 | 37,737.88 |
| 2024-08-02 | 35,909.70 | 37,471.52 | 35,880.15 |
| **2024-08-05** | **31,458.42** | 35,301.18 | 31,156.12 |
| 2024-08-06 | 34,675.46 | 34,911.80 | 32,077.33 |

- **2024-08-05: −4,451.28 points = −12.40%.** Confirmed exactly.
- 2024-08-02: −5.81%. Two-day 2024-08-01 → 2024-08-05: **−17.5%**.
- Peak 42,224.02 (2024-07-11) → 31,458.42 = **−25.50% in 16 sessions**.
- **2024-08-06: +10.23%**, the largest one-day gain — which is precisely why a seller who was margin-called
  out on 08-05 could not recover: the position was gone before the snapback.

**Short-vol products and 0DTE sellers:** Cboe PUT −4.84% and BXM −4.96% (2024-07-31 → 2024-08-05); CNDR −3.23%
(trough 2024-08-07). A 1-day 16-delta strangle sold at the 08-02 close lost **≈7.3× credit** by the 08-05 close
(model, §1.2) — and considerably more if marked at the morning lows.
**No documented fund blowups sourced this session — UNRESOLVED.** Unlike 2018 and 2020, August 2024 produced
no publicly identified short-vol fund failure that I could verify. That itself is informative: the episode was
one session deep, and single-session shocks kill leveraged sellers without killing collateralized ones.

### 3.6 2008 and earlier

**VIX** (Cboe VIX_History.csv):

| Date | High | Close |
|---|---|---|
| 2008-10-24 | **89.53** (all-time intraday high) | 79.13 |
| 2008-10-27 | 81.65 | 80.06 |
| **2008-11-20** | 81.48 | **80.86** |
| 2008-11-21 | 80.74 | 72.67 |

**80.86 on 2008-11-20 confirmed** as the highest VIX close of the 2008 crisis, and the highest ever until
2020-03-16 (82.69).

**SPX drawdown 2007–2009** (Cboe SPX_History.csv): closing peak **1565.15 on 2007-10-09** → closing trough
**676.53 on 2009-03-09** = **−56.78% over 355 trading sessions**. **Confirmed to the reported −56.8%.**

**Karen "the Supertrader" Bruton — SEC action. Primary:**
- **SEC Litigation Release No. 23551, 2016-06-01** —
  https://www.sec.gov/enforcement-litigation/litigation-releases/lr-23551
- *SEC v. Hope Advisors, LLC and Karen Bruton (Defendants) and Just Hope Foundation (Relief Defendant)*,
  **Civil Action No. 1:16-cv-01752-LMM (N.D. Ga.)**, filed **2016-05-31**.

**The allegations are not "her strategy blew up" — they are that she hid the losses to keep earning fees:**
> "…in order to circumvent the funds' fee structure under which the firm is entitled to fees only if the funds'
> profits that month exceed past losses, Hope Advisers and Bruton have been **orchestrating certain trades that
> enable the funds to realize a large gain near the end of the current month while basically guaranteeing a
> large loss to be realized early the following month**."

- Funds: Hope Investments LLC and HDB Investments LLC, **>$175 million NAV**.
- "The scheme has enabled Hope Advisers to **avoid realization of more than $50 million in losses** in the hedge
  funds while earning millions of dollars in fees to which they were not entitled."
- "Without the fraudulent trades, Hope Advisers would have received **almost no incentive fees since October 2014**."
- Interim consent order froze **$7 million** of their own investments and barred further fees below the high-water mark.
- **Outcome:** docket terminated **2018-06-14**; a Fair Fund was established and finally terminated by court
  order **2024-05-14** (CourtListener docket 6370699, entries 155–156).
  **UNRESOLVED — I could not retrieve the final judgment amounts.**
- **[FLAG: Bruton was heavily promoted through tastytrade/tastylive video content as a retail short-strangle
  role model. That promotion is trading-education marketing, and it substantially predates and outlasts the
  SEC's finding that the strategy had accumulated >$50M of losses being rolled forward. Anyone citing her
  track record is citing a number the SEC alleged was manufactured.]**

**Catalyst Hedged Futures Strategy Fund (HFXAX). Primary:**
- **SEC Press Release 2020-21, 2020-01-27** — https://www.sec.gov/newsroom/press-releases/2020-21
- "the fund **lost hundreds of millions of dollars – approximately 20% of its value – from December 2016 through
  February 2017** as markets moved against it."
- CCA "breached those parameters and failed to take the required corrective action during a majority of the
  trading days between December 2016 and February 2017."
- Portfolio manager **Edward Walczak** "told investors that the fund employed a risk management strategy
  involving **safeguards to prevent losses of more than 8%**, when in fact no such safeguards limited losses."
- **Settlement:** Catalyst Capital Advisors LLC + CEO Jerry Szilagyi paid **$10.5 million combined** —
  CCA disgorgement **$8,176,722** + prejudgment interest **$731,759** + civil penalty **$1,300,000**;
  Szilagyi civil penalty **$300,000**; paid into a Fair Fund. Litigated action against Walczak in W.D. Wis.
  Parallel CFTC actions the same day.

**Victor Niederhoffer (1997 and 2007) — UNRESOLVED.** Niederhoffer's funds are documented to have been
destroyed twice by short-put exposure (Refco liquidation, October 1997, after the Asian-crisis SPX drop; and
Matador Fund, September 2007). I could not retrieve a news-of-record source this session. **Do not publish
figures for these without a WSJ/Bloomberg/FT citation.**

---

## PART 4 — What the record actually supports

1. **The multiple, not the move, is the number to size on.** A −4.10% day (2018-02-05) cost a 1-day strangle
   **19× credit**. A −3.00% day (2024-08-05) cost **7.3×**. Nothing about "it was only down 3%" is comforting.
2. **Undefined risk has no bound.** OptionSellers clients lost **~133% of capital** — 100% plus a debit balance
   of roughly a third — and were then pursued for interest and attorney's fees. This is the only category in
   the record where the loss exceeded the account.
3. **Defined risk converts the tail from 10–35× into a known number.** That is the entire argument for it.
   At 7.2% of width you cap at 12.9× — which is barely an improvement on the undefined-risk Feb 2018 number
   of 10.1×. At 20% of width you cap at 4×; at 33% you cap at 2×. **Defined risk with too thin a credit is
   not meaningfully safer than naked; the protection comes from the credit-to-width ratio, not from the
   word "defined."**
3b. **The max-loss event arrives about once every 1.1 years, not once every 3.8.** Eighteen distinct episodes
   since 2007 took SPX more than 6.4% below its level within 21 sessions. At 12.9× credit that is roughly
   break-even before costs.
4. **Speed beats conviction.** Feb 2018: 9 sessions from all-time high to −10%; 4 sessions from VIX 13.54 to a
   50.30 print. Aug 2024: 3 sessions. You will not "manage" your way out; you will be margin-called out, and in
   Aug 2024 the market gained 10.23% (Nikkei) the very next day, after the sellers were already gone.
5. **The VIX level is not a risk filter.** Mean RV÷IV is 0.75–0.81 and p99 is 1.8–2.3 in *every* VIX quintile
   since 1990. The worst 21-day inversion in 36 years started from **VIX 13.68**, at the **23rd percentile**.
   Selling only when calm, and selling only when rich, are both unsupported.
5b. **"Held to expiry" and "held through the month" are different strategies.** A 6.4%-OTM monthly spread
   settled at −6.19% in Feb 2018 — inside the strike — but *touched* −10.16%. Whether you lost depended
   entirely on whether your size let you sit through the mark. Size for the touch, not the settle.
6. **The iron condor specifically has been a loser for a decade.** CNDR **−0.73%/yr for 2010–2019** while SPX
   returned +11.23%/yr. Short premium is not the problem; the *condor's* credit-to-width ratio is.
7. **Every fraud in this record has the same shape.** LJM, Allianz Structured Alpha, Catalyst, Hope Advisors,
   Infinity Q — in each case the strategy's real tail was concealed rather than hedged: falsified stress tests
   (LJM), digit-dropped risk reports (Allianz), a fictitious 8% loss limit (Catalyst), month-end loss-rolling
   (Hope), manipulated pricing code (Infinity Q). **When a short-vol track record looks too smooth, the most
   common explanation in the enforcement record is that the losses were being hidden, not avoided.**

## Open items / do not publish without further sourcing

| Item | Status |
|---|---|
| SVXY exact one-day NAV loss 2018-02-05 | CONFLICT: press −89% to −91%; 10-K split-adjusted low implies worse |
| XIV assets outstanding at 2018-02-02 | ~$1.9bn (Bloomberg-sourced chart); no issuer filing found |
| OptionSellers total client losses | ">$100M" (plaintiffs' counsel). "$150M" traces only to a trading-education seller |
| CFTC/NFA action vs Cordier or OptionSellers.com | None found. Do not assert a case number |
| CFTC case numbers for the LJM parallel actions | Announced 2021-05-27; numbers not retrieved |
| Malachite Capital Management | No SEC/EDGAR/court record found; needs Bloomberg or Reuters |
| Tournant sentence imposed | Guilty plea 2024-06-07 confirmed via metadata; sentence not verified |
| Hope Advisors/Bruton final judgment amounts | Docket terminated 2018-06-14; Fair Fund closed 2024-05-14; amounts not retrieved |
| Niederhoffer 1997 / Matador 2007 figures | Not sourced |
| Business Insider "Target manager" Feb 2018 losses | Not sourced (the 2017 profile predates the blowup) |
| Retail broker (tastytrade/Robinhood) reporting on Mar 2020 seller losses | Not sourced |
| Aug 2024 short-vol fund failures | None found |
