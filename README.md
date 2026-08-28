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

- **"What happens to your body when you stop taking Ozempic?"** — popsci · medium → [PDF](examples/ozempic-after-stopping.pdf) · [Markdown](examples/ozempic-after-stopping.md) · 31 verified sources · three cited figures · 6-page journal article
- **"Are microplastics actually harming our health?"** — ELI5 · small → [PDF](examples/microplastics-health-eli5.pdf) · [Markdown](examples/microplastics-health-eli5.md) · 14 verified sources · two cited figures · 4-page journal article
- **"Do school smartphone bans improve grades and mental health?"** — bullets · small → [PDF](examples/school-smartphone-bans.pdf) · [Markdown](examples/school-smartphone-bans.md) · 11 verified sources · two cited figures · 3-page journal article
- **"Are seed oils really bad for you?"** — scientific · large → [PDF](examples/seed-oils.pdf) · [Markdown](examples/seed-oils.md) · 70 verified sources · five cited figures · 10-page journal article

It can also audit text you already have:

> Use the grounded skill to check this draft's claims and references against the literature.

## Sizes, styles, formats

Every review has three independent dimensions — combine them freely:

**Size** — how much evidence:

| | small | medium | large |
|---|---|---|---|
| Words | 600–1,000 | 1,500–2,500 | 3,500–6,000 |
| Verified sources | 10–20 | 30–60 | 70–150 |

**Style** — how it's written; the rigour never changes:

- **scientific** (default) — a journal-register article: abstract, thematic sections, effect sizes, comparison tables.
- **popsci** — a magazine feature with a narrative arc, the contrary evidence as the story's turn — every claim still DOI-linked.
- **bullets** — TL;DR, punchline headings, cited bullets.
- **ELI5** — the simplest possible English, one idea per step.

**Format** — how it's delivered:

- **inline chat** (default) — the review is the reply; every citation is a clickable DOI link, every technical term links to a plain-language explainer.
- **journal PDF** — journal typesetting with superscript citations and up to 2/5/8 generator-first, style-matched figures for small/medium/large reviews, each doing a distinct evidence job.
- **slides** (experimental) — a 16:9 deck of standalone cited slides; the skill never offers it, you have to ask.

## Installation

**Claude Code, Codex, or any CLI agent** — just tell your agent:

> Install the agent skill from https://github.com/jostelzer/grounded

(For Claude Code that means cloning the repo into `~/.claude/skills/grounded`, or into a project's `.claude/skills/`.)

**claude.ai** — download `grounded.skill` from the [latest release](https://github.com/jostelzer/grounded/releases/latest) and upload it in **Settings → Capabilities → Skills**.

**Other agents** — give the agent the repo folder, use `SKILL.md` as the operating instructions, and keep `references/` and `scripts/` alongside. Any agent that can run Python **or** fetch URLs can run the full pipeline.

## Under the hood

The model does the reading and writing; deterministic scripts do the searching, verification, and rendering. One pipeline, every time:

1. **Scope** — the question is split into the angles a thorough reviewer would cover: existing reviews, largest primary studies, mechanism, contrary and null findings, harms, populations, recent work.
2. **Search** — `find_papers.py` cursor-pages OpenAlex and offset-pages PubMed angle by angle, writing every query to an auditable search manifest; central papers get citation-chased in both directions. Preprints are excluded at the gate.
3. **Read** — every abstract that might be cited; open-access full texts (Europe PMC) for the load-bearing papers, behind an authenticity audit that rejects paywall stubs and challenge pages.
4. **Verify** — `verify_citations.py` checks every DOI against Crossref: title, year, article type, and integrity status — retractions, withdrawals, removals, and expressions of concern via publisher and Retraction Watch update metadata. A failure is a hard stop: the source is fixed or dropped before a word is written. A thin source list on a fringe topic is the skill working, not failing.
5. **Synthesize, write & validate** — the verified evidence is first distilled into a style-neutral claims ledger (every claim with its strength, exact numbers, contrary evidence, and boundaries); the styled review is then composed from those claims, citing ledger keys, never remembered references. Citations and the reference list are generated from the verified records, and a deterministic validator checks structure, citation placement, DOI parity, and figure contracts before delivery.
6. **Render** — conceptual visuals use a capable built-in image generator by default, with rich scientific/popsci/bullets/ELI5 art direction and all exact text rendered directly in the finished image. The first candidate may ship when it passes; targeted edits or alternate candidates are conditional, while deterministic overlays are a documented last resort. Visual-quality gates reject generic or cheap-looking output. The journal PDF is typeset with pinned WeasyPrint, then QA independently proves figures were not stretched and re-rasterizes every page with Poppler.
7. **Audit** (on request) — `verify_claims.py` re-checks each cited sentence against the source's own text. Every verdict must carry a verbatim quote that the checker string-matches against the stored evidence; a quote it can't find rejects the verdict, and a numeric claim must have its number inside the quote.

No network in the agent's Python sandbox (ChatGPT's interpreter, claude.ai)? The same pipeline runs through the agent's web-fetch tool against the same APIs — the verification standard doesn't change.

## License

[MIT](LICENSE)
