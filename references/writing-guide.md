# Writing guide

The review is delivered **as the chat message itself** — not as a file, attachment, artifact, or canvas. Markdown renders in the conversation; a `.md` file does not preview in most clients and opens in a code editor with the formatting stripped, which makes good work look broken. Write it in the reply.

Create a file only if the user asks, and even then also put the review in the chat. Image and mindmap modes add a rendered media artifact by design; they do not move the written review into a file.

It is not a document with front matter, not an essay, and not a report about itself. Every word earns its place.

## The output shape — use this exactly

```
## <The question, as concisely as it can be stated>

**TL;DR** — <the answer in 1–3 sentences, plain language, no citations, no hedging padding>

### <Punchline of section 1 — a claim, stated concisely>
- <evidence with numbers> [Author 2026](https://doi.org/…)
- <evidence with numbers> [Author & Author 2025](https://doi.org/…)

### <Punchline of section 2>
- …

**Sources**
**Author 2026** Title. *Journal*. https://doi.org/…
```

In-text citations render as plain `Author 2026` links: the square brackets are markdown link syntax only and must never be visible in the finished text. If the delivered review shows a bare `[Author 2026]`, `[1]`, or `(Author, 2026)`, it is wrong — every citation is a hyperlink whose visible text is just the author and year.

Nothing before the question. No scope note, no assumptions paragraph, no audience statement, no size label, no date line, no "how this was produced" section.

In explicit image or mindmap mode, keep this written structure unchanged at small depth and insert the rendered media section immediately before **Sources**, using the shape and caption rules in `media-modes.md`.

### The question
One line. The user's question sharpened, not restated at length. If they asked something conversational, compress it to its scientific core.

### TL;DR
The answer, immediately. One to three sentences. **No citations** — they belong in the sections. Say what the evidence supports and how firmly, in plain words ("Probably not", "Yes for X, unclear for Y"). No throat-clearing, no "the evidence is complex".

### Sections
- **The heading is the punchline** — a concise claim that carries the finding, so someone reading only the headings gets the whole argument. "Head-to-head trials show no HbA1c advantage", not "Head-to-head trials" and not "Results".
- **The body is bullets only.** No prose paragraphs under headings. Each bullet is one piece of evidence: what was found, in what study, with numbers, cited.
- Keep bullets tight — typically one sentence, two at most. Front-load the finding; put design and sample in a parenthesis.
- 2–5 bullets per section is usual. If a section needs more, it is probably two sections.
- Bold a few decisive numbers or terms sparingly — enough to guide the eye, not enough to look shouty.

### Ordering
Sequence sections so the argument builds. Usually: the direct answer first (strongest, most relevant evidence) → supporting or mechanistic evidence → the contrary case → who it varies for (moderators) → caveats and what would settle it. Adapt to the question; never order by date of publication or by how you found things.

### Contrast opposing views explicitly
When the literature disagrees, do not average it away. Either give the disagreement its own section with the punchline naming the tension ("Small trials and the large trial disagree — and size explains it"), or use bullets that pair the two sides. Then say which side the better evidence favours, or say plainly that it is unresolved.

### Tables
Use one whenever several studies or options share the same dimensions — competing trials, doses, populations, comparators, or the two sides of a disagreement. A table beats five parallel bullets. Keep to 3–5 columns, numbers in the cells, a citation in each row.

```
| Study | Design | n | Result | [ref] |
|---|---|---|---|---|
```

Do not force a table when the data does not line up; do not build one from a single study.

### Sources
Guidelines published as journal articles belong here and are cited as guidance ("the AAP recommends…"), not as evidence. Tertiary sources — StatPearls, UpToDate, textbooks — never appear; cite the primary study instead (`citation-rules.md`).

A compact block at the end: one line per source, `**Author 2026** Title. *Journal*. DOI link`, alphabetical. This is the only apparatus the review keeps — it is what makes the citations checkable, so it stays even though everything else is trimmed.

## Language

- **Concise above all.** Cut every word that does not carry information. Prefer the short form: "no benefit" over "did not demonstrate a statistically significant benefit".
- **Numbers, not adjectives.** Effect sizes with intervals, sample sizes, absolute risks. "HbA1c −0.06% (95% CI −0.27 to 0.16)" not "no meaningful improvement".
- **Design in a parenthesis**: "(12-mo RCT, n=137)". It calibrates the reader without a clause.
- **Calibrated strength**, per `evidence-weighing.md` — "probably", "may", "unclear" tied to actual evidence quality. No "proven", no bare "significant".
- **No hedging filler**: drop "it is important to note", "interestingly", "it should be emphasised".
- **Active and direct.** Name who found what.
- Define an abbreviation once, at first use.

## ELI5 language

In `eli5` mode only. The evidence pipeline, structure, citations, and verification are exactly small mode; only the register changes. Write for a smart reader with no science background at all.

- **Everyday words only.** "People in the study" not "participants"; "made-up pill" or "dummy pill" not "placebo"; "the studies disagree" not "heterogeneity". If a ten-year-old wouldn't know the word, don't use it.
- **Short sentences.** One idea per sentence. No semicolons, no nested clauses.
- **Numbers stay, but say what they mean.** Not "SMD −0.34 (95% CI −0.68 to −0.00)" but "the people taking creatine improved a little more — about 2 points on a 52-point mood questionnaire, which is too small a change for most people to feel. And the studies were so different from each other that the real effect could be zero."
- **Jargon is rewritten, not linked.** Term links are for standard modes; here the plain words replace the term entirely. If a term truly cannot be avoided (a scale's name, a drug class), name it once, explain it in the same sentence in plain words, and give it the usual verified term link.
- **Honesty survives the simplification.** "We don't really know yet" instead of silently dropping uncertainty. Small studies are "too small to trust on their own", not omitted. Never round a weak finding up to a strong claim because the plain words feel less precise.
- **Analogies are allowed, sparingly**, and must not smuggle in claims the sources don't make.
- **Citations unchanged.** Every factual bullet still ends with its author–year DOI links; punchline headings still tell the story, phrased in plain words ("The studies mostly say it helps a little, but they're small").
- TL;DR, sources block, and the quality gate all apply as normal.

## Term links

The first use of a technical abbreviation or specialist term is a markdown link to its English Wikipedia article — `[SMD](https://en.wikipedia.org/wiki/Standardized_mean_difference)`, `[GRADE](https://en.wikipedia.org/wiki/GRADE_approach)`, `[mRNA](https://en.wikipedia.org/wiki/Messenger_RNA)` — so a non-specialist can click for an explanation without leaving the review.

- **Link what a non-specialist would need explained**, not everyday scientific words: SMD, CI, OR, I², GRADE, HAM-D, PHQ-9, mRNA, phosphocreatine — yes; "placebo", "trial", "dose" — no.
- **First occurrence only**, anywhere in the review (body or table); later occurrences stay plain.
- **Not in the TL;DR** — it is written in plain language and should not need jargon at all.
- **Never link from memory.** Confirm the exact article URL resolves before using it — fetch the page with whatever network access the environment has (the same check as Step 0, or the web-fetch tool on the no-script path). Wikipedia article titles are guessable and often wrong; a link that 404s or lands on the wrong concept is worse than no link. If the target cannot be confirmed, expand the term inline and leave it unlinked.
- **Article pages only, no section anchors** — anchors rot; the article's lead section is usually enough.
- Wikipedia is the linked *explainer*, never a *source*: term links carry no evidential weight and nothing may be cited to them. Citations remain author–year links to DOIs; the two are distinguishable because citations always look like `Author 2026`.

## Length

Default **small**: aim for something a reader takes in within a couple of minutes — roughly 350–700 words in the body plus the sources block. Medium and large scale up the number of sections, bullets, and tables, never the wordiness of individual bullets. Sizes are in `sizes.md`.

## Citing

Write the draft with `[@key]` and let `format_references.py --style bracket` render each citation as an `[Author 2026](https://doi.org/…)` link and build the sources block. On the tool-only path, write the `[Author 2026](https://doi.org/…)` links directly, using the DOI from the verified Crossref record, and transcribe the sources block the same way.

## If verification could not be completed

- A DOI, title, year, or source-type mismatch is a bibliographic failure. Fix or remove that source and any dependent claim before delivering the review. An unverified citation must never reach **Sources**.
- A retraction relation in Crossref's publisher or Retraction Watch update metadata is also a hard failure. Remove the paper as evidence; do not merely decorate it with a warning.
- If Crossref is unavailable, verification is incomplete. Retry reasonably; if it still cannot be completed, omit the affected citations or state plainly that a verified review cannot be delivered yet. Do not publish warning-marked references.
- OpenAlex may be used for discovery, but its availability has no bearing on citation verification and is never mentioned in the finished review.

## Quality gate

0. The review is in the reply, not in a file (unless a file was requested).
1. Every bullet with an empirical claim carries a citation.
2. Headings alone tell the argument.
3. TL;DR has no citations and answers the question in the first sentence.
4. Opposing evidence appears, and is contrasted rather than blended.
5. A table exists wherever several studies share dimensions.
6. Numbers match sources; intervals included where reported.
7. Nothing before the question; no methods section; no audience or scope preamble.
8. Every cited key passed Crossref bibliographic and publisher/Retraction Watch retraction checks; any failure is excluded.
8b. Every term link points to a confirmed-resolving Wikipedia article, first use only; unconfirmed targets are unlinked and expanded inline.
9. Read it once and cut 10% more.
10. In image or mindmap mode, the requested visual is rendered, evidence-grounded, legible, inspected, and accompanied by a cited caption.
