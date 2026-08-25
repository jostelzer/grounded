# Scientific Review Skill

An agent skill that writes scientific literature reviews built **only on real, verified, peer-reviewed citations**. Works with any LLM agent that can read files and run Python or fetch URLs — ChatGPT, Claude, and others.

What makes it great:

- **You choose the depth.** One word — `small`, `medium`, `large`, or `image` — scales the same rigorous pipeline from a fast ~500-word answer to a full field survey with 70+ sources, or a review topped with a scientific illustration.
- **Ultra-compact reviews.** No filler: headings that state the finding, bullets that carry effect sizes and confidence intervals, tables where studies line up — the evidence density of a good systematic review at a fraction of the length.
- **Only real, published, cross-referenced science.** Every source comes from a live OpenAlex/PubMed search, every DOI is verified against Crossref (with retraction screening via publisher and Retraction Watch metadata), and the reference list is generated programmatically from the verified records — so every citation resolves, every time.

## What you get

Give it a topic or research question; it returns a compact, evidence-dense review — question, citation-free TL;DR, sections whose headings are the punchlines, bullet bodies with effect sizes and confidence intervals, tables where studies share dimensions, and a sources block with resolvable DOIs.

Example (excerpt from a real small-mode run):

> ## Does creatine supplementation reduce depressive symptoms?
>
> **TL;DR** — Possibly, as an add-on to an antidepressant or to CBT, but the effect is small, the trials are few and tiny, and the only meta-analysis rates the evidence very low quality and warns the true effect may be nothing. Cheap and safe enough to try alongside real treatment; nowhere near good enough to replace one.
>
> ### The pooled effect is small, uncertain, and below what a patient would notice
>
> - Across 11 randomised trials (n=1,093), creatine beat placebo by [SMD](https://en.wikipedia.org/wiki/Standardized_mean_difference) **−0.34** (95% [CI](https://en.wikipedia.org/wiki/Confidence_interval) −0.68 to −0.00) — about **2.2 points** on the 17-item [Hamilton scale](https://en.wikipedia.org/wiki/Hamilton_Rating_Scale_for_Depression), under the 3.0-point minimal important difference; [I²](https://en.wikipedia.org/wiki/Study_heterogeneity) = 71.3%, [GRADE](https://en.wikipedia.org/wiki/GRADE_approach) **very low** [Eckert et al. 2025](https://doi.org/10.1017/s0007114525105588).
> - …
>
> **Sources**
>
> **Eckert et al. 2025** Creatine supplementation for treating symptoms of depression: a systematic review and meta-analysis. *British Journal of Nutrition*. https://doi.org/10.1017/s0007114525105588
>
> …

Every in-text citation is itself a link to the paper, every DOI in the sources block resolves, and every cited paper was screened for retraction. Technical terms and abbreviations link to a plain-language explainer on first use, so the compact style stays readable for non-specialists. The full, unedited output is in [`examples/small-creatine-depression.md`](examples/small-creatine-depression.md).

## Modes and sizes

Four modes: **small**, **medium**, **large**, and **image**. Name one in your request ("medium review of …", "image mode: …") or say nothing and get small.

| | Small (default) | Medium | Large |
|---|---|---|---|
| Body length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Full texts read | 2–4 load-bearing papers | 8–15 | 25+ |

**Image mode** (experimental) runs the small pipeline and then additionally produces one scientific illustration built from the verified findings — self-explanatory to an educated non-specialist, with a glossary for every abbreviation. The skill can also check an existing draft's claims and references against the literature.

## Ways to use it

Name the skill in your prompt so it triggers reliably:

**Answer a research question**

> Use the scientific-review skill: does intermittent fasting improve insulin sensitivity?

**Get an overview of a field**

> Use the scientific-review skill, medium mode: what's known about the gut microbiome's role in Parkinson's disease?

**Settle a claim you've seen circulating**

> I keep reading that blue light before bed ruins sleep. Use the scientific-review skill — what does the evidence actually show?

**Produce a figure**

> Use the scientific-review skill in image mode: how do mRNA vaccines work?

Practical notes: unless you say otherwise you get a **small** review (a fast, dense ~500-word answer) — say `medium` or `large` when the question genuinely has many sub-questions or you want field coverage. The review always arrives in the chat itself, not as a file; ask for a file ("save it as markdown") only if you want one. And if the skill can't verify a source, it drops the source rather than citing it — so a thin sources list on a fringe topic is the skill working as intended, not failing.

## How it works

1. **Scope** the question into the angles a thorough reviewer would cover (existing reviews, largest primary studies, mechanism, contradictory findings, harms, methodological critiques, …).
2. **Search** angle by angle via OpenAlex + PubMed (`scripts/find_papers.py`), merging hits into a source ledger; preprints excluded, retractions flagged.
3. **Read** every abstract that might be cited; pull open-access full text (`scripts/fetch_fulltext.py`, Europe PMC) for the load-bearing papers.
4. **Verify** every entry against Crossref (`scripts/verify_citations.py`) — DOI, title, year, article type, and retraction status. A failure is a hard stop: the source is fixed or removed before writing.
5. **Write** the draft citing ledger keys, then render citations and the reference list from the verified metadata (`scripts/format_references.py`), which refuses to run on any unverified key.

If the agent's Python sandbox has no network access (e.g. ChatGPT's code interpreter, claude.ai), `references/no-script-fallback.md` runs the same pipeline through the agent's web-fetch tool against the same APIs — the verification standard is identical.

## Requirements

- **No API keys, no pip installs.** The scripts are pure Python 3 standard library, calling the free public APIs of OpenAlex, PubMed, Crossref, and Europe PMC.
- Internet access — either from Python or from the agent's web-fetch tool (the fallback path).

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
5. Make sure **Web Search** is available, then ask: *"scientific review: does creatine reduce depressive symptoms?"* — add `medium`, `large`, or `image` to pick a mode.

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
- `scripts/` — search (`find_papers.py`), full text (`fetch_fulltext.py`), verification (`verify_citations.py`), and reference formatting (`format_references.py`).
- `references/` — detailed guides loaded as needed: search playbook, evidence weighing, writing guide, citation rules, size tiers, media modes, and the no-network fallback pipeline.
- `examples/` — full, unedited example outputs.
- `evals/` — evaluation cases used to test the skill.

## How it's tested

`evals/evals.json` holds the evaluation cases the skill is developed against: review prompts across the modes, each with an expected-output specification — verified peer-reviewed references in the size-appropriate count, contrary evidence included, and the fixed output format (citation-free TL;DR, punchline headings, cited bullets, DOI-linked sources block). If you change the skill, run these before relying on it.

## License

[MIT](LICENSE)
