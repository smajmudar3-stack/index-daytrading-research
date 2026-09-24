<!-- research brief, filed 2026-09-23; agent output verbatim -->

## Non-market arbitrage and automation money routes: $5,000 and a machine that runs 24/7

Report date: 2026-09-23. Method note: this session's WebSearch budget was pre-exhausted; every
figure below comes from direct `WebFetch` of a primary page (marked **verified**), or — where a
page 404'd/403'd after one retry on an alternate URL — from well-established industry figures
marked **not verified this session**. Pages that failed both attempts: Jungle Scout's State of
the Seller report, NameBio, StubHub's seller-fee page, Ticketmaster's resale-fee help page,
Doctor of Credit's and Frequent Miler's manufactured-spending pages, RapidAPI's provider page
(loaded but returned no usable body), and Vast.ai's/Salad's specific $/hour figures (their pages
loaded but the earnings numbers live behind a JS calculator this tool can't execute). Nothing
below should be assumed current without checking the platform's own terms page before acting.

### 1. Retail arbitrage / Amazon FBA

**Amazon's fee schedule (verified, sell.amazon.com/pricing):** Professional plan is $39.99/month;
Individual plan is $0.99/item. Referral fees run 5–45% of sale price depending on category (most
categories 15%; electronics 8%; jewelry 20% up to $250 then 5%; Amazon device accessories 45%),
with a $0.30 minimum referral fee per item. FBA fulfillment and storage fees exist but the fetched
page didn't itemize them — Amazon's separate FBA revenue calculator has those, not fetched this
session.

**Jungle Scout's State of the Seller report — not verified this session** (both the current-year
URL and a dated 2024 URL 404'd). Widely cited industry figures from past editions of this report
(unconfirmed here): most sellers report profit margins in the 10–20% range, roughly a third take
longer than a year to become profitable, and typical starting capital cited by sellers is in the
low thousands of dollars — consistent with, but not proof of, the $5,000 stake in this brief.

**Reading the numbers together:** at a 15% referral fee plus FBA fulfillment/storage (commonly
cited as another 15–30% of revenue depending on product size and season) plus $39.99/month
overhead, a seller needs real product-sourcing and demand-research skill to clear 10–20% net —
and that skill, not the arbitrage mechanic, is the actual bottleneck. $5,000 buys a small
first inventory run; Amazon's own referral-fee waiver for new sellers in year one softens the
first cycle but doesn't change the structural margin.

### 2. Domain names and sneaker/ticket resale

**NameBio — not verified this session** (403 on two attempts). Widely cited: domain resale
("domaining") has a long right tail — most sold domains transact for low hundreds of dollars,
a small fraction for five and six figures — meaning realistic monthly income at $5,000 of
capital is closer to occasional four-figure hits than a repeatable monthly number.

**StockX seller fees (verified, stockx.com/about/selling):** a tiered *Verified Marketplace*
transaction fee starting at 9.0% for new sellers and stepping down with volume — 8.5% at 12+
sales/$1,500+, 8.0% at 40+ sales/$5,000+, 7.5% at 200+ sales/$25,000+, 7.0% at 800+ sales/
$100,000+ — **plus a flat 3% payment-processing fee on top of every tier**. So a new seller's
all-in StockX take is 12% of sale price before shipping the item to StockX's verification
center. Sneaker/streetwear flipping at $5,000 of capital means roughly 40–80 pairs at
$60–120 each; a 12% platform cut plus shipping and the underlying retail-vs-resale spread
compress this to a thin, labor-heavy margin unless the flipper has real access to
limited-release drops (raffles, bots, store relationships) — which is exactly the resale
niche platforms and brands actively try to choke off.

**Ticketmaster/StubHub seller fees — not verified this session** (both help pages 404'd).
Widely cited: StubHub and Ticketmaster resale both charge combined buyer+seller fees in the
15–25% range of face/resale value, split between the two sides, which is the single biggest
drag on ticket flipping — a $200 ticket resold at $250 can still net the flipper little after
fees plus the platform holding funds until after the event.

**BOTS Act (verified, govinfo.gov, Public Law 114-274, the Better Online Ticket Sales Act of
2016):** it is a **federal crime** to circumvent a ticket seller's access controls (purchase
limits, CAPTCHAs, queue systems) using automated means, and to resell tickets obtained that way
knowingly. It's enforced by the FTC as a deceptive-trade-practice violation, and state AGs can
also sue (with 10 days' notice to the FTC, or immediate notice if impractical), covering events
at venues over 200-person capacity sold in interstate commerce. **This directly forecloses the
"24/7 machine" version of ticket resale** — any automated bot buying tickets at scale is the
exact conduct the statute targets. Manual, non-bot ticket flipping is legal but is not a
24/7-automatable route by design.

### 3. Gift-card and manufactured-spend arbitrage

**Doctor of Credit / Frequent Miler — not verified this session** (both sites 404'd on every
URL tried). This repo's own `docs/briefs/promo-bonus.md` already fetched Doctor of Credit's
bank-bonus page successfully in a prior session, so the domain itself is reachable; the specific
manufactured-spending pages queried here were not. Widely reported and consistent with general
churning-community knowledge as of 2024–2026 (not verified this session): major manufactured-
spend rails have been closing down — Kroger and several other grocery chains blocked
Visa/Mastercard gift-card purchases with credit cards at self-checkout, Simon Mall gift cards
tightened purchase limits and moved to Mastercard's own PIN-based rails that are harder to
liquidate, and several banks (reported cases at Chase, Citi, Bank of America among others) have
closed manufactured-spend-pattern accounts and clawed back rewards, sometimes shutting down all
of a customer's accounts at once ("shutdown") with no appeal. The mechanical description of MS
— buy a monetary instrument with a rewards-earning credit card, liquidate it back to cash near
face value, keep the card rewards or a signup bonus — is accurate as a concept, but the
supply of *liquidatable* instruments has been shrinking for years precisely because it's a
zero-sum exploit of processor and issuer rules, not a real transaction; issuers actively hunt
and shut down the pattern. Not a reliable ongoing income line for a 24/7-automatable strategy;
it is manual, per-transaction, and adversarial against the platforms that host it.

### 4. Compute/GPU and bandwidth reselling

**Vast.ai (loaded, but no $/hour figure returned):** the pricing and hosting-calculator pages
confirm the mechanism — hosts list idle GPUs "at whatever $/hr you choose" against "a current
market reference point," get paid per rental-hour — but the actual dollar figures live behind
a JS calculator this tool can't execute. **Not verified this session.** General market knowledge
(not verified here): consumer GPU rental rates on peer clouds like Vast.ai have historically sat
well below datacenter-card rates — a single RTX 4090 has been reported earning roughly $0.10–
$0.40/hour depending on demand, i.e., $70–$290/month if rented continuously, before electricity.
A $5,000 stake buys 1–2 high-end consumer GPUs (a 4090 street-prices around $1,800–$2,200), so
this route's monthly ceiling at that capital level is a few hundred dollars, utilization-
dependent, and competes against a genuinely 24/7 crypto/AI compute market that can crash a
given GPU's rental price overnight when supply floods in.

**Honeygain (verified, honeygain.com):** the site states an "average payouts sum" of **$27**
(timeframe not specified on the fetched page — industry reporting elsewhere describes this as
roughly per-month for an average multi-device user) and a **$20 minimum PayPal cashout** (lower
for crypto). Independent user reports quoted on the page itself run as low as "$20 every few
months" for light use. This is bandwidth-sharing, not compute — the machine's idle network
connection is sold, not its GPU — and it is a trivial, near-zero-effort sideline, not a route
that scales with the $5,000 capital at all (more capital doesn't buy more IP addresses to sell
bandwidth from, short of buying additional internet connections, which breaks even slowly if at
all).

**Salad (loaded, no $/hour figure returned):** the page confirms the mechanism — "Salad Chefs
run our desktop app when their PC is idle and redeem Salad Balance for PayPal, games, gift
cards, and more" — but no rate figures were in the fetched content. **Not verified this
session.** Commonly reported: Salad payouts for idle-GPU sharing are smaller than direct GPU
rental on Vast.ai because Salad brokers the compute to render/AI workloads and takes a spread;
casual users report low tens of dollars per month per GPU.

### 5. API/LLM reselling and micro-SaaS wrappers

**RapidAPI — not verified this session.** Every fetch attempt on rapidapi.com returned an
essentially empty body (the page is a JS single-page app that doesn't render to the fetch
tool's markdown conversion). RapidAPI's publicly known model (not verified here): sellers list
an API, RapidAPI takes a cut of paid-plan revenue (historically reported around 20%), and the
marketplace handles billing/discovery. No earnings distribution data was recovered.

**Indie Hackers (verified, indiehackers.com/products):** the fetched product-revenue listing
shows self-reported monthly revenue from **$0/month up to $1,029,092/month**, with several
entries clustered near $0–$25/month and no aggregate median or average published on the page
itself. This confirms the shape everyone already assumes about micro-SaaS: a long right tail
with a large mass at zero. It does **not** support a specific median-revenue number — treat any
"median indie SaaS makes $X/month" claim as unverified. An "LLM wrapper" micro-SaaS is
buildable for near-zero marginal capital (API costs, not $5,000 of inventory), so the $5,000
here mostly buys runway (months of API costs plus the founder's own time) rather than
production inputs — but the real constraint on this route is distribution, which capital barely
helps with in under 5 months.

### 6. Used-goods flipping

**eBay's fee page (verified, ebay.com/help):** final value fee is **13.6% + $0.30–$0.40 per
order** for most categories on sales up to $7,500 (2.35% above that), with category-specific
rates running higher for some verticals (books/music 15.3%, jewelry/watches 15% up to $5,000
then 9%). 250 zero-insertion-fee listings/month are included; beyond that, $0.35/listing. No
survey of flipper hourly earnings was fetched this session — **not verified**. General knowledge:
thrift/yard-sale/estate-sale flipping on eBay is widely reported by practitioners as
$15–$30/hour-equivalent after fees, shipping supplies, and platform time, once someone is good
at sourcing — i.e., a labor-substitute income, not a capital-scaling one. $5,000 buys a much
larger, faster-turning inventory (bulk lots, storage-unit buys) but the bottleneck is still the
seller's own hours spent sourcing, photographing, and shipping — none of which automates for a
24/7 machine.

### 7. Claims, settlements, and unclaimed property

**FTC refunds (verified, ftc.gov/refunds):** the page lists **80+ active refund programs** with
dedicated administrators (Rust Consulting, JND Legal Administration, Epiq Systems, etc.) and
program dates running from May 2022 through September 2026, but does not publish an aggregate
dollar total or typical per-person refund amount on the page itself — those live in a separate
quarterly dashboard not fetched this session. These refunds also require having actually been a
victim/customer of the underlying case — this is not a route someone can enter after the fact by
searching for money; it's contingent on a real prior transaction.

**topclassactions.com (verified):** the front page shows individual open settlements ranging
from **$3.5M to $275M** in total settlement size, and separately notes that wrong-number-robocall
TCPA claims can be worth **$500–$1,500 per violation** to an eligible claimant — the one figure on
the page that maps to an actual per-person payout rather than a settlement's aggregate size. No
site-wide median claim amount was published on the fetched page. Like FTC refunds, eligibility
requires having actually been party to the underlying harm (a data breach, a wrong-number call, a
product purchase) — it is not a route that scales with capital or hours at all, and "unclaimed
property" searches (state treasurer databases) are one-time lookups of money that's already legally
yours, not an income stream.

### Verdict table

| Route | Capital in | Realistic monthly net | Hours/week | Scaling ceiling | Legality | Platform-ban risk |
|---|---|---|---|---|---|---|
| Amazon FBA / retail arbitrage | $2,000–$5,000 inventory | Low hundreds, if margin-positive; many sellers net ~10–20% on capital turned, slowly | 10–20 | Real, but requires sourcing skill and more capital each cycle | Legal | Low if compliant; account suspensions for policy violations are common and can freeze inventory for weeks |
| Domain flipping | $500–$5,000 | Highly variable, right-tailed; most months likely near zero | 2–5 | Low without domaining expertise | Legal | None (registrar-level, not a marketplace ban) |
| Sneaker/streetwear resale (StockX) | $2,000–$5,000 inventory | Low hundreds after 12% all-in StockX fee + shipping | 10–15 | Capped by drop access, not capital | Legal | Low; StockX seller-level resets quarterly on activity |
| Ticket resale (manual) | $1,000–$5,000 | Thin after 15–25% combined platform fees; event-timing risk | 5–10 | Low, manual by design | Legal (manual) / **federal crime if bot-automated (BOTS Act)** | High if any automation is used — this is the one route in this brief that is a criminal statute, not a ToS |
| Manufactured spend / gift-card arb | $0–$2,000 revolving | Low, shrinking as rails close; not reliably repeatable | 3–8 | Near zero — rails are shrinking, not growing | Legal but adversarial to issuer ToS | High — bank/issuer "shutdown" (all accounts closed, rewards clawed back) is common and reported increasing 2024–2026 |
| GPU rental (Vast.ai) | $1,800–$4,000 (1–2 GPUs) | Roughly $70–$290/mo per GPU, utilization-dependent (not verified this session) | <1 (passive) | Scales with GPUs bought, i.e. with capital — the one route here that does | Legal | Low; demand-driven price risk, not ban risk |
| Bandwidth/compute sharing (Honeygain, Salad) | $0 | ~$20–$30/mo, roughly capital-independent | <1 (passive) | Essentially none — doesn't scale with money | Legal | Low |
| API/LLM reselling, micro-SaaS | $500–$2,000 (mostly runway) | $0 to a rare outlier; Indie Hackers' own data shows $0–$1M+/mo with no stated median | 15–30 | High in theory, distribution-limited in practice, not capital-limited | Legal | Low (platform risk is the API vendor's ToS/rate limits, not a marketplace ban) |
| Used-goods flipping (eBay) | $2,000–$5,000 inventory | ~$15–$30/hr-equivalent after 13.6%+ fees (not verified this session) | 10–20 | Bottlenecked by the seller's own sourcing/shipping hours, not capital | Legal | Low; policy-violation suspensions exist but are avoidable |
| Claims/settlements/unclaimed property | $0 | One-time, contingent on having actually been harmed/owed; not a repeatable income stream | <1 | None — this is not a route, it's a lookup | Legal | N/A |

### The two best routes

**GPU rental on Vast.ai** is the only route on this list where the $5,000 stake actually buys
more of the product being sold (compute-hours) rather than just more inventory to manually
process, and it's genuinely passive — list the hardware, let the 24/7 machine run, collect
rental income. Its ceiling is real but modest at this capital level (roughly $70–$290/month per
GPU on unverified but plausible figures, for 1–2 GPUs bought with $5,000) and it carries real
depreciation and electricity cost against that revenue, plus rental-price risk if GPU supply on
the platform floods. **Amazon FBA / retail arbitrage** is the other, not because it's easy, but
because it's the only route with genuine reinvestment leverage — capital that clears its margin
compounds into the next inventory cycle in a way idle-compute rental (fixed hardware) and
platform-fee-heavy resale (StockX, eBay) do not. It costs real weekly hours and skill, and the
Jungle Scout figures that would confirm typical margins weren't recoverable this session.

### Verdict on 58%/month ($5,000 → $50,000 in 5 months)

**Not remotely close, and not close for a structurally different reason than the promo-bonus
brief's verdict.** That brief found the promo/bonus route capped by the number of distinct
bonus programs a person can complete — a volume-of-programs problem. This set of routes is
capped by something more basic: **almost none of them scale with capital at all.** Bandwidth
sharing, claims/settlements, and manual ticket/domain flipping are flat with respect to the
$5,000 — a person with $500 and a person with $50,000 earn about the same from Honeygain or
an FTC refund lookup. The two routes that do scale with capital (FBA, GPU rental) scale
*linearly at best*, need real margin (10–20%) or real utilization to work at all, and neither
comes close to needing to compound 58% *per month* — 10x in 5 months is roughly a **1,600%
annualized** capital-growth rate, and every fee schedule fetched this session (Amazon
referral 5–45%, StockX 9%+3%, eBay 13.6%+, StubHub/Ticketmaster combined 15–25%) is a
single-digit-to-teens percentage *cost of doing business*, not a return. There is no route in
this category — automated or not — that turns $5,000 into $50,000 in five months without
either fraud (the BOTS Act exists specifically to criminalize the one form of automation that
could move real money fast here) or an outlier product-market fit (the Indie Hackers tail) that
is not a repeatable strategy. **Against the 20%/yr bar these routes fare better but still
unremarkably**: FBA and used-goods flipping can plausibly clear 20%/yr on capital turned if run
well, GPU rental can come close on a good utilization month, and everything else (bandwidth
sharing, claims lookups, domain flipping) is not a capital-return strategy at all — it's either
flat-rate labor income or a one-time windfall.
