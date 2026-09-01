# Claim verification: the adjudication rubric

Bibliographic verification proves a source exists. Claim verification proves the
sentence in front of the citation says what the source says. The machinery is
deterministic (`scripts/verify_claims.py`, `scripts/claim_evidence.py`); the
judgment is yours. This file is the rubric for that judgment.

## The contract

For every (claim, cited source) pair you return a **verdict** and, for most
verdicts, one or more **verbatim quotes** from the source's stored evidence
text. The `check` step enforces this mechanically:

- A quote that does not appear verbatim in the stored evidence (after
  whitespace/Unicode normalization) rejects the verdict to `unverifiable`.
- A numeric claim marked `supported` must have at least one of its numeric
  anchors inside a quote (spelled-out numbers are normalized: "Twenty-two"
  satisfies "22").
- `contradicted` is a hard stop for the whole document.

You can be wrong, but you cannot invent evidence. Never paraphrase inside a
quote, never stitch two passages into one quote (use a list of quotes instead),
and never argue with a downgrade — fix the quote or accept the lower verdict.

## Verdicts

| Verdict | Meaning | Quote required |
|---|---|---|
| `supported` | The source's own text states what the claim states, at the claim's level of specificity | yes |
| `partial` | The source supports the substance but not every element at this evidence tier (a number, a subgroup, one clause) | yes |
| `not_found` | The available evidence text does not address the claim; full text might | no |
| `contradicted` | The source states the opposite or materially conflicts with the claim | yes |
| `unverifiable` | No usable evidence text, or the check rejected the quote | no |

Choosing between `supported` and `partial`:

- Numbers that require arithmetic over the source (n=32 when the source says
  n=15 and n=17) are `partial` with a note showing the arithmetic — the checker
  will force this anyway; write it that way yourself.
- A multi-element claim ("improved X and Y but not Z") is `supported` only when
  every element is quotable; quote each element, or drop to `partial` naming the
  unquoted element in the note.
- A claim about what a paper "reported" is judged against what it reported, even
  if later corrected — but when you know a published correction changed the
  numbers, say so in the note and cite the correction's DOI there.

## Abstention discipline

Abstaining honestly is the feature, not the failure:

- Never promote abstract-tier support to full-text confidence. If the claim's
  specific number is not in the abstract and full text is unavailable, the
  verdict is `partial` or `not_found` with the tier stated.
- Never certify a superlative ("largest", "first", "only") from a source that
  does not itself assert it.
- When two sources are cited for one sentence, judge each source separately for
  the part it plausibly supports; do not let one strong source carry the other.

## Escalation policy

Adjudicate from the abstract first. Escalate to full text (`fetch` does this
automatically for numeric claims) when the claim carries effect sizes, exact
ns, doses, subgroup results, or exclusivity words — the categories where
abstracts routinely lack the anchor. If escalation fails (paywall, PDF-only),
keep the abstract-tier verdict and let the tier column say so.

## Worked example

Claim: "The backward-digit effect was small and uncertain (Cohen's d=0.17;
p=0.067), matrix reasoning changed by d=0.09, and eight exploratory tasks
showed no benefit."

Good adjudication — `supported`, quotes (each verbatim, one per element):

1. "it bordered on significance for BDS (p = 0.067"
2. "was 0.09 for RAPM and 0.17 for BDS"
3. "we included eight exploratory cognitive tests"
4. "There was no indication that creatine improved the performance of our
   exploratory cognitive tasks"

Bad adjudications: one long paraphrase "the study found d=0.17 (p=0.067) for
digit span" (not verbatim — rejected); quoting only element 1 (numeric anchors
0.09 missing from the story — the sentence's other elements uncovered); marking
`supported` from an abstract that lacks the d values (tier dishonesty — the
checker may pass it if the numbers appear, but you should not).

## Delivery

`check --appendix` renders the human-readable audit: every claim, its verdict,
its evidence tier, and its quotes. When you deliver an audit, always report the
verdict counts and the tier split ("14 of 34 sources verified at full text, 20
at abstract level") in the reply. The appendix is the artifact; the honesty
about tiers is what makes it credible.
