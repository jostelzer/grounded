# Modular prompt guide for scientific figures

Build prompts with `scripts/build_figure_prompt.py`; do not improvise one long
prose prompt from memory. Read `figure-generation-contract.md` first. The
builder encodes the visual audit in `figure-reference-analysis.md` and assembles
eight independent modules:

1. **Evidence specification** — what the reviewed literature supports.
2. **Figure archetype** — how that evidence should be organized.
3. **Scientific profile** — domain grammar, composition, and exclusions.
4. **Writing-style overlay** — distinct scientific, popsci, bullets, or ELI5 art direction and typography.
5. **Render route** — generated, hybrid, or deterministic production.
6. **Render context** — article, standalone, or 16:9 deck-slide figure.
7. **Text/overlay manifests** — what the generator may typeset and what must be added deterministically.
8. **Quality and geometry contract** — what must be inspected, compared, and proved before release.

## Minimal specification

```json
{
  "quality_contract_version": 1,
  "profile": "nature-neuroscience",
  "archetype": "mechanism",
  "review_style": "scientific",
  "render_route": "hybrid",
  "render_context": "article",
  "target_aspect_ratio": 2.0,
  "visual_anchor": "A recognizable cell cross-section with one lipid nanoparticle entering from the left",
  "purpose": "Explain how a transient RNA payload leads to immune memory.",
  "title": "How a temporary RNA recipe builds immune memory",
  "story": [
    "A lipid nanoparticle protects and delivers mRNA.",
    "Ribosomes translate it in the cytoplasm.",
    "Antigen display and immune signalling recruit memory responses."
  ],
  "exact_text": [
    "Package",
    "Translate",
    "Signal",
    "Memory"
  ],
  "generated_text": [],
  "overlay": {
    "items": [
      {"type": "text", "x": 0.05, "y": 0.16, "max_width": 0.18, "text": "Package", "size_px_at_1536": 30, "weight": "bold"},
      {"type": "text", "x": 0.29, "y": 0.16, "max_width": 0.18, "text": "Translate", "size_px_at_1536": 30, "weight": "bold"},
      {"type": "text", "x": 0.53, "y": 0.16, "max_width": 0.18, "text": "Signal", "size_px_at_1536": 30, "weight": "bold"},
      {"type": "text", "x": 0.77, "y": 0.16, "max_width": 0.18, "text": "Memory", "size_px_at_1536": 30, "weight": "bold"}
    ]
  }
}
```

Generate the prompt with one command:

```bash
python3 scripts/build_figure_prompt.py --spec examples/image-mrna-vaccines-mechanism.figure.json
```

Use `--profile`, `--archetype`, `--review-style`, or `--render-route` to test a
different visual treatment without rewriting the evidence specification. Save
the selected prompt with `--out figure.prompt.txt` for provenance.

## Specification fields

Required:

- `purpose`: one sentence describing what the reader should understand.
- `title`: the figure title.
- `story`: ordered, evidence-backed visual statements.
- `exact_text`: every required title, label, number, unit, qualifier, legend entry, and glossary line.

Required by `quality_contract_version: 1`:

- `review_style`: `scientific`, `popsci`, `bullets`, or `eli5`; this selects
  the matching overlay in `figure-writing-style-overlays.json`.
- `render_route`: `generated`, `hybrid`, or `deterministic`.
- `target_aspect_ratio`: numeric width divided by height; use 2.0 or wider for
  ordinary journal figures and exactly 16/9 for slides.
- `visual_anchor`: one concrete, domain-specific focal structure for every
  non-quantitative figure.
- `overlay`: required for hybrid figures; normalized deterministic text/line/
  arrow/circle/rectangle items consumed by `compose_hybrid_figure.py`.

Optional:

- `profile`: `nature-neuroscience` (default), `nature-reviews`, or `nature-data`.
- `archetype`: `mechanism`, `anatomical-mechanism`, `study-overview`,
  `comparison`, `quantitative`, `evidence-map`, `timeline`, or `mindmap`.
- `render_context`: `article` (the profile default), `standalone`, or `slide`.
  Use `slide` only for artwork that will be wrapped by `export_deck.py`; the
  builder reserves quiet top and bottom zones for the renderer's real text.
- `subtitle`: short scope or evidence qualifier.
- `observed`: findings directly observed in cited human or experimental data.
- `inferred`: synthesis, model-supported, animal-only, mixed, or uncertain relationships.
- `data`: structured values, intervals, units, scales, sample sizes, and denominators.
- `layout_notes`: topic-specific arrangement requirements.
- `constraints`: scientific or production invariants.
- `avoid`: topic-specific failure modes appended to the profile exclusions.
- `style_overrides`: narrow profile changes such as `canvas.aspect` or a palette value. Do not use this field to change evidence.
- `generated_text`: the subset of `exact_text` the image model may render. The
  rest is reserved for the hybrid overlay. Omit it for a fully generated figure.
- `geometry_invariants`: topic-specific shape guarantees such as “the vessel
  cross-section remains circular” or “both axes use equal unit geometry.”
- `art_direction`: topic-specific material, lighting, focal, or eye-path notes
  appended to the selected writing-style overlay.
- `aspect_ratio_tolerance`: relative raster-ratio tolerance, normally 0.03.

## Prompting rules

- Make the prompt visually specific and richly art-directed: name the focal
  scientific structure, material treatment, hierarchy, eye path, negative
  space, finish, and rejection standard. Richness must clarify the evidence,
  not invent unsupported detail.
- On the `generated` route, ask for the complete text-light finished figure.
  On the `hybrid` route, ask for the finished illustration layer and explicitly
  reserve quiet copy zones with no pseudo-text. On `deterministic`, treat the
  prompt as a production brief for mathematically faithful rendering.
- In `article` context, treat `title` and `subtitle` as caption context and do
  not render them inside the artwork. In `standalone` context, render the title
  compactly and include it in `exact_text`. In `slide` context, keep the title,
  citations, evidence chip, masthead, and slide counter out of the pixels.
- Quote every required in-figure string through `exact_text`; spell difficult
  labels exactly once rather than offering variants. The builder removes an
  exact title/subtitle match from the in-figure manifest in `article` and
  `slide` contexts.
- Use the writing-style font policy: Arial/Helvetica for scientific, Optima/
  Helvetica Neue for popsci, Helvetica Neue/Arial for bullets, and Seravek/
  Helvetica Neue for ELI5. Always require natural-width glyphs and forbid
  condensed, expanded, sheared, outlined, or shadowed type.
- Describe what should be seen, not which software operations to simulate.
- Start from the domain-native visual representation—anatomy, signal flow,
  experiment, task, mathematical geometry, or data. Do not force the content
  into equal cards or a presentation-slide sequence.
- Use alignment and white space before boxes, local labels before a glossary,
  and thin neutral connectors before coloured arrows.
- Keep exact data in structured `data`, not buried in prose.
- Use `observed` and `inferred` to control uncertainty styling.
- Keep citations out of the pixels and put them in the Markdown caption.
- Never request Nature logos, mastheads, branded page furniture, or a replica of a particular published figure.
- State the geometry invariants explicitly: preserve the canvas ratio, never
  resize one axis independently, keep circles circular and squares square, and
  fit text by wrapping/moving/editing rather than distorting glyphs.

## Archetype choice

- **Mechanism:** a sequence with evidence-calibrated arrows.
- **Anatomical mechanism:** a recognizable spatial anchor with local labels and
  explicit scale transitions.
- **Study overview:** the real experimental or analytical topology expressed
  with domain-native inputs, transformations, and outputs.
- **Comparison:** aligned outcomes or explanations without accidental area encoding.
- **Quantitative:** exact axes, values and uncertainty; one targeted correction at most before switching to evidence cards or deterministic fallback.
- **Evidence map:** structured literature coverage, not study-count decoration.
- **Timeline:** one declared time basis and proportional spacing unless labelled schematic.
- **Mindmap:** a readable explanatory hierarchy with explicit evidence-strength encoding.

## Iteration protocol

Inspect every candidate at full size and at its expected PDF width. Classify every defect:

- Add a `relationships` list (`from`, `relation`, `to`) and an `abbreviations`
  mapping to the spec whenever direction or local shorthand matters. Save the
  visual inspection as JSON, then run `scripts/qa_figure.py` with both the
  inspection and provenance; its pixel/spec gate makes blank pixels, missing
  copy, reversed arrows, unexpanded abbreviations, prohibited effects,
  collisions, too-small labels, weak finish, and distortion separate failures.

1. **Text defect:** misspelling, wrong font family, missing line, corrupted symbol.
2. **Data defect:** wrong number, interval, scale, denominator, or geometry.
3. **Science defect:** wrong anatomy, molecule, arrow, causal implication, or certainty.
4. **Composition defect:** overlap, crowding, poor balance, weak hierarchy, or illegible small text.
5. **Style defect:** serif/display typography, glossy 3D, cards, shadows, decorative icons, coloured prose, or journal branding.

Also reject poster framing: a hero title, oversized number, footer banner, or
uniform card grid that is visually louder than the scientific representation.

Generate at least two meaningfully different candidates. Use a targeted edit
for a local defect and regenerate from the same specification when hierarchy or
style is broadly wrong. Compare the candidates explicitly and save the reason
for selection. If dense copy is the only blocker, compose the strongest base
with the deterministic overlay. For an exact quantitative plot, use a
deterministic renderer directly; do not keep an attractive but mathematically
false plot.

## Acceptance contract

Accept only when:

- every required string appears exactly, in the selected style's natural-width font;
- every value, unit, interval, denominator and plotted magnitude matches the specification;
- every arrow and anatomical relationship matches the reviewed synthesis;
- uncertainty remains visible;
- the figure reads cleanly at normal chat width and in the exported PDF;
- no forbidden style element from the selected profile remains.
- composition, hierarchy, domain specificity, writing-style fit, and polish all pass;
- at least two generated candidates were compared for a generated/hybrid route;
- the raster matches `target_aspect_ratio`, no geometry distortion is reported,
  and PDF QA proves the intrinsic ratio was preserved during placement.
