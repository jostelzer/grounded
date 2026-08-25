# Experimental media modes

Read this reference only when the user explicitly requests `image` or `mindmap` as an output mode. Both modes use the complete **small** review pipeline first. The media is an additional synthesis artifact; it never replaces the written review or relaxes the search, reading, citation, or verification standard.

## Shared evidence boundary

- Start media planning only after the small review is complete and every cited source is verified.
- Depict only relationships, mechanisms, comparisons, or uncertainties supported by the reviewed literature.
- Never turn an association into causation, a hypothesis into an established mechanism, or a group average into an individual prediction.
- Encode uncertainty visibly. Use restrained emphasis, dashed or muted elements, and labels such as `mixed`, `limited`, or `hypothesized` when the evidence requires them.
- Keep citations in the written review and caption rather than filling the visual with DOI text.
- Generate the actual media. Do not substitute a prompt, text outline, ASCII diagram, or unrendered diagram source.
- If the required media tooling is unavailable or generation fails, still deliver the small review and state in one sentence that the visual could not be generated. Do not claim that media was created.

## Image mode

Create one polished, self-explanatory scientific illustration that communicates the review's main synthesis at a glance. The figure must be understandable to an educated non-specialist without relying on the surrounding review or caption to decode its terminology.

1. Select the single most useful visual story: a mechanism, process, system-level interaction, anatomy-plus-function relationship, intervention pathway, or evidence-backed comparison.
2. Use the environment's image-generation capability. Prefer a clean scientific-editorial illustration over decorative, cinematic, or photorealistic art unless realism is scientifically necessary.
3. Keep the title and main labels concise. Avoid abbreviations and specialist terminology when an equally accurate plain-language label will fit.
4. Reserve a visually distinct glossary band along the bottom of the illustration. Use type that is smaller than the main labels but still comfortably readable at normal chat width, including on a phone. In that band:
   - expand **every** abbreviation, acronym, initialism, and symbol used anywhere in the figure;
   - explain **every** technical or non-obvious concept in one short plain-language definition;
   - include any color, line, arrow, or uncertainty encoding that is not immediately obvious.
5. Treat an educated reader outside the specialty as the test audience. Do not assume that a term is self-explanatory merely because it is standard within the field. Common everyday words need no definition.
6. The glossary is part of the rendered image, not a substitute placed only in the chat caption. Keep citations and longer methodological caveats in the caption.
7. Prefer a two-stage composition when available: generate the illustration, then typeset exact labels and the glossary with deterministic graphics tooling. Never accept misspelled, garbled, truncated, or invented glossary text from an image model.
8. If the glossary cannot remain legible, reduce the number of depicted concepts, replace jargon with plain language, or simplify the visual. Do not shrink the footer into unreadable fine print.
9. Distinguish observed findings from proposed mechanisms through layout and visual styling. Do not invent molecular structures, anatomical details, instruments, sample images, or quantitative scales.
10. After generation, inspect the image at its delivered size. Regenerate or edit it if labels or glossary text are garbled, any abbreviation or difficult concept is undefined, anatomy is wrong, arrows imply unsupported causality, components are clipped, or the hierarchy does not match the evidence.

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
6. Text is readable at normal chat width; nothing important is clipped or overlapping.
7. The caption explains the synthesis and cites the relevant verified sources.
8. In image mode, every abbreviation and non-obvious concept is defined in a smaller but readable glossary band at the bottom of the image.
9. In image mode, the figure can be understood without consulting the surrounding prose for terminology.
