# Communication-first figure production

Use quality contract v3 for every new Grounded journal-PDF figure and deck
content image. It turns the visual into a tested explanation: decide what the
reader should understand, compare three possible visual explanations, render
the strongest one, then inspect what the image actually communicates. Contract
v1 and v2 remain readable only so older releases can be reproduced.

## 0. Plan visual coverage from the synthesis

Journal PDFs aim for more explanatory graphics than earlier Grounded releases:
2 figures for small reviews, 3–4 for medium, and 5–6 for large, with hard
ceilings of 2, 5, and 8. Start with one whole-answer synthesis visual, then give
each additional figure a different evidence job: mechanism, study design, exact
quantitative result, comparison/moderator, or uncertainty/evidence boundary.
Fewer is valid when the verified synthesis genuinely contains fewer distinct
visual stories. Never hit a target by repeating a table, recolouring the same
topology, or adding decorative scene setting.

For popsci and ELI5, evaluate one optional `cutaway` plate after the ordinary
coverage plan. It earns a slot only when exposing a hidden interior removes a
real mental-imagination step, the evidence supports a faithful interior, the
plate adds a distinct explanatory job, and the whole plus its annotations will
survive at 390 px. It may use otherwise available room under the size ceiling;
it never displaces a stronger evidence job or raises the ceiling merely because
cutaways are attractive.

Apply the review-wide mix and capability check in `media-modes.md` before
individual renderer choices. An all-plot set is not the default scientific style.

## 1. Write the communication contract before choosing a renderer

For every figure, write a `communication_goal` with:

- `visual_question`: the single reader-facing question this figure answers;
- `panel_thesis`: why every section belongs in the same explanation;
- `reader_takeaway`: the one sentence a reader should be able to say after one look;
- `must_show`: the indispensable visual facts or relationships;
- `information_flow`: the intended eye path, in order;
- `evidence_boundary`: what the figure deliberately does not claim;
- `familiar_starting_point`: the recognizable visual idea from which the new
  concept can grow;
- `plain_language_explain_back`: the one sentence a non-specialist should be
  able to say without consulting the caption.

Do this before describing a layout. The figure is not successful because it is
attractive or contains the requested objects; it is successful only when the
selected pixels produce the declared understanding without distorting the
evidence.

## 2. Route by evidence type

At the start of media production, inspect the tools actually available in the
current agent environment, including deferred-tool discovery. Lack of an image
CLI or a worker-local generator does not establish absence from the session.

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
- If verified known numbers carry the message, use a deterministic
  `quantitative` plot with structured `data` and a deliberate `plot_design`, or
  use the `composite` route when a generated, text-free visual anchor adds
  genuine orientation. In a composite, all axes, values, uncertainty, and
  typography remain deterministic; generated pixels never encode magnitude.
- Every other figure uses the capable built-in image generator. Quality
  contract v3 has no hybrid illustration and no non-quantitative deterministic
  fallback. If a generator is unavailable, do not fake an illustration.

Record the result in `<figure-id>.provenance.json`; its canonical schema is in
`figure-inspection-contract.md`. When no generator is exposed, record how that
was determined in `generator_detection` (`method`, `evidence`) and tell the
reader, in one sentence of the delivery, that the figures are plots for that
reason.

## 3. Use one of three v3 routes

### `generated`

This is required for every non-quantitative figure, including qualitative
comparisons, evidence maps, timelines, and mind maps. The image generator
renders the complete selected concept and every essential in-figure string
directly in the pixels. Limit generated copy to eight strings, eight words per
string, and 32 words total. Put explanatory prose, qualifications, and citations
in the caption so text repair does not become the production process.

### `deterministic`

Use only for forest plots, exact axes, or other artifacts whose primary content
is verified mathematical geometry. A v3 deterministic spec must use the
`quantitative` archetype, carry non-empty structured `data`, and declare a
`plot_design` with chart type, encoding, reader path, and style rationale. Use
direct labels, restrained colour, intentional spacing, and profile-matched type;
library-default axes, legends, palettes, gridlines, and margins are failures.
The spec shape, the renderer's grammar, and the scaffold → lint → preview tools
are in `quantitative-figure-guide.md`.

### `composite`

Use only for a quantitative figure whose verified values remain the primary
evidence but whose reader benefits from one or more generated visual anchors.
Generate those anchors without text, scales, values, uncertainty, or
proportional encodings, then integrate them into a deterministic plotting
canvas without anisotropic scaling. The deterministic layer owns every label,
panel letter, axis, estimate, interval, and legend. Record a `composite_plan`
that names each generated asset, its orientation-only role, placement, and the
balance rationale. If deleting the generated asset does not reduce orientation
or comprehension, use the deterministic route instead.

## 4. Propose and select three illustration concepts

Before prompting ImageGen, create exactly three genuinely different concepts.
Each concept records a detailed image description, its information flow,
strengths, and risks. Score every concept from 1–5 for:

1. clarity — can the main point be grasped correctly;
2. simplicity — is every visual element earning its place;
3. completeness — are all must-show elements and the evidence boundary present;
4. elegance — is the explanation coherent, balanced, and visually refined;
5. intuitiveness — can a non-specialist reconstruct the explanation from the
   picture, starting from something recognizable and without hidden jargon.

Select the highest combined score; the winner must score at least 4 in every
dimension. Feed only the selected concept to the image prompt. Do not expose the
two rejected descriptions to the generator, because their layouts and motifs
can leak into a confused compromise.

Use an explain-back discipline inspired by Feynman, not a decorative “Feynman
style.” Prefer the most literal domain-native representation that works. Start
from something the reader can recognize, add one conceptual step at a time,
place every necessary term beside its referent, and remove anything that does
not help reconstruct the explanation. Use a metaphor only when it improves both
accuracy and comprehension; a clever but misleading analogy fails.

## 5. Plan one semantic system before panels

Every v3 figure declares a `semantic_plan` before layout:

- `entities` lists every meaningful object, its specific depiction,
  explanatory role, and evidence basis. Generic placeholders and undeclared
  decorative objects are forbidden.
- `connectors` lists every arrow or line by source, target, semantic meaning
  (`causal`, `temporal`, `transfer`, `comparison`, `association`, or
  `navigation`), and short label. If none is declared, no arrow or bracket may
  appear.
- `panel_jobs` assigns one distinct explanatory job to each labelled section.
  Related outcomes belong in one visual unit; a panel that merely redraws the
  previous result is invalid.
- `grouping_rationale` explains why related information is together and why
  genuinely different content is separate.
- `anatomy_subjects` declares every depicted person or animal requiring an
  original-size integrity check.
- `salience_targets` identifies visually vulnerable must-show entities that
  need deliberate contrast, size, and separation.
- `quantitative_decision` states whether verified numbers exist
  (`verified_numbers_available`), whether they carry the primary message
  (`numbers_carry_primary_message`), and why the route follows (`reason`). Primary known numbers
  always use deterministic rendering.
- `information_priority` classifies every entity as primary or supporting
  (`primary_entities`, `supporting_entities`), names non-essential elements to
  omit (`excluded_nonessential`), and records a `dominance_rationale` and a
  `deletion_test`. Primary
  entities must dominate area, contrast, and first fixation; background
  scenery, props, repeated motifs, and decorative furniture that do not change
  the explain-back sentence are forbidden.
- `uncertainty_encodings` ties every uncertainty mark to a declared entity
  (`target`), names the `source_of_uncertainty`, specifies the
  `visual_encoding`, and states the `reader_interpretation`. A generic question mark, dashed halo, outcome
  icon, or bare `uncertain` label does not communicate an evidence boundary.
- `cross_view_identity` declares repeated specimens or objects whose positions,
  membership, geometry, or other invariant features must remain registered
  across thresholds, filters, or states. Only the declared transformation may
  change.
- `representation_plan` declares whether the visual is literal or
  metaphor-assisted (`kind`), names its `evidence_native_anchor`, allows at
  most one cognitive translation step (`cognitive_translation_steps`), and
  requires a `literal_rejected_reason` when the literal option is rejected,
  plus `added_explanatory_value`, `arranged_elements`, and
  `arrangement_evidence_job`. It also declares whether objects are arranged as a lineup or set;
  such an arrangement is valid only when it performs a named evidence-encoding
  job rather than serving as presentation furniture.
- `cutaway_plan` is required only for the `cutaway` archetype. It declares the
  recognizable exterior silhouette, one coherent cut plane, the essential
  interior entity IDs, their evidence-supported spatial relationships, the
  annotation strategy, and the four-part suitability decision. Every exposed
  interior entity receives exactly one short callout with a declared
  `explanatory_role`; decorative transparency and exploded-parts views fail.
- `anatomical_context` is required for every anatomical subject. It names the
  orientation landmarks and focal region that must survive simplification so a
  reader can locate the finding and understand where an instrument or mechanism
  applies.

The caption title must name the actual subject or finding. A title that comments
on figure construction or admits that the panels answer different questions is
evidence that the concept should be split or reconceived.

## 5b. Plan panels and explanatory callouts in every writing style

Scientific, popsci, bullets, and ELI5 use the same reference system. Distinct
sections receive sequential uppercase panel labels `A`, `B`, `C`, `D`. Put a
short explanation beside the object it explains and use a thin leader line to
the exact target whenever adjacency alone is ambiguous. Record panel labels,
callout text, target, and whether a leader line is required in
`annotation_plan`; all rendered labels also belong in `exact_text`. A continuous
single composition may use no panels or callouts, but the rationale must say why.
Each callout also declares `background: opaque-white` when its text occupies
illustrated, photographic, textured, or otherwise busy pixels, or
`background: quiet-canvas` when clean white space already provides contrast.
Every callout sets `placement_priority: quiet-canvas-first`. An opaque plate is
fallback-only: it also records why moving the label to quiet canvas would break
the spatial relationship to its referent. Opaque plates use restrained padding
and never become decorative cards.

For a cutaway, place the label in surrounding white space whenever possible,
then lead inward to the exact structure. The leader starts at the label and
ends on the target without crossing unrelated layers. Keep the rendered copy
phone-short; `explanatory_role` records the full semantic job so a terse label
cannot become an unexplained anatomy tag. Allocate the 6–8% outer safety margin
and the label lanes before scaling the focal object; at a 1,536 px source, the
smallest primary callout line is at least 40 px high so it remains about 10 px
at the 390 px release view. Supporting labels remain at publication scale and
may require zoom; never enlarge the complete type system to satisfy the
primary-label gate. This preflight prevents repeated typography repairs after
an otherwise good composition.

## 5c. Fit the canvas to the information

Every v3 spec includes a `layout_plan` with content density, a boolean
`wide_canvas_required`, aspect-ratio rationale, balance strategy, and the
intended final display. Do not default to 2:1. A sparse single comparison
normally earns a compact landscape or near-square canvas; a sparse figure
wider than 1.75:1 is invalid unless `wide_canvas_required` is true because the
content has genuinely horizontal topology. Wide canvases otherwise belong to a
horizontal sequence, several aligned panels, or dense categorical coverage.
Inspect the full composition for optical centring, panel-weight balance, and
dead space at native and final size. Passing a numeric aspect-ratio check does
not rescue a lopsided or padded composition.

The canvas is exact `#FFFFFF` in scientific, popsci, bullets, and ELI5 figures.
Colour belongs to evidence-bearing objects, never to a full-page tint or paper
texture. The layout plan also declares a 390 px phone preview, one to three
primary wayfinding labels, a first-glance path of at most five steps, a 10 px
minimum rendered height for those primary labels, and the explain-back sentence
that must remain reconstructable without zoom. It explicitly records that not
every supporting label is required without zoom and how the caption or zoom
carries that detail. Inspect the preview as a separate release view; a large
native raster does not rescue a figure that becomes cognitively opaque on a
phone, but phone QA must not inflate supporting labels into display typography.
For a deterministic figure the renderer sizes each semantic role once across
all panels. A phone-primary point label promotes every comparable point label
to the same size; it never enlarges just one estimate. The renderer records
role sizes and measured primary-label heights in the geometry manifest; `qa_figure.py --geometry` uses that measurement, and
an inspection that attests a taller label than the raster contains fails.
Primary labels are the takeaway strings — a direct series or point label, a
reference-line label, or an annotation — never tick labels, which stay at
publication scale and may be as descriptive as the caption needs.
For a generated figure, each primary phone label is at most four words and 28
characters. Shorten the label rather than letting ImageGen shrink the whole
type system; supporting detail belongs in the caption.
For a generated asset whose only defect is an edge-connected near-white paper
tint, `scripts/normalize_figure_canvas.py` may flatten alpha and normalize that
paper to exact white. It must not erase content: any non-white content remaining
inside the five-percent safety band is a composition failure and requires
re-layout or regeneration.

## 5d. Apply physical and perceptual integrity gates

Inspect every depicted person or animal at original size. Extra, missing,
duplicated, fused, or impossible limbs, hands, digits, facial features, or
joints are release-blocking, even when anatomy is not the scientific subject.

Inspect every connector without consulting the prompt: its source, target, and
meaning must be evident. Reject decorative arrows, floating trajectories,
unexplained brackets, and visual objects with no declared role. Inspect every
salience target at final display size; pale-on-pale, too-small, overlapping, or
otherwise effectively invisible evidence fails. Remove redundant sections:
each panel must add comparison, consequence, uncertainty, mechanism, or
synthesis rather than repeat another panel.

Run a deletion test before rendering: remove each non-primary element in turn.
If the declared explain-back sentence and evidence boundary remain intact, omit
that element. Anatomical simplification is the exception only when the retained
landmarks still locate the focal region unambiguously. When the same specimen
appears in several views, compare registered features directly and reject any
unexplained identity drift.

Prefer a literal, evidence-native representation. A metaphor, tactile motif,
or arranged-object composition is acceptable only when it shortens the reader's
path from pixels to evidence. If the reader must first decode the visual device
and then translate it back into the scientific relationship, the representation
fails even when it is attractive.

## 5e. Bind quantitative semantics to their marks

Every v3 deterministic figure declares `plot_design.axis_semantics` for every
panel, using the exact rendered axis labels and a plain-language statement of
what each dimension means. It also declares a `caption_axis_summary`, a
`numeric_annotation_attachment`, and an `uncertainty_display` plan. The caption
must repeat what the x- and y-axes encode, including units or categories.

Render every y-axis label vertically outside the data region and every x-axis
label horizontally below it. Centre the complete plot, including external axis
labels and direct annotations, within its panel. Every interval, endpoint
value, difference, denominator, and numeric qualifier
must sit on, beside, or connect directly to the mark it describes. An interval
key is omitted for a conventional point-and-whisker encoding when the caption
already explains it. Add a compact legend only when two or more non-standard
encodings genuinely require decoding; state why in `plot_design.legend_plan`
(`needed`, `reason`, `placement`: `none` or `adjacent-to-marks`). The axis
placement rule above is declared verbatim in `plot_design.axis_label_placement`
(`x_orientation: horizontal`, `x_location: below-data-region`,
`y_orientation: vertical`, `y_location: outside-data-region`).
A forest plot encodes each confidence interval with the point's native
`x_interval`; a vertical point-and-whisker plot uses `y_interval`. Do not fake
an interval as a three-point trajectory merely to obtain a horizontal line.
A contrast interval is
attached to the contrast bracket or endpoint comparison it qualifies, never
placed halfway along unrelated trajectories. Direct labels may replace a
redundant legend, but they do not excuse an unnamed axis construct.

## 6. Generate, analyze, and repeat for meaning

For a generated conceptual figure:

1. Build the full prompt from the winning concept with `build_figure_prompt.py`.
2. Generate the complete composition with all essential typography directly in
   the image and inspect it at original size and expected PDF size.
3. Before reading the prompt again, write what a reader would actually
   understand, the eye path they would follow, and the sentence they could
   explain back without the caption. Compare that observation with
   `reader_takeaway`, `must_show`, `information_flow`, the familiar starting
   point, and `plain_language_explain_back`.
4. If meaning, evidence, copy, geometry, and every quality gate pass, select it.
   A passing first candidate is valid.
5. If the defect is local, make a targeted ImageGen edit. If the composition,
   meaning, flow, science, or several labels are broadly wrong, regenerate the
   selected concept or return to the three-concept decision and improve it.
6. Record every candidate in `post_generation_reviews`. A failed review must
   name concrete issues, decide `revise` or `regenerate`, and be followed by
   another attempt. The selected asset must be reviewed exactly once with
   `intended_meaning_conveyed: true`, `information_flow_clear: true`,
   `intuitive_without_caption: true`, an empty `unexplained_jargon` list, no
   issues, and `decision: accept`.
7. Compare candidates only when several exist. Never select a cheaper or more
   generic result merely because its text is easier to OCR.

The selected image must also read as one authored plate. All scientific objects
share a consistent level of abstraction, dimensionality, line treatment,
perspective, lighting, and material finish. Reject a candidate when its meaning
is assembled from glossy stock symbols, emoji-like objects, app pictograms,
sticker-like cutouts, or other visibly mismatched assets. A circle, badge, card,
or frame must encode a declared scientific boundary or grouping; it cannot be
used simply to make an isolated object feel diagrammatic. This is a release
gate under both `style_fit` and `polish`, not a subjective preference.

Mentally hide every label during the same review. The evidence-native visual
structure must still reveal the subject, the principal relationship, and the
intended reading direction. If the explanation collapses into a headline plus
recognizable objects, a sparse icon tableau, or an inventory whose meaning
exists mostly in words, reject the concept rather than polishing its text.

Primary labels are phone-first wayfinding, not miniature captions. Each names
one visible state, change, comparison, or conclusion in one short phrase.
Compound prose, stacked qualifiers, and policy wording that requires multiple
clauses belong in the external caption. Place the label directly on existing
white canvas whenever possible. A white backing over artwork remains a
documented fallback, never a default label style.

For deterministic and composite figures, data marks remain more visually
salient than labels. Direct annotations keep a clear gap from points,
trajectories, axes, and one another, and no label crosses a data line. A stated
interval is rendered as an attached whisker, band, bracket, or equivalent
graphical extent rather than the words `95% CI` floating beside a point. When
the primary 390 px label floor would crowd the evidence, shorten copy or change
topology/aspect ratio instead of inflating axes, ticks, notes, and every
annotation inside the same plot. Equivalent values, direct series labels, and interval annotations
use consistent size and weight within their respective roles across panels.
Glyph content and effect magnitude must never determine emphasis. If promoting
a role causes crowding, choose a short wayfinding annotation, change the layout,
or split the figure; do not shrink individual peer labels to fit.
Independent text boxes retain at least 3 px of clear separation in the
proportional 390 px preview; near-touching type is treated as a collision.

When a qualitative explanation depends on exact cross-view identity, whole-image
generation may be unable to preserve the same specimen, membership, and
geometry across repeated views. After at least two generated candidates or a
generated candidate plus targeted edit fail that declared invariant, v3 may use
the narrow `identity-preserving-composition` hybrid fallback. Generate one
text-free canonical asset, then duplicate, mask, register, connect, and typeset
it deterministically. Provenance must prove a declared `cross_view_identity`,
text-free generated source, deterministic identity geometry, preserved aspect
ratio, and every rejected attempt. This does not license hand-drawn substitute
illustrations or deterministic rendering merely for convenience.

The shared hybrid compositor represents each repeated canonical crop as an
`image_region` overlay item. It requires `asset` and `identity_key`, normalized
`source_x`, `source_y`, `source_width`, and `source_height`, normalized
destination `x` and `y`, and one uniform `scale`. The same `identity_key` must
occur at least twice. Its composition report records the resolved asset hash,
source crop, destination box, scale, and `anisotropic_resize: false`; release
QA rejects a missing identity repeat or any non-uniform resize.

Never ship a technically valid result when it is compositionally weak.
Do not endlessly polish an unsupported or scientifically incorrect image;
correctness remains the first gate.

## 7. Match the review's writing style

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
When the selected archetype is `cutaway`, the archetype module adds an
atlas-like scientific treatment, premium museum-editorial popsci treatment,
compact analytical bullets treatment, or simplified ELI5 “look inside”
treatment without changing the exterior, interior relationships, or labels.

## 8. Prevent stretching at every stage

Non-distortion is a hard invariant:

- Never resize a figure with independent width and height scales.
- Preserve the source aspect ratio during generation, plotting, export, PDF
  placement, rasterization, and thumbnail creation.
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
- The target ratio is content-driven, not a full-width quota. Compact figures
  may render narrower on the journal page when their final effective label size
  still passes; do not add empty horizontal space merely to preserve width.

## 9. Record inspection and provenance

After inspecting the selected pixels, write the visual inspection and generation
provenance records exactly as specified in
`figure-inspection-contract.md`. That reference owns both JSON schemas,
candidate-review requirements, and field-level interpretation. Run
`scripts/qa_figure.py` with the spec, image, inspection, and provenance before
embedding the asset.

## 10. Release decision

A figure is releasable only when all of the following are true:

- scientific/data QA passes;
- all fifteen visual-quality dimensions pass, including coherent thesis,
  anatomy, connector semantics, grouping, salience, non-redundancy, and typography;
- every meaningful object is declared and specific, every anatomical subject
  has been checked at original size, and every integrity issue list is empty;
- primary entities visibly dominate, non-essential elements fail closed under
  the deletion test, anatomical landmarks remain sufficient, repeated views
  preserve identity, and uncertainty marks explain the exact claim they qualify;
- the canvas ratio fits the information density and the complete composition is
  optically centred and balanced rather than padded to page width;
- callouts over busy pixels have opaque white backing and every typographic role
  uses one consistent natural-width house sans-serif family;
- the outer canvas is exact `#FFFFFF`, and the 390 px phone preview preserves
  one to three readable primary labels, the declared first-glance path, and the
  explain-back sentence without zoom, while supporting labels remain at compact
  publication scale;
- the robust upper text height and OCR text-box area remain below the
  typography-dominance ceilings, all multiword labels use sentence case, and
  abbreviation definitions or interpretive prose live in the caption rather
  than inside the artwork;
- the visual explanation survives a labels-hidden review: text remains
  subordinate, and no poster layout or isolated object inventory substitutes
  for evidence-bearing structure;
- deterministic and composite figures label every plotted construct and attach intervals and
  numeric annotations directly to their graphical referents, while captions
  repeat the x- and y-axis meanings;
- composite figures keep every quantitative encoding and all text deterministic,
  use generated assets only for orientation, and preserve each asset's intrinsic
  aspect ratio;
- the familiar starting point, declared takeaway, explain-back sentence,
  must-show list, and information flow pass an independent post-generation
  check without caption dependency or unexplained jargon;
- panel labels and explanatory callouts match the annotation plan;
- a cutaway preserves a recognizable exterior, one physically coherent cut
  plane, truthful interior spatial relationships, and complete one-to-one
  explanatory callouts at native and phone size;
- no geometry distortion is reported;
- its raster aspect matches the declared target;
- generation provenance satisfies the route rules;
- the selected candidate was inspected at final size;
- PDF placement preserves intrinsic aspect ratio.

"Correct but cheap" is a failed visual-quality result, not an acceptable final.

## 11. Generalize feedback without canonizing examples

Follow `figure-feedback-generalization.md`. Translate every observation into an
observable failure, topic-neutral rule, explicit v3 contract field, and
synthetic executable regression fixture. Do not publish a benchmark gallery,
produce before/after boards, or preserve temporary evaluation topics as
templates. Visual samples, when useful, are private, replaceable, and inspected
only as final candidates after the rule is frozen. A targeted edit may repair an
ordinary candidate, but it never counts as the general feedback implementation.
