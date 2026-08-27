# Grounded

Grounded is an agent skill that writes scientific literature reviews built **only on real, verified, peer-reviewed citations**. Every source comes from a live OpenAlex/PubMed search, every DOI is verified against Crossref (including retraction screening), and the reference list is generated programmatically from the verified records — so every citation resolves, every time. It works with any LLM agent that can read files and run Python or fetch URLs.

## Examples

Ask in plain language, naming a size, a style, and an output format. Whatever you leave out, Grounded asks you in one quick question before it starts.

### Answer a research question

> Use the grounded skill in bullet style: does intermittent fasting improve insulin sensitivity?

→ [example output](examples/small-intermittent-fasting-insulin.md)

### Get a journal-styled PDF

> Use the grounded skill, medium scientific, as a journal PDF: how does chronic stress affect the immune system?

→ [example PDF with figures](examples/image-mrna-vaccines.pdf)

### Check a draft

> Use the grounded skill to check this draft's claims and references against the literature.

### Finished reviews

Each example ran through the complete pipeline, with the full Markdown review and its journal-styled PDF:

- **Popsci** — Why do mosquitoes bite some people more than others? → [Markdown](examples/popsci-mosquito-preference.md) · [PDF](examples/popsci-mosquito-preference.pdf) · small · 13 verified sources
- **ELI5** — Why are clouds white, but rain clouds dark? → [Markdown](examples/eli5-why-clouds-are-white.md) · [PDF](examples/eli5-why-clouds-are-white.pdf) · small · 13 verified sources · one cited figure
- **Scientific** — Which Mediterranean-diet benefits are genuinely supported? → [Markdown](examples/prose-large-mediterranean-diet.md) · [PDF](examples/prose-large-mediterranean-diet.pdf) · large · 97 verified sources · four figures (the retracted original PREDIMED report is excluded; its corrected republication is used)

More finished outputs are in [examples/](examples/).

## Sizes and styles

**Size** scales the evidence:

| | Small (default) | Medium | Large |
|---|---|---|---|
| Body length | 600–1,000 words | 1,500–2,500 | 3,500–6,000 |
| Sources | 10–20 | 30–60 | 70–150 |
| Full texts read | 2–4 | 8–15 | 25+ |
| Journal-PDF figures | 1 | up to 3 | up to 5 |
| Slides | 6–8 | 10–15 | 18–25 |

**Style** changes only the writing — same searches, same verified sources, same citations:

- **scientific** (default) — a narrative article in journal register: abstract, introduction, thematic sections with effect sizes, intervals, and comparison tables, conclusion.
- **popsci** — a popular-science magazine feature: honest headline, standfirst, a concrete opening drawn from a real study, narrative sections that build to the contrary evidence as the story's turn, and a kicker — every claim still carrying its checkable DOI link.
- **bullets** — the compact option: TL;DR, punchline headings, cited bullets (runs shorter than the table above).
- **ELI5** — very simple English that starts from something you already know and climbs one idea per step to an answer you could repeat to a friend.

**Format** is the third axis — how the answer is delivered:

- **inline chat** (default) — the review is the reply itself, with every citation a clickable author–year DOI link and technical terms linked to plain-language explainers.
- **journal PDF** — a journal-styled PDF (two-column body, superscript citations, numbered references) that **always includes generated scientific figures** built from the verified evidence: mechanism diagrams, evidence maps, timelines, plotted numbers with intervals.
- **slides** (experimental, hidden by default — the skill never offers it; you have to ask) — say `deck`, `slides`, or `presentation` and the deliverable is a verified 16:9 PDF deck whose every slide stands alone: a full-sentence cited claim plus a generated image that carries the evidence, with live DOI links and evidence grades.

## Installation

**Claude Code, Codex, or any CLI agent** — just tell your agent:

> Install the agent skill from https://github.com/jostelzer/grounded

(For Claude Code that means cloning the repo into `~/.claude/skills/grounded`, or into a project's `.claude/skills/`.)

**claude.ai** — download `grounded.skill` from the [latest release](https://github.com/jostelzer/grounded/releases/latest) and upload it in **Settings → Capabilities → Skills**.

**Other agents** — give the agent the repo folder, use `SKILL.md` as the operating instructions, and keep `references/` and `scripts/` alongside. Any agent that can run Python **or** fetch URLs can run the full pipeline; sandboxes without network access (ChatGPT's code interpreter, claude.ai) automatically switch to a built-in web-fetch fallback with the identical verification standard.

## What makes it great, and how it works

- **Only real, published, cross-referenced science.** Sources come from paginated OpenAlex + PubMed searches run angle by angle (existing reviews, largest primary studies, mechanism, contrary findings, harms, …). Every abstract that might be cited is read; full texts are pulled for the load-bearing papers. Preprints are excluded, and if a source can't be verified it is dropped rather than cited — a thin sources list on a fringe topic is the skill working, not failing.
- **Every citation verified, every time.** Each entry is checked against Crossref — DOI, title, year, article type, and integrity status: retractions, withdrawals, removals, and expressions of concern (via publisher and Retraction Watch metadata), with published corrections noted on the reference. A failure is a hard stop: the source is fixed or removed before writing. No citation is ever recalled from memory.
- **Evidence-led writing in the style you choose.** The draft is written from the verified ledger with a clear throughline, explicit contrasts, numbers with intervals, and tables where studies line up — then a deterministic validator checks structure, citation placement, and DOI parity before delivery.
- **Verified visuals.** Journal-PDF figures and slide images are built only from the verified findings, with exact-text QA on every label and value; the PDF and deck exporters are deterministic, browser-free, and fail closed.
- **Claim-level verification (experimental).** On request, every cited sentence is audited against the source's own text: evidence is fetched tier by tier (full text where available, abstract floor otherwise), and each verdict must carry a verbatim quote that the checker string-matches against the stored evidence — a quote it cannot find is rejected, and a numeric claim needs its number inside the quote. The result is a quote-anchored audit appendix with the evidence tier reported honestly per claim.

## License

[MIT](LICENSE)
