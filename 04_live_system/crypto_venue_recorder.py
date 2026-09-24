"""crypto_venue_recorder.py — record best bid/ask for BTC and ETH on four US-accessible
venues every few seconds, and every cross-venue crossing net of retail taker fees.
RECORDS ONLY. Places nothing.

The claim: "price errors across 50 markets that close in seconds" are a retail edge. The
test: how often does venue A's best ask sit below venue B's best bid -- a gap you could
buy on one side and sell on the other -- and how often is that gap larger than the two
taker fees you would pay? Every poll writes every venue pair's gross and net crossing, so
the answer is a count, not an anecdote. Latency of this script is ~100 ms per venue,
which is the honest latency of a retail machine; the firms that actually do this sit at
the exchange at 0.1 ms, and any gap that survives 100 ms was already taken.

Public endpoints, no keys. Venues and retail taker fees:
    Coinbase 0.60%   Kraken 0.26%   Binance.US 0.10%   Gemini 0.40%
(these are the standard published retail tiers; a large account pays less, and the
result is reported gross as well so the reader can apply their own tier).
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("crypto_venues.db")
TICK_S = 2
FEES = {"coinbase": 0.006, "kraken": 0.0026, "binanceus": 0.001, "gemini": 0.004}
PAIRS = {"BTC": {"coinbase": "BTC-USD", "kraken": "XBTUSD", "binanceus": "BTCUSD", "gemini": "btcusd"},
         "ETH": {"coinbase": "ETH-USD", "kraken": "ETHUSD", "binanceus": "ETHUSD", "gemini": "ethusd"}}


def _get(url, timeout=4):
    req = urllib.request.Request(url, headers={"User-Agent": "idt-recorder/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def quote(venue, sym):
    if venue == "coinbase":
        j = _get(f"https://api.exchange.coinbase.com/products/{sym}/ticker")
        return float(j["bid"]), float(j["ask"])
    if venue == "kraken":
        j = _get(f"https://api.kraken.com/0/public/Ticker?pair={sym}")
        v = list(j["result"].values())[0]
        return float(v["b"][0]), float(v["a"][0])
    if venue == "binanceus":
        j = _get(f"https://api.binance.us/api/v3/ticker/bookTicker?symbol={sym}")
        return float(j["bidPrice"]), float(j["askPrice"])
    if venue == "gemini":
        j = _get(f"https://api.gemini.com/v1/pubticker/{sym}")
        return float(j["bid"]), float(j["ask"])
    raise ValueError(venue)


def con():
    c = _db.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS quotes (ts REAL, asset TEXT, venue TEXT, bid REAL, ask REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS crossings (ts REAL, asset TEXT, buy_venue TEXT, sell_venue TEXT,
                 buy_ask REAL, sell_bid REAL, gross_bp REAL, net_bp REAL)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_q ON quotes(asset, ts)")
    return c


def loop(max_secs=None):
    c = con()
    t0, n = time.time(), 0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        for asset, syms in PAIRS.items():
            q = {}
            for venue, sym in syms.items():
                try:
                    q[venue] = quote(venue, sym)
                except Exception:                             # noqa: BLE001
                    continue
            for venue, (b, a) in q.items():
                c.execute("INSERT INTO quotes VALUES (?,?,?,?,?)", (now, asset, venue, b, a))
            for bv, (_bb, ba) in q.items():
                for sv, (sb, _sa) in q.items():
                    if bv == sv or not ba or not sb:
                        continue
                    gross = sb / ba - 1
                    if gross > 0:
                        net = gross - FEES[bv] - FEES[sv]
                        c.execute("INSERT INTO crossings VALUES (?,?,?,?,?,?,?,?)",
                                  (now, asset, bv, sv, ba, sb, round(gross * 1e4, 3), round(net * 1e4, 3)))
        c.commit()
        n += 1
        if n % 150 == 0:
            k = c.execute("SELECT COUNT(*), SUM(net_bp > 0) FROM crossings").fetchone()
            print(f"{datetime.now(timezone.utc):%H:%M:%S} polls={n} gross crossings={k[0]} net>0={k[1] or 0}", flush=True)
        time.sleep(max(0.0, TICK_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
