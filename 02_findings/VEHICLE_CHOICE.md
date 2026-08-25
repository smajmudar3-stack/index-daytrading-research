# The signal is real. The option is the wrong vehicle.

Short interest is the strongest signal in this repo — IC −0.107 at 63 days,
n = 13,219, monotone. The obvious next step is to trade it with options, and it
does not work. This is the arithmetic, because it decided against a panel that
was already built and live.

---

## Compare per unit of DELTA EXPOSURE, not per unit of premium

A deep-ITM put with delta −0.85 on an $18.75 stock controls
`0.85 × 100 × 18.75 = $1,594` of short exposure. That is what both the edge and
the costs must be measured against. Comparing an option to a stock per dollar of
premium is meaningless.

- **Edge** — hit rate `p = 0.5 + arcsin(0.107)/π = 53.4%`, so expected capture is
  `(2p − 1) × E|move|` over the horizon.
- **Theta** — extrinsic ÷ exposure. Paid whether or not the call is right. The
  stock does not pay it.
- **Spread** — half the quoted bid-ask ÷ exposure, paid once because the position
  settles at intrinsic.

## Measured on the live basket

| ticker | edge | theta cost | **net (option)** | net (stock) |
|---|---:|---:|---:|---:|
| ASTS | +3.01% | 7.48% | **−5.29%** | +1.66% |
| SOUN | +1.97% | 6.68% | **−5.85%** | +0.62% |
| IONQ | +2.57% | 5.78% | **−5.58%** | +1.22% |
| SOFI | +1.56% | 5.51% | **−4.58%** | +0.21% |
| OPEN | +2.96% | 4.12% | **−2.19%** | +1.61% |
| RIVN | +1.90% | 4.37% | **−2.87%** | +0.55% |
| UPST | +1.83% | 1.80% | **−0.94%** | +0.48% |
| **CLF** | +1.90% | 1.00% | **+0.39%** | +0.55% |

| | per 63-day cycle | annualised |
|---|---:|---:|
| **options** | **−3.84%** | **−15.35%** |
| stock | +0.76% | +3.05% |

**Theta averages 4.96% of exposure per cycle against an edge of 2.11% — roughly
2.4× the edge, every cycle.** Only 1 of 12 contracts had a positive net edge.

## Breadth: ten names are not ten bets

Grinold: `IR = IC × √breadth`.

| assumption | breadth | IR |
|---|---:|---:|
| naive (independent names) | 40.0 | 0.68 |
| **correlation-adjusted** (ρ̄ = 0.34) | 9.8 | **0.34** |

Ten high-short-float small caps correlate 0.34 with each other, so the effective
number of independent bets per cycle is **2.5, not 10**. The honest information
ratio is ~0.34 gross of costs.

## Consequence

The ticket panel was built, populated with ten live contracts, and then **gated
off by its own arithmetic**. It now shows the rejection table and names the
alternative instead of showing trades that lose.

This is the general lesson, and it is worth more than the specific result:
**a signal being real does not make every vehicle for it profitable.** The
question is never "is there an edge" alone — it is "does the edge survive the
cost of the instrument I am expressing it through." Here the same signal is
+3%/yr as stock and −15%/yr as options.

Caveat in both directions: the edge estimate assumes the measured IC transfers
to these particular names, and an option also buys a hard loss cap that short
stock does not — GME, SOUN and IONQ are exactly the names that squeeze. Paying
~2.5% of exposure per cycle for that cap is a defensible choice. It is just
insurance, not alpha, and it should be labelled that way.
