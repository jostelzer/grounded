# Preserve scientific meaning

Use this contract when synthesizing, independently adjudicating, or reviewing the
finished argument. Attribution asks whether a source reports something;
interpretation asks whether the review preserves its meaning; outcome certainty
asks how strongly the body of evidence justifies the conclusion. None substitutes
for another. A precise quote can support an imprecise claim.

## Read for the question actually answered

Record the dimensions needed to interpret each claim: population or system,
design, exposure, comparison, outcome, timeframe, quantity and uncertainty, or
qualitative scope. Omit inapplicable dimensions; do not force qualitative or
descriptive research into an intervention template. Put these details in the
existing synthesis evidence/boundary/numbers fields, then preserve them in prose.

Read the source context that could change the interpretation. This normally
means relevant methods and results, with table headings, denominators, notes,
analysis definitions and linked supplements when they matter. Ranked snippets
and writer-selected quotations are navigation leads. The judge can inspect the
whole stored source and obtain additional authenticated text independently.
Full-text access is not proof that relevant context was read.

Resolve source-internal disagreement: an abstract, table, result paragraph or
supplement may describe different analyses. Identify which answers the claim;
do not automatically prefer a section or copy the source's broadest conclusion.
If the relevant context is unavailable or inconsistent, narrow the assertion or
record the uncertainty. A quote cannot repair an unresolved interpretation.

Check distinctions when material to the inference, rather than mechanically
applying every test to every paper: within-group versus between-group change;
baseline versus later reference points; absolute versus relative quantities;
observed outcomes versus proxies; total-period versus phase-specific results;
prespecified versus exploratory analyses; uncertainty and multiplicity; null
evidence versus equivalence; subgroup estimates versus evidence of interaction;
and design or comparator changes over time. These are examples of scope
preservation, not a closed list of failure classes.

## Record the independent decision

New `extract` audits set `context_contract_version: 1`. For supported, partial
or contradicted source verdicts, supply a JSON file to `adjudicate` with
`--context-review pair-context.json --evidence evidence/` in addition to the
ordinary verdict and quotation. The source file printed by `packets` has the
line numbers used here. The following is a schema illustration, not evidence:

```json
{
  "meaning": {
    "design": "Design relevant to this assertion",
    "comparison": "Exact groups or conditions, if applicable",
    "outcome": "The measured outcome, not a broader substitute",
    "uncertainty": "Material limits on the inference"
  },
  "context": [
    {"start_line": 1, "end_line": 8, "reason": "Which definitions or qualifications these lines establish"}
  ],
  "interpretation": "preserved",
  "rationale": "Why the inspected source entails these specific assertion elements",
  "limitations": "Remaining access or scientific limitations; explain when none is material"
}
```

Allowed meaning keys: `population`, `design`, `exposure`, `comparison`, `outcome`,
`timeframe`, `quantity`, `uncertainty`, `scope`. Include only applicable keys,
with concrete source-specific values. `interpretation` is `preserved`,
`mismatch`, or `unresolved`. For a partial verdict, preserved interpretation
applies only to the explicitly covered elements; name the uncovered elements in
the ordinary verdict note. A supported verdict cannot coexist with a material
unresolved or mismatched interpretation. For unavailable or irrelevant evidence,
use the ordinary unverifiable/not_found verdict and explain the limitation;
never invent inspected line ranges.

The command binds the judgment to the source bytes. Check rejects missing
records, invalid ranges, unresolved covered elements and sources changed since
inspection. It cannot decide whether a range is sufficient or a rationale is
correct. Do not generate approval records by filling a template. Quote matching
continues separately. Historical audits lack this contract and must not be
described as context-reviewed; re-extract to perform a new audit.

## Review the argument and the rendered figures

After sentence judgments, independently read the whole deliverable. Compare the
title, summary, headings, selection and emphasis, transitions, captions and
conclusion with the checked evidence. Identify the actual takeaway and its
scientific basis. Check that limitations and contrary findings have not
disappeared through compression, and that the scope matches the included
evidence. Reopen synthesis and assessment if this reveals a problem.

Inspect actual figure pixels, not only prompts or captions. Every quantitative
mark and meaningful relationship must preserve its checked claim's outcome,
comparison, units, origin, uncertainty and scope. Distinguish observed relations,
inference and hypothetical mechanisms in illustrations. Grouping, arrows and
visual emphasis are assertions even when labels are correct. A caption may
provide detail but cannot undo a misleading graphic. Existing geometry and
typography checks remain necessary and separate.

Record the final check with:

```bash
python3 scripts/verify_claims.py review-context --audit claims_audit.json --record document-context.json
```

```json
{
  "takeaway": "What a reader would conclude from the complete deliverable",
  "interpretation": "preserved",
  "basis": ["C001", "C004"],
  "rationale": "Why the selection, framing and conclusion preserve the checked evidence",
  "limitations": "Material remaining evidence or access limitations",
  "figures": [
    {"path": "figure.png", "basis": ["C004"], "observed_meaning": "What the inspected marks, labels and relationships actually communicate"}
  ]
}
```

Use `figures: []` for text only. Input figure paths are relative to the review;
the tool binds every referenced asset by hash and requires exact asset coverage.
Scientific basis IDs must refer to factual assertions or grounded interpretations,
not document-local artifact attestations. Changes to prose, source judgments,
assessment or pixels invalidate the final check. Run `check --strict` afterward.
Mismatch/unresolved records remain recordable for supplied-draft audits and
fail release; the finding must stay visible. New review releases require a
preserved overall interpretation, not absence of uncertainty in the research.

The receipts expose attribution, interpretation, inspected context and outcome
certainty separately. Structured records establish traceability and freshness;
independent judgment and forward evaluation establish whether the workflow is
useful. Neither justifies claiming that every conclusion is true.
