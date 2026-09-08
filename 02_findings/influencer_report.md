# Influencer strategy harvest — Engine D

**Headline: of the eight consensus setups tested, zero cleared significance. Every
confidence interval contains zero and the largest |t| across all eight is 1.15.** That is
the survivor count chance alone produces, which is the same result this repo has reached in
every other sweep it has run.

**Coverage, stated up front so this is not read as a survey.** 39 influencers are in the
registry; **0% have had their full setup list extracted**. This is a discovery pass plus a
test of the consensus families — the setups that many of them teach in different words. It
is not a per-influencer verdict, and no claim-vs-reality table is presented, because
extracting individual performance claims with citations has not been done.

---

## 1. What was tested, and why it is only eight things

Thirty-nine educators do not teach thirty-nine strategies. They teach roughly ten, in
different vocabularies. The opening-range breakout is taught as "the 9:45 break", "break of
the first 15-minute candle", "initial balance break", ICT's "judas swing then displacement",
and as most of the ORB scripts on TradingView. Those are **one hypothesis wearing five
hats**.

Testing it once per influencer and reporting the best result is precisely the
multiple-testing trap `METHODOLOGY_TRAPS.md` exists to document. So setups are deduplicated
by rule signature — `(family, instrument class, timeframe, direction logic)` — and each
family is tested **once**, over the union of the parameter ranges taught.

Ten consensus families are catalogued in `influencers/registry.yaml`. Four are testable with
the data on hand; the rest are queued and say so.

---

## 2. Results — net of costs, 2 bp round trip on shares

Sample: SPY and QQQ minute bars, 2024-07 to 2026-07, ~500 sessions.

| setup | n | net mean | t | 95% CI | win rate |
|---|---:|---:|---:|---|---:|
| ORB 5min SPY → close | 500 | +2.23 bp | +0.59 | [−5.2, +9.6] | 53% |
| ORB 15min SPY → close | 500 | −1.46 bp | −0.40 | [−8.6, +5.6] | 52% |
| ORB 30min SPY → close | 499 | +2.38 bp | +0.70 | [−4.3, +9.1] | 55% |
| ORB 5min QQQ → close | 500 | +4.04 bp | +0.84 | [−5.4, +13.5] | 52% |
| ORB 15min QQQ → close | 500 | +1.11 bp | +0.24 | [−7.8, +10.0] | 52% |
| ORB 30min QQQ → close | 498 | +4.84 bp | +1.15 | [−3.4, +13.1] | 55% |
| VWAP reversion SPY (0.2% band) | 478 | **−3.79 bp** | −1.08 | [−10.7, +3.1] | 44% |
| gap fade SPY (\|gap\| > 0.3%) | 242 | +7.74 bp | +1.10 | [−6.1, +21.6] | 47% |

Eight tests. Largest |t| is 1.15. At a 5% threshold you expect 0.4 false positives from
eight tests; you got zero real ones. **Nothing here is distinguishable from noise.**

The gap fade has the largest point estimate (+7.74 bp) and the widest interval
([−6.1, +21.6]) — a 28 bp-wide CI on 242 trades. It is the one most worth revisiting with a
longer sample, and it is not evidence of anything yet.

### The taught stop makes it worse

Almost every ORB instructor teaches a stop at the other side of the opening range. Tested:

| variant | n | net mean | t | win rate |
|---|---:|---:|---:|---:|
| ORB 15min SPY → close, no stop | 500 | −1.46 bp | −0.40 | 52% |
| ORB 15min SPY **with the OR stop** | 500 | −1.35 bp | −0.62 | **37%** |

The stop does roughly nothing to expectancy and cuts the win rate from 52% to 37%. That is
what a stop does to a setup with no edge: it converts a coin flip into many small losses and
a few larger wins, at the same expected value, and it costs an extra crossing of the spread
each time it fires.

---

## 3. The contrarian test

Required by the spec, and the answer is the useful one.

| | n | net mean | t |
|---|---:|---:|---:|
| ORB 15min SPY | 500 | −1.46 bp | −0.40 |
| **the same setup FADED** | 500 | **−2.54 bp** | +0.40 |

**Both sides lose.** The inverse trade pays the spread too, so fading a losing setup does
not hand you its losses — it hands you the same spread bill pointed the other way. The
losses are not going to the person on the other side of the retail trade; they are going to
the market maker in the middle. This is the single most useful thing in this report, because
"fade the retail setup" is itself a popular published idea.

---

## 4. Crowding — has the setup been arbitraged?

ORB 15min SPY, split at 2025-07-01:

| era | months | n | net mean | t | 95% CI |
|---|---:|---:|---:|---:|---|
| early | 12 | 242 | +4.40 bp | +0.71 | [−7.8, +16.6] |
| late | 13 | 258 | −6.97 bp | −1.81 | [−14.5, +0.6] |

The direction is what the crowding hypothesis predicts — positive then negative. **It is not
evidence.** Two twelve-month halves cannot separate an intraday edge from noise; neither
half is individually significant, and the difference between them is not either. The
machinery is built and correct so that it means something when there is a decade of minute
data to point it at. Right now it means "suggestive at most", and the module says so in its
own output.

---

## 5. Data honesty

- Minute bars cover **25 months** (2024-07 to 2026-07) for SPY/QQQ/DIA/IWM. Many of these
  setups are taught as having worked for twenty years. Twenty-five months cannot confirm or
  refute that; it can only say that over the last two years, net of a realistic spread, they
  did nothing measurable.
- Costs are **2 bp round trip**, which is realistic-to-generous for SPY/QQQ shares at retail.
  Options expressions of these setups would be far more expensive, and this repo has already
  measured what that does: paying theta on a directional view ran −11.12%/trade across
  230,884 real-fill trades.
- Entries are taken at the trigger price. Real fills on a breakout are worse than the trigger
  — that is what a breakout is — so these results are **optimistic**, not conservative.

---

## 6. What is queued, and why it is not done

| family | status | what it needs |
|---|---|---|
| IV-rank premium selling | QUEUED | the option chain store, not minute bars |
| 45-DTE entry / 21-DTE management | QUEUED | same |
| Bollinger/Keltner squeeze | QUEUED | formalizable; just not run |
| ICT kill zones | QUEUED | the window is testable; the entry trigger needs 2–5 formalizations, some may be UNFORMALIZABLE |
| "The Strat" 2-1-2 / 3-1-2 | QUEUED | bar types formalize cleanly |
| SEPA / VCP momentum | QUEUED | needs the single-name panel, not the index |
| Dealer gamma | **ALREADY DONE** | range claim real (0.843x vs 1.139x implied, t=−13.2); direction claim null (1,001 cells, zero survived) |

**Per-influencer extraction is not done.** Pulling every setup from thirty-nine educators —
many teaching 5 to 20 setups each, across video transcripts, books and course material, with
timestamped citations — is transcript-by-transcript work measured in weeks. The registry
records `extraction_status` per influencer precisely so that a report can never quietly imply
coverage it does not have. Every record currently reads `seeded`.

The right order for that work is **by consensus family, not by follower count**: the families
above are already ranked by how many educators teach them, and testing a family once retires
it for everyone who teaches it.

---

## 7. Rules this report follows

- **Public strategy content only.** Published rules and published performance claims. No
  personal information about anyone.
- **Findings are about rules, never about people.** A backtest can say "these rules produced
  −1.46 bp per trade net of costs on 500 sessions". It cannot support a statement about
  anyone's intent, honesty or competence, and none is made here.
- **Vague rules become several concrete ones or are marked `UNFORMALIZABLE` with the quote.**
  Picking one interpretation of "wait for confirmation" and reporting it as someone's
  strategy builds a strawman.
- **Consensus setups are tested once.** Twenty educators teaching one idea is one hypothesis.

---

*Generated by `05_studies/engine_d_influencers.py`. Registry in `influencers/registry.yaml`.*
