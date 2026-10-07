"""pumpfun_trades_recorder.py — every TRADE on every new pump.fun token for its first
TRACK_S seconds, with the wallet that made it, from PumpPortal's free websocket; plus
every trade by a watch-list of wallets (the GMGN leaderboard names Sholo copies) and
every migration. RECORDS ONLY. Buys nothing.

WHY. The first two memecoin recorders see prices every minute or every twenty; neither
sees WHO traded. Every strategy Sholo named — copy the smart money, follow the KOL,
snipe the launch, scalp the first wave, avoid the bundled dev — is a claim about wallets
and seconds, and can only be tested on a tape of individual trades with wallet addresses
and slot-level timing. PumpPortal streams exactly that for free (`wss://pumpportal.fun/api/data`):
  subscribeNewToken      every mint: creator wallet, the dev's own first buy (tokens and
                         SOL), the curve's starting state, name/symbol/uri
  subscribeTokenTrade    every buy/sell on named mints: trader wallet, SOL and token
                         amounts, the curve state after the trade, the signature
  subscribeAccountTrade  every trade by named wallets
  subscribeMigration     the moment a curve completes and the pool opens
Each new mint is tracked for TRACK_S seconds then unsubscribed, so the subscription list
stays at a few hundred. NOTE (2026-10-06): PumpPortal's new-token and migration streams are
free; the per-token TRADE stream is metered (0.01 SOL per 10k events, paid from a PumpPortal
account) and delivered nothing on the free tier in testing. The creates (with the dev's
first buy) and migrations ARE recorded; the trade tape needs either the metered stream or a
Helius/Bitquery subscription — see docs/briefs/memecoin-data-stack.md. With that tape, `memecoin_tape.py` (next) can replay: the dev's
first buy as a factor, the first-N-buyers' PnL, time-to-first-sell by the creator, buy/sell
imbalance by second, bundled wallets (many buys in the creation slot), the copier's fill
price X seconds after a watched wallet's fill, and any exit rule at tick resolution.

Watch-list: one wallet address per line in `data/watch_wallets.txt` (git-ignored, Sholo's
to fill from GMGN); reloaded every minute. Tables: `creates`, `trades`, `migrations`.
"""
import asyncio
import json
import sys
import time
from datetime import datetime, timezone

from idt import db as _db
from idt import paths

DB = paths.state("pumpfun_trades.db")
WATCH = paths.state("watch_wallets.txt")
WS = "wss://pumpportal.fun/api/data"
TRACK_S = 1800
MAX_TRACKED = 400


def con():
    c = _db.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS creates (
        mint TEXT PRIMARY KEY, ts REAL, sig TEXT, creator TEXT, name TEXT, symbol TEXT, uri TEXT,
        initial_buy_tokens REAL, initial_buy_sol REAL, v_tokens REAL, v_sol REAL, mcap_sol REAL, curve TEXT, pool TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS trades (
        ts REAL, mint TEXT, sig TEXT, trader TEXT, side TEXT, sol REAL, tokens REAL, v_tokens REAL, v_sol REAL,
        mcap_sol REAL, new_token_balance REAL, pool TEXT, src TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS migrations (ts REAL, mint TEXT, sig TEXT, pool TEXT, raw TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS ix_t_mint ON trades(mint, ts)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_t_trader ON trades(trader, ts)")
    return c


def load_watch():
    try:
        with open(WATCH, encoding="utf-8") as fh:
            return sorted({ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")})
    except OSError:
        return []


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


async def run(max_secs=None):
    import websockets
    c = con()
    t0 = time.time()
    tracked = {}                                                   # mint -> subscribed_at
    watched = []
    last_watch, n_tr, n_cr = 0.0, 0, 0
    while max_secs is None or time.time() - t0 < max_secs:
        try:
            async with websockets.connect(WS, open_timeout=20, ping_interval=20, max_queue=4096) as ws:
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
                await ws.send(json.dumps({"method": "subscribeMigration"}))
                if tracked:
                    await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": list(tracked)}))
                watched = load_watch()
                if watched:
                    await ws.send(json.dumps({"method": "subscribeAccountTrade", "keys": watched}))
                last_log = time.time()
                while max_secs is None or time.time() - t0 < max_secs:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    except asyncio.TimeoutError:
                        continue
                    now = time.time()
                    try:
                        m = json.loads(raw)
                    except ValueError:
                        continue
                    tx = m.get("txType")
                    if tx == "create":
                        mint = m.get("mint")
                        c.execute("INSERT OR IGNORE INTO creates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (mint, now, m.get("signature"), m.get("traderPublicKey"), m.get("name"), m.get("symbol"),
                                   m.get("uri"), _f(m.get("initialBuy")), _f(m.get("solAmount")), _f(m.get("vTokensInBondingCurve")),
                                   _f(m.get("vSolInBondingCurve")), _f(m.get("marketCapSol")), m.get("bondingCurveKey"), m.get("pool")))
                        n_cr += 1
                        if mint and mint not in tracked and len(tracked) < MAX_TRACKED:
                            tracked[mint] = now
                            await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": [mint]}))
                    elif tx in ("buy", "sell"):
                        trader = m.get("traderPublicKey")
                        c.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                  (now, m.get("mint"), m.get("signature"), trader, tx, _f(m.get("solAmount")), _f(m.get("tokenAmount")),
                                   _f(m.get("vTokensInBondingCurve")), _f(m.get("vSolInBondingCurve")), _f(m.get("marketCapSol")),
                                   _f(m.get("newTokenBalance")), m.get("pool"), "watch" if trader in watched else "token"))
                        n_tr += 1
                    elif m.get("mint") and (tx == "migrate" or "migrat" in str(tx or "").lower() or m.get("pool") in ("pump-amm", "pumpswap")):
                        c.execute("INSERT INTO migrations VALUES (?,?,?,?,?)", (now, m.get("mint"), m.get("signature"), m.get("pool"), raw[:2000]))
                    # expire tracked mints
                    old = [k for k, v in tracked.items() if now - v > TRACK_S]
                    if old:
                        await ws.send(json.dumps({"method": "unsubscribeTokenTrade", "keys": old}))
                        for k in old:
                            del tracked[k]
                    if now - last_watch > 60:
                        w2 = load_watch()
                        if w2 != watched:
                            if watched:
                                await ws.send(json.dumps({"method": "unsubscribeAccountTrade", "keys": watched}))
                            if w2:
                                await ws.send(json.dumps({"method": "subscribeAccountTrade", "keys": w2}))
                            watched = w2
                        last_watch = now
                    if now - last_log > 60:
                        c.commit()
                        print(f"{datetime.now(timezone.utc):%H:%M:%S} creates={n_cr} trades={n_tr} tracked={len(tracked)} watched={len(watched)}", flush=True)
                        last_log = now
        except Exception as e:                                     # noqa: BLE001
            c.commit()
            print(f"{datetime.now(timezone.utc):%H:%M:%S} reconnect after {type(e).__name__}: {str(e)[:80]}", flush=True)
            await asyncio.sleep(5)
    c.commit()


if __name__ == "__main__":
    asyncio.run(run(float(sys.argv[1]) if len(sys.argv) > 1 else None))
