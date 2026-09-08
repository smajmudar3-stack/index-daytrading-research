"""weekly_swing.py — weekly-expiry trade cards, conditioned on macro before technicals.

WHY THIS REPLACES THE SWING PANEL FOR WEEKLY WORK
=================================================
`swing_signals.py` was audited against its own live output on 2026-09-02. Six defects,
all reproducible in that snapshot, and every one of them is fixed here by construction:

  1. STRIKES THAT DO NOT EXIST. `structure()` computed strikes as `round(last*(1+pct), 0)`.
     On TTD (~$14.50) that produced "Buy 14P / Sell 14P" -- a zero-width spread, which is
     not a trade. On RIOT it produced a $1-wide spread on a $19 stock. On COST (~$920) it
     produced "Sell 969C / Buy 1015C", neither of which is a listed strike; COST lists in
     $5 increments. Here every strike is SNAPPED TO THE REAL LADDER read off the chain, and
     a spread whose legs collapse to the same strike is refused rather than printed.

  2. NOT WEEKLY. The `timeframe` field said "1-2 weeks" but was set by `abs(m20) <
     abs(m60)/2`, a momentum ratio with no horizon in it, and the structure targeted the
     ~35 DTE expiry. Every card in that snapshot expired 2026-10-09, 37 days out. Here the
     expiry is chosen from the chain's REAL weekly expiries inside a stated DTE window, and
     preferentially the one that CONTAINS the catalyst being traded.

  3. THE MACRO WAS WORTH PLUS OR MINUS FIVE POINTS. `macro_tilt` was the only non-price
     input to survive to the output, and it moved conviction by at most 5. Everything else
     -- the MA stack, RSI, 20/60/120-day momentum -- is the same price series transformed
     four ways. So the call was technicals wearing a macro hat. Here the macro overlay
     (`desk_notes.py`) is the PRIMARY voter and holds a VETO: a name with no macro basis is
     not proposed, and a name whose trend fights its macro theme is stood down.

  4. EVERY PICK WAS BEARISH OR NEUTRAL. Eight of eight. Because momentum over 20/60/120
     days was negative across a tape that had gone sideways for three weeks, and because
     the regime rule below docked another 8 points from anything bullish.

  5. "RISK-OFF" AT VIX 15.2. `market_context()` fires RISK-OFF when
     `defensive > cyclical + 1`. Energy leading on an oil-war shock satisfied that, so the
     tape was labelled risk-off while VIX sat at 15.2 and QQQ was flat-to-higher on the
     back of chips. A sector-shock label was being read as an equity-risk label. This
     module does not use that regime word at all; it reads the drivers themselves.

  6. NO EXITS. Not one card carried a target, a stop, or a level that would prove it
     wrong. Every card here carries all three, and the invalidation is a PRICE, not a mood.

WHAT THIS IS NOT
================
This is not a backtested edge and nothing in this file claims it is. `02_findings/` is
unambiguous: every swing OPTIONS structure this repo tested was beaten by simply owning
SPY on return, Sharpe and drawdown, and sector-rotation picks did WORSE than random
(p=0.867). Those results falsify SYSTEMATIC, PRICE-DERIVED swing overlays -- which is
exactly what defect 3 above describes, and exactly what was producing the bad cards.

They do not test a macro-conditioned discretionary book, because this repo has never had
one to test. So the honest status of this module is UNPROVEN, not validated, and it says
so on the panel. What it does buy you is that every card names the macro theme it is
expressing and the level that kills it, so it can be scored later. `scorecard.py` picks
these up on a 21-day horizon.

WHAT IT DOES REUSE FROM THE VALIDATED WORK
==========================================
Three findings from `02_findings/WHAT_WORKS.md` are load-bearing here:

  - THE SPREAD FILTER. Far-OTM buying measured -45.6% overall; filtering to contracts with
    a bid-ask spread of 20% or less took it to +5.6%. Execution mattered more than any
    signal tested for choosing which contract to buy. So `MAX_SPREAD_PCT` is a hard gate,
    not a preference, and a leg that fails it kills the card.
  - THE DELTA BAND. Returns improved monotonically toward the money, reaching +26.1% in
    the 16-30 delta band. Short strikes are placed there deliberately.
  - REAL FILLS ONLY. Every leg is priced at the ASK when bought and the BID when sold.
    The repo's central lesson is that a modelled credit which ignored the wings turned
    +3.7%/trade into approximately break-even on real quotes.

Writes `data/weekly_snapshot.json`. Paper only; nothing here places an order.
"""
import math
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from idt import bs, snapshots

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import desk_notes                                             # noqa: E402

ET = ZoneInfo("America/New_York")
OUT = "weekly_snapshot.json"

# ---------------------------------------------------------------- the knobs ---
DTE_MIN, DTE_MAX = 2, 16      # "weekly" means this window, and nothing outside it
DTE_MIN_SWING = 5             # ...but a trade with no event of its own gets a real week
MACRO_BUFFER_DAYS = 3         # days a position must have LEFT after a macro print
BACK_DTE_TARGET = 35          # the reference expiry for the IV term-structure read

# TWO EXECUTION GATES, BECAUSE THEY MEASURE DIFFERENT THINGS.
#
# The +5.6% spread finding is specifically about which contract to BUY: a 20%-wide quote
# on a leg you pay for is 20% of your premium gone at the door. It does NOT transfer to a
# leg you sell -- applying a RELATIVE limit to a $0.15 short strike refuses every credit
# spread on a $65 ETF, which is what the first version of this file did to XLE, XHB and
# XLRE. What actually matters on a spread is the total half-spread cost measured against
# the money at risk, so that is the second gate and it is the binding one.
MAX_BUY_SPREAD_PCT = 20.0     # the measured filter, applied where it was measured
# ROUND TRIP, not one way. You cross the spread on every leg getting in AND getting out,
# so the true cost is the FULL bid-ask on each leg, not half of it. The first version
# summed half-spreads while calling the result "round-trip", which understated the cost of
# every card by exactly a factor of two -- and `weekly_book` caught it immediately, by
# marking six fresh positions and finding them all instantly negative by more than the
# gate claimed was possible.
# 20% is not generous, it is what weekly spreads actually cost. A 10-wide call spread
# bought for 4.00 with a 0.25 bid-ask on each leg gives back 1.00 on the round trip: 25%
# of the money at risk, before the underlying moves at all. The limit exists to reject the
# egregious ones; the number itself is printed on every card, because the honest response
# to "this costs 18% to trade" is to let the reader see it, not to hide it behind a pass.
MAX_TRADE_COST_PCT = 20.0     # full round-trip slippage as a share of max risk
MIN_OPEN_INTEREST = 10        # a strike nobody holds is a strike you cannot leave
SHORT_DELTA_LO, SHORT_DELTA_HI = 0.16, 0.30    # the measured band for short strikes
TERM_RICH = 1.25              # front/back ATM IV above this = front vol is the thing to sell
IV_RICH_VS_RV = 1.15          # ATM IV this far above realised = rich
IV_CHEAP_VS_RV = 0.95
MAX_CARDS = 6

# Concurrency for the universe scan. Every name is an independent set of network round trips,
# so this is the difference between a 14-minute scan and a two-minute one. Kept modest on
# purpose: Unusual Whales has a daily quota and yfinance is unauthenticated and throttles
# under load, so more workers past this point makes the scan SLOWER, not faster.
# 12 was too many and it broke the scan rather than speeding it up: Unusual Whales returned
# HTTP 429 and Yahoo returned 401 "Invalid Crumb", so a 1-minute run produced ZERO cards
# instead of six. Fast and wrong is worse than slow and right. 5 workers with the vendor
# semaphore below keeps the scan around two minutes without tripping either limit.
SCAN_WORKERS = int(os.environ.get("IDT_SCAN_WORKERS", "5"))

# HOW MANY NAMES MAY REACH THE PAID STAGE.
#
# `votes_for` spends Unusual Whales requests, and at 1,550 names 688 of them cleared the basis
# gate and went on to spend. That produced 48 HTTP 429s: 325 names got no flow, dark-pool or
# insider data at all and were refused for "only 2 input(s) had anything to say" — which reads
# on the page as a market condition and was really the scan throttling itself.
#
# Widening the universe was right; letting the whole width through to the expensive stage was
# not. The funnel has to narrow. Candidates are ranked on signals that cost nothing (the
# strength of the free trend read, whether a dated event sits in the window, whether the desk
# names the ticker outright) and only the top slice is analysed. Everything below the cut is
# refused with that stated as the reason, never silently dropped — a name absent because the
# budget ran out is a different fact from a name that was judged and rejected.
PAID_ANALYSIS_CAP = int(os.environ.get("IDT_PAID_CAP", "200"))

# EVERY NAME THAT REACHED THE PAID STAGE GETS RECORDED, NOT JUST THE ONES THAT BECAME CARDS.
#
# The first version of the flow tape recorded only the cards. That is precisely the wrong
# sample: a card is a name that already passed the basis gate, the conviction floor, the
# agreement test and the spread gate, so a study built on those rows would measure the signals
# only where the engine had already decided they agreed. The losers — the names whose flow said
# one thing and whose price went the other way — are the whole point of a cross-section, and
# they are exactly the rows that get filtered out.
#
# So the readings are captured where they are produced, for all ~200 names, whatever the engine
# went on to decide about them.
_TAPE_ROWS = []
_TAPE_LOCK = threading.Lock()

# The vendors are the scarce resource, not the CPU. Unusual Whales enforces a daily quota AND
# a rate limit; yfinance is unauthenticated and hands back 401 crumb errors when hit
# concurrently. Both are held to a small number of simultaneous callers regardless of how
# many scan workers there are, so raising SCAN_WORKERS can never stampede a vendor.
_UW_GATE = threading.Semaphore(2)
_YF_GATE = threading.Semaphore(3)

# ALL ELEVEN SECTORS, ALL THREE CAP TIERS. The first version was 24 names and effectively
# a tech mega-cap list -- NDX-first by design, which made the book a single-sector bet with
# a diversification story attached. `(sector ETF, cap tier)` per name so the panel can show
# what the book is actually concentrated in, and so a theme naming a sector can reach the
# names inside it.
#
# Cap tiers are approximate and only used for reporting. Small caps are included knowing
# most will be REFUSED on liquidity: a weekly option on a $3B name routinely quotes 30-60%
# wide, and the execution gate kills it. That refusal is information -- it is the reason a
# small-cap swing options book is hard -- so those names are scanned and their rejections
# reported rather than quietly left out of the universe.
UNIVERSE_META = {
    # index / theme vehicles
    "QQQ": ("XLK", "index"), "SPY": ("SPY", "index"), "IWM": ("IWM", "index"),
    "SMH": ("XLK", "index"), "XLE": ("XLE", "index"), "XLRE": ("XLRE", "index"),
    "XHB": ("XLY", "index"), "ITB": ("XLY", "index"), "XLF": ("XLF", "index"),
    "XLV": ("XLV", "index"), "XLI": ("XLI", "index"), "XLU": ("XLU", "index"),
    "XLP": ("XLP", "index"), "XLB": ("XLB", "index"), "XLC": ("XLC", "index"),
    # technology
    "AAPL": ("XLK", "large"), "MSFT": ("XLK", "large"), "NVDA": ("XLK", "large"),
    "AVGO": ("XLK", "large"), "ORCL": ("XLK", "large"), "CRM": ("XLK", "large"),
    "AMD": ("XLK", "large"), "MU": ("XLK", "large"),
    "DELL": ("XLK", "mid"), "CRWD": ("XLK", "mid"), "PLTR": ("XLK", "mid"),
    "NET": ("XLK", "mid"), "SNOW": ("XLK", "mid"), "ZS": ("XLK", "mid"),
    "IONQ": ("XLK", "small"), "SOUN": ("XLK", "small"),
    # communications
    "GOOGL": ("XLC", "large"), "META": ("XLC", "large"), "NFLX": ("XLC", "large"),
    "DIS": ("XLC", "mid"), "WBD": ("XLC", "mid"),
    "SNAP": ("XLC", "small"), "PINS": ("XLC", "small"), "ROKU": ("XLC", "small"),
    # consumer discretionary
    "AMZN": ("XLY", "large"), "TSLA": ("XLY", "large"), "HD": ("XLY", "large"),
    "MCD": ("XLY", "large"),
    "ABNB": ("XLY", "mid"), "DASH": ("XLY", "mid"), "CMG": ("XLY", "mid"),
    "CVNA": ("XLY", "small"), "W": ("XLY", "small"), "GME": ("XLY", "small"),
    # consumer staples
    "PG": ("XLP", "large"), "KO": ("XLP", "large"), "COST": ("XLP", "large"),
    "WMT": ("XLP", "large"), "PEP": ("XLP", "large"),
    "KHC": ("XLP", "mid"), "ELF": ("XLP", "small"),
    # energy
    "XOM": ("XLE", "large"), "CVX": ("XLE", "large"),
    "SLB": ("XLE", "mid"), "OXY": ("XLE", "mid"), "MPC": ("XLE", "mid"),
    "AR": ("XLE", "small"), "RRC": ("XLE", "small"),
    # financials
    "JPM": ("XLF", "large"), "BAC": ("XLF", "large"), "GS": ("XLF", "large"),
    "V": ("XLF", "large"), "MA": ("XLF", "large"),
    "COF": ("XLF", "mid"), "SCHW": ("XLF", "mid"),
    "SOFI": ("XLF", "small"), "HOOD": ("XLF", "small"), "AFRM": ("XLF", "small"),
    # health care
    "LLY": ("XLV", "large"), "UNH": ("XLV", "large"), "JNJ": ("XLV", "large"),
    "ABBV": ("XLV", "large"), "MRK": ("XLV", "large"),
    "GILD": ("XLV", "mid"), "VRTX": ("XLV", "mid"),
    "HIMS": ("XLV", "small"),
    # industrials
    "CAT": ("XLI", "large"), "GE": ("XLI", "large"), "HON": ("XLI", "large"),
    "BA": ("XLI", "large"), "UNP": ("XLI", "large"),
    "DE": ("XLI", "mid"), "LMT": ("XLI", "mid"),
    "ACHR": ("XLI", "small"),
    # materials
    "LIN": ("XLB", "large"), "SHW": ("XLB", "large"), "FCX": ("XLB", "large"),
    "NEM": ("XLB", "mid"), "NUE": ("XLB", "mid"),
    # utilities
    "NEE": ("XLU", "large"), "DUK": ("XLU", "large"), "SO": ("XLU", "large"),
    "VST": ("XLU", "mid"), "CEG": ("XLU", "mid"),
    # real estate
    "PLD": ("XLRE", "large"), "AMT": ("XLRE", "large"),
    "O": ("XLRE", "mid"), "SPG": ("XLRE", "mid"),
}
UNIVERSE = sorted(UNIVERSE_META)

# ─── EXPANSION, 2026-09-06 ──────────────────────────────────────────────────────────
# From 103 to ~300 names, every sector, every cap tier. Two things to be honest about:
#
# 1. THE BINDING CONSTRAINT IS THE OVERLAY, NOT THE UNIVERSE. 49 of the previous 103 were
#    already refused for "no macro basis". Tripling the list mostly triples that number. The
#    expansion helps where a theme names a SECTOR, because inheritance then has more names to
#    rank within it -- it does not conjure macro coverage for sectors the desk never writes
#    about.
# 2. LIQUIDITY DOES MOST OF THE FILTERING DOWN HERE. Small and mid caps routinely quote their
#    weeklies 40-160% wide, and the execution gate kills them. Those names are included
#    deliberately so the refusal is REPORTED rather than hidden by never scanning them -- it
#    is the honest reason a small-cap weekly options book is hard.
UNIVERSE_META.update({
    # technology
    "ADBE": ("XLK","large"), "AMAT": ("XLK","large"), "ANET": ("XLK","large"),
    "CSCO": ("XLK","large"), "IBM": ("XLK","large"), "INTC": ("XLK","large"),
    "INTU": ("XLK","large"), "KLAC": ("XLK","large"), "LRCX": ("XLK","large"),
    "NOW": ("XLK","large"), "QCOM": ("XLK","large"), "TXN": ("XLK","large"),
    "PANW": ("XLK","large"), "ACN": ("XLK","large"), "MSI": ("XLK","large"),
    "ADI": ("XLK","large"), "APH": ("XLK","large"), "CRWV": ("XLK","mid"),
    "MRVL": ("XLK","mid"), "ON": ("XLK","mid"), "SMCI": ("XLK","mid"),
    "ARM": ("XLK","mid"), "DDOG": ("XLK","mid"), "TEAM": ("XLK","mid"),
    "HUBS": ("XLK","mid"), "MDB": ("XLK","mid"), "OKTA": ("XLK","mid"),
    "TWLO": ("XLK","mid"), "DOCU": ("XLK","mid"), "PATH": ("XLK","small"),
    "AI": ("XLK","small"), "BBAI": ("XLK","small"), "RGTI": ("XLK","small"),
    "WDC": ("XLK","mid"), "STX": ("XLK","mid"), "NTAP": ("XLK","mid"),
    "GLW": ("XLK","mid"), "TER": ("XLK","mid"), "SNPS": ("XLK","large"),
    "CDNS": ("XLK","large"), "FTNT": ("XLK","large"), "ORCL": ("XLK","large"),
    # communications
    "T": ("XLC","large"), "VZ": ("XLC","large"), "CMCSA": ("XLC","large"),
    "TMUS": ("XLC","large"), "EA": ("XLC","mid"), "TTWO": ("XLC","mid"),
    "MTCH": ("XLC","small"), "PARA": ("XLC","small"), "LYV": ("XLC","mid"),
    "SPOT": ("XLC","mid"), "RDDT": ("XLC","mid"),
    # discretionary
    "NKE": ("XLY","large"), "SBUX": ("XLY","large"), "LOW": ("XLY","large"),
    "TJX": ("XLY","large"), "BKNG": ("XLY","large"), "GM": ("XLY","large"),
    "F": ("XLY","large"), "MAR": ("XLY","mid"), "RCL": ("XLY","mid"),
    "CCL": ("XLY","mid"), "NCLH": ("XLY","small"), "DKNG": ("XLY","mid"),
    "LULU": ("XLY","mid"), "ULTA": ("XLY","mid"), "ROST": ("XLY","mid"),
    "YUM": ("XLY","mid"), "DRI": ("XLY","mid"), "EBAY": ("XLY","mid"),
    "ETSY": ("XLY","small"), "RH": ("XLY","small"), "AN": ("XLY","small"),
    "RIVN": ("XLY","small"), "LCID": ("XLY","small"), "CHWY": ("XLY","small"),
    # staples
    "MDLZ": ("XLP","large"), "CL": ("XLP","large"), "MO": ("XLP","large"),
    "PM": ("XLP","large"), "TGT": ("XLP","large"), "KR": ("XLP","mid"),
    "GIS": ("XLP","mid"), "SYY": ("XLP","mid"), "STZ": ("XLP","mid"),
    "HSY": ("XLP","mid"), "CLX": ("XLP","mid"), "KMB": ("XLP","mid"),
    # energy
    "COP": ("XLE","large"), "EOG": ("XLE","large"), "PSX": ("XLE","mid"),
    "VLO": ("XLE","mid"), "HAL": ("XLE","mid"), "DVN": ("XLE","mid"),
    "FANG": ("XLE","mid"), "HES": ("XLE","mid"), "KMI": ("XLE","mid"),
    "WMB": ("XLE","mid"), "OKE": ("XLE","mid"), "APA": ("XLE","small"),
    # financials
    "MS": ("XLF","large"), "C": ("XLF","large"), "WFC": ("XLF","large"),
    "AXP": ("XLF","large"), "BLK": ("XLF","large"), "SPGI": ("XLF","large"),
    "PYPL": ("XLF","mid"), "USB": ("XLF","mid"), "PNC": ("XLF","mid"),
    "TFC": ("XLF","mid"), "KEY": ("XLF","small"), "ALLY": ("XLF","small"),
    "SYF": ("XLF","mid"), "DFS": ("XLF","mid"), "CME": ("XLF","large"),
    "ICE": ("XLF","large"), "KRE": ("XLF","index"), "UPST": ("XLF","small"),
    # health
    "PFE": ("XLV","large"), "TMO": ("XLV","large"), "DHR": ("XLV","large"),
    "AMGN": ("XLV","large"), "BMY": ("XLV","large"), "CVS": ("XLV","large"),
    "CI": ("XLV","large"), "ISRG": ("XLV","large"), "MRNA": ("XLV","mid"),
    "BIIB": ("XLV","mid"), "REGN": ("XLV","large"), "ZTS": ("XLV","mid"),
    "MCK": ("XLV","mid"), "HCA": ("XLV","mid"), "IQV": ("XLV","mid"),
    # industrials
    "RTX": ("XLI","large"), "UPS": ("XLI","large"), "FDX": ("XLI","large"),
    "MMM": ("XLI","large"), "EMR": ("XLI","large"), "ETN": ("XLI","large"),
    "PH": ("XLI","large"), "NOC": ("XLI","mid"), "GD": ("XLI","mid"),
    "CSX": ("XLI","mid"), "NSC": ("XLI","mid"), "WM": ("XLI","mid"),
    "PWR": ("XLI","mid"), "URI": ("XLI","mid"), "DAL": ("XLI","mid"),
    "UAL": ("XLI","mid"), "AAL": ("XLI","small"), "LUV": ("XLI","mid"),
    # materials
    "APD": ("XLB","large"), "ECL": ("XLB","large"), "DOW": ("XLB","mid"),
    "DD": ("XLB","mid"), "PPG": ("XLB","mid"), "CTVA": ("XLB","mid"),
    "ALB": ("XLB","small"), "CF": ("XLB","small"), "MOS": ("XLB","small"),
    "X": ("XLB","small"), "CLF": ("XLB","small"),
    # utilities
    "AEP": ("XLU","mid"), "D": ("XLU","mid"), "EXC": ("XLU","mid"),
    "SRE": ("XLU","mid"), "XEL": ("XLU","mid"), "ED": ("XLU","mid"),
    "PCG": ("XLU","mid"), "FE": ("XLU","small"), "NRG": ("XLU","mid"),
    # real estate
    "EQIX": ("XLRE","large"), "CCI": ("XLRE","mid"), "PSA": ("XLRE","mid"),
    "WELL": ("XLRE","mid"), "DLR": ("XLRE","mid"), "VICI": ("XLRE","mid"),
    "IRM": ("XLRE","mid"), "ARE": ("XLRE","small"), "HST": ("XLRE","small"),
})

# ─── FULL MARKET EXPOSURE, 2026-09-06 ───────────────────────────────────────────────
# Everything above is a list I typed. That is a selection choice made before any measurement
# runs -- every name in it is one I thought of, which correlates with names that have been in
# the news, which correlates with names that have already moved. Nothing downstream can detect
# that bias, so it has to be removed here.
#
# `universe_builder` takes the S&P 500 + 400 + 600 constituent lists instead: ~1,500 names with
# an official GICS sector for each, and membership rather than my opinion deciding the cap
# tier. The hand list stays as the floor -- it holds the index and theme ETFs (QQQ, SMH, XLE)
# that are not index constituents and that several panels reference by name.
#
# This is affordable because of `_prefetch` below, not in spite of it: history comes down in
# batches, and the expensive per-name work (option chain, Unusual Whales flow) still happens
# only after a name has a basis AND clears a liquidity screen. Widening the front of the
# funnel does not widen the back.
try:
    import universe_builder as _ub
    _wide, _ustatus = _ub.load()
    if _wide:
        for _tk, _m in _wide.items():
            UNIVERSE_META.setdefault(_tk, tuple(_m))
    UNIVERSE_SOURCE = f"index constituents ({_ustatus}) + {len(UNIVERSE_META) - len(_wide or {})} hand-listed vehicles" if _wide else f"hand list only — universe file {_ustatus}"
except Exception as _e:                                       # noqa: BLE001
    UNIVERSE_SOURCE = f"hand list only — {type(_e).__name__}"

UNIVERSE = sorted(UNIVERSE_META)


# ------------------------------------------------------------------- helpers ---

def _now():
    return datetime.now(ET)


def _yf():
    import yfinance as yf
    return yf


# Filled by `_prefetch`. A per-run cache, not a persistent one: stale prices are the failure
# this repo keeps getting bitten by, so it lives and dies with the scan.
_HIST_CACHE = {}
PREFETCH_CHUNK = 120


def _prefetch(tickers, period="1y"):
    """Download history for the whole universe in batches. Returns (n_ok, n_missing).

    THE REASON THE UNIVERSE COULD NOT GROW. `_hist` fetched one ticker per call, so the scan
    cost one HTTP round trip per name and 283 names already took minutes. At 1,500 it would
    have been unusable, and the twelve-worker attempt that produced HTTP 429s and a Yahoo 401
    crumb error was the same problem approached from the wrong end -- more concurrency against
    a rate limit, rather than fewer requests.

    yfinance accepts a LIST. 1,500 names in chunks of 120 is ~13 requests. That is the whole
    trick, and it is why full market coverage costs less than the 283-name scan did.
    """
    yf = _yf()
    ok = 0
    for i in range(0, len(tickers), PREFETCH_CHUNK):
        chunk = tickers[i:i + PREFETCH_CHUNK]
        try:
            with _YF_GATE:
                raw = yf.download(chunk, period=period, interval="1d", progress=False,
                                  auto_adjust=True, group_by="ticker", threads=True)
        except Exception:                                     # noqa: BLE001
            continue
        for tk in chunk:
            try:
                d = raw[tk] if len(chunk) > 1 else raw
                d = d.dropna(how="all").rename(columns=str.lower)
            except (KeyError, TypeError, AttributeError):
                continue
            if d is None or len(d) < 60 or "close" not in d:
                continue
            _HIST_CACHE[tk] = d.dropna(subset=["close"])
            ok += 1
    return ok, len(tickers) - ok


def _hist(tk):
    """One year of daily closes, or None. Never raises.

    Reads the batch cache first; falls back to a single fetch for anything the batch missed
    (a fresh listing, a symbol yfinance spells differently) so one absent name never silently
    removes itself from the scan.
    """
    cached = _HIST_CACHE.get(tk)
    if cached is not None:
        return cached
    try:
        with _YF_GATE:
            d = _yf().download(tk, period="1y", interval="1d", progress=False,
                               auto_adjust=True, multi_level_index=False)
    except Exception:                                         # noqa: BLE001
        return None
    if d is None or len(d) < 60:
        return None
    d = d.rename(columns=str.lower)
    return d.dropna(subset=["close"])


def _realised_vol(closes, n=20, trim=2):
    """Realised vol with the largest moves trimmed. The trim is the point.

    A plain 20-day realised vol that spans an earnings gap is dominated by that one day, and
    every card downstream then reads forward IV as "cheap" against it. On 2026-09-04 CRWD
    showed IV 43.6% against 96.4% realised and CRM 34.0% against 85.3% — both had just
    reported, and both were routed to a DEBIT structure on the strength of a comparison to a
    number that was really one gap.

    That matters because the comparison decides whether the engine buys premium or sells it,
    and this repo measured that choice as worth about ten percentage points a trade (paying
    theta -11.12% against -1.27% for collecting). Getting it wrong on a stale earnings gap is
    an expensive way to be wrong.

    Trimming the two largest absolute moves leaves the ONGOING volatility, which is what a
    forward option is actually priced against. Both figures are returned so the card can show
    the gap between them.
    """
    r = closes.pct_change().tail(n).dropna()
    if len(r) < max(5, n // 2):
        return None
    raw = float(r.std() * math.sqrt(252) * 100)
    if trim and len(r) > trim + 4:
        keep = r.reindex(r.abs().sort_values(ascending=False).index[trim:])
        trimmed = float(keep.std() * math.sqrt(252) * 100)
    else:
        trimmed = raw
    return {"rv": trimmed, "rv_raw": raw,
            "gap_from_raw": round(raw - trimmed, 1)}


def _mid(bid, ask):
    """None unless BOTH sides are real. A one-sided quote is not a price."""
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return None
    if not (b > 0 and a > 0 and a >= b):
        return None
    return (a + b) / 2.0


def _spread_pct(bid, ask):
    m = _mid(bid, ask)
    if m is None or m <= 0:
        return None
    return float((float(ask) - float(bid)) / m * 100)


# ------------------------------------------------------------------- chains ---

def _expiries(tk):
    try:
        return list(_yf().Ticker(tk).options or [])
    except Exception:                                         # noqa: BLE001
        return []


def _dte(exp):
    try:
        d = datetime.strptime(exp, "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d - _now().date()).days


def _pick_weekly(tk, own_events, macro_events):
    """The weekly expiry to trade, and why that one.

    THE DISTINCTION THAT MATTERS. An event on the NAME and an event on the TAPE want
    opposite expiries, and the first version of this file treated them the same. Friday's
    payrolls print pulled every single card onto the 2-day expiry, so six "weekly" trades
    all died on Friday morning's number. That is not a weekly book, it is six lottery
    tickets on one macro print.

      - The name's OWN event (earnings): take the FIRST expiry at or after it. You are
        buying the repricing, so you must still be holding when it happens.
      - A MACRO event (payrolls, CPI, FOMC): take the first expiry at least
        MACRO_BUFFER_DAYS PAST it. The print is a hazard the position has to survive, not
        the thing being bought, and an option that expires into it has no time left to be
        right afterwards.
      - Neither: the middle of the window.
    """
    floor = DTE_MIN if own_events else DTE_MIN_SWING
    cands = [(e, d) for e in _expiries(tk)
             for d in [_dte(e)] if d is not None and floor <= d <= DTE_MAX]
    if not cands:
        return None, None, f"no listed expiry between {floor} and {DTE_MAX} days out"

    for c in own_events:
        covering = [(e, d) for e, d in cands if d >= c["days_away"]]
        if covering:
            e, d = min(covering, key=lambda x: x[1])
            return e, d, f"covers {c['label']} on {c['date']} (+{c['days_away']}d)"

    # EVERY MACRO EVENT IN THE WINDOW, NOT THE FIRST ONE.
    #
    # This loop used to `return` on the first macro event it could clear. On 2026-09-06 the
    # first one was "Labor Day — US markets closed" at +1d, which the 2026-09-11 expiry clears
    # trivially — so the function returned "clears Labor Day with 4 days left to work" and
    # never looked at the August CPI print landing 08:30 ON that expiry. Five of six cards
    # were routed onto CPI morning by a rule whose stated purpose is to avoid exactly that,
    # because a market holiday satisfied it first.
    #
    # A macro event is a hazard, and hazards do not take turns. The candidate has to be judged
    # against ALL of them: for each expiry, any print it spans must leave MACRO_BUFFER_DAYS
    # afterwards. Where nothing in the window is clean — and this week genuinely is not, with
    # CPI on the 11th and FOMC on the 16th — take the candidate with the most room and NAME
    # what it fails to clear, so the card carries the exposure rather than hiding it.
    if macro_events:
        def _worst(d):
            """(violations, smallest gap) for one candidate expiry. Lower is better."""
            gaps = [d - c["days_away"] for c in macro_events if 0 <= c["days_away"] <= d]
            if not gaps:
                return (0, 99)
            return (sum(1 for g in gaps if g < MACRO_BUFFER_DAYS), min(gaps))

        def _key(x):
            """Fewest violations first; then the SHORTEST clean expiry, or the roomiest dirty one.

            The distinction matters. When a candidate clears every print, extra time is not a
            benefit — it is more theta and more exposure for the same thesis, so the shortest
            clean expiry wins. Only when nothing is clean does room become the tiebreak, and
            then it is the least-bad choice rather than a preference.
            """
            v, gap = _worst(x[1])
            return (v, x[1] if v == 0 else -gap)

        e, d = min(cands, key=_key)
        bad = [c for c in macro_events
               if 0 <= c["days_away"] <= d and (d - c["days_away"]) < MACRO_BUFFER_DAYS]
        spans = [c for c in macro_events if 0 <= c["days_away"] <= d]
        if not bad:
            cleared = ", ".join(f"{c['label']} (+{c['days_away']}d)" for c in spans) or "—"
            return e, d, (f"clears {cleared} with room afterwards"
                          if spans else "no dated macro event in the window")
        names = ", ".join(f"{c['label']} on {c['date']}" for c in bad)
        return e, d, (f"NOTHING in the {floor}-{DTE_MAX}d window clears every print: this is "
                      f"the best available and it still sits close to {names}. Treat that as "
                      f"a hazard to exit before, not to hold through.")

    mid = (floor + DTE_MAX) / 2
    e, d = min(cands, key=lambda x: abs(x[1] - mid))
    return e, d, "no dated event in the window; middle of the weekly window"


def _pick_back(tk, front_dte):
    """The reference expiry for the term-structure read: nearest to ~35 DTE, past front."""
    best = None
    for e in _expiries(tk):
        d = _dte(e)
        if d is None or d <= front_dte + 2:
            continue
        if best is None or abs(d - BACK_DTE_TARGET) < abs(best[1] - BACK_DTE_TARGET):
            best = (e, d)
    return best or (None, None)


def _chain(tk, exp):
    try:
        c = _yf().Ticker(tk).option_chain(exp)
    except Exception:                                         # noqa: BLE001
        return None, None
    return c.calls, c.puts


def _ladder(calls, puts):
    """The real strike ladder, and its typical increment.

    THIS IS THE FIX FOR THE BROKEN STRIKES. Every strike this module emits comes off this
    list. Nothing is ever computed as a percentage of spot and rounded.
    """
    ks = set()
    for df in (calls, puts):
        if df is not None and len(df):
            ks.update(float(k) for k in df["strike"].tolist())
    ks = sorted(ks)
    if len(ks) < 4:
        return ks, None
    gaps = [round(b - a, 4) for a, b in zip(ks, ks[1:], strict=False) if b > a]
    inc = float(pd.Series(gaps).mode().iloc[0]) if gaps else None
    return ks, inc


def _side_ladder(df):
    """The strikes listed ON THIS SIDE of the chain.

    Calls and puts do not always list the same strikes, especially in the wings. The
    first version of this file snapped against the UNION and then looked the strike up in
    the calls frame, so a put-only strike came back as "no such listed strike" and killed
    otherwise fine candidates. Snap against the side you are going to trade.
    """
    if df is None or not len(df):
        return []
    return sorted(float(k) for k in df["strike"].tolist())


def _snap(ladder, target, exclude=()):
    """The listed strike nearest `target`, never one already used by another leg."""
    avail = [k for k in ladder if k not in exclude]
    return min(avail, key=lambda k: abs(k - target)) if avail else None


def _row(df, strike):
    if df is None or not len(df):
        return None
    m = df[df["strike"] == strike]
    return m.iloc[0] if len(m) else None


def _atm_iv(calls, puts, spot):
    """ATM implied vol as a percentage, averaged across the nearest call and put."""
    ivs = []
    for df in (calls, puts):
        if df is None or not len(df):
            continue
        r = df.iloc[(df["strike"] - spot).abs().argmin()]
        try:
            v = float(r["impliedVolatility"])
        except (TypeError, ValueError, KeyError):
            continue
        if 0.01 < v < 5.0:
            ivs.append(v * 100)
    return float(np.mean(ivs)) if ivs else None


# An ATM straddle is NOT a one-sigma move. For a lognormal, straddle/S ~= sqrt(2/pi)*sigma*
# sqrt(T) = 0.7979*sigma*sqrt(T). Comparing the raw straddle price against a one-sigma
# realised move is therefore apples-to-oranges and biases the ratio DOWN by ~20%.
STRADDLE_TO_SIGMA = math.sqrt(2.0 / math.pi)      # 0.7979


def _implied_move(calls, puts, spot, ladder):
    """The move the front week is pricing, from the ATM straddle. Percent of spot.

    The desk's own NVDA note is the template: "the market is pricing only about a 5.5%
    move, versus roughly a 7.4% average realized". Comparing what is priced against what
    tends to happen is the whole question on an event week.
    """
    k = _snap(ladder, spot)
    if k is None:
        return None
    c, p = _row(calls, k), _row(puts, k)
    if c is None or p is None:
        return None
    cm, pm = _mid(c.get("bid"), c.get("ask")), _mid(p.get("bid"), p.get("ask"))
    if cm is None or pm is None:
        return None
    straddle = float((cm + pm) / spot * 100)
    # Two numbers, because they answer different questions and conflating them was the bug.
    #   `straddle` is the BREAKEVEN — what the week has to move for a long straddle to pay,
    #             and the right thing to show a reader.
    #   `sigma`    is the implied ONE-SIGMA move, the only version comparable to a realised
    #             vol. Using the straddle here made every fairly-priced name read EXPAND:
    #             IV == RV scores 0.80, under the 0.85 expand threshold, while COMPRESS
    #             needed a ratio of 1.25, i.e. a 57% vol premium almost nothing clears.
    #             Measured 2026-09-06: WFC's true IV/RV was 1.34 and it was reading "normal".
    return {"straddle": straddle, "sigma": straddle / STRADDLE_TO_SIGMA}


def _leg_quote(df, strike, buying):
    """One leg, priced the way it would actually fill, plus its liquidity verdict.

    Bought at the ASK, sold at the BID. This is the repo's central methodological lesson
    and it is not negotiable: modelling the mid is how +3.7%/trade became break-even.
    """
    r = _row(df, strike)
    if r is None:
        return None, f"{strike:g} is not listed on this side of the chain"
    bid, ask = r.get("bid"), r.get("ask")
    sp = _spread_pct(bid, ask)
    if sp is None:
        return None, f"{strike:g} has no two-sided quote"
    if buying and sp > MAX_BUY_SPREAD_PCT:
        return None, (f"{strike:g} costs {sp:.0f}% of its own price in spread and this leg "
                      f"is bought (limit {MAX_BUY_SPREAD_PCT:.0f}%)")
    try:
        oi = int(r.get("openInterest") or 0)
    except (TypeError, ValueError):
        oi = 0
    if oi < MIN_OPEN_INTEREST:
        return None, f"{strike:g} has {oi} open interest (limit {MIN_OPEN_INTEREST})"
    px = float(ask) if buying else float(bid)
    return {"strike": float(strike), "price": px, "spread_pct": round(sp, 1),
            "half_spread": (float(ask) - float(bid)) / 2.0,
            "oi": oi, "buying": bool(buying),
            "iv": float(r.get("impliedVolatility") or 0) * 100}, None


def _delta_strike(df, spot, dte, target_delta, call=True):
    """The listed strike closest to a target delta, using the chain's own IVs."""
    if df is None or not len(df):
        return None
    T = max(dte, 1) / 365.0
    best, bestd = None, 9e9
    for _, r in df.iterrows():
        try:
            iv = float(r["impliedVolatility"])
            k = float(r["strike"])
        except (TypeError, ValueError, KeyError):
            continue
        if not (0.01 < iv < 5.0):
            continue
        d = abs(float(bs.delta(spot, k, T, iv, call=call)))
        if abs(d - target_delta) < bestd:
            best, bestd = k, abs(d - target_delta)
    return best


# -------------------------------------------------------------- the decision ---

def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return float((100 - 100 / (1 + up / (dn + 1e-12))).iloc[-1])


def _trend(px, bench=None):
    """The technical read, on the WEEKLY timeframe the trade is actually held over.

    STILL ONE VOTER AT ONE WEIGHT. `signal_weights` gives `trend` 0.35 as measured-weak
    (~55-60% over weeks) and none of this changes that. What changes is the QUALITY of the
    number handed to that weight. The previous version was `tanh((m60*2 + m20) * 3)` plus a
    ±0.20 moving-average nudge, which on a book of tech names in the same theme returned
    +0.35, +0.35, +0.34, +0.34 -- four names, one number, no information. With the macro
    theme also flat across every name in a sector, the vote had almost nothing left to
    discriminate on.

    Seven components, each on a weekly horizon, each visible on the card so the reader can
    see WHY one name in a theme ranks above another:

      w4 / w12 / w26   4, 12 and 26-week returns — the trade is held for weeks, so the
                       lookbacks should be weeks, not the 20/60 trading days used before
      MA stack         above the 10-week and 40-week averages, the classic weekly stack
      from 52w high    proximity to the high; leaders sit near it, broken names do not
      RSI              stretched in either direction argues against chasing
      RS vs SPY        12-week relative strength against the index

    RS vs SPY is folded INTO the trend value rather than added as its own weighted input.
    A name outperforming the index is stock selection, which is not the thing this repo
    measured as null -- that was SECTOR rotation (1,512 configs, p=0.867) -- but it has not
    been measured here either, so it does not get its own weight.
    """
    c = px["close"]
    last = float(c.iloc[-1])

    def ret(days):
        return (last / float(c.iloc[-days - 1]) - 1) if len(c) > days else None

    w4, w12, w26 = ret(20), ret(60), ret(130)
    s50 = float(c.tail(50).mean())
    s200 = float(c.tail(200).mean()) if len(c) >= 200 else s50
    hi52 = float(c.tail(252).max()) if len(c) >= 60 else last
    from_hi = last / hi52 - 1 if hi52 else 0.0
    rsi = _rsi(c)

    rs12 = None
    if bench is not None and len(bench) > 60:
        b_last, b_then = float(bench.iloc[-1]), float(bench.iloc[-61])
        if b_then and w12 is not None:
            rs12 = w12 - (b_last / b_then - 1)

    # Each part in [-1, +1], then a weighted blend. The weights inside the composite are
    # judgement, not measurement, and they only decide the SHAPE of one 0.35-weight voter.
    parts, weights = [], []

    def add(v, w):
        if v is not None:
            parts.append(max(-1.0, min(1.0, v)))
            weights.append(w)

    add(math.tanh((w4 or 0) * 8), 0.20)      # recent, fast
    add(math.tanh((w12 or 0) * 4), 0.30)     # the horizon that matters most
    add(math.tanh((w26 or 0) * 2.5), 0.15)   # regime
    add(1.0 if last > s50 > s200 else (-1.0 if last < s50 < s200 else 0.0), 0.15)
    # Within 5% of the 52-week high is strength; 30% below it is damage.
    add(max(-1.0, min(1.0, (from_hi + 0.15) / 0.15)), 0.10)
    # Stretched cuts both ways: it argues against chasing, not for reversing.
    add(-0.6 if rsi > 75 else (0.6 if rsi < 25 else 0.0), 0.05)
    # rs12 IS DELIBERATELY NOT A VOTER. rs12 = w12 - spy12, and spy12 is a single scalar per
    # date, so subtracting it cannot change the cross-sectional RANKING of the names. Verified
    # on 200 of 200 dates: w12 and rs12 produce an identical ranking. It was never a seventh
    # component -- it was w12 counted twice, giving w12 an effective 0.45 instead of 0.30, and
    # w12 is the component whose IC flips sign hardest across splits. It is still COMPUTED and
    # shown on the card, because "up 27% while SPY did 4%" is worth reading even when it adds
    # nothing to a rank.

    score = sum(p * w for p, w in zip(parts, weights, strict=False)) / sum(weights) \
        if weights else 0.0

    return {
        "score": round(float(score), 3), "last": round(last, 2),
        "w4": round(w4 * 100, 1) if w4 is not None else None,
        "w12": round(w12 * 100, 1) if w12 is not None else None,
        "w26": round(w26 * 100, 1) if w26 is not None else None,
        "rs12": round(rs12 * 100, 1) if rs12 is not None else None,
        "rsi": round(rsi, 0), "from_hi": round(from_hi * 100, 1),
        "above50": last > s50, "above200": last > s200,
        # Kept under the old names so `_exits` and the ledger keep working.
        "m20": round(w4 * 100, 1) if w4 is not None else 0.0,
        "m60": round(w12 * 100, 1) if w12 is not None else 0.0,
        "hi20": round(float(px["high"].tail(20).max()), 2),
        "lo20": round(float(px["low"].tail(20).min()), 2),
    }


def _macro_view(macro, tk, y10_5d=None, earn_cal=None):
    """The overlay's verdict on this name: (+1|-1|0, themes, why) or a stand-down.

    A ticker named by two themes pointing opposite ways is a CONFLICT and is stood down.
    That is a real disagreement in the macro read, and taking it at half size is how you
    lose slowly with a good-sounding reason.
    """
    hits = desk_notes.theme_for(macro, tk)
    inherited = False

    # SECTOR INHERITANCE. The Crown notes are cross-asset macro: they name maybe a dozen
    # tickers, mostly sector ETFs. Without this, expanding the universe to 103 names across
    # eleven sectors changes nothing -- ninety of them are refused as "no theme names this
    # ticker" and the book stays a tech book with a longer ignore list.
    #
    # So a theme that names a SECTOR reaches the names inside it. "The desk says the oil
    # shock is the cleanest driver on the board" makes energy names ELIGIBLE; it does not
    # pick which one. That distinction matters, because picking names BY sector strength is
    # the thing this repo measured as worse than random (1,512 configs, p=0.867). Here the
    # sector decides eligibility and the evidence-weighted vote -- flow, insider buys, short
    # interest, trend, VIX term structure -- decides direction and conviction within it.
    #
    # Inherited themes are flagged so the card never presents an inference as a statement.
    if not hits:
        sec = SECTOR_OF.get(tk)
        if sec and sec != tk:
            # Themes name VEHICLES (SMH, XHB, ITB, XLE), not GICS codes, so the lookup has
            # to go through the vehicle. Checking `theme_for(macro, "XLK")` finds nothing
            # even when a theme names SMH, which is why the first version of this left
            # ninety of a hundred and three names unreachable.
            for vehicle in VEHICLES_OF_SECTOR.get(sec, (sec,)):
                hits = desk_notes.theme_for(macro, vehicle)
                if hits:
                    inherited = True
                    break

    if not hits:
        # NO MACRO THEME IS NOT NO EVIDENCE. The Crown notes are cross-asset macro and simply
        # do not write about utilities, staples or health care most weeks, so gating purely
        # on them left seven of eleven sectors permanently empty no matter how large the
        # universe got.
        #
        # But `desk_macro` is only ONE of the voters, and it is the only sector-limited one.
        # VIX backwardation (0.30, measured), short interest (0.30, measured), classified
        # flow (0.35), dark pool (0.15) and insider buys (0.10) are all name-level and apply
        # to any sector. A name with no theme can still be judged on those.
        #
        # It is NOT the "pure technicals" configuration that produced the original bad book:
        # trend is 0.35 of a vote that also contains flow, insider buys and short interest.
        # It IS weaker evidence, because the orthogonal macro input is missing, so it carries
        # a higher bar (`VOTE_NO_MACRO`) and every such card is flagged on its face.
        # BEFORE REFUSING, DERIVE ONE. Waiting for a newsletter to mention utilities is not
        # an analysis strategy: 123 of 283 names were refused on arrival because the desk
        # notes happen to be rates/energy/FX-centric. `market_basis` builds a basis from data
        # instead -- a dated earnings event inside the expiry window, or this repo's measured
        # 20-year sector rate betas against the actual yield move. Never from sector rotation,
        # which measured worse than random.
        try:
            import market_basis
            derived = market_basis.derive(tk, SECTOR_OF.get(tk), y10_5d=y10_5d,
                                          calendar=earn_cal)
        except Exception:                                     # noqa: BLE001
            derived = None
        if derived:
            return {"side": derived["side"], "themes": derived["themes"],
                    "why": derived["why"], "derived": True,
                    "neutral": derived.get("neutral", False),
                    "event": derived.get("event"), "stand_down": None}

        if REQUIRE_MACRO_BASIS:
            return {"side": 0, "themes": [], "why": None, "no_macro_basis": True,
                    "stand_down": ("no desk-note theme covers this name or its sector, and no "
                                   "dated event or measured rate exposure could be derived "
                                   "either — a card without a basis is not a trade")}
        return {"side": 0, "themes": [], "why": None, "no_macro_basis": True,
                "stand_down": None}
    sides = {s for _, s in hits}
    if len(sides) > 1:
        labels = " vs ".join(t["label"] for t, _ in hits)
        return {"side": 0, "themes": [t for t, _ in hits], "why": None,
                "stand_down": f"the overlay contradicts itself here — {labels}"}
    side = hits[0][1]
    # A `dispersion` theme is explicitly not a directional view on the whole name.
    stances = {t.get("stance") for t, _ in hits}
    ts = [t for t, _ in hits]
    why = " ".join(t["why"] for t in ts)
    if inherited:
        sec = SECTOR_OF.get(tk)
        why = (f"INHERITED from the {SECTOR_NAME.get(sec, sec)} sector, which the note names "
               f"directly; the note does not mention {tk} itself. " + why)
    return {"side": side, "themes": ts, "why": why, "stances": sorted(stances),
            "inherited": inherited, "stand_down": None}


# How hard the weighted vote must point against the macro gate before the name is stood
# down, and how much of a view the vote needs before it overrides the gate's own direction.
VOTE_CONFLICT = 0.25
VOTE_NEUTRAL = 0.10
# A card with no macro theme behind it is missing the one input orthogonal to price, so it
# has to clear a materially higher bar on the measured voters alone.
# A MACRO BASIS IS REQUIRED, not preferred. This was briefly a handicap (a themeless name
# could clear a higher bar on the measured voters alone) so that every sector could be
# represented. That was wrong, and the 2026-09-04 16:02 cycle showed why: JNJ and NEM shipped
# with ZERO themes on a single voting input — trend — which is precisely the pure-technicals
# card the whole rewrite existed to remove. Sector coverage is not worth a card with nothing
# behind it. A sector the desk does not write about gets no card.
REQUIRE_MACRO_BASIS = True

# MORE THINGS BACKING IT. `desk_macro` and `trend` are the only two voters always available;
# flow, dark pool, short interest and insider buys come from Unusual Whales and VIX
# backwardation abstains whenever the term structure is in contango. So a card resting on two
# inputs is a card resting on the macro read plus a moving average, and `agreement` cannot
# detect it -- one input agreeing with itself is 100%.
#
# Requiring three DISTINCT agreeing inputs forces corroboration from something beyond those
# two. It also has a useful second effect: refusing themeless names before the profile fetch
# cuts the Unusual Whales calls from 103 names a cycle to about 30, which is what exhausted
# the daily quota and caused the silent degradation in the first place.
MIN_VOTING_INPUTS = 3
MIN_AGREEING_INPUTS = 3

# Only consulted if REQUIRE_MACRO_BASIS is ever turned back off.
VOTE_NO_MACRO_FALLBACK = 0.30

# HIGH CONVICTION ONLY. Every card must clear these, themed or not. Before this a themed
# name rode the macro gate's direction on a vote of -0.04, which is no conviction at all --
# TSLA and O both shipped on 2026-09-04 at exactly that. An empty book is a legitimate and
# frequent answer; a book of six low-conviction cards is not.
MIN_CONVICTION = 0.30     # |weighted vote| across every input that has earned a weight
MIN_AGREEMENT = 0.60      # share of live weight pointing the same way as the net score


def _decide(macro_view, trend, vote, own_catalyst=None, move='normal'):
    """Macro gates, the weighted vote calls it. Two layers, and the order matters.

    THE MACRO IS A GATE, NOT A VOTE. A name no desk-note theme mentions is not eligible at
    all. That gate is what stopped the old panel ranking a hundred names on momentum and
    always finding eight, and a gate is not something the other inputs can outvote.

    AMONG ELIGIBLE NAMES, THE VOTE DECIDES. Direction and conviction come from
    `signal_weights.combine()` across every input that has earned a weight: the macro read
    itself (0.35, unmeasured), trend (0.35), classified flow (0.35), short interest (0.30,
    NEGATIVE sign), VIX backwardation inside a golden cross (0.30, the only signal that beat
    its base rate in every era), dark pool (0.15-0.38) and insider open buys (0.10, small
    because n=1,128 and the sign flips by era). Sector rotation and dealer gamma as
    direction contribute exactly zero, by measurement.

    THE CONFLICT CASE. When the vote comes out against the macro theme that made the name
    eligible, the two layers disagree. That normally stands the name down. Into a DATED
    event on that name it does not: AVGO went into its own print down 7% over 60 days while
    the overlay called it the week's most important AI report. That is not a reason to skip
    the only real catalyst on the board, it is a reason not to express it directionally, so
    the card routes to a volatility structure and prints the disagreement.
    """
    if macro_view["stand_down"]:
        return None, macro_view["stand_down"], False
    side = macro_view["side"]
    score = vote["score"]

    if macro_view.get("no_macro_basis"):
        if abs(score) < max(VOTE_NO_MACRO_FALLBACK, MIN_CONVICTION):
            return None, (f"no desk-note theme covers this name or its sector, and the "
                          f"measured voters alone come out at {score:+.2f}, inside the "
                          f"+/-{VOTE_NO_MACRO_FALLBACK:.2f} bar a card without a macro basis has "
                          f"to clear"), False
        agree = [d["input"] for d in vote["detail"]
                 if d["contribution"] and (d["contribution"] > 0) == (score > 0)]
        return ("bullish" if score > 0 else "bearish"), \
               (f"NO MACRO BASIS — the desk notes do not cover this name or its sector. "
                f"Built on the measured voters alone, which came out {score:+.2f} across "
                f"{vote['n_inputs']} inputs ({', '.join(agree[:4]) or 'nothing'} agreeing). "
                f"Weaker evidence than a themed card by construction"), False

    against = (side > 0 and score < -VOTE_CONFLICT) or (side < 0 and score > VOTE_CONFLICT)
    if against:
        top = ", ".join(f"{d['input']} {d['contribution']:+.2f}"
                        for d in vote["detail"][:3] if d["contribution"])
        msg = (f"the overlay argues for {'upside' if side > 0 else 'downside'} but the "
               f"weighted vote comes out {score:+.2f} against it ({top})")
        if not own_catalyst:
            return None, msg + " — stood down", False
        return ("bullish" if side > 0 else "bearish"), \
               (msg + f", so this is expressed as a volatility trade around "
                      f"{own_catalyst['label']}, not a directional one"), True

    # A NEUTRAL EVENT CARD IS JUDGED ON A DIFFERENT AXIS, and this has to come BEFORE the
    # directional floor or it can never pass. The floor asks "does the evidence point strongly
    # ONE WAY" -- but a dated event with no directional side is SUPPOSED to score near zero.
    # KR scored +0.05 on a real earnings date five days out and was refused for lacking
    # conviction it was never claiming to have, which is why the iron condor, iron butterfly
    # and straddle branches had still never fired.
    #
    # The right question for a neutral card is not "which way" but "is the volatility
    # mispriced": the move read must be decisive (compress or expand), and the event must be
    # dated and inside the window. A `normal` move read means there is no vol view either, and
    # then there is genuinely no trade.
    if macro_view.get("neutral"):
        ev = macro_view.get("event") or {}
        if move not in ("compress", "expand"):
            return None, (f"a dated event ({ev.get('label', 'event')} on {ev.get('date')}) but "
                          f"the move read is {move}: no directional view AND no volatility "
                          f"view is not a trade"), False
        if abs(score) > MIN_CONVICTION:
            pass          # the vote developed a real side; fall through and trade it
        else:
            return "neutral", (
                f"a dated event ({ev.get('label', 'event')} on {ev.get('date')}) with no "
                f"directional side — the vote is {score:+.2f}, inside ±{VOTE_NEUTRAL:.2f}. "
                f"The volatility read is {move.upper()}, so this is a view on HOW FAR, not "
                f"which way"), False

    # THE CONVICTION FLOOR, applied to themed cards too. A macro theme makes a name
    # ELIGIBLE; it does not make a trade. Riding the gate's direction on a vote of -0.04 is
    # how a book fills up with cards nobody should take.
    if abs(score) < MIN_CONVICTION:
        return None, (f"vote {score:+.2f} is inside the +/-{MIN_CONVICTION:.2f} conviction "
                      f"floor — the theme makes it eligible, the evidence does not make it "
                      f"a trade"), False
    voting = [d for d in vote.get("detail", []) if d.get("contribution")]
    agreeing = [d for d in voting if (d["contribution"] > 0) == (score > 0)]
    if len(voting) < MIN_VOTING_INPUTS:
        return None, (f"only {len(voting)} input(s) had anything to say "
                      f"({', '.join(d['input'] for d in voting) or 'none'}); a trade needs at "
                      f"least {MIN_VOTING_INPUTS}. With just the macro read and a moving "
                      f"average there is nothing corroborating either of them"), False
    if len(agreeing) < MIN_AGREEING_INPUTS:
        return None, (f"vote {score:+.2f} but only {len(agreeing)} of {len(voting)} inputs "
                      f"point that way ({', '.join(d['input'] for d in agreeing) or 'none'}); "
                      f"a trade needs {MIN_AGREEING_INPUTS} agreeing"), False
    if vote.get("agreement") is not None and vote["agreement"] < MIN_AGREEMENT:
        return None, (f"vote {score:+.2f} but only {vote['agreement']*100:.0f}% of the live "
                      f"weight points that way (floor {MIN_AGREEMENT*100:.0f}%) — the "
                      f"inputs disagree with each other"), False

    # Direction follows the vote when it has a view of its own, and the gate when it does not.
    if abs(score) > VOTE_NEUTRAL:
        direction = "bullish" if score > 0 else "bearish"
    else:
        direction = "bullish" if side > 0 else "bearish"

    agree = [d["input"] for d in vote["detail"]
             if d["contribution"] and (d["contribution"] > 0) == (score > 0)]
    conf = (f"weighted vote {score:+.2f} across {vote['n_inputs']} inputs "
            f"({int(vote['unmeasured_share'] * 100)}% of that weight is still unmeasured); "
            f"{', '.join(agree[:4]) or 'nothing'} pointing the same way")
    return direction, conf, False


# ------------------------------------------------- the evidence-weighted vote ---

# Derived from UNIVERSE_META so a name's sector is stated once, not twice.
SECTOR_OF = {tk: (sec if sec.startswith("XL") else None)
             for tk, (sec, _cap) in UNIVERSE_META.items()}
CAP_OF = {tk: cap for tk, (_sec, cap) in UNIVERSE_META.items()}

# Every ETF a desk note might plausibly name, mapped to the sector whose constituents it
# speaks for. A theme naming any of these reaches the names in that sector.
VEHICLES_OF_SECTOR = {
    "XLK": ("XLK", "SMH", "QQQ"),
    "XLC": ("XLC",),
    "XLY": ("XLY", "XHB", "ITB", "XRT"),
    "XLP": ("XLP",),
    "XLE": ("XLE", "XOP", "USO", "BNO"),
    "XLF": ("XLF", "KRE"),
    "XLV": ("XLV",),
    "XLI": ("XLI", "JETS", "IYT"),
    "XLB": ("XLB", "XME"),
    "XLU": ("XLU",),
    "XLRE": ("XLRE", "VNQ"),
}
SECTOR_NAME = {"XLK": "Tech", "XLC": "Communications", "XLY": "Discretionary",
               "XLF": "Financials", "XLV": "Health", "XLE": "Energy",
               "XLI": "Industrials", "XLP": "Staples", "XLB": "Materials",
               "XLU": "Utilities", "XLRE": "Real estate"}


def sector_read():
    """20-day sector relative strength against SPY. CONTEXT ONLY — it votes zero.

    THIS IS NOT A STOCK PICKER AND THE REPO IS EMPHATIC ABOUT IT. Sector rotation was
    tested to destruction here: 1,512 configurations, none beat buy-and-hold, and swing
    picks selected by rotation did WORSE than random at p = 0.867. `signal_weights` gives
    `sector_rotation` a hard zero and `combine()` drops it, so nothing below can leak into
    a direction call. The old swing engine did not respect that -- it moved conviction by
    +8 for a "leading" sector and -10 for a "lagging" one, which is more than it allowed
    the macro tilt, for an input measured at nothing.

    SO WHY COMPUTE IT AT ALL. Because there is a second, different question that was never
    falsified: does the tape CORROBORATE the desk's macro read? "Buy the leading sector"
    is dead. "The desk says the oil shock is the cleanest driver on the board, and energy
    is in fact leading by 14.6 points" is not a prediction, it is a consistency check on an
    argument that was made for independent reasons. When the two disagree, that is worth
    seeing before you put the trade on -- as a caution, never as a reason.
    """
    etfs = ["SPY", "XLK", "XLC", "XLY", "XLF", "XLV", "XLE", "XLI", "XLP", "XLB",
            "XLU", "XLRE"]
    try:
        px = _yf().download(etfs, period="6mo", interval="1d", progress=False,
                            auto_adjust=True)["Close"].dropna()
    except Exception as e:                                    # noqa: BLE001
        return {"rs": {}, "why": f"sector data unreadable ({type(e).__name__})"}
    if len(px) < 25:
        return {"rs": {}, "why": "not enough history for a 20-day relative strength"}

    def ret(t):
        try:
            return float(px[t].iloc[-1] / px[t].iloc[-21] - 1) * 100
        except Exception:                                     # noqa: BLE001
            return None

    spy = ret("SPY")
    if spy is None:
        return {"rs": {}, "why": "SPY unreadable"}
    rs = {}
    for t in etfs:
        if t == "SPY":
            continue
        r = ret(t)
        if r is not None:
            rs[t] = round(r - spy, 1)
    order = sorted(rs.items(), key=lambda kv: -kv[1])
    return {
        "rs": rs,
        "leaders": [k for k, _ in order[:3]],
        "laggards": [k for k, _ in order[-3:]],
        "why": ("20-day return against SPY. Measured NULL as a stock-picking signal "
                "(1,512 configurations, none beat buy-and-hold; picks worse than random "
                "at p = 0.867), so it carries zero weight in every direction call. It is "
                "here only to show whether the tape corroborates the desk's macro read."),
    }


def sector_corroboration(tk, direction, sectors):
    """Does this name's sector agree with the direction the card is taking? Context only."""
    sec = SECTOR_OF.get(tk)
    if not sec or not sectors or not sectors.get("rs"):
        return None
    val = sectors["rs"].get(sec)
    if val is None:
        return None
    agrees = (val > 0) if direction == "bullish" else (val < 0)
    name = SECTOR_NAME.get(sec, sec)
    return {
        "sector": sec, "sector_name": name, "rs": val, "agrees": agrees,
        "note": (f"{name} is {'ahead of' if val > 0 else 'behind'} SPY by {abs(val):.1f} "
                 f"points over 20 days, which {'corroborates' if agrees else 'runs against'} "
                 f"a {direction} card. Corroboration only — rotation contributes ZERO to "
                 f"the vote, because picking by it measured worse than random (p = 0.867)."),
    }


def market_signal():
    """VIX backwardation inside a golden cross — the strongest measured signal here.

    `signal_weights` calls it "the only signal that beat its base rate in every era":
    +1.3 to +1.8pp excess 21-day return with t = +3.9 / +2.8 / +2.1 across all three
    walk-forward splits. Weight 0.30, tier MEASURED. Nothing else in this repo except
    short interest has that pedigree, and it was not being read at all.

    It is computed from ^VIX and ^VIX3M directly rather than from
    `data/swing/panel.parquet`, which `refresh_signal.py` needs and which lives in the
    16 GB that is not in git. Two tickers is cheaper than a missing dependency.

    THE ENCODING IS DELIBERATELY ONE-SIDED. What was measured is the CONJUNCTION: front
    vol above three-month vol WHILE the trend is intact. Nothing was measured about the
    opposite case, so the opposite case votes ZERO rather than negative. Reading a
    symmetric claim out of a one-sided result is how a finding becomes folklore.
    """
    try:
        px = _yf().download(["^VIX", "^VIX3M", "SPY"], period="1y", interval="1d",
                            progress=False, auto_adjust=True)["Close"].dropna()
    except Exception as e:                                    # noqa: BLE001
        return {"vote": None, "why": f"VIX complex unreadable ({type(e).__name__})"}
    if len(px) < 200:
        return {"vote": None, "why": "not enough history for a 200-day average"}

    try:
        vix = float(px["^VIX"].iloc[-1])
        vix3m = float(px["^VIX3M"].iloc[-1])
        spy = px["SPY"]
        s50, s200 = float(spy.tail(50).mean()), float(spy.tail(200).mean())
    except (KeyError, ValueError, TypeError) as e:
        return {"vote": None, "why": f"VIX complex incomplete ({type(e).__name__})"}

    golden = s50 > s200
    ratio = vix / vix3m if vix3m else None
    if ratio is None:
        return {"vote": None, "why": "VIX3M is zero or missing"}
    backwardated = ratio > 1.0

    if golden and backwardated:
        vote = min((ratio - 1.0) / 0.10, 1.0)              # 10% inversion = full weight
        why = (f"VIX {vix:.1f} is above VIX3M {vix3m:.1f} ({ratio:.2f}x, backwardated) "
               f"while SPY holds its golden cross (50d {s50:.0f} > 200d {s200:.0f}). This "
               f"is the measured setup: +1.3 to +1.8pp excess over 21 days, t = +3.9/"
               f"+2.8/+2.1 in all three splits.")
    else:
        vote = 0.0
        bits = []
        if not backwardated:
            bits.append(f"VIX {vix:.1f} is BELOW VIX3M {vix3m:.1f} ({ratio:.2f}x, normal "
                        f"contango)")
        if not golden:
            bits.append(f"SPY is below its golden cross (50d {s50:.0f} vs 200d {s200:.0f})")
        why = ("; ".join(bits) + ". The measured result is about the conjunction of the "
               "two, so outside it this abstains rather than voting the other way — "
               "nothing was measured about the opposite case.")

    return {"vote": vote, "why": why, "vix": round(vix, 2), "vix3m": round(vix3m, 2),
            "ratio": round(ratio, 3), "golden_cross": golden,
            "backwardated": backwardated}


def votes_for(tk, macro_side, trend, market=None, inherited=False):
    """Every input that has a measured weight, scored through `signal_weights`.

    TWO LAYERS, AND THE DISTINCTION IS THE WHOLE DESIGN.

      THE MACRO IS A GATE. A name no desk-note theme mentions is not eligible, full stop.
      That is what stopped the old panel ranking a hundred names on momentum and always
      finding eight. It is not a vote, because a vote can be outweighed.

      EVERYTHING ELSE IS A VOTE, at the weight its evidence has earned. `signal_weights` is
      the single authority for those weights and it is unsentimental: short interest gets
      0.30 with a NEGATIVE sign (IC -0.107 at 63d), insider open buys get 0.10 because the
      sample is only 1,128 and the sign flips by era, and sector rotation gets exactly zero
      because 1,512 configurations failed to beat buy-and-hold. Nothing here can quietly
      award itself more influence than it measured.

    `combine()` also returns the share of weight that is still UNMEASURED, and every card
    prints it. Three of the inputs here — the macro read, classified flow and dark pool —
    are orthogonal to price but have never been backtested, so a card can be built almost
    entirely on things that merely sound sensible. That has to be visible.
    """
    import signal_weights as sw

    inputs = {"trend": trend["score"]}
    if macro_side:
        # A theme that names the ticker outright is stronger evidence than one inherited
        # through its sector. Voting both at ±1.00 gave every name in a sector the identical
        # +0.35 contribution, which is most of why the cards looked interchangeable.
        inputs["desk_macro"] = float(macro_side) * (0.5 if inherited else 1.0)
    # Market-wide, so it is computed ONCE per run and shared, not re-fetched per name.
    if market and market.get("vote") is not None:
        inputs["vix_backwardation"] = float(market["vote"])

    prof, err = {}, None
    try:
        import uw_endpoints
        with _UW_GATE:
            prof = uw_endpoints.profile(tk) or {}
            # A 429 comes back as an empty profile rather than an exception, which is
            # indistinguishable from "this name has no flow" — and that silently degrades the
            # vote to trend-only, the exact failure of 2026-09-04. One backoff-and-retry, and
            # if it still comes back empty the caller sees `profile_error` and can say so.
            if not prof:
                time.sleep(1.5)
                prof = uw_endpoints.profile(tk) or {}
                if not prof:
                    err = "profile came back empty twice — likely a vendor rate limit"
    except Exception as e:                                    # noqa: BLE001
        err = f"{type(e).__name__}: {str(e)[:80]}"

    # Values are MAGNITUDES. `combine()` applies each input's measured sign from the
    # registry, so negating short interest here as well would flip it back to bullish --
    # which is the exact error the registry comment warns about.
    if prof.get("flow_lean") is not None:
        inputs["flow_lean"] = max(-1.0, min(1.0, float(prof["flow_lean"])))
    if prof.get("dp_buy_share") is not None:
        inputs["dp_buy_share"] = (float(prof["dp_buy_share"]) - 0.5) * 2
    if prof.get("short_float_pct") is not None:
        sf = float(prof["short_float_pct"])
        if 0 <= sf <= 60:                    # above 60 is a vendor error; BYND printed 758%
            inputs["short_float_pct"] = min(sf / 20.0, 1.0)
    # A COUNT WAS THE WRONG MEASURE ENTIRELY, and not by a little. `profile()` returns
    # `insider_open_buys` as a count of filings with 10b5-1 excluded but WITH NO DATE FILTER,
    # so NVDA reported 36 -- scoring tanh(36/6) = 1.00, the maximum bullish value the input
    # can take -- off filings up to 2,103 days old. Every mega-cap has dozens of historical
    # Form 4s, which is also why several cards once carried an identical contribution.
    #
    # `insider_score` reads the filings themselves: routine and 10b5-1 buys dropped (Cohen/
    # Malloy/Pomorski 2012 -- routine trades carry essentially zero abnormal return), each
    # remaining buy decayed on the age of the TRANSACTION with a 12-day half-life and cut off
    # at 45 days, sized against the insider's own prior stake, and blended with the count of
    # DISTINCT buyers rather than of transactions.
    ins = None
    try:
        import insider_score
        ins = insider_score.for_ticker(tk)
    except Exception:                                         # noqa: BLE001
        ins = None
    if ins is not None:
        inputs["insider_open_buys"] = float(ins["score"])
    elif prof.get("insider_open_buys"):
        # Fallback only when the detailed endpoint is unreachable. Capped hard, because the
        # raw count is known to saturate on stale filings and must never dominate a card.
        inputs["insider_open_buys"] = min(0.3, math.tanh(float(prof["insider_open_buys"]) / 6.0))

    res = sw.combine(inputs)
    detail = []
    for name, val in sorted(inputs.items()):
        w, tier, sign = sw.weight(name)
        if w <= 0:
            continue
        detail.append({"input": name, "value": round(float(val), 3), "weight": round(w, 3),
                       "tier": tier, "sign": "+" if sign > 0 else "−",
                       "contribution": res["contrib"].get(name)})
    detail.sort(key=lambda d: -abs(d["contribution"] or 0))

    # AGREEMENT: of the weight that actually EXPRESSED A VIEW, how much points the same way
    # as the net score. A +0.30 with every voter aligned is a different animal from a +0.30
    # that is +0.9 and -0.6 cancelling, and the score alone cannot tell them apart.
    #
    # ABSTENTIONS ARE EXCLUDED FROM THE DENOMINATOR, and getting that wrong is not a detail.
    # VIX backwardation votes exactly 0.0 whenever the term structure is in contango, which
    # is most of the time, and it carries weight 0.30. Counting it in the denominator made a
    # permanent ~20% "disagreement" that nothing could offset: MPC at +0.40 scored 57%
    # agreement and NVDA at +0.34 scored 42%, and both were refused for inputs "disagreeing"
    # when in truth one large voter had simply declined to vote.
    voting = [d for d in detail if d["contribution"]]
    total_w = sum(abs(d["weight"]) for d in voting) or 1.0
    same_w = sum(abs(d["weight"]) for d in voting
                 if (d["contribution"] > 0) == (res["score"] > 0))
    agreement = same_w / total_w
    return {**res, "detail": detail, "agreement": round(agreement, 2),
            "raw": prof, "profile_error": err,
            "insider_open_buys": prof.get("insider_open_buys"),
            "insider_detail": ins,
            "short_float_pct": prof.get("short_float_pct")}


# ------------------------------------------------------ the expected-move view ---

def move_view(spot, implied_move, rv, dte, term, covers_catalyst, index_short_gamma, tk):
    """How FAR, separately from which WAY. Returns (view, why).

    Direction and magnitude are different questions and the old engine only ever asked the
    first, which is why every structure it produced was a vertical. A condor and a straddle
    are both non-directional and they are opposite bets; you cannot choose between them
    from a direction score.

    The comparison that decides it: what the week is PRICING against what this name
    actually DOES over the same number of days. Implied move comes from the ATM straddle;
    the realised comparison is the 20-day realised vol scaled to the horizon.
    """
    why = []
    if implied_move is None or not rv or not dte:
        return "normal", "no implied-move reading, so no magnitude view"

    # Realised vol is annualised; scale to this horizon in trading days.
    # Both sides are now one-sigma moves over the same horizon.
    horizon_move = rv * math.sqrt(max(dte, 1) / 252.0)
    ratio = implied_move / horizon_move if horizon_move else None
    if ratio is None:
        return "normal", "realised vol unreadable"

    why.append(f"implied one-sigma ±{implied_move:.1f}% against ±{horizon_move:.1f}% of "
               f"realised movement over the same {dte} days ({ratio:.2f}x). Both are "
               f"one-sigma: the straddle PRICE is 0.80 of that and comparing it directly "
               f"to a realised vol is what made every fair-priced name read EXPAND")

    score = 0
    if ratio > 1.25:
        score -= 1
        why.append("the market is charging a premium over what this name actually does")
    elif ratio < 0.85:
        score += 1
        why.append("the market is charging less than this name actually moves")

    if covers_catalyst:
        score += 1
        why.append("a dated event on this name lands inside the expiry")
    if term and term >= TERM_RICH:
        score -= 1
        why.append(f"front-week vol is {term:.2f}x the back month, so the premium is "
                   f"concentrated in this week and decays out of it")

    # The one measured conditioning in the repo. It is an INDEX statement, so it only
    # applies to the index proxy, not to every single name that happens to be in it.
    if index_short_gamma is not None and tk in ("QQQ", "SPY"):
        if index_short_gamma:
            score += 1
            why.append("the index is below its gamma flip, where realised range measured "
                       "1.139x implied (t = -13.2)")
        else:
            score -= 1
            why.append("the index is above its gamma flip, where realised range measured "
                       "0.843x implied (t = -13.2)")

    view = "expand" if score >= 1 else ("compress" if score <= -1 else "normal")
    return view, "; ".join(why)


# ------------------------------------------------------- the structure builder ---

def build_named(name, calls, puts, spot, dte, inc):
    """Assemble one named structure on the real ladder. Returns (struct, refusal).

    Every strike here is either snapped to a listed rung or placed by DELTA off the chain's
    own implied vols. Nothing is a rounded percentage of spot, which is the defect that
    produced a zero-width spread on a $14 stock.

    Short strikes go in the 16-30 delta band on purpose: far-OTM buying measured -45.6%
    overall but improved monotonically toward the money, reaching +26.1% in exactly that
    band. It is the only part of the wing structure this repo measured positive.
    """
    import weekly_structures as st

    cl, pu = _side_ladder(calls), _side_ladder(puts)
    if len(cl) < 2 or len(pu) < 2:
        return None, f"{name}: fewer than two strikes listed on one side of the chain"

    def quote(right, strike, buying):
        return _leg_quote(calls if right == "C" else puts, strike, buying)

    mid_delta = (SHORT_DELTA_LO + SHORT_DELTA_HI) / 2
    w = max(inc or 1.0, spot * 0.05)                  # a wing wide enough to be a spread

    def dk(target, call):
        return _delta_strike(calls if call else puts, spot, dte, target, call=call)

    atm_c, atm_p = _snap(cl, spot), _snap(pu, spot)

    if name == "call_debit":
        spec = [("C", atm_c, True, 1), ("C", _snap(cl, (atm_c or spot) + w, {atm_c}), False, 1)]
    elif name == "put_debit":
        spec = [("P", atm_p, True, 1), ("P", _snap(pu, (atm_p or spot) - w, {atm_p}), False, 1)]
    elif name == "put_credit":
        s = dk(mid_delta, call=False)
        spec = [("P", s, False, 1), ("P", _snap(pu, (s or spot) - w, {s}), True, 1)]
    elif name == "call_credit":
        s = dk(mid_delta, call=True)
        spec = [("C", s, False, 1), ("C", _snap(cl, (s or spot) + w, {s}), True, 1)]
    elif name == "iron_condor":
        sp, sc = dk(mid_delta, call=False), dk(mid_delta, call=True)
        spec = [("P", sp, False, 1), ("P", _snap(pu, (sp or spot) - w, {sp}), True, 1),
                ("C", sc, False, 1), ("C", _snap(cl, (sc or spot) + w, {sc}), True, 1)]
    elif name == "iron_butterfly":
        spec = [("P", atm_p, False, 1), ("P", _snap(pu, (atm_p or spot) - w, {atm_p}), True, 1),
                ("C", atm_c, False, 1), ("C", _snap(cl, (atm_c or spot) + w, {atm_c}), True, 1)]
    elif name == "long_straddle":
        spec = [("C", atm_c, True, 1), ("P", atm_p, True, 1)]
    elif name == "long_strangle":
        spec = [("C", dk(0.28, call=True), True, 1), ("P", dk(0.28, call=False), True, 1)]
    elif name == "reverse_condor":
        # The long-vol mirror: own the inner strikes, sell the outer ones to cap the cost.
        lc, lp = dk(0.35, call=True), dk(0.35, call=False)
        spec = [("C", lc, True, 1), ("C", _snap(cl, (lc or spot) + w, {lc}), False, 1),
                ("P", lp, True, 1), ("P", _snap(pu, (lp or spot) - w, {lp}), False, 1)]
    elif name == "call_backspread":
        # Short one nearer, long two further out. Wants a LARGE move up; bleeds if nothing
        # happens, which is why it only appears on an `expand` read.
        s = dk(0.45, call=True)
        lo = _snap(cl, (s or spot) + w, {s})
        spec = [("C", s, False, 1), ("C", lo, True, 2)]
    elif name == "put_backspread":
        s = dk(0.45, call=False)
        lo = _snap(pu, (s or spot) - w, {s})
        spec = [("P", s, False, 1), ("P", lo, True, 2)]
    else:
        return None, f"{name}: no builder"

    return st.assemble(name, spec, quote, MAX_TRADE_COST_PCT)


def _vertical(calls, puts, spot, dte, ladder, inc, bullish, debit):
    """A real, listed, non-degenerate vertical. Returns (card_bits, refusal).

    THE ZERO-WIDTH GUARD. The long and short legs are snapped separately and the short is
    forbidden from landing on the long's strike. If the ladder is too coarse to place a
    real spread on this name at this price, the card is REFUSED. That is what should have
    happened to "Buy 14P / Sell 14P".
    """
    # debit bullish -> call debit; debit bearish -> put debit
    # credit bullish -> put credit;  credit bearish -> call credit
    df = (calls if bullish else puts) if debit else (puts if bullish else calls)
    side = _side_ladder(df)
    if len(side) < 2:
        return None, "fewer than two strikes listed on the side this structure needs"

    if debit:
        long_k = _snap(side, spot)
        if long_k is None:
            return None, "no listed strike near spot"
        width_target = max(inc or 1.0, spot * 0.05)
        tgt = long_k + width_target if bullish else long_k - width_target
        short_k = _snap(side, tgt, exclude={long_k})
    else:
        short_k = _delta_strike(df, spot, dte,
                                (SHORT_DELTA_LO + SHORT_DELTA_HI) / 2, call=not bullish)
        if short_k is None:
            return None, "could not place a short strike in the 16-30 delta band"
        width_target = max(inc or 1.0, spot * 0.05)
        tgt = short_k - width_target if bullish else short_k + width_target
        long_k = _snap(side, tgt, exclude={short_k})

    if long_k is None or short_k is None:
        return None, "the listed ladder has no second strike to pair with"
    width = abs(long_k - short_k)
    if width <= 0:
        return None, "both legs snapped to the same listed strike — no spread exists here"
    if inc and width < inc - 1e-9:
        return None, f"the only pairing is narrower than the ${inc:g} listed increment"

    lq, e1 = _leg_quote(df, long_k, buying=debit)
    if e1:
        return None, e1
    sq, e2 = _leg_quote(df, short_k, buying=not debit)
    if e2:
        return None, e2

    net = (lq["price"] - sq["price"]) if debit else (sq["price"] - lq["price"])
    if net <= 0:
        return None, ("priced at or below zero on real bid/ask once each leg is filled the "
                      "way it would actually fill — no edge to take")
    if not debit and net >= width:
        return None, "the credit exceeds the width, which means the quotes are stale"

    right = "C" if (bullish == debit) else "P"
    if debit:
        legs = f"Buy {long_k:g}{right} / Sell {short_k:g}{right}"
        max_risk, max_reward = net, width - net
    else:
        legs = f"Sell {short_k:g}{right} / Buy {long_k:g}{right}"
        max_risk, max_reward = width - net, net

    # THE BINDING EXECUTION GATE. Half the bid-ask on each leg is what getting in and out
    # actually costs. Measured against the money at risk, it is the number that decides
    # whether an edge survives the trade -- which is the single lesson this repo paid the
    # most to learn.
    cost = 2 * (lq["half_spread"] + sq["half_spread"])       # in AND out, both legs
    cost_pct = (cost / max_risk * 100) if max_risk > 0 else 999
    if cost_pct > MAX_TRADE_COST_PCT:
        return None, (f"round-trip spread costs {cost_pct:.0f}% of the ${max_risk*100:.0f} at "
                      f"risk (limit {MAX_TRADE_COST_PCT:.0f}%) — the execution eats the trade")

    return {"legs": legs, "width": round(width, 2), "net": round(net, 2),
            "debit": debit, "right": right,
            "long_strike": long_k, "short_strike": short_k,
            "max_risk": round(max_risk * 100, 0), "max_reward": round(max_reward * 100, 0),
            "rr": round(max_reward / max_risk, 2) if max_risk > 0 else None,
            "cost_pct": round(cost_pct, 1),
            "worst_spread_pct": max(lq["spread_pct"], sq["spread_pct"])}, None


def _calendar(tk, spot, front_exp, front_dte, back_exp, ladder, calls_f, calls_b, bullish,
              offset=0.0):
    """Sell the expensive front week, own the cheaper back. The desk's own NVDA structure.

    "Aug. 28 ATM IV is around 82% versus ~45% by Sep. 18, making call calendars attractive
    for a contained bullish move." This fires only when the term structure is genuinely
    that shape, measured, not assumed.
    """
    if calls_b is None or not len(calls_b):
        return None, "no back-month chain to own"
    # The strike must be listed in BOTH expiries or it is not a calendar.
    shared = sorted(set(_side_ladder(calls_f)) & set(_side_ladder(calls_b)))
    if len(shared) < 1:
        return None, "the two expiries share no listed strike"
    # offset == 0 gives a true calendar (one strike, two expiries). A non-zero offset makes
    # it a DIAGONAL: the sold front strike sits further out of the money than the owned back
    # strike, so the position carries a directional tilt as well as the term-structure one.
    kb = _snap(shared, spot * (1.02 if bullish else 0.98))
    kf = _snap(shared, (kb or spot) * (1 + offset if bullish else 1 - offset)) if offset else kb
    if kb is None or kf is None:
        return None, "no listed strike near the structure's centre"
    if offset and kf == kb:
        return None, "the ladder is too coarse to offset a diagonal from the calendar strike"
    k = kb
    sq, e1 = _leg_quote(calls_f, kf, buying=False)
    if e1:
        return None, f"front leg: {e1}"
    lq, e2 = _leg_quote(calls_b, kb, buying=True)
    if e2:
        return None, f"back leg: {e2}"
    net = lq["price"] - sq["price"]
    if net <= 0:
        return None, "the back month is not more expensive than the front on real quotes"
    cost = 2 * (lq["half_spread"] + sq["half_spread"])       # in AND out, both legs
    cost_pct = cost / net * 100
    if cost_pct > MAX_TRADE_COST_PCT * 2:
        # A calendar's risk IS its debit, so the same cost is a bigger share of it. The
        # limit is doubled rather than dropped, and the number is printed on the card.
        return None, (f"round-trip spread costs {cost_pct:.0f}% of the ${net*100:.0f} debit "
                      f"— the execution eats the trade")
    return {"legs": f"Sell {kf:g}C {front_exp} / Buy {kb:g}C {back_exp}",
            "width": None, "net": round(net, 2), "debit": True, "right": "C",
            "long_strike": k, "short_strike": k,
            "max_risk": round(net * 100, 0), "max_reward": None,
            "rr": None, "calendar": True, "cost_pct": round(cost_pct, 1),
            "worst_spread_pct": max(lq["spread_pct"], sq["spread_pct"])}, None


def _exits(struct, trend, direction, spot, implied_move):
    """Target, stop, and the PRICE that proves the idea wrong.

    Not one card in the old snapshot carried any of these. A trade you cannot lose on a
    stated level is a trade you hold until it is a different, worse trade.
    """
    # Both a SENTENCE and a NUMBER. The sentence is what you read; the number is what
    # `weekly_book` compares the live mark against every cycle. Deriving the number
    # separately in the tracker would let the two drift, and then the page would say
    # "target 6.00" while the tracker closed the trade at something else.
    debit = bool(struct.get("is_debit", struct.get("debit")))
    width = struct.get("width")

    # ABSOLUTE VALUE, AND THIS IS NOT COSMETIC. `net` is signed cash: negative for a credit
    # structure, because money came in. Deriving thresholds straight from it gave a credit
    # spread a stop of -8.36 and a target of -1.88, while `weekly_book` compares against
    # |mark|, which is positive. `mark >= stop_net` was then trivially true and EVERY credit
    # structure was stopped out on the cycle it was opened. DELL's put credit spread was
    # closed and logged as a "stop" while it was up 10.3%.
    #
    # Both sides now speak the same language: the PRICE OF THE STRUCTURE, always positive.
    mag = abs(struct["net"])

    if struct.get("calendar"):
        target_net, stop_net = round(mag * 1.30, 2), round(mag * 0.50, 2)
        target = (f"close at {target_net:.2f} (+30% on the debit), or the morning after "
                  f"the catalyst")
        stop = f"close at {stop_net:.2f} (−50% of the debit)"
    elif debit and width:
        target_net, stop_net = round(width * 0.6, 2), round(mag * 0.50, 2)
        target = f"close at {target_net:.2f} (60% of the ${width:g} width)"
        stop = f"close at {stop_net:.2f} (−50% of the {mag:.2f} debit)"
    elif debit:
        # A long-premium structure with no single width — straddle, strangle, backspread.
        # There is no width to take a fraction of, so it is managed on the premium itself.
        target_net, stop_net = round(mag * 1.60, 2), round(mag * 0.50, 2)
        target = f"close at {target_net:.2f} (+60% on what you paid)"
        stop = f"close at {stop_net:.2f} (−50% of the {mag:.2f} debit)"
    else:
        target_net, stop_net = round(mag * 0.45, 2), round(mag * 2.0, 2)
        target = f"buy it back at {target_net:.2f} (keep ~55% of the {mag:.2f} credit)"
        stop = f"close at {stop_net:.2f}, twice the credit taken in"

    early = struct.get("close_early_dte")
    if early:
        # Short-premium structures do not want to be held into expiry: gamma goes vertical
        # in the last sessions and a position that was comfortable all week can round-trip
        # in an afternoon. The exit is a DATE as well as a price.
        stop += (f". Close by {early} days to expiry regardless — gamma risk on a short "
                 f"structure climbs sharply into the last sessions.")

    if direction == "bullish":
        level = trend["lo20"]
        inval = (f"a close below {level:g} — the 20-day low. Below that the tape is no "
                 f"longer confirming the macro read and the reason for the trade is gone.")
    else:
        level = trend["hi20"]
        inval = (f"a close above {level:g} — the 20-day high. Above that the tape is no "
                 f"longer confirming the macro read and the reason for the trade is gone.")

    if implied_move:
        inval += (f" The week is pricing a {implied_move:.1f}% move, so size for that, "
                  f"not for the move you want.")
    return {"target": target, "stop": stop, "invalidation": inval,
            "invalidation_level": level,
            "target_net": target_net, "stop_net": stop_net}


# ------------------------------------------------------------------- the run ---

def _premove(tk, view, rv):
    """A cheap magnitude read for the neutral gate, before the chain work is done.

    An event inside the window is the reason to expect movement, so it reads EXPAND; the
    full `move_view` runs later with the real chain and can still overrule it.
    """
    ev = (view or {}).get("event")
    return "expand" if ev else "normal"


def build_card(tk, macro, catalysts, index_short_gamma, market=None, sectors=None,
               bench=None, y10_5d=None, earn_cal=None):
    """One candidate, all the way through. Returns (card, refusal_reason)."""
    view = _macro_view(macro, tk, y10_5d=y10_5d, earn_cal=earn_cal)
    px = _hist(tk)
    if px is None:
        return None, {"ticker": tk, "why": "no usable price history"}
    trend = _trend(px, bench=bench)
    spot = trend["last"]

    own = [c for c in catalysts
           if tk.upper() in [x.upper() for x in (c.get("tickers") or [])]]

    # THE BASIS GATE MOVED AHEAD OF THE VOTE, AND THIS IS A QUOTA DECISION.
    #
    # `votes_for` spends Unusual Whales requests -- flow, dark pool and insider filings, one
    # set per name. It used to run before anything checked whether the name had a basis, which
    # was affordable at 283 names and is not at 1,255: a single cycle would spend the daily
    # quota on names that were about to be refused anyway for having no reason to trade.
    #
    # Nothing is lost by checking first. A name with no theme and no derived basis was already
    # going to be refused by `_decide`; this refuses it for the same reason, before paying for
    # the answer. The refusal text is deliberately the same so the refused panel does not
    # change its wording depending on where in the pipeline the name dropped out.
    if REQUIRE_MACRO_BASIS and not (view.get("themes") or own):
        return None, {"ticker": tk, "why": "no macro basis: the overlay names no theme for "
                                           "this ticker and the data derives none",
                      "themes": []}

    vote = votes_for(tk, view.get("side"), trend, market,
                     inherited=bool(view.get("inherited")))
    # Captured here — after the readings exist, before any gate can remove this name from the
    # sample. See the note on `_TAPE_ROWS`: recording only survivors would build a study set
    # that has already agreed with the engine.
    with _TAPE_LOCK:
        _TAPE_ROWS.append({
            "ticker": tk, "spot": trend.get("last"),
            "flow_lean": vote.get("flow_lean"),
            "dp_buy_share": vote.get("dp_buy_share"),
            "short_float_pct": vote.get("short_float_pct"),
            "insider_score": vote.get("insider_open_buys"),
        })
    # The move read is needed to judge a neutral event card, so it is computed before the
    # decision rather than after it.
    _rvd0 = _realised_vol(px["close"])
    _rv0 = _rvd0["rv"] if _rvd0 else None
    direction, conf, vol_only = _decide(view, trend, vote, own[0] if own else None,
                                        move=_premove(tk, view, _rv0))
    if direction is None:
        return None, {"ticker": tk, "why": conf, "themes":
                      [t["label"] for t in view.get("themes") or []]}

    macro_cats = [c for c in catalysts if not c.get("tickers")]
    front, fdte, exp_why = _pick_weekly(tk, own, macro_cats)
    if front is None:
        return None, {"ticker": tk, "why": exp_why}

    calls_f, puts_f = _chain(tk, front)
    if calls_f is None or not len(calls_f):
        return None, {"ticker": tk, "why": f"no readable chain for {front}"}
    ladder, inc = _ladder(calls_f, puts_f)
    if len(ladder) < 4:
        return None, {"ticker": tk, "why": f"only {len(ladder)} listed strikes for {front}"}

    iv_front = _atm_iv(calls_f, puts_f, spot)
    rvd = _realised_vol(px["close"])
    rv = rvd["rv"] if rvd else None
    rv_raw = rvd["rv_raw"] if rvd else None
    imv = _implied_move(calls_f, puts_f, spot, ladder)
    imove = imv["straddle"] if imv else None          # breakeven, for display
    isigma = imv["sigma"] if imv else None            # one-sigma, for comparison

    back, bdte = _pick_back(tk, fdte)
    calls_b = None
    iv_back = None
    if back:
        calls_b, puts_b = _chain(tk, back)
        iv_back = _atm_iv(calls_b, puts_b, spot)
    term = round(iv_front / iv_back, 2) if (iv_front and iv_back) else None

    rich = bool(iv_front and rv and iv_front > rv * IV_RICH_VS_RV)
    cheap = bool(iv_front and rv and iv_front < rv * IV_CHEAP_VS_RV)
    bullish = direction == "bullish"

    # --- the structure choice ---------------------------------------------------
    # THE MENU, NOT A COIN FLIP. The old engine had exactly one decision here -- debit or
    # credit vertical -- so every card it ever produced was a vertical, whatever the read.
    # A condor and a straddle are both non-directional and they are opposite bets; you
    # cannot pick between them from a direction score, which is why `move_view` exists.
    #
    # `weekly_structures.menu()` returns an ORDERED list for (direction x move x IV band),
    # and each candidate is attempted against the real ladder until one builds and clears
    # the liquidity and execution gates. Where the evidence says a shape loses, it sits
    # lower in that order and carries its measured number onto the card.
    import weekly_structures as st

    tried = []
    struct = None
    covers_catalyst = (exp_why or "").startswith("covers")
    band = "rich" if rich else ("cheap" if cheap else "fair")
    term_rich = bool(term and term >= TERM_RICH)

    move, move_why = move_view(spot, isigma, rv, fdte, term, covers_catalyst,
                               index_short_gamma, tk)

    # A contested direction is a magnitude trade by construction: the disagreement is
    # about which way, not about whether something happens.
    view_dir = "neutral" if vol_only else direction
    if vol_only and move == "compress":
        move = "expand"          # an event you cannot call the direction of is not a pin

    # THE MEASURED VOLATILITY READ, FETCHED HERE AND NOWHERE EARLIER.
    #
    # `market_basis.derive` used to call this, which put a paid Unusual Whales request in the
    # cheapest part of a 1,550-name pipeline. Deferring it fixed the rate limiting and then
    # left it unreachable — `vrp_hint` had no caller, so every card read "no readable
    # volatility history" and the strongest measured finding in the repo became dead code.
    #
    # This is the right place: the name has cleared its basis, its conviction and its expiry,
    # and only a name actually reporting inside the window is asked about. A handful of
    # requests a cycle instead of hundreds.
    vrp = None
    if earn_cal and tk.upper() in earn_cal:
        try:
            import earnings_vol
            vrp = earnings_vol.vrp(tk)
        except Exception:                                     # noqa: BLE001
            vrp = None
    if vrp:
        # Measured: rich premiums showed a +3.63pt seller edge against -4.30pt for cheap ones
        # across 266 events, monotone and holding in all three period splits, with implied flat
        # across buckets so it forecasts the realised move rather than labelling dear prices.
        # It moves the VOL BAND only — never the direction. The finding is about the SIZE of a
        # move, and 02_findings/earnings_vrp.md is explicit that reading it as directional is
        # inventing a claim the measurement does not make.
        if vrp["verdict"] == "rich":
            band, term_rich = "rich", True
        elif vrp["verdict"] == "cheap":
            band = "cheap"

    wanted = st.menu(view_dir, move, band, term_rich, covers_catalyst)

    for name in wanted:
        if name in ("calendar", "diagonal"):
            if calls_b is None:
                tried.append(f"{name}: no back-month chain to own")
                continue
            cand, e = _calendar(tk, spot, front, fdte, back, ladder, calls_f, calls_b,
                                bullish, offset=(0.04 if name == "diagonal" else 0.0))
            if e:
                tried.append(f"{name}: {e}")
                continue
            struct = {**cand, "name": name, "label": st.LABEL[name],
                      "evidence": st.EVIDENCE.get(name), "sells_range": False,
                      "close_early_dte": None, "breakevens": []}
            struct["legs_text"] = cand["legs"]
            break

        # Selling range while the index is short gamma is the wrong side of the only
        # dealer-gamma result that survived: realised range 1.139x implied, t = -13.2.
        if name in st.RANGE_SELLING and index_short_gamma and tk in ("QQQ", "SPY"):
            tried.append(f"{name}: refused — the index is below its gamma flip, where "
                         f"realised range measured 1.139x implied (t = -13.2)")
            continue

        cand, e = build_named(name, calls_f, puts_f, spot, fdte, inc)
        if e:
            tried.append(e)
            continue
        struct = cand
        break

    if struct is None:
        return None, {"ticker": tk, "why": "; ".join(tried) or "no structure could be built"}

    ivline = (f"Front-week IV {iv_front:.0f}% against {rv:.0f}% realised is {band}"
              if iv_front and rv else "IV unreadable")
    if term:
        ivline += f", and {term:.2f}x the {bdte}d month"
    kind = (struct["label"],
            f"{ivline}. Expected move reads {move.upper()}: {move_why}.")

    backing = _backing(view, vote, trend, conf, own, covers_catalyst, market, move, move_why)
    exits = _exits(struct, trend, direction, spot, imove)

    # A stand-alone range trade is refused outright while the index is short gamma. That
    # is the one dealer-gamma finding that survived: below the flip, realised range came
    # in at 1.139x implied, t = -13.2. Selling range into that is selling the wrong side
    # of a measured effect.
    warn = None
    if struct.get("sells_range") and index_short_gamma:
        warn = ("NDX is below its gamma flip, so dealers hedge WITH the move and realised "
                "range measured 1.139x implied (t = -13.2). This is a directional credit "
                "spread, not a range trade, but size it knowing range is expanding.")

    return {
        "ticker": tk, "spot": spot, "direction": direction,
        "expiry": front, "dte": fdte, "expiry_why": exp_why,
        "structure": kind[0], "structure_why": kind[1],
        "legs": struct.get("legs_text") or struct["legs"], "net": struct["net"],
        "width": struct.get("width"),
        "max_risk_usd": struct["max_risk"], "max_reward_usd": struct.get("max_reward"),
        "rr": struct.get("rr"), "is_debit": bool(struct.get("is_debit", struct.get("debit"))),
        "is_calendar": bool(struct.get("calendar")), "vol_only": vol_only,
        "cost_pct": struct.get("cost_pct"),
        "worst_spread_pct": struct["worst_spread_pct"],
        # The legs in machine-readable form. `weekly_book` re-prices exactly these
        # contracts every cycle, so the tracked position is the recommended one and not
        # a re-derivation that could quietly pick different strikes.
        # THE FULL LEG LIST, so `weekly_book` can re-price a four-leg condor as easily as
        # a two-leg vertical. The first version stored long_strike/short_strike/right,
        # which is a two-leg model and silently cannot describe a condor or a butterfly.
        "legs_detail": [{"right": lg["right"], "strike": lg["strike"],
                         "buying": lg["buying"], "qty": lg["qty"],
                         "entry_price": lg["price"]}
                        for lg in (struct.get("legs") if isinstance(struct.get("legs"), list)
                                   else [])],
        "long_strike": struct.get("long_strike"), "short_strike": struct.get("short_strike"),
        "right": struct.get("right"),
        "back_expiry": back if struct.get("calendar") else None,
        "iv_front": round(iv_front, 1) if iv_front else None,
        "iv_back": round(iv_back, 1) if iv_back else None,
        "term_ratio": term, "rvol": round(rv, 1) if rv else None,
        "rvol_raw": round(rv_raw, 1) if rv_raw else None,
        "implied_move_pct": round(imove, 1) if imove else None,
        "implied_sigma_pct": round(isigma, 1) if isigma else None,
        "themes": [{"label": t["label"], "stance": t.get("stance"),
                    "basis": t.get("basis"), "why": t["why"]} for t in view["themes"]],
        "backing": backing, "n_backing": len(backing),
        "macro_why": view["why"], "theme_inherited": bool(view.get("inherited")),
        "no_macro_basis": bool(view.get("no_macro_basis")),
        "derived_basis": bool(view.get("derived")),
        "cap_tier": CAP_OF.get(tk), "tape": conf,
        "vote_score": vote["score"], "vote_confidence": vote["confidence"],
        "agreement": vote.get("agreement"),
        "unmeasured_share": vote["unmeasured_share"], "vote_detail": vote["detail"],
        "insider_open_buys": vote.get("insider_open_buys"),
        "short_float_pct": vote.get("short_float_pct"),
        "move_view": move, "move_why": move_why,
        "sector": sector_corroboration(tk, direction, sectors),
        "evidence": struct.get("evidence"), "breakevens": struct.get("breakevens"),
        "close_early_dte": struct.get("close_early_dte"),
        "structure_name": struct.get("name"),
        "trend": trend, "warn": warn, "vrp": vrp, **exits,
    }, None


def _earnings_vol_rows(earn_cal, cards, limit=14):
    """The earnings-volatility table for the page, computed in the scan. Never raises.

    Built here rather than in the panel because it costs Unusual Whales requests, and a panel
    that makes network calls hangs the page under exactly the rate limiting this scan already
    runs into. Names that produced a card are asked about first: their premium has already
    been fetched this cycle, so it is free, and they are the ones the operator most needs the
    volatility read for.
    """
    try:
        import earnings_vol
        have = {}
        for c in cards or []:
            if c.get("vrp"):
                have[(c.get("ticker") or "").upper()] = c["vrp"]
        rows = []
        ordered = sorted((earn_cal or {}).values(),
                         key=lambda r: (r["days_away"], -(r.get("marketcap") or 0)))
        for row in ordered[:limit]:
            tk = row["ticker"]
            v = have.get(tk)
            if v is None:
                v = earnings_vol.vrp(tk)
            rows.append({**row, "vrp": v,
                         "read": (earnings_vol._read(v, row.get("expected_move_pct"))
                                  if v else "no readable volatility history")})
        return rows
    except Exception:                                         # noqa: BLE001
        return []


def _record_tape():
    """Write this cycle's raw Unusual Whales readings to the data lake. Never raises.

    RAW VALUES ONLY. The vote and the weighted score are this code's interpretation, and a
    study that reads them back measures the engine's opinion instead of the market's data --
    it would confirm whatever `signal_weights` already believes and call it evidence.

    Every name that reached the paid stage, not just the survivors. `_TAPE_ROWS` explains why
    at length; the short version is that a sample of winners cannot measure a signal.
    """
    try:
        import flow_tape
        with _TAPE_LOCK:
            rows = list(_TAPE_ROWS)
            _TAPE_ROWS.clear()
        n = flow_tape.record(rows)
        summary = flow_tape.snapshot_summary()
        print(f"flow tape: +{n} rows, {summary['sessions']}/{summary['min_days']} sessions")
        return summary
    except Exception as exc:                                  # noqa: BLE001
        return {"sessions": 0, "rows": 0, "ready": False,
                "why": f"could not write the tape: {type(exc).__name__}: {exc}",
                "recent": [], "min_days": 60}


def _market_open():
    try:
        import session
        return bool(session.awake())
    except Exception:                                         # noqa: BLE001
        return None


def run(force=False):
    """Every card, plus every refusal and its reason. Refusals are the useful half.

    AFTER THE BELL, THE LAST GOOD BOOK STANDS. Quotes widen the moment the market shuts,
    so a cycle that runs at 18:00 prices every leg off something nobody would trade at:
    the execution gate then rejects almost everything, and a page that had six cards at
    15:55 shows none at 18:05 for no reason connected to the market. Worse, the few that
    survive carry a net debit that is fiction.

    So outside market hours this keeps the snapshot from the last open session rather than
    replacing it, and says on the snapshot that it is doing so. `force=True` overrides,
    for testing.
    """
    if not force and _market_open() is not True:
        prev, st = snapshots.read(OUT)
        if st in ("ok", "stale") and prev and prev.get("ok") and prev.get("cards"):
            prev = dict(prev)
            prev["held_from"] = prev.get("as_of")
            prev["held_note"] = (
                "Held from the last open session. After the bell the bid-ask widens to "
                "something nobody trades at, so re-pricing these legs now would replace a "
                "real book with a fictional one.")
            snapshots.write(OUT, prev)
            print(f"weekly: market closed — held {len(prev['cards'])} card(s) "
                  f"from {prev.get('held_from')}")
            return prev

    macro, status = desk_notes.overlay()

    # THE NOTE'S AGE, NOT THE FILE'S. `snapshots.read` measures staleness from the file
    # mtime, and this overlay is rewritten by hand and by the ingest job, so touching the
    # file made a two-day-old macro read look fresh. On 2026-09-04 the engine was building
    # cards on a Sep 2 overlay whose central driver — a cooling labour market — had been
    # falsified by that morning's payroll print. Gate on when the newest NOTE was written.
    # `snapshots.read` reports "stale" off the FILE MTIME, which is the wrong clock for this
    # one: the overlay is written once and then read for days, so a Friday file is mtime-stale
    # by Sunday even though no session has passed. The session count below is strictly the
    # better test, so a stale-by-mtime overlay is accepted here and judged on sessions. Any
    # other status (absent, unreadable, wrong_version, incomplete) still blocks.
    if status == "stale" and macro:
        status = "ok"

    if status == "ok" and macro:
        missed = desk_notes.sessions_since_newest(macro)
        if missed is not None and missed > desk_notes.MAX_MISSED_SESSIONS:
            status = "stale"
            macro = None

    if status != "ok":
        why, fix = snapshots.explain(desk_notes.FILE, status)
        out = {"ok": False, "as_of": _now().strftime("%Y-%m-%d %H:%M ET"),
               "cards": [], "refusals": [], "macro_as_of": None,
               "blocked": (f"The macro overlay is {status}. {why} Note age is gated on when "
                           f"the newest desk note was WRITTEN, not on the file's timestamp, so "
                           f"rewriting the file does not make a stale read fresh."),
               "fix": fix}
        snapshots.write(OUT, out)
        print(f"weekly: BLOCKED — overlay {status}")
        return out

    cats = desk_notes.catalysts(macro, within_days=DTE_MAX)
    # THE DATED MACRO CALENDAR, merged in beside the desk's own catalysts.
    #
    # `_pick_weekly` has always known how to clear a macro print -- it takes the first expiry
    # MACRO_BUFFER_DAYS past one. That rule was correct and never fired for CPI, because the
    # only source of dated catalysts was the desk notes, and the desk wrote about the August
    # CPI print in three separate notes without ever giving its date. So the engine could not
    # see the single event it was most exposed to.
    #
    # The cost was measured, not hypothetical: on 2026-09-06 all six live cards expired
    # 2026-09-11, and CPI releases 08:30 that morning. The whole book was set to expire INTO
    # the print, with no session left to be right afterwards. Merging the calendar here moves
    # those expiries out automatically, through code that already existed.
    try:
        import macro_calendar
        known = {(str(c.get("date"))[:10], (c.get("label") or "").split()[0].upper())
                 for c in cats}
        for e in macro_calendar.upcoming(within_days=DTE_MAX + MACRO_BUFFER_DAYS):
            if (e["date"], e["label"].split()[0].upper()) not in known:
                cats.append(e)
    except Exception as exc:                                  # noqa: BLE001
        # A calendar that cannot be read must not silently drop back to "no macro events" --
        # that is the exact failure this module exists to end. Say so in the snapshot.
        print(f"weekly: macro calendar unreadable ({type(exc).__name__}: {exc})")

    # Tag the catalysts that belong to one name, so a QQQ card is not routed to AVGO's
    # earnings expiry and vice versa.
    for c in cats:
        lab = (c.get("label") or "").upper()
        c["tickers"] = [t for t in UNIVERSE if lab.startswith(t + " ")]

    # PREFETCH AND SCREEN, BEFORE ANY PER-NAME WORK.
    #
    # Two jobs in one pass. The batch download turns ~1,500 single fetches into ~13, which is
    # what makes a full-market universe affordable at all. Then the liquidity screen drops the
    # names whose weekly options are not quotable at a price worth paying -- read off the same
    # frames, so it costs nothing extra, and it happens BEFORE anything spends an option-chain
    # call or an Unusual Whales request on a name that `MAX_TRADE_COST_PCT` would reject three
    # calls later anyway.
    scan_list = list(UNIVERSE)
    t_pf = time.time()
    n_ok, n_miss = _prefetch(scan_list)
    screened_out = []
    try:
        import pandas as pd
        import universe_builder
        closes = pd.DataFrame({t: d["close"] for t, d in _HIST_CACHE.items() if "close" in d})
        vols = pd.DataFrame({t: d["volume"] for t, d in _HIST_CACHE.items() if "volume" in d})
        keep, dropped = universe_builder.liquid(closes, vols)
        # ETFs and index vehicles are kept regardless: several panels reference them by name,
        # and their liquidity is not in question.
        forced = {t for t in scan_list if CAP_OF.get(t) == "index"}
        keep_set = set(keep) | forced
        screened_out = [t for t, _dv in dropped if t not in forced]
        scan_list = [t for t in scan_list if t in keep_set]
    except Exception as exc:                                  # noqa: BLE001
        # A screen that cannot run must not quietly pass everything through to the expensive
        # stage. Say what happened and carry on with the full list rather than pretending.
        print(f"weekly: liquidity screen skipped ({type(exc).__name__}: {exc})")
    print(f"weekly: prefetched {n_ok}/{len(UNIVERSE)} in {time.time()-t_pf:.0f}s "
          f"({n_miss} missing), {len(screened_out)} screened out on liquidity, "
          f"{len(scan_list)} to scan")

    # THE EARNINGS CALENDAR, ONCE FOR THE WHOLE RUN.
    #
    # `market_basis.derive` used to look a name's earnings date up individually, which is one
    # network round trip per ticker for a fact that changes once a quarter -- 1,550 of them a
    # scan. `/api/earnings/premarket` and `/api/earnings/afterhours` take a DATE and return
    # everyone reporting that session, so the whole forward window costs about two calls per
    # session covered. Roughly thirty calls in place of fifteen hundred.
    earn_cal = {}
    try:
        import earnings_vol
        earn_cal = earnings_vol.calendar(days=DTE_MAX + 2)
        print(f"weekly: earnings calendar — {len(earn_cal)} names reporting in the window")
    except Exception as exc:                                  # noqa: BLE001
        print(f"weekly: earnings calendar unavailable ({type(exc).__name__}: {exc})")

    short_gamma = _index_short_gamma()
    # Market-wide, so once per run and shared by every name rather than refetched 24 times.
    market = market_signal()
    sectors = sector_read()
    try:
        import market_basis
        y10_5d = market_basis.y10_change_5d()
    except Exception:                                         # noqa: BLE001
        y10_5d = None
    # SPY once, shared, for the relative-strength component of every name's trend read.
    bench = None
    try:
        bpx = _hist("SPY")
        bench = bpx["close"] if bpx is not None else None
    except Exception:                                         # noqa: BLE001
        bench = None

    # PARALLEL, BECAUSE THIS IS NETWORK-BOUND, NOT CPU-BOUND. A 283-name serial scan took
    # 13m43s at 5% CPU — almost all of it waiting on yfinance round trips one at a time. The
    # work per name is independent, so a thread pool turns the wall clock into roughly the
    # slowest name rather than the sum of all of them.
    #
    # THREADS, NOT PROCESSES: the payload is IO wait, so the GIL is released for the part
    # that takes the time, and threads share the already-fetched `macro`, `market`, `sectors`
    # and `bench` without pickling them per worker.
    #
    # The worker count is deliberately modest. Unusual Whales enforces a daily request quota
    # that a wide-open pool would burn through in minutes, and yfinance is unauthenticated
    # and rate-limited by politeness rather than by contract — hammering it gets the whole
    # scan throttled, which is slower than never having parallelised.
    # ── RANK BEFORE PAYING ────────────────────────────────────────────────────────────
    # Everything in this pass is free: `_macro_view` now takes the prebuilt earnings calendar
    # and does dictionary lookups, and `_trend` reads the cached history. So the whole screened
    # universe can be judged on the cheap signals before a single paid call is made, and the
    # budget can go to the names that earned it rather than to whoever a thread reached first.
    cards, refusals = [], []
    ranked = []
    for tk in scan_list:
        px = _HIST_CACHE.get(tk)
        if px is None:
            refusals.append({"ticker": tk, "why": "no usable price history"})
            continue
        try:
            v = _macro_view(macro, tk, y10_5d=y10_5d, earn_cal=earn_cal)
            themes = v.get("themes") or []
        except Exception:                                     # noqa: BLE001
            themes = []
        own = [c for c in cats
               if tk.upper() in [x.upper() for x in (c.get("tickers") or [])]]
        if REQUIRE_MACRO_BASIS and not (themes or own):
            refusals.append({"ticker": tk, "themes": [],
                             "why": "no macro basis: the overlay names no theme for this "
                                    "ticker and the data derives none"})
            continue
        try:
            t = _trend(px, bench=bench)
            strength = abs(float(t.get("score") or 0.0))
        except Exception:                                     # noqa: BLE001
            strength = 0.0
        # A dated event and a theme naming the ticker outright are both stronger reasons to
        # spend a request than a moving average is, so they rank ahead of raw trend strength.
        score = strength + (1.0 if own else 0.0) \
            + (0.6 if any(t.get("key") == "dated_event" for t in themes) else 0.0) \
            + (0.4 if not any(t.get("derived") for t in themes) else 0.0)
        ranked.append((score, tk))

    ranked.sort(reverse=True)
    paid = [tk for _s, tk in ranked[:PAID_ANALYSIS_CAP]]
    for _s, tk in ranked[PAID_ANALYSIS_CAP:]:
        refusals.append({"ticker": tk, "themes": [],
                         "why": (f"has a basis but ranked below the paid-analysis cut "
                                 f"({PAID_ANALYSIS_CAP} of {len(ranked)} eligible). Not "
                                 f"judged and not rejected — the flow, dark-pool and insider "
                                 f"data it would need costs API requests, and the budget went "
                                 f"to higher-ranked names.")})
    print(f"weekly: {len(ranked)} names have a basis; analysing the top {len(paid)}")

    def _one(tk):
        try:
            return tk, build_card(tk, macro, cats, short_gamma, market, sectors,
                                  bench=bench, y10_5d=y10_5d, earn_cal=earn_cal)
        except Exception as e:                                # noqa: BLE001
            return tk, (None, {"ticker": tk,
                               "why": f"{type(e).__name__}: {str(e)[:120]}"})

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        for _tk, (card, why) in pool.map(_one, paid):
            (cards.append(card) if card else refusals.append(why))

    # Rank by how much is actually behind the card: a stated theme, tape confirmation,
    # a real catalyst in the window, and an execution cost that is not eating the edge.
    def rank(c):
        s = 2.0 * len(c["themes"])
        s += 1.5 if "confirmed" in (c["tape"] or "") and "not " not in c["tape"] else 0
        s += 1.5 if "covers" in (c["expiry_why"] or "") else 0
        s += 1.0 if (c["rr"] or 0) >= 1.0 else 0
        s -= (c["worst_spread_pct"] or 0) / 20.0
        return s

    cards.sort(key=rank, reverse=True)

    # ONE BOOK, NOT ONE SECTOR. Ranking globally and taking the top six handed back five
    # technology names and one other, because a theme that reaches twenty tech names
    # produces twenty candidates and they crowd everything else out. That is a
    # concentration bet wearing a diversification label.
    #
    # Best card per sector first, in rank order, then the remaining slots go to the best of
    # what is left. A sector with no eligible candidate is simply absent -- this fills slots
    # from what qualified, it never invents a card to cover a sector.
    best_per_sector, seen_sec = [], set()
    for c in cards:
        sec = SECTOR_OF.get(c["ticker"]) or "index"
        if sec not in seen_sec:
            seen_sec.add(sec)
            best_per_sector.append(c)
    chosen = best_per_sector[:MAX_CARDS]
    if len(chosen) < MAX_CARDS:
        picked = {id(c) for c in chosen}
        chosen += [c for c in cards if id(c) not in picked][:MAX_CARDS - len(chosen)]
    chosen.sort(key=rank, reverse=True)

    out = {
        "ok": True,
        "as_of": _now().strftime("%Y-%m-%d %H:%M ET"),
        "macro_as_of": macro.get("as_of"),
        "macro_age_h": round((desk_notes.age_min(macro) or 0) / 60, 1),
        "regime_line": macro.get("regime_line"),
        "catalysts": [{k: v for k, v in c.items() if k != "date_obj"} for c in cats],
        "index_short_gamma": short_gamma,
        "market_signal": market,
        "sectors": sectors,
        "earnings_vol": _earnings_vol_rows(earn_cal, chosen),
        "flow_tape": _record_tape(),
        "index_read": index_read(macro),
        "coverage": _coverage(chosen, refusals),
        "n_eligible": len(cards),
        "cards": chosen,
        "refusals": refusals,
        "n_considered": len(UNIVERSE),
    }
    snapshots.write(OUT, out)
    print(f"weekly {out['as_of']}: {len(out['cards'])} cards, "
          f"{len(refusals)} refused, from {len(UNIVERSE)} names")
    for c in out["cards"]:
        print(f"  {c['ticker']:5} {c['direction']:8} {c['expiry']} ({c['dte']}d)  "
              f"{c['structure']:38} {c['legs']}")
    for r in refusals:
        print(f"    - {r.get('ticker','?'):5} {r.get('why','')[:110]}")
    return out


def index_read(macro):
    """What the macro says about NDX ITSELF, which is usually "not directionally".

    This exists because the honest answer for the index is a REFUSAL, and a refusal that
    is silently filtered out of a list of cards looks identical to a bug. The old panel's
    failure mode was the opposite one -- it always had something to say -- so saying
    "there is no index trade here, and here is precisely why" is the point, not a gap.
    """
    p, st = snapshots.read("periscope_NDX.json")
    theme = next((t for t in desk_notes.themes(macro)
                  if t.get("key") == "ndx_multiple_hurdle"), None)
    rows = []
    if theme:
        rows.append({"k": theme["label"], "v": "", "sub": theme["why"]})

    hurdle = desk_notes.driver(macro, "us10y")
    if hurdle:
        rows.append({"k": "The hurdle", "v": f"{hurdle.get('label')} {hurdle.get('level')}",
                     "sub": hurdle.get("note")})

    if st == "ok" and p:
        spot, flip = p.get("spot"), p.get("gamma_flip")
        try:
            below = float(spot) < float(flip)
            rows.append({
                "k": "Live NDX gamma",
                "v": f"{'below' if below else 'above'} the flip",
                "sub": (f"Spot {float(spot):,.0f} against a flip at {float(flip):,.0f}, "
                        f"put wall {p.get('put_wall')}, call wall {p.get('call_wall')}. "
                        + ("Dealers are short gamma, so they hedge WITH the move and "
                           "realised range measured 1.139x implied (t = -13.2). Selling "
                           "range into that is the wrong side of the one dealer-gamma "
                           "result that survived."
                           if below else
                           "Dealers are long gamma, so moves get damped and range "
                           "compresses. That is a range statement, never a direction.")),
                "severity": "watch" if below else "info"})
        except (TypeError, ValueError):
            pass

    rows.append({
        "k": "Directional index trade this week", "v": "NONE", "severity": "stop",
        "sub": ("The two forces on NDX point opposite ways and both are real: AI earnings "
                "are converting to revenue while the 10y caps what any multiple is worth. "
                "That is a dispersion setup, so the trades are on the NAMES the overlay "
                "can argue for, and there is no index card. This repo also measured no "
                "directional edge in ~340,000 tests, so an index direction here would be "
                "invented, not found.")})
    return {"rows": rows, "has_periscope": st == "ok"}


def _backing(view, vote, trend, conf, own_cats, covers_catalyst, market, move, move_why):
    """The enumerated case for the trade. One row per thing actually standing behind it.

    Written as a list rather than a paragraph on purpose: a thesis you can count the pillars
    of is one you can watch decay. When a pillar stops being true it can be struck off, which
    a prose thesis does not let you do.
    """
    out = []
    for t in view.get("themes") or []:
        out.append({
            "kind": "macro",
            "label": t["label"],
            "detail": t["why"],
            "strength": "inherited from the sector" if view.get("inherited") else "names it directly",
        })

    voting = [d for d in vote.get("detail", []) if d.get("contribution")]
    agreeing = [d for d in voting if (d["contribution"] > 0) == (vote["score"] > 0)]
    for d in sorted(agreeing, key=lambda x: -abs(x["contribution"])):
        if d["input"] == "desk_macro":
            continue                              # already listed as the macro pillar
        out.append({
            "kind": "signal", "label": d["input"].replace("_", " "),
            "detail": (f"value {d['value']:+.2f} at weight {d['weight']:.2f} "
                       f"({d['tier']}) = {d['contribution']:+.3f}"),
            "strength": d["tier"],
        })

    out.append({
        "kind": "tape", "label": "Weekly technicals",
        "detail": (f"4w {trend.get('w4')}%, 12w {trend.get('w12')}%, "
                   f"RS vs SPY {trend.get('rs12')}%, RSI {trend.get('rsi')}, "
                   f"{trend.get('from_hi')}% from the 52-week high"),
        "strength": "measured-weak (~55-60% over weeks)",
    })

    if own_cats:
        c = own_cats[0]
        out.append({"kind": "catalyst", "label": c.get("label", "event"),
                    "detail": f"{c.get('date')} (+{c.get('days_away')}d): "
                              f"{c.get('what_it_moves', '')}",
                    "strength": "dated"})
    if market and market.get("vote"):
        out.append({"kind": "signal", "label": "VIX backwardation + golden cross",
                    "detail": market.get("why", ""), "strength": "measured"})
    out.append({"kind": "magnitude", "label": f"Expected move reads {move.upper()}",
                "detail": move_why, "strength": "derived"})
    return out


def _coverage(cards, refusals):
    """What the book actually spans, and where it cannot reach.

    A universe of 103 names across eleven sectors is only diversification if cards come out
    of more than one of them. This makes the concentration visible instead of leaving the
    reader to infer it from a list of six tickers, and it separates the two very different
    reasons a sector produces nothing: the desk never wrote about it, or its options are too
    wide to trade.
    """
    by_sector, by_cap = {}, {}
    for c in cards:
        sec = SECTOR_OF.get(c["ticker"]) or "index"
        by_sector[sec] = by_sector.get(sec, 0) + 1
        by_cap[c.get("cap_tier") or "?"] = by_cap.get(c.get("cap_tier") or "?", 0) + 1

    no_macro, illiquid, other = [], [], []
    for r in refusals:
        why = r.get("why") or ""
        tk = r.get("ticker", "?")
        if "no desk-note theme" in why:
            no_macro.append(tk)
        elif "spread" in why or "open interest" in why or "two-sided" in why:
            illiquid.append(tk)
        else:
            other.append(tk)

    sectors_present = sorted({SECTOR_OF.get(t) for t in UNIVERSE if SECTOR_OF.get(t)})
    return {
        "n_universe": len(UNIVERSE),
        "sectors_in_universe": len(sectors_present),
        "cards_by_sector": by_sector,
        "cards_by_cap": by_cap,
        "n_no_macro_basis": len(no_macro),
        "n_illiquid": len(illiquid),
        "n_other": len(other),
        "illiquid_names": sorted(illiquid),
        "note": (f"{len(UNIVERSE)} names across {len(sectors_present)} sectors and three cap "
                 f"tiers were scanned. {len(no_macro)} produced nothing because the desk "
                 f"notes never mention them or their sector — that is a limit of the MACRO "
                 f"INPUT, not of the universe, and widening the universe further will not "
                 f"fix it. {len(illiquid)} were refused on execution: their weekly options "
                 f"quote too wide to trade, which is the honest reason a small-cap weekly "
                 f"options book is hard."),
    }


def _index_short_gamma():
    """Is NDX below its gamma flip right now? None when unreadable — never assumed."""
    p, st = snapshots.read("periscope_NDX.json")
    if st != "ok" or not p:
        return None
    spot, flip = p.get("spot"), p.get("gamma_flip")
    try:
        return float(spot) < float(flip)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    run()
