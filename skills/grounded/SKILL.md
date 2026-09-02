---
name: grounded
description: Write a scientific review of a topic or research question — small, medium (default), or large; in scientific, popsci (default), bullets, or ELI5 style; delivered as inline chat, a journal-styled PDF with generated figures (default), or, on explicit request only, an experimental 16:9 slide deck — built solely on peer-reviewed literature found by live search, with every DOI and retraction status verified through Crossref and every cited sentence judged blind against its source's own text and delivered with verbatim quote receipts. Use it for any request for a cited synthesis of the peer-reviewed evidence on a question (literature or narrative review, state of the evidence, research summary, background or related-work section, overview of a field), for an explicit request for a deck, slides, or presentation of the evidence, and for checking the claims and references of a draft the user already has.
---

# Grounded — scientific reviews with no floating claims

The user gives a topic or question and may name a size, style, or output format; you produce a thorough review that looks at the question from every relevant angle and rests entirely on peer-reviewed science, cited correctly. Two disciplines make the whole thing checkable: **no citation is ever recalled from memory** — every source comes from a live index search, every DOI is verified before it is cited, and the reference list is generated from the verified records — and **every cited sentence ships with a receipt**: a verbatim, machine-matched quote from the source, judged by someone other than the writer. A review with one fabricated reference is worth less than no review.

## First: confirm size, style, and output format

A review has three dimensions: **size** (`small`, `medium`, `large`), **style** (`scientific`, `popsci`, `bullets`, `eli5`), and **output format** (`inline chat`, `journal PDF`). Unless the request names all three, ask one short question for whatever is missing before any other work: list the options with the default marked (size: small / medium (default) / large; style: scientific / popsci (default) / bullets / ELI5; format: inline chat / journal PDF (default)). Use an interactive question tool if the host has one; otherwise ask in chat and wait. Ask only for the missing dimensions — what the request names is settled. A request that names all three needs no question. The experimental slides format is not part of the question; an explicit request for a deck settles the format like any other named dimension (see Slides).

If the user answers "you pick" or the session cannot ask, use medium popsci as a journal PDF.

## Checking a draft (the second front door)

When the user hands you text they already have — an LLM answer, a manuscript section, a press release, an essay — and asks to check, verify, or audit its claims or references, skip the size/style/format question and write no review. The draft is the review; the deliverable is a chat-ready check report:

```bash
python3 scripts/check_draft.py ingest --draft draft.md --out-dir check/
python3 scripts/verify_citations.py --ledger check/sources.json
python3 scripts/verify_claims.py extract --review check/draft-normalized.md --ledger check/sources.json --audit check/claims_audit.json
python3 scripts/verify_claims.py fetch   --audit check/claims_audit.json --evidence check/evidence/ --ledger check/sources.json --fulltext-all
python3 scripts/verify_claims.py packets --audit check/claims_audit.json --evidence check/evidence/ --blind
python3 scripts/verify_claims.py adjudicate --audit check/claims_audit.json --packet C001#1 --verdict <verdict> --quote "<verbatim passage>"
python3 scripts/verify_claims.py check   --audit check/claims_audit.json --evidence check/evidence/ --summary check/claims_summary.json
python3 scripts/check_draft.py report --resolution check/resolution.json --ledger check/sources.json --audit check/claims_audit.json --title "<draft title>" --out check/draft-check.md
```

`ingest` reads citations in whatever form they arrive (DOI links, bare DOIs, numeric markers or author–year with a reference list) and resolves each reference to a DOI, searching Crossref when the draft gives none: a reference no index can find is reported as **NOT FOUND**, an in-text citation with no list entry as **UNLISTED**. Verification and the blind claim audit then run exactly as in step 8. A check hides nothing — every verdict is shown, including `not_found` and `contradicted` (`check` exits non-zero on a contradicted pair; in a check that is a finding, not a stop, and the summary is still written) — and the report ends with the citations the author must fix. Deliver the report in chat and keep `check/` as the audit folder. A draft with no citations gets that answer; never invent references for it.

## Output formats

### Inline chat

**Write the finished review directly in your reply.** Do not create `review.md`, attach a file, or put the review in an artifact or canvas: chat clients cannot preview a markdown file, and on the user's machine it opens in a code editor with the formatting stripped. The review is meant to be read in the conversation, where headings, tables, and bold render.

The chat review ends with its **Sources** — each entry stamped with the claims it supports and their evidence tier — and a two-line **Receipts** block carrying the audit tally and the name of the receipts file (`<review>-receipts.md`, written in step 8). That receipts file is the one file an inline-chat review always produces: attach it or name its path, never paste it into the chat.

Working files (`sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `synthesis.md`, `claims_audit.json`, the draft) are audit inputs: keep them if you have a filesystem, never present them as the output, and mention them only if the user wants to audit. Without a filesystem, hold the ledger in context and carry on. Produce other files only when asked ("save it", "give me a .md"), and then still put the review in the chat.

### Journal PDF (default)

Used when the user picks it in the format question or asks for a PDF, a printable or shareable version, or "a journal article". The journal PDF always includes generated figures: choosing the format is what triggers figure creation (step 7). `scripts/export_review.py` renders the single canonical GROUNDED design with pinned WeasyPrint — masthead with the packaged logo, linked "Agentically generated scientific review" descriptor and version on every page; metadata grid with the writing style; numbered sections; two-column Charter body with Helvetica Neue furniture; full-width tables and figures with cited captions; DOI-linked superscript citations and references in first-citation order; clickable figure references; a book-style colophon closing the document with the source count, the DOI-resolution and retraction-screening statement, and the claim-audit tally. The per-pair receipts never enter the PDF; they travel beside it as `<review>-receipts.md`, hashed into the release manifest. A citation that grammatically opens a sentence is a hard export error. Never substitute a browser, ReportLab, or an ad-hoc template.

```bash
python3 scripts/export_review.py --check-pdf-runtime
python3 scripts/export_review.py --in review.md --out review.pdf --pdf --style <scientific|popsci|bullets|eli5> --ledger sources.json --claims-audit claims_audit.json --claim-receipts review-receipts.md --release-manifest release-manifest.json --figure-spec figure.json --figure-prompt figure.prompt.txt --figure-inspection figure.inspection.json --figure-provenance figure.provenance.json
python3 scripts/qa_review_pdf.py review.pdf --manifest release-manifest.json --render-dir review-pdf-qa --report pdf-qa.json
```

The runtime check is a hard gate: if it fails, install the exact packages in `requirements-pdf.txt` and the native Pango runtime (on macOS, the Homebrew WeasyPrint executable), then rerun; never switch renderers. Repeat the four `--figure-*` arguments once per figure. `--claims-audit` is the checked audit from step 8 and `--claim-receipts` the receipts file it produced; the exporter refuses an audit with any pair that is not supported or partial, a review whose Receipts stamp has no matching audit, and any remote, missing, or escaping asset, writes atomically so a failed build cannot replace a good PDF, and refuses a render that is not pinned WeasyPrint with Charter and Helvetica Neue embedded. The QA command is mandatory before delivery: it rehashes every input, rebuilds the HTML, proves figure aspect ratios were preserved, rasterizes every page through Poppler, and records one authoritative render set in the manifest — use a new, case-local `--render-dir` and look at every page and contact sheet yourself. A stranded heading, an avoidably sparse spill page, a stretched figure or font, or a large preventable blank region is release-blocking; rebalance and rebuild without dropping evidence or shrinking type. Editions (the paper identity each style renders in), the pull-quote device, the exporter's automatic spill rebalance, and the layout levers (`--ref-leading`, `--figure-max-height`, `--columns 1`) are specified in `references/quality-gates.md`; QA failure messages name the lever that closes each gap. The review still goes in the chat as well.

### Slides (experimental)

The slides format runs only when the user asks for a **deck**, **slides**, a **presentation**, or a **journal club deck**; it is not offered in the format question, because the deck replaces the written review and a reader who did not ask for that should not get it. Run the complete evidence pipeline through `synthesis.md`, storyboard from those claims per `references/deck-guide.md`, and deliver in chat the sharpened question, a one-to-three-sentence plain answer, and the deck PDF — a full styled review only if the user asks for both. Every content-slide title is a full-sentence cited claim; artwork is created with `render_context: slide` and carries the evidence itself; every slide passes the guide's standalone test (claim, evidence, and firmness readable from that slide alone). Version 1 is 16:9 PDF only, and decks do not yet carry claim receipts — say so in one sentence when delivering one.

```bash
python3 scripts/export_deck.py --check-pdf-runtime
python3 scripts/export_deck.py --storyboard storyboard.json --ledger sources.json --out review-deck.pdf
python3 scripts/qa_deck_pdf.py review-deck.pdf --storyboard storyboard.json --ledger sources.json --render-dir review-deck-qa
```

The exporter enforces the style arc, slide-count limits, verified DOI coverage, 16:9 geometry, data-URI-only assets, atomic writes, canonical fonts, and pinned WeasyPrint; deck QA is mandatory, and you apply the standalone test to every rendered slide. Without a capable image-generation model the deck cannot exist: deliver the synthesis as a normal review and say in one sentence that the deck could not be generated — never fake it with text slides, SVG, or placeholders.

The evidence pipeline, verification, and citation standard are identical in every format.

## Defaults

- **Size: medium. Style: popsci. Format: journal PDF** (`prose` is accepted as an alias for `scientific`; `big` for `large`). Defaults apply only after the question above, when the user says "you pick" or the session cannot ask.
- **Every delivered review carries receipts.** After the figures are placed, run the claim audit (step 8) on the final `review.md` and deliver `<review>-receipts.md` beside the review, with the tally stamped after Sources and in the PDF colophon. A review without receipts is unfinished; only the deck is exempt.
- **Chat citations are `Author 2026` links to the DOI**, placed immediately after the supported claim or quotation and before its sentence-ending punctuation: `claim [Author 2026](DOI).` — never `claim. [Author 2026](DOI)`, never a citation-led sentence, never a bare `[Author 2026]`, `[1]`, or `(Author, 2026)`. The journal renderer alone converts these to linked superscript numbers with a matching numbered reference list.
- **Structure is fixed per style.** Scientific: question → abstract → introduction → claim-headed sections → conclusion → sources. Popsci: headline → standfirst → lede → nut graf → narrative crossheads along one spine with a turn → kicker → sources. Bullets: question → TL;DR → punchline sections of bullets → sources. ELI5: question → TL;DR → familiar starting point → steps that each add one idea, the contrary evidence as its own step → hand-back ending → sources. Shared rules in `references/writing-guide.md`; layouts in `references/style-scientific.md`, `style-popsci.md`, `style-bullets.md`, `style-eli5.md`.
- **Technical terms link to explainers.** The first use of an abbreviation or specialist term links to its verified Wikipedia article (rules in `references/writing-guide.md`).
- **No preamble and no meta.** No scope note, assumptions paragraph, audience statement, size label, or "how this was produced" section; make scope choices silently.
- **Concise throughout.** The shortest language that carries the evidence.

## Sizes and styles

Size is how much evidence; style is how it is written; the two are independent. **Small** when asked for `small` or a compact review; **medium** by default, and when the question plainly contains several distinct sub-questions; **large** when asked for `large` or `big`. **Scientific** on request: a journal-register article. **Popsci** by default, and on "popular science", "magazine style", "science journalism", or a named magazine: a feature told along one narrative spine with a reporter's stance. **Bullets** on request for bullets, a list, or a compact structured format. **ELI5** on request for `eli5` or very simple language: a step-by-step explanation in very simple English, in flowing paragraphs — bullets only if the user also asks for them (then bullets is the structure and ELI5 the register). Style never changes search depth, source counts, citations, or verification; it changes register and jargon treatment (scientific and bullets link terms; popsci names, glosses, and links; ELI5 rewrites jargon and links only an unavoidable term after explaining it).

| | Small | Medium (default) | Large |
|---|---|---|---|
| Scientific/popsci prose length | 600–1,000 words | 1,500–2,500 words | 3,500–6,000 words |
| Bullet / ELI5 prose length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Synthesis claims | 5–12 | 10–25 | 20–45 |
| Searches | 1–2 queries per angle, 3–5 angles | 2–3 per angle, 5–8 angles | 3–5 per angle, 8–12 angles, plus citation chasing |
| Full texts read | the 2–4 load-bearing papers | 8–15 | 25+ |
| Tables | 0–1 | 1–2 | 2–4 |
| Journal-PDF figures | target 2, cap 2 | target 3, cap 5 | target 5, cap 8 |
| Slides: content / total | 4–6 / 6–8 | 8–12 / 10–15 | 14–20 / 18–25 (hard max 25) |

Bigger sizes add sections, evidence, and tables — never longer sentences. The budget binds the running prose alone; table cells, captions, and alt text have their own compact caps in the validator (about 80 words per caption, 40 per alt text, 120 across tables). Full definitions in `references/sizes.md`.

## Step 0: check the network before anything else

Every citation is verified against a live API, so a host that cannot reach them cannot run this skill. Before searching:

```bash
python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.crossref.org/works/10.1136/bmj.n71',timeout=15).status)"
```

`200` → run the pipeline below.

Anything else → **stop and say so.** Report which host is unreachable and that Grounded needs outbound access to `api.crossref.org`, `api.openalex.org`, `eutils.ncbi.nlm.nih.gov`, and `www.ebi.ac.uk`. Browser chat sandboxes (claude.ai, ChatGPT) block these and are not supported; a coding agent with a real shell is. There is no reduced mode: do not substitute a web-search tool, do not cite from memory, and never present an unverified review as verified. Offer an explicitly uncited explainer only if the user asks for one, and label it as carrying no verified sources.

Check this once, before drafting. Discovering it afterwards costs the whole citation apparatus.

## The pipeline

Work through every step in order; each depends on the ledger the earlier ones build. Keep all working files in one folder per review (`<topic-slug>/`): `sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `fulltext-manifest.json`, `synthesis.md`, `review_draft.md`, `review.md`, `evidence/`, `claims_audit.json`, `claims_summary.json`, plus requested media; PDF releases add `release-manifest.json` and one authoritative QA render directory. Machine-auditable contracts: `references/quality-gates.md`.

For **two or more journal reviews in one request**, read `references/production-workflow.md` before step 1: one isolated case folder and `production.json` per review, evidence and semantic gates before media, figure and release gates only after their prerequisites pass. The staged workflow adds coordination and accounting; it weakens no gate below.

### 1. Scope the question into angles

Write down the angles a thorough reviewer would cover before searching. For an empirical question: existing systematic reviews and meta-analyses; the largest or most rigorous primary studies; mechanism or theory; contradictory or null findings; populations, settings, doses, durations; measurement and methodological critiques; harms; the historical origin of the claim; very recent work. Other question types: `references/search-playbook.md`. The angle list goes in `notes.md` and becomes the skeleton of the review.

### 2. Search, angle by angle

Use `scripts/find_papers.py`: it cursor-pages OpenAlex and offset-pages PubMed, writes `search_log.md` and `search-manifest.json`, and merges accepted candidates into `sources.json`. Give every run a stable `--angle-id` and a funnel `--lane`; failed or rate-limited calls stay recorded with `completed: false` and never satisfy coverage. Citation chasing uses OpenAlex first and OpenCitations second. The publication screen is candidate triage, not proof of peer review — confirm ambiguous venues.

Run the reviews lane first, then primary, foundational, recent, and contrary/null. For medium and large reviews, chase central entries in both directions. Before writing, run `scripts/audit_search.py search-manifest.json --size <size>` (large: 8–12 completed angles, 3–5 distinct completed queries per angle, every lane, both directions for 5–10 central papers). Minimums are hard failures; exceeding a maximum warns, and a completed query that accepted nothing never counts toward a maximum. Retire a stray query with `scripts/find_papers.py --supersede-query "<query>" --supersede-reason "..."` rather than editing history. Stop by the coverage rules, not because one page repeats.

### 3. Read

Read every abstract you might cite. Pull load-bearing full texts into `fulltexts/` under their exact ledger keys and record per key — design/sample, result, limitation, synthesis use — in the notes bullet shape shown in `references/quality-gates.md` (`` - `key` — note``). Then run `scripts/audit_fulltexts.py --ledger sources.json --fulltext-dir fulltexts --notes notes.md --out fulltext-manifest.json --minimum <tier-minimum> --update-ledger`: only distinct, authenticated article text with a complete note counts; challenge pages, denials, abstracts, metadata shells, duplicates, and unreadable files do not. No final citation may lack a nontrivial abstract or a valid full text.

### 4. Verify

Run `scripts/verify_citations.py --ledger sources.json`. The Crossref record gives both bibliographic verification (DOI, title, year, article type) and integrity screening: Crossref integrates publisher updates and Retraction Watch records, and the verifier inspects `updated-by` on a flagged original and `update-to` on a notice. A mismatch, an unavailable record, or a retraction, withdrawal, removal, or expression-of-concern signal is a hard failure — fix or remove the source before writing. A corrigendum or erratum does not block; it is saved as `correction_notices` and the reference entry gains a linked "Correction:" note, which is the correction's only appearance (never cited in the body, never listed as a source) — check it does not affect the result you cite. OpenAlex plays no part in verification.

### 5. Distill the synthesis

Before any styled prose, distill the verified evidence into `synthesis.md`, the style-neutral claims ledger specified in `references/synthesis-guide.md` (read it first): a verdict paragraph, the throughline, every load-bearing claim as an atomic calibrated sentence with its strength, exact numbers, supporting keys, contrary evidence, boundary, and dependencies, then cross-claim patterns and open questions. Write it from `sources.json` and `notes.md` only. **Quotes before prose:** every key a claim cites carries a `- quote: [@key] "…"` line copied verbatim from that source's stored text. Seed the evidence store from what you already read and run the gate before a sentence of prose exists:

```bash
python3 scripts/verify_claims.py seed --ledger sources.json --evidence evidence/ --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py synthesis-check --synthesis synthesis.md --ledger sources.json --evidence evidence/ --report synthesis-check.json
```

A claim whose source cannot be quoted is weakened to what the passage says or loses that key; a number in a claim sentence must sit inside one of its quotes; a ledger with no recorded disagreement, or with boundary, numbers, or evidence lines repeated across claims, fails the gate. The synthesis is the single source the styled review, the figures, the deck storyboard, and the claim audit draw from; it is a working file, never delivered or quoted verbatim. If drafting reveals a wrong or missing claim, fix the synthesis first, then the draft.

### 5b. Write the draft

Compose the draft from the synthesis claims — arranged and told in the selected style, never paraphrased line by line — citing with ledger keys before sentence-ending punctuation: `claim [@Kuyken2022effectiveness].`, or `claim [@a; @b].` for several. Follow `references/writing-guide.md` and the selected style file (read it before drafting); the fixed structures are listed under Defaults. In every style: order the argument deliberately, contrast opposing evidence, use a table wherever several studies share dimensions, report numbers with intervals, cite primary studies for findings and reviews for consensus, and cite each source only for the clause its quoted passage states.

### 6. Format and check

Run the formatter through the deterministic writing-contract validator:

```bash
python3 scripts/format_references.py --ledger sources.json --draft review_draft.md --style bracket | python3 scripts/validate_review.py - --style scientific --size small --ledger sources.json --fulltext-manifest fulltext-manifest.json --pass-through --report validation.json
```

Replace the style and size. Add `--strict-tier` when the user named the tier (word, source, section, table, figure ranges and the full-text minimum become hard errors) and `--image-mode` for the journal PDF, whose figures are mandatory. The formatter normalizes `claim. [@key]` to `claim [Author](DOI).`; the validator rejects citations after sentence-ending punctuation or opening a sentence, gates Crossref identity, retraction status, publication eligibility, and reading evidence, and rejects mojibake, scaffold labels, DOI/reference drift, and broken figure placement. Then work through the quality-gate checklist in `references/writing-guide.md`, the manual companion to this gate. Keep the validated author–year markdown as the review source; `export_review.py` performs the presentation-only conversion to superscript numbers for the PDF. Never run `format_references.py --style nature` as a substitute — it would change the chat review and bypass the journal placement gate.

### 7. Create the figures or slides

Skip for inline chat. Journal PDFs require distinct, synthesis-grounded figures: aim for 2 / 3–4 / 5–6 at small / medium / large with hard ceilings of 2 / 5 / 8 — one whole-answer synthesis visual plus whatever mechanism, study-design, quantitative, comparison, or uncertainty views the verified synthesis genuinely earns; fewer is valid only when it holds fewer visual stories, never because producing them is inconvenient. A popsci or ELI5 review may add a sectional cutaway plate under the ceiling when it removes a genuine imagination step, shows hidden structure faithfully, adds distinct information, and stays clear at 390 px (the `cutaway` archetype and its callout contract apply).

Read `references/media-modes.md` for format coverage and embedding, then `references/figure-generation-contract.md` for the communication-first v3 workflow, which owns concept selection, evidence routing, semantic planning, annotations, non-distortion, generation, inspection, and release decisions. Build only from claims and patterns already in `synthesis.md`. Route-specific references: generated or composite art — `references/image-prompt-guide.md`, `references/figure-style-system.md`; inspection and provenance records — `references/figure-inspection-contract.md`; captions and panel cross-references — `references/figure-captions.md`; feedback meant to improve unseen figures — `references/figure-feedback-generalization.md`; slides — `references/deck-guide.md`.

Every new figure uses `quality_contract_version: 3`. Non-quantitative explanations use a capable built-in image generator; verified numbers that carry the message use deterministic plotting, optionally composited with generated text-free anchors. Build prompts with `scripts/build_figure_prompt.py`, inspect the pixels at native and final size, and run:

```bash
python3 scripts/qa_figure.py --spec figure.json --image figure.png --inspection figure.inspection.json --provenance figure.provenance.json
```

A failed meaning, information-flow, anatomy, typography, salience, connector, quantitative, or non-distortion gate means revision and another inspection. Phone QA applies to one to three primary wayfinding labels; keep supporting labels at publication scale and simplify or split a figure rather than enlarging its whole type system. Reject a candidate whose text is poster-like or whose explanation disappears when its labels are mentally hidden. Give each passing figure a stable ID, introduce it before the artwork, refer to its A–D panels in the prose, and end its style-matched caption with verified citations. If capable image generation is unavailable or the visual gates cannot pass, deliver the verified synthesis as a normal review.

### 8. Claim audit and receipts

After the figures are placed — captions are cited sentences too — audit the final `review.md` against the sources' own text and write the receipts, following `references/claim-verification.md`:

```bash
python3 scripts/verify_claims.py extract  --review review.md --ledger sources.json --synthesis synthesis.md --audit claims_audit.json
python3 scripts/verify_claims.py fetch    --audit claims_audit.json --evidence evidence/ --ledger sources.json --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py packets  --audit claims_audit.json --evidence evidence/ --blind
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet C001#1 --verdict supported --quote "<verbatim passage>"
python3 scripts/verify_claims.py check    --audit claims_audit.json --evidence evidence/ --summary claims_summary.json --strict
python3 scripts/verify_claims.py receipts --audit claims_audit.json --review review.md
python3 scripts/validate_review.py review.md --style <style> --size <size> --ledger sources.json --fulltext-manifest fulltext-manifest.json --report validation.json
```

`extract --synthesis` is the trace gate: a source the synthesis never quoted cannot be cited (add the quote and re-run `synthesis-check`, or drop the citation), and each packet leads with the writer's synthesis quotes for that source. `fetch` reuses the seeded store; only sources with no stored text touch the network (`--offline` skips it).

**The writer never judges its own sentences.** A separate judge adjudicates blind from the packets alone — the sentence, the synthesis quotes, the candidate passages; no source identity, no place in the review, no draft. Where the host can spawn a fresh agent, hand it the packets and this rule; in a single-agent host, finish all writing first and adjudicate in a fresh context, never while holding the draft. Before a judge configuration is trusted on a real review, it re-adjudicates `evals/claim-benchmark-creatine.json` blind and `verify_claims.py score --min-agreement 80` passes. The judge records one judgment per packet with `adjudicate --packet`, quoting verbatim from the packet, with a pair-specific note on every `partial` naming the element the quote does not cover and a `--bridge "appetite = hunger"` when a genuine paraphrase shares no word with the sentence; `check` fails an audit whose notes repeat across pairs or whose partials carry no note, and downgrades any quote it cannot string-match or that shares nothing with its claim — accept a downgrade or fix the quote, never argue with it. A sentence with several citations is judged per source for the part that source is cited for; a caption is one claim.

**Only `supported` and `partial` pairs ship.** A `contradicted` verdict means the sentence is wrong: correct it. A `not_found` or `unverifiable` pair is a decorative citation — a real paper attached to a sentence its text does not back: drop the citation, move it to the sentence it does support, or rewrite the sentence to what the source says; then re-extract and re-adjudicate the changed claims. `receipts`, the exporter, and PDF QA all refuse an audit with any other pair. `receipts` writes `<review>-receipts.md` (every cited sentence with its sources, tiers, verdicts, and quotes) and stamps the review — `· 3 claims · full text` on each Sources entry and the two-line Receipts block after Sources; re-run the validator, which checks the stamp and never counts it as prose. Deliver the receipts file beside the review in every format, and state the tier split honestly in the reply: a claim verified only at abstract level is exactly that.

For a draft check, `check_draft.py ingest` supplies the ledger and normalized draft, this step runs unchanged, and `check_draft.py report` renders the result.

## Rules that do not bend

- **Peer-reviewed literature only.** No preprints, blogs, news, or grey literature as evidence. Search eligibility and Crossref type are proxies, not a peer-review registry: check the venue when status is ambiguous, especially conference proceedings and unfamiliar journals. A preprint that is the only source for something important may be mentioned once, labelled "(preprint, not peer reviewed)", never load-bearing. Retracted papers are cited only to say they were retracted.
- **Never claim a check you did not perform.** "Verified" means the DOI resolved in Crossref, title, year, and source type matched, and Crossref's publisher/Retraction Watch update metadata showed no retraction, withdrawal, removal, or expression-of-concern signal; if Crossref is unavailable, the citation does not pass. A receipt's tier is what it says: `full text` only when the quote was matched against version-of-record text.
- **No citation from memory.** A paper you remember is found with the search script and verified, or it does not exist for this review — "classic" papers included.
- **No name from memory.** A person's given name or an institution appears only when copied verbatim from the ledger's author record via the synthesis's `actors` field; surnames from citation tags and generic actors ("researchers", "the trial investigators") are always safe. The validator fails the review on any given-name–surname pair the ledger does not carry.
- **Read before you cite.** Abstract minimum; full text for anything the argument leans on.
- **Represent the whole literature, not the convenient part.** If studies disagree, say so and say why they might; if the best evidence is weak, say so. A review that tells one side is advocacy.
- **Keep the story and the evidence distinct.** Findings are attributed ("the MYRIAD trial found …"), synthesis is signposted ("taken together, …"), speculation is labelled.
- **Never hand back a file instead of an answer.** The review lives in the reply; files are the generated artifacts a format requires, the receipts, or what the user asks for.
- **The sources block and the receipts are the audit trail.** No methods section; resolvable DOIs and verbatim receipts are what make the work checkable. Say nothing else about verification when it completes cleanly, and never decorate the finished review with warning symbols — failures are fixed or removed before writing.
- **Numbers over adjectives.** Effect sizes, intervals, sample sizes, and absolute risks where the sources give them; "significant" alone is not a result.

## Bundled resources

- `scripts/find_papers.py`, `scripts/audit_search.py` — paginated discovery, structured funnel records, publication screening, two-provider citation chasing, tier coverage audit.
- `scripts/fetch_fulltext.py`, `scripts/audit_fulltexts.py` — open-access retrieval with typed authenticity, duplicate, notes, and reading-evidence manifests.
- `scripts/verify_citations.py` — Crossref bibliographic and integrity verification; hard stop on failure.
- `scripts/claim_evidence.py`, `scripts/verify_claims.py`, `scripts/claim_receipts.py`, `scripts/synthesis_quotes.py` — the evidence store (Europe PMC full text → OpenAlex OA locations → abstract floor, fail-closed on challenge pages and binary bodies), the quote-anchored synthesis gate, the seed → extract → fetch → packets → adjudicate → check → receipts audit, and the receipts rendering shared by validator, exporter, and QA.
- `scripts/check_draft.py` — the draft-check front door: citation parsing in any form, Crossref reference resolution, the normalized draft, and the chat report.
- `scripts/format_references.py`, `scripts/validate_review.py` — `[@key]` resolution and reference building; the deterministic structure, tier, citation-placement, reading-evidence, DOI-parity, hygiene, and figure gates.
- `scripts/export_review.py`, `scripts/weasyprint_export.py`, `scripts/qa_review_pdf.py` — canonical atomic PDF/HTML export and the release-lineage, figure-aspect, visible-reference, and Poppler raster QA.
- `scripts/export_deck.py`, `scripts/qa_deck_pdf.py` — verified 16:9 deck export and its fail-closed QA.
- `scripts/build_figure_prompt.py`, `scripts/figure_contract.py`, `scripts/figure_provenance.py`, `scripts/qa_figure.py`, `scripts/quantitative_figure_spec.py`, `scripts/quantitative_drawing.py`, `scripts/render_quantitative_figure.py`, `scripts/qa_quantitative_geometry.py`, `scripts/figure_typography.py`, `scripts/download_figure_references.py` — figure specification, prompt composition, deterministic plotting, and independent pixel and geometry verification.
- `scripts/audit_production.py` — the staged multi-review production gate.
- `scripts/build_release_skill.py`, `VERSION`, `scripts/grounded_metadata.py`, `requirements-pdf.txt` — packaging, shared version and user agent, pinned PDF runtime.
- `evals/claim-benchmark-creatine.json`, `evals/decorative-citations.json` — the judge qualification gold set and the decorative-citation regression set.
- `references/` — `search-playbook.md`, `evidence-weighing.md`, `synthesis-guide.md`, `writing-guide.md` and the four `style-*.md` files, `citation-rules.md`, `claim-verification.md`, `quality-gates.md`, `production-workflow.md`, `sizes.md`, `media-modes.md`, `deck-guide.md`, and the figure contracts (`figure-generation-contract.md`, `figure-inspection-contract.md`, `figure-style-system.md`, `figure-captions.md`, `image-prompt-guide.md`, `figure-reference-analysis.md`, `figure-feedback-generalization.md`, with `figure-style-presets.json`, `figure-archetypes.json`, `figure-writing-style-overlays.json`, `nature-figure-corpus.json`); `contracts.md` is the changelog of invariants and interfaces.
