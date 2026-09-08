"""weekly_book.py — every weekly card that was ever issued, marked to the live chain.

WHY THIS EXISTS. `weekly_swing.run()` rebuilds its cards from scratch on every cycle. That
is correct for GENERATING ideas and useless for JUDGING them: a card that was issued on
Tuesday and is now down 40% simply stops appearing on Thursday, replaced by a fresh one at
a fresh price. The page then shows six healthy-looking suggestions forever, because losers
are deleted rather than displayed. That is the same failure the scorecard was built to
stop, one layer up.

So this module records a card the first time it is seen and never re-prices its ENTRY
again. Everything after that is a mark against that original recommendation.

HOW IT MARKS, AND WHY IT IS PESSIMISTIC ON PURPOSE
==================================================
Entry filled the way `weekly_swing` prices it: bought at the ask, sold at the bid. The exit
has to be the mirror, or the round trip is free and every number is a fiction:

    closing a DEBIT spread   sell the long at the BID, buy the short back at the ASK
    closing a CREDIT spread  buy the short back at the ASK, sell the long at the BID
    closing a CALENDAR       buy the front back at the ASK, sell the back at the BID

So the tracked P&L pays the full bid-ask twice. It will read worse than any mid-to-mid
number you see elsewhere, and that gap IS the finding this repo paid the most to learn:
a modelled credit that ignored real fills turned +3.7%/trade into break-even.

WHAT CLOSES A POSITION, IN PRIORITY ORDER
=========================================
  expired        past its expiry date. Marked at intrinsic, not at the last quote.
  invalidated    the underlying closed through the level the card named at issue.
  stop           the mark reached the stop level the card named at issue.
  target         the mark reached the target level the card named at issue.

Invalidation outranks stop and target because it is a statement about the THESIS. A trade
that hit its target after its reason evaporated was luck, and recording it as a win
teaches the wrong thing.

Nothing here places or closes a real order. It is a paper book: `risk_gates.DRY_RUN` is
True, `LIVE_AGENT` is False, and a test asserts no order-placement code exists.
"""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from idt import db as _db, paths

ET = ZoneInfo("America/New_York")
DB = paths.state("weekly_book.db")

OPEN = "open"

# (column, DDL) for anything added after the table first shipped. Append here; never edit
# the CREATE TABLE alone, or an existing book will not gain the column.
_MIGRATIONS = [("legs_json", "TEXT"), ("owned", "INTEGER DEFAULT 0"),
               ("owned_at", "TEXT"), ("fill_net", "REAL")]
CLOSED_REASONS = ("target", "stop", "invalidated", "expired")


def _con():
    """A connection with the schema in place. Returns None rather than raising.

    A tracker that takes the page down when its database is missing is worse than no
    tracker, and `panels/` cannot render an exception.
    """
    try:
        con = _db.connect(DB)
    except sqlite3.Error:
        return None
    # `idt.db.connect` deliberately does not set a row factory (it is shared by callers
    # that index positionally). Every read here is by column name, so set it locally
    # rather than changing the shared helper out from under them.
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS weekly_cards (
            id            INTEGER PRIMARY KEY,
            issued        TEXT NOT NULL,
            ticker        TEXT NOT NULL,
            direction     TEXT,
            structure     TEXT,
            legs          TEXT NOT NULL,
            expiry        TEXT NOT NULL,
            back_expiry   TEXT,
            right         TEXT,
            long_strike   REAL,
            short_strike  REAL,
            is_debit      INTEGER,
            is_calendar   INTEGER,
            entry_net     REAL,
            width         REAL,
            max_risk      REAL,
            spot_entry    REAL,
            target_net    REAL,
            stop_net      REAL,
            inval_level   REAL,
            theme         TEXT,
            status        TEXT NOT NULL DEFAULT 'open',
            cur_net       REAL,
            cur_spot      REAL,
            pnl_usd       REAL,
            pnl_pct       REAL,
            updated       TEXT,
            closed        TEXT,
            close_reason  TEXT,
            close_net     REAL,
            legs_json     TEXT,
            owned         INTEGER DEFAULT 0,
            owned_at      TEXT,
            fill_net      REAL,
            UNIQUE (ticker, expiry, legs, issued)
        )""")

    # COLUMNS ADDED AFTER THE TABLE SHIPPED. `CREATE TABLE IF NOT EXISTS` does not alter an
    # existing table, so a book created before `owned` existed kept working right up until
    # something read that column and got `no such column: owned`. Compared against
    # PRAGMA table_info rather than wrapped in a try/except, which is the same approach
    # positions.py uses and for the same reason: a swallowed exception hides a real schema
    # error behind the identical silence as "column already exists".
    have = {r[1] for r in con.execute("PRAGMA table_info(weekly_cards)").fetchall()}
    for col, ddl in _MIGRATIONS:
        if col not in have:
            con.execute(f"ALTER TABLE weekly_cards ADD COLUMN {col} {ddl}")
    con.commit()
    return con


def _now():
    return datetime.now(ET)


def _stamp():
    return _now().strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ recording ---

def record(cards):
    """Insert any card not already open. Returns how many were new.

    Dedupe is on (ticker, expiry, legs) among OPEN rows, not on the UNIQUE constraint
    alone: the engine re-issues the same structure every four hours, and each of those is
    the same recommendation, not a new one. Re-recording it would reset the entry price to
    the current mark and erase the loss.
    """
    con = _con()
    if con is None:
        return 0
    n = 0
    for c in cards or []:
        try:
            # DEDUPE ON THE IDEA, NOT ON THE EXACT STRIKES. The generator re-strikes every
            # cycle as spot drifts, so "NVDA call debit spread expiring 09-09" came back as
            # 225/235, then 230/242.5, then 230/242.5 again -- three rows for one
            # recommendation, each with its own entry price. Matching on (ticker, expiry,
            # structure) keeps it to one position and preserves the ORIGINAL entry, which is
            # the whole point of the ledger.
            dup = con.execute(
                "SELECT 1 FROM weekly_cards WHERE ticker=? AND expiry=? AND structure=? "
                "AND status=?",
                (c["ticker"], c["expiry"], c.get("structure"), OPEN)).fetchone()
            if dup:
                continue
            theme = "; ".join(t.get("label", "") for t in (c.get("themes") or []))
            con.execute("""
                INSERT OR IGNORE INTO weekly_cards
                  (issued, ticker, direction, structure, legs, expiry, back_expiry,
                   right, long_strike, short_strike, is_debit, is_calendar, entry_net,
                   width, max_risk, spot_entry, target_net, stop_net, inval_level,
                   theme, status, updated, legs_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (_stamp(), c["ticker"], c.get("direction"), c.get("structure"),
                 c["legs"], c["expiry"], c.get("back_expiry"), c.get("right"),
                 c.get("long_strike"), c.get("short_strike"),
                 1 if c.get("is_debit") else 0, 1 if c.get("is_calendar") else 0,
                 c.get("net"), c.get("width"), c.get("max_risk_usd"), c.get("spot"),
                 c.get("target_net"), c.get("stop_net"), c.get("invalidation_level"),
                 theme, OPEN, _stamp(), json.dumps(c.get("legs_detail") or [])))
            n += 1
        except sqlite3.Error as e:                            # noqa: BLE001
            print(f"weekly_book: could not record {c.get('ticker')}: {e}")
    con.commit()
    con.close()
    return n


# -------------------------------------------------------------------- marking ---

def _col(row, name, default=None):
    """A column that may not exist on this row. sqlite3.Row raises on a missing key and
    an older row (or a test fixture) legitimately will not carry every column."""
    try:
        v = row[name]
    except (KeyError, IndexError):
        return default
    return default if v is None else v


def _exit_net(ws, tk, row):
    """What closing this position would fetch RIGHT NOW, on real quotes. None if unknown.

    The mirror of the entry convention. Getting this backwards is the difference between
    a tracker and a brochure.
    """
    calls, puts = ws._chain(tk, row["expiry"])
    if calls is None:
        return None, "no readable chain for the front expiry"

    if row["is_calendar"]:
        if not row["back_expiry"]:
            return None, "calendar row has no back expiry recorded"
        bcalls, _ = ws._chain(tk, row["back_expiry"])
        if bcalls is None:
            return None, "no readable chain for the back expiry"
        front = ws._row(calls, row["long_strike"])          # same strike both legs
        back = ws._row(bcalls, row["long_strike"])
        if front is None or back is None:
            return None, "the calendar strike is no longer listed in both expiries"
        try:                                                 # buy front back, sell back
            return float(front["ask"]) * -1 + float(back["bid"]), None
        except (TypeError, ValueError):
            return None, "the calendar legs have no usable quote"

    # N LEGS, NOT TWO. The first version read long_strike/short_strike/right, which is a
    # two-leg model: it could not describe a four-leg condor or butterfly at all, so those
    # structures would have been recorded and then never markable. Iterate the stored legs.
    try:
        legs = json.loads(_col(row, "legs_json") or "[]")
    except (TypeError, ValueError):
        legs = []

    if legs:
        total = 0.0
        for lg in legs:
            df = calls if lg["right"] == "C" else puts
            r = ws._row(df, lg["strike"])
            if r is None:
                return None, f"{lg['strike']:g}{lg['right']} is no longer listed"
            try:
                # Unwinding reverses every leg: a leg you BOUGHT is now SOLD at the bid, a
                # leg you SOLD is bought back at the ask. Same convention as the entry,
                # mirrored, so the round trip pays the spread twice and reads honestly.
                px = float(r["bid"]) if lg["buying"] else float(r["ask"])
            except (TypeError, ValueError):
                return None, f"{lg['strike']:g}{lg['right']} has no usable quote"
            total += (1.0 if lg["buying"] else -1.0) * lg["qty"] * px
        return total, None

    # Rows written before legs were stored still mark on the two-leg path. Same signed
    # convention: sell the long at the bid, buy the short back at the ask, and the result
    # is the cash the close would put in your pocket (negative if it takes cash out).
    df = calls if _col(row, "right") == "C" else puts
    lo = ws._row(df, _col(row, "long_strike"))
    sh = ws._row(df, _col(row, "short_strike"))
    if lo is None or sh is None:
        return None, "a leg is no longer listed"
    try:
        return float(lo["bid"]) - float(sh["ask"]), None
    except (TypeError, ValueError):
        return None, "a leg has no usable quote"


def _intrinsic(row, spot):
    """Settlement value at expiry, from spot alone. Quotes at expiry are not usable."""
    if row["is_calendar"]:
        return None                              # the back month still has real time value
    try:
        legs = json.loads(_col(row, "legs_json") or "[]")
    except (TypeError, ValueError):
        legs = []
    if legs:
        # What the position is WORTH at settlement, which is the intrinsic of each leg
        # signed by direction — not the P&L, because the caller compares it to the entry.
        total = 0.0
        for lg in legs:
            iv = (max(0.0, spot - lg["strike"]) if lg["right"] == "C"
                  else max(0.0, lg["strike"] - spot))
            total += (1.0 if lg["buying"] else -1.0) * lg["qty"] * iv
        return total

    lo, sh = _col(row, "long_strike"), _col(row, "short_strike")
    if lo is None or sh is None:
        return None
    if _col(row, "right") == "C":
        lv, sv = max(0.0, spot - lo), max(0.0, spot - sh)
    else:
        lv, sv = max(0.0, lo - spot), max(0.0, sh - spot)
    return lv - sv                                # signed, same as the N-leg path


def _pnl(row, cur_net):
    """(usd, pct of max risk). ONE formula, because there is one sign convention.

    Both numbers are signed CASH. `entry_net` is what the position cost to put on --
    negative when it was a credit and money came in. `cur_net` is what closing it would
    pay you -- negative when closing costs money. So the P&L is always exit minus entry.

    The first version branched on debit-versus-credit and inverted the credit case, which
    was correct under the old two-leg convention and wrong under the signed one. It showed
    a DELL put credit spread at +6.9% while it was in fact down 1.43: the position had been
    opened for a 4.18 credit and would have cost 5.61 to close.
    """
    if cur_net is None:
        return None, None
    usd = (cur_net - row["entry_net"]) * 100
    risk = row["max_risk"] or 0
    return round(usd, 2), (round(usd / risk * 100, 1) if risk else None)


def _market_open():
    """True / False / None when unknowable. None is treated as closed, deliberately."""
    try:
        import session
        return bool(session.awake())
    except Exception:                                         # noqa: BLE001
        return None


def mark():
    """Re-price every open card and close the ones that are done. Returns a summary.

    A MARK IS NOT A CLOSE WHEN THE MARKET IS SHUT. After the bell, quotes widen to
    something that is not a price anyone would trade at -- the first run of this module
    marked six positions minutes after the close and showed DELL down 24% and AVGO down
    29% on nothing but the spread. Acting on those would stop out every position
    overnight, every night. So outside market hours the book still marks (you want to see
    roughly where you stand) but it will not CLOSE anything, and the mark is flagged
    indicative so the panel can say so.
    """
    con = _con()
    if con is None:
        return {"ok": False, "why": "the weekly book database could not be opened"}
    import weekly_swing as ws

    live = _market_open() is True
    rows = con.execute("SELECT * FROM weekly_cards WHERE status=?", (OPEN,)).fetchall()
    marked = closed = failed = 0
    today = _now().date()

    for r in rows:
        row = dict(r)
        tk = row["ticker"]
        px = ws._hist(tk)
        spot = float(px["close"].iloc[-1]) if px is not None and len(px) else None

        try:
            exp_date = datetime.strptime(row["expiry"], "%Y-%m-%d").date()
        except ValueError:
            exp_date = None

        reason = None
        if exp_date and exp_date < today:
            cur_net = _intrinsic(row, spot) if spot is not None else None
            reason = "expired"
            err = None if cur_net is not None else "expired with no spot to settle against"
        else:
            cur_net, err = _exit_net(ws, tk, row)

        if cur_net is None:
            failed += 1
            con.execute("UPDATE weekly_cards SET updated=?, cur_spot=? WHERE id=?",
                        (_stamp(), spot, row["id"]))
            if err:
                print(f"weekly_book: {tk} not marked — {err}")
            continue

        usd, pct = _pnl(row, cur_net)
        marked += 1

        # Expiry is a fact about the calendar and closes the position whatever the tape is
        # doing. Every OTHER close reason reads a live quote, so none of them may fire on
        # an after-hours mark.
        if reason is None and not live:
            con.execute("""UPDATE weekly_cards SET cur_net=?, cur_spot=?, pnl_usd=?,
                           pnl_pct=?, updated=? WHERE id=?""",
                        (cur_net, spot, usd, pct, _stamp(), row["id"]))
            continue

        # Invalidation first: it is a statement about the thesis, and a target reached
        # after the reason evaporated is luck, not a win.
        if reason is None and spot is not None and row["inval_level"]:
            if row["direction"] == "bullish" and spot < row["inval_level"]:
                reason = "invalidated"
            elif row["direction"] == "bearish" and spot > row["inval_level"]:
                reason = "invalidated"
        # `target_net` and `stop_net` are quoted as the structure's own price, positive for
        # a debit and positive-as-a-credit for a credit. Compare against the mark in the
        # same terms: |cur_net| is what the structure is worth right now either way.
        mark = abs(cur_net)
        if reason is None and row["stop_net"] is not None:
            if row["is_debit"] or row["is_calendar"]:
                if mark <= row["stop_net"]:
                    reason = "stop"
            elif mark >= row["stop_net"]:        # a credit costs MORE to buy back
                reason = "stop"
        if reason is None and row["target_net"] is not None:
            if row["is_debit"] or row["is_calendar"]:
                if mark >= row["target_net"]:
                    reason = "target"
            elif mark <= row["target_net"]:
                reason = "target"

        if reason:
            con.execute("""UPDATE weekly_cards SET status=?, closed=?, close_reason=?,
                           close_net=?, cur_net=?, cur_spot=?, pnl_usd=?, pnl_pct=?,
                           updated=? WHERE id=?""",
                        (reason, _stamp(), reason, cur_net, cur_net, spot, usd, pct,
                         _stamp(), row["id"]))
            closed += 1
        else:
            con.execute("""UPDATE weekly_cards SET cur_net=?, cur_spot=?, pnl_usd=?,
                           pnl_pct=?, updated=? WHERE id=?""",
                        (cur_net, spot, usd, pct, _stamp(), row["id"]))

    con.commit()
    con.close()
    return {"ok": True, "marked": marked, "closed": closed, "unmarked": failed,
            "live": live, "as_of": _stamp(),
            "mark_note": (None if live else
                          "Marked outside market hours, so these are indicative: quotes "
                          "widen after the bell and a spread marked on them reads far "
                          "worse than it would trade. Nothing is closed on such a mark.")}


# ------------------------------------------------------------------- ownership ---

def mark_entered(ticker, expiry, structure=None, fill_net=None):
    """"I took this one." Flips a paper card into a position you actually hold.

    WHY THIS MATTERS AND IS NOT COSMETIC. Every card is recorded automatically so the book
    can be scored honestly, which means the ledger is mostly trades nobody put on. Without a
    flag saying which ones are real, the exit guidance has to either shout about all of them
    or about none. This is the difference between a research log and a position blotter.

    `fill_net` is optional: pass what you actually filled at and the P&L is measured against
    YOUR fill rather than the engine's quote. Omit it and the card's entry price is used, and
    the panel says which.
    """
    con = _con()
    if con is None:
        return {"ok": False, "why": "the weekly book database could not be opened"}
    q = ("SELECT id FROM weekly_cards WHERE ticker=? AND expiry=? AND status=?"
         + (" AND structure=?" if structure else "") + " ORDER BY issued DESC LIMIT 1")
    args = [ticker, expiry, OPEN] + ([structure] if structure else [])
    row = con.execute(q, args).fetchone()
    if row is None:
        con.close()
        return {"ok": False, "why": f"no open card for {ticker} expiring {expiry}"}
    con.execute("UPDATE weekly_cards SET owned=1, owned_at=?, fill_net=COALESCE(?, fill_net) "
                "WHERE id=?", (_stamp(), fill_net, row["id"]))
    con.commit()
    con.close()
    return {"ok": True, "ticker": ticker, "expiry": expiry, "fill_net": fill_net}


def mark_exited(ticker, expiry, structure=None):
    """"I'm out." Clears the owned flag; the paper card keeps running for the record."""
    con = _con()
    if con is None:
        return {"ok": False, "why": "the weekly book database could not be opened"}
    q = ("SELECT id FROM weekly_cards WHERE ticker=? AND expiry=? AND owned=1"
         + (" AND structure=?" if structure else "") + " ORDER BY issued DESC LIMIT 1")
    args = [ticker, expiry] + ([structure] if structure else [])
    row = con.execute(q, args).fetchone()
    if row is None:
        con.close()
        return {"ok": False, "why": f"no owned position for {ticker} expiring {expiry}"}
    con.execute("UPDATE weekly_cards SET owned=0 WHERE id=?", (row["id"],))
    con.commit()
    con.close()
    return {"ok": True, "ticker": ticker, "expiry": expiry}


def exit_verdict(row, live):
    """What to do with a position you hold, right now. One of four answers.

    Ordered by which fact outranks which, the same order `mark()` closes on: the calendar
    beats the thesis, the thesis beats the price. A target reached after the reason
    evaporated was luck.
    """
    dte = _dte_left(row.get("expiry"))
    cur = row.get("cur_net")
    spot = row.get("cur_spot")
    mark = abs(cur) if cur is not None else None
    debit = bool(row.get("is_debit")) or bool(row.get("is_calendar"))

    if dte is not None and dte <= 0:
        return {"action": "CLOSE", "urgency": "stop",
                "why": "it expires today — settle it or it settles itself"}
    # A HIGH-IMPORTANCE MACRO PRINT LANDING ON OR BEFORE EXPIRY.
    #
    # Moving the expiry past a print only protects cards opened AFTER the calendar existed.
    # Six positions were already open across 2026-09-11 when the August CPI date was found,
    # and for those the fix is not the expiry, it is the CLOSING date: come out the session
    # before rather than hold a weekly through an 08:30 number with nothing left afterwards.
    #
    # It sits above the gamma rule because it is more specific -- a dated event with a known
    # time beats a general statement about the last few sessions -- and above the thesis and
    # price rules for the reason the docstring already gives.
    if dte is not None and dte >= 0:
        try:
            import macro_calendar
            for c in macro_calendar.collisions(row.get("expiry")):
                if c.get("importance") != "high":
                    continue
                if c["days_away"] <= 1:
                    return {"action": "CLOSE", "urgency": "stop",
                            "why": (f"{c['label']} lands {c['date']} at {c.get('time','08:30')}"
                                    f", and this expires {row.get('expiry')} — "
                                    + ("the same day, so there is no session left to be right "
                                       "afterwards. " if c.get("on_expiry_day")
                                       else f"only {c['days_left_after']}d after. ")
                                    + "Close into the print rather than through it.")}
                # Warned from the moment the collision is visible, not one session before.
                # A position whose expiry IS the print has a problem the day it is opened,
                # and telling the holder about it on the eve is telling them too late to do
                # anything cheap about it.
                if c.get("on_expiry_day"):
                    return {"action": "CLOSE", "urgency": "watch",
                            "why": (f"{c['label']} at {c.get('time','08:30')} on {c['date']} "
                                    f"IS this position's expiry day, {c['days_away']}d out. "
                                    f"There is no session left to recover if the print goes "
                                    f"against it. Plan the exit for the session before.")}
        except Exception:                                     # noqa: BLE001
            pass

    if row.get("close_early_dte") and dte is not None and dte <= row["close_early_dte"]:
        return {"action": "CLOSE", "urgency": "watch",
                "why": (f"{dte}d to expiry on a short-premium structure. Gamma goes vertical "
                        f"in the last sessions and a comfortable week can round-trip in an "
                        f"afternoon.")}
    if spot is not None and row.get("inval_level"):
        bad = ((row.get("direction") == "bullish" and spot < row["inval_level"])
               or (row.get("direction") == "bearish" and spot > row["inval_level"]))
        if bad:
            return {"action": "CLOSE", "urgency": "stop",
                    "why": (f"the underlying is through {row['inval_level']:g}, the level the "
                            f"card named at entry. The reason for the trade is gone, "
                            f"whatever the P&L says.")}
    if mark is not None and row.get("stop_net") is not None:
        if (debit and mark <= row["stop_net"]) or (not debit and mark >= row["stop_net"]):
            return {"action": "CLOSE", "urgency": "stop",
                    "why": f"the mark hit the stop the card named at entry "
                           f"({row['stop_net']:.2f})"}
    if mark is not None and row.get("target_net") is not None:
        if (debit and mark >= row["target_net"]) or (not debit and mark <= row["target_net"]):
            return {"action": "TAKE PROFIT", "urgency": "info",
                    "why": f"the mark reached the target the card named at entry "
                           f"({row['target_net']:.2f})"}
    if not live:
        return {"action": "HOLD", "urgency": None,
                "why": ("the market is shut, so this is an indicative mark and no exit is "
                        "signalled on it")}
    tgt = f"{row['target_net']:.2f}" if row.get("target_net") is not None else "—"
    stp = f"{row['stop_net']:.2f}" if row.get("stop_net") is not None else "—"
    return {"action": "HOLD", "urgency": None,
            "why": (f"between the levels: target {tgt}, stop {stp}, "
                    + (f"{dte}d to expiry" if dte is not None else "expiry unknown")
                    + (f", invalidates below {row['inval_level']:g}"
                       if row.get("inval_level") and row.get("direction") == "bullish"
                       else (f", invalidates above {row['inval_level']:g}"
                             if row.get("inval_level") else ""))) }


def owned_book():
    """Only the positions you said you actually hold, each with its exit verdict."""
    live = _market_open() is True
    rows = [r for r in open_book() if r.get("owned")]
    for r in rows:
        r["verdict"] = exit_verdict(r, live)
        # ALWAYS set both keys. Setting them only when a fill exists left the template
        # reading an attribute that was absent on some rows, and Jinja's Undefined is
        # `is not none`, so the guard passed and the format blew up — taking the whole
        # page to zero bytes.
        if r.get("fill_net") is not None:
            r["pnl_usd_at_fill"], r["pnl_pct_at_fill"] = _pnl(
                {**r, "entry_net": r["fill_net"]}, r.get("cur_net"))
        else:
            r["pnl_usd_at_fill"] = r["pnl_pct_at_fill"] = None
    return rows


# -------------------------------------------------------------------- reading ---

def _days_held(issued):
    try:
        d = datetime.strptime(issued[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (_now().date() - d).days


def open_book():
    """Every live recommendation with its mark. Raises nothing; returns [] on trouble."""
    con = _con()
    if con is None:
        return []
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM weekly_cards WHERE status=? ORDER BY issued DESC", (OPEN,))]
    con.close()
    for r in rows:
        r["owned"] = bool(r.get("owned"))
        r["days_held"] = _days_held(r["issued"])
        r["dte_left"] = _dte_left(r["expiry"])
        r["move_pct"] = (round((r["cur_spot"] / r["spot_entry"] - 1) * 100, 2)
                         if r.get("cur_spot") and r.get("spot_entry") else None)
    return rows


def history(limit=25):
    con = _con()
    if con is None:
        return []
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM weekly_cards WHERE status!=? ORDER BY closed DESC LIMIT ?",
        (OPEN, limit))]
    con.close()
    for r in rows:
        r["days_held"] = _days_held(r["issued"])
    return rows


def _dte_left(expiry):
    try:
        return (datetime.strptime(expiry, "%Y-%m-%d").date() - _now().date()).days
    except (ValueError, TypeError):
        return None


def record_summary():
    """The track record. Honest about being thin: n is always reported alongside.

    A 100% hit rate on two trades is not a track record, and a panel that prints the
    percentage without the count invites reading it as one.
    """
    con = _con()
    if con is None:
        return None
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM weekly_cards WHERE status!=?", (OPEN,))]
    con.close()
    if not rows:
        return {"n": 0}
    with_pnl = [r for r in rows if r.get("pnl_pct") is not None]
    wins = [r for r in with_pnl if r["pnl_pct"] > 0]
    by_reason = {}
    for r in rows:
        by_reason[r.get("close_reason") or "?"] = by_reason.get(r.get("close_reason") or "?", 0) + 1
    return {
        "n": len(rows),
        "n_scored": len(with_pnl),
        "wins": len(wins),
        "hit_rate": round(len(wins) / len(with_pnl) * 100, 1) if with_pnl else None,
        "avg_pnl_pct": round(sum(r["pnl_pct"] for r in with_pnl) / len(with_pnl), 1)
                       if with_pnl else None,
        "total_usd": round(sum(r["pnl_usd"] for r in with_pnl if r.get("pnl_usd")), 2)
                     if with_pnl else None,
        "by_reason": by_reason,
    }


def sync():
    """Record whatever the latest scan produced, then mark the whole book.

    The one entry point `scan_all` needs. Kept here rather than in `weekly_swing` so the
    generator and the ledger stay separable: re-running the generator must never be able
    to rewrite an entry price.
    """
    from idt import snapshots
    snap, st = snapshots.read("weekly_snapshot.json")
    added = 0
    if st == "ok" and snap and snap.get("ok"):
        added = record(snap.get("cards") or [])
    return {"added": added, "snapshot_status": st, **mark()}


if __name__ == "__main__":
    res = sync()
    print(f"weekly book: {res.get('added')} new, {res.get('marked')} marked, "
          f"{res.get('closed')} closed, {res.get('unmarked')} unmarked "
          f"(snapshot {res.get('snapshot_status')})")
    for r in open_book():
        net = "—" if r["cur_net"] is None else f"{r['cur_net']:.2f}"
        pnl = "" if r["pnl_pct"] is None else f"{r['pnl_pct']:+.1f}%"
        print(f"  {r['ticker']:5} {r['legs']:42} {r['expiry']}  "
              f"entry {r['entry_net']:>6.2f} -> {net:>6}  {pnl:>7}  "
              f"held {r['days_held']}d, {r['dte_left']}d left")
    hist = history(10)
    if hist:
        print("  --- closed ---")
        for r in hist:
            pnl = "" if r["pnl_pct"] is None else f"{r['pnl_pct']:+.1f}%"
            print(f"  {r['ticker']:5} {r['close_reason']:12} {pnl:>7}  "
                  f"held {r['days_held']}d")
    print(record_summary())
