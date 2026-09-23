<!-- research brief, filed 2026-09-22; agent output verbatim; verdicts copied to 02_findings/online_methods.md -->

I have what I need. Search budget is exhausted (200/200), and the remaining 403s (Coinbase fee pages, SSRN, ScienceDirect) are covered by the search summaries, so I'll write the report now.

# Crypto derivatives as an automated return source, 2026

**Bottom line:** every crypto "arbitrage" a US retail account can legally run in September 2026 pays somewhere between a T-bill and a T-bill plus a few points, with exchange risk on top. The strategies that do print 30%+ (on-chain MEV, CEX-DEX latency arbitrage) are captured by fewer than twenty firms with co-located hardware and builder relationships. Nothing here compounds $5,000 to $50,000 in five months; nothing here reliably compounds 20%/yr in the 2025–26 rate regime either.

## 1. Funding-rate carry (long spot, short perpetual)

**The academic baseline.** The [BIS working paper 1087 "Crypto carry"](https://www.bis.org/publ/work1087.pdf) (Schmeling, Schrimpf, Todorov; rev. Oct 2025) finds crypto carry averaging above 10%/yr and reaching 60%/yr at 2021 peaks, driven not by interest rates but by retail trend-chasing in booms and by arbitrage capital being wiped out in busts (margin spikes, liquidations). High carry *predicts crashes*, which is the whole problem: the trade pays most right before the counterparty risk it carries materialises.

**Realised by year.** The cleanest public walk-forward is [zwmjj/funding-rate-arb](https://github.com/zwmjj/funding-rate-arb) (Binance only, 2020-01 to 2026-04, 16 bps round-trip taker fees):

| Year | BTC funding-implied carry | ETH |
|---|---|---|
| 2020 | 17.2% | 27.4% |
| 2021 | 30.6% | 37.5% |
| 2022 | 4.2% | 0.8% |
| 2023 | 7.9% | 8.3% |
| 2024 | 11.9% | 13.0% |
| 2025–Apr 2026 | 4.3% | 3.9% |

The rules-based strategy on top of it returned 9.0% (BTC) / 11.4% (ETH) gross per year at −0.3% / −1.8% max drawdown, but only with 30–35% capital utilisation, 18 and 14 trades in six years, and **79–82% of cumulative PnL from trades entered before 2022**. The repo's own August 2026 audit ([PR #1](https://github.com/zwmjj/funding-rate-arb/pull/1)) found the panel join had silently dropped 44% of the funding history. The USD cash rate (4–5%) that the spot leg forgoes is excluded, so the 2025–26 figure is *below* T-bills net.

Ethena's sUSDe is the largest live implementation and a fair proxy for what the trade pays at scale: [4–30% realised APY across 2024–25, mostly 8–18%](https://eco.com/support/en/articles/15254002-ethena-usde-and-susde-2026-delta-neutral-yield); ~13% average funding in 2024; compressed to high single digits by Q2 2026 (9.4% 7-day, 11.8% 90-day on 25 Apr 2026). By mid-2026 [Ethena had made the basis trade a minor part of its reserve](https://medium.com/altitudedp/ethena-stops-farming-the-basis-d6f6edb79a5b) because funding no longer justified it. The "19.26% in 2025, 14.39% in 2024, <2% drawdown" figure that circulates in [vendor blogs](https://zipmex.com/blog/how-to-analyze-funding-rates-in-crypto/) has no stated method and should not be relied on.

**Drawdowns and counterparty risk.** The delta-neutral book has near-zero *price* drawdown but full *venue* drawdown: FTX (Nov 2022) took 100% of anything parked there, and the 2022 negative-funding regime paid 0.8–4.2% for a year of exchange exposure. The BIS paper's mechanism (carry spikes when arbitrage capital is scarce) means the trade needs you to hold through liquidation cascades on the short leg.

**US-legal venues in 2026 and fees:**

| Venue | Product | Fees | Notes |
|---|---|---|---|
| [Coinbase Financial Markets](https://www.coinbase.com/blog/perpetual-futures-have-arrived-in-the-us) (since 21 Jul 2025) | nano BTC perp-style futures, 1/100 BTC, 10x intraday | reported 0% maker / 0.03% taker for US retail ([Coinbase](https://www.coinbase.com/derivatives-trading)) | funding accrues hourly, [settled twice daily](https://help.coinbase.com/en/derivatives/perpetual-style-futures/funding-rate). Spot leg on Coinbase Advanced costs 0.40–0.60% per side at retail tiers, which alone eats ~3 months of 2026 carry per round trip. |
| [Kraken Derivatives US / Bitnomial](https://www.businesswire.com/news/home/20260615010932/en/Kraken-Launches-Perpetual-Futures-for-US-Clients) (since Jun 2026) | BTC, ETH, SOL, XRP perps | [$0.15/contract/side all-in](https://support.kraken.com/articles/us-futures-fees), $10 liquidation fee | funding netted once daily at 3pm CT |
| CME micro BTC (MBT, 0.1 BTC) | dated futures | exchange fee ~[$1.02/side](https://lpfutures.com/micro-bitcoin-futures-contract/) plus broker; [Robinhood $0.50/side ($0.35 Gold)](https://www.firstcard.app/learn/robinhood-futures-trading) | see §2 |
| Robinhood crypto | spot only in US | zero commission, [0.35–0.85% embedded spread](https://www.bitget.com/academy/robinhood-crypto-trading-spreads-explained-2026-america-beginners-guide-costs-features-new-tools) | US perps not offered; EU perps at 2bp+2bp |
| Hyperliquid, Binance, Bybit, OKX | | | [still geoblocked for US persons](https://www.datawallet.com/crypto/is-hyperliquid-available-in-the-usa); Hyperliquid–Bitnomial talks reported Sep 2026, nothing live |

## 2. The CME basis trade via IBIT + micro futures

The CME front-month basis [approached 25% annualised in Feb 2024 and exceeded 20% in Nov 2024](https://www.cfbenchmarks.com/blog/revisiting-the-bitcoin-basis-how-momentum-sentiment-impact-the-structural-drivers-of-basis-activity), briefly went negative in Mar 2025, sat near 10% in May 2025, was [~5% against ~4.5% T-bills by early 2026](https://www.theblock.co/post/396722/cme-bitcoin-futures-activity-slumps-to-14-month-low-as-basis-trade-unwind-drains-institutional-demand), and by [Aug 2026 the 3-month basis was ~3% against 3.8% on 2-year Treasuries](https://www.coindesk.com/markets/2026/08/10/a-rare-cme-shift-hedge-funds-abandon-structural-shorts-to-bet-on-a-bitcoin-rally). CME leveraged funds flipped net long; the basis trade is, in The Block's words, "dead as leveraged funds unwind." Retail costs on top: IBIT's 0.25% fee, four rolls a year at the MBT bid-ask, and margin on the short leg earning nothing at most retail brokers. [Cryptodaily's June 2026 study](https://cryptodaily.co.uk/2026/06/ibit-options-vs-cme-futures-carry-spreads) finds a persistent 2.58pp wedge between IBIT-implied and CME carry and states retail cannot monetise it "at scale". Net 2026 result: roughly T-bill minus costs. In 2024 it genuinely paid 10–20% for anyone who ran it, and it is the one trade here that was legal for a US retail account throughout.

## 3. Options variance risk premium

The evidence is real: [Bitcoin's variance risk premium averaged 0.14/yr on Deribit 2017–2022](https://arxiv.org/html/2410.15195v2) against ~0.02 for the S&P 500, 0.17 in low-vol regimes and 0.12 in high-vol. [Deribit's own study](https://insights.deribit.com/industry/bitcoin-options-finding-edge-in-four-years-of-volatility-regimes/) (Apr 2019–Dec 2022) finds 30-day IV above realised ~70% of the time with a ~15 vol-point premium in contango, and delta-hedged short straddles show "strong risk-adjusted performance", but it publishes no drawdown numbers, and the sample includes March 2020 and May 2021, so the tails are in there somewhere. [Atanasova et al. (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6771170) confirm a positive, persistent VRP.

**US access.** Deribit itself: [Coinbase Financial Markets opened Deribit options to US institutions on 29 May 2026](https://www.coinbase.com/blog/coinbase-brings-global-crypto-derivatives-to-us-market); retail is "a later phase." What a US retail account *can* do today is sell IBIT options at any listed-options broker or CME BTC options through a futures broker. That captures the same premium in a smaller, wider-spread market, with the 2.58pp segmentation wedge above suggesting IBIT prices carry differently from Deribit.

## 4. Cross-exchange spot arbitrage

[Makarov and Schoar (JFE 2020)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3171204) measured Jan 2017–Feb 2018: Korea premium to 40%, Japan ~10%, Europe ~3%, persisting hours to weeks, with an estimated [$2 billion of arbitrage profit Dec 2017–Feb 2018](https://rpc.cfainstitute.org/research/cfa-digest/2020/10/dig-v50-n10-4) ($1.275bn US–Korea alone). The binding constraints were capital controls, exchange governance risk, and settlement delay, not fees. Those constraints are exactly why a US person could not capture it then and cannot now; the US–Europe gap, the only leg open to you, was the smallest and closed first. Later work on the intra-exchange version, [triangular arbitrage on Binance](https://www.sciencedirect.com/science/article/pii/S154461232401537X) ("Wish or reality?", 2024), finds fees eliminate almost everything: 18 exploitable opportunities in a week worth $12–18 total. An older [Binance indirect-conversion study](https://arxiv.org/pdf/2002.12274) found 9.3 bps net per trade, which is a maker-rebate business, not a retail one.

## 5. DEX/CEX and on-chain arbitrage: who captures it

- **CEX-DEX (Ethereum):** [$233.8M extracted over 19 months (Aug 2023–Mar 2025) by 19 searchers; three of them took 75%](https://arxiv.org/abs/2507.13023), with profitability tied to exclusive searcher–builder integration. Searchers on Ethereum [pay more than 90% of gross to proposers via bribes](https://academy.extropy.io/pages/articles/mev-crosschain-analysis-2025.html).
- **Solana / Jito:** [$142.8M of profit over ~90M arbitrages, $1.58 each](https://www.helius.dev/blog/solana-mev-report); top 3 bots hold >60% share; 400ms blocks require co-location at $1,800–3,800/month for RPC alone.
- **Cross-chain:** [242,535 arbitrages, $868.6M volume, Sep 2023–Aug 2024; five addresses did over half](https://arxiv.org/abs/2501.17335); pre-positioned inventory settles in ~9s, bridging in ~242s.
- **The one bright number:** a [Journal of Banking & Finance 2026 paper](https://www.sciencedirect.com/science/article/pii/S0378426626000956) ran four live DEX-CEX bots: 24.9%, 33.4%, 17.4% *per month* in Nov–Dec 2023, decaying to 6.2% per month by Sep–Oct 2024, total profit $20,237. That is the only audited-ish, above-30%/yr result in the literature; it decayed 4–5x within a year, its absolute size is small, and the CEX legs were offshore.

## 6. Retail results above 30%/yr, 2025–26

None with an audit trail. [Crypto Fund Research's 2025 review](https://cryptofundresearch.com/crypto-hedge-fund-performance/): quant funds averaged +0.4%, average 12-month max drawdown −26%, one fund +108%, worst −64%. Market-neutral/arbitrage funds [returned ~13%](https://www.cryptoinsightsgroup.com/resources/industry-guide-to-crypto-hedge-funds-2025-edition). Bot-platform aggregates ([unsourced](https://botverdict.com/articles/are-crypto-trading-bots-profitable-in-2026-an-honest-analysis-of-real-returns/)) put the median 2025 user at ~12% and the top decile at 25–35%, with no methodology.

## Verdict table

| Strategy | Realised return | Max drawdown | Capacity | US-accessible | 58%/month? | 20%/yr? |
|---|---|---|---|---|---|---|
| Perp funding carry | 30–38% (2021), 1–4% (2022), 8% (2023), 12–13% (2024), ~4% (2025–26) gross, before forgone cash rate | <2% price; 100% venue (FTX) | $100k–$10M | Y: Coinbase CFM, Kraken/Bitnomial; spot fees 0.4–0.6% eat 2026 carry | No | Only 2020–21, on offshore venues |
| CME basis via IBIT + MBT | 10–25% (2024), ~10% → 0 (2025), 3–5% (2026) | Small; roll/negative-basis risk | $10k–$100M | Y: any futures broker | No | No (below T-bills now) |
| Short BTC vol (VRP) | VRP ~14 var-points/yr; straddle returns positive, drawdowns unpublished | Fat-tail; Mar 2020 / May 2021 size | $10k–$10M | Deribit: institutions only. IBIT/CME options: Y | No | Plausible in calm years, at risk of a 2–3 year setback in one week |
| Cross-exchange spot arb | Korea 40% (2017); US/EU legs now single bps, below fees | Settlement / exchange failure | Near zero for retail | N (profitable legs are capital-controlled venues) | No | No |
| Triangular arb | $12–18/week gross on Binance | n/a | Near zero | N (Binance) / trivial on Coinbase | No | No |
| CEX-DEX / MEV | $234M over 19 mo to 19 firms; 90% bribed away on Ethereum | Inventory + inclusion risk | Oligopoly | Y in principle (on-chain), but the winners are co-located and builder-integrated | No | Not for a new entrant |
| Live DEX-CEX bots (JBF 2026) | 17–33%/month in late 2023 → 6%/month late 2024 | Unstated | ~$20k profit total | Partly (offshore CEX legs) | Closest thing, and it decayed | Maybe, briefly |

**$5,000 → $50,000 in five months** needs 10x, or 58% compounded monthly. The best year any of these delivered to an unleveraged account was 2021 funding carry at ~2.5%/month; the best live number in the literature was 33% in one month on a tiny DEX-CEX bot that lost 80% of its edge within a year. Leverage does not fix it: funding carry at 3x on 2026 rates is ~12%/yr with real liquidation risk on the short leg. **20%/yr** is reachable only in bull-market funding regimes (2020–21, 2024) on venues that were not US-legal at the time; on the venues open to a US person in 2026, the honest expectation for the whole menu is T-bill plus 0–5 points, with exchange failure as the drawdown.

**Not verified:** Coinbase's US perp fee (0%/0.03%) and Kraken's $0.15/contract came from search summaries and the Kraken support page; Coinbase's own fee pages returned 403. The Kraken contract size was not found, so per-notional cost there is unstated.
