---
name: visualize-with-html
description: Produce experiment visualizations as single self-contained HTML files with a restrained, readable design. Use in the Run stage, usually right after evaluate-llm, to turn metrics and comparisons into figures stored under the experiment's figures/. Large chart data goes to CSV, not inline.
---

# Visualize with HTML Skill

**Stage:** Run (usually right after `evaluate-llm`; also used in Finalize to
polish the figures that go into the record)

Turn metrics and run comparisons into figures. Figures are **single
self-contained HTML files**, written as text so they diff cleanly, open offline,
and stay readable years later. You write the HTML directly — there is no plotting
script to maintain unless the data is large enough to warrant one (see below).

## Why HTML, not PNG

- A figure is a text file you can open, read, and edit directly; Git can diff it.
- No binary blob and no `plot.py` round-trip to regenerate it.
- An agent can author the chart (SVG paths, CSS bars, inline table) from the data
  without running a rendering tool.

## Output rules

1. **One file per figure, self-contained.** Save under
   `experiments/<experiment-id>/figures/<name>.html`. Everything the figure needs
   (markup, CSS, any small data) lives in that one file. It must open correctly
   from `file://` with no local server.

2. **Default: hand-written HTML/CSS/SVG.** For the common case (tens to a few
   hundred points — loss curves, bar comparisons, small tables) draw it yourself
   with SVG or CSS. No JavaScript library needed.

3. **Interactivity only when it earns its place.** If zoom/pan/hover genuinely
   helps (dense series, many runs overlaid), use Plotly loaded **from a CDN**:

   ```html
   <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
   ```

   **Never embed the Plotly JS bundle in the file.** Embedding bloats one file to
   several MB and makes it undiffable. The trade-off of the CDN form — it needs
   internet to open, and the CDN URL could change — is accepted deliberately;
   hand-written HTML/CSS/SVG remains the default for anything kept as the record.

4. **Large data goes to CSV, not inline.** When a chart's data runs to thousands
   of values, do not paste them into the HTML. Save the data as CSV under
   `experiments/<experiment-id>/data/<name>.csv` and have the figure read from it
   (e.g. fetch the CSV and plot with CDN Plotly). Keep the CSV the single source
   of the numbers; the HTML holds presentation, not a second copy of the data.

## Design principles

Aim for a figure a careful analyst would make, not a tool's default output.

- **Maximize data, minimize decoration.** Every mark should carry information.
  Drop chart junk: heavy gridlines, boxes, drop shadows, gradients, 3-D effects,
  redundant legends.
- **Readable type and generous whitespace.** One clear title that states the
  finding, axis labels with units, legible sizes, comfortable spacing. Let the
  plot breathe rather than filling the frame.
- **Sober, purposeful color.** Use a small, muted palette; reserve a strong
  accent for the series that matters. Don't color things that carry no meaning.
  Keep enough contrast for text and lines, and don't rely on color alone to
  distinguish series (vary line style or add direct labels).
- **Label directly where you can.** Prefer labeling a line or bar in place over
  forcing the reader to a separate legend.
- **Honest scales.** State the axis range and whether a baseline is at zero;
  don't truncate an axis in a way that exaggerates a difference. Label derived
  quantities (relative vs. absolute improvement) as such.
- **Avoid generic defaults.** No placeholder titles, no default rainbow palettes,
  no decoration added just to fill space. The figure should look deliberate.

## Procedure

1. **Know the finding.** Decide the one thing the figure should show (a trend, a
   ranking, a gap vs. baseline). Title and layout follow from that.
2. **Decide the form.** Hand-written SVG/CSS by default; CDN Plotly only if
   interactivity earns its place. If the data is large, write the CSV first and
   point the figure at it.
3. **Write the file** under `figures/`, following the output and design rules.
4. **Verify it opens.** Confirm the file renders from `file://` (and, for the CDN
   form, note in the record that it needs internet to open). Check axes, labels,
   and units are correct against the source numbers.
5. **Record it.** Note the figure (and any CSV) in `history.md`, and reference it
   from `journal.md` where it supports a conclusion.

## Notes

- Keep figures tied to recorded evidence — a figure must not show a number that
  isn't in the run's results.
- Figures and their CSV data are committed with the rest of the record (they are
  text/small tabular files, not the gitignored checkpoints or raw logs).
