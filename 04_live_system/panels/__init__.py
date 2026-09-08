"""The panel contract.

Every panel is a function that returns a DICT. It never returns HTML, never prints,
and never raises into the page. A template turns the dict into markup.

Why this exists. The dashboard was one 1,533-line module in which thirty-odd panel
functions each concatenated their own HTML and emoji into a single f-string, with
about 350 lines of CSS inside it. Three consequences, all of which actually happened:

  - Nothing could be tested. A panel's output was a string of markup, so the only
    assertion available was "does the page contain this substring".
  - A panel that raised took the whole page down. On a fresh clone the dashboard
    returned HTTP 000 and zero bytes, because scorecard.panel() hit a missing
    directory and render() had no guard.
  - A panel that failed quietly was indistinguishable from a panel with nothing to
    say. Both returned "". That is how six contradictory recommendations coexisted
    on one page for months without anyone being able to see it.

THE FOUR STATES. Every panel is always in exactly one, and the difference between
them is the whole point:

  ok           it has something to say
  empty        it ran fine and there is genuinely nothing (no open positions)
  stale        the data is real but too old to act on, and it says how old
  unavailable  it could not run, and it says why and what to do about it

`empty` and `unavailable` must never look the same. "No closed trades yet" and "the
trade book could not be read" lead to opposite actions.
"""
import functools
import traceback

OK = "ok"
EMPTY = "empty"
STALE = "stale"
UNAVAILABLE = "unavailable"

STATES = (OK, EMPTY, STALE, UNAVAILABLE)


def panel(key, title, state=OK, body=None, note=None, severity=None,
          fix=None, age_min=None, source=None, **extra):
    """Build a panel dict.

    key       stable identifier, used by the template loader and by tests
    title     what the operator reads at the top of the card
    state     one of STATES
    body      the panel's own data, shape defined by that panel's template
    note      one plain-English sentence under the title
    severity  None | "info" | "watch" | "stop" — see the colour rule in the
              stylesheet. Colour means severity and nothing else.
    fix       for EMPTY and UNAVAILABLE: the command or file that resolves it
    age_min   for STALE: how old the data is, in minutes
    source    where the numbers came from, so a modelled number never reads as measured
    """
    assert state in STATES, f"unknown panel state {state!r}"
    d = {
        "key": key,
        "title": title,
        "state": state,
        "body": body if body is not None else {},
        "note": note,
        "severity": severity,
        "fix": fix,
        "age_min": age_min,
        "source": source,
    }
    d.update(extra)
    return d


def unavailable(key, title, why, fix=None):
    """A panel that could not run. `why` is what broke, `fix` is what to do."""
    return panel(key, title, state=UNAVAILABLE, note=why, fix=fix, severity="stop")


def empty(key, title, why, fix=None):
    """A panel that ran and has nothing to report. This is a normal, healthy state."""
    return panel(key, title, state=EMPTY, note=why, fix=fix)


def safe(fn):
    """Decorator: a panel that raises becomes an `unavailable` card naming the error.

    One bad panel must never blank the page. It must also never disappear silently,
    which is what `except Exception: return ""` did in fourteen places.
    """
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:                     # noqa: BLE001 - deliberate catch-all
            key = getattr(fn, "_panel_key", fn.__name__)
            title = getattr(fn, "_panel_title", fn.__name__.replace("_", " ").title())
            return panel(
                key, title, state=UNAVAILABLE, severity="stop",
                note=f"This panel failed to build: {type(e).__name__}: {e}",
                fix="This is a bug, not a data problem. The traceback is in the panel body.",
                body={"traceback": traceback.format_exc()[-1500:]})
    return wrapper


def describe(key, title):
    """Attach the key and title a `safe` panel should report when it fails."""
    def deco(fn):
        fn._panel_key = key
        fn._panel_title = title
        return fn
    return deco
