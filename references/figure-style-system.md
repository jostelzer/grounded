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
fallback; popsci uses Helvetica Neue with Arial; bullets uses Helvetica Neue
with Arial; ELI5 uses Seravek with Helvetica Neue. These are identity choices,
not permission for display typography. Deterministic plots always declare a
clean upright sans-serif family explicitly. Every face uses its natural width and
height. Reject slab-serif, condensed, expanded, handwritten, outlined, beveled,
shadowed, sheared, horizontally scaled, or vertically scaled lettering.

At a 1,536 px-wide deliverable, use these visual targets:

| Role | Target |
|---|---:|
| Smallest nominal font size requested from ImageGen | at least 96 px |
| Body label requested from ImageGen | 104 px |
| Local panel heading requested from ImageGen | 116 px |
| Compact standalone title requested from ImageGen | 128 px |
| Panel letter requested from ImageGen | 116 px bold, uppercase A–D |

These ImageGen targets deliberately include a large safety margin because the
visible glyph box is often much smaller than the requested font face. A measured 48 px glyph box at a
1,536 px raster remains about 12 px when the figure is proportionally reduced
to a 390 px-wide phone preview. The measured glyph box—not the requested size—
is the release gate. Deterministic plotting derives its own nominal size from
that measured floor and is not forced to use the ImageGen request sizes. The
same delivered glyph box also clears `qa_figure.py`'s 6.5 pt effective-size gate
at the true journal width.
End-to-end raster generation cannot prove an embedded font file; inspect visual
conformance and exact text directly. First repair a local typography defect with
a targeted ImageGen edit. If several labels or the information flow fail, reduce
non-essential copy or rethink the selected concept instead of accumulating text
repair passes. Deterministic typography belongs to a verified quantitative plot,
not a conceptual-illustration overlay.

**Aspect ratio for journal-PDF figures.** Choose the canvas from information
density and topology. A sparse single comparison normally uses a compact
landscape or near-square ratio; a genuinely horizontal sequence or several
balanced panels may use a broad canvas. The exporter caps height at 92 mm by
default and scales proportionally, so compact figures may render narrower than
the 184 mm content width. `qa_figure.py` evaluates labels at that true display
size and fails anything below 6.5 pt. Never add empty horizontal space merely
to keep full width. New specs declare the target ratio and why it fits;
figure QA compares it with the raster, while PDF QA checks the intrinsic ratio
against the painted transformation. Any anisotropic scale or shear fails.

## Default profile

Use the domain-general `nature-reviews` profile from
`figure-style-presets.json` by default. Use `nature-neuroscience` only when the
subject is genuinely neural or biomedical, and `nature-data` when the figure is
predominantly quantitative. Profiles control typography, canvas, palette,
visual language, and exclusions without changing the evidence.

The shared visual grammar is:

- an exact `#FFFFFF` canvas in every writing style, with 6–8% outer margins;
  warm palettes may colour the scientific objects but never tint or texture the
  page itself;
- black or near-black natural-width text from the selected writing-style overlay;
- a shared invisible grid, aligned panel edges, and white-space grouping;
- restrained, colour-blind-safe semantic colour on data and biological
  structures, not prose or large background fields;
- one coherent representational language per figure: match abstraction,
  dimensionality, line weight, perspective, lighting, and material finish
  across every primary and supporting element. Reject stock-icon assemblages,
  glossy sticker or emoji treatment, and decorative object-in-circle badges;
  a boundary or frame is allowed only when it encodes real scientific scope,
  grouping, sampling, or comparison;
- short phone-first labels that each express one visible idea. Prefer a concrete
  noun phrase or verb phrase; move qualifications and policy prose to the
  caption rather than stacking clauses inside the artwork;
- thin black or grey arrows, consistent keylines, and short leaders; use a
  coloured arrow only when pathway identity or direction is encoded;
- morphologically recognizable scientific primitives rather than decorative
  icons;
- one scientific claim per panel, with topology chosen by the content rather
  than a universal sequence of equally sized columns;
- no dashboard cards, glossy 3D, cinematic light, drop shadows, ornamental gradients, grid backgrounds, or journal logos;
- restrained anatomical shading only when it clarifies form;
- uppercase bold panel letters `A`, `B`, `C`, `D` for multi-panel figures in
  every review style, so body prose and captions can refer to stable sections;
- concise explanatory callouts adjacent to their subject, with a thin leader
  line to the exact target whenever the target is not self-evident;
- place callout text on existing quiet white canvas whenever the relationship
  remains clear; use an opaque white, lightly padded backing over textured,
  illustrated, photographic, or otherwise busy pixels only when moving the
  label would break its spatial relationship to the referent;
- verify the complete first-glance path at a 390 px-wide phone preview: the
  primary labels remain readable without zoom and a non-specialist can still
  reconstruct the explain-back sentence;
- keep generated primary labels to at most four words and 28 characters so one
  long heading cannot force ImageGen to shrink every label; move the fuller
  qualification into the caption;
- conserve label bandwidth: when a plotted series needs both an identity and a
  principal value, prefer one direct label such as `Group −6.2%` over a series
  label plus a separate point label; do not repeat the same decoding work in a
  legend, annotation, and caption;
- in quantitative panels, keep data marks more visually salient than their
  annotations. Labels sit beside referents with a clear gap from points,
  trajectories, axes, and one another; no label crosses a data line. If the
  390 px type floor would overwhelm the plot, shorten copy or change panel
  topology/aspect ratio rather than enlarging text inside the same cramped
  layout;
- keep at least 3 px of clear separation between independent text boxes in the
  proportional 390 px preview; near-touching panel letters, axes, labels, and
  annotations count as a collision even when their glyph boxes do not overlap;
- render every stated confidence or credible interval as an attached whisker,
  band, bracket, or equivalent graphical extent. Merely writing `95% CI`
  beside an estimate does not show the interval;
- an intuition-first path in every writing style: begin with a recognizable
  literal structure, add one unfamiliar step at a time, define necessary terms
  at their referents, and remove any mark that does not help a non-specialist
  explain the figure back without its caption;
- uncertainty expressed with a dashed boundary, pale tint, qualifier, or exact interval—not vague visual mood;
- prefer evidence-native scientific structures over novelty metaphors, craft
  textures, product-still-life lineups, or asset-pack arrangements; a metaphor
  is acceptable only when it reduces rather than adds cognitive translation.

Generated near-white paper may be normalized only when it is connected to the
canvas edge. Use `scripts/normalize_figure_canvas.py`; if subject pixels enter
the five-percent safety band, change the composition rather than whitening or
cropping them away.

## Adaptation controls

Change one layer at a time:

1. **Evidence payload:** claims, values, uncertainty, and exact copy.
2. **Archetype:** mechanism, anatomical mechanism, cutaway, study overview,
   comparison, quantitative, evidence map, timeline, or mindmap.
3. **Style profile:** Nature Neuroscience explanatory, Nature Reviews conceptual, or Nature data.
4. **Writing-style overlay:** scientific, popsci, bullets, or ELI5 identity.
5. **Render route:** generated illustration, deterministic quantitative plot,
   or composite quantitative plot with generated text-free anchors.
6. **Render context:** `article`, `standalone`, or `slide` for a requested deck.
7. **Overrides:** aspect ratio, palette subset, panel count, or content-specific constraints.

Never bury evidence changes inside style overrides. If a user requests another journal or house style, add a new profile instead of mutating the default.

### Cutaway adaptation

A cutaway is a representation choice, not a decorative finish. Preserve the
recognizable whole while one coherent section reveals only the hidden
structures needed for the explanation. The exterior and interior share scale,
perspective, lighting, and material language; truthful nesting and adjacency
matter more than spectacle. Put short noun-and-job callouts on surrounding
white space with precise leaders. Reserve the full outer safety margin and
phone-readable annotation lanes before sizing the focal object, rather than
shrinking labels after the illustration is composed. Popsci may add tactile museum-editorial depth;
ELI5 reduces the number of layers and uses everyday words. Neither style may
use gore, cheap transparency, exploded parts, impossible interiors, label
forests, or a tinted page.

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

Nature's production rules prefer editable vector artwork. Grounded deliberately
overrides the source corpus's lower-case panel convention with uppercase A–D for
clear reader references. The skill uses capable image generation for complete
non-quantitative compositions and deterministic rendering only for verified
quantitative plots, with strict communication, pixel, provenance, visual-
quality, and non-distortion QA.
