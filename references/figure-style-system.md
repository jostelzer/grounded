# Journal-grade figure style system

Use this system for every `image`, `mindmap`, or deck content image. It translates
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

**Arial is the defined figure font. Helvetica is the only visual fallback.** State `Arial throughout` in every generation prompt. Reject serif, slab-serif, condensed display, handwritten, outlined, beveled, or shadowed lettering.

At a 1,536 px-wide deliverable, use these visual targets:

| Role | Target |
|---|---:|
| Smallest label or compact legend text | at least 18 px |
| Body label | 20–22 px |
| Local panel heading | 24–26 px |
| Compact standalone title | 30–34 px |
| Panel letter | 26–28 px bold, lower-case |

These are chat-readable targets inspired by Nature's 5–7 pt figure-label range
at double-column width. End-to-end raster generation cannot prove the embedded
font file; inspect visual conformance and reject any output that visibly uses a
serif or display face. If editable embedded font metadata is a deliverable
requirement, use the deterministic vector fallback.

## Default profile

Use `nature-neuroscience` from `figure-style-presets.json` unless the figure is predominantly quantitative (`nature-data`) or a multi-level conceptual synthesis (`nature-reviews`). Profiles control the typography, canvas, palette, visual language, and exclusions without changing the evidence.

The shared visual grammar is:

- white background and 6–8% outer margins;
- black or near-black Arial text;
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
4. **Render context:** `article`, `standalone`, or `slide` for a requested deck.
5. **Overrides:** aspect ratio, palette subset, panel count, or content-specific constraints.

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

Nature's production rules prefer editable vector artwork. This skill instead prioritizes end-to-end image generation because that is the requested authoring route; it therefore uses stricter rendered-text and data QA and keeps deterministic SVG/vector rendering as fallback.
