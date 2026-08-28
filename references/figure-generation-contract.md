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

Use for text-light conceptual, mechanistic, anatomical, study-overview, and
editorial explanatory artwork. The image generator renders the finished
scientific composition. Keep in-pixel copy deliberately short.

### `hybrid`

This is the normal route for a visually rich figure that also contains exact
labels, numbers, arrows, or a legend. Generate the scientific illustration and
composition first, then add the exact typographic/data layer with
`scripts/compose_hybrid_figure.py` or an equally deterministic overlay.

Hybrid is not a fallback or a lesser result. It is the preferred way to retain
the generator's visual quality without asking a raster model to typeset a dense
manifest perfectly. The generated base must remain visible and materially
useful in the final artifact; a token background texture behind an otherwise
deterministic diagram does not count as hybrid.

### `deterministic`

Use directly for forest plots, exact axes, dense tables-as-figures, or other
artifacts whose primary content is mathematical geometry. For a non-quantitative
figure, this route is allowed only when no capable generator exists, or after
the iteration ladder below has failed and the provenance file records why.

## 3. Iterate for quality, not merely validity

For a generated or hybrid conceptual figure:

1. Build the full structured prompt with `build_figure_prompt.py`.
2. Generate a first composition and inspect it at original size and expected
   PDF size.
3. Make one targeted edit when the defect is local. Repeat the scientific and
   geometry invariants in the edit request.
4. If composition, hierarchy, or style is broadly weak, generate a genuinely
   different second candidate from the same evidence specification.
5. Compare at least two candidates side by side. Select for evidence fidelity,
   visual hierarchy, domain specificity, style fit, polish, and legibility—in
   that order. Do not select a visibly cheaper candidate merely because its OCR
   is easier.
6. If dense copy remains the only blocker, keep the strongest generated
   composition and switch to the hybrid overlay route.
7. A pure deterministic fallback for a non-quantitative figure requires at
   least two generated candidates, at least one targeted edit, explicit hybrid
   consideration, and a concrete failure reason.

Never ship the first technically valid result when it is compositionally weak.
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
radius measured against the shorter canvas edge.

## 6. Visual inspection record

For `quality_contract_version: 1`, `<figure-id>.inspection.json` contains:

```json
{
  "ocr_text": "...",
  "minimum_label_height_px": 28,
  "relationships": [],
  "detected_effects": [],
  "text_collisions": [],
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
original size and expected PDF size. Empty or blank pixels cannot be rescued by
a manually supplied OCR transcript.

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
  "selected_route": "hybrid",
  "selected_asset": "figure.png",
  "selected_sha256": "<sha256>",
  "attempts": [
    {
      "kind": "generate",
      "asset": "candidate-1.png",
      "outcome": "rejected",
      "reason": "weak hierarchy"
    },
    {
      "kind": "generate",
      "asset": "candidate-2.png",
      "outcome": "selected-base",
      "reason": "strongest composition"
    },
    {
      "kind": "compose",
      "asset": "figure.png",
      "outcome": "selected",
      "reason": "exact overlay added without rescaling"
    }
  ],
  "comparison": {
    "candidates_compared": 2,
    "selection_rationale": "Candidate 2 has the clearest scientific focal structure and best style fit."
  },
  "hybrid": {
    "compositor": "compose_hybrid_figure.py",
    "base_asset": "candidate-2.png",
    "anisotropic_resize": false
  },
  "fallback_reason": null,
  "hybrid_considered": true
}
```

Use `kind: edit` for a targeted image edit and `kind: render` for a purely
deterministic candidate. Paths are case-local audit records; only the selected
asset must appear in the final review. The release manifest hashes the selected
figure, its specification, prompt, inspection, and provenance.

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
