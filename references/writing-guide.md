# Writing guide

The review is delivered **as the chat message itself** — not as a file, attachment, artifact, or canvas. Markdown renders in the conversation; a `.md` file does not preview in most clients and opens in a code editor with the formatting stripped, which makes good work look broken. Write it in the reply.

Create a file only if the user asks, and even then also put the review in the chat. The journal PDF format adds its rendered figures and PDF by design; it does not move the written review out of the chat.

It is not a document with front matter or a report about itself. Every word earns its place.

## Choose the writing style

Use **scientific by default** (the style previously named `prose` — treat `prose` as an alias). Use the compact bullet structure only when the user explicitly asks for bullets, a list, or the compact structured format. Use **popsci** when the user asks for `popsci`, popular science, magazine style, science journalism, or names that register's magazines (Scientific American, New Scientist, Quanta). Use ELI5 only when requested; ELI5 is flowing prose in simpler language, not an implicit request for bullets.

Each style's full structure and craft rules live in its own guide — **read the selected style's file before drafting**:

- `style-scientific.md` — the default narrative journal article.
- `style-popsci.md` — the magazine feature.
- `style-bullets.md` — the compact punchline-and-bullets format.
- `style-eli5.md` — the plain-language staircase explanation.

The register spectrum runs scientific → popsci → ELI5: a journal reader, a curious educated adult, a smart reader with no science background. Bullets share the scientific register in compact form. This file holds everything the styles share: structure invariants, language, term links, length, citing, and the quality gate.

## The synthesis comes first

No styled prose is written until `synthesis.md` — the style-neutral claims ledger specified in `references/synthesis-guide.md` — is complete. Every style is an *arrangement* of that one ledger: a selection and ordering of its claims, retold in the style's register. The claims, their calibrated strength, their contrary evidence, and their boundaries are identical in every rendering; only the telling changes.

Three consequences bind every style:

- **Trace both ways.** Every load-bearing claim in the styled review corresponds to a claim in the synthesis and carries that claim's ledger keys; a claim recorded with contrary evidence brings that contrary evidence along. A synthesis claim cut for size is cut cleanly — its evidence is not cited elsewhere as if the claim were still made.
- **Compose, never paraphrase.** The synthesis is structured fields precisely so the styled text cannot be a light rewording of it. Prose is born in the target register; if a styled sentence reads like a synthesis line with connective tissue, rewrite it.
- **Numbers are rationed, not lost.** Full precision lives in the synthesis's `numbers` fields and the sources. Each style's own budget selects what its prose carries; whatever the prose drops remains recoverable in the synthesis, the parentheses, and the tables.

## Shared structure (every style)

In the chat review and source Markdown, in-text citations render as plain `Author 2026` links immediately after the supported words and before terminal punctuation: `claim [Author 2026](DOI).` The square brackets are markdown link syntax only and must never be visible. If the chat review shows `claim. [Author 2026](DOI)`, a citation-led sentence, a bare `[Author 2026]`, `[1]`, or `(Author, 2026)`, it is wrong. The journal PDF/HTML is the presentation-only exception: `export_review.py` converts those same DOI links to linked superscript numbers after the punctuation and a matching first-citation-order reference list without changing the Markdown.

Nothing before the question. No scope note, no assumptions paragraph, no audience statement, no size label, no date line, no "how this was produced" section.

For the journal PDF format, keep the style's written structure and insert each
rendered figure immediately after the section it supports. Every figure is
referenced from the body and carries a verified, style-matched caption under
`figure-captions.md`; use `media-modes.md` for the wider visual workflow.

### The question

One line. The user's question sharpened, not restated at length. If they asked something conversational, compress it to its scientific core. (Popsci recasts it as an honest headline; ELI5 puts it in everyday words — see the style files.)

### Ordering

Sequence sections so the argument builds. In scientific and bullet styles usually: the direct answer first (strongest, most relevant evidence) → supporting or mechanistic evidence → the contrary case → who it varies for (moderators) → caveats and what would settle it. Popsci orders by its narrative spine and ELI5 by its staircase — see the style files. Never order by date of publication or by how you found things.

When the same pattern recurs across several sections — the same trial-versus-cohort gap, the same dose dependence, the same confound — name it once, plainly, where it second appears or in a short closing synthesis section. That cross-cutting claim is usually the most valuable sentence in the review, and it has no home in any single section unless you give it one.

### Contrast opposing views explicitly

When the literature disagrees, do not average it away. Give the disagreement its own section or paired treatment naming the tension ("Small trials and the large trial disagree — and size explains it"). Then say which side the better evidence favours, or say plainly that it is unresolved.

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

The register bullets below apply to the **bullet and scientific styles**; popsci and ELI5 replace only the register rules, as defined in their own files. Concision, numbers-over-adjectives, calibrated strength, citations, the machinery ban, and the rhythm cap bind **every** style.

- **Objective scientific register** (bullet and scientific styles). The voice of a good journal article, not of science journalism. No rhetorical hooks ("Few claims have travelled further…"), no rhetorical questions, no drama or colour, no appeals to the reader, no first person. State findings and their limits; let the evidence carry the interest.
- **Concise above all.** Cut every word that does not carry information. Prefer the short form: "no benefit" over "did not demonstrate a statistically significant benefit".
- **Numbers, not adjectives.** Effect sizes with intervals, sample sizes, absolute risks. "HbA1c −0.06% (95% CI −0.27 to 0.16)" not "no meaningful improvement".
- **Design in a parenthesis**: "(12-mo RCT, n=137)". It calibrates the reader without a clause.
- **Calibrated strength**, per `evidence-weighing.md` — "probably", "may", "unclear" tied to actual evidence quality. No "proven", no bare "significant".
- **No hedging filler**: drop "it is important to note", "interestingly", "it should be emphasised". But do not confuse filler with synthesis: a sentence that weighs or connects evidence ("Taken together, the effect appears only at high doses"; "This suggests the marker, not the mechanism, was at fault") is content, not filler. Filler tells the reader to pay attention; synthesis tells them what to conclude.
- **Agents act** (every style). The house sentence has a concrete subject doing something: the trial, the drug, the people, the number. "The supportable inference is limited transient efficacy" has a concept as its subject and "is" as its verb; "The trials show a small effect that fades within months" has an agent and a verb. Sentences shaped "The [abstraction] is/remains/offers…" — the reasonable inference, the appropriate conclusion, the operative question — are a rare deliberate move, never the default: a handful per review, not one sentence in twenty. A paragraph in which no concrete noun does anything gets rewritten.
- **Ration the antithesis** (every style). The verdict shape "X, not Y" ("a signal, not proof"; "a hypothesis, not a finding") is the strongest closing move available and the fastest to wear out. At most one per section, never two in a row, and never as the landing of consecutive sections. Land sections in varied shapes instead: on a number, on a consequence, on the answer to the section's question, on a plain declarative.
- **No coinages** (every style). If a compact phrase appears in neither the sources nor a dictionary — "causally underdetermined", "the third evidentiary axis", "a translational bridge" — unpack it into existing words ("the question is too broad to test as one claim"). Invented abstractions read as precision but cost the reader a decoding step, and they are the strongest tell of machine prose.
- **Never name the machinery** (every style). The text's construction stays invisible: no "throughline", "narrative arc", "the turn", "this section shows/adds", "as discussed above", "are summarized in", or any sentence or heading about the review's own structure. Advance the argument; do not mention it. Headings and crossheads are covered too — a crosshead titled "The turn: …" or a section called "Synthesis" is the same failure.
- **The rhythm cap** (every style). Never more than two consecutive sentences in the same *study–verb–finding–citation* shape ("A meta-analysis of X found… A separate synthesis found… Another review found…" is an inventory, not prose): after two evidence sentences, the next sentence weighs, contrasts, or concludes.
- **Active and direct.** Name who found what.
- **Unstack compound modifiers on repeat use.** Hyphenated noun stacks ("slow-release-formulation trials", "recovered-data analyses of older randomized trials") are precise once and exhausting on repetition: after the first use, prefer the unpacked form ("trials of the slow-release formulation", "the recovered trial data") or the short name established at first mention. Never chain three or more hyphenated modifiers before one noun.
- Define an abbreviation once, at first use.

## Term links

The first use of a technical abbreviation or specialist term is a markdown link to its English Wikipedia article — `[SMD](https://en.wikipedia.org/wiki/Standardized_mean_difference)`, `[GRADE](https://en.wikipedia.org/wiki/GRADE_approach)`, `[mRNA](https://en.wikipedia.org/wiki/Messenger_RNA)` — so a non-specialist can click for an explanation without leaving the review.

- **Link what a non-specialist would need explained**, not everyday scientific words: SMD, CI, OR, I², GRADE, HAM-D, PHQ-9, mRNA, phosphocreatine — yes; "placebo", "trial", "dose" — no.
- **First occurrence only**, anywhere in the review (body or table); later occurrences stay plain.
- **Not in the TL;DR** — it is written in plain language and should not need jargon at all.
- **Never link from memory.** Confirm the exact article URL resolves before using it — fetch the page with whatever network access the environment has (the same check as Step 0, or the web-fetch tool on the no-script path). Wikipedia article titles are guessable and often wrong; a link that 404s or lands on the wrong concept is worse than no link. If the target cannot be confirmed, expand the term inline and leave it unlinked.
- **Article pages only, no section anchors** — anchors rot; the article's lead section is usually enough.
- Wikipedia is the linked *explainer*, never a *source*: term links carry no evidential weight and nothing may be cited to them. Citations remain author–year links to DOIs; the two are distinguishable because citations always look like `Author 2026`.
- Style variations: scientific and bullets link only; popsci names, glosses, and links; ELI5 rewrites jargon and links only an unavoidable term after explaining it — see the style files.

## Length

Default **small scientific**: aim for something a reader takes in within a few minutes — roughly 600–1,000 words of running prose plus the sources block (tables, figure captions, and alt text are budgeted separately by the validator). Popsci uses the same budgets. Explicit bullet style and small ELI5 use 350–700 words, but ELI5 spends that budget on connected paragraphs rather than list items. Medium and large scale up the number of sections and evidence, not sentence density or paragraph length. Sizes are in `sizes.md`.

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
2b. The styled review renders `synthesis.md`: every load-bearing claim traces to a synthesis claim and carries its keys, every rendered claim's contrary evidence appears with it, no styled sentence paraphrases a synthesis line, and no cut claim's evidence is cited as if the claim were still made.
3. The Abstract (scientific), standfirst (popsci), or TL;DR (bullets/ELI5) has no citations; the Abstract and TL;DR answer the question in the first sentence, and the standfirst states the question and the shape of the answer. The scientific Abstract follows the four-move shape (verdict, supporting evidence with at least one number, contrary evidence weighed, boundary), states its verdict affirmatively, and never inventories the sections one sentence each. The popsci standfirst sets stakes and shape without compressing the whole arc or giving away the turn.
4. Opposing evidence appears, and is contrasted rather than blended.
5. A table exists wherever several studies share dimensions.
6. Numbers match sources; intervals included where reported. In ELI5, the interval is rendered as a plain-words range, not as digits.
7. Nothing before the question; no methods section; no audience or scope preamble. In popsci style, the headline is the question recast and the standfirst states it plainly — nothing precedes the headline.
8. Every cited key passed Crossref bibliographic and publisher/Retraction Watch retraction checks; any failure is excluded. A recorded correction appears only as the linked "Correction:" note on the original's reference entry — never narrated in the body, never cited in-text, never its own source.
8b. Every term link points to a confirmed-resolving Wikipedia article, first use only; unconfirmed targets are unlinked and expanded inline.
9. Read it once and cut 10% more. In every style: no machinery word or self-labelling heading ("throughline", "narrative arc", "the turn:", "this section") appears in the text, no more than two consecutive same-shape evidence sentences, no sentence chains more than four citations, at most one "X, not Y" verdict per section, no invented abstract coinages, and concrete subjects outnumber abstraction-copula sentences everywhere.
9a. The voice check: read three non-adjacent paragraphs aloud. If they share the same cadence and the same closing move, the piece has one machine voice, not the selected style's voice — vary sentence length and landing shapes before delivery. Each style file defines what its voice should sound like; the styles must not sound like one author at three formality settings.
9b. In scientific style, the review has an arc: the Introduction poses the tension the Conclusion actually answers, every section heading is a calibrated claim sentence with no hand-typed numbering, every section ends on a plain synthesis sentence rather than its last study — and most of those landings hand off to the next section, at least one cross-section callback appears, no caveat is restated in full more than once, and the Conclusion names the cross-cutting pattern without repeating the Abstract. In bullet style, a recurring cross-section pattern is named once explicitly. In ELI5, the explanation is a staircase: it opens from something the reader already knows, each section adds one new idea built only on earlier steps with no forward references and no later step undermining an earlier flat claim, the contrary evidence gets its own step headed by the reader's own doubt, no heading copies a template slot label or stock phrase, a helper picture carries the hardest idea (absent only when no honest analogy exists), returns in at least two later steps, and is retired at the hand-back, each step's prose carries at most one number in reader units (fractions over percentages, intervals as plain-words ranges), studies are told as stories one per paragraph with same-finding studies rolled up within the citation cap, every sentence passes the say-it-aloud test (would you say it to a friend across a table?) with no abstraction ever acting, shared human experience is written to "we"/"you" rather than "people", no bold emphasis appears in the prose, the closing hand-back passes the tell-a-friend test without a "you can tell a friend" label, and bullet-list bodies are absent unless the user requested them.
9c. In popsci style: the piece follows one declared narrative spine — chronology, investigation, or a followed subject — and its crossheads are beats that cannot be reordered without damage; the headline is honest; the lede is a concrete, cited close-up with no invented detail; the nut graf poses the throughline and names the stakes; each section leads with at most one or two human-scale numbers, surplus precision living in parentheses or a table; the narrator reports rather than counsels — experiential and interpretive claims are cited or attributed, guidance is reported, never prescribed; every section has an actor doing the work and the lede and the turn name who, drawn only from the papers' own records — every given name and institution copied verbatim from the ledger via the synthesis's actors field, never recalled or guessed, with surname-only and generic actors as the always-safe defaults; the piece as a whole runs at magazine numeric density (findings beyond the star numbers carried as verbal quantities); shared bodily experience is written to "you" and at least one genuine question lands at a hinge; any quoted words are a source's own written words, under 15 words, verbatim-checkable against the stored evidence, and never presented as speech; every sentence passes the editor test (a magazine editor would not mark it "academese") with no gerund pile-ups or acting abstractions; every linked term is glossed by apposition; the turn gets its own crosshead; the kicker circles back and looks forward; no hype vocabulary appears; and every hedge in the sources survives into the piece — the certainty matches the evidence exactly.
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
