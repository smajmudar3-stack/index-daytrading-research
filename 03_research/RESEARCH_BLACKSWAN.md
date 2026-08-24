# Buying Cheap Far-OTM Options as a Positive-Skew Strategy: Literature Review

**Date:** 2026-08-15
**Question:** Is the *mean* return of far-OTM long option buying positive net of costs, and can selection make it positive?
**Scope note:** The owner has explicitly accepted a negative median. Nothing below argues against the skew. Everything below is about the **mean**.

---

## TL;DR

Theory is on the strategy's side; the data is not, and the gap is the whole story.

- Coval & Shumway (2001) prove far-OTM **calls should have the highest expected returns in the cross-section**. Ni (2008) finds they are **negative**, and *decreasing* in strike. This inversion is the literature's central puzzle and it is the strategy's problem.
- **The most on-point number in the review — Duarte, Jones & Wang (*JF* 2024): heavily traded deep-OTM calls on individual stocks average −116 basis points PER DAY.** That is the strategy's exact instrument, restricted to liquid names so it is not an illiquidity artifact. Roughly −5.7%/week, −22%/month.
- **The direct test of event convexity — Dubinsky, Johannes, Kaeck & Seeger (*RFS* 2019): buying a straddle into earnings and holding THROUGH the announcement returns −7.96%, t = −13.25, negative in 16 of 16 years** — and *worse than buying one on a random day*. Implied earnings-day vol 8.22% vs realized 7.42%: scheduled-event vol is systematically over-priced.
- **Boyer & Vorkink (*JF* 2014): 10–50% per WEEK** between low- and high-ex-ante-skewness option portfolios, at midpoint pricing. High skewness = far OTM + short dated = the exact target cell. An independent replication puts high-skew two-week puts at **−54%** (t = 7.738).
- **Bali & Murray (*JFQA* 2013)** strip out delta and vega and the penalty survives — so it is **not a leverage artifact**.
- **Barberis & Huang (*AER* 2008)** supply the mechanism: probability weighting makes skewed securities overpriced with **negative expected excess return by construction**. This is a demand story, not a risk story, so it will not decay.
- Costs in the exact cell are decisive: far-OTM buckets carry **28–62% quoted / 12–29% effective** spreads, sub-$250 tickets **23.7% / 10.8%**. At $0.01–$0.05 quotes the tick alone is a ~67% spread. Break-even requires `p × M ≥ 1/(1−c)` — a 2% hit rate needs a **~57× average winner** just to clear costs.
- **Nothing conditions it positive.** Seven candidates were tested and **not one clears t ≥ 4 with costs applied to the long leg** — see §5.4 and verdict (b). Notably, "IV rank" has **zero peer-reviewed literature**; Goyal–Saretto's effect collapses to **t = 0.56** in high-spread names at full execution cost and is sign-flipped on a decade-longer sample by Zhan et al. (*RFS* 2022) at t ≈ 7–10; and the pre-earnings straddle result **excludes the announcement jump** and goes to **−0.67% (t = −1.06)** once weighted by where the open interest actually sits.
- **Jump arrival is not forecastable.** Andersen–Bollerslev–Diebold: jump components carry "**no predictive power**" for next-day volatility, and jump occurrence tests i.i.d. Jump timing is predictable only from the **public calendar** — which options already price. Nothing forecasts a jump's *sign*.
- The strongest cost-robust conditioning variable (Muravyev 2016, order imbalance) says **buy what customers are selling** — the reverse of this strategy.
- Third-party evidence on real tail funds: the **CBOE Eurekahedge Tail Risk Hedge Fund Index ≈ −2%/yr since 2008, ≈ −8%/yr in the 2010s**, likely survivorship-inflated. **Universa's numbers have no independent verification.**

**Verdict: negative expectancy, robustly. Not a close call.** The honest framing is a consumption budget, not an investment sleeve. §9 gives the least-bad construction if it is run anyway.

---

## 0. The strategy, stated fairly

Spread ~$100 across many ~$1 contracts on different underlyings. Deliberately choose far-OTM strikes on names judged likely to make a large move that implied vol has not priced. Accept a win rate in the low single-digit percents. Rely on one large winner to cover many total losses.

**This is a coherent strategy, and standard asset-pricing theory is on its side.** Coval & Shumway (2001, *JF* 56:983–1009) prove that under mild assumptions (a positive market risk premium and a monotone pricing kernel), **expected call returns exceed those of the underlying security and increase with the strike price.** A far-OTM call is the most levered possible claim on the underlying; its beta is enormous; CAPM says it should have the *highest* expected return of any instrument on that name. If the owner's intuition is that far-OTM calls should have a large positive mean, that intuition is the textbook prediction.

The entire adverse literature below exists precisely because **the data does the opposite of what theory predicts.** That contradiction is the subject of this review.

---

## 1. The documented mean return of far-OTM long options

### 1.1 The headline number: this is a puzzle with a name

**Ni, "Stock Option Returns: A Puzzle" (2008, sample 1996–2005, OptionMetrics).** The central finding is in the title's premise: **average returns to out-of-the-money stock calls are negative.** This directly contradicts Coval–Shumway, under which they should be the highest positive returns in the cross-section. Ni attributes it to idiosyncratic volatility and skewness — i.e. to exactly the lottery characteristic the strategy is buying.

**The single most on-point number found in this review. Duarte, Jones & Wang, "Very Noisy Option Prices and Inference Regarding the Volatility Risk Premium," *Journal of Finance* 79(5), 2024, 3581–3621.** Verbatim from the abstract:

> "The stylized fact that volatility is not priced in individual equity options does not withstand scrutiny. First, we show that the average return of **heavily traded deep out-of-the-money call options on stocks is −116 basis points per day.** ... Third, the mean return of heavily traded **delta-hedged at-the-money calls (puts) is −23 (−30) basis points.** Fourth, the variance risk premium in stock options is negative. Our analysis highlights the importance of **microstructure biases** and robustness in empirical work with options."

This is the strategy's exact instrument — deep-OTM **calls** on individual **stocks**, and restricted to the **heavily traded** ones, so it is not an illiquidity artifact — and the measured mean is **−116 bp per day**. Over a one-week holding period that compounds to roughly **−5.7%**; over a month, roughly **−22%**. Note the provenance: the paper began life as a *critique* of the option-anomaly literature, and its methodological point is that microstructure noise had been making equity-option returns look **better** than they are.

Its companion — **Duarte, Jones, Khorram, Mo & Wang, "Too Good to Be True: Look-Ahead Bias in Empirical Options Research," *RFS* 2026** — finds that apparent option "good deals" arise partly from **look-ahead bias** in the standard OptionMetrics filter cascade (using information unavailable at formation to drop "noisy" observations), warns that "elevated Sharpe ratios may serve as potential indicators of such look-ahead biases," and concludes that "only a small set of stock characteristics are in fact associated with option expected returns." This is a general discount factor on every in-sample option-return result cited anywhere in this document, including the favourable ones.

**Bondarenko (2003), via the survey literature:** on the S&P 500 index, average ATM put returns are **−40% per month** and **deep-OTM put returns are −95% per month.**

**Boyer & Vorkink, "Stock Options as Lotteries," *Journal of Finance* 69(4), 2014, 1485–1527.** Verbatim from the published abstract:

> "We find, consistent with recent theory, that total skewness exhibits a strong negative relationship with average option returns. **Differences in average returns for option portfolios sorted on ex ante skewness range from 10% to 50% per week, even after controlling for risk.** Our findings suggest that these large premiums compensate intermediaries for bearing unhedgeable risk when accommodating investor demand for lottery-like options."

Key details:
- **Data:** OptionMetrics (Ivy DB), individual equity options, from 1996.
- **Unit:** *per week*, not per month or per year. A 10–50% weekly spread is an annihilating rate of decay.
- **Direction:** the effect runs the wrong way for this strategy. **High ex-ante skewness = far OTM + short dated = the exact cell the strategy targets = the worst returns.**
- **Coverage:** the effect is present in *both* call and put markets, so it is not a crash-insurance story. It is a lottery-preference story.
- **Gross or net:** returns are computed from OptionMetrics quote data at/near the midpoint. They are **before** the spreads documented in §2. Net returns are worse.
- **Mechanism:** the premium is *paid to intermediaries* for absorbing retail lottery demand. The strategy proposes to be on the paying side of that transfer.

**Independent replication.** Wang (Bocconi field paper, *The Cross-Section of Equity Option Returns*) reconstructs the Boyer–Vorkink ex-ante skewness measure with a different (closed-form, parametric) estimator and reproduces the result on 29 DJIA names. For **puts expiring in two weeks**, the actual average hold-to-maturity return falls monotonically from **−17% (low skewness bin) to −54% (high skewness bin)**, paired **t = 7.738**. Wang's summary: "individual equity option investors give up average returns on the order of **50% monthly** for exposure to the lottery opportunities that options with high ex ante skewness offer."

So the answer to (a), in one line: **the documented mean hold-to-expiration return on the far-OTM, short-dated, high-skewness cell is roughly −50% per month before costs**, with the loss rate accelerating as you go further OTM and shorter dated.

### 1.2 The skewness effect is not a leverage artifact

The obvious objection to §1.1 is that OTM options are levered, so of course their returns are extreme; sorting on skewness might just be sorting on delta.

**Bali & Murray, *JFQA* 48(4), 2013, 1145–1171** kill this objection by construction. Verbatim from the abstract:

> "We investigate the pricing of risk-neutral skewness in the stock options market by creating skewness assets comprised of two option positions (one long and one short) and a position in the underlying stock. The assets are created such that **exposure to changes in the underlying stock price (delta), and exposure to changes in implied volatility (vega) are removed, isolating the effect of skewness.** We find a strong negative relation between risk-neutral skewness and the skewness asset returns, consistent with a positive skewness preference. The returns are not explained by well-known market, size, book-to-market, momentum, short-term reversal, volatility, or option market factors."

With delta and vega stripped out, skewness still earns a strongly negative return. **The penalty is attached to the skewness itself, not to the leverage.** This is the single most important paper for the owner's purposes, because it removes the "I'm just being paid for beta" defence.

### 1.3 The mechanism that makes this negative by construction

**Barberis & Huang, "Stocks as Lotteries," *AER* 98(5), 2008, 2066–2100.** Verbatim:

> "Our main result, derived from a novel equilibrium with nonunique global optima, is that, in contrast to the prediction of a standard expected utility model, **a security's own skewness can be priced: a positively skewed security can be 'overpriced' and can earn a negative average excess return.**"

The mechanism is the probability-weighting component of cumulative prospect theory: investors overweight small probabilities. A security offering a 2% chance of a 30× payoff gets valued as though that chance were 8%. In equilibrium the security is bid above its expected discounted payoff and therefore has a **negative expected excess return by construction.** Barberis & Huang explicitly list out-of-the-money options among the applications.

This matters because it is not a risk story that might reverse. It is a *demand* story: as long as there is a population of investors who overweight tails, the assets that deliver tails will be bid to negative expected returns. The strategy's edge would have to come from being right about *which* tail, in a market where every other tail-buyer is bidding the same instruments up.

Corroborating evidence for the same mechanism in adjacent asset classes:
- **Bali, Cakici & Whitelaw, "Maxing Out," *JFE* 99(2), 2011, 427–446.** Stocks with high maximum daily returns over the past month (the MAX lottery proxy) earn significantly negative alphas, on the order of **−0.51% to −1.17% per month**.
- **Eraker & Ready, *JFE* 2015.** OTC stock returns are "extremely negative on average" with a "highly positively skewed" distribution — most go to zero, a few do spectacularly. They find the Barberis–Huang model plausibly rationalises it. This is the *exact* payoff profile the strategy is trying to construct, in a market where it has been measured, and the mean is deeply negative.

### 1.4 The honest counter-argument: is skewness "priced," or is this just what options do?

Fairness requires flagging the best available rebuttal. Wang (Bocconi, above) replicates the Boyer–Vorkink pattern in real data but then simulates option returns under a β-Heston model (stochastic volatility, market factor, **no skewness preference at all**). The simulated portfolios reproduce the same monotone decline across skewness bins, with even higher t-statistics, and the simulated and actual distributions are **not statistically distinguishable**. His conclusion: "we cannot reject the null that skewness is not priced in the cross-section of individual equity option returns."

Similarly, **Broadie, Chernov & Johannes (2009)** show that for index options, average returns, CAPM alphas and Sharpe ratios of deep-OTM puts are **statistically insignificant** when benchmarked against a properly specified option-pricing model rather than against zero — option returns are so non-normal that standard t-tests badly overstate significance.

**Why this does not help the strategy.** Both critiques argue about *why* far-OTM options lose money — behavioural mispricing vs. fair compensation for jump and volatility risk under a correctly specified model. Neither disputes *that* they lose money. If anything the rational-pricing interpretation is worse news for the owner: a mispricing can be arbitraged and can decay after publication, whereas a genuine risk premium is permanent and no amount of selection skill removes it. **On either reading, the mean is negative.**

---

## 2. Costs: the arithmetic that decides the question

Boyer–Vorkink's −10% to −50% per week is a *midpoint* number. The strategy as described would not trade at midpoints.

### 2.1 Measured spreads in exactly this cell

**Bryzgalova, Pavlova & Sikorskaya, "Retail Trading in Options and the Rise of the Big Three Wholesalers," *Journal of Finance* 78(6), 2023, 3465–3514.** Verbatim from the abstract:

> "Retail trading recently reached over 60% of total market volume. Nearly 90% of PFOF comes from three wholesalers. ... **Retail investors prefer cheaper, weekly options with average bid-ask spread of 12.6%, and lose money on average.**"

Their headline estimates: the aggregate portfolio of retail option trades over **November 2019 – June 2021** lost an average of **−$5.03 million per day at a 10-day horizon, totalling $2.1 billion**, with the bulk attributable to the *indirect* costs of trading rather than to directional error.

The 12.6% average spread is across *all* retail option trades, which are 72% at-the-money. The relevant number for this strategy is the far-OTM cell. From Table 1 of Amaya, Garcia-Ares, Pearson & Vasquez (2025), which reconstructs the same SLIM sample (frequency-weighted averages, moneyness for calls = (Price − Strike)/Strike, so more negative = further OTM):

| Moneyness bucket | Quoted spread | Effective spread |
|---|---|---|
| At the money | 9.23% | 4.02% |
| −1 to −0.1 (10%–100% OTM) | **28.10%** | **12.63%** |
| −2 to −1 (100%–200% OTM) | **52.80%** | **24.20%** |
| Below −2 (>200% OTM) | **61.84%** | **29.12%** |

And by trade size, which is what pins the ~$100-across-many-names structure:

| Trade size (dollars) | Quoted spread | Effective spread |
|---|---|---|
| Below $250 | **23.68%** | **10.84%** |
| $1,000–$2,500 | 6.81% | 2.66% |
| Above $50,000 | 3.02% | 1.15% |

The strategy sits in the worst cell of both tables simultaneously: sub-$250 tickets *and* far-OTM strikes. Effective spread (defined as 2×|trade price − midpoint|/midpoint) of **12–29%** means a one-way cost of **6–15% of premium**, and a round trip of **12–29%** for any position you actually close.

### 2.2 The tick-size problem, which is worse than the tables suggest

The strategy specifies **~$1 contracts**. At the standard 100 multiplier, "$1 per contract" means a quoted price of **$0.01**. This is the regime where minimum tick size dominates everything:

- In Penny Interval Program names, options under $3.00 quote in $0.01 increments. A $0.01/$0.02 market is a **67% quoted spread relative to the $0.015 midpoint**. Buying at the offer and the option expiring worthless is a −100% return; buying at the offer and selling at the bid with no move is **−50%**.
- In non-penny names, options under $3.00 quote in **$0.05** increments. A $0.05/$0.10 market is again a ~67% spread, and $0.10 is the *minimum* you can pay to enter.
- Commissions: at brokers charging $0.50–$0.65 per contract, that is **50–65% of a $1.00 premium each way**. Zero-commission brokers (Robinhood) remove this specific term; most do not.

(Increment conventions are the standard penny-interval vs. non-penny split and should be verified per option class. The magnitude does not rest on them: the measured 52.80% and 61.84% quoted spreads in the >100%-OTM buckets of Table 1 above are direct evidence of the same thing.)

There is no execution technique that rescues a 67% spread. The strategy is buying instruments whose *quoted* cost of round-tripping approaches the value of the instrument.

### 2.3 What the cost numbers do to the required hit rate

Take the strategy at face value: $100 spread across ~20 positions of ~$5 each (or 100 positions of $1). Assume the far-OTM sub-$250 cell, so a one-way execution cost of ~6% of premium entering and, on winners, ~6% exiting — call it 12% round trip, which is the *optimistic* end of Table 1 (it is 24–29% beyond 100% OTM).

For the portfolio to break even, the gross payoff multiple on winners must satisfy:

> `p × M = 1 / (1 − c)` where `p` = win rate, `M` = average gross multiple on winners, `c` = round-trip cost fraction

At c = 12%, you need `p × M ≥ 1.136`. At c = 25% (the >100%-OTM cell), you need `p × M ≥ 1.333`.

So a 2% hit rate requires an average winner of **~57×** just to break even on cost-adjusted fair value — and that is *before* the skewness premium, which the literature measures at 10–50% per week. The uncomfortable part is that the market already knows the distribution of M: the option price *is* the risk-neutral expectation of the payoff. Under a fair (risk-neutral) price with zero premium and zero costs, `p × M = 1` exactly. **Every basis point of spread and every basis point of skewness premium comes directly out of a quantity that starts at 1.00.** There is no slack in the identity. The only way to win is to have `p` or `M` genuinely higher than the market's estimate — which is question (b).

### 2.4 The best available cost counter-argument

**Muravyev & Pearson, "Options Trading Costs Are Lower than You Think," *RFS* 33(11), 2020, 4973–5014.** Verbatim:

> "Conventional estimates of the costs of taking liquidity in options markets are large. ... We resolve this puzzle by showing that options price changes are predictable at high frequency, and many traders time executions by buying (selling) when the option fair value is close to the ask (bid). **Effective spreads of traders who time executions are less than 40% of the size of conventional measures**, and the overall average effective spread is one-quarter smaller than conventional estimates. These findings alter conclusions about the after-cost profitability of options trading strategies."

This is real and should be taken seriously — but note what it requires: a **high-frequency fair-value model** and patient execution timing on each order. It applies to liquid options and to traders with the infrastructure to run it. It does not convert a 67% penny-quoted spread on an illiquid far-OTM weekly into a tradeable cost. Used correctly, it is an argument for *how* to trade, not *whether* the mean is positive.

---

## 3. Does the retail evidence actually show losses? A live dispute

Intellectual honesty requires reporting that the BPS loss finding is **contested**, and by serious people.

**Amaya, Garcia-Ares, Pearson & Vasquez, "New Evidence on the Performance of Customer Options Trades" (April 2025), supported by a data grant from the Cboe Options Institute.** They argue BPS's losses are substantially a measurement artifact, on two grounds:

1. **Expiration values vs. quote midpoints.** BPS compute hold-to-expiration performance using the NBBO midpoint at the last trade before expiry, not the actual expiration value. Because a worthless option still has a strictly positive offer, and deep-ITM soon-to-expire options are quoted below intrinsic (Battalio, Figlewski & Neal 2020), this biases results. Correcting it moves held-to-expiration performance from **−$1.75m/day to +$0.36m/day**, and cuts 5- and 10-day-horizon losses by more than half, rendering them statistically insignificant.
2. **Trade direction.** BPS infer buy/sell with a quote rule. Against Cboe's actual trade-direction data, that rule **misclassifies 42.4% of trades and 42.6% of volume.** Using correct directions, customer SLIM trades show losses at only two horizons, with statistical significance only intraday. Held-to-expiration gains are **+$2.07m/day, t = 1.19** — i.e. **not statistically significant.**

**How much weight this deserves.** Some, but bounded:
- It is a working paper funded by an exchange whose revenue depends on retail option volume, rebutting a *Journal of Finance* paper. That is not disqualifying, but it is a disclosed interest.
- Its headline positive result is **statistically insignificant (t = 1.19)**, so the honest reading is "we cannot reject zero," not "retail makes money."
- The sample (Nov 2019 – Jun 2023) spans one of the strongest equity bull markets and the meme-stock era. An aggregate dollar P&L on a book that is **70% calls** during a period when the S&P went from 3,231 to 4,450 is close to a levered long-equity result, not evidence of an option-specific edge.
- The one horizon where losses remain large and highly significant is **intraday** — the shortest-dated, most lottery-like trading.
- Most importantly: **it says nothing about the far-OTM cell.** It is an aggregate across a book that is 72% ATM. The Boyer–Vorkink and Bali–Murray cross-sectional results, which *are* about the far-OTM cell, are untouched by it.

Separately, **Beckmeyer, Branger & Gayda (2023)** study retail 0DTE S&P 500 option trading (>75% of retail S&P option trades are 0DTE). Even though retail there receives meaningful price improvement that *reduces* effective spreads, **retail investors still experience substantial losses.**

---

## 4. Can SELECTION make the mean positive?

This is question (b), and it is the only place the strategy can be rescued. The strategy's premise is not "buy random far-OTM options" — it is "buy far-OTM options on names likely to make a large move that IV has not priced." So the question is whether any conditioning variable has credible evidence of flipping the sign.

### 4.1 The strategy's own stated selection rule points the wrong way

The strategy selects names *judged likely to make a large move* — in practice, high-volatility, newsy, low-priced, lottery-like names. Every one of those characteristics has been separately tested, and each predicts *lower* option returns:

- **Hu & Jacobs, "Volatility and Expected Option Returns," *JFQA* 55(3), 2020, 1025–1060.** Verbatim: "The expected return from holding a **call (put) option is a decreasing (increasing) function of the volatility of the underlying.** ... In the cross section of equity option returns, returns on call option portfolios **decrease** with underlying stock volatility ... It holds in various option samples with different maturities and moneyness." Buying calls on the highest-volatility names — the ones most likely to make a large move — is the *worst* systematic call selection rule tested.
- **Boulatov, Eisdorfer, Goyal & Zhdanov, "Cheap Options Are Expensive" (2021), sample 1996–2017.** Verbatim: "delta-hedged options on **low-priced stocks underperform those on high-priced stocks by 0.54% per week for calls and 0.34% for puts.**" 7-factor alphas of 0.44%/week (calls) and 0.29%/week (puts). Most of the spread comes from decile one — the lowest-priced stocks. They confirm it with two natural experiments: options become ~13% (calls) / 9% (puts) **more expensive** in the three days after a stock split, and mini-index options are overpriced 0.5% (calls) / 1.2% (puts) relative to identical regular-index options. They explicitly show the effect is **not** skewness preference — it is inattention/anchoring on nominal price — meaning it is an *additional*, orthogonal penalty stacked on top of the Boyer–Vorkink skewness penalty. Their strategy survives effective spreads up to 50% (40%) of quoted for calls (puts).
- **Bali, Cakici & Whitelaw MAX (§1.3)** — the underlying lottery stocks themselves underperform.

So the two most natural implementations of "names likely to make a big move" (high volatility, low nominal price) are both documented negative-return selection rules, over and above the skewness penalty.

### 4.2 The one conditioning variable with genuinely strong evidence — and it points against buying

**Muravyev, "Order Flow and Expected Option Returns," *Journal of Finance* 71(2), 2016, 673–708.** Verbatim:

> "I show that the inventory risk faced by market-makers has a first-order effect on option prices. ... While both components are large for option trades, the **inventory risk component is larger.** ... option order imbalances attributable to inventory risk have five times larger impact on option prices than previously thought. Finally, I find that **past order imbalances have greater predictive power than any other commonly used predictor of option returns.**"

This is the strongest single conditioning result in the equity-option literature, and it is the empirical counterpart of the Boyer–Vorkink mechanism. Options that **customers are buying** are pushed up and subsequently underperform; options that market-makers are long underperform less or outperform. Since far-OTM short-dated lottery calls on newsy names are precisely where retail buying pressure concentrates, this variable classifies the strategy's target instruments as **the expensive ones.**

The tradeable implication is contrarian and inverted: *buy the options nobody wants, not the ones everybody wants.* That is a real, well-evidenced signal — but it is not this strategy.

### 4.3 Informed option trading exists — but the retail side is the wrong side of it

There is a genuine literature showing option order flow contains information. **Pan & Poteshman, "The Information in Option Volume for Future Stock Prices," *RFS* 2006** (1,200+ citations) find option volume predicts underlying returns, concentrated in "stocks with higher concentrations of informed traders." This is the best case that *someone* can select far-OTM options profitably.

The problem is who. **Chang, Hsieh & Lai (2009, *JBF*)** decompose informed flow by investor class and find the buy option volume of **individual investors carries the incorrect sign** — retail flow predicts the underlying in the wrong direction. **Muravyev (2016)** attributes the bulk of option price impact to *inventory risk* rather than asymmetric information, i.e. most of what looks like informed flow is market-makers charging for absorbing demand. And **Bauer, Cosemans & Eichholtz (2009)** attribute individual option losses to "poor market timing that results from overreaction to past stock market returns."

The synthesis: informed option trading is real, it predicts moves, and it is *not* done by the retail cohort buying far-OTM weeklies. The strategy proposes to enter the one market where informed flow is best documented, on the side that is best documented to be uninformed, in the instruments with the highest spreads.

---

## 5. Conditional cheapness: does low IV / high HV-minus-IV predict positive long-option returns?

### 5.1 Goyal & Saretto — verified directly from the published paper

**Goyal & Saretto, "Cross-Section of Option Returns and Volatility," *JFE* 94(2), 2009, 310–326.** Sample **1996–2006**, 4,344 stocks, 75,627 monthly call/put pairs. Sort stocks on the difference between 12-month historical realized volatility (HV) and ATM implied volatility (IV); go long straddles where HV − IV is large positive, short where large negative.

**A prior analyst flagged this as probably a bid-ask artifact, citing a fall from 22.5% to 7.5%/month. I obtained the actual paper and read Table 7. The claim is directionally right and the numbers are worse than quoted.** Verified Table 7, Panel A (10−1 long-short straddle portfolio, monthly returns, t-stats in parentheses):

| Execution assumption | All | Low-spread options | High-spread options | Low volume | High volume |
|---|---|---|---|---|---|
| Midpoint | **22.7%** (10.41) | 19.5% (7.27) | **23.9%** (8.95) | 22.7% (8.83) | 20.7% (6.95) |
| Effective = 50% of quoted | 12.6% (5.98) | 13.0% (4.99) | 11.5% (4.51) | 11.0% (4.50) | 13.5% (4.65) |
| Effective = 75% of quoted | 8.3% (3.94) | 10.5% (4.07) | 6.5% (2.57) | 6.4% (2.62) | 10.7% (3.70) |
| **Effective = 100% of quoted** | **3.9% (1.84)** | 8.2% (3.17) | **1.4% (0.56)** | **1.7% (0.69)** | 8.1% (2.77) |

Verbatim from §5.2.1: "the average return decreases from 22.7% per month when trading at mid-point prices to 3.9% (statistically significant only at the 10% level) per month if we consider trading options at an effective spread equal to the quoted spread." And: "the before-cost profits are higher for illiquid options than for liquid options."

**Verdict on the artifact claim:** *Partly confirmed, with an important nuance.*
- **Confirmed:** the gross effect is *larger* in high-spread stocks (23.9% vs 19.5%) — the classic microstructure-artifact signature — and in that group it **collapses to 1.4% with t = 0.56, i.e. indistinguishable from zero**, once you pay the full quoted spread. Same in the low-volume group: 1.7%, t = 0.69.
- **Nuance the prior flag missed:** what *does* survive full costs is concentrated in the **liquid, low-spread** options — 8.2% (t = 3.17) and 8.1% (t = 2.77). That is not nothing. It is, however, below the t ≥ 4 bar this project demands, and it is a *relative* long-short result, not evidence that the long leg alone makes money.
- Goyal & Saretto also note margin requirements for the short leg are "roughly equal to one and a half times the cost of written options, which drives another wedge into the profitability."

### 5.1a The long leg alone — the number that actually answers the question

Goyal & Saretto's Table 3 decile returns (monthly, midpoint) let us isolate the *buy* side, which is all the strategy can implement:

- **Straddles:** D1 **−12.8%**, D2 −7.8%, D3 −5.7%, D4 −3.3%, D5 −1.8%, D6 −1.0%, D7 −0.2%, D8 +0.7%, D9 +2.7%, **D10 +9.9%**. Monthly Sharpe D1 −0.722, D10 +0.329 → over 132 months, t(D1) ≈ −8.3 but **t(D10) ≈ +3.78**.
- **Delta-hedged calls:** D1 −1.7% (t ≈ −9.8), **D10 +1.0% (t ≈ 2.24)**.

**The anomaly is roughly two-thirds short-side, and both long-leg t-statistics fall below 4** (3.78 and 2.24). Goyal & Saretto never report the D10 leg net of costs; the 10−1 spread decays by 18.8 percentage points under full quoted spread, implying roughly 9pp per leg — which would approximately annihilate the +9.9%.

For scale, from their own footnote: over the identical window the zero-beta S&P 500 ATM straddle averaged **−11.50%/month**.

### 5.1b The direct refutation on a longer sample

**Zhan, Han, Cao & Tong, "Option Return Predictability," *RFS* 2022 (hhab067).** Jan 1996 – Apr 2016, 244 months. Their Table 3 reports delta-neutral call **writing** returns for all ten deciles of every sort, and **every decile of every sort is significantly positive**, t ≈ 5 to 35.

Critically, one of their sorts *is* the Goyal–Saretto signal (−VOL_deviation). In **decile 1 — the cheapest-options bucket by GS's own metric** — writing still earns **+1.23%/month (t = 7.38)** stock-value-weighted, +1.77% equal-weighted (t = 9.74), +1.50% option-value-weighted (t = 5.55). Decile 10 earns +4.10% (t = 23.38).

Stated the other way round: **over 1996–2016, buying delta-hedged calls on the very stocks whose options were cheapest by the Goyal–Saretto metric lost roughly 1.2–1.8% per month gross, at t ≈ 7–10.** That is a ten-year-longer sample with a cleaner return convention, flatly contradicting GS's +1.0% (t ≈ 2.24) long leg. On costs, Zhan et al. find that at 100% of quoted spread 4 of 10 strategies die, while at OPRA-measured actual effective spread (≈55% of quoted) 9 of 10 survive — but again, all of these are **short-volatility** strategies.

**Why this does not support the strategy even if entirely real.** Three reasons, each independently sufficient:
1. It is **long-short**. A large part of the profit comes from *selling* the expensive straddles — and §5.1a shows the buy side alone is t < 4 gross and roughly zero net. The strategy has no short leg.
2. It is **ATM by construction**. The paper restricts moneyness to **0.975–1.025**, explicitly "because we do not want the option returns to be driven by the smile in the volatility surface." It says nothing about far-OTM strikes, and the authors deliberately excluded them.
3. It is a **cross-sectional relative** signal (which name's vol is mispriced relative to others), not a statement that options in general are cheap at any point in time.

### 5.2 Low IV rank / "options are cheap right now" — a hard null

**"IV rank" and "IV percentile" have zero peer-reviewed literature.** They are retail-platform constructs (tastytrade / thinkorswim lineage). Bibliographic search returns only practitioner books. Nothing has been tested.

The closest academic tests all fail, and the best-identified one runs the *other* way:

- **Goyal & Saretto themselves kill the level sort** (p. 316): "the average difference in the return of the extreme decile portfolios obtained by sorting only on the **levels of IV** or only on the levels of HV is often economically small and not statistically significant." Their signal is a *deviation* (HV − IV), not a level.
- **Cao & Han (*JFE* 2013, 108(1), 231–249) is decisive.** Jan 1996 – Oct 2009, 213,640 observations, ~1,514 stocks/month. Unconditional pooled mean delta-hedged ATM call return is **−0.81%** to month-end and **−1.13%** held to maturity. Of 6,141 stocks, **78% have negative average delta-hedged call returns; 32% significantly negative; ~1% significantly positive.** Sorting by volatility, the return to *selling* is positive in **every** quintile: by idiosyncratic vol, Q1 **+0.80% (t = 6.42)** rising monotonically to Q5 +2.20% (t = 9.62); by total vol, Q1 **+0.85% (t = 6.97)**. **There is no volatility quintile in which buying wins.** Low volatility shrinks the seller's edge; it never flips it.
- **The single "low vol is cheap" datapoint anywhere — Bakshi & Kapadia (*RFS* 2003)** — does not survive inspection. SPX 1988–1995, historical vol < 8%, one moneyness bucket: mean delta-hedged gain **+$0.11 (+5.64% of call price)**. But the **median in that same cell is −0.21 (−7.81%)**, the adjacent moneyness bucket is negative in both mean and median, and the authors report **no standard errors at all** ("The standard errors are small and therefore omitted"). Their robust finding is the monotone one: underperformance grows with the level of volatility.
- **The mechanics point the wrong way.** Bollerslev, Tauchen & Zhou report **corr(IV − RV, IV) = +0.86**: the seller's edge is mechanically *larger* when implied vol is high — the exact inverse of the retail "buy when IV rank is low" premise.
- **The VIX-level analogue is a clean null.** Aragon, Mehra & Wahal (*JPM* 2020), VIX futures 2004–2017, mean return **−4.90%/month**: regressing returns on the lagged VIX level gives **t = 0.26 to 1.14, adjusted R² ≤ 0.011** across every frequency and demeaning. Their conclusion: "Samuelson (1965) was right: VIX futures prices properly anticipate predictability in volatility, and are themselves unpredictable." Konstantinidi & Skiadopoulos (*JBF* 2016), using actual OTC S&P 500 variance-swap dealer quotes 1996–2009, find the coefficient on VIX level predicting **long**-variance-swap P&L is **negative in all 15 maturity/horizon cells** (t = −1.21 to −13.58) — higher VIX means *more negative* long-variance P&L — and after costs their VIX-timing model produced **negative Sharpe in 14 of 15 cells** and underperformed the naive always-short benchmark.

The cleanest conceptual statement of why remains **Israelov & Nielsen, "Still Not Cheap: Portfolio Protection in Calm Markets" (AQR, 2015)**: "buying an option is not a bet that realized volatility will increase; it is a bet that realized volatility will increase **above the option's implied volatility.**" Low IV is usually a correct forecast of low subsequent realized vol, not a discount. The variance risk premium (implied minus subsequent realized) is positive on average in essentially every sample and asset studied — Carr & Wu (2009 *RFS* 22(3), 1311–1341), Bollerslev, Tauchen & Zhou (2009 *RFS* 22(11), 4463–4492) — which is the same statement as "option buyers pay a premium on average."

The nearest thing to a conditional exception is **Dew-Becker, Giglio, Le & Rodriguez (2017)** (see §6.6): the premium is concentrated in *unexpected near-term* realized variance, and hedging *forward* variance at horizons of a quarter to 14 years was approximately **costless** — zero premium, not negative.

### 5.3 IV term structure and vol-of-vol — the best long-only candidate in the literature

**Vasquez (*JFQA* 2017)** is the single strongest long-only result found anywhere in this review. Jan 1996 – Jan 2012, ~516 stocks/month, ATM straddles held to maturity, sorted on IV term-structure slope (IV_long-term − IV_1-month):

| | P1 | … | P9 | **P10** | P10−P1 |
|---|---|---|---|---|---|
| Mean/mo | **−9.2%** | | +1.6% | **+7.3%** | **+16.5%** |
| t | −5.96 | | 0.73 | **3.50** | 10.02 |

**Its t is 3.50 — below the bar this project demands** — P9 is insignificant, and deciles 1–8 are all negative. Every reported alpha (t = 3.75 to 10.18) is for the long-*short*, never the long leg. The cost tables report long-short only: whole-sample at full quoted spread gives **+3.1%/month, t = 1.88 (insignificant)**, and the widest-spread quartile goes to **−10.2% (t = −3.48)**. Decisively, Vasquez's own Table 1 shows **P10 carries the widest bid-to-mid spread in the cross-section — 8.5% of option price**. Since P10 is entered at the ask and held to expiry, **the long leg's entire gross edge is approximately the size of its own bid-ask spread**, and it sits precisely in the spread quartile that turns negative. Subperiod returns decay (1996–2003 +19.0% vs 2004–2012 +14.0%) and it is untested after 2012.

Related term-structure work closes the escape hatch rather than opening it: **Aït-Sahalia, Karaman & Mancini (*J. Econometrics* 2020)** find "the term structure of IVRP is on average **downward sloping** … the longer the maturity, the **larger the negative** risk premium," with the ex-ante variance risk premium negative on virtually every day of the sample. **Asensio (*Quantitative Finance* 2020)**, 2006–2018, finds the VIX curve in contango **86% of the time**, with the long end yielding "negative returns, on average, for long positions"; **no net-long-volatility strategy is profitable in the paper.**

**Vol-of-vol** has the right sign and a useless magnitude. Park (*JFM* 2015) finds higher VVIX predicts lower subsequent tail-hedge returns (deep SPX put coefficient **t = −5.54**), but unconditional mean residual returns are **−5.38%/day** for deep SPX puts, and the arithmetic on his own tables implies breakeven requires VVIX **2.25–2.65 SD below its mean** for SPX puts (3.54 SD for VIX calls) — versus a historical *minimum* of −3.03 SD. In other words, the condition that would make buying profitable has essentially never occurred. His returns are also factor-residualized and non-tradeable, with no transaction-cost analysis. Huang, Schlag, Shaliastovich & Thimme (*JFQA* 2019) report VVIX² predictive t-stats of −2.29 to −4.43 (all but one below 4) and find delta-hedged gains negative in every S&P bin; their thesis is that the **price of vol-of-vol risk is negative**, i.e. low VVIX makes the buyer's loss smaller, never positive.

### 5.4 Every "buying options wins" candidate, and why each fails

| Candidate | Gross result | Why it fails |
|---|---|---|
| Goyal–Saretto D10 straddle | +9.9%/mo, t ≈ 3.78 | t < 4; costs never reported for the leg; ~9pp/leg drag; mechanism is short-term IV reversal; sign-flipped by Zhan et al. at t ≈ 7–10 |
| Goyal–Saretto D10 delta-hedged | +1.0%/mo, t ≈ 2.24 | t < 4; contradicted by Zhan et al. (−1.23%, t = 7.38) on a decade-longer sample |
| Vasquez P10 straddle (IV slope) | +7.3%/mo, **t = 3.50** | t < 4; gross edge ≈ its own 8.5% bid-ask spread; widest-spread decile; untested since 2012 |
| Park low-VVIX tail hedge | correct sign, t = −4.5 to −5.5 | breakeven needs VVIX below its historical minimum; non-tradeable residualized returns; zero cost analysis |
| Bakshi–Kapadia low-vol bin | +5.64% of call price | median in same cell −7.81%; adjacent bucket negative; **no standard errors reported** |
| Upside semivariance premium | −2.60 annualized (buyer-positive) | **no t-stats**; AR(1) 0.89 on overlapping data; **not a tradable instrument** |
| Cao–Han lowest-vol quintile | **−0.80%/mo to buyers, t = 6.42** | not a candidate — it is the refutation |

**Not one clears t ≥ 4 in-sample with costs applied to the long leg.**

### 5.5 What conditioning variables actually do survive

The equity-option predictability literature that survives realistic costs (Zhan/Han/Cao/Tong; Bali, Beckmeyer, Moerke & Weigert; Horenstein, Vasquez & Xiao 2026 *RFS*) is overwhelmingly about **delta-hedged** option returns, and the profitable side is overwhelmingly **short volatility**. Horenstein-Vasquez-Xiao identify four common factors in delta-hedged equity option returns — an equally weighted option factor, an HV-minus-IV factor, a cash-holdings factor, and a **vol-of-vol** factor — none of which is a "buy naked far-OTM options" signal.

The single strongest conditioning variable in the literature (Muravyev 2016, §4.2) says to buy what customers are *selling*. There is, on this review, **no conditioning variable with credible evidence of making naked far-OTM long option returns positive net of costs.**

---

## 6. Are far-OTM options ever systematically CHEAP? The tail-risk-premium literature

This is the strongest available line of defence for the strategy, so it gets the most careful treatment.

### 6.1 The one genuine "tails look cheap" result — and what it actually says

**Backus, Chernov & Martin, "Disasters Implied by Equity Index Options," *Journal of Finance* 66(6), 2011, 1969–2012.** From the NBER working-paper abstract (w15240), verified directly:

> "Option prices thus provide independent confirmation of the impact of extreme events on asset returns, **but they imply a more modest distribution of them.**"

And from the body: "option prices imply more modest disasters than the macroeconomic evidence suggests," and "the volatility smile is much steeper in the consumption-based model" than in observed option prices.

Their comparison table (option parameters from Broadie–Chernov–Johannes SVJ estimates on S&P 500 options, 1987–2003) against a Barro-type consumption-disaster calibration:

| | Barro-type consumption | Option-implied |
|---|---|---|
| Jump intensity ω (/yr) | 0.0100 | 1.3987 |
| Mean jump θ | −0.30 (8.6 SD) | −0.0074 (0.21 SD) |
| True skewness | −11.02 | −0.28 |
| True excess kurtosis | 145.06 | 0.48 |
| P(≤ −3 SD) | 0.0090 | 0.0081 |
| P(≤ −5 SD) | 0.0079 | **0.0001** |

**Read literally, this says a Barro-calibrated investor would pay *more* for deep-OTM index puts than the market charges.** That is the only tail-specific academic result pointing toward underpricing, and it deserves to be stated plainly.

**Why it does not convert into a trade — three reasons, two of which are the authors' own:**
1. At the ~3-SD (Great-Depression-scale) level the two columns **agree** (0.0081 vs 0.0090). The entire disagreement is at ≥5 SD — events that have never occurred in the sample.
2. **BCM themselves argue the option-implied column is the more credible one**, because its skewness/kurtosis (−0.28, 0.48) match actual US consumption data (−0.34, 1.11 for 1889–2009), whereas Barro's (−11.02, 145.06) do not. The natural reading is not "options are cheap" but "Barro's calibration is too extreme."
3. It is a claim about an unobservable physical distribution inside a power-utility model, not about realized P&L. It is a Peso-problem argument, and Peso arguments are unfalsifiable in sample by construction. Realized P&L is in §6.2 and it is decisive.

**And critically: this is about index puts and systemic disasters. It says nothing about single-stock far-OTM upside calls, which is what the strategy buys.**

### 6.2 What tail buyers actually earned

**Bondarenko, "Why Are Put Options So Expensive?" (*QJF* 4(3), 2014; WP 2003).** CME S&P 500 futures options, 08/1987–12/2000, N = 161 monthly holding periods:
- ATM put average excess return **−39%/month**; deep-OTM (k = 0.94) **−95%/month**. Negative and highly significant at every strike.
- Jensen's α for ATM puts **−23%/month**, significant at 1%.
- **Break-even for ATM put buyers requires October-1987-magnitude crashes 1.3 times per year.**
- Cumulative wealth transfer from buyers to sellers: **$17.8bn**.
- Even the subperiod 08/87–06/90 *containing the 1987 crash* gives −27% to −12%/month.
- Relevant aside: "Puts on individual stocks also appear overpriced, although to a lesser extent."

**Broadie, Chernov & Johannes (2009 *RFS* 22(11), 4493–4529).** S&P 500 futures options, 08/1987–06/2005, average monthly put returns by moneyness (0.94 / 0.96 / 0.98 / 1.00 / 1.02):
- **Returns: −56.8 / −52.3 / −44.7 / −29.9 / −19.0 %/mo**
- **t-stats: −3.9 / −4.2 / −4.2 / −3.3 / −2.6**
- CAPM α: −48.3 / −44.1 / −36.8 / −22.5 / −12.5 %/mo, t = −4.1 to −5.1

**Coval & Shumway (2001):** zero-beta ATM S&P 500 straddles lose **≈3% per week** (−3.15% average, 1990–1995).

**The BCJ critique, stated precisely and fairly.** BCJ benchmark against model-implied *expected* option returns via parametric bootstrap rather than against zero. Black-Scholes population EOR for 6%-OTM puts is already **−20.6%/mo** (SV model: −25.8%). Against that null, the observed −56.8% has p = 8.1% (BS) / 24.1% (SV). Their verbatim conclusion: "there is no evidence that OTM put returns are mispriced." **But note what this does and does not establish:** it kills statistical significance *only at the deepest OTM strike*, only against a null whose own expected return is −21% to −26% per month. All other strikes remain significant at p < 5%; ATM straddles (>15%/mo) and delta-hedged returns have p ≈ 0. **BCJ's finding is that deep-OTM puts lose about as much as a correctly specified model says they should — not that they make money.** Chambers, Foy, Liebner & Lu, "Index Option Returns: Still Puzzling" (*RFS* 27(6), 2014, 1915–1928) push back with 1987–2012 data, concluding the cost of OTM tail protection "may include a significant premium."

### 6.3 Universa / Spitznagel: is there independent verification?

**No.** There is no peer-reviewed paper, no audited public composite, and no third-party database entry.

- The March 2020 figure in Universa's investor letter is **+3,612% "return on invested capital"** — a return on the *deployed tail-hedge sleeve*, not on a hedged portfolio. Universa's typical mandate is ~3% of an investor's assets. (The +4,144% figure circulating in the press does not match the letter.)
- The only public assessment is journalistic: Aaron Brown, *Bloomberg Opinion*, 9 Apr 2020, "Universa's 3,612% Return Is Legit (But With an Asterisk)" — not peer-reviewed and explicitly caveated.
- *WSJ*, 21 Sep 2018: a 3.3% Universa + 96.7% passive S&P 500 portfolio compounded 12.3%/yr over the 10 years to Feb 2018. Self-reported by Universa; not independently verified.

### 6.4 The systematic third-party test: AQR on put buying vs trend

**Ilmanen, Thapar, Tummala & Villalon, "Tail Risk Hedging: Contrasting Put and Trend Strategies" (AQR, Jul 2020; *Journal of Systematic Investing* 1(1), Feb 2021).**

- The **CBOE Eurekahedge Tail Risk Hedge Fund Index** — the live peer group of actual tail-risk managers — returned **≈ −2%/yr since its 2008 inception and ≈ −8%/yr during the 2010s**, and since the index was only created in 2015, "survivorship bias may have boosted returns between 2008 and 2014."
- Their put backtest (buy 5% OTM 1-month S&P 500 puts, roll at expiry; Jan 1985–2020) shows persistently negative cumulative returns. **Six different OTM put specifications**, including 20% OTM 1-year delta-hedged, all share "the same pattern of persistent losses, interspersed by temporary spikes."
- On crisis efficacy: Put was profitable in 7 of 8 slow drawdowns and 10 of 10 fast ones; **Trend** in 6 of 8 and 9 of 10 — and Trend was up in **9 of the 10 worst S&P 500 months**. Conclusion: "the cost advantage favors Trend over Put."
- Directly relevant sanity check on headline tail-fund numbers: "even the levered OTM puts we study above did not exceed 50% monthly return in the worst equity months (nor did the Eurekahedge Tail Risk Index)." **Four-digit percentage returns are not a property of tail options as an asset class**; they require a tiny deployed notional base, extreme strike/leverage selection, or manager-specific alpha.
- **Israelov & Nielsen, "Still Not Cheap: Portfolio Protection in Calm Markets" (2015)** is the direct answer to "buy when IV is low": a low VIX does not mean good value, because "buying an option is not a bet that realized volatility will increase; it is a bet that realized volatility will increase **above the option's implied volatility**."
- **Ilmanen, *FAJ* 68(5), 2012:** "Selling insurance and selling lottery tickets have delivered positive long-run rewards in a wide range of investment contexts. Conversely, buying financial catastrophe insurance and holding speculative lottery-like investments have delivered poor long-run rewards." (Taleb published a dissenting comment, *FAJ* 69(2), 2013 — conceptual, about Peso problems and small-sample inference, not a competing dataset.)

### 6.5 Index vs single-stock: the strategy is in the worse market

The index put premium is well documented, but the single-stock skew premium genuinely differs — just not in the buyer's favour.

- **Bakshi, Kapadia & Madan (2003 *RFS* 16(1), 101–143):** individual-stock risk-neutral densities are "far less negatively skewed, and substantially more volatile" than the index.
- **Bollen & Whaley (2004 *JF* 59(2)):** demand pressure sits in **index puts** but in **single-stock calls**. "Index option abnormal returns decrease monotonically across exercise prices and are significant, while **stock option abnormal returns are symmetric, smaller, and insignificant.**"
- **Driessen, Maenhout & Vilkov (2009 *JF* 64(3), 1377–1406):** the index-vs-individual wedge is a **correlation risk premium**; harvesting it via dispersion earns alpha, but "realistic frictions prevent profitable exploitation."

So single-stock options are closer to fair than index options *on average* — but the far-OTM lottery end of single names is the actively overpriced part (§1, §4), and retail demand pressure in single names is concentrated in exactly the **calls** this strategy buys.

### 6.6 The nearest things to a pro-buyer result

For completeness, the papers that argue *something* is not expensive:
- **Dew-Becker, Giglio, Le & Rodriguez (2017 *JFE* 123(2), 225–250), "The Price of Variance Risk," 1996–2014:** "it was costless on average to hedge news about future variance at horizons ranging from 1 quarter to 14 years." Only *unexpected short-term realized* volatility carries a premium. This is the best-evidenced "vol exposure is not always expensive" result — but it says **zero** premium on forward variance, not negative cost, and it concerns variance horizon, not strike distance.
- **Constantinides, Jackwerth & Perrakis (2009 *RFS* 22(3), 1247–1277):** widespread stochastic-dominance violations 1986–2006 *net of costs* — notably concentrated in **OTM calls**. This is a real anomaly, but the follow-up (Constantinides, Jackwerth & Savov, 2013 *RAPS* 3(2), 229–257) shows a crisis-factor model with price jumps, volatility jumps and liquidity explains index option returns with "notably reduced pricing anomalies in short-maturity out-of-the-money put options."
- **Atilgan, Bali, Demirtaş & Gunaydın (2020 *JFE*), "Left-Tail Momentum":** the market underreacts to extreme left-tail realizations in individual stocks. Closest thing to "single-name left tails are underpriced" — but it is an *equity*-return anomaly tested on stocks, not options, and concentrated in costly-to-arbitrage names.

**No peer-reviewed paper was found claiming far-OTM options are systematically underpriced.**

---

## 7. Event-conditioned convexity and jump predictability

### 7.0 The decisive result: holding through earnings loses ~8% per event

**Dubinsky, Johannes, Kaeck & Seeger, "Option Pricing of Earnings Announcement Risks," *RFS* 32(2), 2019, 646–687.** (This is the published successor to the Dubinsky–Johannes 2006 working paper.) Sample Jan 2000 – Aug 2015, OptionMetrics. ATM straddle in the shortest available maturity, bought at the close *before* the announcement, sold at the close *after* — i.e. the actual convexity trade this strategy proposes:

| | Data | Bootstrap (matched non-event days) | Bootstrap 1st pct |
|---|---|---|---|
| Mean | **−7.96%** | −1.51% | −2.17% |
| Median | **−10.24%** | −3.17% | −3.66% |
| **t-stat** | **−13.25** | −5.40 | |

- Negative in **all 16 years** of the sample.
- The **highest firm-level average return in the entire cross-section is +1%**.
- **−7.96% is below the 1st percentile of the matched non-event-day bootstrap**: buying a straddle into earnings is *worse* than buying one on a random day.
- Mechanism: **implied earnings-day volatility 8.22% vs realized 7.42% — an 80 bp premium.** σ_j^Q > σ_j^P. **Scheduled-announcement volatility is systematically over-priced.** Their Monte Carlo shows a 1% wedge between physical and risk-neutral jump vol is enough to generate −8.5%.
- Their Table 1 also supplies a cost anchor: **ATM quoted spreads are 5.37–6.17% of mid around announcements (6.28%/7.71% in 2011–2015)** — and that is on large, liquid names.

This is the highest-t result in the entire event-options literature, and it is a direct measurement of the strategy's core proposition.

### 7.1 Pre-earnings straddles: real, but it is not a convexity trade

**Gao, Xing & Zhang, "Anticipating Uncertainty: Straddles around Earnings Announcements," *JFQA* 53(6), 2018, 2587–2617.** Verbatim from the published abstract:

> "Straddles on individual stocks generally earn negative and significant returns. However, average at-the-money straddles **from 3 days before an earnings announcement to the announcement date** yield a highly significant **3.34%** return. The positive returns on straddles indicate that investors underestimate the magnitude of uncertainty around earnings announcements. We find that positive straddle returns are more pronounced for smaller firms and firms with higher volatility, higher kurtosis, more volatile past earnings surprises, and **less trading volume/higher transaction costs.**"

**This is the most important distinction in the entire pro-strategy case, and it goes the wrong way.** Read the window: **3 days before the announcement to the announcement date.** The position is closed *at* the announcement, before the earnings jump is realised. The profit therefore comes from the **pre-event implied-volatility run-up** — a vega trade — **not** from capturing a large realised move. It is the opposite of the strategy under evaluation, which buys convexity precisely to hold *through* the event and collect the jump.

**Their Table 3 settles it.** Returns by window, equal-weighted across firms vs weighted by where the open interest actually sits:

| Window | EW | t | **$-open-interest weighted** | **t** |
|---|---|---|---|---|
| [−3,−1] *(sells strictly BEFORE the news)* | 2.62% | 9.67 | 1.37% | 3.81 |
| [−3, 0] *(the headline)* | **3.34%** | 6.71 | **1.10%** | **2.00** |
| **[−3,+1]** *(genuinely THROUGH the news)* | 2.10% | 2.99 | **−0.67%** | **−1.06** |
| **[−1,+1]** *(THROUGH)* | 2.85% | 4.60 | **0.15%** | **0.30** |

And the day-by-day decomposition of [−3,+1]: the profit is localized almost entirely to **day −2 → −1** (EW 1.62%, t = 10.27), while the announcement day itself contributes **[0,+1] = −0.33% EW and −1.37% ($-OI weighted, t = −3.07)**.

Gao, Xing & Zhang say it themselves, verbatim: *"strategy [−3,1] has a 0.62% lower return than the [−3,0] strategy, indicating that **over day 0 to day 1, the return on a straddle might actually be negative.**"*

Four further caveats, any one of which is disqualifying:
- **Weighted by actual open interest, the through-the-event windows are zero or negative** (−0.67%, t = −1.06). The headline survives only equal-weighted across firms.
- **Berkman & Truong (*JAR* 2009)** document that **>40% of firms announce after the close**, so for a large plurality of observations GXZ's day-0 close is *before* the news — reinforcing that the headline window is a run-up trade.
- The straddles are **at-the-money**, not far-OTM, and returns are computed at **bid-ask midpoints**. The authors explicitly disclaim tradability: "we only use end of the day bid and ask prices. For future research, with intraday data, it would be interesting to know whether there are tradable strategies."
- **The entire effect lives in options you cannot trade.** Their Table 4 Panel C: the [−3,0] return is **1.14% in the tightest-spread quartile vs 4.93% in the widest** (difference t = 5.33), and **5.82% in the lowest-volume quartile vs 0.90% in the highest** (t = −5.42). In the liquid quartile it is 1.14% *gross* — inside a single one-way spread. This is the same microstructure signature as Goyal–Saretto (§5.1) and the same signature McLean & Pontiff identify in the anomalies that decay.

**Baseline context from GXZ's own Table 2**: unconditional single-stock delta-neutral ATM straddles at midpoints earn **−0.19%/day (t = −5.11), −2.12%/week (t = −11.92), −17.09%/month (t = −26.82)**. The earnings "edge" of +2.6% over three days barely buys back a single week of theta.

**The correct summary: own vol *into* the print, be flat *through* it.** GXZ and Dubinsky et al. do not contradict each other — GXZ use 10–60 DTE straddles and mostly close before the news; Dubinsky et al. use the shortest-dated (maximum-crush) options and isolate the event. Both say the same thing, and it is the opposite of the strategy.

**A correction to the framing in the brief:** Barth & So (*The Accounting Review* 89(5), 2014) does **not** document a general positive straddle return. Their delta-neutral ATM straddle over [t−1, t+1], sorted on co-movement with market volatility, runs **+2.0% (t = 3.30) in the lowest quintile to −2.0% (t = −2.94) in the highest**, with an unweighted cross-quintile average of roughly **+0.46%** — nil against a ~6% spread, adjusted R² of 0.000–0.006. Their thesis is that option *writers* earn a volatility risk premium, the same direction as Dubinsky et al.

**And the signed equity edge around earnings is real but far too small to buy options with.** Frazzini & Lamont (*JFE* 2008), CRSP 1972–2004: long expected announcers / short expected non-announcers earns **61 bps/month, ~7%/yr, t > 5** — of which only **~21 bps falls in the 3-day announcement window.** Harvesting 21 bps by buying a call whose round trip costs 6–13% of premium is not arithmetic that works.

### 7.2 M&A, FDA and other binary catalysts: the profits are insiders'

**M&A. Augustin, Brenner & Subrahmanyam (*Management Science* 65(12), 2019, 5697–5720)**: 1,859 U.S. takeovers, 1996–2012; **~25% show abnormal pre-announcement option volume, concentrated in short-dated OTM calls**; over half unexplained by speculation, rumours, insider stock trading, leakage or deal predictability; the SEC litigates only ~8%. But this is an **ex-post forensic identification of insider trading, conditioned on a takeover having occurred.** It is not a live signal, and the paper makes no tradeability claim. Cao, Chen & Griffin (*Journal of Business* 2005) is n = 78 targets over 1986–1994 with a key regression at **t = 2.32**; their own sample shows **OTM calls carrying a 26.6% bid-ask spread** vs 9.4% for ITM.

**The direct test of "can an outsider follow the smart money" has been run, and the answer is no.** Jiang & Strong study CNBC *Fast Money*'s Unusual Option Activity segment: the flagged option trades predict returns *prior to* coverage, spike at coverage, and then **significantly reverse**. Verbatim: "investors **cannot profit** by simply following the CNBC reporting on the 'smart money'." The signal is arbitraged at the exact instant it becomes visible to an outsider. Reinforcing this, Goncalves-Pinto, Grundy, Hameed, van der Heijden & Zhu (*Management Science* 66(9), 2020) show option-based return predictability "does not depend on trading in options" — it is transient, mechanical **stock price pressure** that mean-reverts, not information. And Cremers & Weinbaum (*JFQA* 2010) report their own IV-spread signal decaying over the sample, "consistent with a gradual reduction of the mispricing over time."

**FDA/biotech is a genuine literature gap — and the one on-point paper points the wrong way.** There is no academic study of option *returns* around FDA decisions. The only relevant work, Wu, Borochin & Golec (*Journal of Corporate Finance*, 2024), finds abnormal option volume before advisory-meeting dates concentrated in small firms, with informed traders preferring OTM options — but the decisive sentence is that informed traders **"prefer to *sell* options close to the meeting date, perhaps to capture returns from both expected stock price changes and the sharp drop in implied volatility following the meetings."** *Even the people with private information are short vol into the binary.*

The governing prior for all scheduled binaries is Dubinsky et al. (§7.0): σ_j^Q > σ_j^P, t = −13.25. Corroborating on a different event class, **Kelly, Pástor & Veronesi (*JF* 71(5), 2016)** find options whose lives span elections and summits are systematically **more expensive**. Markets do price known catalysts, and the buyer pays for them.

### 7.3 Jump predictability: intensity is forecastable, arrival is not

This is the load-bearing empirical question for the strategy, because the strategy requires forecasting *which* names make a large move within the option's life.

**Andersen, Bollerslev & Diebold, "Roughing It Up" (*REStat* 2007) — jump components predict essentially nothing.** The standard reading ("separating jumps improves volatility forecasts") is backwards. Their β_J is "systematically negative across all models and markets, and with few exceptions, overwhelmingly significant," and the combined next-day impact of a jump nets to approximately **zero** (DM/$ ≈ 0, S&P 500 −0.027, T-bond −0.002). Verbatim: "if the realized volatility is entirely attributable to jumps, it carries **no predictive power** for the following day's realized volatility," and "the predictability in the HAR-RV regressions is **almost exclusively due to the continuous sample path components.**"

**Jump arrival is close to i.i.d.** Their Christoffersen LR tests for i.i.d. jump occurrence against a first-order Markov alternative (critical value 3.84) fail to reject for DM/$ (0.746, 2.525, 0.224, 0.994, 0.776) and T-bonds; only the S&P 500 rejects. Their conclusion: "jump dynamics are much less persistent (and predictable) than continuous sample path dynamics."

**The one thing that is forecastable is the calendar.** ABD note that "many of the most significant jumps are readily associated with specific macroeconomic news announcements," and Lee & Mykland (*RFS* 2008) and Lee (*RFS* 2012) confirm jump arrival is predictable from Fed announcements, employment reports, jobless claims, earnings releases and analyst actions. **Jump timing is forecastable exactly to the extent that the calendar is public — which is precisely what options already price**, at an 80 bp premium (§7.0). Nothing in this literature forecasts the **sign** of a jump, or its size relative to the option-implied move. That residual is the only thing that would make the strategy work, and it is the component the best-fitting models treat as unpredictable.

**The tail factor predicts equity returns, not tails.** Andersen, Fusari & Todorov (*JBES* 2020; estimation machinery in *Econometrica* 83(3), 2015) find the left-tail jump factor orthogonal to spot variance **positively predicts future equity index excess returns** (R² > 10% at four months, > 15% at six). Critically: "the part of the left jump intensity factor orthogonal to spot volatility has **no explanatory power for the ex-post realized return variation** … The absence of any auxiliary predictive power in the jump factor is striking." **A high tail premium is a signal to be long equities, not long puts** — it says tails are richly priced and the insurance seller is being compensated. (Caveat: 8 years of weekly data with overlapping 2–6 month horizons is ~16–30 independent observations; do not treat those t-stats as clearing t ≥ 4.)

**Bollerslev & Todorov, "Tails, Fears, and Risk Premia" (*JF* 66(6), 2011)** price that compensation. Excluding the crisis window, the median equity risk premium attributable to rare events is **5.2%** against a total of ~8% — "fears of rare events account for roughly **two-thirds** of the total expected excess return." For variance, **88.4% of the variance risk premium comes from the left tail** — "close to **three-quarters** of the variance risk premium may be attributed to investor fears." Their sign convention is explicit: the VRP is "the expected payoff on a (long) variance swap," and it is "on average negative." **The long-tail-insurance position pays that premium; it does not earn it.**

**News and sentiment: real, tiny, ~80% pre-decayed, and dead at 9–10 bps of *equity* cost.** Nothing in this literature predicts a *large* move; every result is a 3–33 bp mean edge at a one-day-to-two-week horizon.
- Tetlock (*JF* 2007): a one-SD increase in WSJ pessimism predicts −8.1 bps next day, **fully reversing within the week**. His own breakeven: costs "may exceed 4.4 basis points per trade — the cutoff value for eliminating the profitability," and that is on Dow futures.
- Tetlock, Saar-Tsechansky & Macskassy (*JF* 2008): of the 61.6 bp event reaction, only **10.6 bps (17.2%) is the tradeable day-+1 component** — 83–93% of the move is in the price before you can act. Their cost sensitivity runs **23.17% annualized at zero cost to −0.39% at 9 bps** round trip.
- Ke, Kelly & Xiu (2019), the strongest modern out-of-sample result: day −1 = 45 bps, **day 0 = 93 bps, day +1 (the tradeable one) = 33 bps** — ~80% gone before you can act. Net of their own 10 bp assumption, the best configuration yields **11.23 bps/day**. That is a fine institutional equity book; it is one to two orders of magnitude below a single-stock weekly option's round trip.
- The famous Bollen, Mao & Zeng Twitter result ("87.6% accuracy") **fails replication**: Lachanski & Pav (*Econ Journal Watch* 2017) find the Granger causality vanishes when the window is extended back to 2007, with no out-of-sample power and training/test overlap. Diagnosis: data snooping. The fund launched to trade it closed in 2012.

**Short interest and gamma squeezes: every verified result has the wrong sign.** Hong, Li, Ni, Scheinkman & Yan (1988–2012) find long-low / short-**high** days-to-cover earns **1.19%/month, t = 6.67** — i.e. **high days-to-cover predicts LOW returns**, the precise inverse of a squeeze thesis. Boehmer, Huszár & Jordan (*JFE* 2010) find the economically large positive returns come from heavily traded stocks with **low** short interest. Soebhag finds high net-gamma stocks **underperform** by 10%/yr. Everything documented on gamma (Baltussen et al. *JFE* 2021; Barbon & Buraschi; Ni, Pearson, Poteshman & White *RFS* 2020) is **intraday, index-level, and mean-reverting**, and the variance effect it identifies is already in the option's price. Baltussen et al.: "we do not consider transaction costs … the strategy as presented might not be exploitable to many investors."

**Bottom line on §7: there is no event or jump-forecasting condition under which buying far-OTM convexity and holding through the event has a documented positive mean net of costs.** The one robust positive result (Gao–Xing–Zhang) requires ATM strikes, requires exiting *before* the event, vanishes when weighted by actual open interest, and lives in the options with the widest spreads. The direct measurement of the strategy's proposition — Dubinsky et al. — is **−7.96% per event at t = −13.25, negative in 16 of 16 years.**

---

## 8. The publication-bias prior

Across the Open Source Asset Pricing library's 212 predictors, post-publication mean return ≈ **−0.122 + 0.61 × (in-sample mean)**, and only **14.3%** clear t > 2 in 2015–2024. The peer-reviewed anchor for this is **McLean & Pontiff, "Does Academic Research Destroy Stock Return Predictability?," *JF* 71(1), 2016, 5–32**: across 97 predictors, portfolio returns are **26% lower out-of-sample and 58% lower post-publication**, with decay *greatest for predictors with the highest in-sample returns* and returns concentrated in **high-idiosyncratic-risk, low-liquidity** stocks — exactly the segment far-OTM single-stock options live in.

Applied here, the prior cuts in a specific direction worth noting: **the adverse findings are not the ones at risk from this prior.** McLean–Pontiff decay applies to *profitable* published anomalies being arbitraged away. Boyer–Vorkink and Bali–Murray document a *cost* borne by a demand-driven investor clientele, which arbitrageurs have every incentive to keep collecting, not to compete away. The 10–50%/week skewness spread is a t-statistic in the high single digits (Wang's replication: t = 7.738) driven by a structural demand imbalance that has *grown* since publication — retail is now >60% of option volume (BPS 2023). This is the rare case where the adverse result should be expected to persist or strengthen.

Conversely, the prior applies with full force to anything in §5–§7 offered as a reason to buy. Hou, Xue & Zhang (*RFS* 33(5), 2020) sharpen it: of **452 anomalies, 65% fail |t| > 1.96 and 82% fail |t| > 2.78** under NYSE breakpoints and value weighting, with **96% of trading-frictions anomalies failing** — and the failures are driven by microcaps, 3% of market cap but 60% of names. That is the same corner of the market where single-stock far-OTM options live.

### 8.1 Two structural facts that govern every number in this document

**First: essentially no paper in this literature reports an option strategy net of spreads.** Goyal–Saretto, Gao–Xing–Zhang, Barth & So, Boyer–Vorkink, Cao–Han, Park and Vasquez all compute returns at **OptionMetrics bid-ask midpoints**. The honest ones say so explicitly — Gao, Xing & Zhang: "we only use end of the day bid and ask prices. For future research, with intraday data, it would be interesting to know whether there are tradable strategies." Every headline figure in this review, favourable or adverse, should be read as an upper bound on what a buyer could realise.

The real counterweight is **Muravyev & Pearson (*RFS* 2020)** — effective spreads for execution-timing traders are **<40% of conventional measures**, overall ~25% smaller. But even a 3× reduction on a 6% ATM quoted spread leaves ~2% round trip against a tradeable-quartile gross edge of 0.5–1.1%, and it presumes sub-second execution infrastructure on 39 of the most liquid names. It does not reach a $1 far-OTM weekly.

**Second: every result in this literature with t > 4 points the wrong way for a buyer.** Dubinsky et al. **t = −13.25**; Barth & So **t = −5.09**; Cao & Han **t = 6.42–9.62** for the *seller*; Zhan et al. **t = 7–35** for the *writer*; Hong et al. **t = 6.67** for the *inverse* of a squeeze trade. Every result pointing the buyer's way — Vasquez's long leg (t = 3.50), Goyal–Saretto's D10 (t ≈ 3.78), Barth & So's low-COMOVE quintile (t = 3.30), GXZ's $-weighted headline (t = 2.00), Cao–Chen–Griffin (t = 2.32) — falls **below the t ≥ 4 bar, in-sample, and before costs.**

Santa-Clara & Saretto (*JFM* 12(3), 2009) state the resulting asymmetry plainly: "strategies that **short** options constitute very good deals… However, exploiting these good deals can be extremely difficult" — margin calls and trading costs bind on the profitable side. The buyer faces no such friction, because there is no edge to protect.

*(Citation note: the brief attributed "Parametric Inference and Dynamic State Recovery from Option Panels" to JFE 2015; it is **Econometrica** 83(3), 2015, 1081–1145. The JFE 2015 Andersen–Fusari–Todorov paper is "The Risk Premia Embedded in Index Options," 117(3), 558–584.)*

---

## 9. If you do it anyway: the least-bad version

Every item below is a documented finding, not an opinion. Each one moves the strategy toward a cell where the measured penalty is smaller. None of them makes the mean positive.

**Structural changes, ranked by measured impact:**

1. **Stop buying $0.01–$0.10 options.** This is the single largest term. Effective spread runs 4.02% at the money, 12.63% at 10–100% OTM, 24.20% at 100–200% OTM, 29.12% beyond that (Amaya et al. Table 1). Tick size alone imposes ~67% quoted spreads at penny quotes. Moving from "far OTM" to "modestly OTM" (10–25%) cuts the cost term by roughly half and cuts the Boyer–Vorkink skewness penalty by more, since ex-ante skewness rises steeply with moneyness.
2. **Increase ticket size.** Sub-$250 tickets pay a 23.68% quoted / 10.84% effective spread; $1,000–$2,500 tickets pay 6.81% / 2.66%. Concentrating $100 into *one* position rather than 100 does not change the spread cell much at that size, but the direction is unambiguous: fragmenting into $1 tickets maximises the cost per dollar deployed.
3. **Lengthen maturity.** The Boyer–Vorkink penalty is quoted *per week* and ex-ante skewness is highest for short-dated OTM options. Weekly expiries are the maximum-penalty cell. Retail's documented preference for "cheaper, weekly options" (BPS 2023) is precisely the behaviour being charged for.
4. **Invert the underlying-selection rule.** Hu & Jacobs (2020): call returns *decrease* with underlying volatility. "Cheap Options Are Expensive": options on low-priced stocks underperform by 0.54%/week for calls. If you must buy calls, buy them on **higher-priced, lower-volatility** names — the exact opposite of the intuitive "name likely to make a big move."
5. **Use order-flow contrarianism, not order-flow following.** Muravyev (2016): past order imbalance is the strongest known predictor of option returns, and the sign says options with heavy customer buying subsequently underperform. Buying the option that is currently popular is buying the most expensive one on the board.
6. **Time executions; never pay the offer.** Muravyev & Pearson (2020): traders who time executions pay <40% of conventional effective spread. Use limit orders resting at or inside the midpoint, and accept non-fills.
7. **Pay zero commission.** At $0.50–0.65/contract, commissions alone are 50–65% of a $1.00 premium each way.

**The honest reframing.** If the goal is *convex exposure to a large market dislocation*, the literature says the cheapest documented way to obtain it is not systematic put/call buying. AQR's work on tail hedging (see §7) finds trend-following delivers comparable crisis payoff at materially lower long-run carry cost. If the goal is *positive skew in a portfolio*, that can be obtained with an equity/cash mix plus a trend sleeve without paying the option-market skewness premium at all.

**The version that is actually defensible.** Treat the $100 as an *entertainment and education budget*, explicitly expensed, not as an investment with positive expectancy. It is a real and legitimate reason to trade — Bauer, Cosemans & Eichholtz (2009, *JBF*) find that "gambling and entertainment appear to be the most important motivations for trading options while hedging motives only play a minor role," and that most investors incur substantial option losses, "much larger than the losses from equity trading," attributed to poor market timing from overreaction to past returns plus high trading costs. Budgeting it honestly as consumption is intellectually clean. Budgeting it as an expected-positive-return sleeve is not supported by anything in this review.

One genuine caveat in the owner's favour: Bauer et al. do find **"strong evidence of performance persistence among option traders."** Some traders are reliably better than others. But persistence in a population with a deeply negative mean is mostly persistence in *how badly* you lose, and none of the papers reviewed identify an ex-ante-observable characteristic of a *retail* trader that predicts a positive mean.

---

## 10. Verdict

**(a) What is the documented mean return of far-OTM long options, net of costs?**

Strongly negative, and the further OTM and shorter dated, the worse. The most directly on-point measurement is **Duarte, Jones & Wang (*JF* 2024): heavily traded deep-OTM calls on individual stocks average −116 bp per day** (≈ −5.7%/week) — the strategy's exact instrument, in liquid names, so not an illiquidity artifact. Boyer & Vorkink (*JF* 2014) measure **10–50% per week** between low- and high-ex-ante-skewness option portfolios, on midpoint pricing, with high-skewness = far-OTM/short-dated. An independent replication puts two-week hold-to-expiration returns in the high-skewness bin at **−54%** (t = 7.738 on the spread). Ni (2008) finds average returns to OTM stock calls are **negative** — a direct contradiction of Coval & Shumway's theoretical prediction that they should be the highest in the cross-section. On top of that, the far-OTM sub-$250 cell pays **12–29% effective spread**, and at $0.01–$0.05 quotes the tick alone is a ~67% spread. Bali & Murray (*JFQA* 2013) show the penalty survives when delta and vega are hedged out, so it is not a leverage artifact. Barberis & Huang (*AER* 2008) supply the mechanism: probability weighting makes positively skewed securities overpriced with **negative expected excess return by construction**.

**(b) Is there any conditioning variable with credible evidence of making it positive?**

**No — not for naked far-OTM longs.** Four candidates were tested seriously and each fails for a specific, identifiable reason:

| Candidate | Best in-sample result | Why it does not transfer |
|---|---|---|
| **HV − IV (Goyal–Saretto)** | 22.7%/mo long-short straddle, t = 10.41 at midpoint | Falls to **3.9%, t = 1.84** at full quoted spread; to **1.4%, t = 0.56** in high-spread names. Survivor is 8.2% (t = 3.17) in *liquid* options only — below the t ≥ 4 bar. And it is **long-short** and **ATM by construction** (moneyness restricted to 0.975–1.025, explicitly to avoid the smile). |
| **Low IV / IV rank** | — | No supporting literature. Low IV is usually a correct forecast, not a discount (Israelov & Nielsen). Variance risk premium is positive on average in every standard sample. |
| **Tail underpricing (BCM)** | Option-implied 5-SD probability 0.0001 vs Barro-calibrated 0.0079 | Authors themselves argue the option column is the *more* credible one; the two agree at 3 SD; unfalsifiable Peso argument; index puts only. Realized index put returns are −57%/mo at 6% OTM (t = −3.9). |
| **Pre-earnings straddles (Gao–Xing–Zhang)** | +3.34%, t = 6.71 | Window is 3 days before → **the announcement date**, i.e. it *excludes* the jump; profit localizes to day −2→−1. **$-open-interest weighted it is 1.10% (t = 2.00), and −0.67% (t = −1.06) through the event.** 4.93% in widest-spread quartile vs 1.14% in tightest. Midpoint pricing; authors disclaim tradability. Holding through loses **−7.96%, t = −13.25** (Dubinsky et al.). |
| **IV term structure (Vasquez)** | +7.3%/mo long leg, t = 3.50 | Best long-only result found anywhere. Still **t < 4**; gross edge ≈ its own **8.5% bid-ask spread**; sits in the widest-spread decile; long-short net of full spread is t = 1.88; untested since 2012. |
| **Low vol-of-vol (Park VVIX)** | correct sign, t = −5.54 | Breakeven requires VVIX **2.25–2.65 SD below mean** vs a historical minimum of −3.03 SD — the enabling condition essentially never occurs. Non-tradeable residualized returns, no cost analysis. |

The one conditioning variable that is both strong and cost-robust — **Muravyev (2016)**, past order imbalance, "greater predictive power than any other commonly used predictor of option returns" — has the wrong sign for this strategy: it says the options customers are buying subsequently underperform. And the strategy's own selection rule (names likely to make a big move ⇒ high volatility, low price) is independently documented to produce *lower* call returns (Hu & Jacobs 2020; "Cheap Options Are Expensive").

The genuinely honest caveats on the other side, which do not overturn the conclusion but should be recorded: Broadie–Chernov–Johannes show deep-OTM index put returns are statistically *insignificant* against a properly specified model (they lose roughly what a correct model says they should); Wang's β-Heston simulation cannot reject that skewness is unpriced; Amaya et al. (2025) contest the retail-loss finding; and Bauer et al. find genuine performance persistence among option traders. None of these produces a positive mean.

**(c) If the strategy is negative-expectancy, what is the least-bad version?**

See §9. Ranked: stop buying penny-priced options; move strikes closer to the money; lengthen maturity beyond weeklies; invert the underlying screen toward higher-priced, lower-volatility names; buy what customer flow is *selling*, not buying; time executions with resting limit orders; pay zero commission. And budget it as consumption, not as expectancy.

---

## Sources

**Core adverse literature**
- Boyer, B. H., & Vorkink, K. (2014). "Stock Options as Lotteries." *Journal of Finance* 69(4), 1485–1527. [DOI 10.1111/jofi.12152](https://doi.org/10.1111/jofi.12152)
- Bali, T. G., & Murray, S. (2013). "Does Risk-Neutral Skewness Predict the Cross-Section of Equity Option Portfolio Returns?" *JFQA* 48(4), 1145–1171. [DOI 10.1017/S0022109013000410](https://doi.org/10.1017/S0022109013000410)
- Barberis, N., & Huang, M. (2008). "Stocks as Lotteries: The Implications of Probability Weighting for Security Prices." *AER* 98(5), 2066–2100. [NBER w12936 PDF](https://www.nber.org/system/files/working_papers/w12936/w12936.pdf)
- Bryzgalova, S., Pavlova, A., & Sikorskaya, T. (2023). "Retail Trading in Options and the Rise of the Big Three Wholesalers." *Journal of Finance* 78(6), 3465–3514. [DOI 10.1111/jofi.13285](https://doi.org/10.1111/jofi.13285)
- Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011). "Maxing Out: Stocks as Lotteries and the Cross-Section of Expected Returns." *JFE* 99(2), 427–446.
- Eraker, B., & Ready, M. (2015). "Do Investors Overpay for Stocks with Lottery-Like Payoffs? An Examination of the Returns of OTC Stocks." *JFE*.
- Ni, S. X. (2008/2009). "Stock Option Returns: A Puzzle." SSRN working paper (circulated as 1259703 and 1340767). Sample 1996–2005. Key finding: OTM calls have negative average returns and returns *decrease* in strike — the reverse of Coval–Shumway.

**Theory and benchmarks**
- Coval, J. D., & Shumway, T. (2001). "Expected Option Returns." *Journal of Finance* 56(3), 983–1009. [DOI 10.1111/0022-1082.00352](https://doi.org/10.1111/0022-1082.00352)
- Broadie, M., Chernov, M., & Johannes, M. (2009). "Understanding Index Option Returns." *RFS*.
- Wang, Z. "The Cross-Section of Equity Option Returns" (Bocconi field paper) — [PDF](https://www.unibocconi.it/sites/default/files/media/attachments/Wang-Zhibin-fieldPaper.pdf). Contains the Boyer–Vorkink replication and the β-Heston critique.

**Costs and market microstructure**
- Muravyev, D., & Pearson, N. D. (2020). "Options Trading Costs Are Lower than You Think." *RFS* 33(11), 4973–5014. [DOI 10.1093/rfs/hhaa010](https://doi.org/10.1093/rfs/hhaa010)
- Muravyev, D. (2016). "Order Flow and Expected Option Returns." *Journal of Finance* 71(2), 673–708. [DOI 10.1111/jofi.12380](https://doi.org/10.1111/jofi.12380)
- Amaya, D., Garcia-Ares, P. A., Pearson, N. D., & Vasquez, A. (2025). "New Evidence on the Performance of Customer Options Trades." Cboe Options Institute data grant. [PDF](https://cdn.cboe.com/resources/education/research_publications/Retail_Profitability.pdf)
- Beckmeyer, H., Branger, N., & Gayda, L. (2023). "Retail Traders Love 0DTE Options… But Should They?" SSRN 4404704.

**Selection variables**
- Hu, G., & Jacobs, K. (2020). "Volatility and Expected Option Returns." *JFQA* 55(3), 1025–1060.
- Boulatov, A., Eisdorfer, A., Goyal, A., & Zhdanov, A. (2021). "Cheap Options Are Expensive." [PDF](https://finance-conference.wpcarey.asu.edu/sites/g/files/litvpz3416/files/imported/21-11-20-04-07-04_Cheap_Options_Are_Expensive%20(1).pdf)
- Bauer, R., Cosemans, M., & Eichholtz, P. (2009). "Option Trading and Individual Investor Performance." *Journal of Banking & Finance*.

**Tail risk, disasters, and crisis alpha**
- Backus, D., Chernov, M., & Martin, I. (2011). "Disasters Implied by Equity Index Options." *Journal of Finance* 66(6), 1969–2012. [NBER w15240 PDF](https://www.nber.org/system/files/working_papers/w15240/w15240.pdf) · [LSE PDF](https://personal.lse.ac.uk/martiniw/BCM-jf.pdf)
- Bondarenko, O. (2014). "Why Are Put Options So Expensive?" *Quarterly Journal of Finance* 4(3).
- Broadie, M., Chernov, M., & Johannes, M. (2009). "Understanding Index Option Returns." *RFS* 22(11), 4493–4529. [Columbia PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/3964/broadie_chernov_johannes.pdf)
- Chambers, D., Foy, M., Liebner, J., & Lu, Q. (2014). "Index Option Returns: Still Puzzling." *RFS* 27(6), 1915–1928.
- Ilmanen, A., Thapar, A., Tummala, H., & Villalon, D. (2021). "Tail Risk Hedging: Contrasting Put and Trend Strategies." *Journal of Systematic Investing* 1(1). [AQR PDF](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/Journal-of-Systematic-Investing-Vol-1-Issue-1--Tail-Risk-Hedging-AQR.pdf)
- Ilmanen, A. (2012). "Do Financial Markets Reward Buying or Selling Insurance and Lottery Tickets?" *FAJ* 68(5). (Taleb dissent: *FAJ* 69(2), 2013.)
- Israelov, R., & Nielsen, L. N. (2015). "Still Not Cheap: Portfolio Protection in Calm Markets." AQR.
- Dew-Becker, I., Giglio, S., Le, A., & Rodriguez, M. (2017). "The Price of Variance Risk." *JFE* 123(2), 225–250.
- Bollerslev, T., & Todorov, V. (2011). "Tails, Fears, and Risk Premia." *Journal of Finance* 66(6).
- Bakshi, G., Kapadia, N., & Madan, D. (2003). *RFS* 16(1), 101–143. · Bollen, N., & Whaley, R. (2004). *JF* 59(2). · Driessen, J., Maenhout, P., & Vilkov, G. (2009). *JF* 64(3), 1377–1406.
- Constantinides, G., Jackwerth, J., & Perrakis, S. (2009). *RFS* 22(3), 1247–1277. · Constantinides, Jackwerth & Savov (2013). *RAPS* 3(2), 229–257.

**Conditional cheapness and events**
- Goyal, A., & Saretto, A. (2009). "Cross-Section of Option Returns and Volatility." *JFE* 94(2), 310–326. [PDF via author site](https://drive.google.com/file/d/1lAvSaDxJn-fbe8sBTd0bkAnpoo--pscY/view) — Table 7 verified directly.
- Gao, C., Xing, Y., & Zhang, X. (2018). "Anticipating Uncertainty: Straddles around Earnings Announcements." *JFQA* 53(6), 2587–2617. [DOI 10.1017/s0022109018000285](https://doi.org/10.1017/s0022109018000285)
- Cao, C., & Han, B. (2013). "Cross Section of Option Returns and Idiosyncratic Stock Volatility." *JFE* 108(1), 231–249.
- Horenstein, A., Vasquez, A., & Xiao, X. (2026). "Common Factors in Equity Option Returns." *RFS*.
- Carr, P., & Wu, L. (2009). *RFS* 22(3), 1311–1341. · Bollerslev, Tauchen & Zhou (2009). *RFS* 22(11), 4463–4492.

**Microstructure critiques of the option-return literature (apply as a discount to every result above)**
- Duarte, J., Jones, C. S., & Wang, J. L. (2024). "Very Noisy Option Prices and Inference Regarding the Volatility Risk Premium." *Journal of Finance* 79(5), 3581–3621. [DOI](https://doi.org/10.1111/jofi.13365) — **deep-OTM stock calls −116 bp/day.**
- Duarte, J., Jones, C. S., Khorram, M., Mo, H., & Wang, J. L. (2026). "Too Good to Be True: Look-Ahead Bias in Empirical Options Research." *RFS*. [DOI](https://doi.org/10.1093/rfs/hhag061)
- Zhan, X., Han, B., Cao, J., & Tong, Q. (2022). "Option Return Predictability." *RFS*. [DOI](https://doi.org/10.1093/rfs/hhab067)
- Hou, K., Xue, C., & Zhang, L. (2020). "Replicating Anomalies." *RFS* 33(5), 2019–2133. — 65% of 452 anomalies fail |t| > 1.96 with NYSE breakpoints and value weighting.

**Events and jumps**
- Dubinsky, A., Johannes, M., Kaeck, A., & Seeger, N. (2019). "Option Pricing of Earnings Announcement Risks." *RFS* 32(2), 646–687. [DOI](https://doi.org/10.1093/rfs/hhy060) — **hold-through-earnings straddle −7.96%, t = −13.25.**
- Barth, M., & So, E. (2014). *The Accounting Review* 89(5), 1579–1607. · Frazzini, A., & Lamont, O. (2008). *JFE* (earnings announcement premium).
- Augustin, P., Brenner, M., & Subrahmanyam, M. G. (2019). "Informed Options Trading Prior to Takeover Announcements." *Management Science* 65(12), 5697–5720. [DOI](https://doi.org/10.1287/mnsc.2018.3122)
- Wu, K., Borochin, P., & Golec, J. (2024). "Informed Options Trading before FDA Drug Advisory Meetings." *JCF*. [DOI](https://doi.org/10.1016/j.jcorpfin.2023.102495)
- Goncalves-Pinto, L., Grundy, B., Hameed, A., van der Heijden, T., & Zhu, Y. (2020). *Management Science* 66(9). [DOI](https://doi.org/10.1287/mnsc.2019.3398)
- Andersen, T., Bollerslev, T., & Diebold, F. (2007). "Roughing It Up." *REStat*. · Lee, S. (2012). *RFS* 25(2), 439–479.
- Andersen, T., Fusari, N., & Todorov, V. (2020). "The Pricing of Tail Risk and the Equity Premium." *JBES*. · Bollerslev, T., Todorov, V., & Xu, L. (2015). *JFE* 118(1), 113–134.
- Kelly, B., Pástor, Ľ., & Veronesi, P. (2016). "The Price of Political Uncertainty." *JF* 71(5).
- Hong, H., Li, W., Ni, S. X., Scheinkman, J., & Yan, P. "Days to Cover and Stock Returns." NBER w21166.
- Lachanski, M., & Pav, S. (2017). "Shy of the Character Limit: 'Twitter Mood Predicts the Stock Market' Revisited." *Econ Journal Watch* 14(3), 302–345.

**Conditional cheapness (additional)**
- Vasquez, A. (2017). "Equity Volatility Term Structures and the Cross Section of Option Returns." *JFQA*.
- Park, Y.-H. (2015). "Volatility-of-Volatility and Tail Risk Hedging Returns." *JFM*. · Huang, D., Schlag, C., Shaliastovich, I., & Thimme, J. (2019). *JFQA*.
- Aragon, G., Mehra, R., & Wahal, S. (2020). *JPM*. · Konstantinidi, E., & Skiadopoulos, G. (2016). *JBF*.
- Aït-Sahalia, Y., Karaman, M., & Mancini, L. (2020). "The Term Structure of Equity and Variance Risk Premia." *J. Econometrics*.
- Bakshi, G., & Kapadia, N. (2003). "Delta-Hedged Gains and the Negative Market Volatility Risk Premium." *RFS* 16(2).

**Publication bias**
- McLean, R. D., & Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance* 71(1), 5–32. [DOI 10.1111/jofi.12365](https://doi.org/10.1111/jofi.12365)
- Chen, A. Y., & Zimmermann, T. (2022). "Open Source Cross-Sectional Asset Pricing." *Critical Finance Review* 11(2), 207–264.
