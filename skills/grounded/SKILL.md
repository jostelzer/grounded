---
name: grounded
description: Write a scientific review of a topic or research question at small, medium (the default), or large size, in scientific style (flowing narrative prose), popsci style (the default; popular-science magazine storytelling), bullets, or ELI5 (very simple flowing prose), delivered as inline chat, a journal-styled PDF (the default, always with generated figures), or — only when the user explicitly asks for it — an experimental verified 16:9 slide deck, built only on peer-reviewed literature found by real searches, with every citation and its retraction status verified through Crossref and every cited sentence audited against its source's own text, delivered with verbatim quote receipts. Use this whenever the user wants a literature review, narrative review, state of the evidence, research summary, background or related-work section, an overview of a scientific field, or explicitly asks for a deck, slides, presentation, slide deck, or journal club deck. Also use it to check a draft's claims or references against the literature.
---

# Grounded — scientific reviews with no floating claims

The user gives a topic or question and may name a size, style, or output format; you produce a clean, thorough review that looks at the question from every relevant angle and tells a story that rests entirely on peer-reviewed science, cited correctly. The central discipline is that **no citation is ever recalled from memory**: every source comes from a live index search, every DOI is verified before it is cited, and the reference list is generated from the verified records. Then every cited sentence is audited against its source's own text and the review ships with **receipts** — one verbatim, machine-matched quote per claim–source pair — so a reader can see not only that a paper exists but that it says what the review says it says. A review with one fabricated reference is worth less than no review.

## First: confirm size, style, and output format

A review has three dimensions: a **size** (`small`, `medium`, `large`), a **style** (`scientific`, `popsci`, `bullets`, `eli5`), and an **output format** (`inline chat`, `journal PDF`, and — hidden by default — the experimental `slides`).

Unless the request names **all three**, your very first action — before any searching, planning, or other work — is to ask one short question for whatever is missing. Do it immediately, within seconds of being invoked, and keep it to a few lines listing the options with the default marked (size: small / medium (default) / large; style: scientific / popsci (default) / bullets / ELI5; format: inline chat / journal PDF (default)). **Do not list slides in the format question**: it is experimental and hidden by default, used only when the user explicitly asks for a deck, slides, or a presentation in their own words — an explicit request settles the format dimension like any other. If the environment has an interactive question tool, use it; otherwise ask in plain chat and wait for the answer. Ask only for the missing dimension(s) — whatever the request already names is settled and is not re-asked. If all three are named, skip the question entirely and start.

If the user answers "you pick", "default", or similar — or the session is non-interactive and cannot ask — use medium popsci as a journal PDF.

## Checking a draft (the second front door)

When the user hands you text they already have — an LLM answer, a manuscript
section, a press release, an essay — and asks to check, verify, fact-check, or
audit its claims or references, **do not ask the size/style/format question**
and do not write a review. The draft is the review; the deliverable is a
chat-ready check report. Run:

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

`ingest` reads citations in whatever form they arrive — DOI links, bare DOIs,
numeric markers with a reference list, author–year with a reference list —
and resolves each reference to a DOI, searching Crossref when the draft gives
none. A reference no index can find is reported as **NOT FOUND**, the first
thing a reader of a fabricated citation needs to know; an in-text citation
with no reference-list entry is **UNLISTED**. Verification and the blind
claim audit then run exactly as for a Grounded review (step 8 rules apply:
judge ≠ writer, verbatim quotes, specific notes). Nothing is repaired and
nothing is hidden — a check shows every verdict, including `not_found` and
`contradicted` (`check` exits non-zero on a contradicted pair; in a draft
check that is a finding, not a stop — the summary is still written) — and the
report ends with the citations the author must fix.
Deliver the report in chat (it is written for that) and keep `check/` as the
audit folder. If the draft has no citations, say so and stop; do not invent
references for it.

## Output formats

There are exactly three output formats. **Journal PDF** is the default; **inline chat** happens when the user chooses it in the original request or as the answer to the format question. **Slides** is experimental and hidden by default: it is never offered in the format question and happens only when the user explicitly asks for a deck, slides, or a presentation themselves. Never infer slides silently.

### Inline chat

**Write the finished review directly in your reply. Do not create `review.md`. Do not attach, upload, or hand back a file. Do not put it in an artifact or canvas.**

This is not a formatting preference — a markdown file is *worse* for the reader: chat clients cannot preview it, and on the user's machine it opens in a code editor with the formatting stripped, which looks broken. The review is meant to be read in the conversation, where the headings, tables and bold actually render.

The chat review ends with its **Sources** — each entry stamped with how many claims it supports and at which evidence tier — and a two-line **Receipts** block carrying the audit tally and the name of the receipts file (`<review>-receipts.md`, written by `verify_claims.py receipts` in step 8: every cited sentence with its source, tier, verdict, and verbatim quote). The receipts file is the one file an inline-chat review always produces; attach it or name its path, and never paste it into the chat.

Working files are different. `sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `synthesis.md`, `claims_audit.json`, and the draft are audit inputs: keep them if you have a filesystem, never present them as the main output, and mention them only if the user might want to audit. If there is no filesystem, hold the ledger in context and carry on.

Produce a file **only** when the user asks for one ("save it", "give me a .md", "export to Word"). Then write the file *and* still put the review in the chat.

### Journal PDF (default)

When the user asks for a **PDF**, a **printable** or **shareable** version, or "make it look like a journal article" — or picks the journal PDF in the format question — use the canonical browser-free PDF path below — and note that **the journal PDF always includes generated figures**. There is no separate image mode: choosing the PDF format is what triggers figure creation. Visual targets/ceilings scale with size (small 2/2, medium 3/5, large 5/8). These are distinct evidence jobs, not quotas: one synthesis visual plus whatever mechanism, study-design, quantitative, comparison, or uncertainty views the verified synthesis genuinely earns. Every figure is built from the verified findings per `references/media-modes.md` and the figure references it names, then embedded in both the review and the PDF. `scripts/export_review.py` turns the finished markdown into the single canonical GROUNDED HTML/CSS design, then renders that exact design with pinned WeasyPrint: Swiss-modern masthead strip with the packaged Grounded logo, a linked "Agentically generated scientific review" descriptor, and the Grounded version on every page; a metadata grid including the selected writing style; numbered sections; two-column Charter body; Helvetica Neue furniture; full-width tables and figures; cited captions; DOI-linked superscript citation numbers; numbered references in first-citation order; clickable figure references; quiet page feet (hairline and folio only); and a book-style verification colophon closing the document — the review's source count, DOI-resolution and retraction-screening statement, the claim-audit line (cited sentences, source checks, verdicts by evidence tier), version, and compile date. The per-pair receipts never enter the PDF: they are delivered beside it as `<review>-receipts.md`, hashed into the release manifest. Journal citations attach to the preceding supported claim or quotation; a citation that grammatically opens a sentence is a hard export error. Do not invoke Chrome, another browser, ReportLab, or an ad-hoc external template as a fallback.

```bash
python3 scripts/export_review.py --check-pdf-runtime
python3 scripts/export_review.py --in review.md --out review.pdf --pdf --style <scientific|popsci|bullets|eli5> --ledger sources.json --claims-audit claims_audit.json --claim-receipts review-receipts.md --release-manifest release-manifest.json --figure-spec figure.json --figure-prompt figure.prompt.txt --figure-inspection figure.inspection.json --figure-provenance figure.provenance.json
python3 scripts/qa_review_pdf.py review.pdf --manifest release-manifest.json --render-dir review-pdf-qa --report pdf-qa.json
```

The runtime check is a hard gate. `--claims-audit` is the checked audit from step 8 and `--claim-receipts` the receipts file it produced: the exporter refuses an audit with any pair that is not supported or partial, refuses a review whose Receipts stamp has no matching audit, and hashes both files into the release manifest. If it fails, install the exact packages in `requirements-pdf.txt` and the native Pango runtime required by WeasyPrint, then rerun it; never silently switch renderers. On macOS, use the matching Homebrew WeasyPrint executable so Pango is self-contained. The exporter embeds every figure as a data URI and permits the renderer to load only `data:` resources: remote, missing, and escaping assets are hard failures, while PNG/JPEG/WebP and SVG are supported directly. Output is written atomically: a failed build cannot overwrite an existing good PDF. After rendering, the exporter strictly parses the artifact and refuses to replace the prior PDF unless the producer is pinned WeasyPrint and the embedded fonts include Charter and Helvetica Neue; a fallback-font redesign is a hard failure. HTML sidecars are off by default and require `--html-sidecar` explicitly.

**Editions.** The PDF's paper identity follows the writing style: scientific renders in the canonical **journal** edition (Charter/Helvetica Neue), bullets renders in the **brief** edition — the condensed two-column brief: tight 8.8pt columns, punchline headings, and a drawn double-chevron marker on every finding — ELI5 renders in the **primer** edition — a friendly explainer page: Seravek humanist sans, orange step badges numbering the staircase, and the TL;DR as a tinted answer card, set — like every other edition — in the two-column measure that lets a phone zoom one column to full screen width — while popsci renders in the **salon** edition — Didot display, Hoefler Text body, Optima furniture, generous margins, an automatic three-line drop cap on the opener, and an asterism closing the article. `--edition journal|salon` overrides the default. Editions restyle the same semantic document; the evidence contract, citation placement, reference order, and every QA gate are identical, and the release manifest records the edition so QA rebuilds and verifies the exact design. For salon PDFs you may set one pull quote with `--pull-quote "<sentence>"`: it must be a verbatim passage of the article body (a non-verbatim quote is a hard export error), it is placed before the paragraph it comes from, and when the pulled sentence carries citations they render as a linked attribution line under the quote — an uncited authorial line gets no attribution rather than a misattributed one.

The QA command is also mandatory before delivery. Its release manifest hashes the exact review, ledger, generated HTML, PDF, and every figure/spec/prompt/inspection/provenance record. QA rehashes them, independently rebuilds the HTML, requires one canonical PDF, a visible terminal References heading, every expected DOI as both visible reference text and a URI annotation, the visible colophon audit line whenever the manifest records an audit, canonical A4 metadata/fonts, and running furniture; it also proves that every raster figure's intrinsic aspect ratio is preserved by its PDF transformation matrix, then rasterizes every page through Poppler and checks masthead, page number, body, clipping, column balance, and sparse terminal reference pages. Use a new or empty case-local `--render-dir` and inspect every generated page and contact sheet visually; the manifest records that one authoritative render set. A heading stranded at the bottom while its first paragraph/table/figure starts on the next page, an avoidably sparse spill page, a stretched figure or font, or a large preventable blank region is release-blocking. Rebalance and rebuild without dropping evidence or shrinking type. The exporter prevents the smallest failure itself: when a final page would carry only the tail of the reference list or the closing colophon, it walks a bounded rebalance ladder — reference leading tightened inside its envelope (type size untouched), then the colophon folded into the References heading at zero height, then both — and keeps the first render with no degenerate spill, noting the adjustment in the release manifest. `--ref-leading` sets that leading manually, `--figure-max-height` (60–120 mm) adjusts the figure cap, and `--columns 1` gives a single-column layout; QA failure messages state how far a sparse page is from its threshold and which lever closes it. For image PDFs, repeat all four `--figure-*` arguments once per figure. Full commands and contracts are in `references/quality-gates.md`. The review still goes in the chat as well.

### Slides (experimental — explicit request only)

The slides format is experimental and never offered: it does not appear in the
format question and is never suggested. It runs only when the user asks for a
**deck**, **slides**, a **presentation**, a **slide deck**, or a **journal club
deck** in their own words. Then **the deck is the deliverable**: run
the complete evidence pipeline through the `synthesis.md` claims ledger
(`references/synthesis-guide.md`), storyboard from those claims, and deliver in
chat the sharpened question, a 1–3 sentence plain answer,
and the deck PDF — not a full styled review, unless the user explicitly asks
for both. Never infer the slides format silently. Read `references/deck-guide.md` before
storyboarding. Turn the verified synthesis into the selected style's
size-appropriate arc, make every content-slide title a full-sentence cited
claim, and create artwork with `render_context: slide` that carries the
evidence itself — every slide must pass the guide's standalone test: claim,
evidence, and firmness readable from that slide alone, with no presenter and no
written review to lean on. Version 1 is 16:9 PDF only, and decks do not yet
carry claim receipts — say so in one sentence when delivering a deck.

```bash
python3 scripts/export_deck.py --check-pdf-runtime
python3 scripts/export_deck.py --storyboard storyboard.json --ledger sources.json --out review-deck.pdf
python3 scripts/qa_deck_pdf.py review-deck.pdf --storyboard storyboard.json --ledger sources.json --render-dir review-deck-qa
```

The exporter enforces the style arc, slide-count limits, verified DOI coverage,
16:9 image geometry, data-URI-only assets, atomic writes, canonical fonts, and
pinned WeasyPrint. Deck QA is mandatory: inspect every generated slide and
contact sheet after the structural and Poppler gates pass, and apply the
standalone test to each rendered content slide. If no capable image-generation
model is available, the deck cannot exist — fall back to delivering the
internal synthesis as a normal full review and state in one sentence that the
deck could not be generated; do not fake it with text slides, SVG, or
placeholders.

To summarize the three formats: **inline chat** delivers the review in the
reply; **journal PDF** delivers the PDF (with its automatic figures) and still
puts the review in the chat; **slides** (experimental, explicit request only)
replaces the delivered written review
with the deck (chat carries the question, a 1–3 sentence plain answer, and the
PDF). There is no image mode and no mindmap mode. The evidence pipeline,
verification, and citation standard never change in any format.

## Defaults

- **Size: medium. Style: popsci. Format: journal PDF** (`scientific` was formerly named `prose`; treat `prose` as an alias) — but these apply only after the "First: confirm size, style, and output format" question above: the defaults are for when the user answers "you pick" or the session cannot ask, never a reason to skip the question.
- **Inline chat means chat only** — delivered in the chat, formatted with markdown, as well-presented as possible. No file, no attachment, unless the user chose the journal PDF or slides.
- **Every delivered review carries receipts.** After the figures are placed, run the claim audit (step 8) on the final `review.md`; deliver `<review>-receipts.md` beside the review (chat or PDF), with the tally stamped after Sources and in the PDF colophon. A review without receipts is unfinished; only the experimental deck is exempt.
- **Chat/markdown citations: `Author 2026` inline, hyperlinked to the DOI.** Put the link immediately after the supported claim or quotation and before its sentence-ending punctuation: `claim [Author 2026](DOI).`, never `claim. [Author 2026](DOI)` and never a citation-led sentence. The reader must never see square brackets around a citation — they exist only as markdown link syntax. Never write a bare `[Author 2026]`, `[1]`, or `(Author, 2026)` in the chat review. The Sources block at the end carries the DOIs. The journal PDF/HTML renderer is the deliberate exception: it replaces those author–year labels only in the journal artifact with linked superscript numbers and a matching numbered reference list.
- **Structure is fixed per style** — scientific: question → abstract → introduction → claim-headed sections → conclusion → sources; popsci: headline → standfirst → lede → nut graf → narrative crossheads along one spine with a turn → kicker → sources; bullets: question → TL;DR → punchline sections of bullets → sources; ELI5: question → TL;DR → familiar starting point → step-by-step sections that each add one idea, with the contrary evidence as its own step → a hand-back ending → sources. Shared rules in `references/writing-guide.md`; exact layouts in the per-style files it names (`references/style-scientific.md`, `style-popsci.md`, `style-bullets.md`, `style-eli5.md`).
- **Technical terms link to explainers.** The first use of an abbreviation or specialist term (SMD, CI, GRADE, HAM-D, mRNA, …) is a link to its verified Wikipedia article, so a non-specialist can click instead of googling. Rules and verification in `references/writing-guide.md`.
- **No preamble and no meta.** No scope note, assumptions paragraph, audience statement, size label, or "how this review was produced" section. Make sensible scope choices silently.
- **Concise throughout.** Shortest language that carries the evidence.

## Sizes and styles

A review has a **size** (how much evidence) and a **style** (how it is written). The two are independent; any size combines with any style.

**Size** — default **medium**:

- **Small** — when the user asks for `small` or wants a compact review.
- **Medium** — default. Use when the user leaves the choice to you after the size/style question, or when the question plainly contains several genuinely distinct sub-questions that cannot be answered well at small depth.
- **Large** — when the user asks for `large` or `big`; the words are aliases.

**Style** — default **popsci**:

- **Scientific** — when the user asks for `scientific` (alias: `prose`, its former name). A narrative article in journal register: abstract, introduction, claim-headed topic-sentence sections, conclusion. Word budgets ~1.5× the bullet tier. Rules in `references/style-scientific.md`.
- **Popsci** — default. Also use when the user asks for `popsci`, "popular science", "magazine style", "science journalism", or names Scientific American, New Scientist, Quanta, or a similar magazine. A magazine feature for a curious educated adult, told along one narrative spine: honest headline, standfirst, concrete cited lede, nut graf, narrative crossheads with the contrary evidence as the turn, kicker — with full verified citations throughout. Rules in `references/style-popsci.md`.
- **Bullets** — when the user asks for `bullets`, a list, or the compact structured format. Punchline headings and cited bullet bodies, per `references/style-bullets.md`.
- **ELI5** — when the user asks for `eli5`, "explain like I'm five", or very simple language. A patient step-by-step explanation in very simple English: it starts from something the reader already knows and climbs one idea at a time to the answer, per `references/style-eli5.md`; do not turn it into a bullet list unless the user also explicitly asks for bullets. When both are requested, use `bullets` as the structural style and ELI5 as its language register.

Style never changes search depth, source counts, citations, or verification. Scientific and bullets use the normal verified term links; popsci names a term, glosses it inline, and links it; ELI5 rewrites jargon into everyday language and links only an unavoidable term after explaining it. The register spectrum runs scientific → popsci → ELI5.

**Output formats** — how the review is delivered, independent of size and style:

- **Inline chat** — when the user explicitly chooses it. The review is the reply itself, ending with its Sources and Receipts; nothing extra is generated.
- **Journal PDF** — the default, and also used when the user asks for a PDF, a printable/shareable version, or a journal-styled artifact, or picks it in the format question. It **always includes generated figures**. Plan toward 2 figures for small, 3–4 for medium, and 5–6 for large, with hard ceilings of 2/5/8; fewer is valid only when the synthesis has fewer distinct visual stories, never because producing the visuals is inconvenient. Run the review pipeline at the chosen size, then create the figures from the verified findings per `references/media-modes.md`. For figure generation, also read `references/figure-generation-contract.md`, `references/figure-reference-analysis.md`, `references/figure-style-system.md`, `references/image-prompt-guide.md`, and `references/figure-captions.md`; build the prompt from a structured figure specification with `scripts/build_figure_prompt.py`. Place each figure after the section it supports, reference it from the body, and give it a style-matched caption with verified citations. Figures flow into the PDF export automatically.
- **Optional popsci/ELI5 cutaway** — after the normal visual jobs are planned,
  test whether a sectional “look inside” plate removes a genuine imagination
  step, can show the hidden structure faithfully, adds distinct information,
  and remains clear at 390 px. It may use an available figure slot under the
  size ceiling; omit it when any gate fails. Follow the `cutaway` archetype and
  its one-to-one explanatory-callout contract rather than treating cutaway as a
  decorative style.
- **Slides** — experimental and hidden by default: never offered in the format question, never suggested, and never inferred. Runs only on the explicit triggers `deck`, `slides`, “presentation”, “slide deck”, or “journal club deck” in the user's own words. Combines freely with every size and style. The deck is the deliverable: chat carries the question, a 1–3 sentence plain answer, and the verified 16:9 PDF; the written synthesis stays an internal working draft. Every content slide must pass the standalone test — claim, evidence, and firmness readable from the slide alone. Follow `references/deck-guide.md`; generate one slide-context evidence image per content slide, then run the canonical exporter and mandatory landscape QA.

Figure and slide creation happens only after the evidence has been searched, read, verified, and synthesized.

| | Small | Medium (default) | Large |
|---|---|---|---|
| Scientific/popsci prose length (default) | 600–1,000 words | 1,500–2,500 words | 3,500–6,000 words |
| Bullet prose length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| ELI5 narrative prose length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Synthesis claims | 5–12 | 10–25 | 20–45 |
| Searches | 1–2 queries per angle, 3–5 angles | 2–3 per angle, 5–8 angles | 3–5 per angle, 8–12 angles, plus citation chasing |
| Full texts read | The 2–4 load-bearing papers | 8–15 | 25+ |
| Tables | 0–1 | 1–2 | 2–4 |
| Journal-PDF figures | target 2, cap 2 | target 3, cap 5 | target 5, cap 8 |
| Slides: content slides | 4–6 | 8–12 | 14–20 |
| Slides: total | 6–8 | 10–15 | 18–25 (hard max 25) |

Bigger sizes add sections, evidence, and tables — never longer sentences. Style changes the prose budget shown above; search depth and evidence requirements stay unchanged. The budget binds the running prose alone: table cells, figure captions, and alt text are counted separately by the validator with their own compact caps (about 80 words per caption, 40 per alt text, 120 across tables), so mandatory apparatus never forces prose cuts.

Full tier and style definitions are in `references/sizes.md`.

## Step 0: check whether the scripts can reach the network

Some environments (claude.ai among them) sandbox Python without outbound network access. Run this **before searching**:

```bash
python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.crossref.org/works/10.1136/bmj.n71',timeout=15).status)"
```

`200` → use the scripts below. Anything else → the scripts cannot run here; switch to `references/no-script-fallback.md`, which does every step through the web-fetch tool against the same APIs (this works on claude.ai). The verification standard does not change between paths — only the mechanism. If neither path works, say so and do not present an unverified review as a verified one.

## The pipeline

Work through every step; the order matters because the later steps depend on the ledger built in the early ones. Keep all working files in one folder for the review (`<topic-slug>/`): `sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `fulltext-manifest.json`, `synthesis.md`, `review_draft.md`, `review.md`, `evidence/`, `claims_audit.json`, and `claims_summary.json`, plus requested media. PDF releases add `release-manifest.json` and one authoritative QA render directory. See `references/quality-gates.md` for the machine-auditable contracts.

When one request asks for **two or more journal reviews**, read
`references/production-workflow.md` before Step 1. Use one isolated case folder
and `production.json` per review, run the evidence and semantic gates before
media, and run the figure and release gates only after their prerequisites pass.
The staged workflow owns batch coordination, prompt packets, effort
stratification, warning adjudication, bounded repair accounting, and exact-width
figure-to-release matching; it does not weaken any gate below.

### 1. Scope the question into angles

Before searching, write down the angles a thorough reviewer would cover — this is what "looking at all angles" means in practice. Typical angles for an empirical question: existing systematic reviews and meta-analyses; the largest or most rigorous primary studies; mechanism or theory; contradictory or null findings; different populations, settings, doses, or durations; measurement and methodological critiques; harms or unintended effects; historical origin of the claim; very recent work. For other question types see `references/search-playbook.md`. Write the angle list into `notes.md`; it becomes the skeleton of the review.

### 2. Search, angle by angle

Use `scripts/find_papers.py`. It cursor-pages through OpenAlex and offset-pages through PubMed, writes both `search_log.md` and structured `search-manifest.json`, and merges accepted candidates into `sources.json`. Give every run a stable `--angle-id` and funnel `--lane`. Failed or rate-limited calls remain recorded with `completed: false` and never satisfy coverage. Citation chasing uses OpenAlex first and OpenCitations as the default second provider. The strict publication screen remains candidate triage, **not proof of peer review**; confirm ambiguous venues.

Run reviews-first, then primary, foundational, recent, and contrary/null lanes. For medium and large reviews, chase central entries in both directions. Run `scripts/audit_search.py search-manifest.json --size <size>` before writing; large means 8–12 completed angles, 3–5 distinct completed queries per angle, every funnel lane, and both directions for 5–10 central papers. Minimums are hard failures; exceeding a maximum only warns, and a completed query that accepted nothing never counts toward a maximum. To retire a stray query without rewriting history, run `scripts/find_papers.py --supersede-query "<query>" --supersede-reason "..."` (optionally with `--angle-id`). Stop by the coverage rules, not because one page repeats.

### 3. Read

Read every abstract you might cite. Pull load-bearing full texts into `fulltexts/` under their exact ledger keys and record, per key, design/sample, result, limitation, and synthesis use, using the notes bullet shape shown in `references/quality-gates.md` (`` - `key` — note``). Then run `scripts/audit_fulltexts.py --ledger sources.json --fulltext-dir fulltexts --notes notes.md --out fulltext-manifest.json --minimum <tier-minimum> --update-ledger`. Only distinct authenticated article text with a complete note counts; challenge pages, denials, abstracts, metadata shells, duplicates, and unreadable files do not. No final citation may lack a nontrivial abstract or valid full text.

### 4. Verify

Run `scripts/verify_citations.py --ledger sources.json`. It uses the Crossref record for both bibliographic verification (DOI, title, year, and article type) and integrity screening. Crossref integrates publisher updates and Retraction Watch records; the verifier inspects both `updated-by` on a flagged original and `update-to` on a notice. A mismatch, unavailable Crossref record, retraction, withdrawal, removal, or expression-of-concern signal is a hard failure and the source is removed or fixed before writing. A corrigendum/erratum does not block; it is saved as `correction_notices` and the reference entry gains a linked "Correction:" note — check the correction does not affect the result you cite. That note is the correction's only appearance: the notice is never cited in the body, never narrated in the running text, and never listed as its own source. OpenAlex is not part of citation verification.

### 5. Distill the synthesis

Before any styled prose, distill the verified evidence into `synthesis.md` — the style-neutral claims ledger specified in `references/synthesis-guide.md` (read it first): a verdict paragraph, the throughline, every load-bearing claim as an atomic calibrated sentence with its strength, exact numbers, supporting keys, contrary evidence, boundary, and dependencies, then the cross-claim patterns and open questions. Write it from `sources.json` and `notes.md` only. **Quotes before prose:** every key a claim cites carries a `- quote: [@key] "…"` line copied verbatim from that source's stored text; seed the evidence store from what you already read and run the gate before a sentence of prose exists:

```bash
python3 scripts/verify_claims.py seed --ledger sources.json --evidence evidence/ --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py synthesis-check --synthesis synthesis.md --ledger sources.json --evidence evidence/ --report synthesis-check.json
```

A claim whose source cannot be quoted is weakened to what the passage says or loses that key; a number in a claim sentence must sit inside one of its quotes. The synthesis is the single source that the styled review, the figures, the deck storyboard, and the claim audit all draw from; it is a working file, never delivered and never quoted verbatim. If drafting later reveals a wrong or missing claim, fix the synthesis first, then the draft.

### 5b. Write the draft

Compose the draft **from the synthesis claims** — arranged and told in the selected style, never paraphrased line by line — citing with ledger keys: `claim [@Kuyken2022effectiveness].`, or `claim [@a; @b].` for several. The citation key precedes sentence-ending punctuation; never write `claim. [@key]`. Follow the shared rules in `references/writing-guide.md` and the selected style's fixed layout in its own file (`references/style-scientific.md`, `style-popsci.md`, `style-bullets.md`, `style-eli5.md`) — read the style file before drafting. Scientific reviews use a citation-free four-move Abstract, an Introduction that poses one throughline, claim-headed sections of topic-sentence paragraphs that advance it, and a Conclusion that names the cross-cutting pattern. The default popsci review uses a magazine feature architecture told along one narrative spine — honest headline, citation-free standfirst, concrete cited lede, nut graf, narrative crossheads with the contrary evidence as the turn, and a kicker — with a reporter's stance and a per-section numbers budget, per `references/style-popsci.md`. Explicit bullet style uses a citation-free TL;DR, punchline headings, and cited bullet bodies. ELI5 uses a citation-free TL;DR, then climbs a staircase: a familiar starting point, step-by-step sections that each add one idea built only on earlier steps (headings are often the reader's own next question), the contrary evidence as its own step, and a hand-back ending the reader could repeat to a friend; bullet bodies are wrong unless the user explicitly requested bullets too. In every style, order the argument deliberately, contrast opposing evidence, use a table wherever several studies share dimensions, report numbers with intervals, cite primary studies for findings, and use reviews for consensus.

### 6. Format and check

Run the formatter through the deterministic writing-contract validator:

```bash
python3 scripts/format_references.py --ledger sources.json --draft review_draft.md --style bracket | python3 scripts/validate_review.py - --style scientific --size small --ledger sources.json --fulltext-manifest fulltext-manifest.json --pass-through --report validation.json
```

Replace the style and size. When the user explicitly named the tier, add `--strict-tier`; add `--image-mode` when the journal PDF format was requested, since its figures are mandatory. Strict mode hard-checks word/source/section/table/figure ranges and the full-text minimum. The formatter normalizes a legacy `claim. [@key]` draft to `claim [Author](DOI).`; the validator rejects finished citations that follow sentence-ending punctuation or open a sentence. It separately gates Crossref identity, retraction status, publication eligibility, and reading evidence, and rejects mojibake, scaffold labels, DOI/reference drift, and broken figure placement/citations. Reviews using the default medium tier keep tier ranges advisory unless the user explicitly named `medium`. Then work through the Quality gate checklist in `references/writing-guide.md` (the manual companion to this deterministic gate). The validated text is delivered only after step 8 has attached its receipts.

Keep the validated author–year markdown as the review source: chat punctuation follows the citation link. If journal PDF/HTML is requested, `export_review.py` performs the presentation-only conversion to DOI-linked superscript numbers, moves the punctuation before those raised numbers, orders the References section by first citation, closes whitespace so each number sits directly after its supported claim or quotation, and rejects sentence-initial citations. Do not run `format_references.py --style nature` as a substitute: that would also change the chat review and bypass the journal placement gate.

### 7. Create the figures or slides

Skip this step for inline chat. Journal PDFs require distinct synthesis-grounded
figures: aim for 2/3–4/5–6 at small/medium/large, with hard ceilings of 2/5/8;
use fewer only when the synthesis contains fewer visual stories. Slides follow
the same evidence boundary.

Before producing pixels, read `references/media-modes.md` for format coverage
and embedding, then `references/figure-generation-contract.md` for the
communication-first v3 workflow. That workflow owns concept selection, evidence
routing, semantic planning, annotations, non-distortion, generation, inspection,
and release decisions; do not duplicate or improvise a parallel recipe here.
Build only from claims and patterns already recorded in `synthesis.md`.

Use the route-specific references only when relevant:

- generated or composite art: `references/image-prompt-guide.md` and
  `references/figure-style-system.md`;
- inspection/provenance records:
  `references/figure-inspection-contract.md`;
- captions and panel cross-references: `references/figure-captions.md`;
- feedback intended to improve unseen figures:
  `references/figure-feedback-generalization.md`;
- slides: `references/deck-guide.md`.

Every new figure uses `quality_contract_version: 3`. Non-quantitative
explanations use a capable built-in image generator; verified numbers that carry
the message use deterministic plotting, optionally with generated text-free
orientation anchors in a composite. Build prompts from the selected structured
specification with `scripts/build_figure_prompt.py`, then inspect the actual
pixels at native and final size and run:

```bash
python3 scripts/qa_figure.py --spec figure.json --image figure.png --inspection figure.inspection.json --provenance figure.provenance.json
```

A failed meaning, information-flow, anatomy, typography, salience, connector,
quantitative, or non-distortion gate requires revision and another inspection.
Phone QA applies only to one to three primary wayfinding labels; keep supporting
labels at publication scale and simplify or split a figure instead of enlarging
its entire type system. Reject any candidate whose robust upper text scale or
text area is poster-like, or whose explanation disappears when labels are
mentally hidden.
Give each passing figure a stable ID, introduce it before the artwork, refer to
relevant A–D panels in the prose, and end its style-matched caption with verified
citations. For slides, build and inspect the deck under `references/deck-guide.md`;
if capable image generation is unavailable or the visual gates cannot pass,
deliver the verified synthesis as a normal review instead.

### 8. Claim audit and receipts (mandatory)

After the figures are placed — their captions are cited sentences too — audit
the final `review.md` against the sources' own text and write the receipts.
Follow the rubric in `references/claim-verification.md`:

```bash
python3 scripts/verify_claims.py extract  --review review.md --ledger sources.json --synthesis synthesis.md --audit claims_audit.json
python3 scripts/verify_claims.py fetch    --audit claims_audit.json --evidence evidence/ --ledger sources.json --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py packets  --audit claims_audit.json --evidence evidence/ --blind
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet C001#1 --verdict supported --quote "<verbatim passage>"
python3 scripts/verify_claims.py check    --audit claims_audit.json --evidence evidence/ --summary claims_summary.json --strict
python3 scripts/verify_claims.py receipts --audit claims_audit.json --review review.md
python3 scripts/validate_review.py review.md --style <style> --size <size> --ledger sources.json --fulltext-manifest fulltext-manifest.json --report validation.json
```

`extract --synthesis` is the trace gate: a source the synthesis never quoted
cannot be cited (add the quote to `synthesis.md` and re-run `synthesis-check`,
or drop the citation), and each packet carries the writer's synthesis quotes
for that source as its first candidates. `fetch` reuses the seeded store; only
sources with no stored text touch the network (`--offline` skips it).

**The writer never judges its own sentences.** Adjudication is done blind by a
separate judge that sees only the packets (`--blind`: the sentence, the
synthesis quotes, the candidate passages — no source identity, no place in the
review, no synthesis, no draft). Where the host can spawn a fresh agent, hand
it the packets and this rule; in a single-agent host, finish all writing first,
then adjudicate in a fresh context as the judge, never while holding the draft.
The judge records each judgment with `adjudicate --packet`, one pair at a time,
with the quote copied verbatim from the packet; it never generates verdicts
with a script, a similarity score, a "conservative default", or a template
note — `check` fails an audit whose notes repeat across pairs or whose
`partial` verdicts carry no note naming the missing element. Before a judge
configuration is trusted on a real review, it re-adjudicates
`evals/claim-benchmark-creatine.json` blind and `verify_claims.py score
--min-agreement 80` passes. A sentence with several citations is judged per
source for the part that source is cited for, and a caption is one claim;
`partial` is the exception, not the default.
`check` rejects any quote it cannot string-match against the stored evidence,
or that shares no content word or number with its claim unless the judgment
names the paraphrase (`--bridge "appetite = hunger"`, verified to connect both
sides and printed in the receipt), and downgrades the verdict — never argue with a downgrade, fix the quote or accept the lower
verdict. **Only `supported` and `partial` pairs ship.** A `contradicted`
verdict is a hard stop: correct the review sentence. A `not_found` or
`unverifiable` pair is a decorative citation — a real paper attached to a
sentence its text does not back — and it is repaired in the review, never
waved through: drop the citation, move it to the sentence it does support, or
rewrite the sentence to what the source says; then re-extract and re-adjudicate
the changed claims. `receipts`, the exporter, and PDF QA all refuse an audit
with any pending, contradicted, not_found, or unverifiable pair. `receipts`
then writes `<review>-receipts.md` — every cited sentence with its sources,
tiers, verdicts, and verbatim quotes — and stamps the review: each Sources
entry gains `· 3 claims · full text` and a two-line **Receipts** block after
Sources carries the tally and the file name. Re-run the validator; it checks
the stamp and never counts it as prose. Deliver the receipts file beside the
review in every format; the journal PDF takes `--claims-audit` and
`--claim-receipts` and prints only the tally in its colophon. State the tier split honestly in the reply (`claims_summary.json` has the
numbers): a claim verified only at abstract level is exactly that.

**Checking a draft** follows its own front door (see "Checking a draft"
above): `check_draft.py ingest` builds the ledger and normalized draft, then
this step runs unchanged and `check_draft.py report` renders the result.

## Rules that do not bend

- **Peer-reviewed literature only.** No preprints, blogs, news, or grey literature as evidence. Search eligibility and Crossref type are useful proxies, not a universal peer-review registry; check the venue or article when status is ambiguous, especially for conference proceedings and unfamiliar journals. If a preprint is the only source for something important, it may be mentioned once, labelled "(preprint, not peer reviewed)", and never load-bearing. Retracted papers are cited only to say they were retracted.
- **Never claim a check you did not perform.** "Verified" means the DOI resolved in Crossref; title, year, and source type matched; and Crossref's publisher/Retraction Watch update metadata showed no retraction, withdrawal, removal, or expression-of-concern signal. If Crossref is unavailable, verification is incomplete and the citation does not pass. OpenAlex search availability is irrelevant to this check. A receipt's tier is what it says: `full text` only when the quote was matched against the version-of-record text, `abstract` otherwise.
- **No citation from memory.** If you remember a paper, find it with the search script and verify it; if it cannot be found, it does not exist for this review. This applies to "classic" papers too.
- **No name from memory.** A person's given name or an institution appears in the review only when copied verbatim from the ledger's stored author record (via the synthesis's `actors` field) — never recalled, guessed, or expanded from an initial, no matter how confident the recall feels. Surnames from the citation tags and generic actors ("researchers", "the trial investigators") are always safe. The validator cross-checks every given-name-plus-surname pair against the ledger and fails the review on a mismatch.
- **Read before you cite.** Abstract minimum; full text for anything the argument leans on.
- **Represent the whole literature, not the convenient part.** If studies disagree, say so and say why they might. If the best evidence is weak, say the evidence is weak. A review that only tells one side is advocacy.
- **Keep the story and the evidence distinct.** Findings are attributed ("the MYRIAD trial found …"); synthesis is signposted ("taken together, …"); speculation is labelled as such.
- **Never hand back a file instead of an answer.** The review lives in the reply. A file is an extra only when the journal PDF or slides format requires the generated artifact, or when the user asks for one.
- **The sources block and the receipts are the audit trail.** Reviews carry no methods section; resolvable DOIs and verbatim receipts are what make the work checkable. Say nothing else about verification when it completes cleanly. Verification failures are fixed or removed before writing, never decorated with warning symbols in the finished review.
- **Numbers over adjectives.** Effect sizes, intervals, sample sizes, and absolute risks where the sources give them; "significant" on its own is not a result.

## Bundled resources

- `scripts/find_papers.py` and `scripts/audit_search.py` — paginated discovery, structured funnel records, publication screening, two-provider citation chasing, and tier coverage audit.
- `scripts/audit_production.py` and `references/production-workflow.md` — fail-fast multi-review journal production: live evidence/synthesis/semantic/figure/release gates, compact stage reports, bounded iteration exceptions, and exact figure hash/width binding to the final PDF.
- `scripts/verify_citations.py` — Crossref bibliographic and integrity verification (retractions, withdrawals, expressions of concern; corrections recorded) using publisher and integrated Retraction Watch update metadata; hard stop on a failure.
- `scripts/fetch_fulltext.py` and `scripts/audit_fulltexts.py` — open-access retrieval plus typed authenticity, duplicate, notes, and reading-evidence manifests.
- `references/claim-verification.md` — the adjudication rubric for claim-level verification: verdict definitions, quote rules, abstention discipline, escalation policy, and a worked example. Development benchmarks remain outside the release bundle.
- `scripts/claim_evidence.py` and `scripts/verify_claims.py` — claim-level verification: a tiered evidence store (Europe PMC full text → OpenAlex OA locations → abstract union floor, fail-closed on challenge pages) and an extract → fetch → packets → check → receipts pipeline that audits whether each cited sentence is supported by its source's own text. Verdicts of supported/partial/contradicted require a verbatim quote that the checker string-matches against the stored evidence (quotes it cannot find are rejected to unverifiable; numeric claims marked supported must carry a claim number inside the quote, with spelled-out numbers normalized). `check --summary` writes the tally the colophon prints; `receipts` attaches the Receipts block and Sources annotations to the review; a contradicted or pending pair blocks release.
- `scripts/check_draft.py` — the draft-check front door: parses citations in any form (DOI links, bare DOIs, numeric markers, author–year) with or without a reference list, resolves references to DOIs through Crossref, writes the ledger and a normalized draft the claim audit can read, and renders the chat report (scorecard, per-reference status incl. NOT FOUND/UNLISTED/RETRACTED, per-sentence receipts, citations to fix).
- `scripts/claim_receipts.py` — the reader-facing rendering of the audit shared by the validator, exporter, and PDF QA: summary counts, the receipts file, the Sources annotations and Receipts stamp, and the strip/shape checks that keep receipts out of the prose budget.
- `scripts/synthesis_quotes.py` — quotes before prose: parses the synthesis claims, requires a verbatim quote line for every cited key, string-matches each against the evidence store, and anchors every number in a claim sentence to a quote (`verify_claims.py synthesis-check`).
- `evals/decorative-citations.json` — regression set of real decorative citations (on-topic papers attached to sentences their text does not support) that the checker's relevance floor must reject, plus legitimate paraphrases an honest bridge must rescue.
- `scripts/format_references.py` — resolves `[@key]` citations, normalizes default chat punctuation, and builds the reference list (Vancouver / APA / Nature).
- `scripts/validate_review.py` — deterministic structure, strict-tier, chat citation placement, citation-reading, DOI parity, text-hygiene, and figure contracts.
- `scripts/export_review.py` and `scripts/weasyprint_export.py` — canonical browser-free, atomic journal-styled PDF/HTML export with linked superscript numbering, first-citation reference order, and sentence-initial-citation rejection.
- `scripts/export_deck.py` — explicit-only, verified 16:9 PDF deck export from a structured storyboard, local slide artwork, and the verified source ledger.
- `scripts/qa_deck_pdf.py` — fail-closed structural and independent Poppler raster QA for every delivered deck PDF.
- `scripts/qa_review_pdf.py` — exact release-lineage, intrinsic-vs-painted figure-aspect, visible-reference, terminal-page, and independent Poppler QA.
- `scripts/figure_contract.py`, `scripts/figure_provenance.py`, and `scripts/qa_figure.py` — shared topic-neutral figure-spec validation, provenance validation, and pixel-level conformance.
- `scripts/quantitative_figure_spec.py`, `scripts/quantitative_drawing.py`, `scripts/render_quantitative_figure.py`, `scripts/qa_quantitative_geometry.py`, and `scripts/figure_typography.py` — topic-neutral quantitative specification, drawing, rendering, plus intentionally independent data-to-pixel and raster-mark verification.
- `references/figure-feedback-generalization.md` — the no-showcase protocol that converts visual criticism into v3 contract fields and topic-neutral executable regression fixtures without canonizing examples.
- `scripts/build_release_skill.py` — deterministic allowlisted `.skill` packaging with version and commit provenance; excludes caches, examples, and scratch output by construction.
- `VERSION` and `scripts/grounded_metadata.py` — one shared semantic version, repository identity, and network user-agent source for every script.
- `requirements-pdf.txt` — pinned PDF export and QA packages; the exporter separately verifies the native print engine and canonical Charter/Helvetica Neue font resolution.
- `scripts/build_figure_prompt.py` — composes a rich route-aware image-generation or production prompt from a structured evidence specification, journal profile, figure archetype, and writing-style overlay.
- `scripts/compose_hybrid_figure.py` — legacy quality-contract-v1 compositor retained only to reproduce older releases; new v3 illustrations do not use it.
- `references/figure-generation-contract.md`, `references/figure-inspection-contract.md`, and `references/figure-writing-style-overlays.json` — communication-first planning/routing/iteration, auditable inspection and provenance schemas, non-distortion, and scientific/popsci/bullets/ELI5 art-direction contracts.
- `scripts/download_figure_references.py` — downloads the official-source visual-analysis corpus to an explicit private directory and records provenance, dimensions, hashes, and byte counts; source pixels are never bundled.
- `references/no-script-fallback.md` — the tool-only pipeline for sandboxes with no Python network access (claude.ai); read this whenever Step 0 fails.
- `references/quality-gates.md` — structured search/full-text/figure/release manifests and strict commands.
- `references/deck-guide.md` — explicit-only storyboard, evidence, slide-artwork, export, and QA contract for verified PDF decks.
- `references/sizes.md` — what small, medium, and large mean for scope, search depth, structure, and effort.
- `references/search-playbook.md` — generating angles, building queries, stopping rules, coverage checks, field notes.
- `references/evidence-weighing.md` — how to judge and describe the strength of what you read.
- `references/synthesis-guide.md` — the style-neutral claims ledger (`synthesis.md`) every style, figure, deck, and claim audit renders from: contract, claim rules, per-style arrangement, and the anti-paraphrase rule.
- `references/writing-guide.md` — the shared writing core: structure invariants, language, term links, length, citing, the quality gate.
- `references/style-scientific.md`, `references/style-popsci.md`, `references/style-bullets.md`, `references/style-eli5.md` — one guide per writing style: exact layout, narrative rules, and register.
- `references/citation-rules.md` — keys, styles, in-text conventions, what may and may not be cited.
- `references/media-modes.md` — figure workflow for the journal PDF and slides formats: visual grammar, rendering, captions, and QA.
- `references/figure-style-system.md` — defined Arial typography, Nature-inspired visual grammar, style selection, and adaptation boundaries.
- `references/figure-reference-analysis.md` and `references/nature-figure-corpus.json` — the 21-figure official-source visual audit and reproducible manifest behind the style profiles; downloaded pixels remain private analysis inputs.
- `references/figure-captions.md` — stable figure IDs, automatic numbering, body cross-references, style-matched caption forms, verified caption citations, and no-script fallback syntax.
- `references/image-prompt-guide.md` — modular prompt specification, iteration protocol, and acceptance contract.
- `references/figure-style-presets.json` and `references/figure-archetypes.json` — machine-readable style and composition modules used by the prompt builder.
