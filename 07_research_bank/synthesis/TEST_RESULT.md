# The decisive test: IV rank → P(10x). Result: NULL.

Pre-registered hypothesis, direction stated before the data was pulled:
**low IV rank at entry → higher P(10x) at 15–25 delta.**

**7,038 entries · 60 symbols · 2020-06 → 2026-08 · entry at ASK, exits at BID ·
one entry per (symbol, expiry) · IV rank from a strictly prior window.**

---

## What held up: the base rate

| | P |
|---|---:|
| P(2×) | 26.29% |
| P(5×) | 7.36% |
| **P(10×)** | **1.39%** [1.14, 1.69] |
| median best-ever multiple | **1.09×** |

**Three independent derivations agree**: measured **1.39%**, report 14's model
**2.09%**, report 13's zero-edge **1.47%**.

That median is worth sitting with: **half of all 15–25Δ calls never got more than
9% above the entry ask at their single best moment.**

## What failed: the screen

Headline looked supportive — Q1 2.39% vs Q5 1.21%, Fisher p = 0.023. But:

| Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|
| 2.39% | 1.42% | **0.64%** | 1.27% | 1.21% |

**A U, not a gradient.** Spearman p = 0.188. The analysis script's verdict logic
gated only on Q1-vs-Q5 and ignored the monotonicity requirement written into its
own docstring — the same class of error as trap #5.

### Stress tests: 3 of 4 reject

| test | result |
|---|---|
| monotonicity | **FAIL** — Spearman p = 0.188, non-monotone |
| **time stability** | **FAIL** — p = 0.0025 first half → **p = 0.42 second half** |
| leave-one-out | **FAIL** — dropping NVDA (7 of 36 low-IV events) → p = 0.080 |
| spread confound | pass — effect appears within every spread quartile |

**The vol-compression screen does not survive.** Report 14's Setup 1 premise
fails, and with it the GME/MSTR configuration — the one thing in this project
that looked screenable ex ante.

## What did survive, and it is monotone

| entry spread | P(10×) | median mult |
|---|---:|---:|
| 0.3–8.1% | **1.82%** | 1.23× |
| 8.1–13.2% | 1.37% | 1.15× |
| 13.2–19.0% | 1.31% | 1.05× |
| 19.0–25.0% | **1.08%** | 0.97× |

**Clean, monotone, in the pre-registered direction.** Tight spreads give **1.7×**
the P(10×) of wide ones.

> **Execution dominates selection.** That is the same conclusion the far-OTM work
> reached (−45.6% → +5.6% under a spread filter), now confirmed on an independent
> sample with a different metric.

---

## The verdict

**No edge.** The one screen that looked real does not replicate out of sample.

What is left is a measured base rate of **1.39%** and one robust, monotone,
economically boring finding: **pay less spread.**

Everything actionable in this project is cost avoidance. There is no alpha in it.
