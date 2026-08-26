# Scientific Review Skill

An agent skill that writes scientific literature reviews built **only on real, verified, peer-reviewed citations**. Works with any LLM agent that can read files and run Python or fetch URLs — ChatGPT, Claude, and others.

What makes it great:

- **You choose the depth.** One word — `small`, `medium`, `large`, or `image` — scales the same rigorous pipeline from a fast ~500-word answer to a full field survey with 70+ sources, or a review topped with a scientific illustration.
- **Ultra-compact reviews.** No filler: headings that state the finding, bullets that carry effect sizes and confidence intervals, tables where studies line up — the evidence density of a good systematic review at a fraction of the length.
- **Only real, published, cross-referenced science.** Every source comes from a live OpenAlex/PubMed search, every DOI is verified against Crossref (with retraction screening via publisher and Retraction Watch metadata), and the reference list is generated programmatically from the verified records — so every citation resolves, every time.

## What you get

Give it a topic or research question; it returns a compact, evidence-dense review — question, citation-free TL;DR, sections whose headings are the punchlines, bullet bodies with effect sizes and confidence intervals, tables where studies share dimensions, and a sources block with resolvable DOIs.

Example (excerpt from a real small-mode run):

> ## Does creatine improve depressive symptoms?
>
> **TL;DR** — Creatine is promising as a short-term add-on to established depression treatment, but it is not yet a proven antidepressant or stand-alone therapy. The pooled average benefit is smaller than a clinically important change, certainty is very low, and the best signals come from small, population-specific trials.
>
> ### The pooled effect is small and may not be clinically important
>
> - A 2025 meta-analysis (11 placebo-controlled trials; n=1,093) estimated a [standardized mean difference](https://en.wikipedia.org/wiki/Standardized_mean_difference) of −0.34 (95% [confidence interval](https://en.wikipedia.org/wiki/Confidence_interval) −0.68 to −0.00), equivalent to **2.2 points** on the [Hamilton Depression Rating Scale](https://en.wikipedia.org/wiki/Hamilton_Rating_Scale_for_Depression)—below its 3-point minimal important difference. Results varied substantially, bias analyses favoured creatine, and [GRADE](https://en.wikipedia.org/wiki/GRADE_approach) certainty was very low. [Eckert et al. 2025](https://doi.org/10.1017/s0007114525105588)
> - …
>
> **Sources**
>
> **Eckert et al. 2025** Creatine supplementation for treating symptoms of depression: a systematic review and meta-analysis. *British Journal of Nutrition*. https://doi.org/10.1017/s0007114525105588
>
> …

Every in-text citation is itself a link to the paper, every DOI in the sources block resolves, and every cited paper was screened for retraction. Technical terms and abbreviations link to a plain-language explainer on first use, so the compact style stays readable for non-specialists. The full, unedited output is in [`examples/small-creatine-depression.md`](examples/small-creatine-depression.md).

## Sizes and styles

A review has a **size** — `small` (default), `medium`, `large` — and a **style** — `bullets` (default), `prose`, `eli5`. They combine freely: "medium prose review of …", "eli5: …". Say nothing and you get a small bullets review. `image` mode additionally produces an illustration.

| | Small (default) | Medium | Large |
|---|---|---|---|
| Body length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Full texts read | 2–4 load-bearing papers | 8–15 | 25+ |

Styles change only the writing, never the rigour — same searches, same verified sources, same citations. **Prose** writes a narrative article: an abstract, an introduction, thematic sections of flowing paragraphs, and a conclusion — the format the journal-styled PDF export was made for. **ELI5** writes in very simple English, so a reader with no science background follows every sentence. **Image mode** (experimental) combines with any size and style and additionally produces scientific figures built from the verified findings — one at small, up to three at medium, up to five at large. Figures can be mechanism diagrams, evidence maps, timelines, comparisons, quantitative summaries and more. A capable image-generation model renders the complete figure, including all in-figure text, when available; deterministic SVG is the fallback. The modular figure system separates verified evidence, archetype, render context and journal-inspired profile, with Arial defined throughout. Its figure-native rules come from a reproducible analysis of 21 official-source *Nature Reviews Neuroscience* and *Nature Neuroscience* figures: article figures omit poster-like internal titles, use content-led topology and local labels, and reserve pale semantic colour for scientific structures and data. Every figure also has a stable ID, automatic number, clickable body reference, and a caption written in the review's bullets, prose, or ELI5 register with verified citations that enter the normal Sources block. Every result remains self-explanatory to a non-specialist, is placed after the section it supports, and flows automatically into the PDF export. The skill can also check an existing draft's claims and references against the literature.

## Ways to use it

Name the skill in your prompt so it triggers reliably. Every prompt below has actually been run through the skill — each links to its full, unedited output:

**Answer a research question**

> Use the scientific-review skill: does intermittent fasting improve insulin sensitivity?

→ [output](examples/small-intermittent-fasting-insulin.md) · small · 15 verified sources

**Get an overview of a field**

> Use the scientific-review skill, medium mode: what's known about the gut microbiome's role in Parkinson's disease?

→ [output](examples/medium-gut-microbiome-parkinsons.md) · medium · 46 verified sources (three retracted papers caught and excluded during search)

**Explain it in very simple terms**

> Use scientific review skill in ELI5 mode to explain me why clouds are white

→ [output](examples/eli5-why-clouds-are-white.md) · eli5 · 13 verified sources

**Survey a field in depth**

> Make me a large scientific review about benefits of mediterranean diet

→ [output](examples/large-mediterranean-diet.md) · large · 97 verified sources, 13 sections (the retracted original PREDIMED report is excluded and its corrected republication is used)
→ the same review in **prose style**: [markdown](examples/prose-large-mediterranean-diet.md) · [journal-styled PDF](examples/prose-large-mediterranean-diet.pdf)

**Settle a claim you've seen circulating**

> I keep reading that blue light before bed ruins sleep. Use the scientific-review skill — what does the evidence actually show?

→ [output](examples/small-blue-light-sleep.md) · small · 11 verified sources · also available [in prose style](examples/prose-small-blue-light-sleep.md)

**Produce figures**

> Use the scientific-review skill, medium image mode: how do mRNA vaccines work?

→ [output](examples/image-mrna-vaccines.md) · medium image · 45 verified sources plus two end-to-end ImageGen figures and one exact-geometry SVG fallback, all built from reusable evidence specs, archetypes and the Arial-based Nature Neuroscience-inspired system · [illustrated PDF](examples/image-mrna-vaccines.pdf)

Practical notes: unless you say otherwise you get a **small** review (a fast, dense ~500-word answer) — say `medium` or `large` when the question genuinely has many sub-questions or you want field coverage. The review always arrives in the chat itself, not as a file; ask for a file ("save it as markdown") only if you want one. And if the skill can't verify a source, it drops the source rather than citing it — so a thin sources list on a fringe topic is the skill working as intended, not failing.

## How it works

1. **Scope** the question into the angles a thorough reviewer would cover (existing reviews, largest primary studies, mechanism, contradictory findings, harms, methodological critiques, …).
2. **Search** angle by angle via paginated OpenAlex + PubMed queries (`scripts/find_papers.py`), with database-specific syntax, automatic audit logging, explicit publication-type screening, and optional backward/forward citation chasing; preprints are excluded and retractions flagged.
3. **Read** every abstract that might be cited; pull open-access full text (`scripts/fetch_fulltext.py`, Europe PMC) for the load-bearing papers.
4. **Verify** every entry against Crossref (`scripts/verify_citations.py`) — DOI, title, year, article type, and retraction status. A failure is a hard stop: the source is fixed or removed before writing.
5. **Write** the draft citing ledger keys, then render citations and the reference list from the verified metadata (`scripts/format_references.py`), which refuses to run on any unverified key.
6. **Illustrate when requested** from a structured evidence-and-copy specification: `scripts/build_figure_prompt.py` combines a reusable figure archetype, article/standalone render context and Arial-based journal-style profile, then the finished render passes text, data, science, composition and style QA. Stable figure IDs and `{{figure:id}}` tokens let `format_references.py` assign numbers, create clickable references, verify caption sources, and reject incomplete figure blocks. A separate downloader can reproduce the private 21-figure reference corpus used to audit the profiles without bundling copyrighted pixels.

If the agent's Python sandbox has no network access (e.g. ChatGPT's code interpreter, claude.ai), `references/no-script-fallback.md` runs the same pipeline through the agent's web-fetch tool against the same APIs — the verification standard is identical.

## Requirements

- **No pip installs.** The scripts use only the Python 3 standard library. PubMed, Crossref, and Europe PMC require no key; OpenAlex can take `OPENALEX_API_KEY`/`--openalex-api-key` when required by its current access policy.
- Internet access — either from Python or from the agent's web-fetch tool (the fallback path).
- **Optional identity metadata:** `OPENALEX_API_KEY` (or `--openalex-api-key`) and `OPENALEX_MAILTO` (or `--mailto`). When OpenAlex becomes unavailable, completed PubMed searches remain usable and the failure is written to the audit log; Crossref verification is separate.

## Installation

### Claude Code

Clone into your skills directory:

```bash
git clone https://github.com/jostelzer/scientific-review-skill.git ~/.claude/skills/scientific-review
```

Then ask for a review in any session ("give me a scientific review of X"), or scope it to one project by cloning into `.claude/skills/` there instead.

### claude.ai

Download `scientific-review.skill` from the [latest release](https://github.com/jostelzer/scientific-review-skill/releases/latest) and upload it in **Settings → Capabilities → Skills**. Or build the bundle yourself:

```bash
git clone https://github.com/jostelzer/scientific-review-skill.git scientific-review && cd scientific-review && zip -r ../scientific-review.zip . -x '.git/*'
```

### ChatGPT

`SKILL.md` is the operating instructions; the rest are files the agent loads on demand. Two ways to set it up:

**As a Project** (quickest):

1. Download the repo: **Code → Download ZIP** on GitHub (or `git clone`), and unzip it.
2. In ChatGPT, create a new **Project**.
3. Upload `SKILL.md` and every file from `references/` and `scripts/` to the project's files.
4. Set the project instructions to:
   > Follow the workflow in SKILL.md for every review request. Load the referenced files from the project files when SKILL.md points to them.
5. Make sure **Web Search** is available, then ask: *"Use the scientific-review skill: does creatine reduce depressive symptoms?"* — add `medium`, `large`, or `image` to pick a mode.

**As a Custom GPT** (reusable/shareable):

1. **Explore GPTs → Create**, give it a name like "Scientific Review".
2. Paste the full text of `SKILL.md` into the **Instructions** field.
3. Upload all files from `references/` and `scripts/` under **Knowledge**.
4. Enable the **Web Search** and **Code Interpreter** capabilities.
5. Save, then ask it for a review.

Note: ChatGPT's Python sandbox has no internet access, so the skill's built-in network check (Step 0 in `SKILL.md`) detects this and the agent switches to `references/no-script-fallback.md`, which runs the identical search-and-verify pipeline through web browsing against the same OpenAlex/PubMed/Crossref APIs. The verification standard doesn't change — this is the designed path for any sandboxed environment.

### Other agents

Give the agent the folder as a working directory or attached files, use `SKILL.md` as the operating instructions, and keep `references/` and `scripts/` alongside. Any agent that can execute Python **or** fetch URLs can run the full pipeline — for CLI agents (e.g. Codex CLI), clone the repo and add a line to your `AGENTS.md` pointing review requests at `SKILL.md`.

## Repository layout

- `SKILL.md` — the skill: workflow, mode routing, and the rules that do not bend.
- `scripts/` — search (`find_papers.py`), full text (`fetch_fulltext.py`), verification (`verify_citations.py`), reference formatting (`format_references.py`), figure prompt building, and private reference-corpus downloading.
- `references/` — detailed guides loaded as needed: search playbook, evidence weighing, writing guide, citation rules, size tiers, media modes, the 21-figure visual audit and manifest, and the no-network fallback pipeline.
- `examples/` — full, unedited example outputs.
- `scripts/export_review.py` — journal-styled HTML/PDF export (see below).
- `evals/` — evaluation cases used to test the skill.

## Export to PDF

Ask for a PDF ("give me that as a PDF", "make it printable") and the skill typesets the review like a journal article — title block, summary lead, two-column body, hairline-ruled tables, references in small type, live DOI links throughout:

```bash
python3 scripts/export_review.py --in review.md --out review.pdf --pdf
```

`--columns 1` gives a single-column layout, and `--out review.html` exports HTML only (which prints cleanly from any browser). PDF rendering uses headless Chrome/Chromium/Edge or WeasyPrint if one is installed; the script itself stays pure standard library.

## How it's tested

The deterministic standard-library suite covers OpenAlex cursor pagination,
PubMed offset pagination, database-specific query routing, publication-type
filtering, automatic logging, bidirectional citation chasing, figure prompt
framing, stable figure numbering and cross-links, cited caption enforcement,
visual-corpus manifest integrity and downloader validation, and PDF export. Run
`python3 -m unittest discover -s tests -v`.
`evals/evals.json` separately holds review-output evaluation cases across the
modes.

## License

[MIT](LICENSE)
