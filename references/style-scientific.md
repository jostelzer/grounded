# Scientific style (default; alias: prose)

Use this style unless the user explicitly selects bullets, popsci, or ELI5. The pipeline, evidence standard, citations, and verification are identical across styles; scientific and bullets share the normal term-link rules defined in `writing-guide.md`. Scientific style shapes the review into a narrative article of the kind journals publish. The shared structure, language, citing, and quality-gate rules in `writing-guide.md` apply in full.

**From the synthesis** (`synthesis.md`, per `synthesis-guide.md`): the claim headings *are* selected synthesis claims, already worded as calibrated sentences; order them by their dependencies and argumentative weight. The Abstract's four moves map directly — the Verdict paragraph becomes move 1, the strongest claim with its lead number move 2, the sharpest contrary line and its resolution move 3, the boundaries move 4. The synthesis's patterns become the cross-section callbacks and the Conclusion's cross-cutting claim.

Structure:

```
## <The question>

**Abstract** — <120–180 words, citation-free, plain language, in exactly four moves:
(1) the verdict, stated affirmatively in the first sentence; (2) the strongest
supporting evidence, with at least one number (an effect size, interval, or count);
(3) the strongest contrary evidence and, in a clause, why it does or does not
overturn the verdict; (4) the boundary — where the verdict stops applying, and the
practical line. An argument with a hierarchy, never a one-sentence-per-section
inventory of the review. State the verdict on its own terms, not as a negation of
the claim being examined ("X lowers LDL when it replaces Y", not "X is not
supported as a hazard"). This replaces the TL;DR.>

### Introduction
<Why the question matters, what is claimed or contested, and the scope — 1–3 paragraphs.
This is the one style where scene-setting is content, not preamble. No methods narration.
End by posing the throughline: the one tension or question the whole review turns on,
and — if it helps the reader — the sub-questions the sections will answer in order.
Pose the question the Conclusion will actually answer: if drafting reveals that the
sections argue a different, better question than the Introduction posed, rewrite the
Introduction to pose that one.>

### <Claim heading — a short full sentence stating what the section shows,
e.g. "Blood lipids provide the clearest randomized signal">
<Paragraphs. See rules below.>

### Conclusion
<Name the cross-cutting pattern plainly — the one claim the sections demonstrated
together — then what the evidence supports at what confidence, and the specific
evidence that would settle what is open. No new evidence introduced here, and no
re-summary: any sentence that could sit in the Abstract unchanged gets cut. The
Conclusion answers the throughline in new words or it is not finished.>

**Sources**
<same generated sources block as always>
```

Narrative arc — what makes the article read as an argument rather than a list:

- **Find the throughline before drafting.** One sentence naming the tension or pattern the whole review turns on ("the biology is solid, but the sleep effect appears only at high doses"). The Introduction poses it, every section advances it, the Conclusion answers it. If no single sentence covers the review, the plan is a taxonomy, not an argument — reorganize until it is one.
- **Land every section.** After the evidence, one plain sentence saying what the section adds to the throughline, ideally handing off to the next section ("So the mechanism is real; whether it costs sleep is a separate question — the one the exposure trials answer next."). A section that stops on its last study is unfinished.
- **Call back across sections.** When a pattern repeats, say so at its second appearance ("the same cohort-versus-trial gap seen for dementia"). One or two callbacks per review are what make it one text rather than stacked summaries. The same discipline caps repetition: make each caveat or confounder fully once, where it bites hardest; every later appearance is a one-clause callback, never a restatement.
- **Interpretive sentences are content, not filler.** Roughly one citation-free sentence per paragraph that weighs or connects the evidence ("The mechanism is real, but the marker does not establish sleep loss."). These carry the argument; the banned-filler list bans throat-clearing, not judgment.
- **Vary the rhythm, and keep it easy to read.** Follow a long evidence sentence with a short verdict sentence; the universal two-in-a-row cap on same-shape evidence sentences (in `writing-guide.md` Language) applies. Prefer two clear sentences over one packed one; plain words and short sentences outrank density everywhere the numbers allow it.

Paragraph craft:

- **The register is that of a peer-reviewed narrative review** — objective, precise, and plain. Open sections with the finding, not with scene-setting flourishes; the Introduction motivates the question with facts (prevalence, contested claims, stakes), never with journalistic hooks. Calibrated verbs ("reduces", "is associated with", "may"), quantities over adjectives, no metaphors, no first person.
- **Headings are claim sentences.** Each section heading is a short full sentence stating what the section shows ("Blood lipids provide the clearest randomized signal"), calibrated to the evidence — the headings alone should read as the skeleton of the argument. Structural headings (Introduction, Conclusion) stay as labels. Every paragraph still opens with the claim it defends, then weaves in the evidence — numbers, intervals, designs — with the same `Author 2026` DOI links inline; the heading states the section's claim, the topic sentences carry the paragraphs' own.
- One claim per paragraph, 3–6 sentences. A paragraph that needs eight sentences is two claims.
- Transitions carry the argument between paragraphs and sections ("The picture changes in older adults…"), but every empirical sentence still carries its citation.
- Contrary evidence gets its own paragraphs with explicit contrast ("Against this…", "The null results cluster where…").
- Tables remain allowed and follow the shared rules; introduce each one in the running text.
- Figures are introduced from the running prose with the stable token in
  `figure-captions.md`. Their captions are short flowing paragraphs in the same
  narrative-review register, with verified author–year citations.
- The banned-filler list still applies in full. Flowing means flowing, not padded: no "it is important to note", no throat-clearing, no restating the abstract in the conclusion.
- Word budgets run ~1.5× the bullet tiers because connective tissue costs words: small 600–1,000, medium 1,500–2,500, large 3,500–6,000. Sources, angles, and search depth are unchanged from the chosen size.
- Scientific reviews print beautifully — end the delivery by offering the journal-styled PDF (`scripts/export_review.py`), but the review itself still goes in the chat.

## The voice: how a good journal article actually sounds

The model for this style is the best-written narrative review you have read — *NEJM* review-article prose, not committee-report prose. Objective never means inert: the great reviews are direct, concrete, and quietly confident, and their authority comes from precision, not from abstraction. The universal rules in `writing-guide.md` (agents act, ration the antithesis, no coinages) bite hardest here, because this register is where the machine voice defaults.

**Do:**

- **Give every claim an agent.** Trials show, cohorts associate, oils lower, doses matter, the data cannot distinguish. When a sentence needs a verdict, let the evidence deliver it: "The trials point to a modest benefit at best" beats "The defensible inference is possible modest benefit."
- **Let calibrated verbs carry the hedging.** "Probably lowers", "may reduce", "is associated with" — the uncertainty lives in the verb, once. Stacking abstraction-hedges ("is compatible with", "is aligned with", "weighs against") around the same claim builds fog, not caution.
- **Earn short sentences and spend them at pressure points.** "Almost every nutrient does." "It would be wrong to call that proof of safety." The shortest sentences in a review are its best moments; a review with none is monotone. After two long evidence sentences, the reader needs a short one.
- **Let a number be the subject sometimes.** "That 0.81 came from trials run before statins existed." Numbers as agents keep quantitative prose alive.
- **Use "this/that" anaphora only with a solid referent.** "That distinction matters" works when the previous sentence made exactly one distinction. "This dependence is visible in both cohorts and trials", three sentences after two candidate dependencies, sends the reader backwards.

**Don't — each ✗ is from a real draft; write the ✓ shape instead:**

- ✗ "Replacement is the second necessary coordinate." → ✓ "The second question is always what the oil replaces."
- ✗ "A category-level verdict is therefore biologically underspecified." → ✓ "The category is too heterogeneous to test as a single exposure."
- ✗ "The appropriate conclusion is uncertainty around small site-specific effects, not evidence for a general carcinogen." → ✓ "The evidence leaves room for small site-specific effects. It does not show a general carcinogen." (One antithesis per section — and this one earns it.)
- ✗ "Lipidomics offers a mechanistic bridge." → ✓ "Lipidomics shows the same shift at the molecular level."
- ✗ "The usable boundary is shown in Figure 3." → ✓ "Figure 3 marks where the risk actually begins: smoke, storage, and reuse."
- ✗ Three sections in a row landing on "…, not …". → ✓ Land one on the number, one on the consequence, one on the open question.

The section-landing sentence deserves special care because it is where the tics concentrate: the landing is a *conclusion the section proved*, in whatever shape that conclusion naturally takes — not a slot to be filled by the antithesis machine.
