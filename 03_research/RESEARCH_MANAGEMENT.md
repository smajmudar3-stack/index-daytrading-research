# Trade Management Rules: What the Evidence Actually Supports

Research compiled 2026-08-06. Every source is tagged with who paid for it and what they sell.

---

## 1. Bottom line

| Rule | Verdict | What the best evidence says | Primary source | Source's conflict |
|---|---|---|---|---|
| Take profit at 50% of max credit | **FOLKLORE as a return rule** | Reduces CAGR at low delta; helps only at 16–30Δ, and there mostly via the 21-DTE leg bundled with it. Your own straddle test: +2.21% → −0.23%. | tastytrade (assertion only); spintwig (real quotes, contradicts) | tastytrade = the brokerage |
| Take profit at 25% | **FOLKLORE** | Worse than 50% on win rate at low delta because commissions turn winners into losers. Only competitive at 30Δ+ leveraged. | spintwig SPY short put 45 DTE | spintwig sells trade logs |
| Stop loss at 2× credit | **UNEVIDENCED — no public study found** | Nobody has published a credible 2× test. Structural argument says it hurts short premium. | none located | — |
| Roll at 21 DTE / roll for credit | **FOLKLORE** | No study of any provenance found that isolates rolling vs closing + reopening. | none located | — |
| Hold to expiry | **EVIDENCED as the default** | Best CAGR, Sharpe and win rate for sub-16Δ short puts on SPY and QQQ. It is also what the CBOE PUT/BXM benchmarks do. | spintwig QQQ + SPY studies | spintwig sells trade logs |
| Close at 21 DTE | **EVIDENCED — but as a RISK rule, not a return rule** | Cuts annual vol 20–34%, softens worst month 35–60%. Mean return falls. Exactly your finding. | spintwig SPY strangle 45 DTE | spintwig sells trade logs |
| **Long premium: profit target** | **Predicted HARMFUL, untested by you** | Caps the only tail that pays, leaves the −100% tail intact. Same error as the short-side 50% rule but worse. | theory + your straddle result | — |
| **Long premium: time stop** | **EVIDENCED in principle, your 21-session rule is sound** | Negative carry means time-in-trade is a cost, so a time stop is EV-accretive on the long side — the sign flips vs short. | Coval–Shumway; spintwig long-call study (paywalled) | — |

**The single most important structural insight in this document:** the carry drift flips sign between short and long premium, so the management logic must flip too. Short premium earns a positive drift for holding, which is why truncating winners early destroys EV. Long premium *pays* a negative drift for holding, which is why a time stop is defensible there and a profit target is not. Rules copied from the short-premium literature to the long side will be systematically wrong.

---

## 2. The conflict-of-interest map

### tastytrade / tastylive — the source of nearly every rule in this document

This is not an inference; the corporate structure is stated in their own site footer:

> "tastytrade, Inc. ('tastytrade') is a registered broker-dealer and member of FINRA, NFA, and SIPC... tastytrade is a wholly-owned subsidiary of tastylive, Inc. **tastytrade has entered into a Marketing Agreement with tastylive ('Marketing Agent') whereby tastytrade pays compensation to Marketing Agent to recommend tastytrade's brokerage services.**"
> — https://www.tastylive.com/concepts-strategies/managing-winners

So: the research publisher (tastylive) is **paid by** the brokerage (tastytrade) to drive business to it, and the brokerage is a wholly-owned subsidiary of the publisher. It is one economic entity that is simultaneously the venue, the media arm and the research house. There is no independent editorial layer anywhere in the chain.

Now look at what the rules do to contract volume, per dollar of client capital:

- **Manage winners at 50%** turns one round-trip into two, and frees the capital to open a third. Their own page says so explicitly: *"we can redeploy capital elsewhere in a new trade, and likely collect more."*
- **Close at 21 DTE** forces an exit on positions that would otherwise expire worthless at **zero commission**. Expiring OTM is free; closing early is not.
- **Roll** is two contracts closed and two opened where holding is zero.
- **Stop loss at 2× credit** adds a closing trade to positions that would otherwise cost nothing to expire.

Every single rule increases billable contracts. Not one of them reduces them. That pattern is not proof the rules are wrong, but it means the null hypothesis has to be "marketing" and the burden of proof sits with them.

**And they have not met it.** The canonical page (https://www.tastylive.com/concepts-strategies/managing-winners) contains:
- no sample period
- no underlying
- no DTE
- no number of occurrences
- no statement of whether P&L used real quotes or midpoints
- no slippage or commission assumption
- no data source
- no link to the underlying research — the "Supplemental Content / Episodes on Managing Winners" block renders as **"No episodes available at this time."**

The entire evidentiary content is three assertions: *"We have found that managing our winning trades prior to expiration can improve our probability of success"*, *"We've found that the target of managing our winning trades at 50% can be the sweet spot over the long run for most trades"*, and *"There are not many downsides to managing winners early."*

The supporting research exists only as video segments on *Market Measures*, *The Skinny on Options*, and *From Theory to Practice* — e.g.:
- https://www.tastylive.com/shows/market-measures/episodes/managing-winners-varying-profit-targets-12-04-2015
- https://www.tastylive.com/shows/market-measures/episodes/managing-winners-exiting-based-on-duration-01-26-2016
- https://www.tastylive.com/shows/market-measures/episodes/manage-winners-and-close-early-04-20-2016
- https://www.tastylive.com/shows/the-skinny-on-options-modeling/episodes/probability-of-50-profit-12-17-2015
- https://www.tastylive.com/shows/market-measures/episodes/21-dte-vs-50-percent-winner-02-04-2021
- https://www.tastylive.com/shows/market-measures/episodes/probability-of-reaching-50-percent-profit-09-06-2023

**These are video segments with on-screen tables. There is no paper, no methodology appendix, no downloadable data, and no way to reproduce any number.** Whether they used real bid/ask or midpoints is undeterminable from the public record — which by itself disqualifies the result from being called evidence. Midpoint marking is the single most common way an option-management backtest is inflated, and closing early is *exactly* the operation that pays a second spread, so this is the one assumption that most needs disclosure and is the one that is missing.

**Verdict on tastytrade as a source: not evidence. Assertion from an interested party, unreproducible by construction.**

### spintwig LLC — the best public source, but not disinterested either

https://spintwig.com/methodology/ — genuinely rigorous, and I'm treating it as the primary evidence base. But state the conflicts:

- Sells trade-log datasets at $9.99/study up to $485.51/bundle.
- Sells custom private backtests from $99.
- Sells a "market insights" subscription at **$249/yr**, which now paywalls the results tables of every current study.
- Sells an "s1 signal" daily email subscription.
- **Is an affiliate of ORATS**, its own data vendor: *"Save up to 66% on ORATS institutional-quality options data and tools. (affiliate link)"* — so it earns a referral on the data it validates its own work with.

Note the direction of the bias, though: spintwig's incentives point *toward* selling more studies, not toward flattering any particular rule — and in practice it publishes results that **actively undercut** broker-friendly management rules, including an explicit "Retail Broker Business Model" section in multiple studies. That makes it more credible on this specific question, not less. It is also the only source that publishes its slippage function.

---

## 3. Rule-by-rule evidence

### 3a. Profit target at 25% / 50% of max credit — FOLKLORE as a return rule

**The only real-quote, reproducible tests are spintwig's.** Full spec, identical across studies:

- Data: ORATS, professional licence, empirical only — *"There is no use of calculated, theoretical or otherwise-modeled pricing."*
- Pricing: **real bid/ask**, with an explicit slippage function: `Buy = Bid + (Ask−Bid)×s`, `Sell = Ask − (Ask−Bid)×s`, where `s=0.50` is midpoint and `s=1.00` is paying the full spread. Published studies use a slippage table (values not in the extracted text — treat as a limitation, but the function is at least disclosed, which is more than any other source offers).
- Commission: $1.00/contract all-in per leg on ETFs, $1.32 on indices, **$0.00 to expire worthless.**
- Entry: **every trading day**, which averages out timing luck. This matters — it's the reason these results are more trustworthy than a single-start-date study.
- Collateral earns 3-month T-bills.
- Single daily snapshot at 3:46pm ET; no intraday path.

**Result 1 — SPY Short Iron Condor 45 DTE.** 2007-01-03 → 2019-07-19, 40 backtests, **120,700 trades**. Exits tested: 25%/21DTE, 50%/21DTE, 75%/expiry, hold-to-expiry.
(https://spintwig.com/spy-short-iron-condor-options-backtest-results/ — live version is paywalled, results readable in the 2020-11-26 Wayback capture)

- CAGR: *"Holding till expiration on the lower risk (sub 16D) trades yielded the best returns. Managing at 50% max profit or 21 DTE yielded the best return on the 16D and 30D trades."*
- Sharpe: best of all IC variants was 16Δ/5Δ managed at 50%-or-21-DTE.
- Volatility: managing at 25% or 50% or 21 DTE cut vol **12.6–40.3%**.
- **56.6% of all profits went to commissions.**
- **None of the 40 variants outperformed buy-and-hold SPY.**
- spintwig's own conclusion: *"Systematically selling iron condors was, on average, more profitable for retail brokers than retail traders."* And, in the study preamble, they ask outright whether the iron condor is *"a strategy invented by brokerages and trading educators to maximize commissions and minimize risk of account blow up in order to extract the most value from account holders?"*

**Result 2 — SPY Short Strangle 45 DTE.** 2007 → 2019.
(https://spintwig.com/spy-short-strangle-options-backtest-results/, 2020-11-26 capture)

This is the one that directly falsifies tastytrade's headline claim:

> **"Managing at 50% max profit or 21 DTE had the worst win rate at each risk level."**

tastytrade's stated reason for the rule is *"Improved Win Percentage."* On real quotes, with commissions, over 12 years of SPY, the rule produced the **worst** win rate at every delta. The mechanism is the one your own straddle test found: you pay a second spread, and at low delta that alone flips winners into losers.

Also from that study:
- Managing at 21 DTE cut portfolio vol **20–34%**, *"because we avoid the steep ramp up in gamma that occurs < 21 DTE."*
- Early management softened worst monthly returns by **35–60%**.
- Cost: *"Implementing early management to reap improved portfolio volatility... comes at the cost of an additional **6.39% to 30.45% of our profits**. Managing trades early is a potentially-expensive activity!"*
- Broker take: ~35% of all strangle profits.

**Result 3 — QQQ Short Put 45 DTE, cash-secured and leveraged.** 2011-04-01 → 2020-09-30. Exits: 50%-or-21-DTE vs hold-to-expiry.
(https://spintwig.com/qqq-short-put-45-dte-cash-secured-options-backtest/ and .../qqq-short-put-45-dte-leveraged-options-backtest/, 2020-12-04 captures)

The cleanest single sentence in the whole literature:

> **"Early management underperformed hold-till-expiration with regard to nearly all key performance indicators (KPIs). The rule of thumb that states early management outperforms holding till expiration did not apply here."**

Specifically: early management lost on win rate, average monthly return, CAGR, annual volatility, Sharpe, premium capture, and total P&L. It won only on capital turnover and trade duration.

**Result 4 — SPY Short Put 45 DTE leveraged.** 2007-01-03 → 2019-07-26, deltas 2.5/5/10/16/30/50, four exit rules.
(https://spintwig.com/spy-short-put-45-dte-leveraged-options-backtest/, 2020-06-13 capture)

- *"Holding till expiration yielded greater profits than managing early on the 2.5D, 5D, 10D and 16D strategies."*
- *"Managing trades early outperformed holding till expiration for the 30D and 50D strategies."*
- Win rate: *"mixed results... tended to perform better with higher-delta positions."*

**Synthesis.** Profit-taking is not a universal improvement; it is a **delta-conditional** one that only turns positive once the credit is large enough to absorb two spreads plus two commissions — roughly 30Δ and up. Below that it is value-destroying. tastytrade promotes it as universal. And note carefully: in every case where 50% management *did* win, the tested rule was "50% **or 21 DTE**, whichever first" — the profit target and the time stop are **confounded in every published study**. Nobody has cleanly separated them. Given that the 21-DTE leg is where the vol reduction demonstrably comes from, the most likely reading is that **the time stop is doing the work and the profit target is along for the ride.**

**Independent, peer-reviewed replication of "manage winners at 50%": none exists.** I searched for it specifically. Not in the academic literature, not from CBOE, not from any non-brokerage institutional source. The claim has never been through peer review, and the only real-quote systematic tests of it (spintwig) contradict it at low delta.

### 3b. Stop loss at 2× credit — UNEVIDENCED

**I could not locate a single credible public backtest of a 2× credit stop on index credit spreads or condors.** Not from tastytrade, not from Option Alpha, not from spintwig, not from academia.

spintwig's site navigation does show trade-log products for **1×, 2×, 3×, 4× and 5× stop loss** variants, and a `/tag/stop-loss/` archive — so the trade logs exist and are purchasable — but the studies tagged there (QQQ short put 45 DTE, SPY wheel, SPY short call 0 DTE) publish only 50%-or-21-DTE vs hold-to-expiry in their results. **The stop-loss grid was generated but the comparison was never written up.** That's the closest thing to a testable dataset and it's behind the store.

The structural argument against stops on short premium is sound and worth stating even without a study:

1. A short option's loss is driven by the underlying moving against you. Index underlyings mean-revert at short horizons far more than they trend.
2. A 2× credit stop triggers deep in the position's left tail — precisely where the conditional probability of recovery by expiry is highest, because there is still time value to decay and the move that caused it is the kind that partially retraces.
3. You pay the full spread at the worst possible moment: stops fire during vol spikes, when spreads are widest and liquidity is thinnest. The realised slippage on a stopped-out condor leg is nothing like the median 1–3% relative spread in calm markets.
4. It converts a bounded-loss defined-risk structure into a path-dependent one, adding a whipsaw failure mode that holding to expiry does not have.

But **this is reasoning, not evidence**, and I'm flagging it as such. Note also that it is *not* symmetric with the profit-target argument: the profit target truncates the tail you get paid for, the stop truncates the tail that can kill you. The right answer is probably "sizing, not stops" — but that too is untested here.

**This is the single biggest hole in the public literature, and it happens to be directly testable on your parquet.** See §6, Test S3.

### 3c. Rolling — FOLKLORE

No study of any provenance — brokerage, vendor or academic — isolates the effect of rolling a tested position versus closing it and opening a fresh one at the same strike/DTE. The two are economically near-identical net of the extra spread on the roll leg, but "roll for a credit" is promoted as if the credit were free money. It is not: the credit is compensation for extending duration and, usually, for taking on a worse strike. Rolling is the highest contracts-per-dollar rule in the entire tastytrade canon and has the least evidence behind it. Treat as unsupported.

### 3d. Hold to expiry — EVIDENCED as the correct default

Three independent strands:

1. **spintwig, real quotes.** Best CAGR for sub-16Δ short puts on SPY (2007–2019) and best on *nearly every KPI* for QQQ short puts (2011–2020). Best Sharpe overall in the QQQ studies was 50Δ hold-to-expiry.
2. **Commission asymmetry.** In spintwig's schedule — which reflects real broker practice — expiring OTM costs **$0.00**, closing early costs a full commission plus a full spread. Holding to expiry is the only exit that is free. For cash-settled index options this is unambiguous.
3. **The benchmark indices do it.** CBOE's PUT (S&P 500 PutWrite) and BXM (BuyWrite) indices — the standard academic and institutional benchmarks for systematic option selling, with history back to 1986 — sell one-month options and **hold them to expiration, rolling only at expiry**. There is no profit target and no time stop in either methodology. Every academic paper that studies the volatility risk premium as a harvestable return stream is studying a hold-to-expiry strategy. *(Methodology stated from the well-established public index rules; I could not fetch Cboe's PDF this session — 403 — so verify before quoting in anything external.)*

**For cash-settled index options specifically** (SPX/NDX/XSP), the usual counter-argument to holding — pin risk and early assignment — **does not exist**. European exercise, cash settlement, no assignment, no residual share position, no pin. spintwig's methodology assumes *"Early assignment of American-style short options never occurs"*, which is a real limitation for their SPY/QQQ studies but is **exactly true by construction for SPX/NDX**. So the case for holding to expiry is *stronger* on cash-settled index products than the ETF-based evidence shows.

### 3e. Close at 21 DTE — EVIDENCED, as a risk rule only

This is the one rule that survives.

- SPY strangles: vol down **20–34%**, worst month softened **35–60%**, mechanism explicitly identified as avoiding the sub-21-DTE gamma ramp.
- SPY iron condors: vol down **12.6–40.3%**.
- Cost: mean return falls, and 6.39–30.45% of profits go to the extra commissions.

**This matches your own result exactly** — mean slightly down, standard deviation halved, worst trade improving from −660% to −212% of credit. Three datasets (your SPY straddles, spintwig's SPY strangles, spintwig's SPY condors), three different structures, same qualitative answer: **21 DTE buys variance reduction and pays for it in mean.** That is a real, replicated, mechanistically-explained effect, and it is the only management rule in the tastytrade canon I'd call evidenced.

Your finding that **21/30/45 is a flat plateau with no optimum** is important and is *not* contradicted by anything in the literature — spintwig never scanned the DTE-exit parameter, they only ever tested 21. The absence of an optimum is the expected result if the effect is "get out before terminal gamma" rather than "21 is special." **21 is not a magic number; it is a round number inside a wide flat region.** Anyone presenting 21 as optimised is overfitting to a plateau. Given the flatness, choose the exit DTE on operational grounds (liquidity, roll calendar, spread width) rather than on backtested return.

---

## 4. Reconciling your straddle result

Your finding — 213 non-overlapping SPY straddles, 50% profit target moved results from **+2.21% to −0.23%** — is consistent with the best independent evidence and I'd defend it over tastytrade's claim without hesitation.

- It matches spintwig's SPY strangle result that 50%-or-21-DTE had *the worst win rate at every risk level*.
- It matches spintwig's QQQ finding that early management lost on nearly all KPIs.
- Your stated mechanism — *caps winners while leaving every loser intact and pays a second round of spread* — is exactly spintwig's mechanism, independently derived. They quantify the second-spread cost at 6.39–30.45% of profits.

Two things strengthen your result relative to the published ones:

1. **You used non-overlapping trades.** spintwig opens a position every trading day, which controls timing luck but produces massively overlapping, autocorrelated observations — their headline stats have far fewer effective degrees of freedom than the trade counts (120,700 etc.) imply. Your 213 independent trades support honest inference; their 120,700 do not, and they never report a standard error or a t-statistic on any comparison. **No published option-management study I found reports statistical significance on the management comparison. Not one.**
2. **Straddles are the cleanest test case.** ATM, maximum vega and gamma, largest credit relative to spread — the structure most favourable to profit-taking surviving costs. If 50% management fails on straddles, it fails a fortiori on lower-delta structures where the credit is smaller relative to the spread.

One caveat to keep honest: 213 trades with a mean effect of ~2.4 percentage points is a modest sample, and you should confirm the +2.21% baseline is itself distinguishable from zero before concluding the target "destroyed" an edge. Your own note that the DTE plateau is *"indistinguishable from zero"* suggests the baseline may not be significant either — in which case the correct statement is **"the 50% target does not help, and the underlying edge is not established"**, which is a different and more defensible claim than "the target hurt."

---

## 5. THE LONG SIDE — priority section

This is where the literature is thinnest and where your data gives you a genuine advantage.

### 5.1 Why short-side rules must not be copied over

The expected-return drift flips sign:

- **Short premium** carries a **positive** expected drift (the volatility risk premium — the reason the CBOE PUT index has a positive long-run return). Holding longer collects more of it. A profit target truncates a positive-drift, left-skewed process at the top while leaving the bad tail fully exposed. That is why it destroys EV, and it is exactly what you measured.
- **Long premium** carries a **negative** expected drift — the same VRP, paid rather than earned. Coval & Shumway, *"Expected Option Returns"*, Journal of Finance 56(3), 2001, established that index option positions earn returns inconsistent with pure risk compensation and that long positions systematically lose; the result has been reproduced repeatedly since (Bondarenko; Broadie, Chernov & Johannes). *(Citation from standing knowledge — I could not re-fetch it this session, JSTOR/Wiley both blocked. Verify before external use.)*

**Consequences, and they are the opposite of the short-side folklore:**

| Rule | Short premium | Long premium |
|---|---|---|
| Profit target | Harmful (truncates the drift you're paid) | **More harmful** — the right tail is the *only* source of return |
| Time stop | Costly (forgoes drift), buys variance reduction | **Beneficial** — every extra day is negative carry paid |
| Stop loss | Likely harmful (mean reversion, wide spreads) | **Plausibly beneficial** — the left tail is a one-way theta bleed with falling recovery odds |
| Hold to expiry | Correct default | **Wrong default** — maximises exposure to negative carry and terminal theta |

A profit target on a long option is the **same structural error** you identified on the straddle — cap the winners, keep the losers — but strictly worse, because for a short option the capped right tail is only part of the return, whereas for a long option the right tail *is* the entire investment case. If your directional edge is real, a profit target is the fastest way to destroy it.

**Prediction to test and, I expect, to kill: a profit target on your long calls will reduce mean return at every delta.**

### 5.2 What your own numbers already tell you

Your result — fixed 21-session hold, 60–68% win rate, deeper ITM higher, 0.16Δ only 29–43% — is exactly what the mechanics predict, and it contains a trap:

**Win rate is nearly uninformative about edge on the long side.** A 0.90Δ 45-DTE call is roughly 90 shares of SPY plus a small time-value drag. Its win rate should be about SPY's 21-session up-rate (~60%) minus theta — which is precisely what you measured. **That 60–68% is not evidence of an edge; it is evidence that deep-ITM calls track the underlying.** Meanwhile the 0.16Δ call needs a large move just to clear its own premium, so 29–43% is also mechanical. The delta gradient in your win rates is a restatement of the delta gradient in breakeven distance, not a signal.

**What you need to compare instead:** mean return per trade, the full return distribution, and — critically — **the option's return against a delta-matched underlying position over the identical window.** If the 0.90Δ call doesn't beat 90 shares of SPY after spreads, the option is a financing decision, not an edge, and no exit rule will fix it. Run that benchmark before optimising any exit.

There is also a nice coincidence worth naming: a 45-DTE entry held 21 sessions exits around 21–24 DTE — the same landing zone as the short-side rule, but **for the opposite reason.** Short sellers leave at 21 DTE to escape the gamma ramp; long holders should leave at 21 DTE to escape the theta ramp. Same door, opposite direction, and both are consequences of the same convexity blow-up near expiry. Your existing rule is better-founded than you may have realised.

### 5.3 The one on-point published long-side study — and it's paywalled

**spintwig, "Long SPX Call 45-DTE Options Backtest", published 2025-10-31.** https://spintwig.com/long-spx-call-45-dte-options-backtest/

This is the closest thing that exists to what you're asking for:

- Underlying SPX (cash-settled, European — no assignment noise), 2007-01-03 → 2025-06-30.
- **83,300 trades**, 18 backtests, one position opened every trading day.
- Deltas 5 / 10 / 16 / 30 / 50 / **90**.
- Exit rules tested, exactly the three that matter to you:
  1. **10% gain on premium paid, or 21 DTE, whichever first**
  2. **50% gain on premium paid, or 21 DTE, whichever first**
  3. **Hold to expiration**
- ORATS data, real bid/ask, published slippage function, $1.32/contract index commissions, T-bill collateral.

**Results are behind the $249/yr subscription.** Two things are readable for free and both are informative:

- The Discussion section analyses **the 90-delta trade** as the representative case — the same deep-ITM structure your own tests found winning most often. A researcher picks the variant worth discussing.
- The study reports a **"Realized Drawdown"** metric that the short-option studies don't carry, which implies the exit rules produced materially different drawdown paths.

**Recommendation: this is the one purchase worth making.** $249 buys you an 83,300-trade, 18-year, real-quote, daily-entry benchmark on SPX for precisely the three exit rules you're choosing between, from a non-brokerage source that has repeatedly published results embarrassing to the industry. Alternatively the individual trade logs are sold separately from ~$9.99 in their store, which may be enough — and buying the logs means you can re-run the analysis yourself rather than trusting their summary. Either way it costs less than one day of the work of rebuilding it, and it gives you an out-of-sample check on SPX against your SPY results.

### 5.4 Academic literature on optimal stopping for option positions

Thin, and mostly not about what you need — but two verified, directly relevant results:

**Leung & Ludkovski, "Optimal Timing to Purchase Options."** *SIAM Journal on Financial Mathematics* 2(1): 768–793, 2011. arXiv:1008.3650. *(Verified this session.)*
Formal optimal-stopping treatment of when to buy an option when the investor's pricing measure differs from the market's. Introduces the **"delayed purchase premium"** — the value of waiting, driven by the stochastic bracket between market and investor risk premia. Covers rolling long-dated options and sequential trading. This is the correct theoretical frame for long-premium entry timing, and it establishes that the optimal policy is a **threshold rule in the investor's own mispricing estimate**, not a fixed calendar rule. Practical implication for you: your exit rule should ideally be indexed to *your* estimate of value versus market price, not to a fixed session count.

**Leung & Zhang, "Optimal Trading with a Trailing Stop."** *Applied Mathematics & Optimization*, 2019 (DOI 10.1007/s00245-019-09559-0). arXiv:1701.03960. *(Verified this session.)*
Optimal double-stopping analysis of selling after a pre-specified percentage drawdown. **Proves the optimality of combining a sell limit order with a trailing stop** — i.e. a trailing stop is optimal *paired with* a profit-side limit, not alone. **Important caveat before you apply this:** the result is derived under an exponential Ornstein–Uhlenbeck (mean-reverting) model. A long SPY call is not mean-reverting in that sense, so the theorem does not transfer directly. It does establish that trailing stops are theoretically respectable — which is more than can be said for fixed 2× credit stops — and it tells you the right functional form to test: **trailing stop plus profit-side limit as a pair, not either alone.**

Beyond these, there is a large optimal-stopping literature on *American option exercise* which is a different problem (when to exercise a contract you hold, under no-arbitrage), and essentially nothing peer-reviewed on the retail question of "when to close a short credit spread." **That absence is itself the finding:** the rules the retail options industry runs on have never been examined by anyone without a commercial stake in the answer.

---

## 6. What you can test directly on `SPY_options.parquet`

### 6.1 Verified data profile

Path: `/Users/sahilmajmudar/index-daytrading/data/opt_eod/SPY_options.parquet`

- **24,681,665 rows**, 50 row groups. `2008-01-02 → 2025-12-12`.
- Calls 12,340,771 / puts 12,340,894.
- Columns: `contract_id, symbol, expiration, strike, type, last, mark, bid, bid_size, ask, ask_size, volume, open_interest, date, implied_volatility, delta, gamma, theta, vega, rho, in_the_money`.
- **Contract tracking works.** `contract_id` is the OCC symbol (`SPY190215C00250000`), stable across dates. Sampled 300 contracts: median daily coverage over their life **0.969** (`np.busday_count` doesn't exclude market holidays, so true coverage is effectively complete). You can follow any position day by day without a join hack.
- **Greeks are complete.** NaN rate for `delta`, `theta`, `bid`, `ask` in 0–62 DTE calls: **0.0000**.
- 28–62 DTE call rows: **1,831,853** across **4,513 distinct dates** — full daily entry coverage for the whole period.
- **Median relative bid/ask spread**, 28–62 DTE calls: 0.16Δ **2.60%**, 0.30Δ **1.42%**, 0.50Δ **0.82%**, 0.65Δ **1.11%**, 0.80Δ **1.35%**. Zero-bid rate in that window ≈ 0 (9.7% across *all* 0–62 DTE calls, concentrated in deep OTM near expiry).
- **Expiration availability by year:** 28–32 distinct expirations in 2008–09 (**monthlies only**), 54–79 in 2010–15, 99–198 in 2016–22, 271–286 in 2023–25.

### 6.2 Non-negotiable execution assumptions

These decide the answer more than the rule does. Get them wrong and you reproduce tastytrade's result.

1. **Never mark at mid.** Buy at `ask`, sell at `bid`. Parameterise as spintwig does — `buy = bid + s×(ask−bid)`, `sell = ask − s×(ask−bid)` — and report **`s = 1.0` as the headline** with `s = 0.5` (mid) shown only as an unattainable upper bound. Every rule that closes early pays this twice; that is the whole mechanism behind your straddle result and it must not be assumed away.
2. **Commissions:** $0.65/contract each way, and **$0.00 for expiring OTM.** The zero-cost expiry is not a rounding detail — it is a structural advantage of holding that spintwig's 56.6%-of-profits-to-commissions figure shows dominating iron condor economics.
3. **Overlap.** Daily entry gives you 4,513 entries but they are heavily autocorrelated. Report the daily-entry mean for stability, but do **all inference** on non-overlapping blocks (as you already did with 213 straddles) or with Newey–West errors at lag = holding period. Report a t-statistic on every rule-vs-baseline comparison — no published study does, and that is why this whole literature is unfalsifiable.
4. **Pre-2010 caution.** Only monthlies exist in 2008–09. A 45-DTE ±17-day tolerance is fine throughout, but any sub-14-DTE study is invalid before ~2011.
5. **Regime split.** Report 2008–2012 / 2013–2019 / 2020–2025 separately. A rule that only works in one is overfitted.

### 6.3 Test specifications

**Priority order: L1 → L2 → L3 → S3. The long-side tests are the ones that answer a question nobody has publicly answered.**

---

**Test L1 — Long-call exit-rule horse race (highest value).**

*Question:* does any exit rule beat your fixed 21-session hold?

- Universe: calls, `dte ∈ [40, 50]` at entry, entry every trading day 2008–2025.
- Delta buckets at entry: 0.16 / 0.30 / 0.50 / 0.65 / 0.80 / 0.90 (nearest within ±0.03).
- Buy at `ask` + commission. Follow via `contract_id`.
- Exit rules, all on the **same entries** so the comparison is paired:
  - **B (baseline):** hold exactly 21 trading sessions.
  - **T1:** hold to `dte ≤ 21`.
  - **T2:** hold to expiry (settle at intrinsic).
  - **P1/P2/P3:** profit target at +25% / +50% / +100% of premium paid, else 21 sessions.
  - **S1/S2:** stop at −30% / −50% of premium paid, else 21 sessions.
  - **TS:** trailing stop, exit on a 30% retracement from the position's running-max `bid`, else 21 sessions.
  - **TS+L:** trailing stop **paired with** a +100% profit-side limit — the Leung–Zhang form.
  - **D1:** delta exit — close when `delta` falls below 0.35 (thesis invalidated) or rises above 0.85 (converted to synthetic stock, no convexity left to pay for).
- Report per rule per delta: mean return, median, SD, win rate, worst trade, Sharpe on non-overlapping blocks, **and a paired t-stat vs baseline B**.
- **Falsifiable predictions:** P1–P3 reduce mean return at every delta (this kills the profit-target folklore on the long side). S1/S2 and TS improve Sharpe but reduce mean. T2 is worst on every metric.

---

**Test L2 — Is the option even worth buying? (Run this before optimising anything.)**

For every L1 entry, compute the return of a **delta-matched SPY share position** held over the identical window, financed at the 3-month T-bill rate. If the option doesn't beat delta-matched shares after spreads, the exit rule is irrelevant — the structure is the problem. Report the option-minus-shares spread by delta bucket. **Expect the 0.90Δ calls to lose narrowly and the 0.16Δ calls to lose badly**; if 0.16Δ *wins*, you have found something genuinely unusual and should be extremely suspicious of the data before believing it.

---

**Test L3 — Where does the negative carry actually bite?**

Decompose each long-call trade into delta P&L, theta P&L and vega P&L using the stored greeks, bucketed by DTE-at-the-time. This locates the exact DTE at which the theta ramp overwhelms the directional edge — which is the *principled* version of "exit at 21 sessions" and will tell you whether your plateau is flat because the ramp is gradual or because there's no edge to protect. Cheap to run, and it converts a calendar heuristic into a mechanism.

---

**Test S3 — The 2× credit stop (fills the literature's biggest hole).**

*Question:* nobody has published this. You can be the first to do it on real quotes.

- Structure: SPY short put vertical, short leg 0.16Δ and 0.30Δ, long leg 5 strikes lower, `dte ∈ [40, 50]`, daily entry.
- Sell short leg at `bid`, buy long leg at `ask`; reverse to close. $0.00 on OTM expiry.
- Exits: hold-to-expiry / stop at 1×, 2×, 3× credit / 50% profit target / 50%-or-21-DTE / 21-DTE-only.
- **Critical:** report the realised spread paid *at the moment the stop fired* separately from the median spread. The whole cost of a stop is that it triggers when spreads are widest, and averaging that into a global slippage constant hides it. This is the number no published study reports.
- Report expectancy, win rate, worst trade, and the full loss distribution — the claim to test is that stops trade a better worst-case for a worse mean.

---

**Test S4 — Decouple the profit target from the time stop.**

Every published study confounds them ("50% **or** 21 DTE"). Run the 2×2: {no target, 50% target} × {no time stop, 21-DTE stop} on identical entries. This single 2×2 settles a question the entire public literature has left open, and given §3e I'd expect it to show **the time stop carrying all of the benefit and the profit target contributing nothing or less.**

---

## 7. Source register

| # | Source | Who funded it | Do they sell the strategy? | Sample & underlying | Real quotes or mid? | Slippage | Weight |
|---|---|---|---|---|---|---|---|
| 1 | tastylive "Managing Winners" concept page | tastylive, Inc. | **Yes — owns the brokerage; paid by it to market it** | **Not stated** | **Not stated** | **Not stated** | **Zero. Assertion, not evidence.** |
| 2 | tastytrade *Market Measures* / *Skinny on Options* episodes (2015, 2016, 2021, 2023) | same | same | Not published | Not published | Not published | **Zero — unreproducible by construction** |
| 3 | spintwig SPY Short Iron Condor 45 DTE | spintwig LLC | Sells trade logs ($9.99–$485), custom backtests ($99+), $249/yr subs; ORATS affiliate | SPY, 2007-01-03→2019-07-19, 120,700 trades, 40 variants | **Real bid/ask (ORATS), no modeled pricing** | Published function; table values not extracted | **High** |
| 4 | spintwig SPY Short Strangle 45 DTE | same | same | SPY, 2007→2019 | Real bid/ask | same | **High** |
| 5 | spintwig SPY Short Put 45 DTE leveraged | same | same | SPY, 2007-01-03→2019-07-26, 6 deltas × 4 exits | Real bid/ask | same | **High** |
| 6 | spintwig QQQ Short Put 45 DTE (CS + leveraged) | same | same | QQQ, 2011-04-01→2020-09-30 | Real bid/ask | same | **High** |
| 7 | spintwig Long SPX Call 45 DTE | same | same | SPX, 2007-01-03→2025-06-30, 83,300 trades | Real bid/ask | same | **High — but results paywalled at $249/yr** |
| 8 | spintwig methodology page | same | same | n/a | Declares empirical-only, no modeled pricing | Explicit formula | Reference |
| 9 | CBOE PUT / BXM indices | Cboe (exchange — earns on volume, but indices are rule-based and public) | No | SPX, 1986→ | Index rules, settlement prices | n/a | **High for "hold to expiry is the benchmark"** — *methodology quoted from standing knowledge, PDF fetch 403'd* |
| 10 | Leung & Ludkovski (2011), *SIAM J. Finan. Math.* 2(1):768–793 | Academic, peer-reviewed | No | Theoretical | n/a | n/a | **High** (verified) |
| 11 | Leung & Zhang (2019), *Appl. Math. Optim.* | Academic, peer-reviewed | No | Theoretical, exp-OU | n/a | n/a | **Moderate** — mean-reverting model, doesn't transfer cleanly (verified) |
| 12 | Coval & Shumway (2001), *J. Finance* 56(3) | Academic, peer-reviewed | No | S&P index options | Market prices | n/a | **High** — *citation from standing knowledge, could not re-fetch (JSTOR/Wiley blocked); verify before external use* |
| 13 | Option Alpha | Sells software + education | **Yes** | — | — | — | **Nothing located this session; would carry the same conflict class as tastytrade** |
| 14 | Your SPY straddle test | You | No | SPY, 213 non-overlapping trades | Real quotes | Real | **Highest — no conflict, non-overlapping, honest costs** |

### Search limitations, stated honestly

WebSearch quota was exhausted early in this session. Findings were assembled by direct fetch: Brave and Bing were partially reachable then rate-limited, DuckDuckGo/searx/Ecosia/Startpage/Mojeek all returned captchas or 403s, Reddit and JSTOR/Wiley are blocked to this tool, SSRN returned 403, and the arXiv API rate-limited. spintwig blocks WebFetch (403) but serves plain curl, and its pre-2021 free studies were recovered through the Wayback Machine CDX API. **The main consequence: I could not run a broad sweep for independent replications, so "no independent replication exists" should be read as "none surfaced through a targeted search of the obvious venues" — strong evidence of absence given where I looked, but not exhaustive.** Two other specific gaps: spintwig's slippage *table values* are rendered as an image and were not extracted (the formula is confirmed, the constants are not), and Option Alpha's research was not reachable at all.

---

## 8. Recommended position

1. **Drop the 50% profit target on short premium.** Your data says it, spintwig's SPY strangles say it ("worst win rate at each risk level"), spintwig's QQQ study says it. It is a brokerage rule that increases round-trips, and its only published support is unreproducible video from the firm that clears the trades.
2. **Keep the 21-DTE exit, and describe it accurately** — a variance-reduction rule that costs mean return, sitting on a flat plateau with no optimum. Do not present 21 as optimised.
3. **Do not adopt a 2× credit stop** until Test S3 runs. There is no public evidence for it in either direction, which given how universally it is recommended is remarkable.
4. **Ignore rolling advice entirely** until someone isolates it. Highest contracts-per-dollar, lowest evidence.
5. **Hold to expiry is the correct default for cash-settled index options** — free OTM expiry, no assignment, no pin, and it is what every benchmark index does.
6. **On the long side, invert the folklore.** Time stops and stops are defensible; profit targets are not. Your 21-session hold is better-founded than you thought — it exits ahead of the theta ramp for the mirror-image reason short sellers exit ahead of the gamma ramp.
7. **Run Test L2 before optimising any long-side exit.** If the calls don't beat delta-matched shares after spreads, no exit rule will save them, and 60–68% win rates on deep-ITM calls are measuring SPY's up-rate, not an edge.
8. **Consider buying the spintwig long SPX call trade logs.** It is the only 18-year, 83,300-trade, real-quote, non-brokerage test of exactly your three candidate long-side exit rules, and buying the logs rather than the summary lets you verify it yourself.
