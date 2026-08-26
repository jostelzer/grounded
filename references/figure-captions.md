# Figure captions and cross-references

Use this contract for every rendered figure: generated image, deterministic
SVG, chart, diagram, or mindmap. A figure is not complete until it has a stable
ID, a cited caption, and a reference from the review body.

## What a caption must do

A caption is part of the evidence-bearing manuscript. It must:

1. begin with a short declarative title that states the visual's point;
2. explain what is shown and how to read any non-obvious encoding;
3. state the important evidence boundary or uncertainty;
4. end with 2–5 citations from the verified review ledger;
5. use the same language register as the review: bullets, prose, or ELI5.

Do not use a caption as a source dump, repeat the surrounding section, or hide
a scientific caveat that belongs in the image itself. Caption citations support
what the figure depicts; they do not replace citations on empirical claims in
the body.

## Draft syntax

Use a lowercase stable ID made of letters, digits, and hyphens. Do not type a
figure number: `format_references.py` assigns numbers from figure order.

Reference the figure from the relevant body sentence or bullet:

```markdown
The delivery-to-memory pathway and its evidence boundary are summarized in {{figure:mechanism}}.
```

Then add the figure and caption:

```markdown
![Specific alt text describing the visible layout and scientific point](mechanism.png)

**Figure {#mechanism}. A transient RNA signal builds immune memory.** Delivery and temporary expression are observed; the dashed signalling stage is supported mainly by animal experiments. [@Pardi2024; @Li2022]
```

The formatter produces clickable final Markdown:

```markdown
The delivery-to-memory pathway and its evidence boundary are summarized in [Figure 1](#fig-mechanism).

<a id="fig-mechanism"></a>
![Specific alt text describing the visible layout and scientific point](mechanism.png)

**Figure 1. A transient RNA signal builds immune memory.** Delivery and temporary expression are observed; the dashed signalling stage is supported mainly by animal experiments. [Pardi & Krammer 2024](https://doi.org/...) [Li et al. 2022](https://doi.org/...)
```

Caption citations pass through the same ledger verification as body citations
and automatically enter the generated Sources block.

## Match the writing style

### Bullets

Use either one compact caption sentence or a three-line structured caption. The
title is a punchline; the lines are evidence-dense rather than paragraph-like.

```markdown
**Figure {#waning}. Protection wanes faster against infection.**
- **Shows:** Average change from month 1 to month 6 for infection and severe disease.
- **Evidence boundary:** Equal row sizes prevent a false visual comparison; the data precede Omicron.
- **Sources:** [@Feikin2022; @Tang2022]
```

### Prose

Use a short flowing paragraph, normally 2–4 sentences. Begin with the finding,
then explain the visual and its limitation. Keep the objective narrative-review
register used in the body.

```markdown
**Figure {#waning}. Protection wanes faster against infection than severe disease.** The aligned estimates separate outcome-specific decline from the mechanisms proposed to explain it. Equal visual areas do not encode magnitude, and the studies do not quantify how much each mechanism contributes. [@Feikin2022; @Tang2022]
```

### ELI5

Use very short sentences and everyday words. Explain any line, colour, or symbol
that a new reader could misunderstand. Keep the uncertainty; simplify the words,
not the evidence.

```markdown
**Figure {#waning}. The vaccine's infection shield gets weaker faster.**
- The top row is about catching the virus. The bottom row is about getting very sick.
- The rows are the same size on purpose. Their size is not the amount of protection.
- **Sources:** [@Feikin2022; @Tang2022]
```

## Reference placement

- Refer to a figure at the first point where it helps the argument, usually in
  the section immediately before it.
- In bullets, add a short navigational clause to an already relevant cited
  bullet, or use a citation-free navigation bullet that makes no new empirical
  claim.
- In prose, integrate the reference grammatically: “As shown in
  `{{figure:mechanism}}`, …”.
- In ELI5, use direct language: “You can see the steps in
  `{{figure:mechanism}}`.”
- Refer to the whole figure as `{{figure:id}}`; refer to a panel as
  “panel a of `{{figure:id}}`”. Panel letters remain lower-case.

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
