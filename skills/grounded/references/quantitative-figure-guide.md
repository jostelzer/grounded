# Deterministic (plotted) figures: spec shape, renderer grammar, tools

Read `figure-generation-contract.md` first for the communication-first
workflow. This reference is the deterministic counterpart of
`image-prompt-guide.md`: it owns the complete shape of a `deterministic` or
`composite` figure specification, the facts about the renderer that the
validators assume you know, and the three tools that remove schema guesswork.
Nothing here changes a gate; it documents what the gates already require.

## Tools, in the order you use them

```bash
python3 scripts/figure_spec_tools.py scaffold --route deterministic --archetype quantitative --review-style popsci --panels 1 --figure-id <id> --out <id>.figure.json
python3 scripts/figure_spec_tools.py lint --spec <id>.figure.json
python3 scripts/figure_spec_tools.py preview --spec <id>.figure.json --out-dir <id>-preview/
python3 scripts/render_quantitative_figure.py --spec <id>.figure.json --out <id>.png --geometry <id>.geometry.json
python3 scripts/qa_quantitative_geometry.py --spec <id>.figure.json --image <id>.png --geometry <id>.geometry.json
python3 scripts/qa_figure.py --spec <id>.figure.json --image <id>.png --geometry <id>.geometry.json --inspection <id>.inspection.json --provenance <id>.provenance.json
```

- `scaffold` writes a skeleton with every required key present and
  `<<FILL: …>>` placeholders; every gate rejects a placeholder, so a skeleton
  cannot ship. The example numbers in `data` are placeholders too.
- `lint` runs every validator independently and reports **all** failures at
  once, with `did you mean` hints for misnamed keys and a dry-run render that
  surfaces text collisions before you write an inspection record.
- `preview` renders, writes the proportional 390 px phone view, and prints
  the measured height of every declared primary label and the effective size
  of the smallest tick at the true journal width. Use it before inspecting.
- The provenance `render` attempt names the geometry manifest
  (`"geometry": "<id>.geometry.json"`), so `qa_figure.py` measures the phone
  gate from the rendered text boxes even when `--geometry` is not passed.

## What the renderer is

`render_quantitative_figure.py` draws one grammar: panels with two labelled
axes, series of points joined by a line, attached intervals, dashed reference
lines and events, contrast brackets, and free annotations. Facts that only the
source otherwise reveals:

- **A series is a polyline.** One series with seven points is a line through
  seven points. A dot plot or forest plot is one single-point series per row;
  write it with `rows` (below) rather than by hand.
- **`label: null` is allowed; `label: ""` is rejected.** Omit a direct label
  by setting it to `null` or leaving it out.
- **A point carries `y_interval` or `x_interval`, never both.** Vertical
  point-and-whisker plots use `y_interval`; horizontal forest plots use
  `x_interval` with a categorical y-axis.
- **`target_aspect_ratio` is 1 to 4.** Taller-than-wide figures are refused
  because the journal page caps figure height at 92 mm: a 0.6:1 raster would
  print 55 mm wide and fail the 6.5 pt label gate. Stack panels with
  `plot_design.render.columns` (2 for A/B side by side) or split the figure.
- **A contrast must equal `from.y − to.y`** at its declared decimal places;
  its `interval` must contain the estimate.
- **Every drawn string must be in `exact_text`, and nothing else.** Panel
  letters, titles, axis labels, tick labels, category names, series and point
  labels, reference, event, contrast, and annotation text. `lint` lists what
  is missing and what nothing draws.
- **Text is laid out once and validated.** A label that leaves its panel or
  sits within 3 px (at 390 px) of another fails the render. Opt into
  `plot_design.render.auto_layout: true` (or `--auto-layout`) to let the
  renderer try the other label sides and then wider canvases; its choices are
  written to the geometry manifest as `resolved_layout` and the spec is never
  rewritten.
- **`plot_design.render.width_px` sets the canvas; type scales with it.** The
  height is `width / target_aspect_ratio`. Widening a canvas does not make
  ticks fit better, because tick type scales too; shorten the tick or move
  detail to the caption.

### Sugar the renderer expands for you

- `x_axis.categories: ["Trial one", "Trial two"]` (or `y_axis.categories`)
  replaces `domain` and `ticks` with `[0.5, n + 0.5]` and one integer tick per
  name. Category names are rendered tick labels and belong in `exact_text`.
- `rows: [{id, value, interval, label, label_position, color}]` on a panel with
  a categorical axis becomes one single-point series per row, in order. With
  `x_axis.categories` the rows are vertical (value on y, `y_interval`); with
  `y_axis.categories` they are a horizontal forest plot (value on x,
  `x_interval`). `series_label` on a row adds a direct series label.
- `annotations: [{id, text, x, y, align, leader_to}]` places free explanatory
  copy at a data coordinate (the anchor is the top edge of the text block:
  left, centre, or right end by `align`). `leader_to: {series_id, point_id}`
  draws a thin leader from the nearest edge of the text to that mark. This is
  where a whole-answer sentence lives.

## The phone gate, and what a primary label is

`layout_plan.mobile_preview` declares one to three `primary_labels` that must
measure at least 10 px tall in a 390 px preview. Before drawing, the renderer
selects one font size per semantic role across all panels. A nominated point
label therefore promotes every point label, not only that value; primary strings
with different glyph heights share the size needed by the shortest glyph box.
The face is capped at the style system's 56 px (scaled). Tick fonts remain
separate. Geometry records actual primary heights in `primary_labels_resolved`
and promoted role sizes in `role_fonts_resolved`. If an entire role cannot fit,
choose a short wayfinding annotation or revise layout; never shrink peer values
individually or promote the largest effect just to emphasize it.
`qa_figure.py --geometry` uses that measurement; an
inspection that attests a taller label than the renderer produced fails. The
same manifest lets the typography-dominance cap ignore OCR boxes for the
rotated y-axis title and for the primary labels themselves, so it measures the
supporting type system; without a manifest a long vertical title can trip that
cap, which is one more reason to always pass the geometry.

Eligible roles: axis titles, series and point labels, panel titles,
reference-line, event, and contrast labels, and annotations. **Tick labels are
never primary.** Choose the takeaway strings — a direct label such as
`Dark nap −2.1 h`, a reference-line label such as `No difference`, or an
annotation carrying the whole-answer sentence — not an axis abbreviation. Tick
labels stay at publication scale, may be as descriptive as the caption needs,
and may require zoom; say so in `supporting_detail_strategy`.

## Required keys the validators check (v3, deterministic)

Top level: `quality_contract_version: 3`, `figure_id`, `profile`,
`archetype: "quantitative"`, `review_style`, `render_route`, `render_context`,
`target_aspect_ratio`, `purpose`, `title`, `story`, `exact_text`,
`communication_goal`, `layout_plan`, `annotation_plan`, `semantic_plan`,
`plot_design`, `data`.

`communication_goal`: `visual_question`, `panel_thesis`, `reader_takeaway`,
`must_show`, `information_flow`, `evidence_boundary`,
`familiar_starting_point`, `plain_language_explain_back`.

`layout_plan`: `content_density`, `wide_canvas_required`,
`aspect_ratio_rationale`, `balance_strategy`, `final_display`,
`mobile_preview` (`width_px: 390`, `minimum_primary_label_height_px: 10`,
`all_labels_required_without_zoom: false`, `primary_labels`,
`first_glance_path`, `supporting_detail_strategy`, `explain_back_without_zoom`).

`annotation_plan`: `panel_labels` (the `A`, `B`, … prefix, empty for one
panel), `callouts`, `rationale`.

`semantic_plan`: `entities[]` (`id`, `depiction`, `role`, `evidence_basis`),
`connectors[]`, `panel_jobs[]` (`label`, `job`, `adds_distinct_information`;
labels equal `panel_labels`), `grouping_rationale`, `anatomy_subjects`,
`anatomical_context`, `salience_targets`, `information_priority`
(`primary_entities`, `supporting_entities`, `excluded_nonessential`,
`dominance_rationale`, `deletion_test`), `uncertainty_encodings[]` (`target`,
`source_of_uncertainty`, `visual_encoding`, `reader_interpretation`),
`cross_view_identity`, `representation_plan` (`kind`,
`evidence_native_anchor`, `cognitive_translation_steps`,
`literal_rejected_reason`, `added_explanatory_value`, `arranged_elements`,
`arrangement_evidence_job`), `quantitative_decision`
(`verified_numbers_available`, `numbers_carry_primary_message`, `reason`; both
booleans true for this route).

`plot_design`: `chart_type`, `encoding`, `reader_path`, `style_rationale`,
`typography` (`family`, `fallback` from the clean sans set, `upright_natural_width:
true`), `render` (`width_px`, `height_px`, `columns`, `supersample`,
`background_color: "#FFFFFF"`, optional `auto_layout`), `axis_semantics[]`
(`panel_id`, `x_label`, `x_meaning`, `y_label`, `y_meaning`; labels equal the
rendered axis labels), `caption_axis_summary`, `numeric_annotation_attachment`,
`uncertainty_display` (`present`, `encoding`, `attachment`),
`axis_label_placement` (exactly `horizontal` / `below-data-region` /
`vertical` / `outside-data-region`), `legend_plan` (`needed`, `reason`,
`placement`: `none` or `adjacent-to-marks`).

## A complete passing example

One panel, three estimates with intervals on a categorical x-axis, a labelled
no-difference line, and an annotation carrying the takeaway as a primary
label. The numbers are illustrative; replace them with verified values from
`synthesis.md`. This block is executed by the test suite: it must lint,
render, and pass geometry QA.

```json figure-spec
{
  "quality_contract_version": 3,
  "figure_id": "example-dot-plot",
  "profile": "nature-data",
  "archetype": "quantitative",
  "review_style": "popsci",
  "render_route": "deterministic",
  "render_context": "article",
  "target_aspect_ratio": 1.6,
  "aspect_ratio_tolerance": 0.02,
  "purpose": "How consistent are the three estimates?",
  "title": "Every estimate favours the intervention, and every interval crosses no difference.",
  "story": [
    "Three estimates sit below 1.0 with intervals that all reach 1.0."
  ],
  "observed": ["Published point estimates and reported intervals"],
  "inferred": [],
  "evidence_keys": ["Example2024one", "Example2024two", "Example2023cohort"],
  "exact_text": [
    "Risk ratio", "Evidence source",
    "Trial one", "Trial two", "Cohort",
    "0.6", "0.8", "1.0", "1.2",
    "No difference",
    "0.86", "0.91", "0.97",
    "All intervals cross 1.0"
  ],
  "communication_goal": {
    "visual_question": "How consistent are the three estimates?",
    "panel_thesis": "All three estimates and their intervals sit on one axis.",
    "reader_takeaway": "Every estimate favours the intervention, and every interval crosses no difference.",
    "must_show": ["Three estimates", "Attached intervals", "The no-difference line"],
    "information_flow": ["Read the source labels", "Compare the dots", "See every whisker cross 1.0"],
    "evidence_boundary": "Alignment on one axis is not a pooled estimate.",
    "familiar_starting_point": "Dots with whiskers on a shared scale",
    "plain_language_explain_back": "The three studies point the same way but none rules out no effect."
  },
  "layout_plan": {
    "content_density": "moderate",
    "wide_canvas_required": false,
    "aspect_ratio_rationale": "Three categories and a short value range fit a compact landscape.",
    "balance_strategy": "Dots occupy the centre; the annotation sits in the quiet upper-left canvas.",
    "final_display": "Journal PDF at no more than 92 mm high",
    "mobile_preview": {
      "width_px": 390,
      "minimum_primary_label_height_px": 10,
      "all_labels_required_without_zoom": false,
      "primary_labels": ["All intervals cross 1.0", "No difference"],
      "first_glance_path": ["Takeaway sentence", "Dashed no-difference line", "Three dots below it"],
      "supporting_detail_strategy": "Source names and values remain publication-sized and are repeated in the caption.",
      "explain_back_without_zoom": "All three point the same way and all could be no effect."
    }
  },
  "annotation_plan": {
    "panel_labels": [],
    "callouts": [],
    "rationale": "One panel; the annotation is free plot copy, not a callout to an illustrated object."
  },
  "semantic_plan": {
    "entities": [
      {
        "id": "estimates",
        "depiction": "Three direct-labelled dots with attached whiskers",
        "role": "Quantitative evidence",
        "evidence_basis": "Example2024one, Example2024two, Example2023cohort"
      },
      {
        "id": "no-difference",
        "depiction": "Dashed horizontal line at 1.0",
        "role": "Reference state",
        "evidence_basis": "Definition of the risk ratio"
      }
    ],
    "connectors": [],
    "panel_jobs": [],
    "grouping_rationale": "One panel keeps every estimate against the same reference line.",
    "anatomy_subjects": [],
    "anatomical_context": [],
    "salience_targets": ["estimates"],
    "information_priority": {
      "primary_entities": ["estimates"],
      "supporting_entities": ["no-difference"],
      "excluded_nonessential": ["icons", "legend", "gridlines"],
      "dominance_rationale": "The dots and whiskers carry the message.",
      "deletion_test": "Removing the annotation leaves the same reading; removing any dot changes it."
    },
    "uncertainty_encodings": [
      {
        "target": "estimates",
        "source_of_uncertainty": "Reported 95% confidence intervals",
        "visual_encoding": "Whiskers attached to each dot",
        "reader_interpretation": "Each estimate is a range that includes no difference"
      }
    ],
    "cross_view_identity": [],
    "representation_plan": {
      "kind": "literal",
      "evidence_native_anchor": "Published estimates and intervals",
      "cognitive_translation_steps": 0,
      "literal_rejected_reason": null,
      "added_explanatory_value": "The plot encodes the reported quantities without metaphor.",
      "arranged_elements": false,
      "arrangement_evidence_job": null
    },
    "quantitative_decision": {
      "verified_numbers_available": true,
      "numbers_carry_primary_message": true,
      "reason": "Magnitude and uncertainty are the message."
    }
  },
  "plot_design": {
    "chart_type": "direct-labelled dot plot with intervals",
    "encoding": "Vertical position is the risk ratio; whiskers are the reported intervals.",
    "reader_path": ["Takeaway", "Reference line", "Dots and whiskers"],
    "style_rationale": "Open axes and direct labels keep the evidence primary.",
    "typography": {"family": "Helvetica Neue", "fallback": "Arial", "upright_natural_width": true},
    "render": {
      "width_px": 1536,
      "height_px": 960,
      "outer_margin_px": 64,
      "panel_gap_px": 64,
      "columns": 1,
      "supersample": 2,
      "background_color": "#FFFFFF",
      "auto_layout": false
    },
    "axis_semantics": [
      {
        "panel_id": "main",
        "x_label": "Evidence source",
        "x_meaning": "The x-axis names each study.",
        "y_label": "Risk ratio",
        "y_meaning": "The y-axis is the reported risk ratio; 1.0 is no difference."
      }
    ],
    "caption_axis_summary": "x names the study; y is the risk ratio with 1.0 as no difference",
    "numeric_annotation_attachment": "Each printed value sits beside its dot.",
    "uncertainty_display": {
      "present": true,
      "encoding": "Whiskers show the reported 95% confidence intervals.",
      "attachment": "Every whisker passes through the dot it qualifies."
    },
    "axis_label_placement": {
      "x_orientation": "horizontal",
      "x_location": "below-data-region",
      "y_orientation": "vertical",
      "y_location": "outside-data-region"
    },
    "legend_plan": {
      "needed": false,
      "reason": "Direct labels identify every mark.",
      "placement": "none"
    }
  },
  "data": {
    "panels": [
      {
        "id": "main",
        "x_axis": {"label": "Evidence source", "categories": ["Trial one", "Trial two", "Cohort"]},
        "y_axis": {
          "label": "Risk ratio",
          "domain": [0.55, 1.3],
          "ticks": [
            {"value": 0.6, "label": "0.6"}, {"value": 0.8, "label": "0.8"},
            {"value": 1.0, "label": "1.0"}, {"value": 1.2, "label": "1.2"}
          ]
        },
        "rows": [
          {"id": "one", "value": 0.86, "interval": [0.72, 1.02], "label": "0.86", "label_position": "right", "color": "#3B7C85"},
          {"id": "two", "value": 0.91, "interval": [0.78, 1.06], "label": "0.91", "label_position": "right", "color": "#3B6F9C"},
          {"id": "cohort", "value": 0.97, "interval": [0.80, 1.17], "label": "0.97", "label_position": "right", "color": "#C86F55"}
        ],
        "reference_lines": [
          {"id": "no-difference", "axis": "y", "value": 1.0, "label": "No difference"}
        ],
        "events": [],
        "contrasts": [],
        "annotations": [
          {"id": "takeaway", "text": "All intervals cross 1.0", "x": 0.6, "y": 1.29, "align": "left", "leader_to": null}
        ]
      }
    ]
  },
  "abbreviations": {},
  "avoid": ["3D", "gradient", "dashboard cards", "decorative icons", "unattached intervals"],
  "geometry_invariants": ["Whiskers intersect their estimates", "No anisotropic transform"]
}
```

The inspection and provenance records follow `figure-inspection-contract.md`.
For a plot, the provenance `attempts` entry is
`{"kind": "render", "asset": "<id>.png", "geometry": "<id>.geometry.json", …}`
and `generator_available` carries a `generator_detection` record when it is
false.
