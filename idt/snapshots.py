"""Snapshot schemas — the interface between the engines and the dashboard.

About 26 JSON files under STATE_ROOT are the entire contract between the engines that
compute and the page that renders, and they had no schema and no version. Two things
that actually happened because of that:

  1. A lapsed Unusual Whales subscription returned nulls where numbers were expected.
     A `None` reached a `:+` format string and took the whole page down. uw_client's
     comments describe it at length: ".get(key, default) does NOT protect against a key
     that exists with a None value".

  2. A snapshot written BEFORE a code fix keeps serving the old wording AFTER it. When
     the engines stopped emitting the refuted "buy premium" advice, the rendered page
     still contained it, from a periscope_SPX.json written twenty minutes earlier. The
     code was clean and the screen was not.

The second is the one a version field fixes. A snapshot whose schema version does not
match what the reader expects is not stale data to be shown with a warning; it is data
written by code that no longer exists, and it must be refused.

Deliberately not a validation framework. This is a version stamp, a required-key check
and a null check on the fields that must not be null, in about a hundred lines with no
dependency. The repo runs anywhere `node`... anywhere `python` runs, and it stays that way.
"""
import json
import os
import time

from . import paths

# Bump a schema's version when the MEANING of a field changes, not when one is added.
#
# periscope 2: `signal` changed from a directional order ("BUY PUTS") to a regime state
#              ("SHORT GAMMA · RANGE EXPANDS"), and `quality` (a fabricated 0-100
#              conviction) became `position` (measured geometry). A version-1 snapshot
#              read by version-2 code would print a retired recommendation.
# gex 2:       `stance` changed from buy_premium/sell_premium (an order) to
#              wide_range/tight_range (a forecast), and `direction_playbook` became
#              `direction_findings`.
SCHEMAS = {
    "periscope": {
        "version": 2,
        "files": ("periscope_SPX.json", "periscope_NDX.json"),
        "required": ("as_of", "ok"),
        "required_when_ok": ("spot", "symbol"),
        "not_null": ("spot",),
        "max_age_min": 20,
    },
    "gex": {
        "version": 2,
        "files": ("gex_snapshot.json",),
        "required": ("as_of", "regime", "stance"),
        "required_when_ok": (),
        "not_null": ("stance",),
        "max_age_min": 90,
    },
    "master_call": {
        "version": 1,
        "files": ("master_call.json",),
        "required": ("ok",),
        "required_when_ok": ("action",),
        "not_null": (),
        "max_age_min": 30,
    },
    "gap": {
        "version": 1,
        "files": ("gap_snapshot.json",),
        "required": ("as_of",),
        "required_when_ok": (),
        "not_null": (),
        "max_age_min": 30,
    },
    "swing": {
        "version": 1,
        "files": ("swing_snapshot.json",),
        "required": ("as_of",),
        "required_when_ok": (),
        "not_null": (),
        "max_age_min": 1500,
    },
}

VERSION_KEY = "schema_version"


def schema_for(filename):
    for name, spec in SCHEMAS.items():
        if filename in spec["files"]:
            return name, spec
    return None, None


def write(filename, payload):
    """Stamp and write a snapshot atomically.

    Atomic because the dashboard reads these while scan_all writes them, and a
    half-written file is a JSONDecodeError in a render.
    """
    name, spec = schema_for(filename)
    if spec:
        payload = dict(payload)
        payload[VERSION_KEY] = spec["version"]
    target = paths.state(filename)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    os.replace(tmp, target)
    return target


def read(filename):
    """A snapshot and its verdict: (payload, status).

    status is one of:
      ok            usable
      absent        never written
      unreadable    present but not valid JSON
      wrong_version written by code that no longer exists, so REFUSE it
      incomplete    a required field is missing or null
      stale         valid, but older than this schema allows

    A caller must be able to tell these apart. `absent` and `unreadable` lead to
    different fixes, and `wrong_version` must never be rendered with a stale warning
    as though the numbers were merely old.
    """
    name, spec = schema_for(filename)
    p = os.path.join(paths.STATE_ROOT, filename)
    if not os.path.exists(p):
        return None, "absent"
    try:
        with open(p, encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None, "unreadable"
    if not isinstance(payload, dict):
        return None, "unreadable"
    if not spec:
        return payload, "ok"

    got = payload.get(VERSION_KEY)
    if got is not None and got != spec["version"]:
        return payload, "wrong_version"
    if got is None and spec["version"] > 1:
        # Unstamped, and this schema has moved on. An unstamped periscope predates the
        # change that removed the retired directional verb, so it is not merely old.
        return payload, "wrong_version"

    for k in spec["required"]:
        if k not in payload:
            return payload, "incomplete"
    if payload.get("ok", True):
        for k in spec["required_when_ok"]:
            if k not in payload:
                return payload, "incomplete"
        for k in spec["not_null"]:
            if payload.get(k) is None:
                return payload, "incomplete"

    age = (time.time() - os.path.getmtime(p)) / 60
    if age > spec["max_age_min"]:
        return payload, "stale"
    return payload, "ok"


def explain(filename, status):
    """One plain-English sentence a panel can show, and the fix."""
    name, spec = schema_for(filename)
    return {
        "absent": (f"{filename} has never been written.", "idt refresh"),
        "unreadable": (f"{filename} is present but is not valid JSON.",
                       f"Delete {filename} and run: idt refresh"),
        "wrong_version": (
            f"{filename} was written by an older version of the engine "
            f"(schema {name} v{spec['version'] if spec else '?'} expected). Its fields no "
            f"longer mean what this page assumes, so it is being refused rather than shown.",
            f"Delete {filename} and run: idt refresh"),
        "incomplete": (f"{filename} is missing a field this page needs.", "idt refresh"),
        "stale": (f"{filename} is older than this data is allowed to be.", "idt refresh"),
        "ok": ("", ""),
    }.get(status, (f"{filename}: unknown status {status}.", "idt audit"))
