# Modular prompt guide for scientific figures

Build prompts with `scripts/build_figure_prompt.py`; do not improvise one long
prose prompt from memory. The builder encodes the visual audit in
`figure-reference-analysis.md` and assembles six independent modules:

1. **Evidence specification** — what the reviewed literature supports.
2. **Figure archetype** — how that evidence should be organized.
3. **Style profile** — font, palette, composition, and exclusions.
4. **Render context** — article figure or standalone figure.
5. **Exact-text manifest** — every in-figure string that must appear verbatim.
6. **QA contract** — what must be inspected and when to fall back.

## Minimal specification

```json
{
  "profile": "nature-neuroscience",
  "archetype": "mechanism",
  "render_context": "article",
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
  ]
}
```

Generate the prompt with one command:

```bash
python3 scripts/build_figure_prompt.py --spec examples/image-mrna-vaccines-mechanism.figure.json
```

Use `--profile` or `--archetype` to test a different visual treatment without rewriting the evidence specification. Use `--out` only for a scratch prompt file.

## Specification fields

Required:

- `purpose`: one sentence describing what the reader should understand.
- `title`: the figure title.
- `story`: ordered, evidence-backed visual statements.
- `exact_text`: every required title, label, number, unit, qualifier, legend entry, and glossary line.

Optional:

- `profile`: `nature-neuroscience` (default), `nature-reviews`, or `nature-data`.
- `archetype`: `mechanism`, `anatomical-mechanism`, `study-overview`,
  `comparison`, `quantitative`, `evidence-map`, `timeline`, or `mindmap`.
- `render_context`: `article` (the profile default) or `standalone`.
- `subtitle`: short scope or evidence qualifier.
- `observed`: findings directly observed in cited human or experimental data.
- `inferred`: synthesis, model-supported, animal-only, mixed, or uncertain relationships.
- `data`: structured values, intervals, units, scales, sample sizes, and denominators.
- `layout_notes`: topic-specific arrangement requirements.
- `constraints`: scientific or production invariants.
- `avoid`: topic-specific failure modes appended to the profile exclusions.
- `style_overrides`: narrow profile changes such as `canvas.aspect` or a palette value. Do not use this field to change evidence.

## Prompting rules

- Ask for the complete finished figure, including text, in one render.
- In `article` context, treat `title` and `subtitle` as caption context and do
  not render them inside the artwork. In `standalone` context, render the title
  compactly and include it in `exact_text`.
- Quote every required in-figure string through `exact_text`; spell difficult
  labels exactly once rather than offering variants. The builder removes an
  exact title/subtitle match from the in-figure manifest in `article` context.
- State `Arial throughout` as a hard requirement and explicitly ban serif type.
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

Inspect the first render at full size and at its expected PDF width. Classify every defect:

1. **Text defect:** misspelling, wrong font family, missing line, corrupted symbol.
2. **Data defect:** wrong number, interval, scale, denominator, or geometry.
3. **Science defect:** wrong anatomy, molecule, arrow, causal implication, or certainty.
4. **Composition defect:** overlap, crowding, poor balance, weak hierarchy, or illegible small text.
5. **Style defect:** serif/display typography, glossy 3D, cards, shadows, decorative icons, coloured prose, or journal branding.

Also reject poster framing: a hero title, oversized number, footer banner, or
uniform card grid that is visually louder than the scientific representation.

Use one targeted edit for a local defect. Regenerate from the same specification if the hierarchy or style is broadly wrong. For an exact quantitative plot, switch to equal-size evidence cards or the deterministic fallback after one failed geometry correction; do not keep an attractive but mathematically false plot.

## Acceptance contract

Accept only when:

- every exact-text string appears correctly in Arial-style sans serif;
- every value, unit, interval, denominator and plotted magnitude matches the specification;
- every arrow and anatomical relationship matches the reviewed synthesis;
- uncertainty remains visible;
- the figure reads cleanly at normal chat width and in the exported PDF;
- no forbidden style element from the selected profile remains.
