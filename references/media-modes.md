# Experimental media modes

Read this reference only when the user explicitly requests `image` or `mindmap` as an output mode. Image mode runs the complete review pipeline at the requested size and style (small bullets when none is named); mindmap mode uses the small pipeline. The media is an additional synthesis artifact; it never replaces the written review or relaxes the search, reading, citation, or verification standard.

Before creating media, also read `figure-reference-analysis.md`,
`figure-style-system.md`, and `image-prompt-guide.md`. They define the visual
evidence base, Arial-based journal system, and structured prompt workflow. Do
not substitute an improvised prose prompt.

## Shared evidence boundary

- Start media planning only after the small review is complete and every cited source is verified.
- Depict only relationships, mechanisms, comparisons, or uncertainties supported by the reviewed literature.
- Never turn an association into causation, a hypothesis into an established mechanism, or a group average into an individual prediction.
- Encode uncertainty visibly. Use restrained emphasis, dashed or muted elements, and labels such as `mixed`, `limited`, or `hypothesized` when the evidence requires them.
- Keep citations in the written review and caption rather than filling the visual with DOI text.
- Generate the actual media. Do not substitute a prompt, text outline, ASCII diagram, or unrendered diagram source.
- Prefer a capable image-generation model for the complete rendered artifact, including text. Supply exact copy and inspect every character; deterministic SVG or another renderer is the fallback when generation is unavailable or cannot pass QA.
- If the required media tooling is unavailable or generation fails, still deliver the small review and state in one sentence that the visual could not be generated. Do not claim that media was created.

## Image mode

Create polished, self-explanatory scientific figures that communicate the review's synthesis. Image mode combines with any size and style; the figure budget scales with the size:

| | Small | Medium | Large |
|---|---|---|---|
| Figures | 1 | up to 3 | up to 5 |

"Up to" is a cap, not a quota: every figure must be earned by a distinct visual story in the evidence. A medium review with one genuinely visual finding gets one figure. Never pad with a figure that restates a table or decorates a section.

**What a figure can be — maximum flexibility within the rules.** Any figure that serves the evidence is allowed. Examples, not an exhaustive list:

- the main synthesis illustration — the whole answer at a glance (this is always figure 1);
- a mechanism or pathway diagram;
- an evidence map — studies laid out by population, dose, duration, or outcome;
- a forest-style effect summary plotting the effect sizes and intervals *already extracted into the review* — real numbers only, each traceable to a cited source;
- a timeline — the history of a claim, or intervention-to-outcome time courses;
- a flow diagram — study selection, patient flow, a decision path;
- a dose–response or exposure–response schematic from reported values;
- an anatomical or structural schematic, at the level of detail the sources support;
- a conceptual framework showing how the field's competing explanations relate;
- a contrast panel — "what the claim says" versus "what the trials measured".

Invent freely beyond this list. The constraints are always the same: built only from the verified synthesis, no fabricated data points or scales, uncertainty visible, and the composition rules below.

**Placement.** Figures go where they support the argument — each one inserted
after the section it illustrates, with its caption — not stacked at the end. In
prose style, reference each figure from the running text. Because that caption
already supplies the title and scope, use `render_context: article` and do not
repeat a hero title or subtitle inside the artwork. Define symbols locally or in
a compact legend; use a glossary region only when essential terminology cannot
be defined without it.

Every figure must be understandable to an educated non-specialist without relying on the surrounding review to decode its terminology.

### Preferred build: generate the complete figure end to end

When a capable image-generation model is available, ask it to render the
finished scientific figure as one complete artifact: illustration, composition,
panel labels, arrows, exact numerical values, legend, uncertainty language, and
any necessary local definitions. Do not automatically split the artwork and
typography into separate stages. Create a figure-spec JSON, set
`render_context: article`, select a profile from `figure-style-presets.json` and
an archetype from `figure-archetypes.json`, then run
`scripts/build_figure_prompt.py`. This keeps evidence, composition, framing, and
art direction independently reusable. Use `render_context: standalone` only
when there will be no adjacent title/caption; its compact title is still
rendered end to end by the image model.

The generated prompt must contain the figure's evidence-backed visual story and **all required text verbatim**. Quote titles, labels, numbers, units, confidence intervals, legend entries, and glossary definitions. State which relationships are observed, inferred, mixed, or uncertain and how that distinction must appear. For quantitative figures, supply every plotted value and scale explicitly; the model must not invent, interpolate, or relabel data. Arial is the defined font; visually reject serif, condensed, display, outlined, or shadowed lettering.

After generation, inspect every word, number, symbol, arrow, plotted magnitude, and scientific relationship. A visually attractive result still fails if it misspells a label, changes a denominator, drops a confidence interval, reverses a relationship, invents anatomy, or implies unsupported certainty. Use targeted image edits or regenerate until it passes. If a capable image model is unavailable, or repeated generation cannot produce a fully correct and readable result, fall back to hand-authored SVG, matplotlib, graphviz, HTML/canvas, or another deterministic renderer.

### Composition dos and don'ts

**Do:**

- Use the selected style profile's canvas, Arial hierarchy, pale semantic
  palette, margins, and exclusions consistently.
- Build the layout from domain-specific scientific primitives and a shared
  invisible grid. Use white space and alignment before borders.
- Prefer the clean 2D scientific-editorial language defined in `figure-style-system.md`; restrained biological shading is allowed only when it clarifies form.
- Give every arrow a meaning stated in the figure ("leads to", "measured by", "mixed evidence").
- Encode uncertainty visibly and explain the encoding in the glossary — dashed outline, muted fill, an explicit `mixed` or `mouse evidence only` tag.
- Keep all required in-figure copy short enough to remain readable at the
  delivered size. Quote the exact copy in the generation prompt and request
  deliberate line wrapping.
- Rasterize and *look* at the result if any renderer is available (`rsvg-convert`, `cairosvg`, a headless browser). Inspect at delivered size and at phone width.

**Don't:**

- **Don't accept approximately correct text or data.** Every rendered word, number, unit, and symbol must match the supplied copy exactly.
- **Don't place text over busy artwork.** Labels need quiet space or a plain backing plate.
- **Don't let panels, icons, or captions overlap.** Bounding boxes must be disjoint. Overlap is not a style choice; it reads as a broken render.
- **Don't drift into slide or dashboard design.** No serif headlines, rounded UI cards, badges, decorative icons, drop shadows, cinematic lighting, glossy 3D, or ornamental gradients.
- **Don't drift into poster design.** In article context, no internal hero title
  or subtitle, oversized number, footer banner, or universal sequence of equal
  presentation columns.
- **Don't invent specifics**: no fabricated molecular structures, anatomical detail, instrument readouts, sample images, chart data, or axis scales. If the review has no numbers for it, the figure has no numbers for it.
- **Don't shrink the glossary into fine print** to make room. Cut concepts instead.
- **Don't ship a figure you have not looked at.** If you genuinely cannot inspect it, say so in one sentence rather than implying it was checked.

### Content requirements

1. Select the single most useful visual story: a mechanism, process, system-level interaction, anatomy-plus-function relationship, intervention pathway, or evidence-backed comparison.
2. Keep the title and main labels concise. Avoid abbreviations and specialist terminology when an equally accurate plain-language label will fit.
3. Define abbreviations and non-obvious concepts with a direct local label when
   possible. If several definitions remain necessary, reserve a visually quiet,
   compact key region. Use Arial that is smaller than the main labels but still
   comfortably readable at normal chat width, including on a phone. In that region:
   - expand **every** abbreviation, acronym, initialism, and symbol used anywhere in the figure;
   - explain **every** technical or non-obvious concept in one short plain-language definition;
   - include any color, line, arrow, or uncertainty encoding that is not immediately obvious.
4. Treat an educated reader outside the specialty as the test audience. Do not assume that a term is self-explanatory merely because it is standard within the field. Common everyday words need no definition.
5. Any essential local definition or glossary is part of the rendered image,
   not a substitute placed only in the chat caption. Include its exact wording
   in the generation prompt. Keep citations and longer methodological caveats in
   the caption.
6. If the glossary cannot remain legible, reduce the number of depicted concepts, replace jargon with plain language, or simplify the visual. Do not shrink the footer into unreadable fine print.
7. Distinguish observed findings from proposed mechanisms through layout and visual styling.
8. After generation, inspect the image at its delivered size. Regenerate or edit it if labels or glossary text are garbled, any abbreviation or difficult concept is undefined, anatomy is wrong, arrows imply unsupported causality, components are clipped or overlapping, or the hierarchy does not match the evidence.

Deliver the review at its size and style using the normal writing guide, inserting each figure after the section it supports:

```text
![<specific alt text: the visual structure and the scientific point>](<figure file>)
*Caption: what the visual shows, what is established versus uncertain, and 2–5 supporting review citations.*
```

(When there is a single synthesis figure and no better anchor section, a `### Scientific illustration` section before **Sources** is still acceptable.) The caption may elaborate, but each figure must remain independently understandable. This exact `![...](...)` + `*Caption: …*` pairing is what `scripts/export_review.py` recognizes, so the figures flow into the PDF export automatically.

## Mindmap mode

Create one rendered, readable mindmap that exposes the structure of the evidence rather than merely decorating the topic.

1. Put the sharpened research question at the root.
2. Use 4–7 primary branches drawn from the review's actual angles and punchlines. Include the direct answer, mechanisms where relevant, moderators or populations, contrary/null findings, limitations, and open questions when supported.
3. Keep node labels to roughly 2–7 words. Add only enough second-level nodes to preserve the major findings; do not reproduce the entire review in the map.
4. Encode evidence strength consistently, with a small legend. A useful default is strong/consistent, mixed/moderate, and limited/uncertain. Do not imply that branch size equals effect size unless the data support that encoding.
5. Prefer a capable image-generation model to render the complete map, including all node and legend text. Inspect every label and relationship. Use deterministic SVG, HTML/canvas, graph rendering, or visibly rendered Mermaid as fallback; never hand back raw diagram source.
6. Inspect the rendered map. Fix overlaps, clipped nodes, unreadable labels, weak contrast, confusing crossing edges, and any branch whose emphasis misstates the literature.

Deliver the small review using the normal writing guide, then insert:

```text
### Findings mindmap
<rendered mindmap>
*Caption: how to read the evidence-strength encoding and which review sections support the main branches.*
```

Use specific alt text that lists the root and primary branches.

## Final media quality gate

1. The media mode was explicitly requested.
2. The written review independently answers the question at small depth.
3. Every depicted scientific claim is supported by the verified review.
4. Uncertainty and disagreement remain visible.
5. The artifact is rendered and displayed, not supplied as instructions or source code.
6. Text is readable and exactly correct at normal chat width; nothing important is clipped, overlapping, or lost against the artwork.
7. The caption explains the synthesis and cites the relevant verified sources.
8. In image mode, every abbreviation and non-obvious concept is defined by a
   local label or a smaller but readable legend/key inside the image.
9. In image mode, the figure can be understood without consulting the surrounding prose for terminology.
