# Figure captions and cross-references

Use this contract for every rendered figure: generated image, deterministic
SVG, chart, diagram, or mindmap. A figure is not complete until it has a stable
ID, a cited caption, and a reference from the review body.

Deck content images are the one delivery-specific exception to the Markdown
caption shape: `deck-guide.md` puts the full-sentence claim and verified DOI
citations in real-text slide chrome instead. The image still obeys the same
exact-text, data, science, uncertainty, and visual-inspection contract, and a
content slide with no chrome citation is a hard failure.

## What a caption must do

A caption is part of the evidence-bearing manuscript. It must:

1. begin with a short declarative title that states the visual's point without prescribing action;
2. explain what is shown and how to read any non-obvious encoding;
3. state the important evidence boundary or uncertainty;
4. end with 2–5 citations from the verified review ledger;
5. use the same language register as the review: scientific, popsci, bullets, or ELI5.

For a quantitative figure, the explanatory body must explicitly say what the
x-axis and y-axis represent, including units or categories, even when the
artwork uses direct endpoint labels. It must also explain the interval encoding
once. Do not make the reader infer axis semantics from tick labels. A
conventional point-and-whisker needs no redundant in-plot legend when the
caption already defines the estimate and interval.

Expand abbreviations and carry interpretation prose here rather than placing a
glossary or caption-like heading inside the artwork. Quantitative panel headings
are short local identifiers only; the caption owns definitions, axis summaries,
and the meaning of the comparison.

Do not use a caption as a source dump, repeat the surrounding section, or hide
a scientific caveat that belongs in the image itself. Caption citations support
what the figure depicts; they do not replace citations on empirical claims in
the body.

## Draft syntax

Use a lowercase stable ID made of letters, digits, and hyphens. Do not type a
figure number: `format_references.py` assigns numbers from figure order.

Introduce the subject before the figure and reference it from the relevant body
sentence or bullet. Keep the result and its necessary qualification together:

```markdown
The dashed segment in {{figure:mechanism}} marks the pathway supported mainly by animal experiments [@Pardi2024; @Li2022].
```

Then add the figure and caption:

```markdown
![Specific alt text describing the visible layout and scientific point](mechanism.png)

**Figure {#mechanism}. A transient RNA signal builds immune memory.** Delivery and temporary expression are observed; the dashed signalling stage is supported mainly by animal experiments [@Pardi2024; @Li2022].
```

The formatter produces clickable final Markdown:

```markdown
The dashed segment in [Figure 1](#fig-mechanism) marks the pathway supported mainly by animal experiments [Pardi & Krammer 2024](https://doi.org/...), [Li et al. 2022](https://doi.org/...).

<a id="fig-mechanism"></a>
![Specific alt text describing the visible layout and scientific point](mechanism.png)

**Figure 1. A transient RNA signal builds immune memory.** Delivery and temporary expression are observed; the dashed signalling stage is supported mainly by animal experiments [Pardi & Krammer 2024](https://doi.org/...), [Li et al. 2022](https://doi.org/...).
```

Caption citations pass through the same ledger verification as body citations
and automatically enter the generated Sources block.

## Match the writing style

### Bullets

Use either a compact caption or a short structured caption. State the visual's
point and preserve the comparison and uncertainty without redundant prose.

```markdown
**Figure {#waning}. Protection wanes faster against infection.**
- **Shows:** Average change from month 1 to month 6 for infection and severe disease.
- **Evidence boundary:** Equal row sizes prevent a false visual comparison; the data precede Omicron.
- **Sources:** [@Feikin2022; @Tang2022]
```

### Scientific

Use a short flowing paragraph, normally 2–4 sentences. Begin with the finding,
then explain the visual and its limitation. Keep the objective narrative-review
register used in the body.

```markdown
**Figure {#waning}. Protection wanes faster against infection than severe disease.** The aligned estimates separate outcome-specific decline from the mechanisms proposed to explain it. Equal visual areas do not encode magnitude, and the studies do not quantify how much each mechanism contributes [@Feikin2022; @Tang2022].
```

### Popsci

Use a short flowing paragraph in the magazine register. Describe the visual's
point and relevant encoding, with the evidence boundary integrated into the
explanation. Use interpretable quantities and the shared reporting voice.

```markdown
**Figure {#waning}. Protection declines at different rates for different outcomes.** The upper row shows the change in protection against infection from month one to month six; the lower row shows the change for severe disease. Equal row areas do not encode the amount of protection, and the observations predate Omicron [@Feikin2022; @Tang2022].
```

### ELI5

Use a short flowing paragraph of connected sentences in everyday words.
Explain any line, colour, or symbol that a new reader could misunderstand. Keep
the uncertainty; simplify the words, not the evidence. Do not switch back to a
structured bullet caption unless the user explicitly asked for bullets.

```markdown
**Figure {#waning}. The vaccine's infection shield gets weaker faster.** The top row is about catching the virus. The bottom row is about getting very sick. The rows are the same size on purpose, so their size is not the amount of protection [@Feikin2022; @Tang2022].
```

## Reference placement

- Refer to a figure where it helps the current explanation, after introducing
  its subject. Its placement must not separate a finding from its necessary
  qualification or interrupt one study's discussion to illustrate another.
- In bullets, add a short navigational clause to an already relevant cited
  bullet, or use a citation-free navigation bullet that makes no new empirical
  claim.
- In scientific style, integrate the reference grammatically: “As shown in
  `{{figure:mechanism}}`, …”.
- In popsci and ELI5, describe the relevant part in ordinary language:
  “The gap in `{{figure:mechanism}}` marks the step that remains untested.”
  The wording must match the actual image and checked evidence; do not add a
  separate command to look, follow or compare.
- Refer to the whole figure as `{{figure:id}}`; refer to a panel as
  “panel A of `{{figure:id}}`”. Panel letters use sequential uppercase A–D in
  scientific, popsci, bullets, and ELI5 figures.

## Alt text and caption are different

Alt text describes what is visibly present and the reading order for someone
who cannot see the image. The caption interprets the scientific point, scope,
and evidence. Do not copy one into the other.

## Deterministic checks

`format_references.py` fails when:

- an image lacks a caption;
- a caption lacks a stable ID, explanatory body, or ledger citation;
- a figure ID is duplicated;
- a body reference names an unknown figure;
- a declared figure is never referenced from the body; or
- any caption citation is unknown, unverified, or retraction-unclear.

`export_review.py` repeats the final checks on numbered captions, DOI links,
figure order, anchors, and body cross-references before writing HTML or PDF.

On the no-script path, number figures in appearance order, add an HTML anchor
`<a id="fig-<stable-id>"></a>` immediately before each image, link body mentions
as `[Figure N](#fig-<stable-id>)`, and enforce the same caption and citation
requirements manually.
