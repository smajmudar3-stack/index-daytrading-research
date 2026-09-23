"""memecoin_recorder.py — record every new token that appears on DexScreener's launch feed,
its price and liquidity when first seen, and its price every few minutes for a day after.
RECORDS ONLY. Buys nothing.

THE CLAIM. "Snipe new launches, sell the pump." The retail version of that trade is: see a
token on the public feed, buy it at whatever price a retail wallet can get, hold minutes to
hours. Reported results are pure survivorship -- the winners post, the rugs do not. The
honest measurement is the DISTRIBUTION of returns from the price a retail bot would
actually see, across every launch, including the ones that go to zero.

Every POLL_S seconds: pull DexScreener's latest token profiles (the launch feed the
snipers watch), and for each token not yet in the table, fetch its pairs and record
first-seen price, liquidity, 24h volume and pair age. Every MARK_S seconds: re-price every
token first seen in the last 24 hours. `memecoin_score.py` then reports, per horizon:
median return, the share that lost more than 50% / 90%, the share that doubled, and what
"buy every launch equally" would have returned -- with liquidity as the size limit, since
a $3,000 pool cannot absorb a $500 order without moving 15% against you.

Public API, no key. ~2 requests a minute plus one per new token.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("memecoins.db")
POLL_S = 60
MARK_S = 300
CHAINS = {"solana", "base", "ethereum", "bsc"}
PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
TOKENS = "https://api.dexscreener.com/latest/dex/tokens/{addr}"


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "idt-recorder/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS tokens (
        chain TEXT, address TEXT, first_seen REAL, pair TEXT, dex TEXT, pair_created REAL,
        first_price REAL, first_liq REAL, first_vol24 REAL, PRIMARY KEY (chain, address))""")
    c.execute("""CREATE TABLE IF NOT EXISTS marks (ts REAL, chain TEXT, address TEXT,
                 price REAL, liq REAL, vol24 REAL, chg_m5 REAL, chg_h1 REAL)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_m ON marks(chain, address, ts)")
    return c


def best_pair(addr):
    d = _get(TOKENS.format(addr=addr))
    pairs = [p for p in (d.get("pairs") or []) if p.get("priceUsd")]
    if not pairs:
        return None
    pairs.sort(key=lambda p: -float(((p.get("liquidity") or {}).get("usd") or 0)))
    p = pairs[0]
    return {"pair": p.get("pairAddress"), "dex": p.get("dexId"),
            "created": (p.get("pairCreatedAt") or 0) / 1000.0,
            "price": float(p["priceUsd"]), "liq": float((p.get("liquidity") or {}).get("usd") or 0),
            "vol24": float((p.get("volume") or {}).get("h24") or 0),
            "m5": (p.get("priceChange") or {}).get("m5"), "h1": (p.get("priceChange") or {}).get("h1")}


def loop(max_secs=None):
    c = con()
    t0, last_mark, n = time.time(), 0.0, 0
    while max_secs is None or time.time() - t0 < max_secs:
        now = time.time()
        try:
            prof = _get(PROFILES)
        except Exception:                                     # noqa: BLE001
            prof = []
        new = 0
        for t in prof:
            chain, addr = t.get("chainId"), t.get("tokenAddress")
            if chain not in CHAINS or not addr:
                continue
            if c.execute("SELECT 1 FROM tokens WHERE chain=? AND address=?", (chain, addr)).fetchone():
                continue
            try:
                p = best_pair(addr)
            except Exception:                                 # noqa: BLE001
                p = None
            if not p:
                continue
            c.execute("INSERT OR IGNORE INTO tokens VALUES (?,?,?,?,?,?,?,?,?)",
                      (chain, addr, now, p["pair"], p["dex"], p["created"], p["price"], p["liq"], p["vol24"]))
            c.execute("INSERT INTO marks VALUES (?,?,?,?,?,?,?,?)",
                      (now, chain, addr, p["price"], p["liq"], p["vol24"], p["m5"], p["h1"]))
            new += 1
        if now - last_mark >= MARK_S:
            for chain, addr in c.execute("SELECT chain, address FROM tokens WHERE first_seen > ?",
                                         (now - 86400,)).fetchall():
                try:
                    p = best_pair(addr)
                except Exception:                             # noqa: BLE001
                    p = None
                if p:
                    c.execute("INSERT INTO marks VALUES (?,?,?,?,?,?,?,?)",
                              (time.time(), chain, addr, p["price"], p["liq"], p["vol24"], p["m5"], p["h1"]))
                else:
                    c.execute("INSERT INTO marks VALUES (?,?,?,?,?,?,?,?)",
                              (time.time(), chain, addr, None, None, None, None, None))
                time.sleep(0.25)
            last_mark = time.time()
        c.commit()
        n += 1
        if n % 10 == 0:
            k = c.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            print(f"{datetime.now(timezone.utc):%H:%M:%S} polls={n} tokens={k} new_this_poll={new}", flush=True)
        time.sleep(max(0.0, POLL_S - (time.time() - now)))


if __name__ == "__main__":
    loop(float(sys.argv[1]) if len(sys.argv) > 1 else None)
