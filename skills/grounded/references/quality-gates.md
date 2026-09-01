# Auditable quality gates

These gates are mandatory for an explicitly requested size, a journal PDF (whose
figures are mandatory), or a PDF release. Reviews using the default medium tier retain advisory tier budgets, but
the evidence, citation, and text-hygiene rules never become advisory.

## Search manifest

`find_papers.py` writes `search-manifest.json` beside the ledger. Give every run
a stable `--angle-id` and one funnel lane: `reviews`, `primary`, `foundational`,
`recent`, or `contrary-null`. Failed and rate-limited records remain in the
manifest with `completed: false`; they are audit evidence, not coverage.

```bash
python3 scripts/find_papers.py --ledger sources.json --angle "direct trials" --angle-id direct-trials --lane primary --query "topic outcome randomized trial"
python3 scripts/audit_search.py search-manifest.json --size large
```

Citation chasing uses OpenAlex first and OpenCitations Index/Meta as the default
fallback. A direction counts only when one provider completes it. Large reviews
need both directions for 5–10 central papers. A thin field may use one explicit
JSON override with a substantive `reason`, a non-empty `saturation_evidence`
list, and named `allowed_search_shortfalls`; failed API calls alone are never
saturation.

## Full-text manifest and reading eligibility

Retain each close-read paper in `fulltexts/` under its exact ledger key and give
it one notes entry containing design/sample, result, limitation, and synthesis
use. The audit parses a specific bullet shape from `notes.md` — a list item
opening with the ledger key in backticks, followed by a dash and the note —
and looks for all four signals inside it:

```markdown
- `Sung2014treating` — Design: double-blind placebo-controlled randomised
  trial, 167 infants under 3 months. Result: found no benefit — the probiotic
  group fussed 49 min/day more at 1 month (95% CI 8–90). Limitation: mostly
  emergency-department recruitment. Synthesis use: the key contrary trial and
  the narrative turn.
```

Continuation lines indented under the bullet belong to the same entry. A note
missing any of the four signals leaves its full text uncounted. Then classify
the corpus and write reading evidence back to the ledger:

```bash
python3 scripts/audit_fulltexts.py --ledger sources.json --fulltext-dir fulltexts --notes notes.md --out fulltext-manifest.json --minimum 25 --update-ledger
```

The manifest records media type, extraction method, words, headings, content
hash, title/DOI identity, source, retrieval time, exact note, and status. Only a
distinct `valid_fulltext` with complete notes counts. Challenge pages, access
denials, abstracts, metadata shells, duplicates, and unreadable files do not.
A final citation is eligible only with a nontrivial stored abstract or a valid
full-text record; bibliographic verification, retraction screening, publication
eligibility, and reading evidence remain separate fields and errors.
For a genuinely thin field, pass the same `--thin-literature-override` JSON to
this audit, `audit_search.py`, and `validate_review.py`; it must name
`fulltexts` in `allowed_shortfalls` and carry saturation evidence.

## Strict finished-review validation

For an explicitly named tier, validate the final file with all evidence inputs:

```bash
python3 scripts/validate_review.py review.md --style scientific --size large --strict-tier --ledger sources.json --fulltext-manifest fulltext-manifest.json --report validation.json
```

Add `--image-mode` for journal-PDF reviews, whose figures are mandatory. Strict mode makes word, source, section,
table, and figure-cap ranges plus the counted-full-text minimum hard errors. A
structured thin-literature override may cover only genuine source/full-text shortfalls;
it never excuses short prose, missing sections/tables, or evidence padding.
Mojibake, replacement characters, exposed scaffold labels, late figure
introductions, and uncited figure captions are always hard failures.

Default chat/Markdown citations are DOI-linked author–year labels immediately
after the supported claim and before terminal punctuation: `claim [Author](DOI).`
The formatter repairs a legacy `claim. [@key]` draft, while finished-review
validation rejects punctuation-before-citation and citation-led sentences. A
DOI-only source cell in a comparison table remains valid.

## Figure conformance

The canonical production rules are in `figure-generation-contract.md`; the
inspection and provenance schemas are in
`figure-inspection-contract.md`. Every new figure uses quality contract v3 and
must be audited against its selected raster:

```bash
python3 scripts/qa_figure.py --spec figure.json --image figure.png --inspection figure.inspection.json --provenance figure.provenance.json
```

This gate fails closed on missing or mismatched copy, relationships, route
semantics, concept selection, panel/callout fidelity, anatomy, undeclared
objects, connector meaning, grouping, salience, typography, explanatory value,
information flow, explain-back, quantitative attachment, geometry, aspect
ratio, candidate lineage, or selected-image hash. Manual OCR transcription is
an inspection record, not permission to accept garbled or absent pixels.
Typography has both lower and upper machine gates: publication labels must
clear the 6.5 pt floor, while robust upper glyph height and OCR text-box area
must remain below the poster-dominance ceilings. Phone QA applies only to one to
three declared primary wayfinding labels; supporting labels may require zoom or
the caption and must not be inflated to satisfy the phone view. A labels-hidden
inspection also rejects headline-plus-icons posters and object inventories whose
meaning is carried mainly by text.

Deterministic and composite figures additionally run
`scripts/qa_quantitative_geometry.py` against the independently produced
geometry manifest. The geometry checker must remain independent of renderer
implementation modules so it can detect common-mode mapping errors.

## Figure-feedback generalization gate

When feedback is intended to improve future figures, follow
`figure-feedback-generalization.md`. Abstract the visible defect into a
topic-neutral rule, add the corresponding v3 contract or QA field, and add a
minimal synthetic regression fixture that fails on the defect. Run the focused
tests and the complete suite. Do not create public before/after boards, link
temporary samples from the README, or treat evaluation topics as permanent
templates. A single-example prompt edit or case-local exception is never an
acceptable implementation.

## Immutable PDF lineage

Create only one canonical PDF in the release directory. The exporter manifest
binds the exact review, verified ledger, rebuilt HTML, PDF, and every figure,
spec, saved prompt, visual inspection, and generation provenance. Repeat all
four figure-lineage arguments once per rendered figure; omit them for a
text-only review.

```bash
python3 scripts/export_review.py --in review.md --out review.pdf --pdf --style <scientific|popsci|bullets|eli5> --ledger sources.json --release-manifest release-manifest.json --release vX.Y.Z --compiled-date YYYY-MM-DD --figure-spec figure.json --figure-prompt figure.prompt.txt --figure-inspection figure.inspection.json --figure-provenance figure.provenance.json
python3 scripts/qa_review_pdf.py review.pdf --manifest release-manifest.json --render-dir review-pdf-qa --report pdf-qa.json
```

QA rehashes every input, independently rebuilds the HTML, checks the one-PDF
scope, requires a visible terminal References heading, requires every DOI as
visible reference text and as a URI annotation, applies terminal reference-page
occupancy checks, rasterizes every page, and records exactly one authoritative
render set in the manifest. Before rasterization, it resolves every painted
raster through page and form transformation matrices and fails if the painted
ratio differs from the intrinsic figure ratio or if the axes are sheared. Keep
failed candidates in a case-local audit folder, never beside the canonical PDF.

The journal build keeps author–year links in the source markdown but renders
them as DOI-linked superscript numbers in first-citation order. Each number must
close directly against the preceding supported claim or quotation, after its
punctuation; a citation that opens a sentence, paragraph, bullet, or caption is
a hard exporter failure. The terminal References list uses the same numbers and
order. Inspect this explicitly in the HTML and page rasters as part of PDF QA.
