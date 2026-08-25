# Journal-grade figure style system

Use this system for every `image` or `mindmap` artifact. It translates top-journal figure conventions into a display-oriented scientific-review style; it is not an official Nature template and must not carry Nature branding.

## Font policy

**Arial is the defined figure font. Helvetica is the only visual fallback.** State `Arial throughout` in every generation prompt. Reject serif, slab-serif, condensed display, handwritten, outlined, beveled, or shadowed lettering.

At a 1,536 px-wide deliverable, use these visual targets:

| Role | Target |
|---|---:|
| Smallest label or glossary text | at least 22 px |
| Body label | 24 px |
| Section heading | 28–29 px |
| Internal title, when needed for chat | 36–40 px |
| Panel letter | 26 px bold, lower-case |

These are display equivalents of Nature's 5–7 pt figure-label range at double-column width, enlarged enough to survive chat and PDF scaling. End-to-end raster generation cannot prove the embedded font file; inspect visual conformance and reject any output that visibly uses a serif or display face. If editable embedded font metadata is a deliverable requirement, use the deterministic vector fallback.

## Default profile

Use `nature-neuroscience` from `figure-style-presets.json` unless the figure is predominantly quantitative (`nature-data`) or a multi-level conceptual synthesis (`nature-reviews`). Profiles control the typography, canvas, palette, visual language, and exclusions without changing the evidence.

The shared visual grammar is:

- white background and 6–8% outer margins;
- black or near-black Arial text;
- colour-blind-safe colour on data and biological structures, not prose;
- thin consistent keylines and short leaders;
- direct labels rather than decorative icons;
- one scientific claim per panel and 3–6 meaningful elements;
- no dashboard cards, glossy 3D, cinematic light, drop shadows, ornamental gradients, grid backgrounds, or journal logos;
- restrained anatomical shading only when it clarifies form;
- lower-case bold panel letters for multi-panel figures;
- uncertainty expressed with a dashed boundary, pale tint, qualifier, or exact interval—not vague visual mood.

## Adaptation controls

Change one layer at a time:

1. **Evidence payload:** claims, values, uncertainty, and exact copy.
2. **Archetype:** mechanism, comparison, quantitative, evidence map, timeline, or mindmap.
3. **Style profile:** Nature Neuroscience explanatory, Nature Reviews conceptual, or Nature data.
4. **Overrides:** aspect ratio, palette subset, panel count, or content-specific constraints.

Never bury evidence changes inside style overrides. If a user requests another journal or house style, add a new profile instead of mutating the default.

## Source basis

The system abstracts these current Nature requirements and examples:

- [Nature research figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/): Arial or Helvetica, accessible colour, legible text, labelled axes and units; avoid gridlines, decorative elements, shadows, patterns, coloured text, overlap, and text over busy imagery.
- [Nature panel-building guidance](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/): 89 mm and 183 mm widths, 5–7 pt labels, compact panel arrangement, lower-case panel sequence, high-contrast text, and restrained icons.
- [Nature Neuroscience formatting](https://www.nature.com/neuro/submission-guidelines/aip-and-formatting): 5–7 pt sans-serif labels, scale/error bars kept editable, sequential figures, and accessibility for non-specialists.
- [Nature formatting guide](https://www.nature.com/nature/for-authors/formatting-guide): figures should be as small and simple as clarity permits, avoid unnecessary colour and detail, and remain comprehensible across disciplines.

Nature's production rules prefer editable vector artwork. This skill instead prioritizes end-to-end image generation because that is the requested authoring route; it therefore uses stricter rendered-text and data QA and keeps deterministic SVG/vector rendering as fallback.
