---
name: grounded
description: Write a scientific review of a topic or research question at small, medium, or large size, as bullets, flowing prose, or eli5 (very simple English), optionally with an image or mindmap, built only on peer-reviewed literature found by real searches, with every citation and its retraction status verified through Crossref. Use this whenever the user wants a literature review, narrative review, state of the evidence, research summary, background or related-work section, an overview of a scientific field, a scientific illustration grounded in reviewed findings, or a findings mindmap. Also use it to check a draft's claims or references against the literature.
---

# Grounded — scientific reviews with no floating claims

The user gives a topic or question and may name a mode; you produce a clean, thorough review that looks at the question from every relevant angle and tells a story that rests entirely on peer-reviewed science, cited correctly. The central discipline is that **no citation is ever recalled from memory**: every source comes from a live index search, every DOI is verified before it is cited, and the reference list is generated from the verified records. A review with one fabricated reference is worth less than no review.

## The deliverable is your chat message

**Write the finished review directly in your reply. Do not create `review.md`. Do not attach, upload, or hand back a file. Do not put it in an artifact or canvas.**

This is not a formatting preference — a markdown file is *worse* for the reader: chat clients cannot preview it, and on the user's machine it opens in a code editor with the formatting stripped, which looks broken. The review is meant to be read in the conversation, where the headings, tables and bold actually render.

Working files are different. `sources.json`, `search_log.md` and the draft are scratch: keep them if you have a filesystem, never present them as the output, and mention them only in a short closing line if the user might want to audit. If there is no filesystem, hold the ledger in context and carry on.

Produce a file **only** when the user asks for one ("save it", "give me a .md", "export to Word"). Then write the file *and* still put the review in the chat.

When the user asks for a **PDF**, a **printable** or **shareable** version, or "make it look like a journal article", use the canonical browser-free PDF path below. `scripts/export_review.py` turns the finished markdown into the single canonical GROUNDED HTML/CSS design, then renders that exact design with pinned WeasyPrint: Swiss-modern masthead strip with the earth-ground chip and "No floating claims." tagline on every page, provenance line, metadata grid, numbered sections, two-column Charter body, Helvetica Neue furniture, full-width tables and figures, cited captions, live DOI links, and clickable figure references. Do not invoke Chrome, another browser, ReportLab, or an ad-hoc external template as a fallback.

```bash
python3 scripts/export_review.py --check-pdf-runtime
python3 scripts/export_review.py --in review.md --out review.pdf --pdf
python3 scripts/qa_review_pdf.py review.pdf --markdown review.md --render-dir review-pdf-qa
```

The runtime check is a hard gate. If it fails, install the exact packages in `requirements-pdf.txt` and the native Pango runtime required by WeasyPrint, then rerun it; never silently switch renderers. On macOS, use the matching Homebrew WeasyPrint executable so Pango is self-contained. The exporter embeds every figure as a data URI and permits the renderer to load only `data:` resources: remote, missing, and escaping assets are hard failures, while PNG/JPEG/WebP and SVG are supported directly. Output is written atomically: a failed build cannot overwrite an existing good PDF. After rendering, the exporter strictly parses the artifact and refuses to replace the prior PDF unless the producer is pinned WeasyPrint and the embedded fonts include Charter and Helvetica Neue; a fallback-font redesign is a hard failure. HTML sidecars are off by default and require `--html-sidecar` explicitly.

The QA command is also mandatory before delivery. It strictly parses the PDF, checks A4 geometry, metadata, prohibited document actions, DOI and internal figure links, running masthead and total-aware page number on every page, then independently rasterizes every page through Poppler and checks masthead, page number, body, and clipping-edge pixels. Use a new or empty `--render-dir`, inspect every generated page/contact sheet visually, and fix any defect before delivering. `--columns 1` gives a single-column layout; plain `--out review.html` remains the separate HTML-only path. `--kicker "Review · Immunology"` sets the label above the title; the version and repository label in the provenance line are auto-detected from git (`--release`/`--repo` override them). The review still goes in the chat as well.

The two experimental media modes are the only standing exception: `image` and `mindmap` still deliver the written review in chat, additionally generating and displaying the media artifacts (one mindmap; one to five figures depending on size). The media never replaces the review.

## Defaults — do not ask, just do this

- **Size: small. Style: bullets.** Only deviate if the user asks or the question plainly needs it. Never ask which size or style.
- **Delivered in the chat**, formatted with markdown, as well-presented as possible. No file, no attachment, unless asked.
- **Citations: `Author 2026` inline, hyperlinked to the DOI.** The reader must never see square brackets around a citation — they exist only as markdown link syntax. Never write a bare `[Author 2026]`, `[1]`, or `(Author, 2026)` in the finished text. Sources block at the end carries the DOIs.
- **Structure is fixed per style** — bullets: question → TL;DR → punchline sections of bullets → sources; prose: question → abstract → introduction → thematic sections → conclusion → sources. Exact layouts in `references/writing-guide.md`.
- **Technical terms link to explainers.** The first use of an abbreviation or specialist term (SMD, CI, GRADE, HAM-D, mRNA, …) is a link to its verified Wikipedia article, so a non-specialist can click instead of googling. Rules and verification in `references/writing-guide.md`.
- **No preamble and no meta.** No scope note, assumptions paragraph, audience statement, size label, or "how this review was produced" section. Make sensible scope choices silently.
- **Concise throughout.** Shortest language that carries the evidence.

## Sizes and styles

A review has a **size** (how much evidence) and a **style** (how it is written). The two are independent; any size combines with any style.

**Size** — default **small**:

- **Small** — default. Use when no size is requested.
- **Medium** — when the user asks for `medium`, or when the question plainly contains several genuinely distinct sub-questions that cannot be answered well at small depth.
- **Large** — when the user asks for `large` or `big`; the words are aliases.

**Style** — default **bullets**:

- **Bullets** — default. Punchline headings, cited bullet bodies, per `references/writing-guide.md`.
- **Prose** — when the user asks for `prose`, "narrative", "essay", or written-out flowing text. A narrative article: abstract, introduction, topic-sentence paragraphs, conclusion. Word budgets ~1.5× the bullet tier. Rules in "Prose style" in `references/writing-guide.md`. Prose prints well — after delivering, offer the PDF export.
- **ELI5** — when the user asks for `eli5`, "explain like I'm five", or very simple language. Very simple English, per "ELI5 language" in `references/writing-guide.md`. Defaults to small size unless a size is named.

Style never changes search depth, source counts, citations, term links, or verification — only the writing register.

**Media modes (experimental)** — these are additive artifacts, not styles:

- **Image** — only when the user explicitly asks for an `image`/`figures` as part of the output or names `image mode`. Do not infer it merely because an image might be helpful or because the research topic contains the word “image.” Combines with any size and style; the figure budget scales with size (small 1, medium up to 3, large up to 5 — caps, not quotas). Run the review pipeline at the chosen size, then create the figures from the verified findings per `references/media-modes.md`. For image generation, also read `references/figure-reference-analysis.md`, `references/figure-style-system.md`, `references/image-prompt-guide.md`, and `references/figure-captions.md`; build the prompt from a structured figure specification with `scripts/build_figure_prompt.py`. Place each figure after the section it supports, reference it from the body, and give it a style-matched caption with verified citations. Figures flow into the PDF export automatically.
- **Mindmap** — only when the user explicitly asks for a `mindmap` as the output or names `mindmap mode`. Do not infer it merely because a diagram might be helpful. Run the **small** review pipeline, then create one rendered mindmap from the verified findings.

If the user explicitly asks for both `image` and `mindmap`, run one small review and add both media artifacts. For either media mode, read `references/media-modes.md` before planning the visual. Media creation happens only after the evidence has been searched, read, verified, and synthesized.

| | Small (default) | Medium | Large |
|---|---|---|---|
| Body length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Searches | 1–2 queries per angle, 3–5 angles | 2–3 per angle, 5–8 angles | 3–5 per angle, 8–12 angles, plus citation chasing |
| Full texts read | The 2–4 load-bearing papers | 8–15 | 25+ |
| Tables | 0–1 | 1–2 | 2–4 |

Bigger sizes add sections, bullets, and tables — never longer sentences. In prose style, multiply body length by ~1.5; everything else in the table is unchanged.

Full tier and style definitions are in `references/sizes.md`.

## Step 0: check whether the scripts can reach the network

Some environments (claude.ai among them) sandbox Python without outbound network access. Run this **before searching**:

```bash
python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.crossref.org/works/10.1136/bmj.n71',timeout=15).status)"
```

`200` → use the scripts below. Anything else → the scripts cannot run here; switch to `references/no-script-fallback.md`, which does every step through the web-fetch tool against the same APIs (this works on claude.ai). The verification standard does not change between paths — only the mechanism. If neither path works, say so and do not present an unverified review as a verified one.

## The pipeline

Work through every step; the order matters because the later steps depend on the ledger built in the early ones. Keep all working files in one folder for the review (`<topic-slug>/`): `sources.json` (the ledger), `search_log.md`, `notes.md`, `review_draft.md`, `review.md`, plus the generated media only in image or mindmap mode.

### 1. Scope the question into angles

Before searching, write down the angles a thorough reviewer would cover — this is what "looking at all angles" means in practice. Typical angles for an empirical question: existing systematic reviews and meta-analyses; the largest or most rigorous primary studies; mechanism or theory; contradictory or null findings; different populations, settings, doses, or durations; measurement and methodological critiques; harms or unintended effects; historical origin of the claim; very recent work. For other question types see `references/search-playbook.md`. Write the angle list into `notes.md`; it becomes the skeleton of the review.

### 2. Search, angle by angle

Use `scripts/find_papers.py`. It cursor-pages through OpenAlex and offset-pages through PubMed up to `--limit` records per query and database (default 100), automatically appends every database run and its total/retrieved/accepted/new counts to `search_log.md`, and merges accepted candidates into `sources.json` with discovery provenance. `--query` searches both databases; use `--openalex-query` and `--pubmed-query` for database-specific syntax. The default strict policy admits explicitly typed journal research/reviews, excludes obvious non-evidence types such as editorials and letters, excludes preprints unless deliberately enabled, and admits conference-literature candidates only with `--include-conference-papers`. This is an index-based candidate screen, **not proof of peer review**: entries say `peer_review_status: not_independently_verified`, so confirm the venue's peer-review model when it is ambiguous.

Run reviews-first (`--types review`) for each angle, then primary studies, then an OpenAlex cited-sort pass for foundational papers. For medium and large reviews, automate backward and forward citation discovery from the central ledger entries with `--chase <key> --chase-direction both`; the resulting ledger provenance records the seed and direction. If OpenAlex is skipped, widen the PubMed queries and use `WebSearch` only to discover candidate titles/DOIs that are then added through the ledger. Stop by the coverage rules in the playbook, not merely because one top-results page repeats.

### 3. Read

Read every abstract in the ledger that you might cite (`find_papers.py --show`, `--abstracts`). For the load-bearing sources — the largest trials, the key meta-analyses, the studies that disagree — pull the full text with `scripts/fetch_fulltext.py` (Europe PMC open access) or `WebFetch` on the open-access URL, and read the methods and results, not just the abstract. Record in `notes.md`, per source: design, sample, main result with numbers and intervals, main limitation, and which angle it speaks to. Do not cite a paper you have not at least read the abstract of. `references/evidence-weighing.md` tells you how to judge what you read.

### 4. Verify

Run `scripts/verify_citations.py --ledger sources.json`. It uses the Crossref record for both bibliographic verification (DOI, title, year, and article type) and retraction screening. Crossref integrates publisher updates and Retraction Watch records; the verifier inspects both `updated-by` on a retracted original and `update-to` on a retraction notice. A mismatch, unavailable Crossref record, or retraction signal is a hard failure and the source is removed or fixed before writing. OpenAlex is not part of citation verification.

### 5. Write the draft

Write the draft citing with ledger keys: `[@Kuyken2022effectiveness]`, or `[@a; @b]` for several. Follow the fixed layout in `references/writing-guide.md`: the question, a citation-free TL;DR, then sections whose **headings are the punchlines** and whose bodies are **bullets only**, ordered so the argument builds, with opposing evidence contrasted and a table wherever several studies share dimensions. Every empirical bullet cited; numbers with intervals; primary studies for findings, reviews for consensus.

### 6. Format and check

`scripts/format_references.py --ledger sources.json --draft review_draft.md --style bracket` — with no `--out`, it prints the finished review to stdout. It renders each citation as an `Author 2026` link to its DOI, builds the sources block from the verified Crossref metadata, and refuses to run if any key is unknown or unverified. Run the quality gate in `references/writing-guide.md`, then **write that text as your reply**. Pass `--out` only when the user asked for a file.

### 7. Create the requested media

Skip this step in small, medium, and large/big modes. In image or mindmap mode, follow `references/media-modes.md` and build the visual from the final verified synthesis—not from preliminary search impressions. Read the visual audit in `references/figure-reference-analysis.md`, the journal-grade system in `references/figure-style-system.md`, and the caption contract in `references/figure-captions.md`; choose a style profile and figure archetype, record the evidence and exact copy in a figure-spec JSON, and generate the prompt with `scripts/build_figure_prompt.py` as specified in `references/image-prompt-guide.md`. Use `render_context: article` for a figure inserted beside a caption and `standalone` only when the pixels must carry their own compact title. When a capable image-generation model is available, use it to render the complete figure end to end, including all in-figure labels, callouts, values, legends, and essential definitions; use deterministic SVG or another vector renderer only when image generation is unavailable or the generated result cannot pass QA. Image-mode illustrations must be self-explanatory to an educated non-specialist. Give every figure a stable ID, reference it from the relevant body text, and write a caption that matches the review's bullets, prose, or ELI5 register and ends with 2–5 verified ledger citations. `format_references.py` assigns figure numbers, creates cross-links, and rejects missing, uncited, duplicated, broken, or unreferenced figures. Inspect the defined Arial typography, every rendered word and number, scientific content, clipping, visual balance, caption, and misleading emphasis. Display it in the reply with useful alt text.

## Rules that do not bend

- **Peer-reviewed literature only.** No preprints, blogs, news, or grey literature as evidence. Search eligibility and Crossref type are useful proxies, not a universal peer-review registry; check the venue or article when status is ambiguous, especially for conference proceedings and unfamiliar journals. If a preprint is the only source for something important, it may be mentioned once, labelled "(preprint, not peer reviewed)", and never load-bearing. Retracted papers are cited only to say they were retracted.
- **Never claim a check you did not perform.** "Verified" means the DOI resolved in Crossref; title, year, and source type matched; and Crossref's publisher/Retraction Watch update metadata showed no retraction signal. If Crossref is unavailable, verification is incomplete and the citation does not pass. OpenAlex search availability is irrelevant to this check.
- **No citation from memory.** If you remember a paper, find it with the search script and verify it; if it cannot be found, it does not exist for this review. This applies to "classic" papers too.
- **Read before you cite.** Abstract minimum; full text for anything the argument leans on.
- **Represent the whole literature, not the convenient part.** If studies disagree, say so and say why they might. If the best evidence is weak, say the evidence is weak. A review that only tells one side is advocacy.
- **Keep the story and the evidence distinct.** Findings are attributed ("the MYRIAD trial found …"); synthesis is signposted ("taken together, …"); speculation is labelled as such.
- **Never hand back a file instead of an answer.** The review lives in the reply. A file is an extra only when requested or when image/mindmap mode requires the generated media artifact.
- **The sources block is the audit trail.** Reviews carry no methods section; resolvable DOIs are what make the work checkable. Say nothing when verification completes cleanly. Verification failures are fixed or removed before writing, never decorated with warning symbols in the finished review.
- **Numbers over adjectives.** Effect sizes, intervals, sample sizes, and absolute risks where the sources give them; "significant" on its own is not a result.

## Bundled resources

- `scripts/find_papers.py` — paginated OpenAlex + PubMed search, database-specific queries, automatic audit logging, explicit publication-eligibility filtering, and OpenAlex citation-graph traversal.
- `scripts/verify_citations.py` — Crossref bibliographic and retraction verification using publisher and integrated Retraction Watch update metadata; hard stop on a failure.
- `scripts/fetch_fulltext.py` — open-access full text via Europe PMC, as plain text.
- `scripts/format_references.py` — resolves `[@key]` citations, builds the reference list (Vancouver / APA / Nature).
- `scripts/export_review.py` and `scripts/weasyprint_export.py` — canonical browser-free, atomic journal-styled PDF export plus the separate HTML-only export.
- `scripts/qa_review_pdf.py` — mandatory structural and independent Poppler raster QA for every delivered PDF.
- `requirements-pdf.txt` — pinned PDF export and QA packages; the exporter separately verifies the native print engine and canonical Charter/Helvetica Neue font resolution.
- `scripts/build_figure_prompt.py` — composes an end-to-end ImageGen prompt from a structured evidence specification, a reusable journal-style profile, and a figure archetype.
- `scripts/download_figure_references.py` — downloads the official-source visual-analysis corpus to an explicit private directory and records provenance, dimensions, hashes, and byte counts; source pixels are never bundled.
- `references/no-script-fallback.md` — the tool-only pipeline for sandboxes with no Python network access (claude.ai); read this whenever Step 0 fails.
- `references/sizes.md` — what small, medium, and large mean for scope, search depth, structure, and effort.
- `references/search-playbook.md` — generating angles, building queries, stopping rules, coverage checks, field notes.
- `references/evidence-weighing.md` — how to judge and describe the strength of what you read.
- `references/writing-guide.md` — structures by size, paragraph craft, evidence language, tables, the methods box, the quality gate.
- `references/citation-rules.md` — keys, styles, in-text conventions, what may and may not be cited.
- `references/media-modes.md` — explicit-only image and mindmap mode workflow, visual grammar, rendering, captions, and QA.
- `references/figure-style-system.md` — defined Arial typography, Nature-inspired visual grammar, style selection, and adaptation boundaries.
- `references/figure-reference-analysis.md` and `references/nature-figure-corpus.json` — the 21-figure official-source visual audit and reproducible manifest behind the style profiles; downloaded pixels remain private analysis inputs.
- `references/figure-captions.md` — stable figure IDs, automatic numbering, body cross-references, style-matched caption forms, verified caption citations, and no-script fallback syntax.
- `references/image-prompt-guide.md` — modular prompt specification, iteration protocol, and acceptance contract.
- `references/figure-style-presets.json` and `references/figure-archetypes.json` — machine-readable style and composition modules used by the prompt builder.
