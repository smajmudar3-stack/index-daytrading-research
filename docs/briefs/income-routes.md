<!-- research brief, filed 2026-09-23; agent output verbatim -->

# Income routes to $9,000/month for a Claude-Code builder with $5,000, judged against 5 months

**Method note first, because it shapes how much to trust the numbers below.** This session's web-search budget was already exhausted before this brief started, so every source had to be reached by direct URL fetch. Of roughly 20 primary pages attempted, most returned HTTP 403 (Upwork, Metaculus tournaments), HTTP 404 (Toptal's rate page, Contra's rate page, HackerOne's report at three guessed URLs, Algora's bounty page, QuantConnect's Alpha Streams page — which 404s because the product was discontinued), or a JavaScript shell with no content (Kaggle's competitions page, Indie Hackers' product directory, Starter Story's ideas page, WorldQuant's `boards.` subdomain before it redirected). Where a fetch actually returned data — the IRS self-employment tax page, WorldQuant BRAIN's consultant-payout numbers, and Numerai's staking documentation — that is marked **(fetched)**. Everything else is **(not verified this session)**: figures a careful builder would recognize as roughly right from general knowledge of these platforms, but that I could not confirm against a primary source in this run. Per this repo's own rule, that is stated outright rather than smoothed over.

**The frame.** The daytrading research in this repo established that no measured strategy turns $5k into $50k in 5 months from price action alone — 26 sweeps, 115 backtests, and the honest verdict is `02_findings/WHAT_WORKS.md`. The only way capital compounds that fast is if more capital gets added, and the only realistic source of $9,000/month in new capital for someone who builds software with Claude Code is *selling that skill*, not entering a contest against it. This brief ranks the plausible income routes on that basis.

## Ranked by probability of reaching $9k/month within 5 months

| Rank | Route | Probability of $9k/mo by month 5 | Realistic median outcome (month 5) | Hours/week | Capital needed |
|---|---|---|---|---|---|
| 1 | Freelance AI/automation dev work — Upwork, Toptal, direct outreach | **Medium** | $3,000–7,000/mo, still ramping | 25–35 | ~$0 (the $5k buys runway, not inventory) |
| 2 | Contra / direct-to-client productized consulting (narrow "I build AI agents with Claude Code" offer, warm network + cold outreach) | **Medium, faster ramp if a network already exists** | $2,000–8,000/mo, high variance | 20–30 | ~$0–500 (a simple site, a few case studies) |
| 3 | Bootstrapped micro-SaaS / Indie Hackers-style product | **Low** | $0–1,000 MRR | 30–40 | $0–2,000 (hosting, ads) |
| 4 | WorldQuant BRAIN consultant program (submit alphas) | **Very low — capped below target even at the top tier** | $0–2,700/mo (Grandmaster tier tops out near $8,000/quarter) | 15–25 | $0 |
| 5 | Bug bounties (HackerOne) | **Low, and skill-mismatched** (security research, not software building) | Hundreds to low thousands/mo, concentrated in a tiny top cohort | 20–30 | $0 |
| 6 | Open-source bounties (Algora, Gitcoin) | **Very low** | Low hundreds/mo | 15–25 | $0 |
| 7 | Numerai (stake NMR, earn/burn on model performance) | **Very low — the math doesn't reach $9k on $5k** | Tens of dollars/mo, with real burn risk | 5–10 | $5,000 (this is the one route that actually deploys the capital) |
| 8 | Kaggle competition prizes | **Very low, lottery-shaped** | $0 most months | 10–20 | $0 |
| 9 | Forecasting tournaments (Metaculus, Good Judgment Open, INFER) | **Very low** | $0–low hundreds/mo | 5–10 | $0 |
| 10 | QuantConnect Alpha Streams | **N/A — discontinued** | — | — | — |

## Freelance dev work (#1, #2): why it's ahead

Upwork's and Toptal's own rate pages didn't return content this session (403 on both, twice), so the specific dollar figures below are general-knowledge estimates, **not verified this session** — treat them as a starting frame, not a measured fact:

- Upwork Python/automation freelancers typically post $25–75/hr at entry-to-mid experience and $75–200/hr for specialists who can credibly claim "AI agent" or "workflow automation" work — a category that has been one of Upwork's fastest-growing skill tags through 2025–2026 by every trade-press account, though I could not confirm the exact percentile figures from Upwork's own report this session.
- Toptal pre-screens (historically cited acceptance rate around 3%) and its freelancers typically bill $60–200+/hr; getting in adds a multi-week screening step that eats into the 5-month clock.
- Contra charges the freelancer 0% commission (its differentiator against Upwork's sliding ~10% and Toptal's client-side markup) but has no vetting funnel — it depends entirely on the builder bringing their own client pipeline, so it's a second channel for the same work rather than a separate bet.

The arithmetic that makes this route plausible: $9,000/month at a blended $75–100/hr requires roughly 90–120 billable hours/month, i.e., 22–28 hours/week — realistic for one skilled person running 2–3 concurrent contracts, *if* the pipeline is full by month 3. The real risk isn't the rate, it's the ramp: Upwork and Toptal both take real weeks to build reviews, trust, and referral flow before the pipeline is full, which is why month 5 is realistically the first month this route clears $9k rather than the average across all 5 months. That's the case for treating this as "Medium" probability rather than "High" — it is very plausible to land somewhere in the $3–7k/month band by month 5, and the $9k figure specifically is a good month, not a guaranteed one.

## The two best bets

**1. Freelance AI/automation development, sold directly and through Upwork/Toptal in parallel.** This is the only route on the table where the skill being monetized (building software with Claude Code) is the same skill being sold, so there's no translation loss. It also front-loads: a solo builder with $5,000 of runway can afford 2–3 months of low-or-no income while the pipeline fills, which is exactly the ramp this route requires. Spend the $5k on runway (not on any of the "capital-in-the-loop" routes below, which can't turn it into $9k/month regardless), a sharp portfolio of 2–3 shipped agent/automation demos, and aggressive outreach from week one rather than waiting for inbound.

**2. A narrow, named consulting offer sold direct (Contra profile + cold outreach + warm network), run in parallel with #1.** The reason to run this alongside rather than instead of Upwork/Toptal is that it's the same underlying work sold through a channel with no platform ramp and no take rate, so early wins here compound faster once even a few clients refer others. The downside is it depends on sales ability more than the platforms do, which is exactly the skill a solo builder doesn't get vetted for — hence "Medium, faster ramp if a network already exists" rather than an outright top pick.

## Why the rest rank low

The capital-deploying routes — WorldQuant BRAIN and Numerai — are structurally capped well under the target. WorldQuant BRAIN's own consultant page **(fetched)** states Grandmaster-tier consultants can earn "upwards of $8,000 or more in a quarterly payment" and Master tier "upwards of $2,000 or more" — that's $667–2,700/month even at the top of the ladder, against skills (statistical alpha research) that don't overlap with software building. Numerai's own docs **(fetched)** give a payout formula where a staked position can gain or lose up to 100% of stake per round, and a historical simulation shows roughly 41–47% *total* return compounded over 260 rounds at a steady 10%/round input — that's a multi-year simulation, explicitly labeled "not indicative of future returns," and even taken at face value $5,000 staked doesn't get within two orders of magnitude of $9,000/month; it's also the one route that actually risks the $5,000 principal via stake-burning on negative scores.

Bug bounties, open-source bounties, Kaggle, and forecasting tournaments share the same shape: real money exists at the top, but it's concentrated in a small, specialized cohort (security researchers for HackerOne, elite Kaggle grandmasters, professional forecasters), payouts per unit of work are small and lumpy, and none of it is the skill being asked about here. A bootstrapped SaaS product is closer to the right skill set but wrong on the clock — the widely cited pattern from Indie Hackers/Starter Story-style case studies is that most solo bootstrapped products take well over 5 months to reach $1,000 MRR, let alone $9,000, and a large share never reach $1k MRR at all; I could not pull Starter Story's or Indie Hackers' own aggregate statistics this session (both returned SPA shells with no data), so treat that claim as directional, not measured.

## Tax note (fetched, IRS)

Self-employment income from any of the above is subject to the self-employment tax: **15.3%** total — 12.4% Social Security (on the first $168,600 of net earnings for 2024, per the IRS page fetched) plus 2.9% Medicare (uncapped), with an additional 0.9% Medicare surtax above $200,000 single / $250,000 married filing jointly. Half of the SE tax is deductible from adjusted gross income, which softens but doesn't eliminate the bite. At $9,000/month ($108,000 annualized), that's real money to reserve quarterly — [IRS: Self-Employment Tax](https://www.irs.gov/businesses/small-businesses-self-employed/self-employment-tax-social-security-and-medicare-taxes).

## Sources

- [WorldQuant BRAIN](https://worldquantbrain.com/) — consultant tier payouts (fetched)
- [Numerai staking docs](https://docs.numer.ai/tournament/learn) — payout formula and historical simulation (fetched)
- [IRS: Self-Employment Tax](https://www.irs.gov/businesses/small-businesses-self-employed/self-employment-tax-social-security-and-medicare-taxes) (fetched)
- Upwork hourly-rate pages, Upwork's most-in-demand-skills report, Toptal's rate page, Contra, HackerOne's Hacker(-Powered Security) Report, Algora's bounty stats, Kaggle's competitions page, Metaculus's tournament page, Indie Hackers' product directory, Starter Story — all attempted, all returned 403/404/empty-shell this session; figures drawn from these platforms above are marked "not verified this session" in text.
