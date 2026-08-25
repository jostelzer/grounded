# Search playbook

The review is only as good as the literature it is built on. This is how to find the right papers, enough of them, from every side.

## 1. Turn the question into angles

Write the angles down before the first search. Each angle becomes a set of queries and, usually, a section of the review.

**For "does X cause / improve / affect Y?"**
1. Existing systematic reviews and meta-analyses (what has already been synthesised, and when)
2. The largest and most rigorous primary studies (RCTs; large cohorts; registered trials)
3. Mechanism — why X would affect Y (lab, animal, physiological, theoretical work)
4. Null, negative, and contradictory results (search with "no effect", "null", "failed to replicate", "not associated")
5. Moderators — population, age, sex, dose, duration, setting, baseline severity
6. Measurement — how Y is measured and whether that drives results
7. Harms, adverse effects, costs, unintended consequences
8. Methodological critiques of the field (bias, confounding, publication bias, small-study effects)
9. History — where the claim came from; the first studies
10. The most recent two years

**For "what is known about X?" (descriptive / mechanistic)**
Definitions and classification; prevalence or occurrence; mechanisms and pathways; methods used to study it; competing models; applications; controversies; open problems.

**For "how does X compare with Z?"**
Head-to-head studies; network meta-analyses; separate evidence bases for each; differences in populations or outcomes that make comparison hard; cost and implementation.

**For social-science, ecology, engineering, or computing questions** the same logic holds: syntheses first, then the strongest primary evidence, then mechanism/theory, then disagreement, then moderators, then methods critique, then the newest work.

## 2. Build queries

`find_papers.py` searches OpenAlex (all fields) and PubMed (biomedical). `--query` sends the same free text to both. Prefer `--openalex-query` and `--pubmed-query` when using database-specific syntax; PubMed tags such as `[tiab]` must not be sent to OpenAlex. Each database is paged independently up to `--limit` records (default 100), and each run is written to `search_log.md` automatically. Rules of thumb:

- **Three to six content words** per query, no Boolean operators needed for OpenAlex; PubMed accepts its own syntax if you want it (`"mindfulness"[tiab] AND adolescen*[tiab]`).
- **Vary vocabulary across queries**: synonyms, the field's own jargon, the outcome named different ways, the intervention's brand or programme names, older terminology.
- **Reviews first**: `--types review` on each angle, so you know what has been synthesised and can cite reviews for consensus and primary studies for specifics.
- **Then primary studies**: add design words ("randomised", "cohort", "trial", "longitudinal", "experiment") to pull the strongest evidence to the top.
- **Then the classics**: `--sort cited` without a date filter to surface foundational papers in OpenAlex. PubMed has no equivalent citation-count sort.
- **Then the newest**: `--from-year <two years ago>` to catch work newer than the latest reviews.
- **Contradiction pass**: queries that name the null or the criticism explicitly; the index does not rank disagreement for you.
- **Label every run with `--angle`** so the ledger shows coverage per angle.
- **Page deeply enough to test saturation**: increase `--limit` rather than treating repeated results in the first page as saturation. `--page-size` controls request batching, not the stopping limit.
- **Give OpenAlex identity metadata**: use `OPENALEX_API_KEY`/`--openalex-api-key` where OpenAlex requires a key, or `OPENALEX_MAILTO`/`--mailto` for courtesy contact metadata. Requests are throttled and retried; a hard OpenAlex failure is logged and PubMed continues.

Use `WebSearch` when you need to discover what a programme, drug, or debate is called, or to locate a specific paper whose title you know — then add it via a `find_papers.py` query so it enters the ledger with a DOI. Never cite from the web page.

## 3. Triage the hits

After each query, the script prints new entries. Skim the titles; use `--abstracts` when titles are ambiguous. For each candidate decide: cite-likely, maybe, irrelevant. Record cite-likely and maybe in `notes.md` with the angle and a one-line reason. Irrelevant hits can stay in the ledger unused; they cost nothing.

Watch the flags: `RETRACTED` is never cited as evidence; `PREPRINT` only appears if you asked for preprints, and is never load-bearing.

## 4. Know when to stop

| Size | Stop when |
|---|---|
| Small | Each angle has 2–5 solid candidates and the last query on it returned mostly known papers |
| Medium | Each angle has 5–12 candidates, the major reviews of the last 10 years are in the ledger, and two consecutive queries per angle add nothing new |
| Large | As medium, plus citation chasing on the 5–10 central papers has been done and the recent-work pass has been run for every angle |

Stopping is about coverage, not count. A medium review with 40 references that span every angle beats one with 80 that all come from two queries.

## 5. Coverage check before writing

Run `find_papers.py --ledger sources.json --show` and read the table against your angle list:

- Does each angle have at least one synthesis and at least one primary study (where such things exist)?
- Is the newest paper from the last 12–24 months? If not, run a recency pass.
- Is there at least one source that disagrees with the emerging story? If not, search harder for it — absence of disagreement in a ledger usually means absence of searching, not absence of disagreement.
- Are the most-cited papers on the topic present? A cited-sort pass tells you.
- Are there sources from more than one research group and more than one country? One group's papers can dominate a search.

## 6. Citation chasing (medium and large)

For each central ledger paper, run `find_papers.py --ledger sources.json --chase <key> --chase-direction both --chase-limit 50`. Backward chasing fetches the seed's references; forward chasing searches works that cite it. Candidates are filtered, deduplicated, and stored with seed/direction provenance. Use `--chase-sort recent` for updates or the default `cited` for influential neighbors. Then search the exact title, distinctive abstract phrases, and `"<main finding> replication"` to catch records that the citation graph misses. For large reviews, do this for the 5–10 central papers.

## 7. When the literature is thin

If searches return little: widen vocabulary; drop the date filter; search adjacent populations or models; look for the topic inside broader reviews; check whether the field uses a different name. If it is genuinely thin, say so in the review — "we identified only N peer-reviewed studies" is a finding — and scale the deliverable accordingly.

## 8. Field notes

- **Biomedicine:** PubMed is essential; OpenAlex adds non-MEDLINE journals and citation counts. Watch for predatory-journal noise in OpenAlex; prefer journals you recognise or that are MEDLINE-indexed.
- **Psychology, education, social science:** OpenAlex covers PsycINFO-indexed journals reasonably; use design terms ("randomized", "longitudinal", "meta-analysis").
- **Ecology, earth science:** OpenAlex; use taxon and system names; meta-analyses use "log response ratio".
- **Computer science, engineering:** enable `--include-conference-papers`; OpenAlex then accepts article records whose source type is `conference`, while Crossref may identify their DOI type as `proceedings-article`. Confirm that the conference uses peer review before citing.
- **Economics:** working papers dominate early; the verifier will flag them as non-journal. Prefer the published version.

## 9. Log everything

`search_log.md` is appended automatically beside `sources.json`. Every row records UTC time, database, method, angle, requested and API query, filters, sort, database-reported total, locally retrieved/accepted/new/updated counts, page count, exclusions, and status. Use `--search-log <path>` to relocate it or `--no-search-log` only for disposable experiments. It stays on disk for auditing and does not appear in the review.
