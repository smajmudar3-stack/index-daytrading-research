"""SQLite connections that survive two writers.

`scan_all` writes the same databases the dashboard reads, and all 11 connect
sites used the default: no WAL, and a 5-second lock timeout. Under concurrency
that surfaces as `database is locked` inside a render, which — before the panel
guards — took the whole page down.
"""
import os
import sqlite3

BUSY_TIMEOUT_S = 15.0


def connect(path, readonly=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(f"PRAGMA busy_timeout={int(BUSY_TIMEOUT_S * 1000)}")
    if readonly:
        con.execute("PRAGMA query_only=ON")
    return con
