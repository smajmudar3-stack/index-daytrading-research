# 🛑 SUPERSEDED. Do not trade anything in this document

**Retired 2026-08-24. Nothing below is an instruction.**

| | |
|---|---|
| **What replaced it** | [`../02_findings/WHAT_WORKS.md`](../02_findings/WHAT_WORKS.md) for what survived, [`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md) for the verdict on every claim |
| **Why** | Its central rule, "below the gamma flip = buy premium", was measured at **−7.2% per trade** on straddles and **−19.1%** on strangles. It loses money. |
| **What is still true here** | Only the gamma regime setting the day's **range**, and the number to quote for that is **t = −13.2** against VIX9D, not the t = −16 stated below |

Read this as a record of how the conclusion moved. Every retired claim in the body
is struck through and labelled where it appears. If a paragraph here disagrees with
[`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md), the verdict log wins.

---

## The original correction banner, kept as part of the record

This is what was written at the top of this document on **2026-08-05**, the day the
rule was killed. It is preserved verbatim because the annotation was correct and
the failure it describes is the most useful thing in the file. What it did not do
was stop the document being served to readers as "📖 How it works", or stop the rule
being restated further down the page. That is what the 2026-08-24 move fixed.

> ## ⚠️ CORRECTION — 2026-08-05
>
> **The rule "below the flip = trend = buy premium" in this document is WRONG and has been retired.**
> It was tested out-of-sample (see `RULES.md` §3.2) and loses money: long straddles on short-gamma days
> return **−7.2%** per trade and strangles **−19.1%** at a realistic variance premium. The gamma gate is
> genuinely valuable (+15 to +24pp versus buying premium at random) — but the base rate is so negative
> that even the gated version loses.
>
> **The correct rule is: on short-gamma days, STAND DOWN. Not "buy premium."**
>
> More broadly, buying 0DTE premium on *any* directional signal in this repo loses −10% to −11% per
> trade. The half of this document about the gamma regime setting the day's RANGE is confirmed and
> stronger than ever (t = −13.2 against real VIX9D-implied vol); the half that converts that into a
> DIRECTIONAL premium-buying trade is refuted. The live system now trades `RULES.md` §1.2 — sell the
> range on high-gamma days, stand down otherwise — and `risk_gates.py` hard-rejects 0DTE premium buying.
>
> Read the rest of this document as background on the signal construction, not as the trading rule.

*(`RULES.md` is now [`RULES.md`](RULES.md) in this same directory, and it is
superseded too. Its §1.2 condor was refuted on real quotes after that banner was
written: see [`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md).)*

---

# SPX 0DTE Decision System — How It Works & How to Trade It

> **SUPERSEDED.** Everything from here down is the 2026-08-05 document, unchanged except that
> retired claims are struck through and labelled inline. Nothing was deleted.

**Dashboard:** http://127.0.0.1:8094 · refreshes every 5 min + Update button · honest paper-first tool.

The one-line philosophy: **you don't beat 0DTE with more indicators — you beat it by only trading on
the right days, in the right structure, on the right side, and standing down the rest.** This system
scores each of those and reconciles them into one decision.

> **RETIRED.** "The right side" was never found. The direction hunt tested 56 features and 220
> conditions across thousands of combinations and **zero** cleared 55% on both train and validate
> (`../02_findings/FINDINGS.md` §2). What survived of this philosophy is only the standing-down half.

---

## The three questions it answers (in order)

### 1. Should I trade premium at all today? → the GAMMA REGIME
Dealer gamma (from the option chain) sets the day's **range**, and it's the most robust thing here.
- ~~**15-year backtest (2011–2026), t = −16, stable EVERY year:**~~ low/negative-gamma days average
  **~2.4% range** vs high-gamma days **~0.7%**. Monotone across gamma quintiles.
  **[SUPERSEDED t-stat: quote t = −13.2, measured against real VIX9D-implied vol. The −16 was
  measured against this repo's own vol forecast, which is not a price anyone can trade. See
  `../docs/VERDICT_LOG.md`.]**
- ~~**Low/short gamma → big range → naked longs have fuel.**~~ High gamma → pin/chop → **naked longs
  bleed theta** (this is the #1 leak in retail 0DTE).
  **[RETIRED, first half only. The range really is bigger in low gamma. "Naked longs have fuel" does
  not follow and was measured at −7.2% / −19.1%.]**
- Live source: SPX gamma flip from Unusual Whales (same-day); SqueezeMetrics 15-yr series is the baseline.
- ~~**Rule:** above the gamma flip = pin (sell premium / spreads); below the flip = trend (buy premium).~~
  **🛑 RETIRED, BOTH HALVES. This is the sentence this whole document was superseded for.**
  Below the flip, buying premium measured **−7.2%** (straddle) and **−19.1%** (strangle) per trade;
  the correct action is to stand down. Above the flip, selling premium was refuted separately on real
  quotes: the 0DTE condor built on this is approximately break-even and the 11:00 entry actually used
  measured **−1.70%** (`../02_findings/FINDINGS.md` §1). Neither half is an instruction.

### 2. Which side — calls or puts? → DIRECTION (this is the hard part)

> **🛑 THIS ENTIRE SECTION IS RETIRED.** There is no answer to "which side". Buying 0DTE premium on
> the best directional signal in this repo measured **−11.3%** per trade on a naked ATM call and
> **−10.0%** on a call debit spread (`RULES.md` §3.1). The signal is genuinely worth about +8pp over
> an unconditional control and that is still nowhere near enough to pay for the option.

- **GEX does NOT predict direction** (proven — it's the vol-risk-premium in disguise). Direction comes
  from flow, not gamma. **[STILL TRUE, and it is the one line in this section worth keeping.]**
- **DIX (dark-pool buying), backtested 15 yr:** high-DIX + low-gamma days close green **60%** (t = +3.0).
  This is a *bullish, night-before* signal. **Confluence ≥ 2 of the 4 validated bullish signals is the
  sweet spot** (t = +3.4, ~70 trades/yr); requiring more gets too picky.
  **[REAL ON THE UNDERLYING, NOT MONETISABLE IN OPTIONS. +12.8 bp open-to-close, t = +3.04. A 13 bp
  expected move cannot pay for an option costing ~0.37% of spot. `RULES.md` §2.1 and §3.1.]**
- **There is NO reliable night-before BEARISH edge** — the market's upward drift beats intraday puts.
  So ~~**puts are REACTIVE only: buy them on a break below the gamma flip**~~ (short gamma amplifies the drop).
  **[🛑 RETIRED. This is the retired rule restated as a "reactive" trade. Buying puts below the flip is
  the −7.2% / −19.1% trade. Do not do it reactively either.]**
- Live overlay: **Unusual Whales real flow** (buy-vs-sell classified) — when it disagrees with DIX,
  conviction collapses and the system says **STAND DOWN**. Real flow > any night-before opinion.

### 3. What structure & size? → REGIME × DIRECTION × CONVICTION

> **🛑 EVERY STRUCTURE NAMED IN THIS SECTION WAS REFUTED.** Naked call and call debit spread:
> −11.3% / −10.0% per trade (`RULES.md` §3.1). Iron condor: approximately break-even on 1,919 sessions
> of real SPXW bid/ask, and −1.70% at the 11:00 entry (`../02_findings/FINDINGS.md` §1).

- ~~Bullish + big range → **naked call**. Bullish + pin → **call debit spread** (a naked call bleeds theta
  on a slow grind even when you're right). No edge + pin → **sell an iron condor** or sit out.~~
  **[RETIRED. "Or sit out" is the only surviving branch.]**
- Size scales with conviction: <35 stand down · <55 half · <70 normal · 70+ full. **Always cap total 0DTE risk to what you can lose entirely** — these options can go to zero.
  **[RETIRED as a sizing rule: it sizes trades that should not be taken. The warning in bold is still
  correct and is worth carrying anywhere.]**

---

## Reading the dashboard (top to bottom)

> **RETIRED as a description of the live dashboard.** The verbs below no longer exist as
> recommendations: no code path may emit "BUY CALLS" or "BUY PUTS". This section is kept because it
> records what the page used to say.

1. ~~**TODAY'S PLAY** — the one-glance verb (BUY CALLS / BUY PUTS / STAND DOWN)~~, conviction, size, levels.
   **[🛑 RETIRED. BUY CALLS and BUY PUTS were the −10% to −11% trade. STAND DOWN survives.]**
2. **SPX regime panel** — live gamma regime + the reconciled thesis showing every signal voting.
3. **Track record** — running win-rate on directional calls (accountability; paper record, builds live).
4. **Periscope (SPX + NDX)** — live gamma flip / call wall / put wall, the exact option order with exit
   plan, pin-risk flag, and the Unusual Whales decision layer.
5. **Session phase** (during RTH) — opening drive (direction) → midday chop → power hour (pinning).
6. **Gap-and-go** (intraday stocks) and **Swing** (days-to-weeks) — ~~separate validated edges~~.
   **[RETIRED. Swing is not a validated edge: `RULES.md` §4 concludes "There is no validated swing
   options rule set in this data." Gap-and-go was measured at 53% hit, t = 1.7, below the bar.]**

## Timing within the day

> **RETIRED as trade timing.** There is no directional 0DTE to time. Entry-hour testing found the
> edge simply decays with delay and there is no magic entry hour (`RULES.md` §3.5). The session-phase
> description is still a fair description of how the day behaves.

- **9:30–11:00 (opening drive):** direction is set; ~~best window for a directional 0DTE~~.
  **[RETIRED: no directional 0DTE.]**
- **11:00–13:30 (midday):** lowest energy; ranges compress; be patient.
- **13:30–16:00 (power hour):** charm/gamma pinning intensifies toward the big strikes; breakouts fade,
  premium sellers favored, long premium decays fast — take profits quickly.

## Exits (the profitability lever most people ignore)

> **RETIRED.** These are exit rules for two trades that no longer exist. Worse, both are contradicted
> by later work: `RESEARCH_MANAGEMENT.md` finds "take profit at 50% of max credit" is **folklore as a
> return rule**, and `RULES.md` §1.2 removed the condor profit target entirely.

- ~~Longs: price-target the wall in your direction; **scale out at +50–100% on premium**; hard stop if
  price loses the flip (thesis dead) or −50% premium.~~ **[RETIRED with the long trade itself.]**
- ~~Condor: take 50% of max credit; stop if either short strike breaks (that's a trend day).~~
  **[RETIRED. Folklore, and superseded even inside the retired rule set.]**

---

## Honest limits (read these)
- **"Double weekly" isn't real.** Nobody compounds 100%/week. ~~The edge here is a repeatable ~56–60%
  directional hit on the *right* days, plus not giving it back on the wrong ones. That's what compounds.~~
  **[First sentence still true and then some. The rest is RETIRED: there is no repeatable directional
  hit. And a directional hit rate would not have been enough anyway. A long ATM 0DTE option needs a
  58.2% hit rate over 90 minutes just to break even at real quotes, measured in
  `../03_research/RESEARCH_DIRECTION.md` §0.]**
- ~~Direction edges are **55–60%, never certainties.** Size for that.~~
  **[RETIRED. No direction edge cleared 55% on train and validate.]**
- **NDX isn't on Unusual Whales** → its flow uses QQQ (same direction, labeled "via QQQ proxy").
- The AI desk-analyst (Fable) is dormant until Anthropic API credits are added; a rule-based read runs now.
- This is a **paper-first** tool. The track record builds forward — trust it as the sample grows, not on day 1.

## What was tested and REJECTED (no p-hacking)
- Index *intraday* directional patterns (20 classic setups × both directions): all negative — dead.
- Gap × gamma direction: 53% hit, t = 1.7 — below bar, not added.
- Night-before bearish signals: all insignificant — puts are reactive-only.

*Backtest scripts: `gex_regime.py`, `direction_signals.py`, `confluence.py`, `dix_direction.py`,
`gap_gamma.py`, `validate_gapgo.py`. Live engine: `gex_signal.py`, `gex_periscope.py`, `uw_client.py`,
`swing_signals.py`, `signal_tracker.py`, `gap_dashboard.py`, `scan_all.py`.*
