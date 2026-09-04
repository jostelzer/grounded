# Outcome certainty and study overlap

Create `evidence-assessment.json` before drafting. This is a compact structured judgment, not a claim to have performed formal GRADE. Use the question-appropriate evidence designs described in evidence-weighing.md. Each major outcome and every synthesis claim must have a justified confidence assessment. Text access and quote entailment are separate from this assessment.

```json
{
  "schema_version": 1,
  "scope": {
    "question": "Does X improve Y in population Z versus comparator C?",
    "review_type": "narrative",
    "search_date": "2026-09-04",
    "databases": ["PubMed", "OpenAlex"],
    "inclusion": "Peer-reviewed direct comparisons in population Z.",
    "exclusion": "Animal models excluded from estimates of human benefit.",
    "access_limitations": "Two peripheral papers were available only as abstracts."
  },
  "studies": [
    {"id": "trial-a", "kind": "primary", "design": "randomized trial",
     "source_keys": ["Trial2024", "TrialFollowup2025"]},
    {"id": "review-a", "kind": "review", "design": "systematic review",
     "source_keys": ["Review2025"], "underlying_study_ids": ["trial-a"],
     "overlap_status": "known", "overlap_note": "The review includes trial-a; it is not an independent replication."}
  ],
  "outcomes": [{
    "id": "outcome-y", "outcome": "Y at six months", "claim_ids": ["C1"],
    "source_keys": ["Trial2024", "TrialFollowup2025", "Review2025"],
    "certainty": "low", "rationale": "One small trial with imprecision and limited generalizability.",
    "domains": {
      "risk_of_bias": {"judgment": "some", "reason": "Outcome assessors were unblinded."},
      "inconsistency": {"judgment": "unclear", "reason": "Only one independent trial."},
      "indirectness": {"judgment": "some", "reason": "Participants were healthier than the target population."},
      "imprecision": {"judgment": "high", "reason": "The interval spans benefit and no material difference."},
      "publication_bias": {"judgment": "unclear", "reason": "Too few independent studies to assess reliably."}
    }
  }]
}
```

Use actual ledger keys and synthesis IDs. Domain judgments are `low`, `some`, `high`, `unclear`, or `not_applicable`, always with a reason; certainty is `high`, `moderate`, `low`, or `very_low`, justified for the body of evidence. Do not mechanically infer certainty from study count or design. A `systematic` review also records its protocol and screening-method reference in `scope.protocol`.

One study family may have several publications, including follow-ups and secondary analyses. Assign a publication to exactly one family. For reviews, record the primary study IDs shared with the included corpus. If overlap cannot be determined, use `overlap_status: unknown`, explain why, and do not count the review as independent confirmation. Known overlap outside the included corpus can be explained in the note; never invent study IDs.

The assessment validator checks schema completeness and source/claim coverage. It does not verify the clinical or scientific judgments; the reviewer must check those against study methods and the relevant evidence body.

```bash
python3 scripts/evidence_assessment.py --assessment evidence-assessment.json --ledger sources.json --synthesis synthesis.md --report evidence-assessment-check.json
```

The synthesis gate runs this check and review extraction embeds the validated assessment in the audit. Include a short methods disclosure using the scope fields, and report the main outcome confidence in ordinary prose. Use “no integrity signal found in the queried data as of [date]”; metadata screening cannot establish that no correction or concern exists.

Methodological reference: [Cochrane Handbook, chapter 14](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14). Integrity coverage: [Crossref Retraction Watch documentation](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/).
