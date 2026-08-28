# The synthesis — the claims ledger every style renders

`synthesis.md` is the style-neutral distillation of the verified evidence, written after verification (pipeline step 4) and before a single sentence of styled prose (step 5b). It is where deciding **what the literature says** is finished, so that the styled draft can be a pure act of telling. Every downstream artifact draws from it and only from it: the styled review, the figures, and the deck storyboard; the claim audit, which verifies the review's sentences against the sources' own text, gains a fixed claim inventory to check coverage against. It is a working file — never delivered, never attached, never quoted verbatim.

Why it exists: when synthesis and styling happen in one pass, the synthesis leaks into the deliverable as inventory sentences ("One meta-analysis found… Another found…"), number dumps, and register wobble. Finishing the synthesis first — as structured fields, not prose — makes those failure modes structurally hard: the styled text cannot paraphrase what was never prose to begin with.

## The contract

```markdown
# Synthesis — <the sharpened question>

## Verdict
<One citation-free paragraph: the answer, stated affirmatively on its own terms,
its certainty in calibrated language, and the main boundary. This is the paragraph
every style's opening move is carved from — the abstract's first move, the
standfirst's shape, the TL;DR.>

## Throughline
<One sentence naming the tension or pattern the whole review turns on. If two
framings genuinely compete, list both and pick one before drafting begins.>

## Claims

### C1. <The claim, as one atomic calibrated full sentence.>
- strength: <strong | moderate | limited | contested> — <one-line reason, per the
  ladder in evidence-weighing.md>
- evidence: <the decisive studies, one line each: design, n, exact result with
  interval> [@key; @key]
- contrary: <what disagrees or is null, and why it might, one line each> [@key]
  <or "none found — searched">
- boundary: <populations, doses, settings, durations where the claim stops applying>
- depends-on: <claim IDs this claim presupposes, e.g. C2, C3 — or "—">
- numbers: <every figure any style might need, full precision with intervals and
  denominators — this field is the licensed home of precision>

### C2. …

## Patterns
- P1. <A cross-cutting pattern with the claim IDs it spans: "the trial-versus-cohort
  gap (C2, C4, C7)". These become the callbacks, the popsci turn, the conclusion.>

## Open
- <What is unknown, and the specific study that would settle it. Unknowns live
  here, not disguised as claims.>
```

Field labels, claim IDs (`C1`, `C2`, …), and pattern IDs (`P1`, …) are exact and stable — the format is deterministic by design so that tooling can parse and cross-check it without guessing. Do not rename fields, merge them, or add prose between entries.

## Claim rules

- **Atomic.** One claim is one assertable sentence a reader could agree or disagree with. "X lowers relapse risk when it replaces Y" — yes. "X affects mood and sleep" — two claims. If a claim needs "and", split it.
- **Calibrated in the sentence itself.** The strength lives in the verb ("lowers", "probably reduces", "is associated with", "may"), matched to the `strength` field per `evidence-weighing.md`. A claim whose wording outruns its strength field is wrong at the source, and every style inherits the error.
- **Evidence-anchored.** Every evidence and contrary line carries ledger keys; a claim with no keys is not a claim, it is an opinion, and it does not enter the ledger. Speculation and mechanism-plausibility belong inside a claim's wording ("is biologically plausible but unproven in humans") or in Open — never as bare claims.
- **Contrary evidence is recorded on the claim it opposes**, not pooled in a separate section. This is what guarantees no style can quietly drop it: whoever renders C4 renders C4's contrary line.
- **`depends-on` is the argument's skeleton.** It must be acyclic. Ordering claims so every claim follows its dependencies gives ELI5 its staircase, scientific its argument order, and the deck its arc for free. If the dependencies are cyclic or everything depends on everything, the claims are cut wrong — recut.
- **`numbers` is the single home of full precision.** Exact effect sizes, intervals, denominators, absolute risks. The styles then *ration* from it under their own budgets — scientific keeps the most, popsci leads with one or two per section, ELI5 carries one per step in reader units. Nothing is ever lost by a budget: the precision stays here and in the sources.
- **Claim count scales with size** — advisory, like the other tier ranges: small 5–12, medium 10–25, large 20–45. Sections typically render 1–3 claims each.
- A corrected source's claim must be checked against its recorded correction; a claim resting on the corrected-away part of a paper is removed here, before any style can inherit it.

## Rendering: how each style arranges the same claims

The styles are four arrangements of one claims ledger — selection, ordering, and register change; the claims, their strengths, and their contrary evidence do not.

- **Scientific** — claim headings *are* selected claims, worded as the calibrated sentences they already are. Order by `depends-on` and argumentative weight. Abstract four moves map directly: Verdict paragraph → move 1; the strongest claim with its lead number → move 2; the strongest contrary line and its resolution → move 3; the boundaries → move 4. Patterns become the callbacks and the Conclusion.
- **Popsci** — choose the spine (chronology, investigation, or a followed subject), then map claims to beats along it; the star number each section leads with comes from that claim's `numbers` field; the turn is the claim (or pattern) whose contrary line bites hardest; the kicker looks forward using Open.
- **Bullets** — punchline headings are the claims; bullets are the evidence lines made concise; the once-named cross-section pattern is a P-entry.
- **ELI5** — the staircase is the dependency order: sort claims so each stands only on earlier ones; each step renders one claim with one number in reader units; the helper picture is chosen for the hardest claim; the turn step is the strongest contrary line in the reader's own doubt-words.
- **Slides** — content-slide titles are claims (the deck already requires full-sentence cited claim titles); the storyboard's `reference_keys` are the synthesis's keys; the evidence grade describes the slide's claim exactly as `strength` recorded it (strong → `strong`; moderate/limited → `mixed`/`limited`; contested → `mixed` with the contrary evidence visible in the artwork).
- **Figures** — every figure specification is built from claim entries and pattern entries, never from a fresh reading of the papers; the caption's citations are the rendered claims' keys.

## The anti-paraphrase rule

The styled review is **composed from** the synthesis, never **translated from** it. The synthesis is fields precisely so there are no sentences to lightly reword; if any styled sentence reads as a synthesis line with connective tissue, the telling pass has collapsed into transcription — rewrite it as prose born in the target register. The check runs in both directions: every load-bearing styled claim traces to a C-entry and carries that entry's keys; no C-entry that survived into the plan is silently dropped, and dropping one deliberately (a size cut) means its evidence is not cited elsewhere as if the claim were still made.

## Workflow and hygiene

- Write `synthesis.md` from `sources.json` and `notes.md` only — every number checked against the ledger record it cites, not against memory of the paper.
- Update it, don't fork it: if drafting reveals a wrong or missing claim, fix the synthesis first, then the draft. The synthesis and the delivered review must agree at release; a draft that quietly outgrew its synthesis has an unaudited claim in it.
- It lives in the review's working folder next to `notes.md`, and like the other working files it is mentioned to the user only if they want to audit.
- On the no-script path the synthesis is written identically — it needs no network and no scripts, only the verified ledger.
