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

# SPX 0DTE Decision System — How It Works & How to Trade It

**Dashboard:** http://127.0.0.1:8094 · refreshes every 5 min + Update button · honest paper-first tool.

The one-line philosophy: **you don't beat 0DTE with more indicators — you beat it by only trading on
the right days, in the right structure, on the right side, and standing down the rest.** This system
scores each of those and reconciles them into one decision.

---

## The three questions it answers (in order)

### 1. Should I trade premium at all today? → the GAMMA REGIME
Dealer gamma (from the option chain) sets the day's **range**, and it's the most robust thing here.
- **15-year backtest (2011–2026), t = −16, stable EVERY year:** low/negative-gamma days average
  **~2.4% range** vs high-gamma days **~0.7%**. Monotone across gamma quintiles.
- **Low/short gamma → big range → naked longs have fuel.** High gamma → pin/chop → **naked longs
  bleed theta** (this is the #1 leak in retail 0DTE).
- Live source: SPX gamma flip from Unusual Whales (same-day); SqueezeMetrics 15-yr series is the baseline.
- **Rule:** above the gamma flip = pin (sell premium / spreads); below the flip = trend (buy premium).

### 2. Which side — calls or puts? → DIRECTION (this is the hard part)
- **GEX does NOT predict direction** (proven — it's the vol-risk-premium in disguise). Direction comes
  from flow, not gamma.
- **DIX (dark-pool buying), backtested 15 yr:** high-DIX + low-gamma days close green **60%** (t = +3.0).
  This is a *bullish, night-before* signal. **Confluence ≥ 2 of the 4 validated bullish signals is the
  sweet spot** (t = +3.4, ~70 trades/yr); requiring more gets too picky.
- **There is NO reliable night-before BEARISH edge** — the market's upward drift beats intraday puts.
  So **puts are REACTIVE only: buy them on a break below the gamma flip** (short gamma amplifies the drop).
- Live overlay: **Unusual Whales real flow** (buy-vs-sell classified) — when it disagrees with DIX,
  conviction collapses and the system says **STAND DOWN**. Real flow > any night-before opinion.

### 3. What structure & size? → REGIME × DIRECTION × CONVICTION
- Bullish + big range → **naked call**. Bullish + pin → **call debit spread** (a naked call bleeds theta
  on a slow grind even when you're right). No edge + pin → **sell an iron condor** or sit out.
- Size scales with conviction: <35 stand down · <55 half · <70 normal · 70+ full. **Always cap total 0DTE risk to what you can lose entirely** — these options can go to zero.

---

## Reading the dashboard (top to bottom)
1. **TODAY'S PLAY** — the one-glance verb (BUY CALLS / BUY PUTS / STAND DOWN), conviction, size, levels.
2. **SPX regime panel** — live gamma regime + the reconciled thesis showing every signal voting.
3. **Track record** — running win-rate on directional calls (accountability; paper record, builds live).
4. **Periscope (SPX + NDX)** — live gamma flip / call wall / put wall, the exact option order with exit
   plan, pin-risk flag, and the Unusual Whales decision layer.
5. **Session phase** (during RTH) — opening drive (direction) → midday chop → power hour (pinning).
6. **Gap-and-go** (intraday stocks) and **Swing** (days-to-weeks) — separate validated edges.

## Timing within the day
- **9:30–11:00 (opening drive):** direction is set; best window for a directional 0DTE.
- **11:00–13:30 (midday):** lowest energy; ranges compress; be patient.
- **13:30–16:00 (power hour):** charm/gamma pinning intensifies toward the big strikes; breakouts fade,
  premium sellers favored, long premium decays fast — take profits quickly.

## Exits (the profitability lever most people ignore)
- Longs: price-target the wall in your direction; **scale out at +50–100% on premium**; hard stop if
  price loses the flip (thesis dead) or −50% premium.
- Condor: take 50% of max credit; stop if either short strike breaks (that's a trend day).

---

## Honest limits (read these)
- **"Double weekly" isn't real.** Nobody compounds 100%/week. The edge here is a repeatable ~56–60%
  directional hit on the *right* days, plus not giving it back on the wrong ones. That's what compounds.
- Direction edges are **55–60%, never certainties.** Size for that.
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
