# Figures for journal PDFs and slides

Read this reference whenever the selected output is a journal PDF or slides. It
defines when media is required, how many distinct visual jobs to plan, and how
finished figures enter the deliverable. The production recipe lives in
`figure-generation-contract.md`; do not restate it here.

## Shared evidence boundary

Plan media only after `synthesis.md` is complete. Figures and slides may depict
only claims, relationships, mechanisms, comparisons, quantities, and
uncertainties already supported there. They never relax search, reading,
citation, or verification requirements and never convert association into
causation, hypotheses into established mechanisms, or group averages into
individual predictions.

Generate and inspect the actual media. A prompt, text outline, ASCII diagram, or
unrendered source is not a figure. If required media tooling is unavailable,
deliver the written review and state briefly that the visual could not be
generated; never imply that an uninspected artifact passed.

For every figure, read `figure-generation-contract.md`. Then load only the
route-specific references it names:

- generated/composite prompting: `image-prompt-guide.md`;
- visual identity: `figure-style-system.md`;
- inspection/provenance schemas: `figure-inspection-contract.md`;
- captions and body references: `figure-captions.md`;
- feedback meant to improve unseen figures:
  `figure-feedback-generalization.md`.

## Journal-PDF coverage

Every journal PDF includes synthesis-grounded figures. Coverage scales with the
selected review size:

| | Small | Medium | Large |
|---|---:|---:|---:|
| Normal target | 2 | 3–4 | 5–6 |
| Hard ceiling | 2 | 5 | 8 |

These are distinct evidence jobs, not quotas. Normally Figure 1 gives the
whole-answer synthesis; additional figures may explain a mechanism, study
design, exact quantitative result, comparison/moderator, or uncertainty
boundary. Use fewer when the synthesis contains fewer genuinely visual stories.
Never pad coverage with decoration, a recoloured duplicate, or a graphical
restatement of a table.

Each figure must answer one visual question and remain understandable to an
educated non-specialist. Place it immediately after the section it supports,
introduce it in the body, and use stable-ID cross-references. Set
`render_context: article`; the caption supplies the title and scope, so do not
repeat a hero title or subtitle inside the artwork.

Use this draft contract:

```text
The mechanism is summarized in {{figure:mechanism}}.

![<specific alt text: visual structure and scientific point>](<figure file>)
**Figure {#mechanism}. <declarative title>.** <style-matched explanation, evidence boundary, and 2–5 ledger citations>
```

The formatter assigns figure numbers, validates caption citations, creates
anchors, and resolves body tokens. Scientific, popsci, bullets, and ELI5 may
differ in caption voice, never in evidence or QA. Full caption rules are in
`figure-captions.md`.

## Slides

Slides are explicit-only and are the deliverable: chat contains the sharpened
question, a one-to-three-sentence answer, and the verified 16:9 PDF.
`synthesis.md` remains a working file. Read `deck-guide.md` before
storyboarding.

Every content slide uses `render_context: slide`, a full-sentence cited claim
in renderer chrome, a `strong`/`mixed`/`limited` evidence grade, and artwork
that carries the evidence itself. It must pass the standalone test: claim,
evidence, and firmness are understandable without a presenter or separate
review. The deck exporter owns presentation chrome and references. If capable
image generation is unavailable or the images cannot pass QA, deliver the
verified synthesis as a normal review instead.

## Delivery gate

Before release, confirm that:

1. each visual performs a distinct synthesis-grounded explanatory job;
2. uncertainty and disagreement remain visible;
3. the selected route passed the communication-first workflow;
4. labels, relationships, values, anatomy, and geometry were inspected at native
   and final size;
5. every figure has a stable ID, body introduction, style-matched caption, and
   two to five verified caption citations;
6. journal PDF or deck QA proves readable typography and aspect-preserving
   placement without shear or anisotropic scaling.
