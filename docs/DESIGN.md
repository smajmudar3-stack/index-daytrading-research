# The dashboard's visual system

Written 2026-08-25, after a four-track research sweep of 27 reference products:
professional trading terminals (Bloomberg, TradingView, LSEG Workspace, Unusual
Whales, Kraken Pro, Robinhood Legend, SpotGamma), modern SaaS consoles (Linear,
Vercel, Stripe, Grafana, Resend, Plausible, Railway), dark-theme design systems
(GitHub Primer, Radix Colors, Material, Apple HIG, Vercel Geist, Tailwind), and
editorial data design (FT, NYT, The Pudding, Our World in Data, Tufte, Observable,
Bloomberg UX). The stylesheet is `04_live_system/static/app.css`; this file records
the rules it follows so the next edit does not undo them by accident.

## The rules

1. **Colour means severity and nothing else.** Four levels: none, info (`#4c9ffe`),
   watch (`#fab219`), stop (`#f2685f`), each as a text/border/background ladder of
   the same hue (the Vercel badge pattern). Signed numbers use a deliberately
   desaturated up/down pair (`#6fae81`/`#c97b74`) so a green P&L never competes
   with a red gate. This is also Bloomberg's rule: green/amber/red pixels may only
   ever mean state, never decoration. The set was run through the data-viz palette
   validator against the card surface: CVD separation, normal-vision floor and 3:1
   contrast all pass.

2. **Elevation is lightness, never shadow.** Background `#0a0c10` (blue-tinted
   near-black, the TradingView/Railway move; never pure `#000`), card `#10141b`,
   raised `#151a23`. Shadows vanish on near-black, so they are not used.

3. **Borders are white at low alpha, in three tiers.** 8% for hairlines, 13% for
   emphasis, 20% for interactive edges (Grafana's 0.12/0.20, GitHub `#30363d`).
   No ad-hoc border colours.

4. **Three ink tiers.** `#e8ecf3` primary (never pure white), `#98a2b3` secondary,
   `#5c6675` faint. Hierarchy beyond that comes from size and weight, not more greys
   (the FT/NYT two-ink law, loosened by one tier for a dense console).

5. **Numbers wear the mono face; `tnum` is global.** `font-feature-settings:
   "tnum" 1` on body (The Pudding's trick) so every row, table and meter
   column-aligns. Display-size figures opt out locally: tabular sets a big number
   loose, so the hero verb uses proportional figures (the dataviz skill's rule).

6. **Exactly one hero per view, and it states the verdict.** The decision verb at
   52px/750 with negative tracking, headline-states-the-conclusion (NYT), and it is
   the only element on the site allowed to carry an action verb — enforced by
   `test_only_the_answer_panel_may_issue_an_action`.

7. **Severity keys a thin top accent on the decision card, not a full border.**
   The card should feel weighted, not alarmed.

8. **Badge the degraded state.** Service rows badge `no-key`/`outage`; healthy is
   quiet (TradingView badges delayed data, never live). Deliberate exception: the
   Evidence view badges `measured` too, because teaching provenance is that view's
   whole purpose — an unbadged number there would be ambiguous, not calm.

9. **A sentence is never right-aligned mono.** Values right-align in mono;
   explanatory text is a wrapped, muted, left-aligned sub-line. Six amber
   right-aligned sentences in the service panel taught this one.

10. **Focus is geometry, not glow**: 2px accent outline, 3px offset (Vercel Geist).
    Tables are typography: hairlines at header only, no zebra, no vertical rules
    (Tufte/Pudding). Provenance notes sit at ~0.8x body in the mono face.

## Known constraints

- Chrome's CLI headless mode has a ~500px minimum window width; a `--window-size=390`
  screenshot is a clipped 500px viewport, not a layout bug. The real breakpoint is
  700px and holds at 500.
- Snapshot JSONs written by an older engine version are refused by the panels
  (`idt.snapshots`), so a redesign never resurrects retired wording from stale state.

## Where this build deviates from the distilled brief, and why

The research distillation (docs/DESIGN-BRIEF.md) votes for a terminal-machined
identity: 0-3px radii, a 28px mono verdict figure, zebra-free 20px rows. This build
keeps a softer console identity instead, and the deviations are deliberate:

- **Radius 14px, not 3px.** This is a single-user research console read a few times a
  day, not an eight-hour terminal. The soft-card identity tested better against the
  actual content (long explanatory notes, verdict prose).
- **The hero verb is 52px sans, not a 28px mono figure.** The decision here is a WORD
  (STAND DOWN), not a number; the dataviz hero-figure rule (>=48px, same sans) fits it
  better than the terminal stat pattern.
- **`measured` keeps its badge on the Evidence view.** The brief's "healthy is silent"
  rule is right in general and applied to service health; Evidence exists to teach
  provenance, so silence there would be ambiguous rather than calm.
- **Adopted from the brief after the fact:** the sticky blurred masthead (Linear),
  and pure `#ffffff` reserved for the verdict alone (LSEG/Bloomberg: brightest =
  the thing under judgment).
