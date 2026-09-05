# Writing guide

Write a connected, source-grounded report that develops an answer to the research question. Every sentence must contribute meaning and connect to its context; paragraphs develop points, and sections build the reader's understanding of the whole. Accuracy, continuity and a clear reporting voice apply to every style.

## Select the audience and format

Read only the selected style guide in addition to this shared contract:

- `style-popsci.md`: default; accessible science reporting for a curious adult.
- `style-scientific.md`: scientific or journal-register prose; `prose` is an alias.
- `style-bullets.md`: only when explicitly requested; compact scientific reporting.
- `style-eli5.md`: only when requested; connected explanation without assumed science knowledge. It does not imply bullets.

Style changes vocabulary, technical depth and presentation. It does not relax evidence requirements or change the narrator into a counselor. Size and word budgets come from `sizes.md` and `scripts/review_config.py`; size controls scope, not sentence density or reference quotas.

Deliver the written review in chat. Create files when requested; journal PDF adds its figures and PDF without replacing the chat review. Include a compact scope/methods disclosure near the end: review type, search date, databases, inclusion/exclusion boundaries and material access limitations.

## Plan the explanation from the evidence

Finish the verified `synthesis.md` under `synthesis-guide.md` before drafting. In its existing **Throughline** field, briefly set out the question, the developing answer, and why each proposed section follows or sits alongside the others. Identify which claims establish, explain, qualify or challenge the answer. Match the detail of this plan to the review's size; no separate planning document is required.

Dependencies identify prerequisites, not a finished narrative. Several parallel outcomes or unresolved findings may belong in one coherent review. Explain their relationship to the question without inventing chronology, causation, disagreement or resolution. Publication order and source-discovery order are not default article structures.

Select evidence for its contribution. A paper belongs because its finding or method advances the explanation, not because it was retrieved. Combine redundant coverage while retaining material contrary findings and qualifications. Every load-bearing claim must trace to the synthesis and carry the appropriate source keys; do not cite a cut claim's evidence as though the claim remains. Changes to scientific meaning require updating synthesis and assessment before revising the deliverable.

## Compose connected prose

- **Give each sentence a purpose.** It may establish a fact, explain a relationship, supply necessary context, qualify an inference or connect parts of the answer. It need not introduce another fact. Remove sentences that merely announce a study, repeat a point or tell the reader that something matters without explaining why.
- **Connect familiar information to the next point.** Make referents clear and introduce context before relying on it. Let the subject under discussion continue when appropriate; restarting with a new researcher or study name can interrupt it. Keep established terms stable rather than varying synonyms for decoration.
- **Develop a point through the paragraph.** Select and relate the evidence needed to understand that point. The ledger's atomic claims need not become isolated sentences or one-study paragraphs. Sentence length follows the relationship being expressed; cutting every clause into a short sentence can break the flow.
- **Make transitions carry reasoning.** Show how the next finding extends, explains, contrasts with or limits the preceding one. A word such as “therefore” cannot supply a missing premise. Where outcomes are parallel, orient the reader to the change in question instead of implying one follows causally from another.
- **Keep qualifications with the inference they limit.** Preserve comparators, populations, endpoints, timescales and uncertainty wherever needed. Return to a limitation when its consequence changes; avoid recurring generic cautions or assessment announcements. Explain supported reasons for disagreement and leave unresolved differences unresolved.
- **Use repetition purposefully.** A brief reminder can connect distant parts of the explanation. Repeating the same result, caveat or conclusion without a new role adds reading effort. End paragraphs where their point is complete; do not append a verdict, dramatic contrast or bridge sentence by formula.

Use direct verbs, clear subjects and ordinary wording where precise. Keep necessary disciplinary terms; explain unfamiliar ones for the selected audience. Avoid dense noun stacks, invented abstractions and repeated stock constructions. Rhythm should serve the meaning, with no quotas for short sentences, actors, rhetorical questions, callbacks or section endings. In prose, emphasis comes from wording and placement rather than mid-sentence bolding.

## Report without advising

State what was observed, what it supports and what remains uncertain. Do not tell readers what to do, choose, believe, ask or feel. This applies to summaries, headings, captions and conclusions as well as body prose. Describe gaps in the evidence instead of ending with instructions for researchers.

When recommendations are relevant, attribute them to their source and report their scope without adopting them. A citation does not turn the narrator's advice into reporting. Describe study populations directly rather than implying that a group result predicts an individual reader's experience. Accessible language can be warm without personal address or navigation commands.

For example, “We should keep our confidence in a causal answer low” becomes “The available studies leave the causal relationship uncertain,” when that is what the evidence supports. Review meaning in context; neither a pronoun counter nor a blacklist of “should” can enforce this distinction.

## Evidence, quantities and citations

Preserve the strength and boundaries established under `interpretation-review.md` and `evidence-weighing.md`. A non-significant estimate does not establish no benefit or equivalence. Report relevant quantities with units, denominators and uncertainty; prefer interpretable effects to evaluative adjectives. Accessible rounding must preserve the comparison and inference. A table can carry supporting precision, but a qualification needed to understand the prose stays beside its claim.

Every empirical claim carries a citation; citation-free abstracts and summaries map to audited body claims. Write draft citations as `[@key]`; `format_references.py --style bracket` renders author–year DOI links and the Sources block. On the tool-only path, transcribe verified ledger records. Each citation sits immediately after its supported clause and before terminal punctuation: `claim [Author 2026](DOI).` Never begin a sentence with a citation or print bare citation brackets. Multiple claims may share a grammatical sentence when each source's support remains local and unambiguous. Do not manufacture agreement through a citation cluster. Authorial synthesis must have an identifiable factual basis in the assertion audit even when it has no inline citation.

The journal exporter converts these links to numbered, linked superscripts after punctuation and a first-citation-order reference list; the source Markdown remains unchanged. The generated Markdown Sources block is alphabetical, with every author, year, title, journal and verified DOI. Peer-reviewed guideline articles are cited as guidance, not as experimental evidence. Follow `citation-rules.md` for eligibility and integrity checks; unresolved identity or retraction failures cannot reach Sources. Report access limits honestly.

At the first use of a specialist term or abbreviation, link its English Wikipedia article after confirming the exact URL resolves. Use article URLs without section anchors; expand and leave unlinked if confirmation fails. Link terms a non-specialist needs explained, not everyday words, and never place jargon links in the plain-language TL;DR. Wikipedia supplies an explanation, never evidence. The style guide determines whether to gloss a term or replace it with ordinary words.

## Tables, figures and captions

Use a table when shared dimensions make several studies easier to compare. Keep it compact, normally 3–5 columns, and cite each empirical row. Explain why the comparison matters in the prose; do not duplicate the table's contents sentence by sentence or force unlike outcomes into a common comparison.

Place a figure after the body has introduced its subject and at the point where it helps develop the explanation. Keep a result and its necessary qualification together. Do not let artwork or a table interrupt one argument to illustrate a different study. Use stable body references, alt text and cited captions under `figure-captions.md`; each caption reports what is shown, its encoding and its evidence boundary in the selected register. Re-read the prose–figure–caption sequence as a whole.

For visual generation and PDF production, follow `media-modes.md` and `output-formats.md`. Preserve figure provenance, exact quantities, scientific meaning, natural proportions, legibility and inspection of every rendered page. Layout repair must preserve the explanation and evidence.

## Editorial acceptance

Before generating figures, read the complete draft as a reader who has not seen the ledger. Check the title, opening, headings, body, planned visual placements and conclusion together:

1. Can the reader state the question, the answer and its material uncertainty?
2. Does each section contribute to that answer, with a clear reason for its position or its relationship to parallel sections?
3. Does each paragraph develop a point, and does every sentence contribute to it while connecting naturally to its context? Resolve inventories, unexplained jumps, unclear referents and redundant returns.
4. Do transitions express supported relationships, with qualifications available when needed?
5. Does the narrator report throughout, including the ending? Do figures and tables support the current explanation?
6. Does the conclusion answer the opening question without introducing unsupported claims or prescribing action?

Record a short case-specific judgment in the existing working notes: the answer a reader would take away, how the explanation develops, and any located failures and repairs. A bare “coherent” or checked style box is insufficient. Revise failures before production; do not add a new form or paragraph-by-paragraph scorecard.

After claim repairs or figure placement, re-read the complete article for changed meaning and broken continuity. Re-audit altered factual claims. The final independent `review-context` check under `interpretation-review.md` records the reading judgment alongside scientific interpretation and binds it to the finished deliverable. Source support and editorial quality are separate judgments.

Finally run `validate_review.py` with the selected style, size, ledger and full-text manifest; use `--strict-tier` when size was explicitly requested. Resolve errors and review warnings under `quality-gates.md`. Complete the independent assertion audit, source annotations, receipts and any PDF release checks. Deterministic validation establishes consistency; it does not establish that the explanation is good.
