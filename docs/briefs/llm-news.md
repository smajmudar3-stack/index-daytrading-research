<!-- research brief, filed 2026-09-23; agent output verbatim -->

# LLM and news/sentiment trading signals, judged against $5k→$50k/5mo and 20%/yr

**Bottom line:** the one paper in this space with a real, disclosed backtest (Lopez-Lira & Tang,
GPT-4 headline sentiment) shows a genuine, publishable finding — and it decayed by 5.4x in under
three years and goes negative at a cost level (20bp round-trip) this repo's own weekly-book work
already treats as normal. Every other artifact fetched this session (Ke-Kelly-Xiu, FinBERT,
FinGPT, the WallStreetBets literature) either discloses no return number at all or measures
something adjacent to trading (classification accuracy, community structure, price
*predictability* in a statistical sense) rather than a number that survives costs. Nothing here
is in reach of 58%/month. The Lopez-Lira number, at its 2021 peak, might have brushed 20%/yr in
isolation for a market-neutral, professionally-executed basket — a retail day trader running one
account cannot replicate its mechanics (thousands of names, same-second API calls, dollar-neutral
shorting) and by the authors' own numbers would be trading the already-decayed 2024 residual, not
the 2021 peak.

## 1. What was fetched and what was computed

Fetched via WebFetch this session: the Lopez-Lira & Tang arXiv abstract, HTML, and PDF (multiple
versions, v5/v6); Ke, Kelly & Xiu's NBER working-paper page; the Loughran-McDonald master
dictionary page (sraf.nd.edu); FinBERT and FinGPT GitHub READMEs; SEC EDGAR's webmaster FAQ on
filing dissemination; an arXiv API query for WallStreetBets/Reddit retail-sentiment papers, which
surfaced Semenova & Winkler's "Social Contagion and Asset Prices" (arXiv:2104.01847) as the paper
in this space with an actual price-predictability claim. Tetlock (2007) could not be reached in
full text this session (Wiley 403, SSRN 403) and is cited from established literature only.

Computed directly with `/Users/sahilmajmudar/index-daytrading/venv/bin/python3` and `yfinance`:
1-day and 5-day post-earnings return dispersion on 30 S&P large caps (mega-cap tech, financials,
healthcare, staples, energy, telecom), 2023 through mid-2026, 450 events (15/name). This answers
one question: after a 10bp/side (20bp round-trip) cost, how big does a news-driven directional
call have to be right to clear the bar, on names any retail news/LLM signal would actually trade.
Script and output are in this session's scratchpad; not committed (single-use compute, not a
study harness).

## 2. Lopez-Lira & Tang (2023–2024), "Can ChatGPT Forecast Stock Price Movements?"

[arXiv:2304.07619](https://arxiv.org/abs/2304.07619) — fetched directly, HTML rendering of the
full paper body (not abstract-only). Method: feed same-day news headlines to an LLM, ask it to
score each headline −1 to +1 for likely price impact, go long the most-positive-scored names and
short the most-negative, rebalance daily. Sample: October 2021 – May 2024.

| Metric | Value | Source |
|---|---:|---|
| GPT-4 headline sentiment, daily long-short return (gross) | **34 bps/day** | paper, HTML body |
| Annualized Sharpe, overnight-news strategy (GPT-4) | **2.97** | paper |
| Annualized Sharpe, intraday-news strategy (GPT-4) | 2.63 | paper |
| GPT-4 vs GPT-3.5 Sharpe (same overnight construction) | 2.97 vs 1.66 | paper |
| Cumulative return net of 5bp round-trip cost | still >300% over the sample | paper |
| Cumulative return net of 10bp round-trip cost | still >100% over the sample | paper |
| Cumulative return net of **20bp round-trip cost** | **unprofitable** | paper |
| Sharpe, 2021 Q4 (peak) | **6.54** | paper |
| Sharpe, full-year 2022 | 3.68 | paper |
| Sharpe, full-year 2023 | 2.33 | paper |
| Sharpe, Jan–May 2024 | **1.22** | paper |
| Non-tradable same-headline hit rate (direction only, GPT-4) | ~90% | abstract |

Two things matter more than the headline Sharpe. First, the paper's own words: "strategy returns
decline as adoption rises" — the Sharpe series above (6.54 → 3.68 → 2.33 → 1.22) is that decay
measured, not implied, by the authors. A signal that roughly halves every year and was already
unprofitable at 20bp round-trip (this repo's own vertical-spread cost, 8.4-14.5% of max risk, is
far above that — 20bp is already where *this* strategy dies) is not a stable edge to build a 2026
plan on. Second, the backtest is a cross-sectional, dollar-neutral, same-day-rebalanced basket
across a broad scored universe, not a single-name day-trading account — a solo retail trader
cannot short the bottom decile and buy the top decile of the whole universe same-day. Replicating
the mechanics this return was measured on needs infrastructure this repo does not have and the
paper never claims retail can access.

## 3. Ke, Kelly & Xiu, "Predicting Returns With Text Data"

[NBER Working Paper 26186](https://www.nber.org/papers/w26186) — abstract fetched directly.
Method: a three-step supervised pipeline (screen sentiment terms → weight via topic modeling →
aggregate via penalized likelihood) applied to Dow Jones Newswires articles, explicitly built to
predict returns rather than reuse a generic dictionary score. The abstract states the model
"excels at extracting return-predictive signals" relative to dictionary methods (i.e.
Loughran-McDonald) and vendor sentiment scores, but **discloses no return, Sharpe, or
out-of-sample percentage figure** in the abstract itself — a genuinely different situation from
Lopez-Lira & Tang, where the number is the finding. Treat the magnitude of this edge as **not
verified this session**; the claim that supervised text models beat dictionary sentiment is
directionally consistent with the wider text-as-data literature but this brief did not reach a
number to put in the table.

## 4. Dictionary sentiment (Loughran-McDonald), Tetlock, and the WallStreetBets literature

- **Loughran-McDonald master dictionary** ([sraf.nd.edu](https://sraf.nd.edu/loughranmcdonald-master-dictionary/)),
  fetched directly: seven-category word lists (negative, positive, uncertainty, litigious, strong
  modal, weak modal, constraining) built from actual 10-K language rather than a generic English
  sentiment list — the original 2011 *Journal of Finance* motivation was that Harvard-IV
  dictionaries misclassify ordinary business words ("liability," "tax," "cost") as negative in a
  filings context. The page itself does not carry predictive-return statistics; those live in the
  underlying papers, not fetched in full this session. **Not verified**: the actual effect size.
- **Tetlock (2007), "Giving Content to Investor Sentiment."** Wiley (403) and SSRN (403) both
  blocked full-text this session. Established-literature citation, not independently re-verified:
  media pessimism (measured from a *Wall Street Journal* column) predicts a next-day market-wide
  return decline that partially reverses over the following weeks — a market-level, not
  single-name, effect, and one from 2007-era daily-column data, not real-time machine-readable
  news. **Not verified this session.**
- **Semenova & Winkler, "Social Contagion and Asset Prices: Reddit's Self-Organised Bull Runs"**
  ([arXiv:2104.01847](https://arxiv.org/abs/2104.01847)), abstract fetched directly: documents
  that retail demand (measured via TAQ trade data) follows WallStreetBets discussion volume, and
  that price predictability and amplified market impact exist around viral WSB content — framed
  as *predictability* and *bubble dynamics*, not a disclosed Sharpe ratio or a claim the effect
  survives costs at retail execution speed. A second paper from the same search, "WallStreetBets:
  Positions or Ban," is a social-dynamics study with zero return content — most of this literature
  studies the community, not the trade.

## 5. FinBERT / FinGPT: classification tools, not backtests

Both GitHub READMEs were fetched directly and both report **zero trading returns, zero Sharpe
ratios, zero backtests**. FinBERT ([ProsusAI/finBERT](https://github.com/ProsusAI/finBERT)) is a
BERT model fine-tuned on the Financial PhraseBank for three-way sentiment classification
(positive/negative/neutral) — a component, not a strategy. FinGPT
([AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)) reports only
F1 classification scores against FPB/FiQA-SA/TFNS/NWGI benchmarks and states outright that its
forecaster module is "NOT a recommendation to trade real money." Anyone citing either of these
as evidence of a tradeable edge is citing a sentiment classifier's accuracy on a labeled dataset,
which is a different claim from a return series.

## 6. Latency reality for a retail machine

SEC EDGAR's own webmaster FAQ (fetched directly): filings are "often available on sec.gov within
1-3 minutes" of the internal timestamp, with **no guarantee** and **no published timestamp marking
when a filing first became publicly visible** — the 1-3 minute figure can't even be independently
verified after the fact. The FAQ's own recommendation for anything close to real time is the
Public Dissemination Service, a paid subscription. RavenPack's public page did not disclose
specific millisecond latency figures this session (**not verified**), but the structural point
survives without the number: institutional machine-readable-news vendors exist specifically to
shave the retail-visible lag down, which is only a business if that lag is worth money. A solo
builder pulling headlines from a free news API is reading the same event materially later than
the participants whose activity Lopez-Lira & Tang's own decay curve already prices in.

## 7. The compute: what a news signal has to beat

450 earnings events, 30 large caps, 2023 – mid-2026 (1-day and 5-day return from the first
trading day on/after the reported date):

| Horizon | Mean move | Mean \|move\| | Median \|move\| | % of events clearing 20bp RT cost |
|---|---:|---:|---:|---:|
| 1-day | +0.07% | 1.54% | 1.12% | 89.3% |
| 5-day | +0.48% | 2.90% | 2.30% | 92.9% |

The cost bar (20bp round-trip, the level where Lopez-Lira & Tang's *own* diversified basket
strategy died) is trivially small next to single-name earnings dispersion — a median move of
1.1% is ~5.6x the round-trip cost. That is the good news and also the trap: **dispersion is not
edge.** Costs are not what kills a single-name earnings-news trade; correctly picking the sign,
consistently, is — and that is exactly the thing this session found no verified retail-reachable
evidence for. Lopez-Lira & Tang's ~90% headline hit-rate is explicitly for the *non-tradable
initial reaction* (the paper's own qualifier), not the post-cost, post-latency drift a retail
account would actually capture.

## 8. The two things a solo builder could actually run

1. **Loughran-McDonald dictionary scoring on 8-Ks the moment EDGAR serves them.** Zero
   API cost, no LLM inference bill, and it targets the one real structural edge this session
   verified — EDGAR's ~1-3 minute (unverifiable, uncapped) dissemination lag — rather than a
   sentiment edge with no disclosed number behind it. Would need its own backtest before sizing
   anything; nothing here measures its return.
2. **A small-scale, single-account replication of the Lopez-Lira & Tang overnight-headline
   construction** (score overnight headlines on ~30-50 liquid large caps with an LLM, trade the
   extremes) — the one design in this whole search with a disclosed, reproducible backtest. Must
   be built and run against real fills knowing going in that the measured Sharpe fell from 6.54
   to 1.22 over 2021-2024 and died outright above 20bp round-trip; a 2026 retail run is starting
   from a worse point on that decay curve, not the 2021 peak the headline Sharpe describes.

Neither of these is verified to work; both are cheap enough (a news API and, for #2, LLM
inference cost per headline) that "build it and measure it" costs little against the alternative
of trusting a number no one re-derived.

## 9. Verdict

| Signal | Disclosed gross edge | Survives costs? | vs $5k→$50k/5mo (58%/mo) | vs 20%/yr |
|---|---|---|---|---|
| LLM headline sentiment (Lopez-Lira & Tang, GPT-4, 2021-2024) | 34bps/day, Sharpe 2.97 (peak) | No above 20bp RT; Sharpe fell to 1.22 by 2024 | No — mechanics not retail-replicable at basket scale | Maybe, at 2021's peak, for a professional market-neutral book; not for 2026 |
| Supervised text sentiment (Ke-Kelly-Xiu) | Not disclosed | Not verified | No basis to say | No basis to say |
| Dictionary sentiment (Loughran-McDonald) | Not disclosed this session | Not verified | No | No |
| Media pessimism (Tetlock 2007) | Not verified this session (403s) | Not verified | No | No — market-level, weeks-scale reversal, not a retail trade |
| WallStreetBets discourse (Semenova & Winkler) | Predictability shown, no Sharpe disclosed | Not verified | No | No basis to say |
| FinBERT / FinGPT | Classification F1 only, zero returns | N/A — not a strategy | No | No |
| Earnings-day dispersion (this session's compute) | N/A — dispersion, not an edge | Costs are not the binding constraint | No | No — requires a directional edge this session did not find |

Judged against $5,000→$50,000 in five months, nothing here clears it: the only real number in the
whole search (Lopez-Lira & Tang's peak 34bps/day) is a diversified market-neutral basket return,
not a single-account day-trading return, and it had already decayed 5.4x in Sharpe terms by the
end of its own sample. Judged against 20%/year, the same paper's *early* numbers might have
cleared that bar for someone running the actual basket in 2021-2022; by 2024 the paper's own
Sharpe of 1.22 is thin, and a 2026 attempt starts further down the same decay curve with none of
this session's other sources offering a disclosed number to substitute. The honest reading is
that LLM headline-sentiment is the one genuinely measured, real, publishable finding in this
entire category — and it is a professional-infrastructure, decaying, basket-level result, not a
retail plan.

**Not verified:** Tetlock (2007) full text (Wiley 403, SSRN 403 — cited from established
literature only); Loughran-McDonald's own quantitative predictive-return figures (page fetched,
statistics not present on it); Ke-Kelly-Xiu's actual return/Sharpe magnitude (abstract discloses
the claim, not the number); RavenPack's specific latency figures (page fetched, no numbers
disclosed); Semenova & Winkler's effect size in return terms (abstract is qualitative on
magnitude). The Lopez-Lira & Tang numbers and the 450-event earnings-dispersion compute were
verified directly this session — the former from the paper's own HTML body, the latter run
against live `yfinance` data with `/Users/sahilmajmudar/index-daytrading/venv/bin/python3`.
