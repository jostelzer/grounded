[![Four Grounded reviews rendered as journal PDFs: seed oils, microplastics, Ozempic and school smartphone bans](assets/grounded-banner.png)](#examples)

# Grounded

Ever typed *"look into the scientific evidence on…"* and gotten a beautiful, confident answer?

Two things can be wrong with it, and both are invisible:

1. **The references don't exist.** Papers nobody wrote, DOIs that resolve to nothing, retracted studies quoted as settled fact.
2. **The references exist — but don't say that.** A real paper, correctly formatted, attached to a claim its authors never made.

You can't catch either without checking every reference by hand. Grounded is an agent skill that does exactly that, so you don't have to.

It turns your question into a real literature review with **zero citations from memory**: every source comes from a live OpenAlex/PubMed search, every DOI is verified against Crossref and screened for retractions, and every paper is read before it's cited. On request, it goes one level deeper and audits **every cited sentence against the paper's own text**, anchored to verbatim quotes that a deterministic checker string-matches against the source. A claim the source doesn't back gets downgraded or dropped — never decorated.

**Real papers, actually saying what the review says they say.**

Works with any LLM agent that can read files and run Python or fetch URLs — Claude, ChatGPT and friends.

## Examples

Ask in plain language, naming a size, a style, and an output format — like this:

> Use the grounded skill to tell me: what happens to your body when you stop taking Ozempic? Popsci, medium, journal PDF.

Whatever you leave out, Grounded asks you in one quick question before it starts. Four real runs, unedited:

- **"What happens to your body when you stop taking Ozempic?"** — popsci · medium → [PDF](examples/ozempic-after-stopping.pdf) · [Markdown](examples/ozempic-after-stopping.md) · 30 verified sources · three cited figures · 6-page journal article
- **"Are microplastics actually harming our health?"** — ELI5 · small → [PDF](examples/microplastics-health-eli5.pdf) · [Markdown](examples/microplastics-health-eli5.md) · 10 verified sources · two cited figures · 3-page journal article
- **"Do school smartphone bans improve grades and mental health?"** — bullets · small → [PDF](examples/school-smartphone-bans.pdf) · [Markdown](examples/school-smartphone-bans.md) · 10 verified sources · two cited figures · 2-page journal article
- **"Are seed oils really bad for you?"** — scientific · large → [PDF](examples/seed-oils.pdf) · [Markdown](examples/seed-oils.md) · 75 verified sources · six cited figures · 11-page journal article

It can also audit text you already have:

> Use the grounded skill to check this draft's claims and references against the literature.

## Sizes, styles, formats

Every review has three independent dimensions — combine them freely. The default is **medium · popsci · journal PDF**.

**Size** — how much evidence:

| | small | medium (default) | large |
|---|---|---|---|
| Words | 600–1,000 | 1,500–2,500 | 3,500–6,000 |
| Verified sources | 10–20 | 30–60 | 70–150 |

**Style** — how it's written; the rigour never changes:

- **scientific** — a journal-register article: abstract, thematic sections, effect sizes, comparison tables.
- **popsci** (default) — a magazine feature with a narrative arc, the contrary evidence as the story's turn — every claim still DOI-linked.
- **bullets** — TL;DR, punchline headings, cited bullets.
- **ELI5** — the simplest possible English, one idea per step.

**Format** — how it's delivered:

- **inline chat** — the review is the reply; every citation is a clickable DOI link, every technical term links to a plain-language explainer.
- **journal PDF** (default) — journal typesetting with superscript citations and up to 2/5/8 communication-first, style-matched figures for small/medium/large reviews, each doing a distinct evidence job.
- **slides** (experimental) — a 16:9 deck of standalone cited slides; the skill never offers it, you have to ask.

## Installation

Grounded is a standard [Agent Skill](https://github.com/anthropics/skills) — one `SKILL.md` plus its `references/` and `scripts/`. The same bundle works everywhere; only the delivery differs.

**Claude Code** — install it as a plugin from this repo:

```
/plugin marketplace add jostelzer/grounded
/plugin install grounded@grounded
```

Or clone the repo and point `~/.claude/skills/grounded` (or a project's `.claude/skills/`) at its `skills/grounded/` directory.

**ChatGPT** — download `grounded.zip` from the [latest release](https://github.com/jostelzer/grounded/releases/latest) and upload it under **Skills → Create → Upload from your computer**. (Skills availability depends on your ChatGPT plan.)

**claude.ai** — download `grounded.skill` from the same release and upload it in **Settings → Capabilities → Skills**.

**Codex CLI** — unzip `grounded.zip` into `~/.codex/skills/` (or a project's `.codex/skills/`), then start a new session.

**OpenAI API** — `POST /v1/skills` with `grounded.zip`; the manifest's name and description are read from `SKILL.md` frontmatter.

**Other agents** — give the agent the `skills/grounded/` folder, use `SKILL.md` as the operating instructions, and keep `references/` and `scripts/` alongside. Any agent that can run Python **or** fetch URLs can run the full pipeline.

## Under the hood

The model does the reading and writing; deterministic scripts do the searching, verification, and rendering. One pipeline, every time:

1. **Scope** — the question is split into the angles a thorough reviewer would cover: existing reviews, largest primary studies, mechanism, contrary and null findings, harms, populations, recent work.
2. **Search** — `find_papers.py` cursor-pages OpenAlex and offset-pages PubMed angle by angle, writing every query to an auditable search manifest; central papers get citation-chased in both directions. Preprints are excluded at the gate.
3. **Read** — every abstract that might be cited; open-access full texts (Europe PMC) for the load-bearing papers, behind an authenticity audit that rejects paywall stubs and challenge pages.
4. **Verify** — `verify_citations.py` checks every DOI against Crossref: title, year, article type, and integrity status — retractions, withdrawals, removals, and expressions of concern via publisher and Retraction Watch update metadata. A failure is a hard stop: the source is fixed or dropped before a word is written. A thin source list on a fringe topic is the skill working, not failing.
5. **Synthesize, write & validate** — the verified evidence is first distilled into a style-neutral claims ledger (every claim with its strength, exact numbers, contrary evidence, and boundaries); the styled review is then composed from those claims, citing ledger keys, never remembered references. Citations and the reference list are generated from the verified records, and a deterministic validator checks structure, citation placement, DOI parity, and figure contracts before delivery.
6. **Explain visually, then render** — every figure first states what the reader should understand, where familiar intuition begins, the eye path that builds the idea, and the one sentence a non-specialist should be able to explain back. Non-quantitative figures compare three detailed concepts for clarity, simplicity, completeness, elegance, and intuitiveness; only the winner reaches the image generator. In-pixel copy stays short, distinct sections use uppercase A–D in every writing style, and explanatory callouts point to exact targets when useful. Verified numbers use bespoke deterministic plots instead. After rendering, the agent states what the pixels actually communicate and must revise when the image requires its caption, leaves jargon unexplained, or fails the explain-back test. The journal PDF is typeset with pinned WeasyPrint, then QA independently proves figures and fonts were not stretched and re-rasterizes every page with Poppler.
7. **Audit** (on request) — `verify_claims.py` re-checks each cited sentence against the source's own text. Every verdict must carry a verbatim quote that the checker string-matches against the stored evidence; a quote it can't find rejects the verdict, and a numeric claim must have its number inside the quote.

No network in the agent's Python sandbox (ChatGPT's interpreter, claude.ai)? The same pipeline runs through the agent's web-fetch tool against the same APIs — the verification standard doesn't change.

## License

[MIT](LICENSE)
