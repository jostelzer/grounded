# Sizes and styles

A review has a **size** (`small`, `medium` default, `large`/`big` — scope and depth) and a **style** (`scientific`, alias `prose`; `popsci` default, `bullets`, `eli5` — audience and presentation). The axes are independent: "medium scientific" and "large eli5" are both valid requests. Infer missing dimensions from context; otherwise use medium popsci as a journal PDF and start work. Ask only when ambiguity materially changes the task. Size changes coverage; sentence length follows the explanation.

Styles change the writing register and jargon treatment — never search depth, source counts, citations, or verification. The register spectrum runs scientific → popsci → ELI5: a journal reader, a curious educated adult, a smart reader with no science background.

- **Scientific** (explicit: `scientific`, alias `prose`): a narrative article in journal register — abstract, introduction, thematic sections of topic-sentence paragraphs, conclusion. Body budget: small 600–1,000, medium 1,500–2,500, large 3,500–6,000 words. Rules in `style-scientific.md`.
- **Popsci** (default; also explicit: `popsci`, "popular science", "magazine style", "science journalism", or naming Scientific American / New Scientist / Quanta): accessible reporting with an honest headline, citation-free standfirst and a connected explanation under informative crossheads. Jargon is glossed and linked. Same body budgets as scientific. Rules in `style-popsci.md`.
- **Bullets** (explicit: "bullets", "list", "compact structured format"): question → TL;DR → informative headings and connected cited bullets → sources. Body budget: small 350–700, medium 900–1,600, large 2,000–4,000 words. Layout in `style-bullets.md`.
- **ELI5** (explicit: `eli5`, "explain like I'm five", very simple language): connected paragraphs that introduce ideas before relying on them, using everyday words and a plain answer with its uncertainty. It is not a bullet format unless bullets are also requested. Rules in `style-eli5.md`.

The **output format** — `inline chat`, `journal PDF` (default), or `slides` — is the third independent axis, inferred from the request or defaults when missing. The journal PDF always includes generated figures, with a size-scaled visual target and ceiling (small target 2/cap 2, medium target 3/cap 5, large target 5/cap 8), per `media-modes.md`. These are distinct evidence jobs, not illustration quotas; one is still valid when the synthesis genuinely contains only one visual story. Slides combines with any size and style and is itself the deliverable — a verified 16:9 PDF of standalone slides, with a 1–3 sentence plain answer in chat and the written synthesis kept as an internal working draft, per `deck-guide.md`.

The authoritative budgets are generated in [budgets.md](budgets.md) from `scripts/review_config.py`. Source ranges are advisory.

## Small

Answer the focused question with the evidence and qualifications needed to understand it. Use a table when shared dimensions make the comparison clearer. Read the load-bearing papers in full; abstracts for the rest.

## Medium (default)

Develop additional relevant questions, such as mechanisms, variation, measurement or harms, where they contribute to the answer. Integrate them into the explanation instead of assigning a section to each available evidence category. Use comparison tables where appropriate.

## Large / big

Cover the defined scope in depth, including relevant history, competing explanations, generalisability and unresolved questions. Retain a connected argument as coverage expands; do not claim systematic completeness from length alone. Use multiple useful tables and chase citations from central papers. Use only when the user asks for `large` or `big`.

## Journal PDF and slides

The journal PDF uses the selected review tier and scales its mandatory figure cap with it. Every figure must synthesize the same verified evidence; it is not a separate unsourced interpretation.

Slides use the selected review tier. The content-slide and total-slide ranges are caps, not quotas: use the shortest complete style arc. The renderer adds the title and closing reference slides, and large decks may never exceed 25 total pages. Size changes the amount of evidence and the deck length; style changes the storyboard genre. Neither changes search, reading, verification, or citation requirements.

## When the literature does not match the size

When the user explicitly names a tier, run `validate_review.py --strict-tier` so its word, section, table, and figure-cap ranges plus the authenticated-full-text minimum are hard gates. If a topic has 12 papers, do not pad: record a structured thin-literature override with a substantive reason and saturation evidence. The override may excuse only genuine source/full-text/search shortfalls, never missing prose, sections, tables, or figure legibility. If a field has thousands of papers, tighten the question rather than sprawling.
