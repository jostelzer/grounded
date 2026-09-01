# Staged production for multiple journal reviews

Read this reference when one request asks for two or more Grounded journal
reviews. It keeps the quality contract unchanged while preventing four reports
from becoming four long, interleaved histories of search, rewriting, image
generation, and whole-PDF repair.

The unit of work is one case directory and one `production.json`. Cases may run
in parallel after one shared preflight. They never share mutable ledgers,
figure candidates, review files, release directories, or QA render sets.

## Batch topology

The coordinator does only work that is genuinely shared:

1. settle size, style, output format, naming, and the journal figure-height cap;
2. run the network and PDF-runtime preflights once;
3. create isolated case directories and short worker packets;
4. collect compact gate reports rather than polling full working histories;
5. send one independent audit only after every case clears its machine gates.

Each case has one owner through evidence and writing. Each figure may have an
isolated owner, but that owner receives only its visual job, the cited synthesis
claims, the shared figure contract, and its case-local paths. It does not receive
another report's history or invent a new evidence interpretation.

## Stratify work by judgment required

Use deterministic scripts for runtime checks, manifest audits, citation
verification, reference formatting, rendering, and QA. Routine retrieval,
record normalization, and command execution do not benefit from the strongest
reasoning setting. Reserve stronger reasoning for synthesis, difficult evidence
adjudication, the selected style's narrative structure, and the single final
independent audit. An explicit user choice of model or reasoning level always
wins.

Do not assign a general-purpose reviewer to watch exports or repeatedly inspect
unchanged state. Wait on workers in bounded snapshots. A worker that returns a
passing gate report is done; the coordinator reads the report, not its whole
transcript.

## Four gates, in order

### 1. Evidence freeze

Search, verify, close-read, and finish `synthesis.md`. Then set
`evidence.frozen: true` and run:

```bash
python3 scripts/audit_production.py production.json --stage evidence --report production-evidence.json
```

The gate re-runs the search audit, checks the requested full-text minimum,
parses the synthesis contract, verifies its ledger keys, and requires every
warning to be either fixed or accepted with an exact message and a substantive
reason. Do not draft while this gate fails.

After the freeze, a missing source or changed claim is an evidence change, not a
copy edit. Reopen the evidence stage, update the synthesis, and invalidate the
downstream work that depended on it.

### 2. Semantic preflight

Compose the review in its selected register before generating pixels or tuning
PDF layout. Check claim traceability, style structure and voice, citation
locality, first-use term links, numeric density, table fit, and the visual-job
matrix. Then run:

```bash
python3 scripts/audit_production.py production.json --stage semantic --report production-semantic.json
```

The review validator runs against the live review, ledger, and full-text
manifest. The visual plan must begin with exactly one whole-answer synthesis
view; every later job must ask a distinct question and cite synthesis C/P keys.
This is where a scientific abstract, popsci turn, ELI5 staircase, bullet density,
or table boundary is repaired. None of those should first be discovered after
figures or PDF pagination exist.

### 3. Figure set

Freeze `render.figure_max_height_mm` before figure QA. Give each figure owner one
visual job. Keep definitions, axis explanation, and interpretation in the
caption; one to three primary wayfinding labels drive phone QA, while supporting
labels remain at publication scale. Reject poster-like text systems and figures
whose meaning disappears when labels are hidden.

After all case-local figures pass their own communication and pixel checks, run:

```bash
python3 scripts/audit_production.py production.json --stage figures --report production-figures.json
```

This calls `qa_figure.py` directly from the saved spec, image, inspection, and
provenance. It computes the width implied by the frozen journal height cap,
records the image hash and evaluated physical width, and keeps those values for
the release gate. A passing first candidate is valid. The normal local budget is
three authored attempts per figure; exceeding it requires a diagnosed exception
and one bounded next action, never a waiver of figure quality.

`figures.full_set_cycles` normally stays at one. Repair a failed figure locally;
do not regenerate or re-audit every passing figure because one item failed.

### 4. Release

Export only after the semantic and figure gates pass. Run the canonical PDF QA
and inspect every rasterized page and contact sheet. Then run one independent
audit over the compact gate reports and final artifacts. Repair only a named
blocker, rerun its downstream gates, mark the release manual checks, and run:

```bash
python3 scripts/audit_production.py production.json --stage release --report production-release.json
```

The release gate re-validates the current review in strict image mode, rebuilds
and verifies the immutable release lineage, hashes the authoritative page-raster
set, and matches every released figure—in order—against the live figure-QA image
hash and rendered width. A figure checked at 184 mm cannot silently ship at 72
mm. The normal document budget is the initial complete build plus one repair.
More than two full builds requires a diagnosed exception; local copy, figure, or
pagination defects never justify rebuilding unrelated case histories.

Give the auditor the compact production reports, final PDFs, and release
blockers to check—not every search result, candidate image, terminal transcript,
and abandoned PDF. The final release command verifies the post-audit artifacts;
it is the last gate.

## Worker packets

Keep delegated prompts short and stage-bounded. These are packet shapes, not
extra output sections:

- **Evidence owner:** case question, size, case directory, evidence and synthesis
  contracts. “Produce the ledger, search/full-text records, notes, and
  `synthesis.md`; stop after the evidence gate. Do not draft or create media.”
- **Writer:** frozen synthesis, ledger, selected style and size. “Compose and
  validate the review; complete the semantic manual checks and visual-job
  matrix; stop after the semantic gate. Reopen evidence only for a named
  unsupported claim.”
- **Figure owner:** one visual-job record, its C/P entries and ledger keys, route
  contracts, and case-local filenames. “Return one passing figure lineage; do
  not revise prose, other figures, or shared rules.”
- **Release owner:** passing semantic/figure reports and canonical export
  command. “Build once, run PDF QA, repair at most one diagnosed release defect,
  and stop at the release gate.”
- **Independent auditor:** compact gate reports and final artifacts. “Return
  only evidence, writing, figure, or release blockers with their owning layer;
  do not reopen passing work for preference-only variants.”

## `production.json`

Paths are relative to the manifest. Repeat the `visual_jobs` and `figures.items`
records in the same order. `accepted_warnings` uses the exact warning string
printed by the live gate; obsolete or approximate acceptances fail.

```json
{
  "schema_version": 1,
  "case_id": "stable-case-id",
  "size": "small",
  "style": "popsci",
  "output_format": "journal-pdf",
  "render": {
    "figure_max_height_mm": 92
  },
  "evidence": {
    "ledger": "sources.json",
    "search_manifest": "search-manifest.json",
    "fulltext_manifest": "fulltext-manifest.json",
    "synthesis": "synthesis.md",
    "frozen": true,
    "unresolved_issues": [],
    "accepted_warnings": []
  },
  "semantic": {
    "review": "review.md",
    "manual_checks": {
      "claim_traceability": true,
      "selected_style_structure": true,
      "selected_style_voice": true,
      "citation_locality": true,
      "first_use_term_links": true,
      "number_density": true,
      "table_fit": true,
      "visual_job_distinctness": true
    },
    "visual_jobs": [
      {
        "id": "whole-answer",
        "kind": "synthesis",
        "question": "What is the whole evidence-based answer?",
        "evidence_keys": ["C1", "C2", "P1"]
      },
      {
        "id": "decisive-comparison",
        "kind": "comparison",
        "question": "Which comparison changes the conclusion most?",
        "evidence_keys": ["C3", "C4"]
      }
    ],
    "unresolved_issues": [],
    "accepted_warnings": []
  },
  "figures": {
    "items": [
      {
        "job_id": "whole-answer",
        "spec": "whole-answer.figure.json",
        "image": "whole-answer.png",
        "inspection": "whole-answer.inspection.json",
        "provenance": "whole-answer.provenance.json"
      },
      {
        "job_id": "decisive-comparison",
        "spec": "decisive-comparison.figure.json",
        "image": "decisive-comparison.png",
        "inspection": "decisive-comparison.inspection.json",
        "provenance": "decisive-comparison.provenance.json"
      }
    ],
    "full_set_cycles": 1,
    "unresolved_issues": [],
    "accepted_warnings": []
  },
  "release": {
    "manifest": "release-manifest.json",
    "pdf": "review.pdf",
    "full_document_builds": 1,
    "manual_checks": {
      "all_pages_inspected": true,
      "figure_text_checked_at_final_size": true,
      "references_and_links_inspected": true,
      "independent_audit_completed": true
    },
    "unresolved_issues": [],
    "accepted_warnings": []
  }
}
```

When a normal iteration budget is exceeded, add `iteration_exception` beside
the relevant count:

```json
{
  "failure_class": "layout",
  "reason": "The references created a sparse terminal page after one local repair.",
  "next_action": "Adjust only the documented reference-leading lever and rerun release QA."
}
```

Allowed failure classes are `evidence`, `writing`, `figure-meaning`,
`figure-copy`, `layout`, `runtime`, and `external`. An exception explains extra
work; it never converts a failed gate into a pass.
