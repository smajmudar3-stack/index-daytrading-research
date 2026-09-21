# What predicts a single stock over one to four weeks — the published record

**Written 2026-09-21** for the weekly options book, after its first 129 closed cards came
in at a 21% win rate with the direction call right 37.6% of the time. Every voter behind
that call is a price transform, a human macro read, or a same-day vendor number with no
history. This is the list of things that are actually documented to work at the horizon
the book trades, ranked by how strong the effect is, how well it has replicated, and
whether this repo can compute it from data it already has (seven years of EOD chains in
Dolt, 514 names of short-interest and borrow-fee history, and the Unusual Whales API).

Sources are linked. Where a number is quoted it is the paper's own; where I could not
verify a claim it says so.

## The ranking

| # | predictor | horizon | documented size | replicated? | computable here? |
|---|---|---|---|---|---|
| 1 | **Borrow fee / short interest** (Drechsler & Drechsler 2014; Boehmer et al.) | 1 month | CME decile spread 1.31%/mo gross, 0.78% net; alpha 1.44% | yes, widely; the repo's own IC −0.107 @63d is this | **yes** — `short_interest.parquet` carries `fee_rate` and `si_float` for 514 names, 2021–2026 |
| 2 | **Call–put IV spread** (Cremers & Weinbaum 2010 JFQA) | 1 week | 50 bp/week long-short, decaying through the sample | yes — but MPP 2025 show ≥⅔ of it is the borrow fee in disguise | **yes** — matched call/put IV from the Dolt chain |
| 3 | **Smirk / OTM put skew** (Xing, Zhang & Zhao 2010 JFQA) | 1 week to 6 months | 10.9%/yr risk-adjusted decile spread | yes; same borrow-fee caveat | **yes** — OTM put IV minus ATM call IV |
| 4 | **Changes in call and put IV** (An, Ang, Bali & Cakici 2014 JF) | 1 month | ~1%/mo decile spread; persists 6 months | yes | **yes** — ATM IV series from the chain |
| 5 | **Option/stock volume ratio** (Johnson & So 2012 JFE) | 1 week | lowest decile beats highest by 0.34%/week | yes; sign is NEGATIVE (high O/S → low returns) | partly — needs option volume; UW `options-volume` has ~1 yr |
| 6 | **Signed open-buy put/call ratio** (Pan & Poteshman 2006 RFS) | 1 day to 1 week | low P/C beats high by >40 bp next day, >1% next week | the original used proprietary CBOE open/close data; vendor proxies are weaker | proxy only — UW flow classification |
| 7 | **Unusual options activity** (Jiang & Strong 2020 SSRN; JPM 2026) | days | OTM near-dated call UOA → positive abnormal returns | declining since 2020; CNBC-covered alerts REVERSE | proxy — UW flow alerts |
| 8 | **Short-term reversal** (de Groot, Huij & Zhou; Nagel) | 1 week | 30–50 bp/week net in large caps at weekly rebalance | very robust; costs matter | **yes** — closes |
| 9 | **52-week-high momentum** (George & Hwang 2004) | 1 month | 0.65–0.70%/mo decile spread | robust; monthly, not weekly | **yes** — closes |
| 10 | **Insider opportunistic buys** (Cohen, Malloy & Pomorski 2012) | months | routine trades ≈ 0; opportunistic carry the abnormal return | yes | already in `insider_score.py` |
| 11 | **Dark-pool volume** (Buti, Rindi & Werner; Boulton et al.) | days | weak; short sales in dark pools less informative than exchange shorts | mixed; one 2024 study reports 15% decay 2018–2023 | proxy — UW dark pool |
| 12 | **IV − RV for the OPTION's return** (Goyal & Saretto 2009 JFE) | 1 month | large; long high-RV−IV straddles, short low | yes — this is about which options are mispriced, not direction | **yes** — `volhist.parquet` + chain |
| 13 | **Pre-earnings straddle** (Gao, Xing & Zhang 2018 JFQA) | days | +3.3% holding a straddle into (not through) the print | yes | **yes** — earnings calendar + chain |

The single most important line is the one the JFE put in print in 2025: **the options-implied
predictors (2, 3) mostly work because they measure the stock borrow fee** (Muravyev, Pearson
& Pollet 2025). Exclude the high-fee names and the predictability falls by at least two
thirds. That is the same finding this repo made on its own with short interest, from the
other side. It means the book should treat #1, #2 and #3 as ONE signal family, not three
independent votes, and it means the cheapest version of the signal (the fee itself, which
the short-interest file already carries) is the one to lean on.

## Per predictor

### 1. Borrow fee and short interest
Drechsler & Drechsler, *The Shorting Premium and Asset Pricing Anomalies* (NBER w20282,
2014). Deciles on the shorting fee, monthly rebalance, 2004–2012: cheap-minus-expensive earns
1.31%/month gross, 0.78% net of the fee, 1.44% four-factor alpha. Eight of the largest known
anomalies live almost entirely inside the 20% of stocks with high fees. Boehmer, Jones & Zhang
(2008) and Diether, Lee & Werner (2009) document the same sign for short-selling flow.
Sign: NEGATIVE — heavily shorted, expensive-to-borrow names underperform. The repo's own
measurement (IC −0.022 @5d rising to −0.107 @63d, n = 13,219) is consistent, and consistent
with the effect being weak at a one-week horizon and strong at three months.
Sources: [NBER](https://www.nber.org/papers/w20282), [SSRN](https://doi.org/10.2139/ssrn.2387099).

### 2. Call–put implied volatility spread
Cremers & Weinbaum, *Deviations from Put-Call Parity and Stock Return Predictability*, JFQA
45(2), 2010. IV of a call minus IV of the matched put (same strike, same expiry), averaged
across pairs weighted by open interest. Stocks with relatively expensive calls beat those with
relatively expensive puts by ~50 bp/week. Stronger when option liquidity is high and stock
liquidity low. **The effect decays over their own sample.** Muravyev, Pearson & Pollet (JFE
172, 2025) derive that the spread is proportional to the omitted borrow fee, and that dropping
high-fee stocks removes at least two thirds of the predictability. Later work (Eksi & Roy 2025
JFR) finds what remains is concentrated around non-fundamental (flow) shocks.
Sources: [JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/deviations-from-putcall-parity-and-stock-return-predictability/D9BA8F97580328AAFD7988B092FE5D50),
[MPP 2025](https://www.sciencedirect.com/science/article/pii/S0304405X25001618).

### 3. The smirk
Xing, Zhang & Zhao, JFQA 45(3), 2010. Smirk = IV of the OTM put with moneyness nearest 0.95
(band 0.80–0.95, 10–60 DTE) minus IV of the ATM call (moneyness nearest 1.0). Steepest-smirk
decile underperforms the flattest by 10.9%/yr risk-adjusted; persists at least six months;
steep-smirk firms go on to report the worst earnings surprises. Same borrow-fee caveat as #2.
Source: [JFQA](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/what-does-the-individual-option-volatility-smirk-tell-us-about-future-equity-returns/ECFD16BA9ACBDC8D577D1BD866FBEA72),
[working paper PDF](https://www.ruf.rice.edu/~yxing/option-skew-FINAL.pdf).

### 4. Changes in implied volatility
An, Ang, Bali & Cakici, *The Joint Cross Section of Stocks and Options*, JF 69(5), 2014.
Monthly change in ATM call IV predicts the next month POSITIVELY; change in put IV predicts it
NEGATIVELY. Decile spread about 1%/month, persisting up to six months. Also the reverse:
past stock returns predict IV changes. Source: [JF](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12181),
[NBER](https://www.nber.org/papers/w19590).

### 5. Option-to-stock volume ratio
Johnson & So, JFE 106(2), 2012. O/S = option volume (contracts) over stock volume (shares),
weekly. Lowest O/S decile beats highest by 0.34%/week (19.3% annualised). The mechanism is
short-sale costs: informed BAD news goes to the options market. So high option volume is, on
average, bearish — the opposite of the "unusual activity = smart money is buying" story.
Source: [JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X12000797),
[author PDF](https://www.travislakejohnson.com/pdfs/Johnson%20So%20OS%202012%20(JFE).pdf).

### 6. Signed open-buy put/call ratio
Pan & Poteshman, RFS 19(3), 2006. Put/call ratio built ONLY from volume that opened new
positions on the buy side (CBOE open/close data, not public). Low-P/C stocks beat high by
>40 bp next day and >1% over the next week. The source of the predictability is private
information. A vendor's "flow lean" is a Lee-Ready-style proxy for this, not the thing
itself. Source: [RFS](https://academic.oup.com/rfs/article-abstract/19/3/871/1646711),
[MIT PDF](https://www.mit.edu/~junpan/volume.pdf).

### 7. Unusual options activity
Jiang & Strong, *Unusual Option Activity: Is it Smart to Follow "Smart Money"?* (SSRN 3618427,
2020): UOA in general does predict returns; UOA COVERED ON CNBC overreacts and reverses. A 2026
Journal of Portfolio Management paper (*The Information Content of Unusual Option Activity*)
finds the effect concentrated in OTM near-dated CALLS and reports it has **declined since 2020
as the strategy became widely followed**, with more of the reaction now same-day. This is the
paper most relevant to what Unusual Whales sells. Sources: [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3618427),
[JPM 2026](https://www.pm-research.com/content/iijpormgmt/early/2026/06/09/jpm2026029).

### 8. Short-term reversal
de Groot, Huij & Zhou, *Another Look at Trading Costs and Short-Term Reversal Profits* (JBF
2012): the daily strategy earns 93 bp/week gross; the weekly-rebalanced one 55 bp gross and
30–50 bp NET in large caps once small caps are excluded. Nagel (2012) shows it is
compensation for liquidity provision and is largest when VIX is high. Sign: last week's
losers outperform last week's winners. Source: [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1605049).

### 9. 52-week high
George & Hwang, JF 2004. Nearness to the 52-week high predicts monthly returns (0.65%/mo
decile spread) better than past returns do. A monthly effect; nothing says it works at one
week. Source: [Bauer PDF](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf).

### 10. Insider trades
Cohen, Malloy & Pomorski, *Decoding Inside Information*, JF 2012: routine (same calendar
month each year) trades carry no information; opportunistic trades do, ~82 bp/month. The
repo's `insider_score.py` already applies this filter. Lakonishok & Lee (2001) found the
effect is a twelve-month, small-cap effect — wrong horizon and wrong cap tier for a weekly
mega-cap book.

### 11. Dark pools
Buti, Rindi & Werner (*Diving into Dark Pools*, FM 2022) and Boulton et al. find dark pool
activity is dominated by uninformed, midpoint-matching flow; short sales executed in dark
pools are LESS informative than exchange shorts. A signal, but a weak one, and the repo's
0.10 weight on it is about right. Source: [FM 2022](https://onlinelibrary.wiley.com/doi/full/10.1111/fima.12395).

### 12. IV minus realised, for the option's own return
Goyal & Saretto, JFE 94(2), 2009. Sort on (12-month realised vol − 1-month ATM IV); long
straddles in the top decile, short in the bottom: large, significant monthly returns (they
report ~23%/month gross on straddles before costs; delta-hedged calls ~1.5%/mo). This is a
statement about WHICH OPTIONS are mispriced, so it belongs in structure selection (buy
premium where IV ≪ RV, sell where IV ≫ RV), never in the direction vote. Vasquez (2017 JFQA)
adds the IV term structure: steep slopes predict higher straddle returns.
Source: [JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X09001251).

### 13. Straddles INTO earnings
Gao, Xing & Zhang, *Anticipating Uncertainty: Straddles around Earnings Announcements*, JFQA
53(6), 2018. Buy the straddle a few days before the print, sell BEFORE it: +3.34% average,
from the IV ramp, not the move. Holding THROUGH the print is the repo's own −35% straddle
result. Source: [JFQA](https://ideas.repec.org/a/cup/jfinqa/v53y2018i06p2587-2617_00.html).

## What this changes for the book

1. The direction vote's strongest documented inputs are the borrow fee, the IV spread, the
   smirk and IV changes. Three of the four are computable today from the Dolt chains and are
   being measured in `05_studies/xsec_predictors_test.py`. Whatever survives there is what
   should carry weight. Nothing else in the vote has a published weekly-horizon effect of
   comparable size.
2. Those three are one family (the fee). They should enter as one composite voter, not three.
3. Option volume signals (#5, #6, #7) are what Unusual Whales sells, and the literature says
   the unsigned volume is BEARISH on average, the signed open-buy ratio needs data the vendor
   does not have, and the alert-following trade has decayed since 2020. Treat the vendor's
   flow lean as a prior worth 0.10–0.20, not 0.40, until the flow tape has 60 sessions.
4. Goyal–Saretto and the earnings VRP measured here decide the STRUCTURE, and the ledger
   already shows why that matters more than direction: debit spreads −56%/card, credit
   spreads −4%.
