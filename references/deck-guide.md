# Deck mode

Read this reference only when the user explicitly requests `deck`, `slides`, a
`presentation`, a `slide deck`, or a `journal club deck`. Never infer deck mode
because the topic is visual or because slides might be useful. Deck runs the
complete Grounded evidence pipeline: angles, searching, reading, verification,
evidence weighing, and ledger construction do not change. The synthesis is
still written — as an internal working draft that drives the storyboard — but
it is a working file, not the deliverable.

**The deck is the deliverable.** The reader gets the slides, not a written
review, so the slides must carry the entire answer. Deliver in chat: the
sharpened question, a 1–3 sentence plain-language answer in the selected
style's register (the TL;DR register), and the deck PDF. Do not paste a full
styled review into the chat and do not treat the deck as figures attached to
one; produce a delivered written review as well only when the user explicitly
asks for both. Version 1 is 16:9 PDF only: no 4:3 variant, PowerPoint,
reveal.js, or browser renderer.

## The standalone test — the rule the whole mode hangs on

A Grounded deck is read, not presented. Assume no presenter, no talk track, no
chat context, and no other slide: a reader who opens the PDF at any content
slide must be able to answer three questions from that slide alone —

1. **What is claimed?** (the full-sentence title)
2. **What is the evidence?** — who or what was studied, how many, what was
   compared or measured, and what the numbers say (the artwork)
3. **How firm is it?** — the uncertainty, visible in the artwork itself, with
   the evidence chip as reinforcement, never as the only carrier.

A slide that needs narration, the written synthesis, or a neighbouring slide to
be understood is unfinished, no matter how attractive its artwork. Apply this
test to every content slide before export and again on the rendered raster
pages during QA; a failing slide is a release blocker.

## Evidence boundary

- Start storyboarding only after the internal written synthesis is complete and
  every cited source has passed Crossref bibliographic verification and
  retraction screening.
- Build every slide from the final synthesis, including contrary findings,
  limitations, population boundaries, and uncertainty. Do not storyboard from
  preliminary search impressions.
- Every content-slide title is a full-sentence assertion or question and carries
  at least one verified ledger citation in that slide's footer. A content slide
  with zero citations fails before rendering.
- Use `strong`, `mixed`, or `limited` as the evidence grade. The grade describes
  support for the slide's exact claim, not the topic as a whole.
- Keep claim titles, citation labels, DOI links, evidence grades, and slide
  numbers as real HTML/PDF text. Never ask the image model to paint them.
- Internal image text is labels, values, units, intervals, legends, essential
  qualifiers, and brief reading-guide annotations under the normal figure QA
  contract. Numbers, geometry, anatomy, arrows, and uncertainty must match the
  verified synthesis.
- List only verified ledger keys in the storyboard. Normally `reference_keys`
  contains every source cited in the internal synthesis; every per-slide
  citation must be a member of that list.

## Slide budgets

These are caps, not targets. Use the shortest deck that carries the selected
style's argument; never pad to the upper bound.

| Size | Content slides | Total PDF slides |
|---|---:|---:|
| Small | 4–6 | 6–8 |
| Medium | 8–12 | 10–15 |
| Large | 14–20 | 18–25, hard maximum 25 |

The renderer adds one title slide and the closing reference slides. It allocates
reference slides from the verified reference count, with at most 38 entries per
reference slide, while enforcing the selected total range. Large decks reserve
at least three reference slides so a 14-slide evidence arc still reaches the
18-slide minimum. If the references and content cannot fit below the selected
cap, reduce content slides or tighten the evidence selection; never shrink or
drop references silently.

## Storyboard grammar by style

Style changes the sequence and language, not the evidence.

### Scientific

Use a journal-club arc: `question` → one or more `evidence` slides →
`limitations` → `conclusion`. The first slide sharpens the research question;
the middle compares the load-bearing findings; the limitations slide gives the
best contrary or boundary evidence full visual weight; the conclusion states
what the evidence supports now.

### Popsci

Use `hook` → one or more `story` slides → one `contrary-evidence` turn →
`kicker`. The hook is concrete and honest, not sensational. The turn must be a
dedicated slide rather than a caveat hidden in a footer. The kicker resolves the
opening image without outrunning the evidence.

### Bullets

Use one `tldr` slide followed by `point` slides. The rendered slides still have
no bullet-list body: each point becomes one full-sentence claim and one
punchline image. Do not place several list items in the pixels.

### ELI5

Use `idea` for every content slide. Each slide carries one simple idea in plain
language, with everyday labels in the image. Simplify the words, not the
evidence, quantities, disagreement, or uncertainty.

## Storyboard contract

Write `storyboard.json` beside the generated slide images. The renderer rejects
unknown fields so misspelled contract keys cannot disappear silently.

```json
{
  "title": "What the evidence says about the intervention",
  "subtitle": "A verified journal-club review",
  "style": "scientific",
  "size": "small",
  "kicker": "Journal club",
  "reference_keys": ["Review2024", "Trial2022"],
  "slides": [
    {
      "id": "question",
      "role": "question",
      "title": "The intervention may improve the target outcome, but the relevant effect is uncertain.",
      "image": "question.png",
      "alt": "Two aligned outcome paths show the claimed benefit and the unresolved evidence gap.",
      "citations": ["Review2024"],
      "evidence": "mixed"
    },
    {
      "id": "direct-evidence",
      "role": "evidence",
      "title": "Randomized trials show a small average benefit over the control condition.",
      "image": "direct-evidence.png",
      "alt": "A dot-and-whisker comparison shows small trial effects and their confidence intervals.",
      "citations": ["Review2024", "Trial2022"],
      "evidence": "strong"
    },
    {
      "id": "limitations",
      "role": "limitations",
      "title": "Short follow-up and heterogeneous measures limit confidence in durability.",
      "image": "limitations.png",
      "alt": "A timeline and measurement comparison highlight short follow-up and incompatible outcome scales.",
      "citations": ["Review2024", "Trial2022"],
      "evidence": "limited"
    },
    {
      "id": "conclusion",
      "role": "conclusion",
      "title": "The current evidence supports a modest short-term effect, not a durable universal benefit.",
      "image": "conclusion.png",
      "alt": "A calibrated summary separates the supported short-term effect from unsupported broader claims.",
      "citations": ["Review2024", "Trial2022"],
      "evidence": "mixed"
    }
  ]
}
```

Required top-level fields:

- `title`: deck title used on the title slide.
- `style`: `scientific`, `popsci`, `bullets`, or `eli5`.
- `size`: `small`, `medium`, or `large`.
- `reference_keys`: unique verified ledger keys used for the closing references.
- `slides`: content slides in reading order.

Optional top-level fields:

- `subtitle`: one short scope line for the title slide.
- `kicker`: a short running label; the style default is used when omitted.

Every content slide requires:

- `id`: unique lowercase letters, digits, and hyphens;
- `role`: one of the roles allowed by the selected style arc;
- `title`: a full sentence ending in `.`, `?`, or `!`;
- `image`: local PNG, JPEG, or WebP with a 16:9 pixel ratio;
- `alt`: specific reading-order text describing what is visibly present;
- `citations`: one to five unique verified ledger keys; and
- `evidence`: `strong`, `mixed`, or `limited`.

## Image specification

**The artwork is the evidence, not an illustration of it.** Because the deck is
the deliverable, each content slide's image must function as a complete,
self-explanatory scientific figure — the kind a reader could study for thirty
seconds and then explain to someone else. Atmospheric, decorative, or merely
topical full-bleed artwork is a release failure however attractive: if the
image tells the reader nothing the claim title didn't already say, it is
decoration, and the slide fails the standalone test.

Every content-slide image must therefore:

- **show the evidence itself** — the comparison, the plotted numbers with units
  and intervals, the mechanism with every part labelled, or the study design as
  a simple pictured flow ("412 people got the drug → 405 got a dummy pill →
  12 weeks → both groups measured"); pick the archetype that carries this, not
  the prettiest one;
- **define everything on the slide** — every axis, symbol, abbreviation, and
  non-everyday term gets a local label, compact legend entry, or plain-word
  gloss in the pixels; the reader has no caption, body text, or glossary to
  fall back on;
- **carry a brief reading-guide annotation where the encoding is not obvious**
  — one short phrase telling the reader how to read the visual ("each dot is
  one trial; whiskers show the range the true effect could be in"), placed
  inside the image near what it explains;
- **make the uncertainty visible in the artwork** — interval whiskers, dashed
  hypothesized stages, a "based on 3 small studies" qualifier — not delegated
  to the evidence chip alone;
- **state the key numbers as numbers** — a slide whose claim contains a
  quantity must show that quantity (with its interval where reported) in the
  image, exactly matching the verified synthesis.

Create one figure specification per content slide and run
`scripts/build_figure_prompt.py` with `render_context: slide`. Reuse the normal
style profile and the archetype that best carries the evidence. Slide context
forces a full-bleed 16:9 canvas, removes an exact title/subtitle match from the
in-image text manifest, and reserves the top 19% and bottom 8% as visually quiet
zones for the canonical chrome.

The image can fill those zones with background colour or non-essential texture,
but no label, value, arrow, legend, focal anatomy, or plotted mark may depend on
them. Do not render a title banner, citation footer, evidence badge, masthead,
slide number, journal logo, dashboard card, or presentation furniture. The
image carries the evidence; the renderer carries the audit trail.

Generate the complete image with a capable image-generation model and inspect
it at full size and at its delivered PDF size. The normal text, data, science,
composition, and style defects in `image-prompt-guide.md` remain release
failures, and so does a failed standalone test. Unlike journal-PDF figures,
the slides format has no deterministic SVG or placeholder fallback: every content slide
is specifically an AI-generated image. If a capable image model is unavailable
or a required render cannot pass QA, do not manufacture a text slide or reuse
an unrelated figure.

## Canonical page anatomy

Every PDF page is landscape 16:9 and exactly one slide.

- **Title slide:** GROUNDED masthead as the hero, linked review descriptor, deck
  title and optional scope line, verified-reference count, compilation date,
  version, and `1 / total`.
- **Content slide:** a full-page generated image below the chrome; top strip with
  the electricity-ground mark, GROUNDED identity, linked review descriptor,
  style/role kicker, total-aware counter, version, and the real-text claim title;
  bottom strip with linked `Author 2024 · Author 2022` citations and the evidence chip.
- **Reference slides:** journal small type in two text columns, populated only
  from the verified ledger, with live DOI links and no generated body image.

The exporter embeds every content image as a data URI, rejects remote, missing,
escaping, unsupported, unreadable, and non-16:9 assets, and writes through the
same atomic pinned-WeasyPrint path as the journal PDF. It never uses Chrome,
reveal.js, PowerPoint, or a network fetch.

## Build and QA

Run the canonical commands from the skill repository:

```bash
python3 scripts/export_deck.py --check-pdf-runtime
python3 scripts/export_deck.py --storyboard storyboard.json --ledger sources.json --out review-deck.pdf
python3 scripts/qa_deck_pdf.py review-deck.pdf --storyboard storyboard.json --ledger sources.json --render-dir review-deck-qa
```

For checked-in or release artifacts, pass the intended version to both export
and QA with `--release vX.Y.Z`. Use a new or empty QA directory.

Structural QA must pass all of these:

1. strict, unencrypted PDF parsing and safe document actions;
2. canonical 960 × 540 pt pages and the exact storyboard page count;
3. Grounded metadata, pinned WeasyPrint producer, Charter, and Helvetica Neue;
4. GROUNDED identity, linked review descriptor, version, and `N / total` on every slide;
5. one painted raster body image on every content slide and none on title or
   reference bodies;
6. the full-sentence claim and evidence grade as extractable content-slide text;
7. every content slide's expected DOI annotations on that same PDF page; and
8. every closing-reference DOI present and live.

Poppler raster QA must then inspect every landscape page for painted masthead,
orange chip, counter, claim, image body, citation footer, evidence chip,
reference text, consistent dimensions, and chrome clipping at both side edges.
Inspect every individual PNG and every contact sheet visually, and apply the
standalone test to each rendered content slide: from that page alone, the
claim, the evidence behind it (who or what, how many, what was compared, what
the numbers say), and its firmness must all be readable. Text touching an
edge, a clipped or covered label, a missing chrome element, a blank image, an
unreadable reference column, a malformed DOI label, any image defect under
the figure QA contract, or a slide that fails the standalone test blocks
delivery. Repeat full-deck raster inspection after every layout or storyboard
change.

## Fallback

If no capable image-generation model is available, the deck cannot exist — so
the deliverable falls back to the written review: deliver the internal
synthesis as a normal full review in the selected style and size, and add one
sentence: “The deck could not be generated because a capable image-generation
model was unavailable.” Do not provide a prompt, outline, placeholder deck,
text-only substitute, SVG reconstruction, or unverified PDF.
