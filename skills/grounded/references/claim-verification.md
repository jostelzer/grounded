# Independent assertion verification

When agent spawning is available, spawn a fresh judge with only the packets and rubric; do not fork the writer’s context. Otherwise use a separate fresh context and disclose a blocker if independence cannot be established.

The judge reads this rubric together with `interpretation-review.md`. It sees the assertion, source passages, source access paths and evidence access level; never the writer's intended answer or the qualification gold labels. Writer-selected synthesis quotes are leads, not a limit on admissible evidence. Inspect the relevant definitions, methods/results, table headers and notes needed to interpret the source. The deterministic checker establishes quote identity and quantity consistency; it does not establish scientific entailment or genuine judge independence.

## Qualify the judge

The coordinator prepares unlabelled synthetic packets:

```bash
python3 scripts/verify_claims.py benchmark-packets --input evals/judge-benchmark-input.json --audit judge-candidate.json
```

Give only the printed packets, the candidate audit, and this rubric to a fresh judge. Do not pass `judge-benchmark-gold.json`. Record judgments using `adjudicate`, then the coordinator scores them:

```bash
python3 scripts/verify_claims.py score --audit judge-candidate.json --gold evals/judge-benchmark-gold.json --qualify --min-agreement 80 --max-false-acceptance 0 --report judge-qualification.json
```

Every gold pair must appear exactly once; missing, extra, or changed assertions fail. The report records benchmark/candidate hashes, confusion counts, agreement, and false acceptance. Use a fresh held-out evaluation before changing this rubric; never tune the judge against the gold answers and present the same score as independent validation. The older creatine and decorative-citation sets remain regression resources, not standalone qualification. These synthetic passages test judgment, not literature search.

## Inventory and classification

Run `extract` on the finished Markdown. It inventories headings, paragraphs, citation-free summaries, image alt text, captions, and table rows, including items without citations. Source-list entries and receipts are apparatus and excluded. Cited items start as factual; uncited items require independent classification:

```bash
python3 scripts/verify_claims.py classify --audit claims_audit.json --claim C001 --classification nonfactual --note "Question heading; it asserts no empirical answer."
python3 scripts/verify_claims.py classify --audit claims_audit.json --claim C002 --classification interpretation --basis C008 --basis C009 --note "Calibrated summary of the checked findings, with no additional factual premise."
```

`interpretation` is only an explicit inference or faithful summary whose factual basis IDs are in the same audit. It cannot excuse a new number, population, causal claim, or unsupported assertion. `nonfactual` is for questions, labels, and non-assertive connective text. A factual uncited sentence needs a citation, or revision, before release. The tool checks that basis IDs identify factual claims; the judge checks their meaning. Cited text cannot be relabelled nonfactual or artifact to avoid verification.

`artifact` supports only uncited assertions about this document's own provenance (for example, recorded search dates, databases and access limitations) or depicted geometry (for example, which panel contains a curve). The independent judge must open and inspect every supplied file, and give a substantive note explaining exactly which observed contents support the complete assertion. A filename, hash or the author's promise is not evidence of its contents. Use search manifests, access records, or the actual figure as appropriate. Never use this classification for scientific results, causal claims, efficacy, biological mechanisms, quantitative findings, or scientific interpretations; those require factual source evidence or interpretation with checked factual basis IDs. Mixed captions must be separated into atomic sentences before classification; never omit an assertion. An uncited scientific heading remains an interpretation with factual basis IDs, not an artifact.

```bash
python3 scripts/verify_claims.py classify --audit claims_audit.json --claim C003 --classification artifact --artifact search-manifest.json --artifact fulltext-manifest.json --note "The inspected manifests record the stated search date, databases and access limitations."
```

`--artifact` is repeatable and resolves from the command's working directory. The audit stores each file path relative to the audit file and the SHA256 of its actual bytes. Check and release both require those exact files and hashes; changed or missing files require renewed independent inspection and classification. Receipts expose these paths and hashes. Hash binding establishes identity, not semantic support or independent inspection.

## Verdicts and complete support

- `supported`: the source in its inspected context entails the assigned assertion elements, including material qualifications; an authentic quotation alone is insufficient.
- `partial`: the source supports only specified elements. Name the uncovered element in a pair-specific note.
- `contradicted`: the source states incompatible evidence.
- `not_found`: source text is available but does not address the claim.
- `unverifiable`: usable source text is unavailable, or a quotation cannot be authenticated.

An assertion has one element by default. Split a compound assertion into consecutive verbatim clauses before adjudicating when different sources support different parts:

```bash
python3 scripts/verify_claims.py elements --audit claims_audit.json --claim C005 --element "Reading improved" --element "and attendance increased."
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet 'C005#1' --verdict partial --covers E1 --quote "Reading improved" --note "This source did not assess attendance."
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet 'C005#2' --verdict partial --covers E2 --quote "Attendance increased" --note "This source did not assess reading."
```

Elements must partition the complete sentence without dropping qualifications. Changing the partition resets its judgments. `--covers` names only elements fully supported by that source; repeat it for several elements. A supported verdict defaults to all elements. A partial verdict defaults to no covered elements and cannot claim the whole assertion. Release requires the union to cover every element. A compound caption or table row follows the same rule. Prefer atomic sentences when splitting is awkward.

Check population/model, design, comparison, outcome, timepoint, effect direction, magnitude, uncertainty, and causal/adjustment qualifiers. An association cannot support a causal verb. A narrow population cannot support a universal statement. Statistical significance alone is not effect magnitude. All quantities in a covered element must occur with matching signs and units in its supporting quotations. Exact numeric matching is a guard, not proof that the number refers to the right group or outcome. For derived values, retain a quoted source value in the factual statement and explain the reproducible calculation as an interpretation with factual basis IDs; do not bypass the quantity check.

Quotes must occur verbatim in the stored source text after normalization. `--bridge` may record a genuine paraphrase with no shared content term, but cannot supply missing evidence. Keep pair-specific notes. Read original source context where the candidate passage omits a comparator, qualifier, or outcome definition.

For newly extracted audits, record the source-specific meaning, inspected line ranges, interpretation and limitations with `--context-review` and `--evidence` as defined in `interpretation-review.md`. The short adjudication commands above illustrate verdict/element syntax; new audits additionally require that context record for supported, partial and contradicted judgments. Unavailable evidence must not be assigned invented context ranges. A complete review also requires the `review-context` judgment after sentence checks, including every rendered figure’s observed meaning and checked scientific basis.

## Check, bind, and release

Run `check --strict`, then `receipts`. Schema-v2 audits store an inventory fingerprint, independent classifications, element coverage, evidence hashes, and a checked-content digest. Receipts, exporter, and PDF QA re-extract the current review, compare its complete inventory, validate coverage, and rehash the saved evidence. A changed assertion, source assignment, classification, element, or evidence file invalidates the check. Old audits have no complete inventory and must be rebuilt.

Only completely covered assertions ship. A partial source verdict is allowed only when its missing elements are supported elsewhere. Removing a citation does not remove its factual assertion from the inventory. Correct, qualify, or remove the unsupported assertion, then re-audit.

For a supplied draft, every negative verdict and uncovered assertion remains visible in the report. An audit failure is a finding, not a reason to hide it. Text access (`full text`/`abstract`), source support, and outcome certainty are separate quantities. The receipts show source support and access; the review and evidence assessment explain certainty.
