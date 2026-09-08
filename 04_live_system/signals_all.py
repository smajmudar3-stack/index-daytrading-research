"""Run all signal engines for the dashboard (launchd + /refresh point here).

This file did not import at all until mes_signals was moved here from
05_studies/, which meant the documented entry point of the live system was the
one thing in it that could not run.

The work sits under a main guard so that importing this module — which is what
a test or a health check would do — does not fire two network scans.
"""
import intraday_live
import mes_signals


def main():
    mes_signals.run()
    intraday_live.run()


if __name__ == "__main__":
    main()
