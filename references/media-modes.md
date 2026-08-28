# Figures for the journal PDF and slides formats

Read this reference whenever the output format is the **journal PDF** (whose figures are mandatory and automatic — there is no separate image mode) or **slides**. The figures are an additional synthesis artifact created after the complete review pipeline has run at the selected size and style; they never replace the written review or relax the search, reading, citation, or verification standard. An explicitly requested `deck`, `slides`, presentation, slide deck, or journal club deck follows the same shared evidence boundary below but uses the complete workflow in `deck-guide.md` — and differs in delivery: the deck is the deliverable, with the synthesis (`synthesis.md`, per `synthesis-guide.md`) kept as a working file rather than delivered in chat.

Before creating media, also read `figure-generation-contract.md`,
`figure-reference-analysis.md`, `figure-style-system.md`,
`image-prompt-guide.md`, and `figure-captions.md`. They define the generator-
first route, visual evidence base, style-aware figure system, structured prompt
workflow, and cited caption/cross-reference contract. Do not substitute an
improvised prose prompt.

## Shared evidence boundary

- Start media planning only after the written review at the selected tier is complete and every cited source is verified.
- Depict only relationships, mechanisms, comparisons, or uncertainties supported by the reviewed literature.
- Never turn an association into causation, a hypothesis into an established mechanism, or a group average into an individual prediction.
- Encode uncertainty visibly. Use restrained emphasis, dashed or muted elements, and labels such as `mixed`, `limited`, or `hypothesized` when the evidence requires them.
- Keep citations in the written review and caption rather than filling the visual with DOI text.
- Generate the actual media. Do not substitute a prompt, text outline, ASCII diagram, or unrendered diagram source.
- Prefer a capable built-in image-generation model for the visually rich layer. Use complete generation for text-light work and hybrid generation plus deterministic overlay when labels, numbers, or exact arrows are dense. Deterministic rendering is primary only when mathematical geometry is the evidence.
- If the required media tooling is unavailable or generation fails, still deliver the written review at its selected tier and state in one sentence that the visual could not be generated. Do not claim that media was created.

## Slides

The slides format is explicit-only, combines with every size and style, and is itself the deliverable: chat carries the question, a 1–3 sentence plain answer, and the verified 16:9 PDF, while `synthesis.md` stays a working file. Read `deck-guide.md` before planning it. Every content slide uses `render_context: slide`, a full-sentence cited claim in real-text chrome, one generated image that carries the evidence itself, and a `strong`/`mixed`/`limited` evidence grade — and must pass the guide's standalone test: claim, evidence, and firmness readable from the slide alone. The canonical exporter adds title and two-column reference slides from the verified ledger; the dedicated QA inspects every landscape page and its live DOI links. Deck has no deterministic or text-slide fallback: when no capable image-generation model is available, fall back to rendering `synthesis.md` as a normal full review in the selected style and state in one sentence that the deck could not be generated.

## Journal-PDF figures

Create polished, self-explanatory scientific figures that communicate the review's synthesis. The journal PDF always carries figures, at any size and style; the figure budget scales with the size:

| | Small | Medium | Large |
|---|---:|---:|---:|
| Normal target | 2 | 3–4 | 5–6 |
| Hard ceiling | 2 | 5 | 8 |

The target expresses the new visual ambition, while the ceiling prevents a
review from becoming a picture stack. Plan visual coverage immediately after
`synthesis.md`: normally Figure 1 is the whole-answer synthesis, then choose
different jobs from mechanism, study design, exact quantitative result,
comparison/moderator, and uncertainty/evidence boundary. Every figure must be
earned by a distinct visual story. A review with only one genuinely visual
finding may still use one; the validator warns below target but does not force
padding. Never add a figure that merely restates a table, repeats another
figure, or decorates a section.

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
every writing style, reference each figure from the relevant body text using
the stable-ID syntax in `figure-captions.md`. Because the cited caption supplies
the title and scope, use `render_context: article` and do not repeat a hero title
or subtitle inside the artwork. Define symbols locally or in a compact legend;
use a glossary region only when essential terminology cannot be defined without
it.

Every figure must be understandable to an educated non-specialist without relying on the surrounding review to decode its terminology.

### Preferred build: generator-first, exact where it matters

Probe the current agent's media capabilities before choosing a renderer. When a
capable built-in image generator is available, use it for the visually authored
portion of every non-quantitative figure. Create a quality-contract figure-spec
JSON with `review_style`, `render_route`, `target_aspect_ratio`, and one dominant
`visual_anchor`; set `render_context: article`, select a scientific profile and
archetype, then run `scripts/build_figure_prompt.py`. The prompt builder combines
the verified story with route-specific instructions and distinct scientific,
popsci, bullets, or ELI5 art direction.

Choose `generated` for text-light finished artwork, `hybrid` for rich artwork
with exact labels/numbers/arrows added by `compose_hybrid_figure.py`, and
`deterministic` from the start for exact plots or other mathematical geometry.
Hybrid is the normal high-quality answer to a generator that illustrates
beautifully but typesets dense copy poorly; it is not a fallback. The generated
base must remain the meaningful scientific composition, not a token texture
behind a generic vector diagram.

For generated and hybrid routes, make at least two meaningfully different
candidates and compare evidence fidelity, hierarchy, domain specificity, style
fit, polish, and legibility. Use a targeted edit for a local flaw and a fresh
candidate for a broadly weak composition. Preserve the strongest generated
composition with a deterministic overlay when dense copy is the only blocker.
A non-quantitative pure deterministic fallback requires two generated
candidates, one targeted edit, explicit hybrid consideration, and a concrete
failure reason in provenance. Never ship the first technically valid result or
prefer a visibly cheaper flowchart merely because OCR is easier.

After composition, inspect every word, number, symbol, arrow, plotted magnitude,
scientific relationship, and shape. A visually attractive result still fails if
it changes evidence; a correct result still fails if it is generic, cheap, or
stylistically wrong. Save the inspection and generation provenance and run
`qa_figure.py` with both. No stage may scale width and height independently:
circles remain circular and lettering keeps its natural proportions. Final PDF
QA independently measures the image transformation matrix rather than trusting
CSS intent.

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
  delivered size. Quote generator-rendered copy exactly; for hybrid figures,
  reserve quiet zones and put dense exact copy in the overlay manifest.
- Rasterize and *look* at the result if any renderer is available (`rsvg-convert`, `cairosvg`, a headless browser). Inspect at delivered size and at phone width.
- Keep journal-PDF figures at an aspect ratio of at least 2:1. The exporter
  caps figure height (92 mm by default, `--figure-max-height` to adjust within
  60–120 mm) and scales taller figures down proportionally, shrinking every
  label with them; `qa_figure.py` evaluates label legibility at the true
  rendered width and fails figures whose labels fall below 6.5 pt on paper.

**Don't:**

- **Don't accept approximately correct text or data.** Every rendered word, number, unit, and symbol must match the supplied copy exactly.
- **Don't place text over busy artwork.** Labels need quiet space or a plain backing plate.
- **Don't let panels, icons, or captions overlap.** Bounding boxes must be disjoint. Overlap is not a style choice; it reads as a broken render.
- **Don't stretch to fit.** Never set independent width and height scales, shear
  a raster, condense lettering, or turn a circle into an ellipse. Wrap, move,
  crop proportionally, or revise the composition instead.
- **Don't drift into slide or dashboard design.** Article and standalone figures
  must not imitate presentation furniture. Slide-context artwork still excludes
  serif headlines, rounded UI cards, badges, decorative icons, drop shadows,
  cinematic lighting, glossy 3D, and ornamental gradients; the canonical deck
  renderer owns all presentation chrome.
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

Deliver the review at its size and style using the stable-ID draft contract in
`figure-captions.md`. The formatter assigns numbers, verifies the caption's
ledger citations, inserts anchors, resolves body tokens to clickable `Figure N`
links, and adds caption sources to the normal Sources block:

```text
The mechanism is summarized in {{figure:mechanism}}.

![<specific alt text: the visual structure and the scientific point>](<figure file>)
**Figure {#mechanism}. <declarative title>.** <style-matched explanation, evidence boundary, and 2–5 ledger citations>
```

(When there is a single synthesis figure and no better anchor section, a
`### Scientific illustration` section before **Sources** is still acceptable.)
The caption may elaborate, but each figure must remain independently
understandable. Bullet reviews may use the structured `Shows / Evidence boundary
/ Sources` caption; scientific uses a short flowing paragraph; popsci uses a
short flowing paragraph in the magazine register; ELI5 uses a short flowing
paragraph of everyday sentences. `scripts/format_references.py` and
`scripts/export_review.py` validate the contract.

## Final media quality gate

1. The journal PDF or slides format was explicitly requested.
2. The written review independently answers the question at the selected tier.
3. Every depicted scientific claim is supported by the verified review.
4. Uncertainty and disagreement remain visible.
5. The artifact is rendered and displayed, not supplied as instructions or source code.
6. Text is readable and exactly correct at normal chat width; nothing important is clipped, overlapping, or lost against the artwork.
7. Every figure has a stable ID, is referenced from the body, and has a caption
   that matches the review's scientific, popsci, bullets, or ELI5 register.
8. The caption explains the synthesis, states its evidence boundary, and cites
   2–5 relevant verified sources that also appear in the Sources block.
9. In every figure, every abbreviation and non-obvious concept is defined by a
   local label or a smaller but readable legend/key inside the image.
10. Every figure can be understood without consulting the surrounding prose for terminology.
11. The selected route and iteration history are recorded; all five visual-
    quality dimensions pass, the raster matches its declared aspect, and final
    PDF placement preserves that intrinsic ratio without shear.
