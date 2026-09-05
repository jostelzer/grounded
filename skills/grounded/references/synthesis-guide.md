# Synthesis: verified evidence for the explanation

`synthesis.md` is the maintained, style-neutral record of the verified evidence, prepared before styled prose. Downstream prose, figures and storyboards trace to it. It is not a locked interpretation: source-context review or drafting can reveal an error or missing qualification, requiring an update to synthesis and assessment before the deliverable changes. The independent audit checks original source context, not merely agreement with this record. Keep the working file available for inspection.

The ledger separates evidence assessment from composition. It makes claims and their limits inspectable; it does not supply paragraph structure or guarantee coherent writing. Plan the explanation in Throughline, then apply `writing-guide.md` and the selected style guide.

## The contract

```markdown
# Synthesis — <the sharpened question>

## Verdict
<One citation-free paragraph: the answer, including inconclusive or mixed results,
its certainty in calibrated language, and the main boundary. This is the paragraph
every style's opening move is carved from — the abstract's first move, the
standfirst's shape, the TL;DR.>

## Throughline
<A brief plan of how the explanation develops: the question, the answer, each
proposed section's contribution and why it follows or sits alongside the others.
Identify the relevant claim IDs. Do not force a single conclusion, chronology,
tension or resolution when the evidence does not support it.>

## Claims

### C1. <The claim, as one atomic calibrated full sentence.>
- strength: <strong | moderate | limited | contested> — <one-line reason, per the
  ladder in evidence-weighing.md>
- evidence: <the decisive studies, one line each: design, n, exact result with
  interval> [@key; @key]
- quote: [@key] "<the passage, copied character for character from the stored
  text of that source, that says what the evidence line attributes to it>"
- quote: [@key] "<one line per cited key; more lines when one passage cannot
  carry the claim's numbers>"
- contrary: <what disagrees or is null, and why it might, one line each> [@key]
  <or "none found — searched">
- quote: [@key] "<the contrary passage, likewise verbatim>"
- boundary: <populations, doses, settings, durations where the claim stops applying>
- depends-on: <claim IDs this claim presupposes, e.g. C2, C3 — or "—">
- numbers: <every figure any style might need, full precision with intervals and
  denominators — this field is the licensed home of precision>
- actors: <optional, for styles that name people: the lead authors and any
  recorded affiliations of this claim's decisive studies, copied verbatim from
  the ledger's `authors_structured` — "Sean Wharton (Wharton et al. 2022,
  affiliation: McMaster University)". This field is the ONLY channel through
  which a person's given name or an institution may reach the prose; if it is
  not recorded here from the ledger, the prose uses the surname or "researchers">

### C2. …

## Patterns
- P1. <A supported relationship across claims, with their IDs: "the
  trial-versus-cohort gap (C2, C4, C7)". Use where it advances the explanation.>

## Open
- <What remains unknown and which missing observations or comparisons limit the
  answer. Unknowns live here, not disguised as claims or advice.>
```

Field labels, claim IDs (`C1`, `C2`, …), and pattern IDs (`P1`, …) are exact and stable — the format is deterministic by design so that tooling can parse and cross-check it without guessing. Do not rename fields, merge them, or add prose between entries.

## Quotes before prose

Every key on a claim's evidence or contrary line carries at least one
`- quote: [@key] "…"` line — the passage from that source's stored text
(`evidence/`, seeded from the full texts already read and the ledger
abstracts) that says what the line attributes to it. This is where the receipt
is born: the review's citations are rendered from these lines, so a sentence
cannot be written against a source that was never quoted, and a source cannot
be cited by the review unless the synthesis quotes it. Before any drafting:

```bash
python3 scripts/verify_claims.py seed --ledger sources.json --evidence evidence/ --fulltext-dir fulltexts --fulltext-manifest fulltext-manifest.json
python3 scripts/verify_claims.py synthesis-check --synthesis synthesis.md --ledger sources.json --evidence evidence/ --report synthesis-check.json
```

The gate string-matches every quote against the stored text, requires every
number in the claim sentence to sit inside one of the claim's quotes, and
warns when a `numbers:` value appears in no quote (derived arithmetic is
allowed only when the prose labels it as such). A claim that cannot be quoted
is not a claim yet — find the passage, weaken the sentence to what the
passage says, or drop the key. A quote is judged for meaning when the review
is audited (step 8); here it only has to exist and be verbatim.

Record applicable population/system, design, exposure, comparison, outcome, timeframe, quantity and uncertainty in the existing evidence, boundary and numbers fields. Use qualitative scope where appropriate; do not force every claim into a trial template. See `interpretation-review.md` for the independent context check.

## Claim rules

- **Atomic.** One claim is one assertable sentence a reader could agree or disagree with. "X lowers relapse risk when it replaces Y" — yes. "X affects mood and sleep" — two claims. Split components when they need different evidence or qualifications; a conjunction alone does not require fragmentation.
- **Calibrated in the sentence itself.** The strength lives in the verb ("lowers", "probably reduces", "is associated with", "may"), matched to the `strength` field per `evidence-weighing.md`. A claim whose wording outruns its strength field is wrong at the source, and every style inherits the error.
- **Evidence-anchored.** Every evidence and contrary line carries ledger keys, and every key carries its quote line; a claim with no keys is not a claim, it is an opinion, and it does not enter the ledger. One source, one statement: a key appears on a claim only for what its quoted passage states — a generalisation about the field ("reviews agree that…") cites a review whose text makes it, or is recorded as a pattern (P-entry) rather than dressed as evidence. Speculation and mechanism-plausibility belong inside a claim's wording ("is biologically plausible but unproven in humans") or in Open — never as bare claims.
- **Contrary evidence is recorded on the claim it opposes**, not pooled in a separate section. This is what guarantees no style can quietly drop it: whoever renders C4 renders C4's contrary line.
- **`depends-on` records prerequisites.** It must be acyclic. Check cyclic or indiscriminate dependencies for incorrectly separated claims. Respect prerequisites when planning, but choose the order and explanatory relationships in Throughline; a valid dependency order is not a finished narrative.
- **`numbers` preserves full precision.** Record exact effect sizes, intervals, denominators and absolute risks. Select quantities appropriate to the audience while preserving what is needed to interpret the finding; supporting precision remains available here and in the sources.
- **Claim count scales with size** — advisory, like the other tier ranges: small 5–12, medium 10–25, large 20–45. Sections typically render 1–3 claims each.
- A corrected source's claim must be checked against its recorded correction; a claim resting on the corrected-away part of a paper is removed here, before any style can inherit it.

## Compose from the record

Use `writing-guide.md` and only the selected style guide for composition. Atomic evidence checks do not require atomic prose: several claims can develop one paragraph, and a necessary explanation can span paragraphs. Reuse precise wording when it fits; there is no obligation to paraphrase an already clear claim. The article must develop the answer rather than transcribe evidence entries.

Every load-bearing rendered claim traces to a C-entry and retains its strength, boundaries and material contrary evidence. Select claims for scope and contribution; do not silently omit a necessary part of the planned answer or cite a discarded claim as though it remains. Keep full precision in the ledger even when the prose uses appropriate rounding.

Figure specifications trace to C/P entries. Revisit sources for definitions, visual relationships or quantities and update the synthesis before incorporating new content. For explicitly requested slides, `deck-guide.md` defines the storyboard: reference keys come from the synthesis and evidence grades preserve claim strength and contrary findings.

## Workflow and hygiene

- Write `synthesis.md` from `sources.json` and `notes.md` only — every number checked against the ledger record it cites, not against memory of the paper.
- Update it, don't fork it: if drafting reveals a wrong or missing claim, fix the synthesis first, then the draft. The synthesis and the delivered review must agree at release; a draft that quietly outgrew its synthesis has an unaudited claim in it.
- It lives in the review's working folder next to `notes.md`, and like the other working files it is mentioned to the user only if they want to audit.
- On the no-script path the synthesis is written identically — it needs no network and no scripts, only the verified ledger.

## Certainty assessment

Record per-outcome certainty and study-family overlap in `evidence-assessment.json` as specified in evidence-assessment.md. `synthesis-check` requires it. No contrary citations is a valid result after the required completed contrary/null search; the narrative must not manufacture disagreement.
