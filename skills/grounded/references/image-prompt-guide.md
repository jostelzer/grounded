# Modular prompt guide for scientific figures

Read `figure-generation-contract.md` first. This reference covers only the
structured specification-to-prompt step. Build prompts with
`scripts/build_figure_prompt.py`; do not improvise one long prose prompt and do
not copy a past topic's visual motifs into a new figure.

The builder combines independent modules: communication goal, selected concept,
evidence specification, archetype, scientific profile, writing-style overlay,
render route, render context, annotation/exact-text manifests, and geometry
constraints. Rejected concepts remain in the audit specification but are never
shown to the image generator.

## Command

```bash
python3 scripts/build_figure_prompt.py --spec figure.json --out figure.prompt.txt
```

Use `--profile`, `--archetype`, `--review-style`, or `--render-route` only
to test an intentional treatment change. Save the selected prompt as provenance.

## Topic-neutral specification shape

The contract validators own the exact field requirements. A new v3 specification
has this general shape; replace placeholders with synthesis-grounded content
rather than retaining them as rendered copy:

```json
{
  "quality_contract_version": 3,
  "profile": "nature-reviews",
  "archetype": "<route-appropriate archetype>",
  "review_style": "<scientific|popsci|bullets|eli5>",
  "render_route": "<generated|deterministic|composite>",
  "render_context": "<article|standalone|slide>",
  "target_aspect_ratio": 1.5,
  "purpose": "<one communication purpose>",
  "title": "<caption title>",
  "story": ["<ordered supported statement>"],
  "exact_text": ["<essential rendered string>"],
  "communication_goal": {
    "visual_question": "<one reader-facing question>",
    "panel_thesis": "<why all sections form one explanation>",
    "reader_takeaway": "<one-look takeaway>",
    "must_show": ["<indispensable visual fact>"],
    "information_flow": ["<ordered eye-path step>"],
    "evidence_boundary": "<what the image does not claim>",
    "familiar_starting_point": "<recognizable entry point>",
    "plain_language_explain_back": "<caption-independent sentence>"
  },
  "layout_plan": {
    "content_density": "<sparse|moderate|dense>",
    "wide_canvas_required": false,
    "aspect_ratio_rationale": "<why this topology earns the ratio>",
    "balance_strategy": "<how optical weight is centered>",
    "final_display": "<intended delivered size>",
    "mobile_preview": {
      "width_px": 390,
      "minimum_primary_label_height_px": 10,
      "all_labels_required_without_zoom": false,
      "primary_labels": ["<up to three first-glance labels>"],
      "first_glance_path": ["<up to five ordered steps>"],
      "supporting_detail_strategy": "<how zoom or the caption carries compact supporting labels>",
      "explain_back_without_zoom": "<what remains clear on a phone>"
    }
  },
  "concepts": [
    {
      "id": "<concept-one>",
      "description": "<complete visual description>",
      "information_flow": ["<step>"],
      "strengths": ["<strength>"],
      "risks": ["<risk>"]
    },
    {
      "id": "<concept-two>",
      "description": "<genuinely different description>",
      "information_flow": ["<different step>"],
      "strengths": ["<strength>"],
      "risks": ["<risk>"]
    },
    {
      "id": "<concept-three>",
      "description": "<genuinely different description>",
      "information_flow": ["<different step>"],
      "strengths": ["<strength>"],
      "risks": ["<risk>"]
    }
  ],
  "concept_selection": {
    "selected_id": "<highest-scoring concept>",
    "selection_rationale": "<why it communicates best>",
    "evaluations": [
      {
        "id": "<concept-one>",
        "clarity": 5,
        "simplicity": 5,
        "completeness": 5,
        "elegance": 5,
        "intuitiveness": 5,
        "assessment": "<brief assessment>"
      },
      {
        "id": "<concept-two>",
        "clarity": 4,
        "simplicity": 4,
        "completeness": 4,
        "elegance": 4,
        "intuitiveness": 4,
        "assessment": "<brief assessment>"
      },
      {
        "id": "<concept-three>",
        "clarity": 4,
        "simplicity": 4,
        "completeness": 4,
        "elegance": 4,
        "intuitiveness": 4,
        "assessment": "<brief assessment>"
      }
    ]
  },
  "annotation_plan": {
    "panel_labels": [],
    "callouts": [],
    "rationale": "<why panels/callouts are or are not needed>"
  },
  "semantic_plan": {
    "entities": [],
    "connectors": [],
    "panel_jobs": [],
    "grouping_rationale": "<one coherent grouping rationale>",
    "anatomy_subjects": [],
    "anatomical_context": [],
    "salience_targets": [],
    "information_priority": {},
    "uncertainty_encodings": [],
    "cross_view_identity": [],
    "representation_plan": {
      "kind": "<literal|metaphor-assisted>",
      "evidence_native_anchor": "<literal scientific structure>",
      "cognitive_translation_steps": 0,
      "literal_rejected_reason": null,
      "added_explanatory_value": "<why this is the shortest route to the evidence>",
      "arranged_elements": false,
      "arrangement_evidence_job": null
    },
    "cutaway_plan": {
      "exterior_silhouette": "<recognizable whole-object orientation anchor>",
      "cut_plane": "<one coherent section and viewpoint>",
      "interior_entities": ["<declared entity id>"],
      "spatial_relationships": ["<truthful nesting or adjacency rule>"],
      "annotation_strategy": "<how short labels and leaders explain the interior>",
      "suitability": {
        "hidden_interior_removes_mental_step": true,
        "faithful_interior_supported": true,
        "distinct_evidence_job": true,
        "phone_readable": true,
        "reason": "<why this cutaway earns a figure slot>"
      }
    },
    "quantitative_decision": {
      "verified_numbers_available": false,
      "numbers_carry_primary_message": false,
      "reason": "<route rationale>"
    }
  }
}
```

Omit `cutaway_plan` unless `archetype` is `cutaway`. For a cutaway, every ID in
`interior_entities` must be a declared semantic entity and must be the target of
exactly one `annotation_plan.callouts` item. That callout also declares a
non-empty `explanatory_role` describing what the short rendered label teaches.

Generated figures require all three concepts and complete evaluations. The
selected concept must have the highest total and score at least four in every
dimension. Deterministic figures omit generated-concept fields and supply
structured `data` plus `plot_design`. Composite figures additionally supply
`composite_plan`; generated assets are text-free and orientation-only.

## Field guidance

- `purpose`, `visual_question`, and `reader_takeaway` each express one job.
- `story` contains ordered, evidence-backed visual statements.
- `exact_text` is the complete manifest of rendered labels, values, units,
  qualifiers, panel letters, and callout copy.
- `target_aspect_ratio` follows content topology. A sparse wide canvas requires
  an explicit horizontal-topology justification.
- every writing style uses an exact `#FFFFFF` canvas; warm art direction colours
  objects, never the page background.
- `layout_plan.mobile_preview` fixes a 390 px release view, a no-zoom floor for
  one to three primary wayfinding labels, a compact first-glance path, and an
  explain-back check. It explicitly forbids making every supporting label a
  phone-scale primary label and records how zoom or the caption carries detail.
- generated primary phone labels use at most four words and 28 characters;
  preserve nuance in the caption instead of shrinking the figure's type.
- each primary label carries one visible state, change, comparison, or
  conclusion; compound policy prose and stacked qualifiers belong in the
  caption. Put labels on natural exact-white canvas before considering a
  backed callout.
- multiword rendered labels use sentence case. Abbreviation definitions,
  glossary lines, and interpretation prose belong in the external caption, not
  in the artwork.
- every object shares one authored visual language across abstraction,
  dimensionality, line treatment, perspective, lighting, and material finish.
  Reject glossy stock-symbol, emoji, app-pictogram, sticker, or decorative-badge
  assemblies even when the component objects are recognizable.
- merge redundant plot copy before rendering: a direct series label may carry
  its principal value, while detail that is not needed for first-glance decoding
  belongs in the caption rather than in a second floating label.
- `visual_anchor` is required for non-quantitative figures and names a concrete
  domain-native focal structure.
- `semantic_plan` declares every meaningful object, connector, panel job,
  anatomy subject, vulnerable salience target, uncertainty encoding, repeated
  identity, information priority, and route decision.
- `annotation_plan` uses sequential A–D labels for distinct sections and gives
  each callout an exact target, leader-line decision, and background treatment.
- `cutaway_plan` is a fail-closed suitability and physical-integrity contract:
  recognizable exterior, one cut plane, at most six essential interior
  entities, truthful spatial relationships, one explanatory callout per entity,
  and native-plus-phone inspection.
- `plot_design` gives quantitative figures chart type, encoding, reader path,
  style rationale, typography, per-panel axis semantics, caption axis summary,
  numeric attachment, uncertainty attachment, and legend decision.
- `geometry_invariants` records shapes or unit geometry that must survive.
- `observed` and `inferred` distinguish evidence status.
- `style_overrides` may adjust treatment but never evidence.
- `avoid` contains topic-specific scientific failure modes, not generic style
  rules already supplied by the profile.

## Prompting rules

- Describe the focal scientific structure, information hierarchy, eye path,
  negative space, material treatment, finish, and rejection standard richly
  enough to guide a capable image generator. Richness clarifies evidence; it
  does not authorize invented detail.
- Request the complete finished generated figure on the first call, including
  every essential manifest string. Prohibit blank label zones, placeholders,
  pseudo-text, and a separate textless-base workflow.
- Generated copy is limited to eight strings, eight words per string, and
  32 words total. Longer explanation and citations belong in the caption.
- In `article` and `slide` contexts, keep title/subtitle and presentation
  chrome out of the pixels. In `standalone`, render the compact title and list
  it in `exact_text`.
- Quote every required string once through the exact-text manifest. Do not offer
  spelling variants or repeat the manifest throughout the prose prompt.
- Render only declared semantic objects and connectors. Give primary entities
  the dominant area, contrast, and first fixation; omit props or scenery that
  fail the deletion test.
- Use literal domain-native representations before metaphors. Preserve
  anatomical orientation, cross-view identity, and the declared evidence
  boundary.
- Use sequential A–D panel labels where sections are genuinely distinct.
  Callouts sit beside their referents, use thin leaders when adjacency is
  ambiguous, and first seek quiet white canvas. Opaque white backing over busy
  pixels is fallback-only and requires a spatial justification.
- Prefer evidence-native representation. Reject a metaphor or arranged-object
  treatment when it adds a decoding step that a literal scientific structure
  would avoid.
- Use one natural-width house sans-serif family. Fit copy by editing, wrapping,
  or moving it—never by condensing, shearing, or stretching type.
- Keep the visual explanation legible when labels are mentally hidden. Reject a
  headline-plus-icons poster, sparse object inventory, or any composition whose
  takeaway is carried mainly by words rather than evidence-native structure.
- Keep exact numerical evidence in structured `data`. Generated pixels never
  invent or proportionally encode values.
- Keep citations, DOI strings, journal branding, mastheads, logos, slide chrome,
  dashboard furniture, and decorative arrows out of the artwork.

After generation, return to `figure-generation-contract.md` for meaning-first
iteration and to `figure-inspection-contract.md` for the inspection and
provenance records. Prompt compliance alone never releases a figure.
