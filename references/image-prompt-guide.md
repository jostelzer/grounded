# Modular prompt guide for scientific figures

Build prompts with `scripts/build_figure_prompt.py`; do not improvise one long
prose prompt from memory. Read `figure-generation-contract.md` first. The
builder encodes the visual audit in `figure-reference-analysis.md` and assembles
ten independent modules:

1. **Communication goal** — what the reader should understand and in what order.
2. **Three-concept decision** — the selected detailed visual explanation and why it won.
3. **Evidence specification** — what the reviewed literature supports.
4. **Figure archetype** — how that evidence should be organized.
5. **Scientific profile** — domain grammar, composition, and exclusions.
6. **Writing-style overlay** — distinct scientific, popsci, bullets, or ELI5 art direction and typography.
7. **Render route** — generated illustration, deterministic quantitative plot,
   or composite quantitative plot with generated text-free anchors.
8. **Render context** — article, standalone, or 16:9 deck-slide figure.
9. **Panel/callout and exact-text manifests** — referenceable sections, explanatory pointers, and essential strings.
10. **Meaning, quality, and geometry contract** — what must be inspected and proved before release.

## Minimal specification

```json
{
  "quality_contract_version": 3,
  "profile": "nature-reviews",
  "archetype": "mechanism",
  "review_style": "scientific",
  "render_route": "generated",
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
    "A",
    "B",
    "Package",
    "Translate",
    "Signal",
    "Memory"
  ],
  "communication_goal": {
    "visual_question": "How can a temporary RNA message create lasting immune memory?",
    "panel_thesis": "Every section follows the same message from delivery through translation to memory.",
    "reader_takeaway": "A temporary protected RNA message is translated, then disappears while immune memory remains.",
    "must_show": ["protected delivery", "cytoplasmic translation", "temporary message", "lasting memory"],
    "information_flow": ["Follow the package into the cell", "See translation", "See the message fade", "End at immune memory"],
    "evidence_boundary": "This is a supported mechanism schematic, not a proportional time course.",
    "familiar_starting_point": "A temporary recipe is delivered, used, and then disappears.",
    "plain_language_explain_back": "The temporary RNA recipe disappears after use, but the immune system keeps the memory."
  },
  "concepts": [
    {
      "id": "cell-journey",
      "description": "One continuous cell cutaway with the package entering at left, translation central, fading message above, and memory cells emerging at right.",
      "information_flow": ["package", "translation", "fading message", "memory"],
      "strengths": ["one uninterrupted eye path", "domain-native anatomy"],
      "risks": ["must not imply proportional timing"]
    },
    {
      "id": "paired-times",
      "description": "Two aligned cell states: early translation and later immune memory, joined by one restrained transition.",
      "information_flow": ["early state", "transition", "later state"],
      "strengths": ["simple contrast"],
      "risks": ["hides intermediate signalling"]
    },
    {
      "id": "nested-scales",
      "description": "A nested zoom from injection site to cell to molecular translation, returning outward to memory cells.",
      "information_flow": ["body", "cell", "molecule", "memory"],
      "strengths": ["complete scale story"],
      "risks": ["more visually demanding"]
    }
  ],
  "concept_selection": {
    "selected_id": "cell-journey",
    "selection_rationale": "It is the clearest complete explanation with the simplest continuous eye path.",
    "evaluations": [
      {"id": "cell-journey", "clarity": 5, "simplicity": 5, "completeness": 4, "elegance": 5, "intuitiveness": 5, "assessment": "Best overall."},
      {"id": "paired-times", "clarity": 4, "simplicity": 5, "completeness": 3, "elegance": 4, "intuitiveness": 4, "assessment": "Too much mechanism is lost."},
      {"id": "nested-scales", "clarity": 3, "simplicity": 2, "completeness": 5, "elegance": 4, "intuitiveness": 3, "assessment": "Complete but too complex."}
    ]
  },
  "annotation_plan": {
    "panel_labels": ["A", "B"],
    "callouts": [
      {"text": "Translate", "target": "ribosomes in the cytoplasm", "leader_line": true}
    ],
    "rationale": "Two referenceable stages aid discussion; the translation target needs a precise pointer."
  },
  "semantic_plan": {
    "entities": [
      {"id": "package", "depiction": "a specific lipid package entering a cell", "role": "protect and deliver the message", "evidence_basis": "supported delivery step"},
      {"id": "translation", "depiction": "ribosomes using the message in the cytoplasm", "role": "produce the antigen", "evidence_basis": "supported translation step"},
      {"id": "memory", "depiction": "recognizable immune memory cells", "role": "the lasting response", "evidence_basis": "supported immune outcome"}
    ],
    "connectors": [
      {"from": "package", "to": "translation", "meaning": "temporal", "label": "deliver then translate"},
      {"from": "translation", "to": "memory", "meaning": "causal", "label": "recruits memory"}
    ],
    "panel_jobs": [
      {"label": "A", "job": "show delivery and translation", "adds_distinct_information": true},
      {"label": "B", "job": "show the resulting immune memory", "adds_distinct_information": true}
    ],
    "grouping_rationale": "Delivery and translation are one stage; the later response is the distinct consequence.",
    "anatomy_subjects": [],
    "salience_targets": ["package", "translation", "memory"],
    "quantitative_decision": {
      "verified_numbers_available": false,
      "numbers_carry_primary_message": false,
      "reason": "The figure explains a qualitative mechanism rather than an effect magnitude."
    }
  }
}
```

Generate the prompt with one command:

```bash
python3 scripts/build_figure_prompt.py --spec figure.json
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

Required by `quality_contract_version: 3`:

- `review_style`: `scientific`, `popsci`, `bullets`, or `eli5`; this selects
  the matching overlay in `figure-writing-style-overlays.json`.
- `render_route`: `generated` for a non-quantitative figure, `deterministic`
  for a quantitative plot with verified `data`, or `composite` when a
  text-free generated anchor materially improves that quantitative plot.
- `target_aspect_ratio`: numeric width divided by height; choose it from content
  density and topology rather than defaulting to a broad canvas. Slides remain
  exactly 16/9.
- `layout_plan`: content density, boolean `wide_canvas_required`, aspect-ratio
  rationale, optical-balance strategy, and intended final display.
- `visual_anchor`: one concrete, domain-specific focal structure for every
  non-quantitative figure.
- `communication_goal`: the reader takeaway, must-show elements, intended
  information flow, evidence boundary, familiar visual starting point,
  reader-facing visual question, single panel thesis, and the one-sentence
  plain-language explain-back target.
- `concepts` and `concept_selection`: exactly three detailed alternatives plus
  clarity/simplicity/completeness/elegance/intuitiveness scoring for generated
  illustrations.
- `annotation_plan`: sequential uppercase `A`–`D` panel labels where sections
  exist, concise explanatory callouts, exact targets, and leader-line decisions.
- `semantic_plan`: specific meaningful entities, typed connectors, distinct
  panel jobs, grouping rationale, anatomical subjects, salience targets, and
  the quantitative-routing decision. It also requires a visual information
  priority, explicit uncertainty encodings, cross-view identity constraints,
  and sufficient context for every anatomical subject.
- `plot_design`: required for deterministic quantitative figures; chart type,
  encoding, reader path, style rationale, and a `typography` object declaring a
  clean sans-serif family/fallback plus `upright_natural_width: true`. V3 plots
  additionally declare per-panel axis semantics, a caption axis summary,
  numeric-annotation attachment, and uncertainty-display attachment.
- `composite_plan`: required for the composite route; names each generated
  text-free asset, its orientation-only role and placement, the deterministic
  evidence layer, and the integration/balance rationale.

Optional:

- `profile`: `nature-reviews` (default), `nature-neuroscience`, or `nature-data`.
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
- `generated_text`: legacy quality-contract-v1 field only. New generated
  figures render every essential in-figure `exact_text` string directly.
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
- Require one visual question and one answer. Reject a concept whose title or
  panel structure admits that it combines independent questions.
- On the `generated` route, ask for the complete, fully typeset finished figure
  in the first ImageGen call. Explicitly prohibit a textless base, blank label
  zones, placeholders, and pseudo-text. Keep the manifest to at most eight
  essential strings, eight words each, and 32 words total; caption prose is not
  image copy. On `deterministic`, treat the prompt as a production brief for
  mathematically faithful but bespoke publication rendering.
- In `article` context, treat `title` and `subtitle` as caption context and do
  not render them inside the artwork. In `standalone` context, render the title
  compactly and include it in `exact_text`. In `slide` context, keep the title,
  citations, evidence chip, masthead, and slide counter out of the pixels.
- Quote every required in-figure string through `exact_text`; spell difficult
  labels exactly once rather than offering variants. The generated prompt
  contains one literal manifest only; surrounding instructions refer to that
  manifest without repeating its strings. The builder removes an
  exact title/subtitle match from the in-figure manifest in `article` and
  `slide` contexts.
- Render only the selected concept. Rejected concept descriptions stay in the
  audit spec and out of the prompt so visual motifs cannot leak across options.
- Use uppercase `A`, `B`, `C`, `D` for distinct sections in every writing style.
  Keep explanatory callouts beside their target and use a thin leader line when
  adjacency alone is ambiguous.
- Put callout text on an opaque white backing plate with restrained padding
  whenever it overlaps non-quiet pixels; clean white canvas may remain unboxed.
- Use one natural-width house sans-serif family consistently across panel
  letters, callouts, axes, values, and legends.
- Apply the explain-back test: begin from a recognizable literal structure,
  bridge to the unfamiliar idea one step at a time, define necessary terms at
  their referents, and remove any mark that does not help a non-specialist say
  the declared plain-language sentence. Do not force a metaphor when the
  domain-native mechanism is already clearer.
- Use the writing-style font policy: Arial/Helvetica for scientific, Helvetica
  Neue/Arial for popsci and bullets, and Seravek/
  Helvetica Neue for ELI5. Always require natural-width glyphs and forbid
  condensed, expanded, sheared, outlined, or shadowed type.
- Describe what should be seen, not which software operations to simulate.
- Start from the domain-native visual representation—anatomy, signal flow,
  experiment, task, mathematical geometry, or data. Do not force the content
  into equal cards or a presentation-slide sequence.
- Use alignment and white space before boxes, local labels before a glossary,
  and thin neutral connectors before coloured arrows.
- Render only declared semantic objects. Every connector must use its declared
  source, target, and meaning; do not invent decorative arrows or brackets.
- Allocate the dominant area, contrast, and first fixation to the primary
  entities. Remove any prop, scenery, background treatment, or repeated motif
  whose deletion leaves the explain-back sentence unchanged.
- When one specimen or object appears in several views, preserve its registered
  identity and invariant features; change only the declared threshold, filter,
  state, or transformation.
- When anatomy is simplified, retain enough orientation landmarks to locate the
  focal region and understand any depicted instrument or mechanism.
- Tie uncertainty to the exact claim or quantity it qualifies and state what it
  changes in the reader's interpretation; never rely on a generic icon, dashed
  halo, question mark, or bare uncertainty label.
- Keep related outcomes in one visual unit. A new panel must add distinct
  information rather than repeat a prior result.
- For every depicted person or animal, explicitly reject extra, missing,
  duplicated, fused, or impossible body parts and verify anatomy at original size.
- Give every salience target enough size, contrast, separation, and colour to
  remain visible at the final display width.
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
6. **Thesis defect:** panels answer different questions or the title describes figure construction rather than the subject.
7. **Integrity defect:** extra or impossible anatomy, undeclared objects, or a connector with no clear semantic role.
8. **Grouping defect:** related results are split clumsily or a later panel repeats the previous panel.
9. **Salience defect:** a must-show element disappears through low contrast, tiny size, overlap, or poor separation.
10. **Typography defect:** crowded labels, inconsistent hierarchy, flared/display faces, or default-chart placement.

Also reject poster framing: a hero title, oversized number, footer banner, or
uniform card grid that is visually louder than the scientific representation.

Inspect the first complete candidate without using the prompt as an answer key:
write the observed takeaway and eye path from the pixels. Select it when meaning,
flow, evidence, copy, style, and geometry all pass. Use a targeted ImageGen edit
for a local defect and regenerate when hierarchy, style, science, meaning, flow,
or several text elements are broadly wrong. A failed communication review must
name the issue and be followed by another attempt. Compare candidates and save
the selection reason only when more than one exists. For an exact quantitative
plot, use a deterministic renderer directly; do not keep an attractive but
mathematically false plot or library-default styling.
Deterministic plots use clean upright sans-serif type with a shallow hierarchy,
preflighted text boxes, collision-free labels, and deliberate whitespace.
Article display faces do not carry into plotted evidence.
Axes must name the represented construct and unit or category. Place every
vertical y-axis label outside the data region and the horizontal x-axis label
below it. Omit a legend for a conventional point-and-whisker encoding when the
caption explains it; when a non-standard legend is genuinely needed, place it
beside the relevant marks, not in an axis-title position. Centre and balance
the complete composition, including external labels and annotations. Attach
each numeric annotation or contrast interval directly to its endpoint,
estimate, or bracket. Captions repeat both axis meanings in plain language.

## Acceptance contract

Accept only when:

- every required string appears exactly, in the selected style's natural-width font;
- every value, unit, interval, denominator and plotted magnitude matches the specification;
- every arrow and anatomical relationship matches the reviewed synthesis;
- uncertainty remains visible;
- the figure reads cleanly at normal chat width and in the exported PDF;
- no forbidden style element from the selected profile remains.
- composition, hierarchy, domain specificity, writing-style fit, and polish all pass;
- concept coherence, anatomical integrity, connector semantics, logical
  grouping, salience, non-redundancy, and typography all pass;
- every semantic object is declared, every anatomical subject is checked at
  original size, and every integrity issue list is empty;
- explanatory value and information flow pass;
- intuitiveness passes: the familiar starting point is visible, no unexplained
  jargon remains, and the figure can be explained back without its caption;
- the observed takeaway matches the communication goal, every must-show element
  is visible, and the observed eye path is clear;
- sequential uppercase panel labels and planned explanatory callouts point to
  their intended targets;
- the aspect ratio fits the content density, the optical centre is balanced,
  busy-region callouts have opaque white backing, and all typographic roles use
  the declared house font system;
- composite figures keep generated assets text-free and orientation-only while
  the deterministic layer owns every value, axis, interval, and label;
- the first complete candidate passed, or any additional candidates were explicitly compared;
- the raster matches `target_aspect_ratio`, no geometry distortion is reported,
  and PDF QA proves the intrinsic ratio was preserved during placement.
