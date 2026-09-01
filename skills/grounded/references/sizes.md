# Sizes and styles

A review has a **size** (`small`, `medium` default, `large`/`big` — how much evidence) and a **style** (`scientific` — alias `prose` — `popsci` default, `bullets`, `eli5` — how it is written). The axes are independent: "medium scientific" and "large eli5" are both valid requests. Unless the request names the size, the style, and the output format, immediately ask one short question for the missing dimension(s) before any other work (see "First: confirm size, style, and output format" in `SKILL.md`); medium popsci as a journal PDF is the default when the user says "you pick" or the session cannot ask. Bigger sizes add sections, evidence and tables — never longer sentences.

Styles change the writing register and jargon treatment — never search depth, source counts, citations, or verification. The register spectrum runs scientific → popsci → ELI5: a journal reader, a curious educated adult, a smart reader with no science background.

- **Scientific** (explicit: `scientific`; alias `prose`, its former name): a narrative article in journal register — abstract, introduction, thematic sections of topic-sentence paragraphs, conclusion. Body budget: small 600–1,000, medium 1,500–2,500, large 3,500–6,000 words. Rules in `style-scientific.md`.
- **Popsci** (default; also explicit: `popsci`, "popular science", "magazine style", "science journalism", or naming Scientific American / New Scientist / Quanta): a magazine feature — honest headline, citation-free standfirst, concrete cited lede, nut graf, narrative crossheads with the contrary evidence as the turn, kicker — jargon named, glossed inline, and linked. Same body budgets as scientific. Rules in `style-popsci.md`.
- **Bullets** (explicit: "bullets", "list", "compact structured format"): question → TL;DR → punchline headings → cited bullets → sources. Body budget: small 350–700, medium 900–1,600, large 2,000–4,000 words. Layout in `style-bullets.md`.
- **ELI5** (explicit: `eli5`, "explain like I'm five", very simple language): a step-by-step explanation in short paragraphs and very simple English at the chosen size (defaults medium) — a familiar starting point, one new idea per section built on the steps before it, the contrary evidence as its own step, and a hand-back ending. It rewrites jargon instead of applying the normal term-link pattern. It is not a bullet format unless the user explicitly asks for bullets too. Rules in `style-eli5.md`.

The **output format** — `inline chat`, `journal PDF` (default), or `slides` — is the third independent axis, included in the same ask-back when missing. The journal PDF always includes generated figures, with a size-scaled visual target and ceiling (small target 2/cap 2, medium target 3/cap 5, large target 5/cap 8), per `media-modes.md`. These are distinct evidence jobs, not illustration quotas; one is still valid when the synthesis genuinely contains only one visual story. Slides combines with any size and style and is itself the deliverable — a verified 16:9 PDF of standalone slides, with a 1–3 sentence plain answer in chat and the written synthesis kept as an internal working draft, per `deck-guide.md`.

| | Small | Medium (default) | Large |
|---|---|---|---|
| Scientific/popsci prose words | 600–1,000 | 1,500–2,500 | 3,500–6,000 |
| Bullet body words | 350–700 | 900–1,600 | 2,000–4,000 |
| ELI5 narrative body words | 350–700 | 900–1,600 | 2,000–4,000 |
| Sections | 3–5 | 6–9 | 10–15 |
| Evidence units per section | 2–4 | 3–5 | 3–6 |
| Sources | 10–20 | 30–60 | 70–150 |
| Synthesis claims | 5–12 | 10–25 | 20–45 |
| Angles searched | 3–5 | 5–8 | 8–12 + citation chasing |
| Queries per angle | 1–2 | 2–3 | 3–5 |
| Full texts read | 2–4 load-bearing | 8–15 | 25+ |
| Tables | 0–1 | 1–2 | 2–4 |
| Journal-PDF figures | target 2, cap 2 | target 3, cap 5 | target 5, cap 8 |
| Slides: content slides | 4–6 | 8–12 | 14–20 |
| Slides: total | 6–8 | 10–15 | 18–25 (hard max 25) |

## Small

Answer the question and stop. Typical sections: the direct evidence, the contrary case, who it varies for, what would settle it. One table if several studies share dimensions. Read the load-bearing papers in full; abstracts for the rest.

## Medium (default)

More angles, not denser paragraphs or bullets: add mechanism, moderators, measurement problems, harms, and recent work as their own thematic sections. Expect at least one comparison table. Use when the user asks, or when the question has several genuinely distinct sub-questions.

## Large / big

Full coverage of the field: history, competing frameworks, generalisability, quality of the evidence base, research agenda — each as a distinct thematic section. Multiple tables. Citation chasing on the central papers. Use only when the user asks for `large` or `big`.

## Journal PDF and slides

The journal PDF uses the selected review tier and scales its mandatory figure cap with it. Every figure must synthesize the same verified evidence; it is not a separate unsourced interpretation.

Slides use the selected review tier. The content-slide and total-slide ranges are caps, not quotas: use the shortest complete style arc. The renderer adds the title and closing reference slides, and large decks may never exceed 25 total pages. Size changes the amount of evidence and the deck length; style changes the storyboard genre. Neither changes search, reading, verification, or citation requirements.

## When the literature does not match the size

When the user explicitly names a tier, run `validate_review.py --strict-tier` so its word, source, section, table, and figure-cap ranges plus the authenticated-full-text minimum are hard gates. If a topic has 12 papers, do not pad: record a structured thin-literature override with a substantive reason and saturation evidence. The override may excuse only genuine source/full-text/search shortfalls, never missing prose, sections, tables, or figure legibility. If a field has thousands of papers, tighten the question rather than sprawling.
