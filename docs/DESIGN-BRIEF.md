# Research-distilled design brief (reference)

Produced 2026-08-25 by a four-track sweep of 27 dashboard products, then distilled
by a synthesis pass. This is the RAW brief as distilled. The build follows it with
the deviations recorded at the end of docs/DESIGN.md.

---

# Design brief: dark-theme options-trading research console

One CSS file, server-rendered HTML, no framework. Every value below is exact and final. The governing rule: **color means severity and nothing else.** Structure is luminance; hierarchy is brightness; chroma is a verdict.

---

## 1. Surfaces & elevation

Cold blue-tinted near-black (TradingView ramp), never pure black. Exactly three surface levels, stepped by lightness. No shadows on anything in-flow.

```css
:root {
  --bg:        #131722;   /* page canvas */
  --card:      #1e222d;   /* every card, panel, input */
  --raised:    #2a2e39;   /* popovers, menus, sticky header, active states */

  --ink: 210 214 228;     /* ONE ink drives all text and borders (Grafana pattern) */

  --line-quiet:  rgb(var(--ink) / 0.08);  /* table row dividers, internal rules */
  --line:        rgb(var(--ink) / 0.14);  /* card edges, static input borders */
  --line-strong: rgb(var(--ink) / 0.25);  /* interactive hover borders, selected */

  --hover-wash:  rgb(var(--ink) / 0.05);  /* row + control hover fill */
  --select-wash: rgb(var(--ink) / 0.08);  /* selected row fill */
}
```

- **Card recipe:** `background: var(--card); border: 1px solid var(--line);` and nothing else. Elevation is the +lightness step plus the 1px ring (GitHub Primer / Tailwind dark pattern). Nesting a card inside a card: keep `--card` bg, promote the border to `--line-strong`.
- **Radius scale:** `0` on tables, meters, and the status bar; `3px` on cards, chips, inputs (Pudding's single token). Nothing larger. No pills.
- **Glow vs border:** never glow. The single permitted shadow token is for floating layers only (popover, menu): `box-shadow: 0 8px 24px rgb(0 0 0 / 0.4)` plus its normal 1px border. Focus is geometry, not glow: `outline: 2px solid #50a8ff; outline-offset: 2px;` with no blur (Vercel spec).
- Sticky header: `background: rgb(19 23 34 / 0.85); backdrop-filter: blur(20px); border-bottom: 1px solid var(--line);` (Linear).

## 2. Type

```css
--sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
body { font-variant-numeric: tabular-nums lining-nums; }  /* Pudding: on body, site-wide */
```

**Rule: labels proportional, figures mono, always** (Kraken/Robinhood pairing). Every number that means anything is set in `--mono` at the same size as the sans text beside it.

| Role | Size / line | Face | Weight | Tracking | Ink |
|---|---|---|---|---|---|
| Hero verdict number | 28px / 1.1 | mono | 600 | -0.8px | `#ffffff` (reserved, see below) |
| Big stat | 20px / 1.2 | mono | 500 | -0.3px | primary |
| Card / section title | 15px / 1.3 | sans | 600 | -0.2px | primary |
| Body | 13px / 20px | sans | 400 | 0 | primary |
| Table & key-value data | 12px / 16px | mono (figures), sans (words) | 400 | 0 | primary |
| Caption / meta / source | 11px / 16px | sans | 400 | 0 | secondary |
| Label / kicker / chip / column header | 11px | mono | 500 | +0.06em, `text-transform: uppercase` | muted |

- Text tiers, all from one ink (never a hand-picked third grey): primary `rgb(var(--ink))`, secondary `rgb(var(--ink) / 0.67)`, muted `rgb(var(--ink) / 0.45)`, disabled/null `rgb(var(--ink) / 0.30)`.
- **Pure `#ffffff` is reserved for the figure currently under judgment** - the LSEG/Bloomberg move: brightest = focus. Everything else caps at primary ink.
- Weights 400/500/600 only. Negative tracking only at 15px and above; table text stays at 0.
- Numerals right-aligned in every table column; words left-aligned. No centered columns.

## 3. Color

Total chromatic budget for the entire console: **five values.** Blue, amber, stop-red, down-red, up-teal. Nothing else may carry hue.

**Severity chips** - three-value ladder per state, same hue for tint, border, and text (Vercel dark badge values, verbatim):

| State | Background | Border | Text |
|---|---|---|---|
| neutral | `rgb(var(--ink) / 0.06)` | `rgb(var(--ink) / 0.14)` | `rgb(var(--ink) / 0.67)` |
| info | `#06193a` | `#003771` | `#50a8ff` |
| watch | `#291800` | `#573200` | `#ff9900` |
| stop | `#330a11` | `#6f101b` | `#ff5e63` |

Chip anatomy: mono 10px uppercase, 500, padding `2px 6px`, radius 3px, 1px border. Severity is the hue; **urgency is the fill** (Kraken): the ladder above is the everyday "low" form. Reserve one "high" form for genuine alarms only (e.g. HALT): solid fill `#d11d45` (stop) / `#ffcd60` (watch), text `#0d0d0d`. If a screen shows more than one high chip, the design has failed.

**Signed numbers (up/down):** up `#089981`, down `#f23645` (TradingView's CVD-tuned pair - teal pulled away from red deliberately). These two colors appear **only on the numeral, delta, or arrow itself** - never as fills, borders, backgrounds, or any other text. Zero/unchanged: muted ink, no color. Green belongs exclusively to "up"; never use it for success, health, or confirmation. Down-red (`#f23645`, bare numeral) and stop-red (`#ff5e63`, chip) are distinguished by form: direction is a colored number, severity is a chip.

**Interaction accent:** `#50a8ff` does double duty as link color and focus ring, sharing the info family so the hue count stays at five.

**Provenance badges** - achromatic, because color is spent on severity:
- **measured** - no badge at all. Bare default text. Healthy is silent (TradingView: live data has no chip).
- **prior** - outline chip: transparent bg, border `rgb(var(--ink) / 0.20)`, text `rgb(var(--ink) / 0.67)`, mono 10px uppercase "PRIOR".
- **null** - filled chip: bg `rgb(var(--ink) / 0.06)`, text `rgb(var(--ink) / 0.40)`, "NULL"; the associated value is also dimmed to `rgb(var(--ink) / 0.45)`.

## 4. Spacing & density

Stripe's scale, literally, as the only spacing tokens: `0, 2, 4, 8, 16, 24, 32, 48px`. The 2px and 4px steps are what make dense chips and cells feel machined instead of cramped.

- Page gutter 24px; gap between cards 16px; gap between page sections 24px.
- Card padding 16px; card title to card body 8px.
- **Tables (Pudding's typographic table, verbatim):** horizontal rules only - `thead { border-bottom: 1px solid var(--line-quiet) }`, `tfoot { border-top: 1px solid var(--line-quiet) }`, row dividers `--line-quiet`. No vertical rules, no zebra striping. Cell padding `4px 8px`, row min-height 24px; dense variant `2px 8px` / 20px. Header row: 11px mono uppercase muted. Row hover: `--hover-wash` fill, no border change.
- Key-value rows (levels tables, greeks): 28px, label sans 12px secondary left, value mono 12px primary right.
- Status bar: 28px tall, canvas bg, 1px `--line-quiet` bottom border, mono 11px, items on 16px gaps.
- Data regions dense, chrome generous (Stripe): tight inside the card, 16-24px of air around it.

## 5. Signature moves

1. **The verdict card** (NYT headline-states-the-finding + Stripe metric block + LSEG white-is-current). The hero card's title is a plain-English conclusion ("Dealers flip short gamma below 5910"), not a metric name. Under it, the evidence number: mono 28px, weight 600, in pure `#ffffff` - the only white on the screen. Directly beneath, the comparison (prior close, previous reading) at 12px muted, uncolored. Severity lives in one chip in the card's top-right corner; the number itself is never tinted.
2. **Named-level discipline** (SpotGamma). Call Wall, Put Wall, Zero Gamma, Vol Trigger are first-class named objects. Each keeps its exact name and identical neutral rendering in every form it appears: chart annotation, table row, and running prose. Every levels view also ships the plain key-value table, not just lines on a chart.
3. **Quiet default, loud exception** (TradingView's delayed-data "D" chip). Fresh, measured, healthy state carries zero decoration anywhere - no LIVE badge, no green dot. Only degraded states (prior, null, delayed, watch, stop) earn a chip. A fully healthy status bar reads as near-silence.
4. **currentColor instrumentation** (Observable Plot). Every meter, sparkline, and threshold rule strokes `currentColor`: meter track `rgb(var(--ink) / 0.10)`, fill `currentColor`, 4px tall, radius 0. Then `.card--watch { color: #ff9900 }` recolors every gauge in the card with one rule, and severity states cost zero extra CSS.
5. **One grey for everything not under judgment** (FT muted-first palette, inverted for dark). All context series, comparison figures, and reference numbers sit at `rgb(var(--ink) / 0.45)`. Exactly one focus treatment per view: the figure being decided on, in white. If two things are white, neither is the decision.

Also required, from Geist: every empty region is designed - title 13px/500, one sentence 12px secondary, one Verb-Noun action; and skeletons match final content dimensions exactly so nothing shifts on load.

## 6. What to avoid

- **Saturated solid fills with white text** - the number-one amateur dark-dashboard tell. Chips are always tinted-bg + hue-matched border + bright text (the Section 3 ladders).
- **Shadows or glows for elevation.** No `box-shadow` except the single popover token. No colored focus glows, ever.
- **Pure `#000000` canvas and pure-white body text.** White exists only as the reserved decision figure.
- **A third grey.** No hand-picked per-component border or text colors; everything derives from `--ink` alphas or the three surface hexes.
- **Hierarchy by inventing font sizes.** The scale in Section 2 is closed. Rank with brightness and weight inside it.
- **Reusing the directional pair.** Up-teal and down-red never appear on buttons, branding, toasts, or "success" states.
- **Zebra striping, vertical table rules, centered number columns, proportional numerals** anywhere near data.
- **Legends where a label can sit on the data**, and metric-name headlines where a plain-English verdict fits.
- **Badging the healthy state.** A LIVE chip is noise that deafens the DELAYED chip.
- **Radius above 3px, pills, and decorative border treatments.** This is a terminal, not a marketing site.
