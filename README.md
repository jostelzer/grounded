# Scientific Review Skill

An agent skill that writes scientific literature reviews built **only on real, verified, peer-reviewed citations**. Works with Claude (Claude Code, claude.ai), ChatGPT, and any LLM agent that can read files and run Python or fetch URLs.

The core problem this skill solves: LLMs fabricate references. Here, **no citation is ever recalled from memory** — every source comes from a live search of OpenAlex and PubMed, every DOI is verified against Crossref (including retraction screening via publisher and Retraction Watch update metadata), and the reference list is generated programmatically from the verified records. A citation that cannot be found and verified does not exist for the review.

## What you get

Give it a topic or research question; it returns a compact, evidence-dense review — question, citation-free TL;DR, sections whose headings are the punchlines, bullet bodies with effect sizes and confidence intervals, tables where studies share dimensions, and a sources block with resolvable DOIs.

Example (excerpt from a real small-mode run):

> ## Does creatine supplementation reduce depressive symptoms?
>
> **TL;DR** — Possibly, as an add-on to an antidepressant or to CBT, but the effect is small, the trials are few and tiny, and the only meta-analysis rates the evidence very low quality and warns the true effect may be nothing. Cheap and safe enough to try alongside real treatment; nowhere near good enough to replace one.
>
> ### The pooled effect is small, uncertain, and below what a patient would notice
>
> - Across 11 randomised trials (n=1,093), creatine beat placebo by SMD **−0.34** (95% CI −0.68 to −0.00) — about **2.2 points** on the 17-item Hamilton scale, under the 3.0-point minimal important difference; I² = 71.3%, GRADE **very low** [Eckert et al. 2025].
> - …
>
> **Sources**
>
> **[Eckert et al. 2025]** Creatine supplementation for treating symptoms of depression: a systematic review and meta-analysis. *British Journal of Nutrition*. https://doi.org/10.1017/s0007114525105588
>
> …

Every DOI in the sources block resolves, and every cited paper was screened for retraction.

## Modes and sizes

Four modes: **small**, **medium**, **large**, and **image**. Name one in your request ("medium review of …", "image mode: …") or say nothing and get small.

| | Small (default) | Medium | Large |
|---|---|---|---|
| Body length | 350–700 words | 900–1,600 words | 2,000–4,000 words |
| Sections | 3–5 | 6–9 | 10–15 |
| Sources | 10–20 | 30–60 | 70–150 |
| Full texts read | 2–4 load-bearing papers | 8–15 | 25+ |

**Image mode** (experimental) runs the small pipeline and then additionally produces one scientific illustration built from the verified findings — self-explanatory to an educated non-specialist, with a glossary for every abbreviation. The skill can also check an existing draft's claims and references against the literature.

## How it works

1. **Scope** the question into the angles a thorough reviewer would cover (existing reviews, largest primary studies, mechanism, contradictory findings, harms, methodological critiques, …).
2. **Search** angle by angle via OpenAlex + PubMed (`scripts/find_papers.py`), merging hits into a source ledger; preprints excluded, retractions flagged.
3. **Read** every abstract that might be cited; pull open-access full text (`scripts/fetch_fulltext.py`, Europe PMC) for the load-bearing papers.
4. **Verify** every entry against Crossref (`scripts/verify_citations.py`) — DOI, title, year, article type, and retraction status. A failure is a hard stop: the source is fixed or removed before writing.
5. **Write** the draft citing ledger keys, then render citations and the reference list from the verified metadata (`scripts/format_references.py`), which refuses to run on any unverified key.

If the agent's Python sandbox has no network access (e.g. claude.ai), `references/no-script-fallback.md` runs the same pipeline through the agent's web-fetch tool against the same APIs — the verification standard is identical.

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

Zip the folder and upload it as a skill in **Settings → Capabilities → Skills**:

```bash
git clone https://github.com/jostelzer/scientific-review-skill.git scientific-review && cd scientific-review && zip -r ../scientific-review.zip . -x '.git/*'
```

### ChatGPT

Nothing in the skill is Claude-specific — `SKILL.md` is the operating instructions, and the rest are files the agent loads on demand. Two ways to set it up:

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

One expected difference from Claude Code: ChatGPT's Python sandbox has no internet access, so the skill's built-in network check (Step 0 in `SKILL.md`) fails and the agent switches to `references/no-script-fallback.md`, which runs the identical search-and-verify pipeline through web browsing against the same OpenAlex/PubMed/Crossref APIs. The verification standard doesn't change — this is the designed path for sandboxed environments, the same one used on claude.ai.

### Other agents

Give the agent the folder as a working directory or attached files, use `SKILL.md` as the operating instructions, and keep `references/` and `scripts/` alongside. Any agent that can execute Python **or** fetch URLs can run the full pipeline — for CLI agents (e.g. Codex CLI), clone the repo and add a line to your `AGENTS.md` pointing review requests at `SKILL.md`.

## Repository layout

- `SKILL.md` — the skill: workflow, mode routing, and the rules that do not bend.
- `scripts/` — search (`find_papers.py`), full text (`fetch_fulltext.py`), verification (`verify_citations.py`), and reference formatting (`format_references.py`).
- `references/` — detailed guides loaded as needed: search playbook, evidence weighing, writing guide, citation rules, size tiers, media modes, and the no-network fallback pipeline.
- `evals/` — evaluation cases used to test the skill.

## License

[MIT](LICENSE)
