# Figure inspection and provenance contract

Read this after `figure-generation-contract.md` when producing or auditing a
figure. It is the canonical schema reference for the visual inspection and
generation provenance records consumed by `scripts/qa_figure.py`. Keep
production decisions in the workflow contract and machine-auditable attestations
here.

## Visual inspection record

For `quality_contract_version: 3`, `<figure-id>.inspection.json` contains:

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
    "polish": "pass",
    "explanatory_value": "pass",
    "information_flow": "pass",
    "intuitiveness": "pass",
    "concept_coherence": "pass",
    "anatomical_integrity": "pass",
    "connector_semantics": "pass",
    "logical_grouping": "pass",
    "salience": "pass",
    "nonredundancy": "pass",
    "typography": "pass"
  },
  "communication": {
    "observed_takeaway": "A plain-language statement of what the pixels communicate.",
    "observed_explain_back": "The sentence a non-specialist could say from the image alone.",
    "explain_back_matches": true,
    "intuitive_without_caption": true,
    "familiar_starting_point_visible": true,
    "requires_caption_to_understand": false,
    "unexplained_jargon": [],
    "intended_takeaway_conveyed": true,
    "information_flow_clear": true,
    "must_show_visible": ["..."],
    "observed_information_flow": ["..."],
    "misleading_or_ambiguous": [],
    "revision_needed": false
  },
  "annotation": {
    "panel_labels": ["A", "B"],
    "callouts": [
      {
        "text": "Short explanation",
        "target": "the exact depicted structure",
        "leader_line_present": true,
        "leader_origin_attached_to_label": true,
        "leader_endpoint_hits_target": true
      }
    ]
  },
  "integrity": {
    "title_matches_visual_question": true,
    "panels_form_one_explanation": true,
    "declared_entities_specific": true,
    "all_objects_declared": true,
    "all_connectors_semantic": true,
    "related_content_grouped": true,
    "panels_add_distinct_information": true,
    "primary_entities_visually_dominant": true,
    "nonessential_elements_absent": true,
    "aspect_ratio_suits_content": true,
    "composition_optically_balanced": true,
    "callout_backings_legible": true,
    "font_system_consistent": true,
    "composite_components_integrated": true,
    "anatomy_checked_at_original_size": true,
    "anatomical_context_sufficient": true,
    "uncertainty_encodings_explanatory": true,
    "cross_view_identity_preserved": [],
    "salience_targets_visible": ["entity-id"],
    "anatomy_errors": [],
    "unexplained_objects": [],
    "ambiguous_connectors": [],
    "salience_failures": [],
    "redundant_sections": [],
    "typography_issues": [],
    "entity_specificity_issues": [],
    "visual_clutter": [],
    "anatomical_context_losses": [],
    "identity_drift": [],
    "uncertainty_ambiguities": [],
    "quantitative_annotation_issues": [],
    "layout_balance_issues": [],
    "callout_backing_issues": [],
    "font_consistency_issues": [],
    "composite_integration_issues": []
  },
  "quantitative": {
    "axis_semantics_visible": true,
    "numeric_annotations_attached_to_referents": true,
    "uncertainty_attached_to_estimate": true
  }
}
```

Each `pass` is a real visual judgment made after viewing the selected pixels at
original size and expected PDF size. Visually transcribe the exact rendered copy
into `ocr_text`; machine OCR is a secondary discrepancy warning, not an excuse
for another generation when the pixels are plainly correct. Conversely, never
use a manual transcript to certify garbled or absent lettering. Write
`observed_takeaway` from the pixels, not by copying the prompt.
`duplicate_text` lists any label rendered more than
its manifest count; `unlisted_text` lists meaningful copy absent from the
manifest. Either list being non-empty is release-blocking. A planned callout
must point to its declared target, and every required leader line must actually
be visible. The connector must visibly begin at or attach to its label rather
than appear as a detached line elsewhere in the panel. Its endpoint must visibly terminate on the exact named referent
rather than nearby empty space; when the callout names a group, the connector
or bracket must reach every member of that group. Record this as
`leader_origin_attached_to_label: true` and
`leader_endpoint_hits_target: true`; any missing or false attestation is
release-blocking. Empty or blank pixels cannot be rescued by a manually
supplied OCR transcript.

## Generation provenance record

For `quality_contract_version: 3`, provenance keeps schema version 2 and contains:

```json
{
  "schema_version": 2,
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
    "selection_rationale": "The first complete candidate passed every gate."
  },
  "post_generation_reviews": [
    {
      "asset": "figure.png",
      "intended_takeaway": "The exact communication_goal.reader_takeaway string.",
      "observed_takeaway": "What the inspector understood from the image.",
      "observed_explain_back": "What the inspector could explain from the image alone.",
      "intended_meaning_conveyed": true,
      "information_flow_clear": true,
      "intuitive_without_caption": true,
      "unexplained_jargon": [],
      "issues": [],
      "decision": "accept"
    }
  ]
}
```

Use `kind: edit` for a targeted ImageGen edit and `kind: render` for a
deterministic plot. Every generated, edited, or rendered candidate requires a
matching post-generation review. Paths are case-local audit records; only the
selected asset appears in the final review. The release manifest hashes the
selected figure, its specification, prompt, inspection, and provenance.
