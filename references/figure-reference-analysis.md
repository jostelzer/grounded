# Nature-family figure reference analysis

This is the visual evidence base for the bundled journal-inspired profiles. It
is a style analysis, not an official Nature template. Never reproduce a source
figure, trace its artwork, reuse its scientific content, or add Nature branding.

## Corpus and method

The committed manifest in `nature-figure-corpus.json` identifies 21 figures
from 12 official Nature article pages published between 2019 and 2025:

- 15 figures from *Nature Reviews Neuroscience*;
- 6 figures from *Nature Neuroscience*;
- 11 mechanism examples, 7 comparisons, 6 conceptual syntheses, 6 cellular
  examples, 5 study overviews, and smaller samples of quantitative, timeline,
  spatial-model, anatomy, task, and network figures. Roles overlap.

The source pixels are analysis inputs only and are never repository assets.
When the profiles need to be re-audited, download them to an explicit private
temporary directory:

```bash
python3 scripts/download_figure_references.py --out /private/tmp/nature-figure-corpus
```

The downloader checks the PNG signature, records dimensions, byte counts,
SHA-256 hashes, and source URLs in `download-report.json`, and never writes
source images into the skill by default.

## What the corpus consistently does

### Figure-native framing

- The artwork normally starts with panel content. The article caption supplies
  the figure title; the pixels do not contain a large title and subtitle.
- Lower-case bold panel letters (`a`, `b`, `c`) sit at the true upper-left of a
  panel. They are navigation, not decoration.
- A shared invisible grid and white space establish groups before boxes do.
  Panels are not automatically turned into equal rounded cards.

### Typography and annotation

- Compact black or near-black sans-serif labels dominate. Bold is reserved for
  panel letters and short local headings.
- Labels sit next to the structure, trace, or region they explain. Short leaders
  replace glossary-heavy footer bars when a local annotation is sufficient.
- Legends are small, close to their data, and unboxed or only lightly bounded.
  Text hierarchy remains deliberately shallow.

### Geometry and scientific primitives

- Layout follows the scientific representation: anatomy, signal flow, task
  timing, mathematical geometry, experimental pipeline, or data comparison.
  A universal sequence of presentation columns is not imposed on the science.
- Thin black or grey arrows are the default. Colour is used on arrows only when
  direction or pathway identity is itself encoded.
- Biology is simplified but morphologically specific. Cells, tissue, brain
  outlines, molecular assemblies, waveforms, equations, and axes are treated as
  scientific primitives rather than replaced with generic icons.
- Quantitative figures keep axes, scales, uncertainty, and denominators visually
  primary. Conceptual figures can be dense, but each mark still has a role.

### Colour and surface

- White canvas dominates. Pale cyan, blue, lavender, salmon, muted green, and
  occasional yellow or orange distinguish entities and regions.
- Saturated colour is reserved for a contrast or focal signal. Repeated entities
  keep exactly the same colour across panels.
- Very pale tints or light grey may group a molecular region or comparison band.
  Full-canvas texture, glossy lighting, drop shadows, and ornamental gradients
  are absent.

## Profile consequences

The profiles therefore separate two render contexts:

- `article` is the default for figures inserted into a review or PDF. Keep the
  title and explanatory caption outside the artwork. Render all panel letters,
  labels, values, units, legends, and essential qualifiers inside the figure.
- `standalone` is for a figure delivered without adjacent caption context. It
  may render a compact title and, only when essential, a short subtitle. The
  title must not become a poster headline.

Across both contexts, prefer content-led topology, local labels, exact domain
primitives, pale semantic colour, and open white space. A glossary is permitted
only when a necessary abbreviation or encoding cannot be defined locally.

## Failure signatures

Reject or revise a result that looks like a presentation slide, marketing
infographic, dashboard, or mobile interface. Frequent symptoms are:

- an oversized title consuming the top quarter of the canvas;
- four equal rounded cards regardless of the scientific relationships;
- a decorative footer glossary or warning banner;
- generic shield, checkmark, book, or app icons standing in for evidence;
- saturated colour blocks, large coloured prose, or rendered background texture;
- oversized numbers whose typography matters more than their scale or context;
- arrows, panels, or anatomy chosen for polish rather than scientific meaning.

## Maintenance boundary

Use the manifest and private downloader to periodically test whether the style
grammar still spans both review synthesis and primary-research overview figures.
Add sources for a missing archetype, not merely more examples of an already
well-represented look. Keep article URLs and brief analytical metadata in the
repository; keep downloaded copyrighted pixels outside it.
