# US Listed Options — All-In Regulatory + Commission Fee Stack (retail)

Research date: **2026-08-06**. Every number below carries its primary source URL and effective date.
Numbers marked **[VERIFIED]** were read directly from a primary document (SEC rule filing, Federal
Register full text, OCC schedule of fees, or the broker's own published fee schedule PDF/page).
Numbers marked **[UNCERTAIN]** are secondary or inferred and should be re-checked before use.

---

## 0. TL;DR for the Robinhood question

**Robinhood, level 3, self-directed retail account, SPY (equity/ETF) options:**

| Item | Per contract per side |
|---|---|
| Commission | **$0.00** |
| "Options Regulatory and OCC Clearing Fee" (RH blended charge, buys **and** sells) | **$0.04** |
| Consolidated Audit Trail (CAT) fee | $0.0003 |
| FINRA TAF (sells only) | $0.00329 |
| SEC Section 31 (sells only) | $20.60 per $1,000,000 of sale proceeds ≈ $0.0041 on a $2.00 premium contract |
| **Economic all-in, buy side** | **≈ $0.0403** |
| **Economic all-in, sell side** | **≈ $0.0476** (at $2.00 premium) |
| **Economic all-in, round trip (1 contract)** | **≈ $0.088** |
| **Actually billed, round trip (1 contract), after RH rounding** | **≈ $0.09** |

**1-lot SPY iron condor, opened and closed (8 contract-sides): ≈ $0.36 total.**
Held to worthless expiration instead of closed (4 sides): **≈ $0.18 total.**

Against a $40–$80 condor credit that is **0.45%–0.90% of the credit**. The fee stack is *not*
what kills this trade. The bid/ask spread is: crossing 8 SPY option legs at $0.01–$0.02 wide costs
**$8–$16 per condor**, i.e. 20–45x the entire regulatory fee stack, and 10–40% of the credit.
Model slippage, not fees, if you only have budget to model one.

---

## 1. OCC clearing fee

Source: OCC Schedule of Fees, https://www.theocc.com/company-information/schedule-of-fees
(page footer: "As of November 2025. ALL FEES ARE SUBJECT TO CHANGE.")

| Line | Rate |
|---|---|
| Clearing fee — All Transactions | **$0.025 / contract** **[VERIFIED]** |
| Linkage, per side | $0.00 |
| Minimum Monthly Clearing Fee | $200.00 |
| New products (first listing → end of following calendar month) | $0.00 |
| **Exercise Fee — per line item on exercise notice** | **$1.00** **[VERIFIED]** |

Charged to the **clearing member** on each side of each cleared contract. A retail round trip
therefore costs the broker $0.025 (buy) + $0.025 (sell) = **$0.05/contract**.

### History / caps / holidays
- Reduced from **$0.045 → $0.02**/contract effective **June 1, 2021**.
  https://www.businesswire.com/news/home/20210419005648/en
- **January 2025**: increased **$0.02 → $0.025**/contract, and the **$55.00 per-trade fee cap was
  removed**. Confirmed in SR-OCC-2025-019: "Beginning in January 2025, OCC increased its clearing
  fee to $0.025 per contract in part to cover increased capital expenditures and decreasing interest
  income." https://www.sec.gov/files/rules/sro/occ/2025/34-104274.pdf **[VERIFIED]**
  OCC Info Memo #55830 (Dec 31, 2024): https://infomemo.theocc.com/infomemos?number=55830
- The **$55.00 per-trade cap survives only for Linkage transactions** (>2,750 contracts), and OCC
  then **eliminated the linkage clearing fee entirely** (SR-OCC-2025-016, Nov 2025), taking linkage
  to $0.00. https://www.sec.gov/files/rules/sro/occ/2025/34-104106.pdf and
  https://www.sec.gov/files/rules/sro/occ/2025/34-104106-ex5.pdf **[VERIFIED]**
  There is **no per-trade cap on the ordinary $0.025 clearing fee today.**
- **Fee holiday: Dec 1 – Dec 31, 2025, clearing fee = $0.00/contract.** Reverted to $0.025 on the
  first trading day of 2026. SR-OCC-2025-019, Exhibit 5A:
  https://www.sec.gov/files/rules/sro/occ/2025/34-104274-ex5a.pdf **[VERIFIED]**
  OCC estimated ~$59.4M of foregone revenue. OCC Info Memo #57379 (Oct 3, 2025):
  https://infomemo.theocc.com/infomemos?number=57379
- **No 2026 fee holiday has been filed as of 2026-08-06** (searched SEC/Federal Register OCC
  filings). OCC's stated policy is that it will consider fee holidays whenever LNAFBE exceeds 110%
  of Target Capital, and it said LNAFBE "appears likely to remain above that mark for the remainder
  of 2025 and 2026" — so another holiday is plausible but not currently scheduled. **[UNCERTAIN]**

> Note on "the $0.01/contract cap": I found **no** $0.01/contract OCC cap in any current or recent
> filing. The cap that existed and was removed in Jan 2025 was **$55.00 per trade** (bites only at
> ≥2,750 contracts). Retail brokers commonly *quote* $0.01–$0.02 as their own OCC pass-through,
> which is a broker convention, not an OCC rule.

---

## 2. Options Regulatory Fee (ORF) — by exchange

**The ORF model changed fundamentally on July 1, 2026.** Until then, each exchange charged ORF on
*all* customer-range contracts cleared by its member, regardless of where they executed (so a member
of 10 exchanges paid ~10 small ORFs on every contract). Since **July 1, 2026**, ORF is
**"On-Exchange ORF"**: each exchange charges only for contracts that **executed on that exchange**
and clear in the customer range at OCC. Rates therefore jumped ~10–50x, but you now pay **one**
exchange's ORF per contract-side instead of a stack of them.

Cboe rule filing describing the change: https://www.federalregister.gov/documents/2026/07/17/2026-14398/self-regulatory-organizations-cboe-exchange-inc-notice-of-filing-and-immediate-effectiveness-of-a
(SR-CBOE-2025-086 adopted the methodology Dec 12, 2025; implementation July 1, 2026.) **[VERIFIED]**

### Current ORF rates (per contract side, customer range)

| Exchange | ORF | Effective | Source |
|---|---|---|---|
| Cboe Options (C1) | **$0.01248** | 2026-07-01 | [FR 2026-14398](https://www.federalregister.gov/documents/2026/07/17/2026-14398/self-regulatory-organizations-cboe-exchange-inc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Cboe C2 | **$0.01417** | 2026-07-01 | [FR 2026-14399](https://www.federalregister.gov/documents/2026/07/17/2026-14399/self-regulatory-organizations-cboe-c2-exchange-inc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Cboe BZX Options | **$0.00476** | 2026-07-01 | [FR 2026-14400](https://www.federalregister.gov/documents/2026/07/17/2026-14400/self-regulatory-organizations-cboe-bzx-exchange-inc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Cboe EDGX Options | **$0.00286** | 2026-07-01 | [FR 2026-14411](https://www.federalregister.gov/documents/2026/07/17/2026-14411/self-regulatory-organizations-cboe-edgx-exchange-inc-notice-of-filing-and-immediate-effectiveness-of) **[VERIFIED]** |
| Nasdaq ISE | **$0.0080** | 2026-07-01 | [FR 2026-12256](https://www.federalregister.gov/documents/2026/06/18/2026-12256/self-regulatory-organizations-nasdaq-ise-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Nasdaq PHLX | **$0.0080** | 2026-07-01 | [FR 2026-12258](https://www.federalregister.gov/documents/2026/06/18/2026-12258/self-regulatory-organizations-nasdaq-phlx-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Nasdaq MRX | **$0.0080** | 2026-07-01 | [FR 2026-12255](https://www.federalregister.gov/documents/2026/06/18/2026-12255/self-regulatory-organizations-nasdaq-mrx-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Nasdaq GEMX | **$0.0100** | 2026-07-01 | [FR 2026-12254](https://www.federalregister.gov/documents/2026/06/18/2026-12254/self-regulatory-organizations-nasdaq-gemx-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Nasdaq Options Market (NOM) | **$0.0200** | 2026-07-01 | [FR 2026-12257](https://www.federalregister.gov/documents/2026/06/18/2026-12257/self-regulatory-organizations-the-nasdaq-stock-market-llc-notice-of-filing-and-immediate) **[VERIFIED]** |
| Nasdaq Texas (NTX) Options | **$0.0200** | 2026-07-01 | [FR 2026-12259](https://www.federalregister.gov/documents/2026/06/18/2026-12259/self-regulatory-organizations-nasdaq-texas-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| Nasdaq BX Options | $0.0005 under the *old* methodology through 2026-06-30; new-model rate set by SR-BX-2025-012, not re-filed in June 2026 | — | [FR 2025-24139](https://www.federalregister.gov/documents/2026/01/02/2025-24139/self-regulatory-organizations-nasdaq-bx-inc-notice-of-filing-and-immediate-effectiveness-of-a) **[UNCERTAIN]** |
| MIAX | **$0.0170** | 2026-07-01 | [FR 2026-14263](https://www.federalregister.gov/documents/2026/07/16/2026-14263/self-regulatory-organizations-miami-international-securities-exchange-llc-notice-of-filing-and) **[VERIFIED]** |
| MIAX Pearl | **$0.0240** | 2026-07-01 | [FR 2026-14264](https://www.federalregister.gov/documents/2026/07/16/2026-14264/self-regulatory-organizations-miax-pearl-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| MIAX Emerald | **$0.0220** | 2026-07-01 | [FR 2026-14268](https://www.federalregister.gov/documents/2026/07/16/2026-14268/self-regulatory-organizations-miax-emerald-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| MIAX Sapphire | **$0.0220** | 2026-07-01 | [FR 2026-14269](https://www.federalregister.gov/documents/2026/07/16/2026-14269/self-regulatory-organizations-miax-sapphire-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| BOX | **$0.0220** | 2026-07-01 | [FR 2026-14200](https://www.federalregister.gov/documents/2026/07/15/2026-14200/self-regulatory-organizations-box-exchange-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| MEMX Options | **$0.0200** | 2026-07 (immediately effective on filing) | [FR 2026-14862](https://www.federalregister.gov/documents/2026/07/23/2026-14862/self-regulatory-organizations-memx-llc-notice-of-filing-and-immediate-effectiveness-of-a-proposed) **[VERIFIED]** |
| NYSE Arca Options | $0.0120 from 2026-07-01, **→ $0.0080 effective 2026-09-01** | see source | [FR 2026-15925](https://www.federalregister.gov/documents/2026/08/06/2026-15925/self-regulatory-organizations-nysearca-inc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |
| NYSE American Options | $0.0160 from 2026-07-01, **→ $0.0050 effective 2026-09-01** | see source | [FR 2026-15926](https://www.federalregister.gov/documents/2026/08/06/2026-15926/self-regulatory-organizations-nyse-american-llc-notice-of-filing-and-immediate-effectiveness-of-a) **[VERIFIED]** |

### Prior (Jan 2 – Jun 30, 2026) rates, for comparison
Cboe Options $0.0023, BZX $0.0002, EDGX $0.0002, C2 $0.0003 — Cboe circular
[Regulatory Fee Update Effective January 2, 2026](https://cdn.cboe.com/resources/fee_schedule/2026/Cboe-Options-Exchanges-Regulatory-Fee-Update-Effective-January-2-2026.pdf) **[VERIFIED]**;
ISE $0.0011, BX $0.0005. NYSE Arca/American $0.0026.

**Practical retail takeaway:** a customer contract-side now attracts **one** exchange's ORF,
roughly **$0.003 – $0.024**, blended across routing venues to something in the **$0.010 – $0.020**
range. ORF applies to **both buys and sells** (any customer-range clearing), unlike TAF/SEC-31.
ORF is **not** assessed on Firm-range or Market-Maker-range accounts.

---

## 3. SEC Section 31 fee

- **Current rate: $20.60 per $1,000,000 of covered sale proceeds ($0.0000206 per $1), effective
  April 4, 2026.** **[VERIFIED]**
  - SEC Fee Rate Advisory FY2026: https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2
  - Order Making FY2026 Annual Adjustments: https://www.federalregister.gov/documents/2026/03/04/2026-04233/order-making-fiscal-year-2026-annual-adjustments-to-transaction-fee-rates
  - FINRA Information Notice 3/17/2026: https://www.finra.org/rules-guidance/notices/information-notice-20260317
    — quotes new rate $20.60/M, prior rate $0.00/M, effective April 4, 2026, security futures
    unchanged at $0.0042 per round-turn.
  - Remains in effect until 60 days after FY2027 appropriation legislation is enacted.
- **Rate was $0.00 per million from May 14, 2025 through April 3, 2026.** **[VERIFIED]**
  FINRA Information Notice 4/24/2025: https://www.finra.org/rules-guidance/notices/information-notice-20250424
  ("will decrease from its current rate of $27.80 per million dollars in transactions to a new rate
  of $0.00 per million dollars in transactions", trade date May 14, 2025 or later).
  **Any backtest cost model calibrated on 2025 data will have a Section 31 hole in it.**
- FY2025 rate before that was **$27.80/M** (effective Feb 25, 2025).

### How it applies to options
- **Sales only.** Buys are never charged.
- **Assessed on premium, not notional.** The "covered sale" amount is the option **premium
  proceeds** = price × 100 × contracts. A $2.00 SPY call is a $200 sale, not a $60,000 sale.
- **Exercise/assignment of an equity option creates a stock sale** for the writer of a call /
  holder of a put, and *that* stock sale is charged Section 31 on the **full stock notional** —
  this is where Section 31 can actually bite (e.g. assignment on 1 SPY call at $600 → $60,000
  notional → $1.24). Cash-settled index options (SPX/XSP/NDX) have no such stock leg.
- Brokers round; Robinhood rounds **up** to the nearest penny, so the minimum effective charge on
  any option sale order is **$0.01**.

---

## 4. FINRA Trading Activity Fee (TAF)

Source: FINRA By-Laws Schedule A Section 1 (https://www.finra.org/rules-guidance/rulebooks/corporate-organization/section-1-member-regulatory-fees)
and the multi-year adjustment schedule filed under SR-FINRA-2024-019:
https://www.finra.org/rules-guidance/rule-filings/sr-finra-2024-019/fee-adjustment-schedule **[VERIFIED]**

| Year | Options, per contract (sales) | Equities, per share (sales) | Equity per-trade cap |
|---|---|---|---|
| 2025 | $0.00279 | $0.000166 | $8.30 |
| **2026 (current)** | **$0.00329** | $0.000195 | $9.79 |
| 2027 | $0.00390 | $0.000232 | $11.61 |
| 2028 | $0.00404 | $0.000240 | $12.05 |

- **Sales only.**
- **There is no per-trade cap on the options TAF.** The $9.79 cap in Schedule A applies to the
  **covered equity security** per-share TAF, not to options. Brokers (incl. Robinhood) often print
  the $9.79 cap on the same line as the option rate, which is misleading. **[VERIFIED — the cap
  language in Schedule A is attached to the per-share equity rate]**
- Rounded to the nearest penny by most brokers; if under one cent, typically rounded to $0.00,
  which means a **1–3 contract sale often pays $0.00 TAF in practice.**

---

## 5. Cboe index option surcharges (SPX / XSP / VIX) — what retail actually pays

Source: **Cboe Exchange, Inc. Fees Schedule — August 3, 2026**,
https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf **[VERIFIED, read directly]**

### Public Customer (capacity code "C") transaction fees per contract

| Product | Customer rate |
|---|---|
| **SPX / SPXW** | **$0.36** for premium ≤ $0.99; **$0.45** for premium ≥ $1.00 (codes {CS}/{CT}) |
| RUT | $0.18 ({CR}) |
| OEX / XEO | $0.35 ({CO}) |
| VIX (simple) | $0.10 / $0.25 / $0.40 / $0.45 by premium tier ({CV}/{CW}/{CX}/{CY}) |
| **XSP, MRUT, DJX** | **$0.07 for orders ≥ 10 contracts; a $(0.30) per-contract REBATE for orders < 10 contracts** ({CC}/{XC}) |
| All other index products | $0.18 ({CB}) |
| Equity / ETF / ETN options | **$0.00** ({CK}) — Cboe charges customers nothing on SPY etc. |
| NANOS | FREE |

### The surcharges — and why retail does NOT pay them
- **SPX Surcharge Fee: $0.20/contract**
- **Index License Surcharge: $0.10/contract** (OEX, XEO, VIX; SPX covered by the $0.20 line)
- **SPX (not SPXW) Execution Surcharge: $0.21; SPXW electronic: $0.14**
- **Footnote 14 (verbatim):** *"The Surcharge Fees apply to all non-public customer transactions
  (i.e. Cboe Options and non-Trading Permit Holder market-maker, Clearing Trading Permit Holder,
  JBO participant, and broker-dealer), including professionals, except for FLEX Micro
  transactions."* **[VERIFIED]**

**Therefore: a Priority (retail) Customer SPX trade pays the $0.36/$0.45 customer transaction fee
and NOT the $0.20 SPX surcharge or the $0.10 index license surcharge.** A **Professional Customer**
(>390 orders/day averaged over a calendar month) *does* pay them — that is a real cliff for a
high-frequency retail algo. Also note the Exotic Surcharge of $0.25 applies to capacity "C"
($0.03 for XSP/MRUT), and a Complex Surcharge of $0.12 applies on complex orders in equity/ETF and
"all other index" products.

**What brokers actually pass through** (see §6): they do *not* itemize the Cboe schedule; they bill
a flat per-symbol index fee that bundles the exchange fee plus a markup.

---

## 6. Broker fee schedules — current

### 6.1 Robinhood **[VERIFIED — read the official PDF]**
Source: **Robinhood Financial — Standard Pricing Fee Schedule**,
https://cdn.robinhood.com/assets/robinhood/legal/RHF%20Fee%20Schedule.pdf
Document control number on the PDF: **20260430-5448493-17186923** (i.e. April 30, 2026 revision).
Help article: https://robinhood.com/us/en/support/articles/trading-fees-on-robinhood/

| Line | Rate (verbatim) |
|---|---|
| US listed equities, ETFs, closed-end funds **and their options** | $0 commission |
| **Index Options (Contract Fee)** | **Non-Gold: $0.50 per options contract (buys and sells)**<br>**Gold: $0.35 per options contract (buys and sells)**<br>*"Index options are also subject to exchange fees, in addition to regulatory trading fees."* |
| Regulatory Fee (SEC Section 31) | "$20.60 per $1,000,000 of total principal amount of sale, **rounded up to the nearest penny**." Footnote iii: *"The published fee is effective April 4, 2026. Prior to April 4, 2026, the fee is $0.00."* |
| Trading Activity Fee | "Effective January 1, 2026 … **$0.00329 per contract (options sells)**. This fee is rounded to the nearest penny and no greater than $9.79." (rounded **down to 0** if < $0.01) |
| **Options Regulatory and OCC Clearing Fee** | **"$0.04 per options contract (buys and sells)."** |
| Consolidated Audit Trail (CAT) Fee | **$0.0003 per options contract** (rounded to nearest penny; < $0.01 → $0) |
| **Exercise fee** | **Not listed → $0** |
| **Assignment fee** | **Not listed → $0** |
| **Expiration (worthless)** | **Not a trade; no contract fee, no OCC/ORF fee, no TAF, no SEC fee. $0.** |

**On the "$0.03 extra" story.** This is real and now **$0.04**, not $0.03. Robinhood collapses ORF
+ OCC clearing into a single **$0.04/contract charged on BOTH buys and sells**. Its own footnote v
is explicit that this is a house number, not a pass-through:

> *"Robinhood calculates an average blended rate based on the amount it is required to remit to the
> exchanges. The fee charged by Robinhood **may differ from or exceed** the actual fee paid by
> Robinhood in connection with any transaction… You acknowledge, understand, and agree that
> Robinhood determines the amount of the ORF charged to you and its other customers **in its sole
> and exclusive discretion**, and that the ORF amount collected from you by Robinhood may differ
> from or exceed the ORF that Robinhood pays to OCC."* **[VERIFIED, verbatim]**

The help article dates the $0.04 combined charge to **January 10, 2025** (prior to that Robinhood
billed ORF alone at roughly $0.03). **[secondary — from the help article's own effective-date
label, not a filing]**

Sanity check against true cost: OCC $0.025 + blended on-exchange ORF (~$0.010–$0.020 post-July-2026)
= **$0.035–$0.045**. So as of August 2026 Robinhood's $0.04 is roughly break-even to slightly
under-recovering — it was clearly *over*-recovering during the Jan–Jun 2026 window when ORF was
$0.0002–$0.0023 and true cost was ~$0.026.

Robinhood index options: it does list SPX/XSP/NDX/RUT/VIX index options, at $0.50/$0.35 per
contract **plus unspecified "exchange fees."** Robinhood does not publish the exchange-fee
schedule, so the true SPX all-in at Robinhood is **[UNCERTAIN]** — budget the Cboe customer rate
($0.45) on top unless verified from a live confirm.

### 6.2 tastytrade **[VERIFIED — read the official PDF]**
Source: https://tastytrade.com/pricing/ → https://assets.contentstack.io/v3/assets/blt7dc2e3d4a7071563/blt2b752fef372188fe/commissions-and-fees
Footer: **"Last updated July 30, 2026."**

| Line | Rate |
|---|---|
| Equity/ETF options | **$1.00/contract to open, $0.00 to close**, capped **$10 per leg** |
| Broad-based index options | **$1.00/contract to open, $0.00 to close** (excluded from the $10 cap) |
| Clearing fee — options | **$0.10/contract** (charged on opening **and** closing trades) |
| **ORF (tastytrade blended)** | **$0.02/contract** |
| FINRA TAF — option sales | $0.00329/contract |
| SEC fee | $20.60 per $1,000,000 in sales, *"As of April 4 2026"* |
| **Option Exercise / Assignment** | **$5.00** |
| **Single-Listed Exchange Proprietary Index Options Fees** | SPX **$0.60**; NDX $0.25; RUT $0.18; VIX $0.35; OEX/XEO $0.40; DJX $0.18; CBTX $0.50; MBTX $0.25; **XSP $0.00 for < 10 contracts per leg, $0.07 for ≥ 10 contracts per leg** (footnote 7) |

### 6.3 Interactive Brokers **[VERIFIED — read the live pricing page]**
Source: https://www.interactivebrokers.com/en/pricing/commissions-options.php

**IBKR Pro, US options, tiered** (≤ 10,000 contracts/month):
- Premium ≥ $0.10 → **$0.65/contract**
- Premium ≥ $0.05 and < $0.10 → **$0.50/contract**
- Premium < $0.05 → **$0.25/contract**
- Higher volume tiers: 10,001–50,000 → $0.50/$0.25; 50,001–100,000 → $0.25 all premiums;
  ≥100,001 → $0.15 all premiums
- **Minimum per order: $1.00** — and, critically, *"Order minimums will be applied to the individual
  legs of a COMBO order."* **[VERIFIED, verbatim]** This is the single biggest hidden cost for
  small multi-leg retail traders at IBKR: a 1-lot 4-leg condor pays **$4.00** per side, not $2.60.

**IBKR Lite**: $0.65/contract, $1.00 order minimum, US residents only, fixed rate on the first
1,000 US option contracts/month (Pro tiered pricing applies above that).

Pass-throughs, verbatim from the page:
- **OCC Clearing Fees: "All Contracts: 0.025 /contract"**
- **SEC Transaction Fee: "USD 0.0000206 * Value of Aggregate Sales"** (sell orders only)
- **FINRA Trading Activity Fee: "USD 0.00329 * Quantity Sold"**
- **FINRA Consolidated Audit Trail Fees: "USD 0.0003 /contract"**
- ORF charged by: AMEX, ARCA, BATS, BOX, CBOE, CBOE2, EDGX, EMERALD, ISE, GEMINI, MERCURY, MIAX,
  MEMX, NOM, NASDAQBX, PEARL, PHLX, SAPPHIRE
- IBKR **Pro** passes through **exchange fees + clearing + regulatory + transaction + surcharge**
  fees; IBKR **Lite** passes through **surcharge + regulatory + transaction + OCC clearing** but not
  exchange transaction fees.
- **"Commissions are not charged for US exercise and assignment."** **[VERIFIED, verbatim]**
- Explicit warning that tiered pass-throughs are not exact: *"Costs passed on to clients in IBKR's
  Tiered commission schedule may be greater than the costs paid by IBKR."*

### 6.4 E*TRADE (Morgan Stanley) **[VERIFIED via the pricing page, less granular]**
Source: https://us.etrade.com/what-we-offer/pricing-and-rates
- Options: **$0.65/contract**; **$0.50/contract** with 30+ trades/quarter
- **Exercise & assignment: $0**
- **Index Option Fee (IOF)** varies by underlying — e.g. **SPX $0.54**, **NDX $0.68** per contract
- Dime Buyback: $0 contract fee to close a short option priced ≤ $0.10
- "An options regulatory fee applies to all option orders; additional regulatory and exchange fees
  may apply"

### 6.5 Fidelity **[VERIFIED for the headline; index surcharge not published]**
Source: https://www.fidelity.com/trading/commissions-margin-rates
- $0 commission on US stock/ETF/option trades; **$0.65 per options contract** (non-professional)
- Exercise/assignment: **$0** — **[UNCERTAIN, not found on the fetched page; Fidelity has
  historically charged $0. Verify against the Fidelity commission schedule PDF before relying.]**
- Index option surcharge: Fidelity does not publish a per-symbol index fee table. **[UNCERTAIN]**

### 6.6 Schwab / thinkorswim **[NOT VERIFIED — schwab.com returned auth errors to every fetch]**
Publicly known and stable for several years, but **I could not confirm from a primary source in
this session**, so treat as **[UNCERTAIN]**:
- $0 commission + **$0.65 per options contract**
- **Exercise/assignment: $0** (Schwab removed the $25 fee when it merged the TD Ameritrade book)
- Index options carry an additional per-contract "index option fee" pass-through, symbol-dependent
- **Action item: re-verify from the "Charles Schwab Pricing Guide for Individual Investors" PDF.**

---

## 7. Exercise and assignment — summary

| Party | Fee |
|---|---|
| **OCC → clearing member** | **$1.00 per line item on the exercise notice** (not per contract) — OCC Schedule of Fees, as of Nov 2025 **[VERIFIED]** |
| Robinhood → customer | **$0** (no line in the fee schedule) |
| tastytrade → customer | **$5.00** per exercise/assignment **[VERIFIED]** |
| Interactive Brokers → customer | **$0** for US exercise/assignment **[VERIFIED]** |
| E*TRADE → customer | **$0** **[VERIFIED]** |
| Fidelity → customer | $0 **[UNCERTAIN]** |
| Schwab → customer | $0 **[UNCERTAIN]** |

**Hidden cost of assignment on equity options:** the resulting **stock** transaction is a covered
sale for Section 31 purposes at **full share notional**, and attracts the equity TAF
($0.000195/share, $9.79 cap). Assignment on 1 SPY call at $600: $60,000 × 0.0000206 = **$1.24**
Section 31 + 100 × $0.000195 = $0.02 TAF ≈ **$1.26**, which is ~14x the entire fee stack of trading
the option itself. **Cash-settled index options (SPX/XSP/NDX/RUT/VIX) avoid this entirely.**

---

## 8. Worked examples

### Assumptions
1. Retail, non-professional, self-directed cash/margin account. Options level 3 (spreads).
2. SPY option premium **$2.00** ⇒ $200 principal per contract.
3. XSP premium $2.00; SPX premium $20.00 (≥ $1.00 tier ⇒ Cboe customer rate $0.45).
4. Round trip = open + close, so 1 contract = **2 contract-sides**; a 2-leg vertical = **4 sides**;
   a 4-leg iron condor = **8 sides**.
5. Per-order rounding applied as each broker documents it. Robinhood rounds Section 31 **up** to
   $0.01 and rounds TAF/CAT **down to $0** when under a penny — so tiny orders pay $0.01 SEC and
   $0.00 TAF.
6. IBKR = **Pro, tiered, ≤10,000 contracts/month, premium ≥ $0.10 ⇒ $0.65/contract, $1.00 minimum
   per order, applied per leg of a combo.**
7. **Exchange transaction fees on SPY are excluded** — they are maker/taker and can be a rebate or
   a charge (roughly −$0.30 to +$0.50 per side depending on venue and add/remove). Robinhood does
   not pass them through at all (PFOF model); IBKR Pro does. This is the largest source of
   uncertainty in the IBKR numbers.
8. Slippage/spread is **not** included in any figure below.

### (a) 1 SPY contract, round trip

| | Robinhood | tastytrade | IBKR Pro |
|---|---|---|---|
| Commission | $0.00 | $1.00 open + $0.00 close | $1.00 + $1.00 (order minimum binds) |
| Clearing / OCC | $0.04 × 2 = $0.08 (combined w/ ORF) | $0.10 × 2 = $0.20 | $0.025 × 2 = $0.05 |
| ORF | *(in the $0.08)* | $0.02 × 2 = $0.04 | ~$0.012 × 2 = $0.024 |
| CAT | $0.0006 → $0.00 | — | $0.0003 × 2 = $0.0006 |
| FINRA TAF (1 sell) | $0.00329 → $0.00 billed | $0.00329 | $0.00329 |
| SEC 31 (1 sell, $200) | $0.0041 → **$0.01** | $0.0041 | $0.0041 |
| **Total** | **≈ $0.09** | **≈ $1.25** | **≈ $2.08** + exchange fees |

### (b) 1-lot SPY vertical spread (2 legs each way = 4 contract-sides)

| | Robinhood | tastytrade | IBKR Pro |
|---|---|---|---|
| Commission | $0.00 | $1.00 × 2 legs = $2.00 (open only) | $1.00 × 2 legs × 2 sides = **$4.00** |
| Clearing/OCC + ORF | $0.04 × 4 = **$0.16** | ($0.10 + $0.02) × 4 = $0.48 | ($0.025 + $0.012) × 4 = $0.148 |
| TAF (2 sell-sides) | $0.0066 → $0.01 billed | $0.0066 | $0.0066 |
| SEC 31 (2 sell-sides) | ~$0.006 → **$0.02** (rounds up per order) | $0.006 | $0.006 |
| CAT | ~$0.001 → $0.00 | — | $0.0012 |
| **Total** | **≈ $0.19** | **≈ $2.49** | **≈ $4.16** + exchange fees |

### (c) 1 XSP contract, round trip

| | Robinhood | tastytrade | IBKR Pro |
|---|---|---|---|
| Commission / index contract fee | $0.50 × 2 = **$1.00** (Gold: $0.35 × 2 = $0.70) | $1.00 open + $0 close | $1.00 + $1.00 (minimum) |
| Broker clearing | — | $0.10 × 2 = $0.20 | OCC $0.025 × 2 = $0.05 |
| ORF | $0.04 × 2 = $0.08 | $0.02 × 2 = $0.04 | Cboe $0.01248 × 2 = $0.025 |
| Exchange (Cboe) index fee | "exchange fees" — unpublished **[UNCERTAIN]** | XSP $0.00 (< 10 contracts/leg) | Cboe customer XSP < 10 contracts = **$(0.30) rebate** per side ⇒ −$0.60 if passed through **[UNCERTAIN]** |
| TAF + SEC 31 | ~$0.01 | ~$0.01 | ~$0.01 |
| **Total** | **≈ $1.09** non-Gold / **$0.79** Gold, + unknown exchange fee | **≈ $1.25** | **≈ $2.08**, or ≈ $1.49 if the Cboe small-order rebate is passed through |

### (d) 1 SPX contract, round trip

| | Robinhood | tastytrade | IBKR Pro |
|---|---|---|---|
| Commission / index contract fee | $0.50 × 2 = $1.00 (Gold $0.70) | $1.00 open + $0 close | $1.00 + $1.00 (minimum) |
| Broker clearing | — | $0.10 × 2 = $0.20 | OCC $0.025 × 2 = $0.05 |
| ORF | $0.04 × 2 = $0.08 | $0.02 × 2 = $0.04 | Cboe $0.01248 × 2 = $0.025 |
| Exchange index fee | "exchange fees" unpublished; budget Cboe customer $0.45 × 2 = $0.90 **[UNCERTAIN]** | SPX $0.60 × 2 = **$1.20** | Cboe customer $0.45 × 2 = $0.90 |
| TAF + SEC 31 (premium $20 ⇒ $2,000 sale) | $0.0033 + $0.0412 → ~$0.05 | ~$0.045 | ~$0.045 |
| **Total** | **≈ $1.13** billed + up to ~$0.90 exchange = **≈ $2.03** | **≈ $2.49** | **≈ $3.02** |

Note SPX notional is 10x XSP, so per dollar of exposure SPX is by far the cheapest of the three
retail index vehicles, and it avoids the equity-assignment Section 31 hit entirely.

### (e) **The condor question: 1-lot SPY iron condor, opened and closed (8 contract-sides)**

Short legs assumed ~$1.20 each, long legs ~$0.35 each; net credit $40–$80.

| | Robinhood | tastytrade | IBKR Pro |
|---|---|---|---|
| Commission | **$0.00** | $1.00 × 4 legs = **$4.00** (open only; close is free) | $1.00 min × 4 legs × 2 sides = **$8.00** |
| Broker clearing / OCC | $0.04 × 8 = **$0.32** (incl. ORF) | $0.10 × 8 = $0.80 | $0.025 × 8 = $0.20 |
| ORF | *(included above)* | $0.02 × 8 = $0.16 | ~$0.012 × 8 = $0.10 |
| CAT | $0.0024 → $0.00 | — | $0.0024 |
| FINRA TAF (4 sell-sides) | $0.0132 → **$0.02** billed | $0.0132 | $0.0132 |
| SEC 31 (4 sell-sides) | $0.0063 → **$0.02** (rounds up per order) | $0.0063 | $0.0063 |
| **TOTAL per condor round trip** | **≈ $0.36** | **≈ $4.98** | **≈ $8.32** + exchange fees |
| **As % of a $60 credit** | **0.6%** | **8.3%** | **13.9%** |
| **As % of a $40 credit** | **0.9%** | **12.5%** | **20.8%** |

**If the condor expires worthless (open only, 4 contract-sides, no closing trade):**
- Robinhood: **≈ $0.18**
- tastytrade: ≈ $4.42 ($4.00 commission + $0.40 clearing + ... — note tastytrade's $0 close means
  letting it expire saves only the clearing/ORF, ~$0.50)
- IBKR Pro: ≈ $4.16

**Robinhood charges nothing when a position expires worthless.** Expiration is not a transaction:
no contract fee, no ORF/OCC charge, no TAF, no Section 31. Same at every broker surveyed — the only
expiration-related fees anywhere in the stack are exercise/assignment fees (§7), which apply to
in-the-money contracts, not worthless ones.

---

## 9. What this means for the SPY-condor strategy

1. **At Robinhood, the regulatory fee stack is economically irrelevant to a defined-risk SPY
   condor: ~$0.36 per round trip on a $40–$80 credit, under 1%.** Even at 250 condors/year that is
   $90/year on a $2,000–$5,000 account. It does not change the trade's viability.
2. **At tastytrade or IBKR it absolutely does.** $5–$8 per condor against a $40–$80 credit is
   8–21% of gross premium, which will convert a marginally-positive edge into a loser. IBKR's
   per-leg $1.00 order minimum is the specific culprit — it punishes 1-lots brutally. Trading
   5-lots instead of 1-lots at IBKR drops the per-condor cost from $8.32 to about $10.60 total,
   i.e. from $8.32/condor to $2.12/condor.
3. **The real cost is slippage, and no fee schedule captures it.** Eight SPY option legs crossed at
   $0.01–$0.02 wide is $8–$16 per condor — 20–45x the Robinhood fee stack, and 10–40% of the
   credit. Any backtest that ignores fees but also ignores the spread is wrong by an order of
   magnitude more on the spread side.
4. **Section 31 was $0.00/million from May 14, 2025 through April 3, 2026** and is $20.60/million
   now. If a cost model was fit on 2025 fills it silently omits it — though at option-premium
   scale, this is pennies.
5. **Avoid equity-option assignment.** Assignment converts the trade into a full-notional stock sale
   that pays Section 31 on ~$60,000, not on $200. Cash-settled index options (XSP is the natural
   1/10-size SPY substitute) sidestep it, and XSP additionally earns a Cboe customer **rebate** on
   sub-10-contract orders — though only IBKR Pro plausibly passes that through.
6. **Watch the Professional Customer cliff.** Averaging more than **390 orders per day** in listed
   options over a calendar month reclassifies you as a Professional at every exchange. Cboe's
   footnote 14 then makes you liable for the $0.20 SPX surcharge and $0.10 index license surcharge
   that Priority Customers escape, and it changes your queue priority. An automated condor engine
   can hit 390 orders/day faster than you'd think once you count cancels/replaces on 4 legs.

---

## 10. Verification status

**Read directly from a primary document:** OCC schedule of fees and both 2025 fee filings; all
ORF rates except Nasdaq BX; SEC FY2026 Section 31 order and FINRA notices; FINRA TAF multi-year
schedule; Cboe Fees Schedule dated Aug 3, 2026; Robinhood's own fee-schedule PDF; tastytrade's own
commissions-and-fees PDF; IBKR's live options pricing page.

**Could not verify in this session:** Schwab/thinkorswim's entire schedule (schwab.com refused
every fetch), Fidelity's index-option surcharge and exercise/assignment fees, Nasdaq BX's post-July-
2026 ORF, and Robinhood's unpublished "exchange fees" for index options. The Robinhood SPX/XSP
totals in §8(c)/(d) are the least reliable figures in this document — confirm against a live trade
confirmation before using them.
