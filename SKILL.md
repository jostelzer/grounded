---
name: grounded
description: Write a scientific review of a topic or research question at small, medium, or large size, in scientific style (flowing narrative prose, the default), popsci style (popular-science magazine storytelling), bullets, or ELI5 (very simple flowing prose), delivered as inline chat (the default), a journal-styled PDF that always includes generated figures, or — only when the user explicitly asks for it — an experimental verified 16:9 slide deck, built only on peer-reviewed literature found by real searches, with every citation and its retraction status verified through Crossref. Use this whenever the user wants a literature review, narrative review, state of the evidence, research summary, background or related-work section, an overview of a scientific field, or explicitly asks for a deck, slides, presentation, slide deck, or journal club deck. Also use it to check a draft's claims or references against the literature.
---

# Grounded — scientific reviews with no floating claims

The user gives a topic or question and may name a size, style, or output format; you produce a clean, thorough review that looks at the question from every relevant angle and tells a story that rests entirely on peer-reviewed science, cited correctly. The central discipline is that **no citation is ever recalled from memory**: every source comes from a live index search, every DOI is verified before it is cited, and the reference list is generated from the verified records. A review with one fabricated reference is worth less than no review.

## First: confirm size, style, and output format

A review has three dimensions: a **size** (`small`, `medium`, `large`), a **style** (`scientific`, `popsci`, `bullets`, `eli5`), and an **output format** (`inline chat`, `journal PDF`, and — hidden by default — the experimental `slides`).

Unless the request names **all three**, your very first action — before any searching, planning, or other work — is to ask one short question for whatever is missing. Do it immediately, within seconds of being invoked, and keep it to a few lines listing the options with the default marked (size: small / medium / large; style: scientific / popsci / bullets / ELI5; format: inline chat / journal PDF). **Do not list slides in the format question**: it is experimental and hidden by default, used only when the user explicitly asks for a deck, slides, or a presentation in their own words — an explicit request settles the format dimension like any other. If the environment has an interactive question tool, use it; otherwise ask in plain chat and wait for the answer. Ask only for the missing dimension(s) — whatever the request already names is settled and is not re-asked. If all three are named, skip the question entirely and start.

If the user answers "you pick", "default", or similar — or the session is non-interactive and cannot ask — use small scientific in inline chat.

## Output formats

There are exactly three output formats. **Inline chat** is the default; **journal PDF** happens only when the user chooses it — in the original request or as the answer to the format question. **Slides** is experimental and hidden by default: it is never offered in the format question and happens only when the user explicitly asks for a deck, slides, or a presentation themselves. Never infer journal PDF or slides silently.

### Inline chat (default)

**Write the finished review directly in your reply. Do not create `review.md`. Do not attach, upload, or hand back a file. Do not put it in an artifact or canvas.**

This is not a formatting preference — a markdown file is *worse* for the reader: chat clients cannot preview it, and on the user's machine it opens in a code editor with the formatting stripped, which looks broken. The review is meant to be read in the conversation, where the headings, tables and bold actually render.

Working files are different. `sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `synthesis.md`, and the draft are audit inputs: keep them if you have a filesystem, never present them as the main output, and mention them only if the user might want to audit. If there is no filesystem, hold the ledger in context and carry on.

Produce a file **only** when the user asks for one ("save it", "give me a .md", "export to Word"). Then write the file *and* still put the review in the chat.

### Journal PDF

When the user asks for a **PDF**, a **printable** or **shareable** version, or "make it look like a journal article" — or picks the journal PDF in the format question — use the canonical browser-free PDF path below — and note that **the journal PDF always includes generated figures**. There is no separate image mode: choosing the PDF format is what triggers figure creation. The figure budget scales with size (small 1, medium up to 3, large up to 5 — caps, not quotas), and every figure is built from the verified findings per `references/media-modes.md` and the figure references it names, then embedded in both the review and the PDF. `scripts/export_review.py` turns the finished markdown into the single canonical GROUNDED HTML/CSS design, then renders that exact design with pinned WeasyPrint: Swiss-modern masthead strip with the packaged Grounded logo, a linked "Agentically generated scientific review" descriptor, and the Grounded version on every page; a metadata grid including the selected writing style; numbered sections; two-column Charter body; Helvetica Neue furniture; full-width tables and figures; cited captions; DOI-linked superscript citation numbers; numbered references in first-citation order; and clickable figure references. Journal citations attach to the preceding supported claim or quotation; a citation that grammatically opens a sentence is a hard export error. Do not invoke Chrome, another browser, ReportLab, or an ad-hoc external template as a fallback.

```bash
python3 scripts/export_review.py --check-pdf-runtime
python3 scripts/export_review.py --in review.md --out review.pdf --pdf --style <scientific|popsci|bullets|eli5> --ledger sources.json --release-manifest release-manifest.json
python3 scripts/qa_review_pdf.py review.pdf --manifest release-manifest.json --render-dir review-pdf-qa --report pdf-qa.json
```

The runtime check is a hard gate. If it fails, install the exact packages in `requirements-pdf.txt` and the native Pango runtime required by WeasyPrint, then rerun it; never silently switch renderers. On macOS, use the matching Homebrew WeasyPrint executable so Pango is self-contained. The exporter embeds every figure as a data URI and permits the renderer to load only `data:` resources: remote, missing, and escaping assets are hard failures, while PNG/JPEG/WebP and SVG are supported directly. Output is written atomically: a failed build cannot overwrite an existing good PDF. After rendering, the exporter strictly parses the artifact and refuses to replace the prior PDF unless the producer is pinned WeasyPrint and the embedded fonts include Charter and Helvetica Neue; a fallback-font redesign is a hard failure. HTML sidecars are off by default and require `--html-sidecar` explicitly.

The QA command is also mandatory before delivery. Its release manifest hashes the exact review, ledger, generated HTML, PDF, and every figure/spec/prompt. QA rehashes them, independently rebuilds the HTML, requires one canonical PDF, a visible terminal References heading, every expected DOI as both visible reference text and a URI annotation, canonical A4 metadata/fonts, and running furniture; it then rasterizes every page through Poppler and checks masthead, page number, body, clipping, column balance, and sparse terminal reference pages. Use a new or empty case-local `--render-dir` and inspect every generated page and contact sheet visually; the manifest records that one authoritative render set. A heading stranded at the bottom while its first paragraph/table/figure starts on the next page, an avoidably sparse spill page, or a large preventable blank region is release-blocking. Rebalance and rebuild without dropping evidence or shrinking type. The exporter prevents the smallest failure itself: when a final page would carry only the tail of the reference list, it re-renders once with reference leading tightened inside a bounded envelope (type size untouched) and keeps whichever render has no spill, noting the adjustment in the release manifest. `--ref-leading` sets that leading manually, `--figure-max-height` (60–120 mm) adjusts the figure cap, and `--columns 1` gives a single-column layout; QA failure messages state how far a sparse page is from its threshold and which lever closes it. For image PDFs, repeat `--figure-spec` and `--figure-prompt` once per figure. Full commands and contracts are in `references/quality-gates.md`. The review still goes in the chat as well.

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
written review to lean on. Version 1 is 16:9 PDF only.

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

- **Size: small. Style: scientific. Format: inline chat** (`scientific` was formerly named `prose`; treat `prose` as an alias) — but these apply only after the "First: confirm size, style, and output format" question above: the defaults are for when the user answers "you pick" or the session cannot ask, never a reason to skip the question.
- **Inline chat means chat only** — delivered in the chat, formatted with markdown, as well-presented as possible. No file, no attachment, unless the user chose the journal PDF or slides.
- **Chat/markdown citations: `Author 2026` inline, hyperlinked to the DOI.** Put the link immediately after the supported claim or quotation and before its sentence-ending punctuation: `claim [Author 2026](DOI).`, never `claim. [Author 2026](DOI)` and never a citation-led sentence. The reader must never see square brackets around a citation — they exist only as markdown link syntax. Never write a bare `[Author 2026]`, `[1]`, or `(Author, 2026)` in the chat review. The Sources block at the end carries the DOIs. The journal PDF/HTML renderer is the deliberate exception: it replaces those author–year labels only in the journal artifact with linked superscript numbers and a matching numbered reference list.
- **Structure is fixed per style** — scientific: question → abstract → introduction → claim-headed sections → conclusion → sources; popsci: headline → standfirst → lede → nut graf → narrative crossheads along one spine with a turn → kicker → sources; bullets: question → TL;DR → punchline sections of bullets → sources; ELI5: question → TL;DR → familiar starting point → step-by-step sections that each add one idea, with the contrary evidence as its own step → a hand-back ending → sources. Shared rules in `references/writing-guide.md`; exact layouts in the per-style files it names (`references/style-scientific.md`, `style-popsci.md`, `style-bullets.md`, `style-eli5.md`).
- **Technical terms link to explainers.** The first use of an abbreviation or specialist term (SMD, CI, GRADE, HAM-D, mRNA, …) is a link to its verified Wikipedia article, so a non-specialist can click instead of googling. Rules and verification in `references/writing-guide.md`.
- **No preamble and no meta.** No scope note, assumptions paragraph, audience statement, size label, or "how this review was produced" section. Make sensible scope choices silently.
- **Concise throughout.** Shortest language that carries the evidence.

## Sizes and styles

A review has a **size** (how much evidence) and a **style** (how it is written). The two are independent; any size combines with any style.

**Size** — default **small**:

- **Small** — default. Use when the user leaves the choice to you after the size/style question.
- **Medium** — when the user asks for `medium`, or when the question plainly contains several genuinely distinct sub-questions that cannot be answered well at small depth.
- **Large** — when the user asks for `large` or `big`; the words are aliases.

**Style** — default **scientific**:

- **Scientific** — default (alias: `prose`, its former name). A narrative article in journal register: abstract, introduction, claim-headed topic-sentence sections, conclusion. Word budgets ~1.5× the bullet tier. Rules in `references/style-scientific.md`. Scientific prints well — after delivering, offer the PDF export.
- **Popsci** — when the user asks for `popsci`, "popular science", "magazine style", "science journalism", or names Scientific American, New Scientist, Quanta, or a similar magazine. A magazine feature for a curious educated adult, told along one narrative spine: honest headline, standfirst, concrete cited lede, nut graf, narrative crossheads with the contrary evidence as the turn, kicker — with full verified citations throughout. Rules in `references/style-popsci.md`.
- **Bullets** — when the user asks for `bullets`, a list, or the compact structured format. Punchline headings and cited bullet bodies, per `references/style-bullets.md`.
- **ELI5** — when the user asks for `eli5`, "explain like I'm five", or very simple language. A patient step-by-step explanation in very simple English: it starts from something the reader already knows and climbs one idea at a time to the answer, per `references/style-eli5.md`; do not turn it into a bullet list unless the user also explicitly asks for bullets. When both are requested, use `bullets` as the structural style and ELI5 as its language register.

Style never changes search depth, source counts, citations, or verification. Scientific and bullets use the normal verified term links; popsci names a term, glosses it inline, and links it; ELI5 rewrites jargon into everyday language and links only an unavoidable term after explaining it. The register spectrum runs scientific → popsci → ELI5.

**Output formats** — how the review is delivered, independent of size and style:

- **Inline chat** — the default. The review is the reply itself; nothing extra is generated.
- **Journal PDF** — when the user asks for a PDF, a printable/shareable version, or a journal-styled artifact, or picks it in the format question. It **always includes generated figures**; the figure budget scales with size (small 1, medium up to 3, large up to 5 — caps, not quotas). Run the review pipeline at the chosen size, then create the figures from the verified findings per `references/media-modes.md`. For figure generation, also read `references/figure-reference-analysis.md`, `references/figure-style-system.md`, `references/image-prompt-guide.md`, and `references/figure-captions.md`; build the prompt from a structured figure specification with `scripts/build_figure_prompt.py`. Place each figure after the section it supports, reference it from the body, and give it a style-matched caption with verified citations. Figures flow into the PDF export automatically.
- **Slides** — experimental and hidden by default: never offered in the format question, never suggested, and never inferred. Runs only on the explicit triggers `deck`, `slides`, “presentation”, “slide deck”, or “journal club deck” in the user's own words. Combines freely with every size and style. The deck is the deliverable: chat carries the question, a 1–3 sentence plain answer, and the verified 16:9 PDF; the written synthesis stays an internal working draft. Every content slide must pass the standalone test — claim, evidence, and firmness readable from the slide alone. Follow `references/deck-guide.md`; generate one slide-context evidence image per content slide, then run the canonical exporter and mandatory landscape QA.

Figure and slide creation happens only after the evidence has been searched, read, verified, and synthesized.

| | Small (default) | Medium | Large |
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
| Journal-PDF figures | 1 | up to 3 | up to 5 |
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

Work through every step; the order matters because the later steps depend on the ledger built in the early ones. Keep all working files in one folder for the review (`<topic-slug>/`): `sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `fulltext-manifest.json`, `synthesis.md`, `review_draft.md`, and `review.md`, plus requested media. PDF releases add `release-manifest.json` and one authoritative QA render directory. See `references/quality-gates.md` for the machine-auditable contracts.

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

Before any styled prose, distill the verified evidence into `synthesis.md` — the style-neutral claims ledger specified in `references/synthesis-guide.md` (read it first): a verdict paragraph, the throughline, every load-bearing claim as an atomic calibrated sentence with its strength, exact numbers, supporting keys, contrary evidence, boundary, and dependencies, then the cross-claim patterns and open questions. Write it from `sources.json` and `notes.md` only. The synthesis is the single source that the styled review, the figures, the deck storyboard, and the claim audit all draw from; it is a working file, never delivered and never quoted verbatim. If drafting later reveals a wrong or missing claim, fix the synthesis first, then the draft.

### 5b. Write the draft

Compose the draft **from the synthesis claims** — arranged and told in the selected style, never paraphrased line by line — citing with ledger keys: `claim [@Kuyken2022effectiveness].`, or `claim [@a; @b].` for several. The citation key precedes sentence-ending punctuation; never write `claim. [@key]`. Follow the shared rules in `references/writing-guide.md` and the selected style's fixed layout in its own file (`references/style-scientific.md`, `style-popsci.md`, `style-bullets.md`, `style-eli5.md`) — read the style file before drafting. The default scientific review uses a citation-free four-move Abstract, an Introduction that poses one throughline, claim-headed sections of topic-sentence paragraphs that advance it, and a Conclusion that names the cross-cutting pattern. Popsci uses a magazine feature architecture told along one narrative spine — honest headline, citation-free standfirst, concrete cited lede, nut graf, narrative crossheads with the contrary evidence as the turn, and a kicker — with a reporter's stance and a per-section numbers budget, per `references/style-popsci.md`. Explicit bullet style uses a citation-free TL;DR, punchline headings, and cited bullet bodies. ELI5 uses a citation-free TL;DR, then climbs a staircase: a familiar starting point, step-by-step sections that each add one idea built only on earlier steps (headings are often the reader's own next question), the contrary evidence as its own step, and a hand-back ending the reader could repeat to a friend; bullet bodies are wrong unless the user explicitly requested bullets too. In every style, order the argument deliberately, contrast opposing evidence, use a table wherever several studies share dimensions, report numbers with intervals, cite primary studies for findings, and use reviews for consensus.

### 6. Format and check

Run the formatter through the deterministic writing-contract validator:

```bash
python3 scripts/format_references.py --ledger sources.json --draft review_draft.md --style bracket | python3 scripts/validate_review.py - --style scientific --size small --ledger sources.json --fulltext-manifest fulltext-manifest.json --pass-through --report validation.json
```

Replace the style and size. When the user explicitly named the tier, add `--strict-tier`; add `--image-mode` when the journal PDF format was requested, since its figures are mandatory. Strict mode hard-checks word/source/section/table/figure ranges and the full-text minimum. The formatter normalizes a legacy `claim. [@key]` draft to `claim [Author](DOI).`; the validator rejects finished citations that follow sentence-ending punctuation or open a sentence. It separately gates Crossref identity, retraction status, publication eligibility, and reading evidence, and rejects mojibake, scaffold labels, DOI/reference drift, and broken figure placement/citations. Default-small chat answers keep tier ranges advisory. Then work through the Quality gate checklist in `references/writing-guide.md` (the manual companion to this deterministic gate), and write the validated text in the reply.

Keep the validated author–year markdown as the review source: chat punctuation follows the citation link. If journal PDF/HTML is requested, `export_review.py` performs the presentation-only conversion to DOI-linked superscript numbers, moves the punctuation before those raised numbers, orders the References section by first citation, closes whitespace so each number sits directly after its supported claim or quotation, and rejects sentence-initial citations. Do not run `format_references.py --style nature` as a substitute: that would also change the chat review and bypass the journal placement gate.

### 6b. Claim audit (experimental; on request or when checking a draft)

When the user asks for a claim-level audit, asks to check a draft's claims against the literature, or asks for a review with a verified-claims appendix, run the quote-anchored audit after the writing gate. Follow the rubric in `references/claim-verification.md`:

```bash
python3 scripts/verify_claims.py extract --review review.md --audit claims_audit.json
python3 scripts/verify_claims.py fetch   --audit claims_audit.json --evidence evidence/
python3 scripts/verify_claims.py packets --audit claims_audit.json --evidence evidence/
# adjudicate each packet: write verdict + verbatim quote(s) into claims_audit.json
python3 scripts/verify_claims.py check   --audit claims_audit.json --evidence evidence/ --appendix claims_appendix.md
```

Verdicts you write must carry quotes copied verbatim from the packet passages; `check` rejects any quote it cannot string-match against the stored evidence and downgrades the verdict — never argue with a downgrade, fix the quote or accept the lower verdict. A `contradicted` verdict is a hard stop: correct the review sentence, not the audit. Report the evidence-tier split honestly (full text vs abstract) whenever you deliver an audit; a claim verified only at abstract level is stated as exactly that.

### 7. Create the figures or slides

Skip this step for inline chat. For the journal PDF format the figures are mandatory (small 1, medium up to 3, large up to 5); for slides, build the deck. Follow the figure references and build visuals only from the claim and pattern entries in `synthesis.md`, never from a fresh reading of the papers. Save the figure spec and generated prompt; include directed `relationships` and local `abbreviations` where applicable. After generation, run `scripts/qa_figure.py --spec figure.json --image figure.png --inspection figure-inspection.json`. It gates exact OCR text, relationship direction, abbreviations, prohibited effects, collisions, and effective PDF label size. Make one targeted repair; use a deterministic vector figure when text-heavy ImageGen output still cannot pass. Give every figure a stable ID, introduce it before the artwork, and end its style-matched caption with 2–5 verified citations.

For the slides format, follow `references/deck-guide.md`. Use the same verified synthesis
and figure pipeline, but set `render_context: slide` for every content image and
make each image carry the evidence itself — comparisons, plotted numbers with
intervals, labelled mechanisms, pictured study designs — so the slide passes
the standalone test with no caption or body text to lean on. Storyboard
according to the selected style, keep claim titles and DOI citations in
renderer chrome, build with `export_deck.py`, and run `qa_deck_pdf.py`. Inspect
every slide raster and apply the standalone test to each. The slides format does
not permit the deterministic vector fallback: if a capable image model is
unavailable or the images cannot pass QA, fall back to delivering the internal
synthesis as a normal full review and state in one sentence that the deck could
not be generated.

## Rules that do not bend

- **Peer-reviewed literature only.** No preprints, blogs, news, or grey literature as evidence. Search eligibility and Crossref type are useful proxies, not a universal peer-review registry; check the venue or article when status is ambiguous, especially for conference proceedings and unfamiliar journals. If a preprint is the only source for something important, it may be mentioned once, labelled "(preprint, not peer reviewed)", and never load-bearing. Retracted papers are cited only to say they were retracted.
- **Never claim a check you did not perform.** "Verified" means the DOI resolved in Crossref; title, year, and source type matched; and Crossref's publisher/Retraction Watch update metadata showed no retraction, withdrawal, removal, or expression-of-concern signal. If Crossref is unavailable, verification is incomplete and the citation does not pass. OpenAlex search availability is irrelevant to this check.
- **No citation from memory.** If you remember a paper, find it with the search script and verify it; if it cannot be found, it does not exist for this review. This applies to "classic" papers too.
- **Read before you cite.** Abstract minimum; full text for anything the argument leans on.
- **Represent the whole literature, not the convenient part.** If studies disagree, say so and say why they might. If the best evidence is weak, say the evidence is weak. A review that only tells one side is advocacy.
- **Keep the story and the evidence distinct.** Findings are attributed ("the MYRIAD trial found …"); synthesis is signposted ("taken together, …"); speculation is labelled as such.
- **Never hand back a file instead of an answer.** The review lives in the reply. A file is an extra only when the journal PDF or slides format requires the generated artifact, or when the user asks for one.
- **The sources block is the audit trail.** Reviews carry no methods section; resolvable DOIs are what make the work checkable. Say nothing when verification completes cleanly. Verification failures are fixed or removed before writing, never decorated with warning symbols in the finished review.
- **Numbers over adjectives.** Effect sizes, intervals, sample sizes, and absolute risks where the sources give them; "significant" on its own is not a result.

## Bundled resources

- `scripts/find_papers.py` and `scripts/audit_search.py` — paginated discovery, structured funnel records, publication screening, two-provider citation chasing, and tier coverage audit.
- `scripts/verify_citations.py` — Crossref bibliographic and integrity verification (retractions, withdrawals, expressions of concern; corrections recorded) using publisher and integrated Retraction Watch update metadata; hard stop on a failure.
- `scripts/fetch_fulltext.py` and `scripts/audit_fulltexts.py` — open-access retrieval plus typed authenticity, duplicate, notes, and reading-evidence manifests.
- `references/claim-verification.md` — the adjudication rubric for claim-level verification: verdict definitions, quote rules, abstention discipline, escalation policy, and a worked example. `evals/claim-benchmark-creatine.json` is the gold-labeled benchmark; measure a judge with `verify_claims.py score`.
- `scripts/claim_evidence.py` and `scripts/verify_claims.py` (experimental) — claim-level verification: a tiered evidence store (Europe PMC full text → OpenAlex OA locations → abstract union floor, fail-closed on challenge pages) and an extract → fetch → packets → check pipeline that audits whether each cited sentence is supported by its source's own text. Verdicts of supported/partial/contradicted require a verbatim quote that the checker string-matches against the stored evidence (quotes it cannot find are rejected to unverifiable; numeric claims marked supported must carry a claim number inside the quote, with spelled-out numbers normalized). Output is a machine-readable audit plus a rendered appendix; a contradicted claim is a hard stop.
- `scripts/format_references.py` — resolves `[@key]` citations, normalizes default chat punctuation, and builds the reference list (Vancouver / APA / Nature).
- `scripts/validate_review.py` — deterministic structure, strict-tier, chat citation placement, citation-reading, DOI parity, text-hygiene, and figure contracts.
- `scripts/export_review.py` and `scripts/weasyprint_export.py` — canonical browser-free, atomic journal-styled PDF/HTML export with linked superscript numbering, first-citation reference order, and sentence-initial-citation rejection.
- `scripts/export_deck.py` — explicit-only, verified 16:9 PDF deck export from a structured storyboard, local slide artwork, and the verified source ledger.
- `scripts/qa_deck_pdf.py` — fail-closed structural and independent Poppler raster QA for every delivered deck PDF.
- `scripts/qa_review_pdf.py` — exact release-lineage, visible-reference, terminal-page, and independent Poppler QA.
- `scripts/qa_figure.py` — OCR/spec/topology/effective-label conformance for generated figures.
- `scripts/build_release_skill.py` — deterministic allowlisted `.skill` packaging with version and commit provenance; excludes caches, examples, and scratch output by construction.
- `VERSION` and `scripts/grounded_metadata.py` — one shared semantic version, repository identity, and network user-agent source for every script.
- `requirements-pdf.txt` — pinned PDF export and QA packages; the exporter separately verifies the native print engine and canonical Charter/Helvetica Neue font resolution.
- `scripts/build_figure_prompt.py` — composes an end-to-end ImageGen prompt from a structured evidence specification, a reusable journal-style profile, and a figure archetype.
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
