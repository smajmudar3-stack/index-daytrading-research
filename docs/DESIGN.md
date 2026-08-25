# The dashboard's visual system: the dark dossier, drawn

Fifth pass. The dossier's layout survived (rail + grid, ruled sections, three type
voices); two things changed on operator feedback ("dark mode, visuals over text —
I'm staring at walls of text"):

- **Dark.** Ink on paper became light on carbon (#0c0f15). The thick printed rules
  stay, inverted: near-white rules on near-black are the signature.
- **Drawn.** Every panel that has numbers now draws them. The gamma regime is a
  gauge with the z marker on a −2.5..+2.5 band. The periscope is a price ladder:
  put wall, gamma flip, spot and call wall on one axis. The verdicts are a
  diverging record: survivors extend right in ink, the refuted left in red.
  Weights are bars (amber = fabricated prior). The evidence meters are rings.
  Gates, services and swing are chips with state squares; account, calendar and
  calibration are stat tiles. Prose is the caption, not the content.

Drawing rules: geometry that carries no severity is drawn in ink and greys;
severity is the only hue; signed RETURNS wear the desaturated up/down pair, never
severity red, because a measured loss is a measurement, not an alert. The
one-action-verb invariant now scans the drawn layer too (chips, switches, tiles,
gauges, ladders, finding bars).

The section below records the previous (paper) identity for the record.

---

## The previous identity: the paper dossier

Third identity, and the first true redesign. The first two passes were both the same
object with better finish: a dark page, one centered column, stacked rounded cards.
The operator's judgment was that it "looks literally exactly the same", and he was
right — polish is not design. So this pass changed the paradigm, not the values:

| | the dark passes | the dossier |
|---|---|---|
| layout | one centered column | fixed left rail + asymmetric two-column grid |
| surface | dark cards on darker page | warm paper, ink, printed rules; no boxes |
| chrome | top masthead + status strip | rail: nameplate, numbered nav, vitals, refresh |
| type | one sans voice | serif display / sans text / mono figures |
| verdict | 52px sans in a card | 84px serif under a kicker, set like a broadsheet lead |

The research sweep behind the palette-and-hierarchy rules is docs/DESIGN-BRIEF.md
(27 products); the editorial direction leans on the FT/NYT/Tufte category of that
research rather than the terminal category.

## The rules

1. **Colour means severity and nothing else** — the product's law, and it survived
   the reskin untouched. Printed inks: stop `#a8271d`, watch `#8a5a00`, info
   `#1d4f9e`, live `#1e6b45` on paper `#f7f4ed`. Signed numbers use a desaturated
   up/down pair that never competes with a severity.
2. **Sections, not cards.** A panel is a 2px ink rule + a small-caps mono title +
   content. Elevation does not exist on paper; hierarchy is rule weight (3px the
   decision, 2px sections, hairlines inside) and type.
3. **Three voices, one job each.** Serif for verdicts, titles and standfirsts; sans
   for running text; mono for every figure, label and source line. `tnum` global,
   proportional figures at display sizes.
4. **Provenance is printed, not coloured.** `measured` is a solid ink chip,
   `prior` an outline, `null` struck through. None of them depends on hue.
5. **Degraded states are marked, healthy ones are quiet.** An unavailable section
   gets a red rule and a wash; an empty one a dashed rule and an italic note naming
   the command that fills it; stale gets an ochre rule and its age.
6. **The vitals live in the rail**, bottom-left: freshness squares per source, the
   last cycle's outcome, and the one refresh action. The page itself carries only
   content.
7. **The grid is asymmetric on purpose.** The decision and list-heavy panels
   (verdicts, weights, the gate stack) span both columns; everything else sits
   two-up. Panel order in `panels/views.py` is layout.
8. **A sentence is never right-aligned mono**; values right-align, explanations
   wrap as muted sub-lines. And a rule never stops short of its section: a
   max-width on text must not cut the border above it (this read as a mistake
   twice before it became a rule).

## Known constraints

- Chrome's CLI headless mode has a ~500px minimum window; narrower screenshots are
  clipped viewports, not layout bugs. The single breakpoint is 980px, where the rail
  becomes a top band and the grid a single column.
- Snapshots from an older engine are refused by the panels (`idt.snapshots`), so a
  reskin can never resurrect retired wording from stale state.
- The serif stack is system (`Iowan Old Style` → `Palatino` → Georgia): no webfont,
  no build step, nothing to load.
