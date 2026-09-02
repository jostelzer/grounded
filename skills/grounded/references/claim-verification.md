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

## Where the receipt is born

The audit does not go looking for quotes after the prose exists. The
synthesis already carries, for every key a claim cites, the verbatim passage
that key was cited for (`synthesis-guide.md`, "Quotes before prose"), and
`extract --synthesis` refuses a cited source the synthesis never quoted. Each
packet therefore opens with the writer's own receipts for that source (`S1.`,
`S2.`), followed by candidate passages selected around the sentence's numbers
and rare terms. The judge's question is narrower than "is there support
somewhere in this paper?": it is "does this sentence, in this register, still
say what these passages say?"

## The judge is not the writer

Verdicts are judgments about what a passage says, made by someone who did not
write the sentence and has nothing invested in it. The writer never
adjudicates its own review. Packets are produced with `--blind` — the
sentence, the synthesis quotes, the candidate passages, and the evidence tier;
no source identity, no place in the review, no synthesis, no draft — and
handed to a judge that sees nothing else: a fresh agent where the host can
spawn one, otherwise a fresh context after all writing is finished. A judge
configuration is trusted on a real review only after it has re-adjudicated
`evals/claim-benchmark-creatine.json` blind and `score --min-agreement 80`
passes; the decorative citations in `evals/decorative-citations.json` are the
regression set the checker's relevance floor must keep rejecting.

Verdicts are never produced by a script, a similarity score, a keyword
overlap, a "conservative default", or a template note "for manual review" —
a verdict generated that way is a fabricated audit, and the checker treats the
tell-tale signs as hard failures: a note copied onto three or more pairs, or a
`partial` with no note. Read each packet, decide, and record one pair at a
time:

```bash
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet C007#1 \
    --verdict supported --quote "exact passage from the packet"
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet C008#2 \
    --verdict partial --quote "exact passage" --note "abstract gives the direction but not the 12% figure"
python3 scripts/verify_claims.py adjudicate --audit claims_audit.json --packet C009#1 \
    --verdict supported --quote "restoration of appetite following withdrawal" --bridge "appetite = hunger"
```

The note is where the judgment lives. It is optional on `supported`, required
on `partial` (name the element the quote does not cover), and it must be
specific to the pair — "the source supports the evidence stream but not every
element" written forty times is not forty judgments.

## Verdicts

| Verdict | Meaning | Quote required |
|---|---|---|
| `supported` | The source's own text states what the claim states, at the claim's level of specificity | yes |
| `partial` | The source supports the substance but not every element at this evidence tier (a number, a subgroup, one clause) | yes |
| `not_found` | The available evidence text does not address the claim; full text might | no |
| `contradicted` | The source states the opposite or materially conflicts with the claim | yes |
| `unverifiable` | No usable evidence text, or the check rejected the quote | no |

Choosing between `supported` and `partial`:

- **A sentence with several citations is judged per source, for the part
  that source is cited for.** "Reviews describe appetite returning, weight
  regain, and markers deteriorating [A] [B] [C]" is `supported` by A when A
  states any of those elements as the review attributes it — the sentence's
  coverage is the union of its sources, not each source alone. `partial` on
  such a sentence means the source only half-supports *its own* part (a
  weaker claim, a different population), not that it is silent on the other
  sources' parts. Judged this way, `partial` is the exception; a run above a
  quarter of pairs means the rubric is being misread or the review over-cites.
- **A figure caption is one claim.** The extractor audits the whole caption
  once per cited source; quote the passage behind what the caption attributes
  to that source. Descriptions of the artwork ("whiskers are 95% intervals")
  are not claims about the source and never justify `partial` on their own.
- **A table row is the row's cells.** Quote what establishes each factual
  cell; a characterising cell ("confounding", "heterogeneous") needs the
  passage that characterises.

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
  verdict is `partial` (naming the missing number) when the abstract supports
  the substance, and `not_found` when it does not — and a `not_found` citation
  is then repaired in the review before delivery.
- A quote must visibly connect to its claim: the checker rejects a quote
  sharing no content word or number with the sentence. When the connection is
  a genuine paraphrase — the review says "hunger", the paper says "appetite";
  ELI5 says "no-sample check", the paper says "procedural blank" — state it
  as a **bridge** (`--bridge "appetite = hunger"`). The checker requires the
  bridge to name a term from the quote and a term from the claim, the receipt
  prints it, and a bridge copied across pairs fails like a templated note.
  "The source is on topic" is not a bridge; a passage about the search
  strategy or the consent procedure never supports a finding.
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

## Delivery: the receipts file

The audit is part of every delivered review. `check --summary
claims_summary.json` writes the tally; `receipts` writes
`<review>-receipts.md` — one section per cited sentence, listing each source
as the text names it, its evidence tier, the verdict, the verbatim quote, and
any bridge — and stamps the review: every Sources entry gains `· N claims ·
full text|abstract`, and a two-line `**Receipts**` block after Sources carries
the tally and the file name. The receipts file travels with the review in
every format; the journal PDF (`export_review.py --claims-audit
--claim-receipts`) hashes it into the release manifest and prints only the
tally in its colophon. `check --appendix` still renders the flat appendix for
a draft check.

Only `supported` and `partial` pairs are receipts. `receipts`, the exporter,
and PDF QA refuse an audit with any pending, contradicted, `not_found`, or
`unverifiable` pair: a citation the source's own text does not back is a
decorative citation, and the repair belongs in the review — drop it, move it
to the sentence it does support, or rewrite the sentence to what the source
says — followed by re-extraction and re-adjudication of the changed claims.
Abstaining is still the honest verdict during adjudication; it just cannot be
the final state of a shipped citation. When you deliver, report the verdict counts and the tier split ("12
supported at full text, 13 at abstract") in the reply. The receipts are the
artifact; the honesty about tiers is what makes them credible.
