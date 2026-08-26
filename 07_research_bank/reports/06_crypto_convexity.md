# 06 — Crypto convexity: access, and a real correction to our far-OTM null

**Status:** complete · **Evidence quality:** high — primary sources (CFTC staff
letter, Deribit rulebook, live order books, peer-reviewed arXiv) · **Relevance:**
the first finding that legitimately qualifies our own −90% far-OTM result

---

## The correction that matters

Our measured null — far-OTM buying returns −90% to −48%, cheaper is worse — was
established on **equity** options. Crypto is structurally different for one
reason:

> **High IV ≠ negative expectancy when the underlying carries a 66%/yr risk
> premium.**

**Almeida, Grith, Miftachov & Wang** ([arXiv:2410.15195v2](https://arxiv.org/abs/2410.15195)),
**7.8 million Deribit trades, 2017–2022**:

> "The increasing BP(r) for positive returns indicates that **OTM calls are
> profitable on average**… The hump is above one, indicating that **ATM options
> are expensive**, leading to negative returns for both ATM put and call options."

And the caveat that kills the lottery-ticket version:

> "**The BP attributable to returns below −60% and above +60% is relatively
> small.** These results suggest that **large positive returns, but not extreme
> returns**, are the main source of Bitcoin risk premia."

### Where the premium actually lives

| monthly return band | share of Bitcoin premium |
|---|---|
| **[+20%, +60%]** | **38.7%** (rising to **52.3%** in low-vol regimes) |
| beyond ±60% | small |

Compare the S&P 500, where **~80% of the premium comes from months below −10%**.
Crypto's premium is on the **upside**; equity's is compensation for the downside.

| | BTC | SPX |
|---|---|---|
| variance risk premium | **+14%** (RN 0.72 vs realized 0.58) | ~2% |
| asset risk premium | **~66% p.a.** | ~5% |

**Practical consequence: the right strike is 25Δ–10Δ calls at 1–3 month tenor —
NOT the 2–5Δ far wing.** The deep tail sits in the >+60% band where the premium
contribution is small, and where the live surface charges **98–136 vol against
41 ATM**. Buying it is paying triple the ATM vol for the part of the
distribution that carries almost none of the premium.

This is the same shape as our own equity finding (+26.1% at 16–30 delta vs −90%
at the tail) — arrived at independently, on a different asset class, with a
stated economic mechanism. **Two independent confirmations that the money is at
moderate delta, not the far wing.**

---

## Access: a US individual still cannot trade Deribit

**Verified in Deribit's own Exchange Rulebook (Deribit FZE, updated 2026-08-12),
Appendix F:** the United States, US Virgin Islands, Guam and Puerto Rico are
Restricted Jurisdictions. The rulebook contains **zero references to "Coinbase",
"FCM", or "Part 30"** — no membership carve-out exists. Domicile is Dubai (VARA
licence L-2994).

**But there is now an institutional pathway.** CFTC Staff Letter 26-17
(29 May 2026) lets **Coinbase Financial Markets** (registered FCM) offer Deribit
Futures, **Options on Futures**, and Perpetuals to US customers via Coinbase
Bermuda as foreign broker under Reg. 30.4(a), with customers in Reg. 30.7
accounts.

Note the product is purpose-built: *"physically settled, European-style options
on underlying Deribit Futures"* — **not** Deribit's standard cash-settled inverse
options. Coinbase (29 May 2026): *"Institutional clients can begin onboarding
today… Broader client access, including **retail, is coming soon**."* Q2'26
earnings deck still lists US retail under "What's Next."

**For a $5k US retail account today: IBIT/ETHA listed options are the only
route.**

## The onshore product is the expensive leg

Same expiry, clean comparison:

| | 25 Sep 2026 ATM IV |
|---|---|
| Deribit BTC (30 DTE) | **41.2%** |
| **IBIT (31 DTE, K45)** | **43.7%** |

**IBIT trades ~2.5 vol points above Deribit for identical exposure.** The honest
answer to "do the ETF options show mispricing" is yes — in the wrong direction.

Full Deribit BTC 25SEP26 smile — note it is a **smile, not an equity smirk**:
both wings lift.

| K/S | 0.63 | 0.88 | **1.00** | 1.14 | 1.52 | 2.02 | 2.53 | 3.79 |
|---|---|---|---|---|---|---|---|---|
| IV | 73.7 | 43.1 | **40.8** | 45.0 | 63.8 | 82.5 | 98.2 | 136.3 |

The call-rich/put-rich crossover sits near **5 delta**: at 10Δ the call is richer
(45.0 vs 43.1), at ~1Δ the put is richer. So "crypto has positive call skew" is a
**25Δ–10Δ statement that inverts in the deep tail**.

## Skew is regime-dependent, not structural

The agent explicitly walked back its own earlier framing. Block Scholes on
Deribit Insights, **days before** the August 2026 breakout — Week 34
(19 Aug 2026): *"as we've seen for most of the year, skew is yet to turn positive
meaningfully"*; Week 33: *"put options continue to trade at premiums"*; Week 30:
the *"bearish put-premium that has mostly dominated the first half of this year."*
BTC 7-day ATM IV had fallen to **23%**, lowest since Sept 2023.

Current term structure is front-end **call**-rich (25Δ RR +3.17 at 1 DTE) and
long-dated **put**-rich (−0.98 at 212 DTE) — **the inverse of the 2025 pattern**.

Longer arc: ATH **$124,786 (4 Oct 2025)** → $66K (Mar'26) → $60.1K (Jul'26) →
+24% in five sessions 19–24 Aug 2026 ($64.3K → $79.7K), DVOL 35.5 → 43.1.

**Any measurement taken today is mid-squeeze.** The agent flagged that its own
earlier readings were stale and its live ones elevated for that reason.

---

## What to test when the bank closes

1. **25Δ–10Δ IBIT calls, 1–3 month tenor.** This is where the documented +38.7%
   premium band lives, spreads are 2–3%, and it avoids both the expensive ATM
   body (pricing kernel > 1) and the 98–136 vol deep tail.
2. **The 2.5-vol IBIT-vs-Deribit basis** — is it persistent or a snapshot? If
   persistent, it is a structural cost of onshore access that must be netted from
   any IBIT convexity trade.
3. **Regime dependence of skew** — the 25Δ RR flipped sign between 2025 and 2026.
   Any strategy conditioned on skew must be tested across both.

## Still unverified

Dec-2024 MSTX/MSTU leverage cut · SOL/XRP ETF options · CME micro specs · and
critically, the **commercial terms of the new CFM/Deribit product** (fees,
minimums, listed strikes, liquidity) — Letter 26-17 describes the structure but
publishes no contract specs.
