# Generator-first figure production

Use this contract for every Grounded journal-PDF figure and deck content image.
It turns "prefer image generation" into an auditable production route while
preserving the evidence, exact-copy, and geometry guarantees elsewhere in the
skill.

## 0. Plan visual coverage from the synthesis

Journal PDFs aim for more explanatory graphics than earlier Grounded releases:
2 figures for small reviews, 3–4 for medium, and 5–6 for large, with hard
ceilings of 2, 5, and 8. Start with one whole-answer synthesis visual, then give
each additional figure a different evidence job: mechanism, study design, exact
quantitative result, comparison/moderator, or uncertainty/evidence boundary.
Fewer is valid when the verified synthesis genuinely contains fewer distinct
visual stories. Never hit a target by repeating a table, recolouring the same
topology, or adding decorative scene setting.

## 1. Probe capability before choosing a renderer

At the start of media production, inspect the tools actually available in the
current agent environment.

- If a capable built-in image generator is exposed, record
  `generator_available: true` and use it for the generated portion of every
  conceptual, mechanistic, anatomical, study-overview, timeline, popsci, or
  ELI5 figure.
- A generator is capable when it can create a project-bound raster, accept a
  detailed scientific art brief, support targeted edits, and return an image
  the agent can inspect. A vague assertion that the model is "not suitable"
  does not make it unavailable.
- Use the built-in generator before any API or CLI fallback. Copy the selected
  project asset into the review workspace; do not leave it only in a generator
  cache.
- Exact quantitative plots may use a deterministic renderer from the start.
  Their geometry is the evidence, so generation is not a quality upgrade.

Record the result in `<figure-id>.provenance.json`; the schema is below.

## 2. Choose one of three explicit routes

### `generated`

This is the default for every non-quantitative figure, including comparisons,
evidence maps, timelines, and mind maps. The image generator renders the
complete finished scientific composition and every required in-figure string
directly in the pixels on the first call. Keep copy concise because concise
figures read better, not because typography is deferred.

### `hybrid`

Hybrid is a last-resort repair route. Use it only after a complete direct-text
generation and either a targeted ImageGen edit or a genuinely different second
candidate still leave exact copy unusable. Preserve the strongest authored
composition, then add only the unresolved typographic/data layer with
`scripts/compose_hybrid_figure.py` or an equally deterministic overlay.

The provenance must record `direct_text_attempted: true`, the direct-text
attempt, the repair attempt, and a concrete `fallback_reason`. The generated
base must remain visible and materially useful in the final artifact; a token
background texture behind an otherwise deterministic diagram does not count as
hybrid.

### `deterministic`

Use directly for forest plots, exact axes, dense tables-as-figures, or other
artifacts whose primary content is mathematical geometry. For a non-quantitative
figure, this route is allowed only when no capable generator exists, or after
the iteration ladder below has failed and the provenance file records why.

## 3. Iterate for quality, not merely validity

For a generated conceptual figure:

1. Build the full structured prompt with `build_figure_prompt.py`.
2. Generate the complete composition with all exact typography directly in the
   image and inspect it at original size and expected PDF size.
3. If every gate passes, select it immediately. A second candidate is not a
   quota and a passing first candidate is not evidence of insufficient effort.
4. Make one targeted ImageGen edit when the defect is local, repeating the
   exact string plus scientific and geometry invariants while preserving the
   rest of the composition.
5. If composition, hierarchy, style, science, or several text elements are
   broadly weak, generate a genuinely different second candidate from the same
   evidence specification.
6. Compare candidates only when multiple candidates exist. Select for evidence
   fidelity, visual hierarchy, domain specificity, style fit, polish, and
   legibility—in that order. Do not select a visibly cheaper candidate merely
   because its OCR is easier.
7. If exact copy remains the only blocker after direct generation and repair,
   keep the strongest generated composition and switch to the hybrid route.
8. A pure deterministic fallback for a non-quantitative figure requires at
   least two generated candidates, at least one targeted edit, explicit hybrid
   consideration, and a concrete failure reason.

Never ship a technically valid result when it is compositionally weak.
Do not endlessly polish an unsupported or scientifically incorrect image;
correctness remains the first gate.

## 4. Match the review's writing style

`review_style` is required in new figure specifications and selects a writing-
style overlay from `figure-writing-style-overlays.json`:

| Review style | Figure identity |
|---|---|
| `scientific` | Precise journal-native scientific illustration; restrained colour, high information density, exact local annotation. |
| `popsci` | Premium editorial science art; one memorable focal visual, elegant tonal depth, less in-pixel copy, no marketing-infographic furniture. |
| `bullets` | Fast-scanning analytical visual; decisive hierarchy, compact comparison structure, strong but restrained contrast. |
| `eli5` | Warm explanatory illustration; concrete visual metaphor, friendly spatial storytelling, generous breathing room, never childish clip art. |

The writing-style overlay changes art direction, finish, palette, and permitted
typography. It never changes the evidence payload or certainty encoding.

## 5. Prevent stretching at every stage

Non-distortion is a hard invariant:

- Never resize a figure with independent width and height scales.
- Preserve the source aspect ratio during generation, hybrid composition,
  export, PDF placement, rasterization, and thumbnail creation.
- Circles and circular anatomical structures remain circular; squares remain
  square; regular axes retain equal unit geometry where applicable.
- Text uses natural font proportions. Never horizontally condense, expand,
  shear, or vertically stretch glyphs to make copy fit.
- Flatten transparent generated pixels onto the writing style's declared paper
  colour before export. Never discard alpha into black or noisy RGB pixels.
- Fit copy by editing, wrapping, moving, or reducing concepts—not by scaling
  one axis.
- Every new spec declares numeric `target_aspect_ratio` and may declare
  `geometry_invariants`. `qa_figure.py` checks the delivered raster ratio and
  rejects reported geometry distortion. PDF QA independently compares the
  intrinsic figure ratio with the PDF image transformation.

The hybrid compositor never resizes its base image. Its output dimensions are
identical to the generated input dimensions, and circles are drawn from one
radius measured against the shorter canvas edge. It also measures the original
geometry of every deterministic text envelope. Every text overlay requires an
explicit opaque background or a preceding opaque rectangle that fully contains
that envelope. Unmasked hybrid text is rejected categorically, preventing a
repair label from being painted over generated type without relying on any
topic, example, OCR engine, pixel colour, or tuned image threshold.

## 6. Visual inspection record

For `quality_contract_version: 1`, `<figure-id>.inspection.json` contains:

```json
{
  "ocr_text": "...",
  "minimum_label_height_px": 28,
  "relationships": [],
  "detected_effects": [],
  "text_collisions": [],
  "duplicate_text": [],
  "unlisted_text": [],
  "geometry_distortions": [],
  "visual_quality": {
    "composition": "pass",
    "hierarchy": "pass",
    "domain_specificity": "pass",
    "style_fit": "pass",
    "polish": "pass"
  }
}
```

Each `pass` is a real visual judgment made after viewing the selected pixels at
original size and expected PDF size. `duplicate_text` lists any label rendered
more than its manifest count; `unlisted_text` lists meaningful copy absent from
the manifest. Either list being non-empty is release-blocking. Empty or blank
pixels cannot be rescued by a manually supplied OCR transcript.

## 7. Generation provenance record

For `quality_contract_version: 1`, `<figure-id>.provenance.json` contains:

```json
{
  "schema_version": 1,
  "generator_available": true,
  "generator": {
    "tool": "built-in-imagegen",
    "supports_edit": true
  },
  "selected_route": "generated",
  "selected_asset": "figure.png",
  "selected_sha256": "<sha256>",
  "attempts": [
    {
      "kind": "generate",
      "asset": "figure.png",
      "outcome": "selected",
      "text_mode": "direct",
      "reason": "first candidate passed science, copy, geometry, and visual-quality gates"
    }
  ],
  "comparison": {
    "candidates_compared": 1,
    "selection_rationale": "The first complete direct-text candidate passed every gate."
  },
  "fallback_reason": null,
  "hybrid_considered": false
}
```

Use `kind: edit` for a targeted image edit and `kind: render` for a purely
deterministic candidate. Paths are case-local audit records; only the selected
asset must appear in the final review. The release manifest hashes the selected
figure, its specification, prompt, inspection, and provenance.

For a hybrid selection, additionally record `direct_text_attempted: true`, a
direct-text generate attempt (`text_mode: "direct"`), an edit attempt or second
generated candidate, `fallback_reason`, one `compose` attempt, and the existing
`hybrid` compositor/base/aspect record. `comparison` may be omitted when only
one candidate exists; if retained, use `candidates_compared: 1`.

## 8. Release decision

A figure is releasable only when all of the following are true:

- scientific/data QA passes;
- all five visual-quality dimensions pass;
- no geometry distortion is reported;
- its raster aspect matches the declared target;
- generation provenance satisfies the route rules;
- the selected candidate was inspected at final size;
- PDF placement preserves intrinsic aspect ratio.

"Correct but cheap" is a failed visual-quality result, not an acceptable final.
