# The Retail Options Cost Stack

Research compiled 2026-08-06. All live option quotes measured this session via the
Robinhood market-data API. Every number below carries a source and a date.

**Headline:** For SPY specifically, the all-in friction at 20–60 DTE is genuinely small
(~1% of a vertical's credit) and the widely-cited academic cost estimates of 3–5% do
**not** apply. Those estimates describe pre-2007 SPX options and present-day
single-stock options — and the second of those is exactly what this account also
trades, where measured friction runs 6–18x worse than SPY.

---

## 0. The reconciliation (measured SPY vs. published estimates)

### The apparent conflict

| Source | Instrument | Sample | ATM quoted spread | Deep OTM |
|---|---|---|---|---|
| **Owner's measurement** | SPY | 2008–2025 EOD, 35–75 DTE, OI>10, 2.04M contract-days | **0.75%** (0.40–0.60Δ) | 1.30% (0.10–0.25Δ) |
| Broadie–Chernov–Johannes | SPX | 1987–2005 | 3–5% | ~10% |
| Constantinides–Jackwerth–Savov | SPX | 1986–2012 | ~5% | 2–3x ATM |
| Muravyev–Pearson | 39 equity/ETF names | Apr 2003–Oct 2006 | 8.1¢ quoted on $1.70 avg = **4.8%** | — |

### The gap is real, and it decomposes into five things

**1. Minimum tick size — the dominant factor.** This is the single biggest driver and
it is verifiable structurally, not statistically. Pulling `min_ticks` from the live
option chain metadata today (2026-08-06):

| Underlying | Tick below $3.00 | Tick **above** $3.00 |
|---|---|---|
| SPY, QQQ, IWM, XSP | $0.01 | **$0.01** |
| AAPL, NVDA, MSFT, META, COST, CAT, PANW | $0.01 | **$0.05** |
| XLF, XLE, XLK | $0.01 | **$0.05** |
| SPX / SPXW | $0.05 | **$0.10** |

SPY sits in a privileged tick regime (the Penny Interval Program, successor to the
Penny Pilot that began 2007-01-26) that *almost nothing else shares*. An ATM 43-DTE
SPY put worth $13.22 can be quoted 1¢ wide = 0.08% floor. The same option on SPX
(worth $50.85) faces a $0.10 tick = 0.20% floor, and on a single stock worth $19.67 a
$0.05 tick = 0.25% floor — but single-stock markets are quoted several ticks wide, not
one. BCJ and CJS both sample SPX in an era when the tick was $0.05/$0.10 *and* market
makers quoted multiple ticks wide. **Their 3–5% is substantially a tick-size artifact
plus a pre-electronic-market-making artifact, not a statement about SPY today.**

**2. Instrument: SPX ≠ SPY.** Measured live today at matched delta and DTE (20Δ,
43 DTE): SPY 740P spread 0.36% of mid; SPXW 7400P spread 0.59%; ratio 1.6x. So
SPX-vs-SPY explains a *modest* part of the gap in the modern era — nowhere near the
4–6x implied by the academic figures. Most of the gap is era, not instrument.

**3. Era.** The owner's own data shows this internally: a 2008–2025 median of 0.75% ATM
against my live intraday measurement today of **0.30%** ATM. Spreads have compressed
~2.5x across the sample. The 2008–2011 portion of the owner's window carries crisis-era
and early-penny-pilot spreads that no longer obtain.

**4. Quoted vs. effective.** The owner measures *quoted* spread. Muravyev–Pearson
(RFS 2020) find conventional effective spreads average 6.2¢ vs 8.1¢ quoted — i.e.
effective ≈ 77% of quoted, because trades cluster when quotes are narrow. That is a
modest favorable adjustment. **But see §2 — M&P explicitly exclude retail from their
headline result.** Quoted spread remains the correct conservative retail assumption.

**5. Median vs. mean, and EOD vs. intraday.** Two caveats that cut *against* the owner's
numbers:
- The owner reports a **median**. Option spread distributions are strongly right-skewed;
  the mean is materially higher. The median describes a calm Tuesday, not the day you
  are forced to exit.
- EOD snapshots miss the open (9:30–9:45, spreads widest) and miss intraday stress.
  A short-premium strategy exits precisely when conditions are worst (§6).

### Verdict

**The owner's measured SPY numbers are correct and the academic caveats do not apply to
SPY.** Use 0.75% ATM / 1.30% far-OTM as the planning assumption for SPY, with the
understanding that it is a median and the tail is worse. The academic cost warnings
should be **redirected**, not discarded — they apply almost perfectly to the
single-stock book (§1b).

---

## 1a. Measured spreads — ETFs and index, 43 DTE

Live quotes, 2026-08-06 ~14:14 ET (intraday), expiry 2026-09-18 (43 DTE).
SPY 769.21 / QQQ 715.73 / IWM 298.87 / XLF 57.79 / XLE 57.95 / XLK 186.06.

| Underlying | Contract | Δ | Bid | Ask | Spread | Mid | **Spread % of mid** | Volume |
|---|---|---|---|---|---|---|---|---|
| SPY | 770P (ATM) | −0.47 | 13.20 | 13.24 | 0.04 | 13.22 | **0.30%** | 2,456 |
| SPY | 740P | −0.22 | 5.48 | 5.50 | 0.02 | 5.49 | **0.36%** | 1,123 |
| SPY | 790C | +0.30 | 5.69 | 5.72 | 0.03 | 5.71 | **0.53%** | 35,172 |
| SPY | 700P | −0.08 | 2.16 | 2.17 | 0.01 | 2.17 | **0.46%** | 1,510 |
| SPY | 720C (deep ITM) | +0.87 | 55.31 | 55.71 | 0.40 | 55.51 | **0.72%** | 26 |
| QQQ | 680P | −0.24 | 8.66 | 8.74 | 0.08 | 8.70 | **0.92%** | 833 |
| IWM | 283P | −0.20 | 2.56 | 2.61 | 0.05 | 2.59 | **1.93%** | 60 |
| XLE | 55P | −0.25 | 0.75 | 0.76 | 0.01 | 0.76 | **1.32%** | 14,242 |
| XLF | 58P (ATM) | −0.49 | 1.10 | 1.20 | 0.10 | 1.15 | **8.70%** | 125 |
| XLK | 175P | −0.26 | 3.35 | 3.85 | 0.50 | 3.60 | **13.89%** | 18 |
| XSP | 740P | −0.20 | 5.00 | 5.16 | 0.16 | 5.08 | **3.15%** | 25 |
| SPXW | 7400P | −0.20 | 50.70 | 51.00 | 0.30 | 50.85 | **0.59%** | 61 |

Notes:
- The live SPY moneyness profile reproduces the **U-shape** in the owner's dataset
  (tightest ATM, wider both OTM and deep ITM) at roughly 0.4x the level.
- The deep-ITM widening (0.72% at 0.87Δ, a 40¢ spread) is exactly the anomaly
  Muravyev–Pearson set out to explain — it cannot be hedging cost, since deep-ITM
  options need almost no rebalancing.
- **Sector SPDRs are not "SPY-like."** XLK at 13.89% and XLF ATM at 8.70% are an order
  of magnitude worse than SPY. XLE is the exception (1.32%) purely because that strike
  had 14,242 contracts of volume. Sector-SPDR liquidity is strike-specific and fragile.

## 1b. Measured spreads — SINGLE STOCKS (the coordinator's expected gap: confirmed, large)

ATM 43-DTE puts, **2026-08-06 closing quotes (16:00 ET)**. These are EOD quotes, so they
are methodologically comparable to the owner's EOD SPY dataset.

| Symbol | Strike | Δ | Bid | Ask | Spread | Mid | **Spread % of mid** | RT $/ct | Volume |
|---|---|---|---|---|---|---|---|---|---|
| NVDA | 220 | −0.47 | 12.40 | 12.50 | 0.10 | 12.45 | **0.80%** | $10 | 1,764 |
| MSFT | 500 | −0.47 | 19.40 | 19.95 | 0.55 | 19.67 | **2.80%** | $55 | 581 |
| AAPL | 310 | −0.43 | 8.85 | 9.25 | 0.40 | 9.05 | **4.42%** | $40 | 1,251 |
| META | 590 | −0.46 | 28.15 | 29.45 | 1.30 | 28.80 | **4.51%** | $130 | 19 |
| CAT | 860 | −0.47 | 46.50 | 50.95 | 4.45 | 48.73 | **9.13%** | $445 | 7 |
| COST | 950 | −0.47 | 27.00 | 30.15 | 3.15 | 28.57 | **11.02%** | $315 | 17 |
| PANW | 360 | −0.45 | 28.65 | 32.85 | 4.20 | 30.75 | **13.66%** | $420 | 32 |

**Median single-stock ATM spread: 4.51%.** Range 0.80% → 13.66%.

Against the owner's SPY ATM EOD median of 0.75%:
- **6.0x worse at the median single name**
- **18.2x worse at the worst name measured**

And note that **4.51% median lands squarely inside the Broadie–Chernov–Johannes 3–5%
band.** The academic estimates were never wrong; they simply describe a different
liquidity regime — one that today's single-stock options still inhabit and SPY has left.

Caveat: these are 16:00 ET closing quotes and are wider than mid-day. NVDA at 0.80%
demonstrates a genuinely liquid single name can approach ETF tightness even at the
close; the dispersion across names is the finding, not the absolute level. n=7 on one
day — indicative, not a distribution. **Recommendation: run the owner's EOD pipeline
over the single-stock book before sizing anything there.**

---

## 2. PFOF and price improvement — does retail get the mid?

**Short answer: no, and the PFOF arithmetic proves it.**

### Robinhood's options PFOF, from its own filings

| Period | Options revenue | Contracts traded | **PFOF per contract** |
|---|---|---|---|
| Q2 2026 | $342M | 774M | **$0.442** |
| Q2 2025 | $265M (implied) | 516M (implied) | **$0.514** |
| FY2025 | $1,123M | — | — |
| FY2024 | $760M | — | — |
| FY2023 | $505M | — | — |

Source: [HOOD Q2 2026 8-K Ex-99.1](https://www.sec.gov/Archives/edgar/data/1783879/000178387926000113/q22026robinhoodexhibit991.htm)
(filed 2026-07-29: "Options Contracts Traded increased 50% year-over-year to a record
774 million"; "options revenue of $342 million, up 29%") and
[HOOD FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1783879/000178387926000023/hood-20251231.htm)
(filed 2026-02-18, revenue disaggregation note). The 10-K states: *"In the case of
options, our fee is on a per contract basis based on the underlying security."*

### The arithmetic that settles the question

A wholesaler pays Robinhood ~$0.44/contract and must still profit. Therefore the
wholesaler's gross capture per contract must exceed $0.44.

- SPY 740P, spread $0.02 → **half-spread = $1.00/contract**. PFOF alone consumes
  **44% of the entire half-spread.** There is no way to route this order at the
  midpoint and fund a $0.44 payment — midpoint execution captures zero.
- Single-stock option, spread $0.55 (MSFT above) → half-spread $27.50. Here $0.44 is
  1.6%, so meaningful price improvement *is* fundable — and indeed the wider the
  spread, the more room exists.

**Conclusion:** on penny-wide ETF options the retail marketable order fills at or very
near **the touch**, not the mid. On wide single-stock options there is room for genuine
price improvement, but the spread being improved upon is itself 6–18x wider.

Corroboration from Muravyev–Pearson's own data: **84% of option trades occur at the
NBBO prices** (2003–2006 sample) — i.e. at the touch.

### The Muravyev–Pearson caveat that matters most

The paper is titled "Options Trading Costs Are Lower than You Think" and is routinely
cited to argue option costs are overstated. Read the actual text:

> "At most only a few retail investors have the resources and ability to time their
> option trades based on high-frequency changes in stock prices... **Retail and other
> investors who are not able to time executions will on average trade when the option
> price is expected to stay the same and their costs will equal the conventionally
> measured effective spreads.**"

Their headline numbers (timing-adjusted effective spread of 1.3¢ vs conventional 6.2¢ vs
quoted 8.1¢) apply to **algorithmic proprietary and institutional traders**, ~40% of
trades in-sample. **The paper explicitly assigns retail the full conventional effective
spread.** Citing this paper to justify low retail cost assumptions inverts its finding.

- Published: Muravyev & Pearson, *Review of Financial Studies* 33(11), 4973–5014,
  Nov 2020 (online 2020-02-10).
  [Abstract](https://academic.oup.com/rfs/article-abstract/33/11/4973/5732665) ·
  [Working paper PDF](https://www.cicfconf.org/sites/default/files/paper_745.pdf)
- Published abstract: "Effective spreads of traders who time executions are less than
  40% of the size of conventional measures, and the overall average effective spread is
  one-quarter smaller than conventional estimates."

### The SEC's 2020 Robinhood settlement — and why it is not about options

SEC Order [33-10906](https://www.sec.gov/files/litigation/admin/2020/33-10906.pdf),
2020-12-17; $65,000,000 civil penalty; Admin. Proc. 3-20171.
[Press release 2020-321](https://www.sec.gov/newsroom/press-releases/2020-321).

Findings (verbatim from the order):
- ¶22: a principal trading firm told Robinhood that large retail brokers "typically
  receive four times as much price improvement for customers than they do payment for
  order flow for themselves — **an 80/20 split** of the value between price improvement
  and payment for order flow."
- ¶23: Robinhood instead negotiated "approximately a **20/80 split**... Robinhood
  explicitly offered to accept less price improvement for its customers than what the
  principal trading firms were offering, in exchange for receiving a higher rate of
  payment for order flow for itself."
- ¶40: for orders over 500 shares, the average Robinhood order "lost over $15 in price
  improvement"; over 2,000 shares, "more than $23 per order."
- ¶42: total customer harm **$34.1 million**, Oct 2016–Jun 2019, net of the ~$5/order
  commissions competitors then charged.

**Critical scope limitation:** the order concerns **equity securities only** (¶10:
"customer orders to buy or sell equity securities"). The word "options" appears nowhere
in the findings. Robinhood did not launch options until Dec 2017. **There is no
equivalent regulatory finding on Robinhood options execution quality.**

### And there is no data to check it with

**Rule 605 does not cover options.** 17 CFR §242.605 applies to "covered orders in **NMS
stocks**" — not NMS securities. [Text](https://www.law.cornell.edu/cfr/text/17/242.605).
The SEC's 2024 Rule 605 expansion (effective for larger firms) still covers only NMS
stocks. Consequences:
- No standardized effective-spread, price-improvement, or effective/quoted statistics
  exist for retail **options** orders at any broker.
- Rule 606 disclosures show *routing venues and payment received* but not execution
  quality.
- **You cannot verify your options execution quality from public data.** The only
  measurement available is your own fills vs. the NBBO midpoint at order-entry time —
  which is worth logging.

---

## 3. Commissions and fees — Robinhood's actual current schedule

Primary source: **[Robinhood Financial Standard Pricing Fee Schedule
(PDF)](https://cdn.robinhood.com/assets/robinhood/legal/RHF%20Fee%20Schedule.pdf)**,
document stamp `20260430-5448493-17186923` (2026-04-30).

| Item | Amount | Applies |
|---|---|---|
| Commission, listed equity/ETF options | **$0** | — |
| **Options Regulatory Fee + OCC Clearing Fee** (bundled) | **$0.04 / contract** | **buys AND sells** |
| Consolidated Audit Trail (CAT) fee | $0.0003 / contract | buys and sells |
| FINRA Trading Activity Fee (TAF) | **$0.00329 / contract**, cap $9.79 | **sells only**, eff. 2026-01-01 |
| SEC Section 31 "Regulatory Fee" | **$20.60 per $1,000,000** of principal, rounded up to the penny | **sells only**, eff. **2026-04-04** (was $0.00 before that date) |
| **Index options contract fee (SPX/XSP/NDX)** | **$0.50 / contract** non-Gold; **$0.35** Gold | **buys AND sells**, plus exchange fees |
| Exercise / assignment fee | **Not listed → $0** | — |
| Worthless securities processing | $0 | — |

Answering the specific question asked: the charge is **$0.04 per contract, not $0.03**,
it bundles ORF and OCC clearing (Robinhood does not itemize them), and it is charged on
**both** the opening and closing side. Robinhood's footnote v discloses that it computes
"an average blended rate" and that "the ORF amount collected from you by Robinhood **may
differ from or exceed** the ORF that Robinhood pays to OCC."

Two items worth flagging:
1. **The SEC Section 31 fee was $0.00 until 2026-04-04** and is now $20.60/$1M. On a
   $549 option sale that is ~$0.011, rounded up to $0.02.
2. **Index options are NOT commission-free at Robinhood.** $0.50/contract each way is
   ~12x the all-in ETF-option regulatory cost. This materially damages the SPX/XSP tax
   case (§7).

### All-in per-contract, round trip (open + close)

| Instrument | Regulatory + contract fees, round trip |
|---|---|
| SPY option ($5.49 premium) | **$0.095 / contract** |
| XLK option ($3.60 premium) | **$0.091 / contract** |
| XSP option ($5.08 premium) | **$1.094 / contract** |
| SPXW option ($50.85 premium) | **$1.189 / contract** |

**For ETF and single-stock options, fees are noise — bid-ask is ~30x larger.** For index
options the contract fee is real but still second to the spread.

---

## 4. The multi-leg problem

A vertical crosses two spreads to open and two to close. But the four crossings are
**four half-spreads**, which sum to *(full spread of leg A) + (full spread of leg B)* —
not four full spreads. This is a common overestimate.

Round-trip friction, 1-lot 43-DTE vertical, from the live quotes above:

| Structure | Bid-ask | Fees | **Total** | **% of credit** | % of max loss |
|---|---|---|---|---|---|
| SPY 740/700 put spread ($332 credit, $40 wide) | $3.00 | $0.17 | **$3.17** | **1.0%** | 0.09% |
| XSP 740/700 put spread ($303 credit) | $30.00 | $2.17 | **$32.17** | **10.6%** | 0.87% |
| XLK 175/165 put spread ($170 credit, $10 wide) | $85.00 | $0.17 | **$85.17** | **50.1%** | 10.2% |

**SPY verticals are cheap — 1% of the credit.** The multi-leg problem is essentially a
non-issue on SPY and becomes catastrophic exactly in proportion to how far the
underlying is from SPY's tick regime. An XLK vertical loses **half the credit** to
friction before the trade has any chance to work.

### Do spread orders fill better than legging? Yes — mechanically.

From [Cboe's complex order documentation](https://www.cboe.com/us/options/trading/complex_orders/):
- **Complex Order Book (COB)** handles orders up to **16 legs** as a single package.
- **Complex Order Auction (COA)**: marketable/near-marketable complex orders trigger a
  **100-millisecond electronic auction**; responders may reply in **$0.01 increments**.
- Orders are "auctioned as a packaged order with one net price," and can execute at net
  prices **inside the individual-leg NBBO**.

This is the key structural advantage: the $0.01 COA response increment applies to the
*net price* even when the individual legs are on $0.05 ticks. A single-stock or
sector-SPDR vertical can therefore fill at a net price finer than the leg ticks
suggest — which partly mitigates (but does not eliminate) the XLK-style penalty above.

Practical implications:
1. **Always submit spreads as a single complex order**, never leg in. Legging forfeits
   the COA, exposes you to leg risk, and pays both touches.
2. **Work the net price.** The COA exists to find price improvement; a limit at the net
   mid has a real chance.
3. Note a Cboe constraint: SPX/SPXW customer complex orders during RTH are capped at
   **10 contracts on the smallest leg** for COA eligibility.

---

## 5. Assignment, early exercise, and pin risk

### What actually happens to options (debunking the "80–90% expire worthless" myth)

Per OCC/OIC ([Options Industry Council](https://www.optionseducation.org/referencelibrary/faq/options-exercise)):

> "More than **72%** of all option contracts are closed out in the market prior to
> expiration. Additionally, another **22%** expire without value while the remaining
> **6%** get exercised."

So ~22% expire worthless, not 80–90%. The popular claim is false. Note also that only
**6%** are exercised at all — early exercise is the exception, not the rule.

### Exercise by exception

OCC auto-exercises at **$0.01 in the money**, all account types, equity and index. But
this is *not* mandatory: clearing members may submit contrary exercise instructions. A
long option 1¢ ITM that you do not want exercised requires an affirmative instruction to
your broker — and Robinhood's default is to sell/exercise automatically near expiry
(the API exposes a per-contract `sellout_datetime`, 19:45 UTC on expiration day for SPY).

Assignment allocation: "OCC randomly assigns exercise notices to its clearing members
who, in turn assign their customers."

### The ex-dividend early-exercise condition

Early exercise of an American short **call** is rational immediately before the ex-date
when the dividend exceeds the remaining time value. Precisely, exercise when:

```
D  >  P + K·r·t
```
where `D` = dividend, `P` = value of the same-strike put, `K` = strike, `r` = short rate,
`t` = time to expiry. (Exercising early forfeits the put-equivalent optionality and the
interest on the strike, and gains the dividend.)

### The dates that matter — measured today

| ETF | Quarterly dividend | Yield | Next / last ex-date |
|---|---|---|---|
| **SPY** | **$1.9035** | 1.02% | **2026-09-18** |
| QQQ | $0.8135 | 0.51% | 2026-06-22 |
| XLF | $0.1871 | 1.43% | 2026-06-22 |
| XLE | $0.3849 | 2.55% | 2026-06-22 |
| XLK | $0.2279 | 0.50% | 2026-06-22 |

Source: Robinhood fundamentals API, 2026-08-06.

**Two important corrections to the common belief:**

1. **SPY's ex-date is the third Friday — which is expiration day itself.** SPY's next
   ex-date, 2026-09-18, is *exactly* the expiration I priced throughout this document.
   A short SPY call in the Sept monthly is at peak assignment risk on **Thursday
   2026-09-17**, the last day to exercise and capture $1.90/share.
2. **QQQ and the sector SPDRs did NOT go ex on the third Friday** in the most recent
   quarter — they went ex on **Monday 2026-06-22**, the next business day after the
   June 19 expiration. So the "ex-div collides with opex" rule holds for SPY but not
   currently for QQQ/XLF/XLE/XLK. Verify per-quarter rather than assuming.

**Practical threshold for SPY:** with $1.9035 of dividend and ~1 day to expiry, the
matching put must be worth less than ~$1.90 for exercise to be rational. At 43 DTE your
short call is safe; the risk is concentrated in the final days before the September,
December, March and June ex-dates. Sizing rule: **be flat or defended in SPY short calls
into the third Thursday of quarter-end months.**

### Documented irrational early exercise

Poteshman & Serbin, "Clearly Irrational Financial Market Behavior: Evidence from the
Early Exercise of Exchange Traded Stock Options," *Journal of Finance* 2003
([SSRN 280795](https://doi.org/10.2139/ssrn.280795)). Finding: a large volume of early
exercises are unambiguously irrational (exercising when the option is worth more sold
than exercised), concentrated in discount-broker retail accounts and *not* in
professional accounts.

**Asymmetric consequence for you:** irrational early exercise is a *gift* to the short
(you keep extrinsic value you should have lost). Rational early exercise is the tail
that hurts. The 6% overall exercise rate means assignment is rare — but it is not
randomly distributed, it clusters at ex-dates and deep ITM.

### Pin risk and the weekend gap

The structural hazard for a short option holder: you do not learn assignment status
until after Friday's close, and OCC processes exercises Saturday. If your short leg
pins the strike, you may discover Saturday/Sunday that you hold an unhedged 100-share
position per contract, with **no ability to trade until Monday's open**. A weekend gap
is unhedgeable.

**Assignment on the short leg of a defined-risk vertical is the small-account killer.**
The spread is "defined risk" only in P&L terms, not in *capital* terms. Assignment on
one short SPY 740 put converts a $40-wide spread — max loss $3,668 — into an obligation
to buy 100 shares at $740 = **$74,000 of stock**. For a small account this triggers a
margin call and likely forced liquidation at Monday's open, at whatever price exists.
The long leg protects the P&L but does not supply the cash.

### Index options eliminate all of this

SPX / XSP / NDX are **European-style and cash-settled**: no early exercise, no
assignment, no stock position, no weekend gap, no pin risk. Confirmed structurally in
the chain metadata (`underlying_type: "index"`, `underlying_instruments: []`).

One residual risk: **AM vs PM settlement.** From the live chain data:
- `SPX` chain (third-Friday monthlies): `settle_on_open: true` → **AM-settled** on the
  SET print, computed from Friday's *opening* prices. You stop trading Thursday but
  your settlement is determined by Friday's open — an overnight gap you cannot hedge.
- `SPXW` and `XSP` chains: `settle_on_open: false` → **PM-settled** at the close.

**Prefer PM-settled (SPXW/XSP) to avoid SET risk.**

---

## 6. Slippage in stress

### Hard data on the regimes (Cboe official VIX history, through 2026-08-05)

Source: [Cboe VIX_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)

| Event | Date | Open | High | Close | Note |
|---|---|---|---|---|---|
| **COVID** | 2020-03-16 | 57.83 | 83.56 | **82.69** | **Highest close in VIX history** |
| COVID | 2020-03-18 | 69.37 | **85.47** | 76.45 | Highest intraday of the era |
| GFC | 2008-10-24 | — | **89.53** | 79.13 | All-time intraday high |
| **Volmageddon** | 2018-02-05 | 18.44 | 38.80 | **37.32** | **+115.6% in one day** from 17.31 |
| Volmageddon | 2018-02-06 | 37.32 | **50.30** | 29.98 | 28-point intraday round trip |
| **Yen carry** | 2024-08-05 | 23.39 | **65.73** | **38.57** | **27-point intraday collapse** |
| **Tariff** | 2025-04-07 | **60.13** | 60.13 | 46.98 | Opened at the high, low 38.58 |
| Tariff | 2025-04-08 | 44.04 | 57.52 | 52.33 | |

### The 2024-08-05 event is the smoking gun for spread risk

VIX opened at 23.39 (= prior close), printed **65.73**, and closed at **38.57**. VIX is
computed from SPX option **bid/ask midpoints**. A 27-point intraday collapse with no
corresponding move in realized risk is the signature of **quotes so wide that the
midpoint itself became unreliable** during the illiquid early session. This is the
cleanest documented case that in stress, option quotes stop carrying information —
and the index built from them printed a number that never represented a tradeable price.

**Implication: the mid you see in a stress open is not a price you can trade at.**

### Why spreads widen — the mechanism

Cho & Engle (1999), "Modeling the Impacts of Market Activity on Bid-Ask Spreads in the
Option Market," [NBER w7331](https://www.nber.org/papers/w7331). Their **derivative
hedge theory**: option spreads are driven by the market maker's ability to hedge in the
*underlying*, so "spreads arise from the illiquidity of the underlying market, rather
than from inventory risk or informed trading in the option market itself." Key findings:
- Option-market volume is **insignificant** in explaining option spreads.
- Option spreads correlate positively with **underlying** spreads.
- **Both very slow and very fast markets produce larger spreads** — i.e. spreads widen
  at both tails of activity.

This mechanism predicts precisely the wrong-way risk: in a crash the underlying's own
spread widens, hedging becomes expensive and uncertain, and option spreads widen
*because* of it — at the exact moment a short-premium book needs to buy back.

### The asymmetry that matters for short premium

Muravyev & Pearson document that spreads rise with |delta| — quoted spreads average
below 7¢ for OTM options but **11¢ for ITM options**. Live data reproduces this: the
0.87Δ SPY call has a **40¢** spread (0.72%) vs 1–2¢ for OTM.

**This is the core structural hazard for short premium.** A short put you sold at 20Δ
for $5.49 with a 2¢ spread becomes, after a selloff, a 70–90Δ option — and it now
carries a 20–40¢ spread. **The instrument you must buy back is a different, far more
expensive instrument than the one you sold.** The spread widens both because volatility
rose *and* because your option migrated up the delta curve into the wide part of the
smile. These compound.

Planning assumption: **budget 5–10x the calm-market spread for a stressed exit**, and
treat the entry spread as a lower bound on the exit spread, never an estimate of it.

Honest limitation: I was unable to obtain contemporaneous SPY/SPX option bid-ask
snapshots from March 2020 or February 2018 within this session (web search budget
exhausted). The VIX data above is hard and primary; the spread-widening magnitudes are
inferred from mechanism plus the 2024-08-05 midpoint anomaly, not measured. **This is
the highest-value remaining measurement: the owner's own EOD SPY chain archive spans
2008–2025 and therefore already contains March 2020 and February 2018. Query it for the
spread distribution conditional on VIX bucket — that would replace inference with fact.**

---

## 7. Taxes

*Research, not tax advice.*

### The statute

[26 U.S.C. §1256](https://www.law.cornell.edu/uscode/text/26/1256). A "section 1256
contract" includes "any **nonequity option**" = "any listed option which is not an equity
option." An **equity option** is one on stock or "any **narrow-based** security index" —
and the statute expressly excludes broad-based indexes from the equity-option definition.

- **Section 1256 (60/40):** SPX, SPXW, XSP, NDX, RUT, VIX options — broad-based index
  options.
- **NOT 1256:** SPY, QQQ, IWM and all sector SPDRs. These are options on an *ETF*, which
  is a security, so they are **equity options** taxed as ordinary short-term. The
  underlying tracking a broad index is irrelevant.

§1256(a): contracts are "treated as sold for fair market value on the last business day
of such taxable year" (**mark-to-market**), with gain/loss "60 percent... long-term...
40 percent... short-term" regardless of holding period.

### The advantage, exactly

The Section 1256 benefit reduces to a clean formula:

> **Advantage (percentage points) = 0.6 × (ordinary rate − LTCG rate)**

| Bracket | LTCG | 1256 blended rate | vs. ordinary | **Advantage** |
|---|---|---|---|---|
| 22% | 15% | 17.80% | 22% | **4.20 pts** |
| 24% | 15% | 18.60% | 24% | **5.40 pts** |
| 32% | 15% | 21.80% | 32% | **10.20 pts** |
| 35% | 15% | 23.00% | 35% | **12.00 pts** |
| 37% (top) | 20% | **26.80%** | 37% | **10.20 pts** |

The widely-quoted "26.8% vs 40.8%" comparison is **inconsistent** — it takes the blended
rate *excluding* NIIT and compares it to the ordinary rate *including* NIIT. Done
consistently: 26.8% vs 37.0% pre-NIIT, or 30.6% vs 40.8% post-NIIT. Either way the true
top-bracket advantage is **10.2 points**, not 14.

Other §1256 features: **no wash-sale rules** apply (mark-to-market moots them); losses
may be **carried back 3 years** against prior §1256 gains by election (Form 6781);
reporting is aggregate on Form 6781 rather than per-trade on Form 8949. The
mark-to-market rule has a cash-flow cost: unrealized year-end gains are taxed.

### But XSP's spread destroys the advantage — quantified

Matched 20Δ, 43 DTE, measured today:

| | Spread | % of mid | Round-trip bid-ask | RH contract fee (RT) |
|---|---|---|---|---|
| SPY 740P | $0.02 | 0.36% | $4.00 | $0.10 |
| **XSP 740P** | **$0.16** | **3.15%** | **$32.00** | **$1.09** |

XSP's spread is **8.8x SPY's** in relative terms, and Robinhood charges **$0.50/contract
each way** on index options versus effectively nothing on ETF options. Total excess
friction ≈ **$32 per contract round trip**.

**Break-even net gain required for XSP to beat SPY after tax:**

| Bracket | Advantage | **Required net gain per contract round-trip** |
|---|---|---|
| 22% | 4.2 pts | **$762** |
| 24% | 5.4 pts | **$593** |
| 32% / 37% | 10.2 pts | **$314** |

An XSP 20Δ 43-DTE put carries only ~$508 of total premium. A realistic per-contract
profit is $100–250. **At typical retail brackets, XSP does not pay for itself versus
SPY.** The tax advantage is real but smaller than the liquidity penalty.

XSP liquidity, measured: 740P volume **25**, OI **224**; 700P volume **14**, OI **1,471**.
Compare SPY 740P: volume **1,123**, OI **20,217**. XSP is thinly traded.

**Where the index case *does* work:** SPXW. Measured spread 0.59% of mid at 20Δ/43 DTE —
only 1.6x SPY, far better than XSP's 8.8x, because the $50.85 premium dwarfs the $0.10
tick. The obstacle is size: one SPXW contract carries ~$5,085 of premium and ~10x the
notional. **For an account large enough to trade SPX in round lots, the Section 1256
advantage is capturable. For a small account forced into XSP, it is not.**

---

## Bottom line for this account

1. **SPY is genuinely cheap and the academic warnings don't apply to it.** ~1% of credit
   round-trip on a vertical. Trade SPY freely; the owner's measured 0.75%/1.30% numbers
   are sound.
2. **The single-stock book is where the cost stack bites** — median 4.51% ATM, up to
   13.66%, i.e. 6–18x SPY. This is precisely the regime the academic literature
   describes. Measure it before sizing it.
3. **Sector SPDRs are not SPY substitutes.** XLK at 13.89% and XLF at 8.70% would
   consume half a vertical's credit. Avoid, or restrict to high-volume strikes like the
   XLE example (1.32%).
4. **Never leg a spread.** Use complex orders; the COA prices in $0.01 net increments
   even when legs are on nickel ticks.
5. **Assume you fill at the touch, not the mid.** The PFOF arithmetic ($0.44/contract
   against a $1.00 half-spread on SPY) makes midpoint fills impossible on penny-wide
   ETF options. Log your fills vs. NBBO mid — no public data will tell you.
6. **Be flat SPY short calls into the third Thursday of Mar/Jun/Sep/Dec.** Next: SPY
   goes ex-$1.9035 on **2026-09-18**.
7. **Budget 5–10x calm spreads for stressed exits.** Your short option migrates into the
   wide, high-delta part of the surface exactly when you need to close it.
8. **Skip XSP.** The Section 1256 advantage (4–10 points) loses to a $32/contract
   liquidity-plus-fee penalty at realistic trade sizes. Revisit at SPX size.

---

### Open items / lower confidence

- **March 2020 and February 2018 option spread magnitudes are inferred, not measured.**
  The owner's 2008–2025 EOD archive contains these dates — querying spread vs. VIX
  bucket from it is the single highest-value follow-up.
- Single-stock spreads are **n=7, one day, closing quotes**. Directionally certain,
  distributionally unmeasured.
- OCC clearing fee and ORF are **bundled by Robinhood** at $0.04 and not itemized;
  the component rates were not independently verified against OCC/exchange schedules.
- 2026 federal bracket dollar thresholds were not retrieved; the tax table above is
  expressed in marginal-rate terms, which is threshold-independent.
