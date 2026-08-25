# Experimental media modes

Read this reference only when the user explicitly requests `image` or `mindmap` as an output mode. Both modes use the complete **small** review pipeline first. The media is an additional synthesis artifact; it never replaces the written review or relaxes the search, reading, citation, or verification standard.

## Shared evidence boundary

- Start media planning only after the small review is complete and every cited source is verified.
- Depict only relationships, mechanisms, comparisons, or uncertainties supported by the reviewed literature.
- Never turn an association into causation, a hypothesis into an established mechanism, or a group average into an individual prediction.
- Encode uncertainty visibly. Use restrained emphasis, dashed or muted elements, and labels such as `mixed`, `limited`, or `hypothesized` when the evidence requires them.
- Keep citations in the written review and caption rather than filling the visual with DOI text.
- Generate the actual media. Do not substitute a prompt, text outline, ASCII diagram, or unrendered diagram source.
- **All text is typeset deterministically, never drawn by an image model** — see the rule under Image mode. This applies to both modes.
- If the required media tooling is unavailable or generation fails, still deliver the small review and state in one sentence that the visual could not be generated. Do not claim that media was created.

## Image mode

Create one polished, self-explanatory scientific illustration that communicates the review's main synthesis at a glance. The figure must be understandable to an educated non-specialist without relying on the surrounding review or caption to decode its terminology.

### The one rule that governs everything: text is typeset, never generated

**Every character in the figure — title, labels, callouts, the glossary — is placed by deterministic vector tooling that you author (hand-written SVG, or matplotlib/graphviz).** Diffusion image models cannot spell reliably, cannot align text to the thing it labels, and cannot be edited afterwards. A figure whose labels came out of an image model will have misspellings, invented words, colliding text, and labels sitting on top of the artwork. This is the single most common way this mode fails.

Two acceptable builds:

- **Vector-only — the default, and always safe.** Author the whole figure as SVG: shapes, arrows, panels, text. Flat scientific-editorial style, simple icons built from primitives.
- **Two-stage, only if an image model is genuinely needed** for texture or organic form. Generate the *artwork containing no text whatsoever* (say "no text, no labels, no letters, no numbers" in the prompt), then place every label and the glossary in a vector layer you control, in empty space you reserved for it. If the generated artwork comes back with any lettering in it, discard it — never try to cover it up.

### Composition dos and don'ts

**Do:**

- Design the layout first as a grid of regions — title band, figure body, glossary band — and give every text element its own region with margins. Text and artwork occupy *separate* space.
- Keep one visual story with 3–6 elements. A figure that tries to show everything shows nothing.
- Use flat, diagrammatic shapes. A labelled box beats a beautiful rendering the reader has to decode.
- Give every arrow a meaning stated in the figure ("leads to", "measured by", "mixed evidence").
- Encode uncertainty visibly and explain the encoding in the glossary — dashed outline, muted fill, an explicit `mixed` or `mouse evidence only` tag.
- Check text length against its box *before* rendering: estimate width as roughly 0.55 × font-size × character count, and wrap manually into `tspan` lines with explicit `x`/`y`. SVG collapses whitespace, so never fake indentation with spaces.
- Rasterize and *look* at the result if any renderer is available (`rsvg-convert`, `cairosvg`, a headless browser). Inspect at delivered size and at phone width.

**Don't:**

- **Don't let an image model draw any text.** No exceptions, including "just the title".
- **Don't place text over busy artwork.** No label sitting on a gradient, a photo-like surface, or another element's edge. If a label must sit on artwork, give it a solid backing plate.
- **Don't let panels, icons, or captions overlap.** Bounding boxes must be disjoint. Overlap is not a style choice; it reads as a broken render.
- **Don't decorate.** Sunbursts, clouds, glows, drop shadows, cinematic lighting and stock-illustration flourishes add nothing and crowd out the labels.
- **Don't invent specifics**: no fabricated molecular structures, anatomical detail, instrument readouts, sample images, chart data, or axis scales. If the review has no numbers for it, the figure has no numbers for it.
- **Don't shrink the glossary into fine print** to make room. Cut concepts instead.
- **Don't ship a figure you have not looked at.** If you genuinely cannot inspect it, say so in one sentence rather than implying it was checked.

### Content requirements

1. Select the single most useful visual story: a mechanism, process, system-level interaction, anatomy-plus-function relationship, intervention pathway, or evidence-backed comparison.
2. Keep the title and main labels concise. Avoid abbreviations and specialist terminology when an equally accurate plain-language label will fit.
3. Reserve a visually distinct glossary band along the bottom of the illustration. Use type that is smaller than the main labels but still comfortably readable at normal chat width, including on a phone. In that band:
   - expand **every** abbreviation, acronym, initialism, and symbol used anywhere in the figure;
   - explain **every** technical or non-obvious concept in one short plain-language definition;
   - include any color, line, arrow, or uncertainty encoding that is not immediately obvious.
4. Treat an educated reader outside the specialty as the test audience. Do not assume that a term is self-explanatory merely because it is standard within the field. Common everyday words need no definition.
5. The glossary is part of the rendered image, not a substitute placed only in the chat caption. Keep citations and longer methodological caveats in the caption.
6. If the glossary cannot remain legible, reduce the number of depicted concepts, replace jargon with plain language, or simplify the visual. Do not shrink the footer into unreadable fine print.
7. Distinguish observed findings from proposed mechanisms through layout and visual styling.
8. After generation, inspect the image at its delivered size. Regenerate or edit it if labels or glossary text are garbled, any abbreviation or difficult concept is undefined, anatomy is wrong, arrows imply unsupported causality, components are clipped or overlapping, or the hierarchy does not match the evidence.

Deliver the small review using the normal writing guide, then insert:

```text
### Scientific illustration
<rendered image>
*Caption: what the visual shows, what is established versus uncertain, and 2–5 supporting review citations.*
```

Use specific alt text that communicates the visual structure and scientific point. The caption may elaborate, but the illustration itself must remain independently understandable.

## Mindmap mode

Create one rendered, readable mindmap that exposes the structure of the evidence rather than merely decorating the topic.

1. Put the sharpened research question at the root.
2. Use 4–7 primary branches drawn from the review's actual angles and punchlines. Include the direct answer, mechanisms where relevant, moderators or populations, contrary/null findings, limitations, and open questions when supported.
3. Keep node labels to roughly 2–7 words. Add only enough second-level nodes to preserve the major findings; do not reproduce the entire review in the map.
4. Encode evidence strength consistently, with a small legend. A useful default is strong/consistent, mixed/moderate, and limited/uncertain. Do not imply that branch size equals effect size unless the data support that encoding.
5. Use an available visualization or diagram renderer that produces a real displayed artifact. Prefer deterministic SVG, HTML/canvas, or graph rendering for legible text. Mermaid is acceptable only when the client renders it visibly; never hand back raw Mermaid as the media deliverable.
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
6. Text is readable at normal chat width; nothing important is clipped or overlapping; no text sits on top of artwork; every character was typeset, not generated.
7. The caption explains the synthesis and cites the relevant verified sources.
8. In image mode, every abbreviation and non-obvious concept is defined in a smaller but readable glossary band at the bottom of the image.
9. In image mode, the figure can be understood without consulting the surrounding prose for terminology.
