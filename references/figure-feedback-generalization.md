# Generalizing figure feedback

User feedback about a rendered figure is evidence about the shared figure
recipe. It is not permission to hand-tune that specimen, publish it as a
showcase, or preserve its topic as a permanent template.

## The invariant

An accepted change must be expressible without a subject name, case ID,
case-local path, named object from the criticized image, or magic coordinate.
It must add a portable rule and an executable regression check. If the proposed
change would not make sense for an unseen subject, another visual archetype,
and every applicable writing style, abstract it further.

Topics are disposable test inputs. The durable product is the contract, prompt
builder, renderer, inspection schema, and QA behavior.

## Translate the observation into a gate

Record this chain internally:

1. **Raw observation** — preserve what the user noticed.
2. **Observable failure** — describe what a reader can see or misunderstand.
3. **Failure class** — map it to a reusable dimension.
4. **General rule** — state the required behavior without topic vocabulary.
5. **Contract field** — identify what must be planned or inspected explicitly.
6. **Executable regression check** — create a topic-neutral fixture that fails
   when the rule is absent or violated.

Prefer invariant checks over aesthetic scores. The core reusable failure
classes are:

- **visual thesis** — one reader-facing question and one answer; every section
  must be necessary to that same explanation;
- **entity specificity** — every intervention, comparator, marker, instrument,
  anatomical structure, or other meaningful object is identifiable and earns
  its place;
- **anatomical integrity** — no extra, missing, fused, duplicated, or
  impossible body parts;
- **connector semantics** — every arrow or line has a declared source, target,
  and meaning; decorative or ambiguous connectors are forbidden;
- **logical grouping** — related results share one visual unit, while separate
  panels must contribute genuinely different information;
- **salience** — every must-show element is visible at final size with enough
  contrast and size to perform its explanatory job;
- **non-redundancy** — a later panel must add comparison, consequence,
  uncertainty, or synthesis rather than redraw the preceding panel;
- **quantitative routing** — verified values that carry the message use the
  deterministic route;
- **typographic finish** — clean upright sans-serif type, restrained hierarchy,
  collision-free placement, and no default-chart appearance.
- **visual content budget** — primary entities dominate; supporting entities
  clarify rather than compete; props, scenery, background furniture, and
  repeated motifs that do not change the explain-back sentence are removed.
- **anatomical context sufficiency** — simplification retains the landmarks
  needed to locate the focal region and understand the depicted instrument,
  symptom, or mechanism.
- **cross-view identity** — repeated specimens or objects preserve registered
  positions, membership, and geometry so a threshold, filter, or state change
  is the only difference.
- **identity-preserving fallback** — when repeated-view identity is itself the
  evidence and generation repeatedly drifts, one text-free generated canonical
  asset may be duplicated/masked/typeset deterministically under audited v3
  hybrid provenance; aesthetic convenience alone never triggers this route.
- **uncertainty semantics** — uncertainty is attached to the exact claim or
  quantity and tells the reader what cannot be concluded; a generic symbol or
  bare qualifier is insufficient.
- **quantitative attachment** — axes name their constructs and units or
  categories; captions repeat both axis meanings; every interval and numeric
  annotation visibly belongs to its estimate, endpoint, or contrast.
- **content-fit and balance** — the aspect ratio follows information topology
  and density; sparse content does not sit in an arbitrarily broad canvas, and
  the final composition has an intentional optical centre without dead gutters.
  A sparse v3 figure wider than 1.75:1 must explicitly prove that horizontal
  topology requires the width.
- **composite evidence integrity** — when a generated visual anchor helps a
  quantitative figure, exact values, axes, intervals, and typography stay on a
  deterministic layer; the generated component is text-free, undistorted, and
  never carries magnitude.
- **axis and legend convention** — y-axis labels are vertical and outside the
  data region, x-axis labels are horizontal below it, and conventional
  point-and-interval glyphs do not receive a redundant floating legend.
- **annotation backing** — explanatory copy over non-quiet pixels uses an
  opaque white backing plate with padding only after quiet-canvas placement has
  been considered and rejected for a stated spatial reason; callouts on clean
  white space remain unboxed.
- **font-system consistency** — panels, axes, values, callouts, and legends use
  one natural-width house sans-serif family within a figure.
- **paper integrity** — the canvas is exact `#FFFFFF` in every writing style;
  full-canvas tints and paper textures are forbidden even when the object
  palette is warm.
- **phone-scale comprehension** — at a 390 px preview, primary labels remain
  readable without zoom and the first-glance path still yields the declared
  explain-back sentence.
- **representation economy** — prefer evidence-native scientific structures;
  a metaphor or arranged-object treatment fails when it adds a decoding step
  that a literal representation would avoid.
- **visual-language coherence** — every element belongs to one authored visual
  system: consistent abstraction, dimensionality, line treatment, lighting,
  and material finish. A collage of glossy symbols, emoji-like objects, stock
  pictograms, or mismatched illustration styles fails even when each object is
  individually recognizable. Circles, badges, cards, and frames must encode a
  declared scientific boundary or comparison, never merely make an isolated
  object look like an icon.
- **mobile label simplicity** — each primary label names one visible state,
  change, comparison, or conclusion in a short phrase. Compound policy prose,
  stacked qualifiers, unexplained shorthand, and labels that need punctuation
  to hold multiple ideas move to the caption.

## Change the recipe, not the specimen

Never implement feedback with a subject noun in a shared prompt, a case-local
exception, a one-off `avoid` string, a topic-specific coordinate, or an edit
instruction that exists only for the criticized asset. A targeted ImageGen edit
may repair an ordinary production candidate, but it is not evidence that the
feedback generalized.

## Validate forward, without before/after showcases

Do not create public benchmark galleries or before/after boards. Do not promote
temporary test topics into the README. Acceptance is forward-looking:

1. add the topic-neutral contract or QA rule;
2. add a minimal synthetic regression fixture for the failure;
3. run the focused tests and the complete suite;
4. when visual sampling is useful, choose replaceable topics after the rule is
   frozen and inspect only the final candidates against the same contract;
5. keep the sample set private and rotate it so examples cannot become prompt
   templates.

For a multi-image sampling run, one independent owner may still be assigned to
each image. Owners receive only the shared recipe and their isolated spec; they
must not edit the recipe or another image. The coordinator accepts a rule only
when every sampled final candidate passes. The result is a gate audit, not a
comparative showcase.

The complete Python test suite is the canonical machine-readable gate. Old
visual experiments may remain as local audit history, but they are not shipped,
linked, or treated as canonical topics.
