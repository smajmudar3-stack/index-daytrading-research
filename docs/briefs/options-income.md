<!-- research brief, filed 2026-09-23; agent output verbatim; verdicts copied to 02_findings/online_methods.md -->

Everything needed is in hand. Implied financing from the Dec-2027 SPY quotes (4:14 pm ET, 22 Sep 2026, SPY 773.38, 451 days): 600-strike call mid 214.68 / put mid 12.65 gives C−P = 202.04, so K·e^(−rT) = 571.35 and r = 3.96%/yr net of dividends; 500-strike gives 3.81%. Buying the 600 call at the ask (217.00) you pay 43.62 of extrinsic on a 600 borrow over 1.24 years = 5.9%/yr all-in, of which ~1.7%/yr is the embedded put. The bid-ask on that call is 4.64 (2.1% of premium). A 0.9-delta SPY LEAPS costs about $21,500, so a $5,000 account cannot buy one.

# Systematic options strategies with a public record, judged against $5k→$50k in 5 months (58%/month) and 20%/year

**Bottom line first.** Nothing with a public track record compounds at 58% a month. The best-documented option strategies earn 5–10% a year gross with 20–35% drawdowns; the strategies that *look* like they earn more (0DTE selling, earnings straddles) are negative once the bid-ask is paid. For 20%/year the only honest route in this list is leverage on the index (2× exposure via LEAPS or margin), which reaches that level only in good years and carries a 50–60% drawdown. Our own real-quote measurement of a 15-delta SPY put-write (2019–2026, sold at the bid) was **4.7%/yr, max DD −3.3%, Sharpe 2.07** — a yield, not a growth path ([02_findings/online_methods.md](/Users/sahilmajmudar/index-daytrading-dev/02_findings/online_methods.md)).

## 1. The CBOE benchmarks

All figures are gross, pre-tax index values with no bid-ask; [CXO Advisory](https://www.cxoadvisory.com/equity-options/performance-of-cboe-putwrite-indexes/) notes ETPs tracking BXM "substantially underperform" the index, and WisdomTree's PUTW returned 6.90%/yr from Feb 2016 to end-2019 against 16.65% for the S&P ([SEC 497K](https://www.sec.gov/Archives/edgar/data/1350487/000119312521369019/d255515d497k.htm)).

| Index | Period | CAGR | Vol | Max DD | Sharpe | S&P 500 same period |
|---|---|---|---|---|---|---|
| PUT (ATM monthly put-write) | Jun 1986–Dec 2018 | 9.54% | 9.95% | −32.7% | 0.65 | 9.80% / 14.93% / −50.9% / 0.49 ([Bondarenko 2019](https://cdn.cboe.com/resources/education/research_publications/PutWriteCBOE19_v14_by_Prof_Oleg_Bondarenko_as_of_June_14.pdf)) |
| PUT | Jan 2007–Aug 2026 | 7.1% | 10.7% | −32.7% | 0.52 | 11.0% / 15.4% / −50.9% / 0.61 ([Cboe fact sheet](https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_PUT-Index.pdf)) |
| BXM (ATM covered call) | Jun 1986–Jun 2026 | 8.6% | 10.7% | −35.8% | 0.56 | 11.2% / 15.2% / −50.9% / 0.57 ([fact sheet](https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXM-Index.pdf)) |
| BXY (2% OTM covered call) | Jun 1988–2026 | 10.3% | 11.9% | −40.3% | 0.59 | 11.4% / 14.6% / −50.9% / 0.57 ([fact sheet](https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXY-Index.pdf)) |
| CNDR (20Δ/5Δ iron condor) | since 1986 | not published in accessible text | — | −19% (since 1986); −13.7% (2006–19) | — | [Cboe 2021](https://www.cboe.com/insights/posts/benchmark-indices-series-volatility-management-with-cboes-bfly-and-cndr-indices/), [benchmarks sheet](https://cdn.cboe.com/resources/indices/documents/benchmarks-fact-sheet.pdf) |
| BFLY (ATM iron butterfly, 5% wings) | since 1986 | level 414 on 16 Sep 2026 → about 3.6%/yr if based at 100 in 1986 (unverified base) | — | −47.1% | — | [FXEmpire](https://www.fxempire.com/indices/bfly-ind_cbom/history) |
| VPD (short 1m VIX futures, de-levered) | Feb 2006–Dec 2018 | 7.4% | 21.9% | −61.7% | 0.33 | 7.5% / 19.3% / −55.2% / 0.38 ([Szado 2020](https://cdn.cboe.com/resources/education/research_publications/Szado_Selling_VIX_Fut_&_Opt_for_Enhancement_June_15_2020.pdf)) |
| VPN (VPD + long OTM VIX calls) | same | 6.5% | 18.7% | −53.0% | 0.34 | same |

**2018–2025 sub-period, from the fact-sheet calendar rows.** PUT: −5.9, 13.5, 2.1, 21.8, −7.7, 14.3, 17.8, 9.2 → **7.6%/yr** vs S&P **14.3%/yr**. BXM: −4.8, 15.7, −2.8, 20.5, −11.4, 11.8, 20.1, 8.9 → **6.6%/yr**. Trailing to Aug 2026: PUT 1y 15.8%, 5y 9.2%, 10y 8.4%; BXM 5y 8.5%, 10y 7.9%. Option-writing lagged the index by 6–8 points a year in an era of strong equity returns; it wins only on drawdown. VPD/VPN lost more than the S&P in 2008 and 2018 and beat it in 2009, 2016, and H1 2023 (+27.4%/+25.3%, [Cboe](https://www.cboe.com/insights/posts/cboes-vpd-vpn-and-bxn-indices-rose-more-than-19-in-the-first-half-of-2023)); the CNDR drawdown is the smallest of any Cboe benchmark because most of it is T-bills, and 59% of its months land between 0% and +2%.

## 2. Harvesting the variance risk premium with defined risk

The premium is real: VIX exceeded subsequent 1-month realised vol by 4.2 points on average 1990–2018 (Bondarenko), and the implied-minus-realised gap predicts quarterly index returns ([Bollerslev, Tauchen & Zhou, RFS 2009](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=948309)). [Israelov & Nielsen, "Covered Calls Uncovered"](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Covered-Calls-Uncovered.pdf) decompose BXM: the short-vol piece has a Sharpe near 1.0 but is only 10% of the risk; equity beta is most of the return; an uncompensated "reversal" exposure is 25% of the risk. So the harvestable part is small in dollar terms, which is why isolating it (delta-hedged) produces yields, not growth.

Practitioner results after costs:
- **tastytrade 16Δ/45DTE strangle, IVR>50, close at 50%/stop at 2×** replicated on SPX 2005–2016 ([SJ Options](https://www.sjoptions.com/does-tastytrade-work/)): at 15% margin use, 0–3%/yr; at 35%, −5.5%/yr; at 70%, blown up in 2011. Win rate 65%, avg win +10%, avg loss −24%. Not available on Robinhood anyway (no naked short options at Level 3, [Robinhood](https://robinhood.com/us/en/support/articles/advanced-options-strategies/)).
- **SPX iron condors 2006–2025, 15,360 trades** ([OptionsPilot](https://optionspilot.app/blog/best-delta-dte-settings-iron-condors-backtest-data)): best set (16Δ, 45 DTE, close at 50%) = 74.6% win rate, +$138 per $2,000 risked (**6.9% of risk per trade**), max DD −21.3%, Sharpe 0.78; 8Δ wings: +$48/trade, DD −10.8%. Mid-price fills, commissions "$1–3/leg" only.
- **Our data**: ATM monthly SPY put-write sold at the bid 2019–2026: 4.2%/yr, DD −16%; 15-delta: **4.7%/yr, DD −3.3%, 91% positive months**; 30Δ covered call 7.6% vs SPY 10.0%. At 2× the 15-delta write is 3.2% (costs scale, premium doesn't).

Retail haircut: [Bryzgalova, Pavlova & Sikorskaya (JF 2023)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4065019) measure a 12.6% average retail bid-ask; [Bogousslavsky & Muravyev (2025)](https://www.brettonwoodsskiconference.com/uploads/b/f9bfc8b0-0251-11ed-a646-3dea17112d2f/An%20Anatomy%20of%20Retail%20Option%20Trading.pdf) find −0.9% per option trade against a 3.7% quoted spread, and option-only traders losing $547/month. On SPX/SPY the spread is far tighter than single names, which is why index put-writing survives and single-name premium selling mostly does not.

## 3. Dispersion

[Quantpedia's](https://quantpedia.com/strategies/dispersion-trading) academic version (short index vol, long 20 single-name puts, 1996–2007) reports 15.39%/yr after costs, Sharpe 0.82, max DD −43.5%, 21 legs, monthly. The correlation premium has shrunk from ~18 points (1996–2003) to 6.7–8.9 points on 91-day options ([HMA Quant](https://hmaquant.substack.com/p/dispersion-trading-selling-the-index)). **Not retail-feasible**: the short leg is a naked index straddle (not permitted at Robinhood Level 3), the long side is 20+ single-name straddles at 3–12% spreads, and the book needs vega-weighting and delta hedging. With $5,000 you cannot hold one leg, let alone twenty.

## 4. 0DTE: who makes money

Volume: 0DTE was 59% of SPX volume in 2025 (2.3m/day), 62.4% in Aug 2025 with retail 53% of it ([Cboe](https://www.cboe.com/insights/posts/spx-0-dte-options-jump-to-record-62-share-in-august/)), and 65% by May 2026 after the Pattern Day Trader rule was repealed in June 2026; SPX ADV 5.1m ([Cboe Q2 2026](https://ca.investing.com/news/company-news/cboe-q2-2026-slides-record-revenue-0dte-options-surge-to-65-of-spx-93CH-4768656)).

P&L: [Beckmeyer, Branger & Gayda](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4404704) find retail lost over $70m in 0DTE over ~2 years, **more than $50m of it transaction costs**, about $241,000 per day Feb 2021–Sep 2023; retail is net long, market makers net short and profitable. [Bandi, Fusari & Renò (JF)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4503344) is a pricing paper (2014–2023 intraday) and finds a 0DTE variance premium but no retail-tradable edge. The one favourable finding, [SEC DERA (Fu, Li, Musto, Pearson 2025)](https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf), is about *execution*: customers are at the best bid/offer more than half the time, and the SPXW ATM spread was one tick wide 64.7% of the time by July 2023 (0.5% in July 2020). Limit orders cut the spread cost; they do not create an edge. Vendor backtests claiming a "5,496% CAGR" on 0DTE condors ([OptionsTradingIQ](https://optionstradingiq.com/option-omega/)) cover 8 months of 2022 at 100% allocation with a −27.8% drawdown and an avg loss twice the avg win. Our own 147,350 real SPXW trades: every credit structure negative, |t| > 9.

## 5. Earnings

- **Pre-announcement long straddle** ([Gao, Xing & Zhang, JFQA 2018](https://doi.org/10.2139/ssrn.2204549)): +3.34% from day −3 to the print at mid, 1996–2013. Their Table 6: at 50% of quoted spread the effect is +0.27%/day (t 2.8) in low-spread names; at 100% of quoted spread only the low-spread half survives, at +0.04%/day (t 0.48), not significant. A 2011–2021 replication ([BSIC](https://www.bsic.it/straddling-outside-and-into-earnings-part-ii-2/)): +1.17% at mid, **−9.07% at bid/ask**.
- **Selling the crush**: [de Silva, So & Smith (RoF 2026)](https://www.timdesilva.me/files/papers/losing_optional.pdf) show retail option *buyers* lose 5–9% (10–14% on high-vol names), the half-spread alone costs them 9%, and short positions earn +180 bps over the 11-day window — a $1.5B annual wealth transfer to the sellers. The seller edge exists but is spread-sized. Our 12,035 straddles through the print: −35%/trade held long; our earnings-VRP study: sellers gain +3.63 pts when the implied move is rich-percentile, −4.30 when cheap (t 9.07).
- **Calendars**: [Quantcha](https://www.quantcha.com/news/an-analysis-of-trading-earnings-releases-using-options/), 1,097 events 2016–2022, long calendar straddle +13% average, 53% win rate, at mid prices with no peer review. Two single-name legs at 5–10% spread each remove most of that.

## 6. Leverage for a growth path

[Ayres & Nalebuff](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1687272): 2:1 when young, monthly rebalanced, 37% certainty-equivalent gain (CRRA 4); the leveraged path matched a constant 74% stock allocation with 21% less dispersion and never hit a margin call in 130 years — because no *month* fell 33%. Critics note retail margin at 7.5–8.6% erases much of it ([LessWrong review](https://www.lesswrong.com/posts/4wL5rcS97rw58G98B/review-of-lifecycle-investing)). Our own repo: 2× index with a VIX-backwardation overlay, 2006–2026, 15.3%/yr vs 11.5%, DD 59%.

**Measured tonight on Robinhood SPY quotes** (22 Sep 2026 close, SPY 773.38, Dec-2027 expiry): put-call parity gives an implied carry of 3.96%/yr (600 strike) and 3.81%/yr (500 strike) net of dividends, so roughly 5%/yr gross; buying the 600 call at the ask costs 5.9%/yr of the borrowed amount including a 1.7%/yr embedded put. Spread on the call 2.1% of premium. Historically deep-ITM S&P calls carried 1.89–6.42% over the 1-year Treasury ([Bogleheads](https://www.bogleheads.org/forum/viewtopic.php?t=306197)). The blocker is size: a 0.9-delta SPY LEAPS is $21,500; **$5,000 cannot buy one**, so 1.5–2× on an index at this account size means margin or a leveraged ETF, not LEAPS.

## Verdict table

| Strategy | Expected annual return | Max DD | Per-trade cost, % of risk | Retail (RH L2–3) | 58%/mo | 20%/yr |
|---|---|---|---|---|---|---|
| ATM index put-write (PUT) | 7–9% gross; 4.2% ours net | −33% | ~1% of notional/month on SPX; more on SPY | needs L3 + margin (cash-secured put is L2) | No | No |
| 15Δ index put-write | 4.7% net (ours) | −3.3% | spread ≈ 10–20% of premium | yes | No | No |
| Covered call (BXM/BXY) | 6.6–10% gross; 7.6% ours | −36 to −40% | small | yes, L2 | No | No |
| Iron condor 16Δ/45DTE, SPX | ~5–8% on capital at risk; 6.9% of risk/trade | −21% | spread 3–8% of risk (4 legs) | yes, L3 | No | No |
| Short strangle (tasty) | 0–3%; negative above 25% margin | −60% to ruin | 5–10% of credit | not allowed | No | No |
| VPD/VPN (short VIX) | 6.5–7.4% | −53 to −62% | n/a for retail (futures) | no | No | No |
| Dispersion | 15% (1996–2007, institutional) | −43% | 20+ legs at 3–12% each | no | No | No |
| 0DTE SPX selling | negative in ours and in the literature | −28% in 8 months at full size | spread + fees ≈ the whole edge | yes | No | No |
| Pre-earnings long straddle | +1% mid, −9% at bid/ask | per-trade −100% | 8–12% of premium | yes, L3 | No | No |
| Earnings crush selling (spread) | +1–4 pts/event when IV rich | one gap = max loss | 8–15% of risk | yes, L3 | No | No |
| Earnings calendar | +13% at mid, unverified | high | ~10% of debit | yes, L3 | No | No |
| 2× index via LEAPS/margin | ~15% gross in a 10%-index world, less 5–6% carry ≈ 10–14% | −50 to −60% | 2% of premium once a year | LEAPS not at $5k; margin yes | No | Some years |

**Feasibility.** 58%/month is a 5-month 10× with no public precedent in options; the highest legitimate long-run number here is dispersion at 15% for institutions. 20%/year is reachable only with 1.5–2× index leverage in an above-average year, at a drawdown that would halve a $5,000 account before it doubled. Premium-selling on the index is worth doing for a 5–8% yield with a shallow drawdown, and nothing else on this list survives its own bid-ask.
