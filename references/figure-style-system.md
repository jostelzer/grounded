# Journal-grade figure style system

Use this system for every journal-PDF figure and deck content image. It translates
top-journal figure conventions into a display-oriented Grounded review style;
it is not an official Nature template and must not carry Nature branding. Read
`figure-reference-analysis.md` for the 21-figure visual audit behind the rules.

## Figure-native, not poster-native

The scientific representation determines the layout. Begin with the anatomy,
signal flow, experiment, mathematical geometry, or data—not a title banner and
not a row of generic cards.

- In `article` context, which is the default for a review or PDF, keep the title
  and explanatory caption outside the pixels. Render all panel letters, local
  labels, values, units, legends, and essential qualifiers in the figure.
- In `standalone` context, render a compact title and only an essential short
  subtitle. They must not dominate the scientific content.
- In `slide` context, render full-bleed 16:9 artwork while keeping the top 19%
  and bottom 8% visually quiet. The canonical deck renderer adds the claim,
  citations, evidence chip, masthead, and counter as real text.
- Establish grouping with alignment and white space before adding borders or
  pale background regions. Do not box every panel.
- Put explanations next to the structure or data they describe. Use a glossary
  only for necessary terminology or encodings that cannot be defined locally.

## Font policy

Typography follows the review's writing style via
`figure-writing-style-overlays.json`: scientific uses Arial with Helvetica as
fallback; popsci uses Optima with Helvetica Neue; bullets uses Helvetica Neue
with Arial; ELI5 uses Seravek with Helvetica Neue. These are identity choices,
not permission for display typography. Every face uses its natural width and
height. Reject slab-serif, condensed, expanded, handwritten, outlined, beveled,
shadowed, sheared, horizontally scaled, or vertically scaled lettering.

At a 1,536 px-wide deliverable, use these visual targets:

| Role | Target |
|---|---:|
| Smallest label or compact legend text | at least 26 px |
| Body label | 27–31 px |
| Local panel heading | 31–33 px |
| Compact standalone title | 34–38 px |
| Panel letter | 31–33 px bold, lower-case |

These are chat-readable targets inspired by Nature's 5–7 pt figure-label range
at double-column width, raised so the smallest OCR-measured word height clears
`qa_figure.py`'s 6.5 pt effective-size gate at the true journal render width.
End-to-end raster generation cannot prove an embedded font file; inspect visual
conformance and exact text directly. First repair a local typography defect with
a targeted ImageGen edit. Use the hybrid compositor only after that direct-text
route fails; it resolves a real font and draws labels at natural proportions
without resizing the generated base. If editable embedded font metadata is a
deliverable requirement, use a deterministic vector renderer for that layer.

**Aspect ratio for journal-PDF figures.** The exporter renders figures at full
content width (184 mm) but caps their height (92 mm by default), scaling tall
figures down proportionally — which silently shrinks every label. Design
journal figures at an aspect ratio of at least 2:1 (for example 1,536 × ≤768 px
at the default cap) so the figure keeps the full content width; `qa_figure.py`
evaluates label sizes at the true rendered width and will fail a tall figure
whose labels drop below 6.5 pt on paper. New specs declare the target ratio;
figure QA compares it with the raster, and PDF QA independently compares the
intrinsic ratio with the painted transformation matrix. Any anisotropic scale
or shear is release-blocking.

## Default profile

Use `nature-neuroscience` from `figure-style-presets.json` unless the figure is predominantly quantitative (`nature-data`) or a multi-level conceptual synthesis (`nature-reviews`). Profiles control the typography, canvas, palette, visual language, and exclusions without changing the evidence.

The shared visual grammar is:

- white background and 6–8% outer margins;
- black or near-black natural-width text from the selected writing-style overlay;
- a shared invisible grid, aligned panel edges, and white-space grouping;
- restrained, colour-blind-safe semantic colour on data and biological
  structures, not prose or large background fields;
- thin black or grey arrows, consistent keylines, and short leaders; use a
  coloured arrow only when pathway identity or direction is encoded;
- morphologically recognizable scientific primitives rather than decorative
  icons;
- one scientific claim per panel, with topology chosen by the content rather
  than a universal sequence of equally sized columns;
- no dashboard cards, glossy 3D, cinematic light, drop shadows, ornamental gradients, grid backgrounds, or journal logos;
- restrained anatomical shading only when it clarifies form;
- lower-case bold panel letters for multi-panel figures;
- uncertainty expressed with a dashed boundary, pale tint, qualifier, or exact interval—not vague visual mood.

## Adaptation controls

Change one layer at a time:

1. **Evidence payload:** claims, values, uncertainty, and exact copy.
2. **Archetype:** mechanism, anatomical mechanism, study overview, comparison,
   quantitative, evidence map, timeline, or mindmap.
3. **Style profile:** Nature Neuroscience explanatory, Nature Reviews conceptual, or Nature data.
4. **Writing-style overlay:** scientific, popsci, bullets, or ELI5 identity.
5. **Render route:** generated, hybrid, or deterministic.
6. **Render context:** `article`, `standalone`, or `slide` for a requested deck.
7. **Overrides:** aspect ratio, palette subset, panel count, or content-specific constraints.

Never bury evidence changes inside style overrides. If a user requests another journal or house style, add a new profile instead of mutating the default.

## Source basis

The system abstracts these current Nature requirements and examples:

- [Nature research figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/): Arial or Helvetica, accessible colour, legible text, labelled axes and units; avoid gridlines, decorative elements, shadows, patterns, coloured text, overlap, and text over busy imagery.
- [Nature panel-building guidance](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/): 89 mm and 183 mm widths, 5–7 pt labels, compact panel arrangement, lower-case panel sequence, high-contrast text, and restrained icons.
- [Nature Neuroscience formatting](https://www.nature.com/neuro/submission-guidelines/aip-and-formatting): 5–7 pt sans-serif labels, scale/error bars kept editable, sequential figures, and accessibility for non-specialists.
- [Nature formatting guide](https://www.nature.com/nature/for-authors/formatting-guide): figures should be as small and simple as clarity permits, avoid unnecessary colour and detail, and remain comprehensible across disciplines.
- `nature-figure-corpus.json`: a reproducible official-source manifest of 21
  *Nature Reviews Neuroscience* and *Nature Neuroscience* figures spanning
  mechanism, comparison, study-overview, quantitative, cellular, timeline, and
  conceptual-synthesis roles. The copyrighted pixels stay outside the repository.

Nature's production rules prefer editable vector artwork. This skill prioritizes
capable image generation for the complete authored, directly typeset scientific
composition, reserves deterministic overlays for failed direct-text repair and
exact deterministic plots, and uses strict pixel, provenance, visual-quality,
and non-distortion QA.
