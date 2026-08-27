# Writing guide

The review is delivered **as the chat message itself** — not as a file, attachment, artifact, or canvas. Markdown renders in the conversation; a `.md` file does not preview in most clients and opens in a code editor with the formatting stripped, which makes good work look broken. Write it in the reply.

Create a file only if the user asks, and even then also put the review in the chat. The journal PDF format adds its rendered figures and PDF by design; it does not move the written review out of the chat.

It is not a document with front matter or a report about itself. Every word earns its place.

## Choose the writing style

Use **scientific by default** (the style previously named `prose` — treat `prose` as an alias). Its exact structure and narrative rules are in "Scientific style" below. Use the compact bullet structure only when the user explicitly asks for bullets, a list, or the compact structured format. Use **popsci** when the user asks for `popsci`, popular science, magazine style, science journalism, or names that register's magazines (Scientific American, New Scientist, Quanta). Use ELI5 only when requested; ELI5 is flowing prose in simpler language, not an implicit request for bullets.

The register spectrum runs scientific → popsci → ELI5: a journal reader, a curious educated adult, a smart reader with no science background. Bullets share the scientific register in compact form.

## Bullet style (explicit)

```
## <The question, as concisely as it can be stated>

**TL;DR** — <the answer in 1–3 sentences, plain language, no citations, no hedging padding>

### <Punchline of section 1 — a claim, stated concisely>
- <evidence with numbers> [Author 2026](https://doi.org/…).
- <evidence with numbers> [Author & Author 2025](https://doi.org/…).

### <Punchline of section 2>
- …

**Sources**
**Author A, Author B, Author C (2026)** Title. *Journal*. https://doi.org/…
```

In the chat review and source Markdown, in-text citations render as plain `Author 2026` links immediately after the supported words and before terminal punctuation: `claim [Author 2026](DOI).` The square brackets are markdown link syntax only and must never be visible. If the chat review shows `claim. [Author 2026](DOI)`, a citation-led sentence, a bare `[Author 2026]`, `[1]`, or `(Author, 2026)`, it is wrong. The journal PDF/HTML is the presentation-only exception: `export_review.py` converts those same DOI links to linked superscript numbers after the punctuation and a matching first-citation-order reference list without changing the Markdown.

Nothing before the question. No scope note, no assumptions paragraph, no audience statement, no size label, no date line, no "how this was produced" section.

For the journal PDF format, keep this written structure and insert each
rendered figure immediately after the section it supports. Every figure is
referenced from the body and carries a verified, style-matched caption under
`figure-captions.md`; use `media-modes.md` for the wider visual workflow.

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

When the same pattern recurs across several sections — the same trial-versus-cohort gap, the same dose dependence, the same confound — name it once, plainly, where it second appears or in a short closing synthesis section. That cross-cutting claim is usually the most valuable sentence in the review, and it has no home in any single section unless you give it one.

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

A compact block at the end: one line per source, `**All Authors (2026)** Title. *Journal*. DOI link`, alphabetical, with every author named — "et al." never appears in the sources block (it lives only in the in-text tags). This is the only apparatus the review keeps — it is what makes the citations checkable, so it stays even though everything else is trimmed.

## Language

This register applies to the **bullet and scientific styles**. Popsci and ELI5 replace only the register rules, as defined in their own sections; concision, numbers-over-adjectives, calibrated strength, and citations bind every style.

- **Objective scientific register.** The voice of a good journal article, not of science journalism. No rhetorical hooks ("Few claims have travelled further…"), no rhetorical questions, no drama or colour, no appeals to the reader, no first person. State findings and their limits; let the evidence carry the interest.
- **Concise above all.** Cut every word that does not carry information. Prefer the short form: "no benefit" over "did not demonstrate a statistically significant benefit".
- **Numbers, not adjectives.** Effect sizes with intervals, sample sizes, absolute risks. "HbA1c −0.06% (95% CI −0.27 to 0.16)" not "no meaningful improvement".
- **Design in a parenthesis**: "(12-mo RCT, n=137)". It calibrates the reader without a clause.
- **Calibrated strength**, per `evidence-weighing.md` — "probably", "may", "unclear" tied to actual evidence quality. No "proven", no bare "significant".
- **No hedging filler**: drop "it is important to note", "interestingly", "it should be emphasised". But do not confuse filler with synthesis: a sentence that weighs or connects evidence ("Taken together, the effect appears only at high doses"; "This suggests the marker, not the mechanism, was at fault") is content, not filler. Filler tells the reader to pay attention; synthesis tells them what to conclude.
- **Active and direct.** Name who found what.
- Define an abbreviation once, at first use.

## Scientific style (default; alias: prose)

Use this style unless the user explicitly selects bullets, popsci, or ELI5. The pipeline, evidence standard, citations, and verification are identical across styles; scientific and bullets share the normal term-link rules, popsci's gloss-and-link pattern and ELI5's jargon exception are defined below. Scientific style shapes the review into a narrative article of the kind journals publish.

Structure:

```
## <The question>

**Abstract** — <120–250 words, citation-free, plain language, answering the question:
the finding, its size, its certainty, and the main caveat. This replaces the TL;DR.>

### Introduction
<Why the question matters, what is claimed or contested, and the scope — 1–3 paragraphs.
This is the one style where scene-setting is content, not preamble. No methods narration.
End by posing the throughline: the one tension or question the whole review turns on,
and — if it helps the reader — the sub-questions the sections will answer in order.>

### <Short thematic heading, e.g. "Cardiovascular outcomes">
<Paragraphs. See rules below.>

### Conclusion
<Name the cross-cutting pattern plainly — the one claim the sections demonstrated
together — then what the evidence supports at what confidence, and the specific
evidence that would settle what is open. No new evidence introduced here.>

**Sources**
<same generated sources block as always>
```

Narrative arc — what makes the article read as an argument rather than a list:

- **Find the throughline before drafting.** One sentence naming the tension or pattern the whole review turns on ("the biology is solid, but the sleep effect appears only at high doses"). The Introduction poses it, every section advances it, the Conclusion answers it. If no single sentence covers the review, the plan is a taxonomy, not an argument — reorganize until it is one.
- **Land every section.** After the evidence, one plain sentence saying what the section adds to the throughline, ideally handing off to the next section ("So the mechanism is real; whether it costs sleep is a separate question — the one the exposure trials answer next."). A section that stops on its last study is unfinished.
- **Call back across sections.** When a pattern repeats, say so at its second appearance ("the same cohort-versus-trial gap seen for dementia"). One or two callbacks per review are what make it one text rather than stacked summaries.
- **Interpretive sentences are content, not filler.** Roughly one citation-free sentence per paragraph that weighs or connects the evidence ("The mechanism is real, but the marker does not establish sleep loss."). These carry the argument; the banned-filler list bans throat-clearing, not judgment.
- **Vary the rhythm, and keep it easy to read.** Not every sentence is finding + (design, n) + citation — follow a long evidence sentence with a short verdict sentence. Prefer two clear sentences over one packed one; plain words and short sentences outrank density everywhere the numbers allow it.

Paragraph craft:

- **The register is that of a peer-reviewed narrative review** — objective, precise, and plain. Open sections with the finding, not with scene-setting flourishes; the Introduction motivates the question with facts (prevalence, contested claims, stakes), never with journalistic hooks. Calibrated verbs ("reduces", "is associated with", "may"), quantities over adjectives, no metaphors, no first person.
- **The punchline moves from the heading into the topic sentence.** Headings become short thematic labels; every paragraph opens with the claim it defends, then weaves in the evidence — numbers, intervals, designs — with the same `Author 2026` DOI links inline.
- One claim per paragraph, 3–6 sentences. A paragraph that needs eight sentences is two claims.
- Transitions carry the argument between paragraphs and sections ("The picture changes in older adults…"), but every empirical sentence still carries its citation.
- Contrary evidence gets its own paragraphs with explicit contrast ("Against this…", "The null results cluster where…").
- Tables remain allowed and follow the same rules; introduce each one in the running text.
- Figures are introduced from the running prose with the stable token in
  `figure-captions.md`. Their captions are short flowing paragraphs in the same
  narrative-review register, with verified author–year citations.
- The banned-filler list still applies in full. Flowing means flowing, not padded: no "it is important to note", no throat-clearing, no restating the abstract in the conclusion.
- Word budgets run ~1.5× the bullet tiers because connective tissue costs words: small 600–1,000, medium 1,500–2,500, large 3,500–6,000. Sources, angles, and search depth are unchanged from the chosen size.
- Scientific reviews print beautifully — end the delivery by offering the journal-styled PDF (`scripts/export_review.py`), but the review itself still goes in the chat.

## Popsci style (explicit)

Use when the user asks for `popsci`, "popular science", "magazine style", "science journalism", or names a magazine of that register (Scientific American, New Scientist, Quanta, Nautilus). The pipeline, evidence standard, source counts, citations, and verification are identical to every other style — popsci changes the register and the architecture of the telling, nothing underneath. The model is the feature well of a great popular-science magazine: a piece a curious adult reads for pleasure and finishes knowing exactly what science does and does not say — with the one thing no magazine gives them, a checkable citation on every claim.

Structure:

```
## <Headline — the question recast as a magazine title: concrete, curious, honest>

*<Standfirst — 1–3 citation-free sentences under the headline, italic: state the
question plainly and preview the stakes and the shape of the answer. This replaces
the abstract.>*

<The lede: a cold open of 1–2 short paragraphs — a concrete moment from a real
study, a striking verified fact, or the place the question shows up in the
reader's life. Cited like all body text.>

<The nut graf: one paragraph that widens the shot — why the question matters,
what is claimed and contested, and what the piece sets out to find. This is
where the throughline is posed.>

### <Crosshead — a narrative beat, evocative but honest>
<Sections as story beats. See rules below.>

### <The turn — the crosshead that names where the evidence complicates>
<The contrary or null evidence, told as the twist it is.>

### <The kicker>
<Circle back to the opening image, say plainly where the evidence lands and at
what confidence, and end on the specific thing that would settle what is open —
a forward-looking last line, not a shrug.>

**Sources**
<same generated sources block as always>
```

The storytelling — how the magazines actually do it:

- **The headline is honest curiosity.** Recast the question so a browsing reader wants the answer ("Does creatine treat depression?" → "The gym supplement that might lift mood"). It may intrigue; it may not overclaim, tease a payoff the evidence doesn't deliver, or promise certainty the kicker walks back. A null result can still headline — make the absence the story ("The memory pill that never was").
- **Open close, then widen.** The lede is a close-up: one trial's setup, one measured moment, one number that surprises. The nut graf pulls back to the whole literature and poses the throughline. That zoom — close-up on a study, wide shot across the field, back in close — is the piece's basic camera work, and it is what separates a feature from a summary.
- **Studies are events; people do things.** "In 2022, a team at Oxford followed 8,376 teenagers for a year" — findings arrive as moments in an unfolding investigation, with researchers, cohorts, and instruments as the actors. Use only details that are actually in the paper: sample sizes, settings, methods, years, locations. **Never invent colour** — no imagined patients, composite characters, weather, or lab scenes the methods section doesn't contain. A hypothetical is allowed only when explicitly framed as one ("imagine…"), and sparingly; a real study told well beats an invented scene every time.
- **Concrete before abstract.** Show the phenomenon, then name the mechanism. Define terms by apposition in the sentence itself — "the hippocampus, the brain's memory hub" — and still give the term its verified link: **name it, gloss it, link it.** This is the middle path between scientific style (link only) and ELI5 (rewrite entirely); the reader leaves knowing the real vocabulary.
- **Numbers become human-scale, without losing precision.** Lead with what the number means, keep the exact statistic in a parenthesis: "about one extra case for every 900 people vaccinated ([RR](https://en.wikipedia.org/wiki/Relative_risk) 1.13, 95% CI 1.02–1.25)". Prefer absolute risks, frequencies ("one in eight"), and comparisons to familiar magnitudes over bare relative effects.
- **The contrary evidence is the plot twist, not a footnote.** Popular science at its best treats the complication as the most interesting part. Give the turn its own crosshead, let it genuinely threaten the story so far, then resolve it the way the evidence resolves it — including "it doesn't, yet".
- **One metaphor family, carried through.** A single well-chosen image (a thermostat, a relay race, a leaky bucket) may recur and evolve across the piece. Mixed metaphors read as decoration; a sustained one is structure. It must never smuggle in a claim the sources don't make.
- **Rhythm and address.** Sentences vary: a long evidence sentence, then a short verdict. Rhetorical questions and second person are allowed — one or two of each per piece, at genuine hinge points, never as filler. First person plural ("we") only for the shared human situation, never for the analysis.
- **The certainty survives the storytelling.** This is the rule that keeps popsci honest. Hedges stay hedged; a weak finding stays weak no matter how good the sentence feels; "scientists are still arguing about this" is a legitimate story beat, not a flaw to write around. Banned vocabulary: breakthrough, game-changer, revolutionary, holy grail, miracle, stunning, "scientists baffled".
- **Citations unchanged.** Every empirical sentence carries its `Author 2026` DOI link immediately before terminal punctuation, exactly as in every other style. This is the piece's quiet flex — magazine prose that can be checked line by line — so the links are worn lightly but never dropped.
- **Crossheads are evocative but honest.** A reader who skims only the headline and crossheads should come away with the true arc of the evidence, curiosity intact but never misled.
- Tables remain allowed where studies line up; introduce each from the running text. Figure captions follow the popsci register in `figure-captions.md`.
- The banned-filler list still applies: hooks are earned with concreteness, not with "In today's fast-paced world" or "Imagine a world where…" boilerplate.
- Word budgets match the scientific tiers: small 600–1,000, medium 1,500–2,500, large 3,500–6,000. Sources, angles, and search depth are unchanged from the chosen size.
- Popsci prints well too — offer the PDF export after delivering, as with scientific style.

## ELI5 style

In `eli5` mode only. Write a connected explanation in short, flowing paragraphs for a smart reader with no science background at all. The evidence pipeline, citations, and verification are unchanged; only the architecture, language, and jargon treatment change. The model is not a simplified review — it is a great explainer: a patient teacher building a staircase, where every new idea stands only on ideas the reader already has. Do not use list bodies or structured bullet captions unless the user explicitly asks for bullets too; in that case use `bullets` as the structural style for validation and apply this plain-language register to it.

Structure:

```text
## <The question in everyday words>

**TL;DR** — <the answer in 1–3 short, citation-free sentences>

<The starting point: one short paragraph that begins where the reader already
stands — something familiar they have seen, felt, or heard — and turns it into
the question. Cited if it makes an empirical claim.>

### <Step 1 — a plain heading; a simple question is often best>
<Short, connected paragraphs. Each step gives the reader exactly one new idea,
built on the steps before it.>

### <Step 2, and so on — each heading is the reader's own next question>
<…>

### <The "but here's the thing" step>
<The evidence that complicates or disagrees, as its own honest step.>

### <The hand-back>
<Bring the steps together and give the answer back in one or two sentences the
reader could repeat to a friend. Then say, in plain words, what scientists
still need to find out. No new evidence.>

**Sources**
<same generated sources block as always>
```

The story flow — what makes it an explanation rather than a stack of simple facts:

- **Start where the reader stands.** The opening paragraph anchors in something the reader already knows — the sniffle they get every winter, the powder tub at the gym, the label on the bottle — and turns that familiar thing into the question. Not an invented anecdote: an everyday observation or a verified fact, nothing more specific than the sources support.
- **Build a staircase, not a pile.** Order the sections by what the reader needs to understand *next*, not by evidence category or by how a review would organize it. Each section adds exactly one new idea, and uses only ideas from earlier steps. If a sentence needs something not yet explained, the steps are in the wrong order — reorder rather than patch with a forward reference ("more on this later" is a broken staircase).
- **Headings are the reader's own questions.** The best ELI5 headings are the questions a curious reader would actually ask next: "So does it work?", "Why do the studies disagree?", "Is it safe to try?". A reader skimming only the headings should see the path of the explanation. Plain statements are fine too; teaser headings are not.
- **Tell the studies as little stories.** "Scientists gave 100 people the real pill and 100 people a dummy pill, and neither group knew which they got." A study told as a short story explains the method for free — the reader understands *why* the dummy pill matters without ever hearing the word "placebo". Use only real details from the paper: numbers of people, what was given, how long, what was measured.
- **One helper picture, introduced and retired.** A single analogy may be the explanation's backbone ("think of your immune system as a security team"). Introduce it early, reuse it so each step lands somewhere familiar, and retire it honestly when it stops fitting — say where the picture breaks rather than stretching it. It must never smuggle in a claim the sources don't make.
- **Answer the question the reader is holding.** After each step, the natural next question changes. Track it. If step 2 shows the pill works a little, the reader is now wondering "then why doesn't everyone take it?" — that is step 3, whether or not a review would put it there.
- **The turn is a step, not a fine-print paragraph.** The evidence that disagrees gets its own honest step ("But here's the thing — the bigger the study, the smaller the effect"), told with the same patience as the good news.
- **Hand the answer back.** The closing section passes the tell-a-friend test: one or two plain sentences the reader could actually say to someone else tomorrow and be right. Then what scientists still need to find out, in everyday words. If the honest summary is "nobody knows yet", hand back exactly that.

The language — unchanged rules:

- **Everyday words only.** "People in the study" not "participants"; "made-up pill" or "dummy pill" not "placebo"; "the studies disagree" not "heterogeneity". If a ten-year-old wouldn't know the word, don't use it.
- **Short sentences.** One idea per sentence. No semicolons, no nested clauses.
- **Paragraphs must flow.** Put related sentences together and use simple transitions so each section reads as an explanation, not a stack of facts. A paragraph is usually 2–4 sentences. Begin with the point, support it, then say what it means or lead into the next point.
- **Numbers stay, but say what they mean.** Not "SMD −0.34 (95% CI −0.68 to −0.00)" but "the people taking creatine improved a little more — about 2 points on a 52-point mood questionnaire, which is too small a change for most people to feel. And the studies were so different from each other that the real effect could be zero."
- **Jargon is rewritten, not linked.** Term links are for standard modes; here the plain words replace the term entirely. If a term truly cannot be avoided (a scale's name, a drug class), name it once, explain it in the same sentence in plain words, and give it the usual verified term link.
- **Honesty survives the simplification.** "We don't really know yet" instead of silently dropping uncertainty. Small studies are "too small to trust on their own", not omitted. Never round a weak finding up to a strong claim because the plain words feel less precise.
- **Citations unchanged.** Every empirical claim still carries its author–year DOI links. Place links naturally at the end of the sentence or short claim cluster they support, before terminal punctuation; do not collect them in a list-like citation dump.
- **Figure captions stay ELI5 too.** Use a short flowing paragraph of everyday sentences, explain what
  the reader sees and what remains uncertain, and keep the usual verified
  citations. Refer to the picture directly: “You can see the steps in
  `{{figure:mechanism}}`.”
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

Default **small scientific**: aim for something a reader takes in within a few minutes — roughly 600–1,000 words in the body plus the sources block. Popsci uses the same budgets. Explicit bullet style and small ELI5 use 350–700 words, but ELI5 spends that budget on connected paragraphs rather than list items. Medium and large scale up the number of sections and evidence, not sentence density or paragraph length. Sizes are in `sizes.md`.

## Citing

Write the draft with `[@key]` and let `format_references.py --style bracket` render each citation as an `[Author 2026](https://doi.org/…)` link and build the sources block. On the tool-only path, write the `[Author 2026](https://doi.org/…)` links directly, using the DOI from the verified Crossref record, and transcribe the sources block the same way.

Place every citation immediately after the sentence, clause, quotation, figure-caption claim, or table row it supports and before terminal punctuation: `supported claim [Author 2026](DOI).` Never write `supported claim. [Author 2026](DOI)` or make an author–year link the grammatical subject that opens a sentence. `format_references.py --style bracket` normalizes punctuation misplaced before a draft key, and `validate_review.py` rejects misplaced finished links. For journal export, the renderer deliberately moves terminal punctuation before the linked superscript and separately rejects a citation that opens a sentence, paragraph, bullet, or caption. A DOI-only source cell in a comparison table is allowed.

## If verification could not be completed

- A DOI, title, year, or source-type mismatch is a bibliographic failure. Fix or remove that source and any dependent claim before delivering the review. An unverified citation must never reach **Sources**.
- A retraction relation in Crossref's publisher or Retraction Watch update metadata is also a hard failure. Remove the paper as evidence; do not merely decorate it with a warning.
- If Crossref is unavailable, verification is incomplete. Retry reasonably; if it still cannot be completed, omit the affected citations or state plainly that a verified review cannot be delivered yet. Do not publish warning-marked references.
- OpenAlex may be used for discovery, but its availability has no bearing on citation verification and is never mentioned in the finished review.

## Quality gate

0. The review is in the reply, not in a file (unless a file was requested).
1. Every empirical claim carries a citation; in bullet style, every empirical bullet is cited; in ELI5, citations sit naturally beside the sentence or short claim cluster they support. In chat/Markdown, every author–year link precedes terminal punctuation and no sentence begins with a citation.
2. In bullet style, headings alone tell the argument; in scientific, popsci, and ELI5 styles, topic sentences and section landings advance one throughline.
3. The Abstract (scientific), standfirst (popsci), or TL;DR (bullets/ELI5) has no citations; the Abstract and TL;DR answer the question in the first sentence, and the standfirst states the question and the shape of the answer.
4. Opposing evidence appears, and is contrasted rather than blended.
5. A table exists wherever several studies share dimensions.
6. Numbers match sources; intervals included where reported.
7. Nothing before the question; no methods section; no audience or scope preamble. In popsci style, the headline is the question recast and the standfirst states it plainly — nothing precedes the headline.
8. Every cited key passed Crossref bibliographic and publisher/Retraction Watch retraction checks; any failure is excluded.
8b. Every term link points to a confirmed-resolving Wikipedia article, first use only; unconfirmed targets are unlinked and expanded inline.
9. Read it once and cut 10% more.
9b. In scientific style, the review has an arc: the Introduction poses one central tension, every section ends on a plain synthesis sentence rather than its last study, at least one cross-section callback appears, and the Conclusion names the cross-cutting pattern. In bullet style, a recurring cross-section pattern is named once explicitly. In ELI5, the explanation is a staircase: it opens from something the reader already knows, each section adds one new idea built only on earlier steps with no forward references, the contrary evidence gets its own step, the closing hand-back passes the tell-a-friend test, and bullet-list bodies are absent unless the user requested them.
9c. In popsci style: the headline is honest; the lede is a concrete, cited close-up with no invented detail; the nut graf poses the throughline; the turn gets its own crosshead; the kicker circles back and looks forward; no hype vocabulary appears; and every hedge in the sources survives into the piece — the certainty matches the evidence exactly.
10. In the journal PDF format, every required figure is rendered,
    evidence-grounded, legible, and inspected; has a unique stable ID; is
    referenced from the relevant body text; and has a caption in the same
    scientific, popsci, bullet, or ELI5 register with 2–5 verified citations.
10b. Every generated figure passes `qa_figure.py`: exact copy, local
    abbreviation expansions, directed relationships, prohibited effects,
    collisions, and effective PDF label size all match its saved spec and
    inspection. The body introduces the figure before the artwork.
11. When a PDF is requested, inspect every rendered page. No heading may be
    stranded or separated from its first paragraph, table, or figure; no page
    may be an avoidably sparse spill; and no large preventable blank region may
    remain. Rebalance and rebuild without dropping evidence or reducing
    legibility, then repeat the complete raster inspection. Journal citations
    are linked superscript numbers attached to the preceding claim or quotation,
    never the beginning of a sentence, and the numbered References list follows
    first-citation order.
12. Run the finished Markdown through `scripts/validate_review.py` with the
    selected style and size, the ledger, and the full-text manifest. Add
    `--strict-tier` whenever the user explicitly requested a size. Fix every
    hard failure, including mojibake/replacement characters and exposed drafting
    labels, and review every remaining warning; this deterministic gate
    complements rather than replaces checks
    1–11.
