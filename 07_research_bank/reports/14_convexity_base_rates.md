# 14 — The P(10x) base-rate table

**Status:** complete · **Evidence quality:** one paper read in full (Cao & Han
2013 JFE), 8.5 years of real weekly bars measured this session, plus a closed-form
derivation · **Relevance:** the table that decides strike selection — and it
contradicts reports 10/11 on the vehicle

---

## The headline: deep OTM is six times worse, not better

| delta | index (20 IV) | high-beta (50 IV) | small-cap (90 IV) | crypto-linked 180d |
|---|---:|---:|---:|---:|
| 0.50 | 0.03% | 0.54% | 1.88% | 3.06% |
| 0.30 | 0.44% | 1.50% | 2.99% | 4.70% |
| 0.25 | — | 1.80% | — | **4.85%** ← max |
| 0.20 | 1.10% | **2.03%** | **3.30%** ← max | 4.73% |
| **0.16** | 1.38% | **2.09%** ← max | 3.23% | 4.38% |
| 0.10 | **1.53%** ← max | 1.82% | 2.78% | 3.37% |
| 0.05 | 1.10% | 1.15% | 2.00% | 2.08% |
| **0.01** | 0.30% | **0.34%** | 1.05% | 0.75% |

> **"2-delta lottery tickets 10x more often" is false.** At 1Δ, P(10×) is 0.34% —
> **six times worse** than 2.09% at 16Δ.

**The arithmetic nobody does:** 10× held to expiry requires `S_T ≥ K + 10·C₀`.
Going further OTM raises K but collapses C₀, so the **required move is U-shaped**.
At 50Δ on a 50-IV name you need **+78%**; at 16Δ you need **+48%**; at 1Δ you need
**+91% again.** The required move is minimised at **12–20 delta.**

## The central tension dissolves

- **Expectancy** peaks at 16–30Δ (our +26.1% result)
- **P(10×)** peaks at **10–25Δ**, centring on **16–20Δ**

They peak in nearly the same place. What genuinely differs:

**Optimal delta is a monotone function of the target:**

| target | optimal delta |
|---|---|
| 2× | 50Δ |
| 5× | 30Δ |
| **10×** | **16–25Δ** |
| 50× | 5–7Δ |
| 100× | 2–5Δ |

**Deep OTM is correct only if the target is 50×+.**

And the tail is remarkably flat: at 16Δ, P(2×) = 5.01% and P(10×) = 2.09%.
**Aiming for 10× instead of 2× costs only 2.4× in probability.**

## DTE is nearly irrelevant

The z-score required to 10× is **1.82 / 1.81 / 1.81 / 1.82 / 1.90** across
7/30/60/120/365 DTE at 16Δ. Both strike distance and premium scale with σ√T, so
they cancel. Net effect of the second-order channels: **longer is mildly better,
90–180 DTE. Weeklies are not where 10× lives.**

---

## ⚠️ This contradicts reports 10 and 11 on the vehicle

Reports 10 and 11 converged on **XSP** — Section 1256 tax treatment plus the only
structure with no path to a negative balance.

**Report 14 says index options are the structurally worst 10× vehicle.**

| | P(10×) at optimum |
|---|---:|
| SPX/QQQ index | **1.53%** |
| high-beta single name | 2.09% |
| small-cap | 3.30% |
| crypto-linked, 180d | **4.85%** |

Reason: indices have **negative** skew; single names have **positive
idiosyncratic** skew. *"Never buy index calls for this."*

### Resolution

**The probability difference dominates the tax benefit.** Section 1256 is worth
38–108% of the stake — **but only on gains you actually realise.** Trading a 1.53%
vehicle instead of a 4.85% one to save tax is paying a 3× probability penalty for
a benefit that is conditional on winning.

> **Single names for the bet. XSP only if the thesis is genuinely index-level.**

Report 11's bounded-structure argument still binds, but is satisfiable another
way: **long calls in a cash account** are bounded at premium on any underlying.
The exercise-by-exception risk is real but avoidable behaviourally — close before
expiration day.

---

## Volatility barely helps, and screening on high IV backfires

Going from a 20-IV index to a 90-IV biotech raises P(10×) only from 1.4% to
3.2% — **a 2.3× gain, not the 10× people assume.** Because the required z-score
is scale-free.

Two verified results say the high-IV screen actively hurts:

- **Cao & Han (2013 JFE), read in full:** delta-hedged option returns are
  **decreasing in the underlying's idiosyncratic volatility**, for calls and puts.
  You overpay most on the most volatile names.
- **Boyer & Vorkink**, quoted directly by Cao & Han: *"higher stock volatility
  leads to **much lower skewness for out-of-the-money call options**."* The right
  tail of the *option return* is thinner on a high-vol name — **the vol is
  already in the price.**

### What to screen for instead

1. **Positive drift / genuine risk premium** — the largest single lever.
   Crypto-linked (30%/yr drift) gives 4.85% vs 2.09% for a zero-premium
   high-beta name. This is Almeida's Deribit mechanism.
2. **Positive idiosyncratic skew, negative index skew** — never index calls.
3. **Flat call skew at entry** — if 25Δ IV − ATM IV > +3 vol pts, the right tail
   is already bid.
4. **Low IV *rank* on a structurally high-vol name** — opens the vega channel.
5. **Real float/borrow constraint** (SI > 20%, DTC > 5, rising fee).
6. **Bid-ask ≤ 12% of mid.** Going 5% → 25% round-trip cuts P(10×) from 2.09% to
   1.74% and turns E[return] from −43% to −52%.
7. **Leveraged ETFs: avoid.** Volatility drag destroys the right tail — TQQQ-like
   scores *below* a plain 50-vol single name at every delta.

---

## IV expansion is the only thing that justifies deep OTM

Underlying move required to reach 10× with 1/3 of life left, 50-vol name:

| delta | IV ×1.0 | IV ×2.0 | P(touch) ×1.0 | P(touch) ×2.0 |
|---|---:|---:|---:|---:|
| 0.50 | +74.1% | +74.0% | 0.96% | 0.97% |
| 0.16 | +39.5% | +32.1% | 5.48% | 9.00% |
| 0.05 | +37.0% | **+19.8%** | 6.45% | **22.55%** |
| **0.02** | +38.1% | **+14.5%** | 6.01% | **34.24%** |

> **At 50Δ, doubling IV is worth nothing (0.1pp).** At 2Δ it is worth **5.7×** and
> cuts the required move from +38% to **+14.5%**.
>
> **Delta drives 10× near the money; IV expansion drives it far from the money.**

**Corollary: you must buy before IV expands, not after.** Absent a genuine
vol-expansion thesis, sit at 16–20Δ. With one, shift to 5–10Δ.

## Wide debit verticals — the real discovery

Sell the far wing, which our own 10.5M-trade evidence says is the most overpriced
part of the chain:

| structure (50-vol, 60 DTE) | debit | max mult | move for 10× | **P(10×)** | vs outright |
|---|---:|---:|---:|---:|---:|
| outright 16Δ | $1.82 | ∞ | +47.6% | 2.09% | — |
| **16Δ / 10Δ vertical** | **$0.76** | 13.4× | **+37.0%** | **3.89%** | **1.86×** |
| 16Δ / 5Δ vertical | $1.33 | 18.9× | +42.7% | 2.76% | 1.32× |
| 30Δ / 10Δ | $2.80 | 8.7× | — | **cannot 10×** | — |

**Rule: sell the strike where width/debit lands at 12–16×.**

**The catch:** a vertical is near vega-neutral, so it captures **none** of the
IV-expansion channel — the biggest lever available. Netting both, outright with
touch-exit (~5.5%) and vertical held to expiry (~3.9%) are **comparable**.

| thesis | structure |
|---|---|
| vol event (squeeze, crash, unknown magnitude) | **outright calls** — the vega channel is worth more |
| directional grind (known move, low vol-of-vol) | **wide debit vertical** |

**Ratio backspreads are disqualified.** The short leg requires margin equal to the
strike width, so a $0.22 credit structure ties up $1,378 and pays 2.7% at S=180.
**On a $5k account without portfolio margin, any structure with a short leg not
fully covered by a long leg is out** — margin, not debit, is your capital.

---

## The empirical cross-check, and the selection-bias trap measured

60-day windows, 2018–2026 weekly bars:

| basket | close ≥ +40% | **touch ≥ +40%** |
|---|---:|---:|
| ex-post winners (TSLA NVDA MSTR GME…) | 14.31% | **27.03%** |
| **not winner-selected** (ROKU SNAP PTON LYFT…) | **8.52%** | **17.36%** |

**The winners basket runs ~2× the honest basket at moderate thresholds and ~5× at
extremes — that gap is the size of the selection-bias trap.** The honest basket is
the right anchor.

> **The 10× move is not rare in high-vol names — it happens roughly 0.3–0.5 times
> per name per year. What is rare is being positioned before it.**
> **P(10×) is a timing problem, not an existence problem.**

Every name in the *non-winner* basket had 2–3 windows over 8.5 years where a 16Δ
60-DTE call would have 10×'d.

## Was any of it foreseeable?

- **GME: yes, on the vol-expansion channel** — SI >100% of float, extreme borrow
  fees, and **IV still moderate in early December 2020**. That is a screenable
  configuration, not hindsight.
- **MSTR ×4: yes, on the drift channel** — a levered Bitcoin proxy with a known
  60%+/yr underlying premium, repeating four separate times.
- NVDA/SMCI/AMD: not foreseeable at the specific window.

---

## The bottom line

**P(10×) is maximised at 15–25 delta, 90–180 DTE, on a positively-skewed single
name with genuine drift premium and compressed implied vol — exited on touch, not
held to expiry.**

| | |
|---|---:|
| single shot, realistic | **5–7%** |
| across 4–5 uncorrelated | **8–10%** |
| **P(total loss) at the optimum** | **91–94%** |

**Discard outright:** index options (0.03–1.5%, structurally worst), leveraged
ETFs (drag kills the tail), anything below 5 delta (six times worse, worst
spreads, and where our own evidence says pricing is most adverse).

## Priority falsification tests

1. **Does IV rank at entry predict P(10×) at 15–25Δ?** This adjudicates our
   "cheap-IV selection makes it worse" result (measured far-OTM) against
   Goyal–Saretto (near the money). **If low IV rank does not help at 15–25Δ, the
   whole vol-compression screen drops.**
2. **Does the vertical actually beat the outright on real quotes?** Real far-wing
   quotes are richer than modelled, which should make the vertical look *better*
   since we're the seller.
3. **Measure the running-max multiplier empirically** — a reflection-principle 2×
   was assumed; theta will give less. This is the difference between 5.5% and 3%.
