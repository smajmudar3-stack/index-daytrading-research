<!-- research brief, filed 2026-10-06; agent output verbatim. Companion to docs/briefs/memecoins.md
     and docs/briefs/memecoin-sniping.md — those cover pump.fun graduation odds and the sniper
     infrastructure stack; this one is specifically about following a human (KOL tweet, Telegram
     "call channel", or a coordinated insider group) rather than a bot racing the launch itself.
     Verdicts belong in 02_findings/ if anything here is acted on. WebSearch was exhausted mid-session
     (prior work in this session used the 200-call budget); findings below rely on WebFetch against
     primary sources (arXiv, Wikipedia, GitHub, the study itself) plus one background research
     subagent. Anything not confirmed by a fetched source is marked "not verified." -->

# Twitter/X and Telegram call-channel memecoin trading on Solana (2025–2026)

This is about following a *person* — a KOL's tweet, a Telegram "call channel," or riding a
coordinated insider launch — rather than racing the chain with a sniper bot (that's
`memecoin-sniping.md`) or betting on graduation odds generally (`memecoins.md`). The question
is narrower and nastier: by the time a retail follower can act on a human-generated signal, is
there anything left?

## 1. What happens to a token after the call — the only fixed-hold study that exists

The one study that measured **follower-side** returns at retail latency is
[Money Leaves Clues](https://moneyleavesclues.substack.com/p/inside-the-economics-of-pumpfun-call),
which exported a Telegram "call channel" (Jan 22–Mar 9, 2025): 144,913 messages, 8,118 of them
signals, 770 public pump.fun calls, 767 completed, 2,411,719 trades reconstructed, 375 calls
with a usable price curve. At an idealized 30-second entry the median return was **+0.2%** at
30 seconds, **−6.2%** at 1 minute, **−10.5%** at 5 minutes, **−10.7%** at 10 minutes — before
fees. Push entry to a realistic 30-second delay and 5-minute median return falls to **−27.6%**;
the share of calls ever reaching +20% drops from 56.4% to 31.4%. The study's own headline
number is the trap in these datasets generally: one "instant-entry" framing averaged **+552%**
while the median was **−4.0%** — a handful of 50x–100x outliers carry the mean and nobody at
retail latency captures them. This is a Telegram channel, not Twitter; no public study isolates
X/Twitter-sourced KOL calls from Telegram-sourced ones, so whether a tweet call performs
differently is **not verified** — the underlying venue (a pump.fun bonding curve) and the
economics of being last to know are the same regardless of which platform carried the message.

The academic literature backs the direction without matching the venue, and two papers that
look alike are easy to conflate. Hamrick, Rouhi, Mukherjee, Feder, Gandal, Moore & Vasek,
["The Economics of Cryptocurrency Pump and Dump Schemes"](https://par.nsf.gov/servlets/purl/10098691)
(WEIS), joined pump groups on Discord and Telegram directly, scraped the calls via API, and
matched them to 5-minute price data from CoinMarketCap across ~2,000 coins and 220 exchanges,
Jan–Jul 2018; they identified **nearly 5,000 distinct pump-and-dump schemes** in that six-month
window and confirmed prices "often rise significantly" right before the dump. Xu & Livshits,
["The Anatomy of a Cryptocurrency Pump-and-Dump Scheme"](https://arxiv.org/abs/1811.10109)
(USENIX Security 2019), is a different study — 412 Telegram-organized pump-and-dumps (Jun
2018–Feb 2019) with a predictive model showing returns "as high as 60% on small retail
investments" — but that figure describes the *organizer's* early position, not a follower
reacting to the public call; their own detection model exists because the public call is the
exit liquidity, not the edge. Clough & Edwards,
["Pump, Dump, and then What?"](https://arxiv.org/abs/2309.06608), found the long-term effect of
a pump-and-dump is an average **30% relative price drop a year later** — there is no "buy the
rumor, hold" rescue. La Morgia et al.'s
["The Doge of Wall Street"](https://arxiv.org/abs/2105.00733) monitored organized
Telegram/Discord pump groups for three years and detected ~900 events with a 94.5% F1 detector
— useful for flagging the scheme, silent on what a follower's P&L looks like inside it.

A Dune dashboard specifically for KOL-wallet PnL does exist — ["SOL KOL PNL Tracker"
by mwuhjyf](https://dune.com/mwuhjyf/sol-kol-pnl-tracker) — but Dune renders its charts
client-side, so no headline number (win rate, % net-profitable) could be extracted through a
fetch; what fraction of tracked KOL wallets are actually profitable is **not verified** from
this dashboard, only its existence is confirmed. General pump.fun trader PnL is already in
`memecoins.md`: 0.76% of wallets ever clear $1,000.

## 2. The economics of paid promotion, and the KOL as the exit

No dollar-denominated rate card for a crypto KOL's shill tweet could be confirmed this session
— **not verified**. What is confirmed is something arguably more damning: a documented
*in-kind* rate card, and the split between what the promoter keeps and what followers lose on
the highest-profile cases.

- **The LAB token "KOL capital pitch" (reported by ZachXBT via The Block,
  [May 7](https://www.theblock.co/news/regulation/2026-05-07-zachxbt-accuses-projects-like-lab-of-highly-questionable-price-action-posts-10000-bounty-for-info-on-alleged-market-manipulation-400465)
  and [May 14, 2026](https://www.theblock.co/news/ecosystems/2026-05-14-zachxbt-alleges-95-insider-control-of-lab-token-in-investigation-into-ai-terminals-6-billion-fdv-project-401290)).**
  ZachXBT alleged **95% insider control** of a token carrying a **$6B** fully-diluted
  valuation, with ~100M tokens (**~$482M**) moved May 11–12 and **$12M** of a related token
  (RIVER) sent to exchange deposit addresses. The pitch deck he surfaced describes paying KOLs
  not in cash but in **discounted tokens (80% off), vesting in two tranches, conditioned on the
  KOL posting promotional content multiple times or being blacklisted from the deal** — a rate
  card denominated in supply and promotional output rather than dollars. ZachXBT posted a
  $10,000 bounty (funding $1,500 of it himself) for further evidence. The chain was **not
  specified** in reporting found this session — **not verified as Solana** specifically, so
  treat it as evidence about the KOL-economics pattern generally, not a Solana-only data point.
- **$LIBRA (Argentina, Feb 2025).** President Javier Milei tweeted the contract address three
  minutes after the token's creation; price ran from $0.000001 to $5.20 in 40 minutes. Per
  [Bubblemaps' on-chain reconstruction](https://blog.bubblemaps.io/the-libra-playbook-how-one-cluster-drained-87-million-in-a-single-hour/),
  one wallet cluster at **82% concentration** extracted **~$87 million** inside the first hour
  (≈$29.6M + $13.8M in SOL tranches, ~$44.6M in USDC, plus $25M in that hour's LP fees); Hayden
  Davis separately claimed **$113 million** personally. An Argentine congressional
  investigation's 200-page report (late Nov 2025) put aggregate investor losses above
  **$250 million** across an estimated **44,000–74,000** affected wallets, with 112 criminal
  complaints filed in the first 48 hours and the token down 85% within a day.
- **$HAWK (Dec 2024).** Per [Bubblemaps' "Anatomy of a Celebrity Rug"](https://blog.bubblemaps.io/hawk-anatomy-of-a-celebrity-rug/),
  **96% of supply sat in one cluster at launch** (80%+ team-held, 17% to 285 fully-unlocked
  presale wallets, 3% LP); **155 of the 285 presale wallets sold, realizing $3.3 million
  combined**. Market cap went from near **$500 million to $25 million**, a ~98% collapse.
  Coffeezilla publicly alleged insider trading and an exit scam; a lawsuit was filed in the
  EDNY against the token's creators (not Haliey Welch personally) for unlawfully promoting an
  unregistered security, and at least one SEC complaint was filed by an investor. Welch's own
  claim — that she "only got paid a marketing fee" — is **not independently verified**, and
  whether any DOJ criminal charges followed by 2026 is also **not verified**.
- **Gen Z Quant (Nov 2024).** A 13-year-old streamed promotion of his own pump.fun token live,
  reached a $1 million market cap, and sold into the viewers who'd just watched him promote it
  — a reported **$50,000** take. Small scale, but it is the mechanism in miniature: the
  "influencer" is also the counterparty.

No other ZachXBT exposé naming a specific KOL selling into their own Solana call, with dollar
figures, could be confirmed via a fetchable primary source this session — flagged
**not verified** rather than asserted from memory, despite being a widely-discussed pattern in
crypto press.

## 3. Latency: how fast a token moves, and what a tweet-sniper actually claims

`memecoin-sniping.md` already covers the sniper stack in depth (Geyser/gRPC vs WebSocket vs
polling, Jito tip auctions, slot-0 landing rates). The KOL-specific layer sits on top of it:
[Pine Analytics](https://www.bitget.com/news/detail/12560604803448) found that the deployer's
own funded wallets — the fastest possible "call," since they know before anyone else — exit
55% of positions within 1 minute and 85% within 5 minutes. A public tweet or Telegram call
necessarily arrives after that.

Open-source "tweet-sniper" bots exist and are simple: GitHub's
[Twitter_Activated_Crypto_Trading_Bot](https://github.com/jaimindp/Twitter_Activated_Crypto_Trading_Bot)
(114 stars) watches tweets for keyword matches and claims **~5 seconds via streaming or ~1
second via polling** from tweet to order, reporting "100%+ from Elon's doge tweets" on
leveraged futures and "+25%" on new-listing tweets. That is a self-reported anecdote on a
handful of Elon Musk tweets during a period (2021–2023) when a single account could move
Dogecoin broadly — not an out-of-sample backtest, and not transferable evidence for a Solana
memecoin call today. [TopTrenDev/twitter-sniper-bot](https://github.com/TopTrenDev/twitter-sniper-bot)
(7 stars) is purpose-built for exactly this strategy — "listens to a specific Twitter account
in real-time, detects predefined keywords, and instantly buys via Jupiter swap, with MEV
protection" — and, like every repo found,
[Crypto-X-Twitter-Trader-2023](https://github.com/MyLinuxChoice/Crypto-X-Twitter-Trader-2023)
(25 stars) and a Twitter-sourced meme-coin bot by
[Navaneeth-R-Krishnan](https://github.com/Navaneeth-R-Krishnan) included, publishes **no
performance numbers at all**. This matches the pattern `memecoins.md` already found for pure
sniper bots: no vendor publishes a signed, audited wallet history.

X's API economics work against a retail tweet-sniper, and the structure changed in 2026. The
free read tier was cut in Feb 2023 (confirmed:
[Wikipedia, Twitter under Elon Musk](https://en.wikipedia.org/wiki/Twitter_under_Elon_Musk) —
"announced it would be removing the free tier... and replacing it with a basic paid tier"), and
by 2026 the named Free/Basic/Pro/Enterprise subscription ladder from that era had itself been
replaced: per X's current pricing docs, access now runs on a **pay-per-usage credit model** —
post reads $0.005 each, user reads $0.010, likes/mutes/blocks $0.001, post writes $0.015, a
post containing a URL $0.200, capped at 3,000,000 post reads per monthly billing cycle, no
minimum spend, new accounts get up to $70 in free credits, and up to 20% of spend above $200
comes back as xAI credits. A tweet-sniper watching many KOL accounts simultaneously is a reads
business, not a writes business, so the practical cap is the 3M-reads/month ceiling and the
per-read charge, not a flat monthly subscription — cheaper to start than the old $200/month
Basic tier implied, but metered in a way that scales badly if the bot polls many accounts at
high frequency to keep latency down.

## 4. "Cabal" trading: evidence insiders coordinate, none that outsiders can ride it

[MELT (arXiv 2602.13480)](https://arxiv.org/html/2602.13480v1), already cited in `memecoins.md`
for its rug-detector numbers, is also the best evidence on coordination structure: across
41,470 tokens that migrated off the bonding curve, **36.5%** of supply sat in accounts the
paper classifies as coordinated/bundled, and **28%** of holders were bundled wallets. Pine
Analytics' 4,600 sniper wallets funded by 10,400 deployer-linked wallets (cited in
`memecoin-sniping.md`) is the infrastructure side of the same fact: the "cabal" is often one
operator's wallet farm, not an organic alpha group. Solidus Labs' finding that 93% of 388,000
Raydium pools show soft-rug patterns is the same population from a different angle. None of
this literature finds a mechanism by which an outsider — someone reading the public call rather
than running the wallets — captures any of that coordination's edge; structurally, the public
call is how the cabal finds its exit liquidity.

## 5. Sentiment scrapers and LLM-on-tweet bots

No published out-of-sample return for an LLM-on-Twitter-sentiment memecoin bot could be found
— **not verified, and the absence itself is informative**: this repo's own `xsec_uw_test.py`
work already found signed options/flow sentiment carries ~0 information content for next-week
direction on 286 liquid equities over two years; nothing in the memecoin literature surveyed
here claims to have cleared that bar on a noisier, faster, more adversarial asset class with a
smaller dataset.

## Verdict table

| Strategy variant | Documented return at retail latency | Sample | Who measured | Verdict |
|---|---|---|---|---|
| Telegram call-channel, ideal 30s entry | Median +0.2% (30s) → −10.7% (10min) | 770 calls, 375 usable, Jan–Mar 2025 | Money Leaves Clues | Negative once fees are added; mean is a misleading tail |
| Same, realistic 30s delay | Median −27.6% at 5min | same sample | Money Leaves Clues | Worse — delay compounds loss |
| Twitter/X-specific KOL call, fixed hold | No isolated study found | — | not verified | Assume same venue economics as Telegram (not verified distinct) |
| Pump-group organizer/insider position | "Up to 60%" over 2.5 months | 412 events, 2018–19 | Xu & Livshits, USENIX 2019 | Insider-side edge; not available to a public-call follower |
| Buy-the-rumor-hold-a-year | avg −30% relative to market, 1yr later | Telegram dataset | Clough & Edwards, arXiv 2309.06608 | No long-run rescue |
| Tweet-detection sniper bot | Self-reported "100%+" on Elon Musk doge tweets, ~1–5s latency | 1 anecdote, unaudited | Repo author (jaimindp) | Survivorship-biased anecdote, not a backtest |
| Ride a coordinated "cabal" launch as an outsider | 36.5% of supply bundled; 84% of survivors fall below 0.3x migration price in 20min | 41,470 migrated tokens | MELT, arXiv 2602.13480 | Outsider is the exit liquidity, not a participant in the edge |
| Presidential/celebrity call (LIBRA) | One cluster +$87M in first hour (82% concentration); followers −$250M+ across ~44k–74k wallets | 1 event, Feb 2025 | Bubblemaps + Argentine congressional report | Textbook pump-and-dump; retail loses en masse |
| Celebrity-licensed token (HAWK) | 96% supply in one cluster; 155/285 presale wallets sold for $3.3M; mcap $500M→$25M (−98%) | 1 event, Dec 2024 | Bubblemaps, EDNY lawsuit, Coffeezilla | Same pattern; Welch's own take not independently verified |
| "KOL capital pitch" — paid in discounted tokens for promotion, conditioned on posting | 95% insider control alleged; ~$482M moved in 2 days; KOLs got 80%-off tokens, vesting on compliance | 1 event, May 2026, chain not confirmed as Solana | ZachXBT via The Block | Documented pay-for-promotion rate card; retail is explicitly the exit |
| LLM/sentiment-scraper bot on tweets | No published result found | — | not verified | No evidence either way; unproven |

**Bottom line:** every number that can be traced to a primary source points the same way.
The organizer/deployer side of a KOL call is where the documented profit sits (LIBRA's nine
wallets, Pine Analytics' deployer-funded snipers exiting within minutes); the public-facing
call — tweet or Telegram, no venue distinction has been measured — is the mechanism by which
that side finds someone to sell to. The one dataset that measured the follower's actual
fixed-hold return (Money Leaves Clues, 770 calls) found a negative median at every horizon
from 30 seconds to 10 minutes before fees. Nothing in the KOL-specific literature undercuts the
verdict `memecoins.md` already reached for sniping generally — it adds that the "better"
signal (a named human vouching for the token) is not better, because the human is frequently
the counterparty.
