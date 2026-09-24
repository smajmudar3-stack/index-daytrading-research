<!-- research brief, filed 2026-09-23; agent output verbatim; verdicts copied to 02_findings/online_methods.md -->

Several secondary sources blocked (Blackjack Apprenticeship 403, Stake.com 403 bot-check, two casino-app
bonus-terms pages 403/404, PokerStars/GGPoker policy pages redirected into blocked domains, DuckDuckGo/Bing
search proxies returned CAPTCHA or mismatched cached pages). Where a claim rests on general industry
knowledge rather than a page I actually fetched this session, it is marked **not verified**. Primary numbers
below (blackjack house edge, card-counting edge, IRS Topic 419, the 90% loss-deduction change, US online
poker legality) all came from pages fetched directly.

# Online advantage gambling as a route from $5,000 to $50,000 in 5 months (US individual, Sept 2026)

## 1. Card counting, live-dealer/online blackjack

Wizard of Odds' rule-by-rule house-edge table (baseline 8-deck, dealer stands soft 17, DAS): single deck
+0.48%, 6:5 blackjack payout −1.39%, dealer hits soft 17 −0.22%, late surrender +0.08%
([wizardofodds.com/games/blackjack/basics](https://wizardofodds.com/games/blackjack/basics/)). A well-dealt
shoe with full rules runs a house edge of roughly 0.3–0.5%; counting flips that. Wizard of Odds' own
introduction states a realistic counting edge of **0.5%–1.5%**
([wizardofodds.com/games/blackjack/card-counting/introduction](https://wizardofodds.com/games/blackjack/card-counting/introduction/)),
and Wikipedia's Card Counting entry gives the same order of magnitude — "approximately 1% over the casino"
— with a worked example: at a $100 average bet and 50 hands/hour, a 1% edge nets **$50/hour**, with high
variance requiring hundreds of hours to realize it
([en.wikipedia.org/wiki/Card_counting](https://en.wikipedia.org/wiki/Card_counting)).

That $50/hour figure caps out fast: doubling it needs doubling the average bet, and "more than doubling
your last bet is a fast way to arouse attention from the dealer and pit boss" (Wizard of Odds). None of
this transfers online. Wizard of Odds' 2026 online-blackjack survey compares house edges across software
providers (as low as 0.01–0.31% for specific rule sets) but contains **no discussion of counting
feasibility** — because it doesn't apply. Wikipedia's Card Counting page is explicit: "In most online
casinos the deck is shuffled at the start of each new round, ensuring the house always has the advantage,"
and continuous shuffle machines in live-dealer rooms "essentially force minimal penetration," eliminating
the counter's edge entirely. So the one blackjack method with a real, documented positive edge (0.5–1.5%,
~$50/hr on modest stakes) is a land-casino method that online and live-dealer platforms are specifically
engineered to prevent. Land casinos also ban or backroom known counters — legal everywhere except Atlantic
City, per a 1982 court ruling (Wikipedia). Blackjack Apprenticeship's page on realistic counter income
returned HTTP 403 every attempt this session; its widely cited public claim — that a disciplined counter can
clear roughly $50,000–$100,000/year on a $30-50k team bankroll after years of training and travel — is
**not verified** here.

## 2. Poker: skill edge, bots, and solver-assisted play

**Legality.** Regulated real-money online poker exists in six US states sharing one interstate pool:
Nevada (2013), Delaware (2013), New Jersey (2018), Michigan (2022), West Virginia (Nov 2023), and
Pennsylvania (joined the compact 28 Apr 2025) — a US individual outside those states has no legal regulated
online-poker route
([en.wikipedia.org/wiki/Online_poker_in_the_United_States](https://en.wikipedia.org/wiki/Online_poker_in_the_United_States)).

**Solvers and bots.** This session could not reach a primary PokerStars/GGPoker RTA (real-time-assistance)
policy page — `pokerstars.com/.../security/` 301-redirected to `pokerstarsnj.com`, then to
`poker.fanduel.com` (PokerStars' US operation has folded into FanDuel), which 403'd; GGPoker's `/rta-policy/`
404'd. Verified instead via Wikipedia's Online Poker article: its "integrity and fairness" section documents
a **2025 GGPoker enforcement action** against a screen-sharing/account-ghosting ring, i.e. major sites
actively police collusion and RTA use with bans and seizures. The specifics of current detection methods and
confiscated-funds policy are **not verified** by a primary source this session, though it is public record
that PokerStars, GGPoker and other major networks prohibit solver use during live play and have banned and
clawed back winnings from RTA users in publicized cases. Solvers used for *study* (not live play) are
universal among winning players and not banned — that edge is shared by the whole professional pool, so it
raises the bar to break even rather than creating one for a new entrant.

**Realistic edge.** Public win-rate data from regulated US sites was not located this session — **not
verified**. General knowledge: a strong online cash-game grinder nets roughly 3–6 big blinds per 100 hands
after rake at low-to-mid stakes, a modest hourly wage once rakeback is included. The binding constraints
mirror sports value-betting in this repo's `sports-betting.md`: a thin legal footprint (6 states), and any
automation or scripting breaches every site's terms.

## 3. "Provably fair" offshore crypto casinos (Stake.com and similar)

`stake.com/provably-fair` returned a bot-check wall (403) on every attempt, including a text-proxy retry, so
nothing here is verified against Stake's own page. What is publicly known: "provably fair" is a
cryptographic scheme letting a player verify a round wasn't altered *after the fact* — it proves the RNG
wasn't tampered with, it does not change the built-in house edge, which on this class of site runs roughly
1% (some dice/crash games) up to 4–15% on slots, same as any other online casino. Stake and equivalent
unlicensed offshore platforms **do not accept US customers and are not legal for US persons** — standard
industry knowledge, not verified from a primary compliance page this session. Even best-case, "provably
fair" changes nothing about the arithmetic: a negative-edge game played at volume converges to the house
edge.

## 4. Casino welcome bonuses ("bonus hunting")

BetMGM's and DraftKings' bonus-terms pages both blocked this session (403/404). The general mechanic — also
used in this repo's `sports-betting.md`, which found the same $2-4k one-time ceiling for matched sports
betting — is a playthrough/wagering requirement: typically 1x on "bonus bets" (stake not returned) up to
15-30x on deposit-match bonuses at negative-EV games, calibrated to return the house edge over the required
volume. **Not verified against a live terms page this session**, but the structure is uncontested public
knowledge. A new player can extract roughly $1,000-4,000 in one-time value per platform; it is a one-off,
not a repeatable income stream, and accounts get flagged for "bonus abuse" after 1-2 cycles.

## 5. Tax treatment (2026)

IRS Topic 419 (verified,
[irs.gov/taxtopics/tc419](https://www.irs.gov/taxtopics/tc419)): all gambling winnings are fully taxable and
reportable on Schedule 1 regardless of W-2G issuance; losses are deductible only if you itemize on Schedule A,
and only up to the amount of reported winnings.

Layered on top from 1 Jan 2026: the One Big Beautiful Bill Act caps deductible gambling losses at **90%** of
losses, down from 100% (verified,
[taxfoundation.org/blog/gambling-losses-tax-big-beautiful-bill](https://taxfoundation.org/blog/gambling-losses-tax-big-beautiful-bill/)).
Tax Foundation's own worked examples: a gambler who wagers $1,000,000 and wins back exactly $1,000,000 (net
zero) now owes **$37,000** in tax; a gambler who nets $50,000 in real profit can owe $55,500 — a negative
take-home outcome; poker pro Daniel Negreanu's tax bill on $181,097 of net winnings rose from $67,006 to
$115,000. This is fatal specifically to high-turnover strategies: card counting, poker grinding, and bonus
cycling all involve wagering many multiples of net profit, so every dollar of gross loss on the way to a net
win is now taxed as if 10% of it were phantom income.

## Verdict

| Method | Real edge | Realistic $/hr or $/yr | Capital needed | Ban/detection risk | Legality (US) | 58%/mo | 20%/yr |
|---|---|---|---|---|---|---|---|
| Card counting, land blackjack | 0.5–1.5% (verified, Wizard of Odds/Wikipedia) | ~$50/hr at $100 avg bet, 50 hands/hr | $5-10k bankroll for variance control | High — backrooming/bans everywhere but Atlantic City | Legal to count, casinos can refuse service | No | Maybe, with a team, over years |
| Card counting, online/live-dealer | ~0% (engineered out via CSM/reshuffle-per-round, verified) | $0 | n/a | n/a — the edge doesn't exist | Legal | No | No |
| Poker, regulated US sites | Small, skill-dependent, not verified | Low-to-modest, not verified | Bankroll mgmt, ~20-50 buy-ins | Bans for RTA/bots/collusion (2025 GGPoker case, verified) | Legal only in NV/DE/NJ/MI/WV/PA (verified) | No | Only for the pre-existing elite |
| Offshore "provably fair" crypto casino | Negative (1-15% house edge, not verified against primary source) | Negative in expectation | n/a | Account/fund seizure risk; not licensed for US | Not legal for US persons | No | No |
| Casino bonus hunting | One-time positive, small | $1-4k one-time per platform | Low | Fast — flagged after 1-2 cycles | Legal | No | No (not recurring) |

None of this clears 58%/month, or even 20%/year as a scalable, repeatable plan. The one method with a
real, measured positive edge — card counting — is capped at roughly $50/hour by table limits and heat, does
not exist in any online or live-dealer form (verified: online platforms specifically reshuffle every round
or use continuous shufflers to prevent it), and the 2026 tax change now taxes the gross churn of exactly
this kind of high-turnover play, not the net profit. Poker's legal footprint in the US is six states, and
the OBBBA's 90% loss cap already produced a real-world case (Negreanu) of a professional's effective tax
rate spiking toward 65% of net winnings. Advantage gambling is a real but small, capital- and time-capped
side income at best, not a $5,000→$50,000-in-5-months route.
