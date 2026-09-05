---
name: grounded
description: Produce source-grounded scientific narrative reviews, or audit the claims and references of a supplied draft, using live literature discovery, verified bibliographic records, independent claim checking, and evidence receipts. Supports chat, journal PDFs, and explicitly requested experimental slide decks.
---

# Grounded

Answer the research question with a calibrated synthesis of peer-reviewed evidence. Find every citation through live search, verify its identity, read its source text, and independently check the assertions made from it. Quote receipts establish attribution; outcome certainty establishes how much confidence the evidence deserves. Neither guarantees a conclusion is true.

## Route the request

- **Review:** preserve the user's choices. Infer missing dimensions from the request; otherwise use medium, popsci, journal PDF. Start work without a size/style/format question. Ask only if ambiguity would materially change the research question, audience, or deliverable.
- **Draft check:** audit the supplied text; do not replace it with a new review. Follow `references/draft-check.md`. Unsupported claims and unresolved sources are findings, not reasons to suppress the report.
- **Slides:** only when explicitly requested. Read `references/deck-guide.md` and the slides section of `references/output-formats.md`. Slides remain experimental and lack assertion receipts; disclose that limitation. Never describe a deck as having the written-review audit.

Keep one case directory with the ledger, search manifest, reading notes and authenticated texts, synthesis, evidence assessment, draft, evidence store, and audit. Preserve failed attempts as audit history. For multiple journal reviews, also read `references/production-workflow.md`.

Budgets come from `scripts/review_config.py`; the generated table is `references/budgets.md`. Size controls scope and length, not a quota of references. Never include an irrelevant paper to hit a count. Use the existing documented-saturation override when a thin field cannot meet search or full-text targets.

## 1. Establish access and scope

Check literature API access before drafting:

```bash
python3 -c "import urllib.request;print(urllib.request.urlopen('https://api.crossref.org/works/10.1136/bmj.n71',timeout=15).status)"
```

On failure, diagnose connectivity, credentials, rate limits, and available supported access paths. Do not assume capabilities from the host's product name. If required verification remains unavailable, report the actual blocker; do not present unverified evidence as verified.

Record the question, population/model, comparison, outcomes, inclusion/exclusion boundaries, and review type before searching. Default to a **narrative review**; use systematic-review terminology only when protocol, search, and screening methods justify it.

## 2. Discover and read

Read `references/search-playbook.md`. Search reviews, primary evidence, recent work, and contrary/null findings with `scripts/find_papers.py`; use stable angle IDs and funnel lanes. Chase central papers for medium and large reviews. Run `scripts/audit_search.py search-manifest.json --size <size>`.

A contrary/null search must complete at every size. Finding disagreement is not required: report that none was found within the searched scope when that is what happened. Failed calls are not saturation.

Read every cited abstract and obtain full text for load-bearing claims. Save full texts under ledger keys and record design/sample, result, limitation, and synthesis use in notes. Run `scripts/audit_fulltexts.py` as specified in `references/quality-gates.md`. Missing text limits what may be claimed; never guess inaccessible methods or results.

Run `scripts/verify_citations.py --ledger sources.json`. Peer-review eligibility, bibliographic identity, integrity screening, and text access are separate checks. Crossref's absence of an integrity signal means **no signal found in the queried data as of the check date**, not proof that no correction or concern exists; inspect publisher notices for load-bearing sources and recorded corrections.

## 3. Assess and synthesize

Read `references/evidence-weighing.md` and `references/synthesis-guide.md`. Write atomic, calibrated claims in `synthesis.md`, with source keys, verbatim quotes, boundaries, contrary evidence if found, dependencies, and exact quantities.

Create `evidence-assessment.json` following `references/evidence-assessment.md`. For every synthesis claim, record outcome certainty and reasons across risk of bias, inconsistency, indirectness, imprecision, and publication bias. Group publications from the same study and record overlap between reviews. Unknown overlap cannot count as independent corroboration. These are structured judgments, not automatically certified GRADE ratings.

```bash
python3 scripts/verify_claims.py seed --ledger sources.json --evidence evidence/ --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py synthesis-check --synthesis synthesis.md --ledger sources.json --evidence evidence/ --assessment evidence-assessment.json --report synthesis-check.json
```

Fix failed evidence checks before drafting. Derived arithmetic must be explicit and reproducible; never change units or convert an association into causation merely to simplify prose.

## 4. Write and produce the selected format

Read `references/writing-guide.md` and only the selected `style-scientific.md`, `style-popsci.md`, `style-bullets.md`, or `style-eli5.md`. Compose from the synthesis; if the argument changes, update the synthesis and assessment first. Cite claims with ledger keys, then use `scripts/format_references.py` and `scripts/validate_review.py` as specified in `references/quality-gates.md`.

Include a compact scope/methods disclosure: narrative/systematic status, search date, databases, boundaries, and material access limitations. Keep it separate from the main explanation. Findings must distinguish text access, source support, and evidence certainty.

For PDF or slides, read the selected section in `references/output-formats.md` and its linked media contracts. Plan a review-wide mix of explanatory illustrations and quantitative plots in every style; discover the actual image tools, including deferred tools, before claiming image generation is unavailable. Use the available image generator for illustrations and deterministic plots for exact quantities. Preserve the canonical renderer, figure provenance, and visual QA. Inline chat needs no media workflow. Figures and captions must be finished before the written-review assertion audit.

## 5. Independently audit all assertions

Follow `references/claim-verification.md`. Use a fresh independent judge. It must qualify on the unlabelled, multi-domain benchmark; gold answers stay outside its context. Require complete coverage, at least 80% verdict agreement, and zero false acceptance on the supplied qualification set. The older creatine benchmark is additional calibration, not sufficient qualification.

```bash
python3 scripts/verify_claims.py extract --review review.md --ledger sources.json --synthesis synthesis.md --assessment evidence-assessment.json --audit claims_audit.json
python3 scripts/verify_claims.py fetch --audit claims_audit.json --evidence evidence/ --ledger sources.json --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py packets --audit claims_audit.json --evidence evidence/ --blind
```

The inventory includes uncited text, headings, summaries, table cells and captions. The independent judge classifies each uncited item as factual, interpretation with factual basis IDs, nonfactual with a reason, or document-local artifact evidence with inspected file hashes and a substantive reason. Artifact evidence is restricted to local provenance or depicted geometry, never scientific factual claims. A factual item without evidence cannot ship. Citation-free abstracts and summaries must map their assertions to checked factual claims, not disappear from the audit.

Judge source support per assertion element. A partial source may ship only if other evidence covers the remainder; every element must be supported. Never drop a citation while leaving its unsupported assertion behind. Repair the prose or evidence, re-extract, and re-adjudicate changed assertions.

```bash
python3 scripts/verify_claims.py check --audit claims_audit.json --evidence evidence/ --summary claims_summary.json --strict
python3 scripts/verify_claims.py receipts --audit claims_audit.json --review review.md
```

Receipts, export, and PDF QA bind the exact assertion inventory and evidence versions to the checked audit. Legacy audits must be re-extracted and checked. Modifying claims, classifications, source assignments, or saved evidence invalidates the release. An audit hash establishes consistency, not independence or truth.

## 6. Deliver

Write the review in chat; deliver any requested PDF and the receipts alongside it. State the source-access split and the outcome certainty honestly. For PDF, run the mandatory release QA and inspect every rendered page before delivery. Follow `references/output-formats.md` for the export command and lineage files.

Preserve the audit inputs for inspection. Do not claim live checks, independent judgment, source access, or successful QA that were not performed.
