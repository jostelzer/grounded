# Running without the scripts (sandboxed environments)

Some environments — claude.ai among them — run Python in a sandbox with **no outbound network access**. The scripts in `scripts/` will fail there with connection errors. This does **not** mean the review has to be written on unverified citations, because the web-fetch tool runs outside that sandbox and can reach the same APIs. This file gives the tool-only equivalent of every pipeline step.

Verified working through a fetch tool: `api.crossref.org`, `api.openalex.org`, `eutils.ncbi.nlm.nih.gov`, `www.ebi.ac.uk/europepmc`.

## Step 0: decide which path you are on

Before searching, run this once:

```bash
python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.crossref.org/works/10.1136/bmj.n71',timeout=15).status)"
```

- Prints `200` → **Path A**: use the scripts as SKILL.md describes.
- Any error (URLError, timeout, DNS failure, no `python3`) → **Path B**: this file.

Do not discover this halfway through. Checking costs one command; finding out after drafting costs the whole citation apparatus.

## Path B: the tool-only pipeline

The ledger is now a markdown table you maintain in `notes.md` (or in your working context if there is no filesystem). Same fields, same discipline: nothing gets cited that has not been through verification. The finished review is still written **in the reply**, never saved as a file unless the user asks.

### B1. Search

**OpenAlex** (all fields, relevance-ranked). Fetch the first page with a cursor:

```
https://api.openalex.org/works?search=YOUR+OPENALEX_QUERY&filter=type:article|review,is_paratext:false,from_publication_date:2015-01-01&per_page=100&cursor=*&select=doi,title,authorships,publication_year,cited_by_count,primary_location,type,is_retracted,abstract_inverted_index&api_key=YOUR_OPENALEX_API_KEY
```

Ask the fetch prompt for the results plus `meta.count` and `meta.next_cursor`. Follow `next_cursor` until you reach the planned limit or it becomes null; do not infer saturation from the first page. Record title, DOI, year, journal, citation count, type, `is_retracted`, and abstract. Drop `from_publication_date` for foundational work; add `&sort=-cited_by_count` for the most-cited pass. Use a query written for OpenAlex, not PubMed field tags.

**PubMed** (biomedical). Two steps:

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=YOUR+PUBMED_QUERY&retstart=0&retmax=100&retmode=json&sort=relevance
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=PMID1,PMID2,PMID3&retmode=xml
```

Ask the first fetch for `count` as well as the PMID list. Repeat it with `retstart=100`, `200`, … until the planned limit or count is reached, fetching each PMID batch with the second URL. Extract title, journal, year, DOI, abstract, and publication types. Exclude editorials, letters, comments, news, corrections/retraction notices, and records without an eligible research/review/guideline publication type. Journal/index inclusion is not proof of peer review; confirm ambiguous venues manually.

Use the regular web-search tool only to *discover* what something is called or to locate a paper whose title you know. Never cite from a search-result snippet or a publisher web page — everything must come back through the API records above.

Run the same angle coverage as `search-playbook.md`: reviews first, then primary studies, then most-cited, then most-recent, then an explicit contradiction pass.

For citation chasing, fetch each central OpenAlex work and read its `referenced_works` for backward links. For forward links, page through `https://api.openalex.org/works?filter=cites:OPENALEX_ID&sort=-cited_by_count&per_page=100&cursor=*&api_key=YOUR_OPENALEX_API_KEY`. Add accepted candidates to the ledger with seed and direction. Because the fallback has no script to write it, maintain the same `search_log.md` columns manually.

### B2. Read

Open-access full text, Europe PMC:

```
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:%22<doi>%22&format=json&resultType=lite
https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML
```

The first gives the PMCID if an open-access full text exists; the second returns the text. If neither works, read the abstract from the API record only. Never infer methods detail you did not read.

### B3. Verify — batched, and non-negotiable

Crossref accepts repeated DOI filters, so several records can be checked per fetch. Do not add a restrictive `select`: the complete records are needed because retraction metadata appears in `updated-by` and `update-to`.

**Crossref, up to ~20 DOIs per call** (registration record, canonical metadata, and retraction updates):

```
https://api.crossref.org/works?filter=doi:DOI1,doi:DOI2,doi:DOI3&rows=20
```

For every cited DOI, check all of the following in its Crossref record:

1. It appears in the Crossref response (absent → the DOI does not exist → remove the citation).
2. Crossref `type` is `journal-article` (or a knowingly-accepted type per `citation-rules.md`).
3. The Crossref title matches the title you recorded (a wrong-DOI error shows up here).
4. The year matches within one.

5. `updated-by` contains no entry whose `type` or `label` begins with `retract` (this field marks an original work that was later retracted).
6. `update-to` contains no entry whose `type` or `label` begins with `retract` (this field marks a retraction notice and points to the affected work).

The update entry's `source` may be `publisher` or `retraction-watch`; both are hard retraction signals. As a defensive fallback, also reject records whose title clearly identifies them as a retraction notice (for example, “Retraction to …”) even if an old deposit lacks the update relation. Do not reject ordinary papers merely because their titles discuss retractions.

**A DOI missing from the batch response is a failure, not an omission.** Re-request it singly to be sure; if it is still absent, the paper does not exist as cited — delete it and any claim resting on it.

### B4. Format references by transcription

Build each reference entry from the Crossref response you just fetched — authors, title, journal, year, volume, pages — transcribing the returned values, never recalling them. Follow the style layouts in `citation-rules.md`. In the chat review, put each author–year DOI link immediately after its supported claim and before terminal punctuation: `claim [Author 2026](DOI).`, never `claim. [Author 2026](DOI)` and never a citation-led sentence. Then check: the number of entries equals the number of distinct cited keys, and every entry ends with its DOI.

If a Crossref record genuinely lacks volume or pages (common for online-first and article-number journals), give what exists plus the DOI and leave the rest out. Do not invent a volume to make an entry look complete.

### B5. Figures when local scripts are unavailable

The evidence boundary and `figure-generation-contract.md` still apply. State
the reader takeaway, must-show elements, evidence boundary, and intended eye
path before choosing a layout. For every non-quantitative figure, write three
detailed concepts, score them for clarity, simplicity, completeness, elegance,
and intuitiveness, and expose only the winner to a capable built-in image generator. Declare a familiar visual starting point and the one plain-language
sentence a non-specialist should be able to explain back. Keep
in-pixel text to essential short labels. Use deterministic rendering only for a
polished plot of verified known numbers. Inspect what the selected pixels
actually communicate; if meaning or flow is unclear, record the issue and edit
or regenerate. The final image must make the starting point visible, define or
replace all necessary jargon, and be explainable without its caption. A failed review cannot be the final candidate. Use uppercase
`A`–`D` for distinct sections in every style and connect concise explanatory
callouts to exact targets with thin leader lines when needed. Never resize width
and height independently: circles remain circular and glyphs keep their natural
proportions.

Maintain the figure spec, prompt, inspection, and provenance as working records
even when the scripts cannot run. Inspect the selected image at original and
delivery size and reject weak composition, generic/cheap styling, low
explanatory value, unclear information flow, incorrect science or copy, and any
stretched shape or lettering. If the environment
cannot create, inspect, and preserve a real image artifact—or cannot produce a
PDF whose figure aspect can be checked—deliver the verified written review and
say in one sentence that the visual/PDF could not be generated. Never claim the
scripted quality gates or matrix check passed when they were unavailable.

### B6. Multiple-review production without the stage script

For two or more journal reviews, preserve the four boundaries in
`production-workflow.md` manually even though `audit_production.py` cannot run.
Keep every case isolated. Freeze and inspect evidence plus `synthesis.md` before
drafting; complete the selected-style and visual-job checks before generating
figures; inspect every figure at the physical width implied by the frozen PDF
height cap; and build the complete PDF once with at most one ordinary repair.
Record every unresolved issue and warning at its owning stage. One to three
primary labels drive phone QA, supporting labels stay at publication scale, and
definitions remain in captions. A manual check is reported as manual—never as a
passing scripted gate.

## The honesty rules that matter most here

These exist because the tempting failure mode is to *quietly downgrade* what "verified" means.

- **Name the check accurately.** Confirming that a publisher page or index listing exists is not verification. Crossref verification establishes DOI identity and canonical metadata and checks publisher plus integrated Retraction Watch update records.
- **Do not turn a service outage into a source warning.** If Crossref cannot be reached, the check is incomplete; retry or omit the source. Do not add ⚠️ or other marks beside entries and present them as verified.
- **Keep discovery separate from verification.** OpenAlex may supply candidate papers, abstracts, and discovery-time flags, but it is not queried by the verification step and its availability is never a reason for a reader-facing note.
- **Incomplete bibliographic detail is a defect, not a footnote.** If you cannot get full metadata for a reference, either fetch it singly until you can, or drop the reference.
- **If neither path is available** — no scripts and no working fetch tool — you cannot produce a review to this skill's standard. Say so plainly and offer the alternatives: write it in an environment that has network access, or produce an explicitly unverified draft clearly labelled as such, with a list of DOIs the user must resolve themselves. Do not deliver something that reads as verified when it is not. Handing the user the verification job while presenting a finished-looking review is the one outcome this skill exists to prevent.

## Reporting it (there is no methods section)

Reviews carry no "how this was produced" section. When every cited DOI matched and Crossref returned no publisher or Retraction Watch retraction relation, say nothing about verification; the resolvable DOI sources block is the audit trail. If Crossref verification fails or returns a retraction signal, remove the affected citation before delivering the review.
