# Volatility: predictable, and already priced

Direction topped out at 51% on this data. Volatility is the other candidate, and
the literature is emphatic that it is the predictable one — OOS R² of 0.4–0.7
against roughly zero for direction.

That reproduces here. It still does not produce a trade, and the reason is
worth understanding precisely.

---

## 1. Volatility is genuinely forecastable

Realized variance from 5-minute returns, 494 sessions, expanding-window
walk-forward, R² measured against a **constant** benchmark (not a rolling mean,
which inflates R² by ~3pp/month — Gu-Kelly-Xiu footnote 34).

| model | SPY R² | QQQ R² | QLIKE (SPY) |
|---|---:|---:|---:|
| random walk (yesterday's RV) | 21.2% | 19.4% | 0.4497 |
| AR(1) on log RV | 36.1% | 34.5% | 0.3944 |
| HAR without monthly | 39.8% | 39.8% | 0.3782 |
| **HAR (daily+weekly+monthly)** | **39.8%** | **39.8%** | **0.3778** |
| HAR + 5d min/max | 39.6% | 39.8% | 0.3844 |

**OOS R² of 39.8%, correlation 0.63.** Against direction on the same data —
R² 0.11%, hit rate 51.0% — that is roughly **360× the signal**.

Note what does *not* help: the monthly term adds nothing over daily+weekly, and
range features make it slightly worse. Consistent with "HARd to Beat" (1,455
stocks), where the fitting scheme mattered more than the model and ML failed to
beat a properly specified HAR.

---

## 2. But the market forecasts it better than we do

The decisive test is an encompassing regression. Options are priced off implied
volatility, so a forecast only pays if it holds information the market has not
already priced.

`log RV_{t+1} = a + b·log IV_t + c·HAR_forecast_t`

| regression | SPY R² | coefficient |
|---|---:|---|
| log IV alone | **51.2%** | IV +1.817 (t +18.32) |
| HAR forecast alone | 39.8% | HAR +0.919 (t +14.55) |
| **both** | 51.5% | IV +1.590 (t +8.79), **HAR +0.155 (t +1.50)** |

QQQ is the same story: HAR falls to +0.122 (t +1.07) once VXN is included.

**VIX alone (51.2%) beats HAR alone (39.8%), and HAR adds 0.3pp and an
insignificant coefficient on top of VIX.** The market has already priced
everything the forecast knows. There is no volatility-timing trade here.

---

## 3. The variance risk premium is enormous — and that is the trap

| | SPY | QQQ |
|---|---:|---:|
| mean realized vol | 13.6% | 18.3% |
| mean implied vol | 19.2% | 23.4% |
| **premium** | **+5.6 vol pts** | **+5.1 vol pts** |
| days realized came in **below** implied | **88.5%** | **85.1%** |

Selling volatility wins **88.5% of the time**.

And every credit structure in this repo still lost money — negative expectancy at
|t| > 9 across 147,350 real-quote SPY trades, independently confirmed by Vilkov
(gross Sharpe 0.77 → **net −0.20**).

**This is trap #8 in its purest form: an 88.5% win rate with negative
expectancy.** The 11.5% of days when realized exceeds implied are catastrophic
enough to erase the other 88.5%, and the bid-ask takes what remains. The premium
is not free money; it is compensation for exactly that tail.

Worse, the forecast cannot even time it: predicting whether RV lands below IV is
correct **87.3%** of the time versus **88.5%** for the constant rule "always say
below." The forecast is 1.2 points *worse* than saying nothing.

---

## 4. As a gate, it adds nothing over reading VIX

The original motivation was to gate directional trades on predicted move size.
Matching the number of flagged days across selectors so precision is comparable:

| selector | precision | lift |
|---|---:|---:|
| HAR range forecast | 82.3% | 1.07× |
| yesterday's range | 83.1% | 1.08× |
| **VIX level** | **83.5%** | **1.08×** |

All three are identical, and the free one wins. A forecast that merely matches
VIX adds nothing you cannot read off the screen.

---

## 5. The correction that matters most

Testing the gate exposed an error in the earlier hurdle analysis, and correcting
it makes the conclusion **stronger**, not weaker.

The hurdle was compared against the *intraday range*. But range is not the move
a trade captures — a day can range 1% and close flat. Measured properly, as
|return over the hold| across 495 sessions:

| hold | median &#124;move&#124; | median range | accuracy needed at median |
|---|---:|---:|---:|
| **30 min** | **0.09%** | 0.23% | **69.3%** |
| 1 hour | 0.13% | 0.33% | 71.8% |
| 2 hours | 0.19% | 0.48% | 74.9% |
| 4 hours | 0.36% | 0.78% | 74.2% |

Range runs **2–3× the captured move** at every hold. Only **1.9%** of 30-minute
windows on SPY (4.4% on QQQ) are large enough to clear the hurdle at the 52.9%
ceiling.

So the real gap is not the 0.7 points implied earlier. A typical 30-minute 0DTE
directional trade needs **69.3%** accuracy against a documented ceiling of
**52.9%** — a shortfall of more than sixteen points.

---

## Conclusion

Volatility is the predictable quantity — 360× the signal in direction — and it
is predictable enough that the option market has already priced it better than
we can. The tradeable consequence is not "forecast vol and trade it" but the
narrower and more useful fact that **the variance premium is the only large,
persistent, well-identified effect in this whole body of work**, and harvesting
it requires surviving a tail that has so far eaten every structure tested.

What would change the answer: a cost structure that materially undercuts the
bid-ask we measured (0.30 index points round trip, with theta at 0.37 per half
hour), or a tail hedge cheap enough to make the 88.5% win rate bankable. Neither
is a forecasting problem.
