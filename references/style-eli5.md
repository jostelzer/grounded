# ELI5 style (explicit)

In `eli5` mode only. Write a connected explanation in short, flowing paragraphs for a smart reader with no science background at all. The evidence pipeline, citations, and verification are unchanged; only the architecture, language, and jargon treatment change. The model is not a simplified review — it is a great explainer: a patient teacher building a staircase, where every new idea stands only on ideas the reader already has. Do not use list bodies or structured bullet captions unless the user explicitly asks for bullets too; in that case use `bullets` as the structural style for validation and apply this plain-language register to it. The shared structure, citing, and quality-gate rules in `writing-guide.md` apply in full; ELI5 replaces the register rules as defined here.

Structure:

```text
## <The question in everyday words>

**TL;DR** — <the answer in 1–3 short, citation-free sentences>

<The starting point: one short paragraph that begins where the reader already
stands — something familiar they have seen, felt, or heard — and turns it into
the question. Cited if it makes an empirical claim.>

### <Step 1 — a plain heading; a simple question is often best>
<Short, connected paragraphs. Each step gives the reader exactly one new idea,
built on the steps before it.>

### <Step 2, and so on — each heading is the reader's own next question>
<…>

### <The "but here's the thing" step>
<The evidence that complicates or disagrees, as its own honest step.>

### <The hand-back>
<Bring the steps together and give the answer back in one or two sentences the
reader could repeat to a friend. Then say, in plain words, what scientists
still need to find out. No new evidence.>

**Sources**
<same generated sources block as always>
```

The story flow — what makes it an explanation rather than a stack of simple facts:

- **Start where the reader stands.** The opening paragraph anchors in something the reader already knows — the sniffle they get every winter, the powder tub at the gym, the label on the bottle — and turns that familiar thing into the question. Not an invented anecdote: an everyday observation or a verified fact, nothing more specific than the sources support.
- **Build a staircase, not a pile.** Order the sections by what the reader needs to understand *next*, not by evidence category or by how a review would organize it. Each section adds exactly one new idea, and uses only ideas from earlier steps. If a sentence needs something not yet explained, the steps are in the wrong order — reorder rather than patch with a forward reference ("more on this later" is a broken staircase).
- **Headings are the reader's own questions.** The best ELI5 headings are the questions a curious reader would actually ask next: "So does it work?", "Why do the studies disagree?", "Is it safe to try?". A reader skimming only the headings should see the path of the explanation. Plain statements are fine too; teaser headings are not.
- **Tell the studies as little stories.** "Scientists gave 100 people the real pill and 100 people a dummy pill, and neither group knew which they got." A study told as a short story explains the method for free — the reader understands *why* the dummy pill matters without ever hearing the word "placebo". Use only real details from the paper: numbers of people, what was given, how long, what was measured.
- **One helper picture, introduced and retired.** A single analogy may be the explanation's backbone ("think of your immune system as a security team"). Introduce it early, reuse it so each step lands somewhere familiar, and retire it honestly when it stops fitting — say where the picture breaks rather than stretching it. It must never smuggle in a claim the sources don't make.
- **Answer the question the reader is holding.** After each step, the natural next question changes. Track it. If step 2 shows the pill works a little, the reader is now wondering "then why doesn't everyone take it?" — that is step 3, whether or not a review would put it there.
- **The turn is a step, not a fine-print paragraph.** The evidence that disagrees gets its own honest step ("But here's the thing — the bigger the study, the smaller the effect"), told with the same patience as the good news.
- **Hand the answer back.** The closing section passes the tell-a-friend test: one or two plain sentences the reader could actually say to someone else tomorrow and be right. Then what scientists still need to find out, in everyday words. If the honest summary is "nobody knows yet", hand back exactly that.

The language — unchanged rules:

- **Everyday words only.** "People in the study" not "participants"; "made-up pill" or "dummy pill" not "placebo"; "the studies disagree" not "heterogeneity". If a ten-year-old wouldn't know the word, don't use it.
- **Short sentences.** One idea per sentence. No semicolons, no nested clauses.
- **Paragraphs must flow.** Put related sentences together and use simple transitions so each section reads as an explanation, not a stack of facts. A paragraph is usually 2–4 sentences. Begin with the point, support it, then say what it means or lead into the next point.
- **Numbers stay, but say what they mean.** Not "SMD −0.34 (95% CI −0.68 to −0.00)" but "the people taking creatine improved a little more — about 2 points on a 52-point mood questionnaire, which is too small a change for most people to feel. And the studies were so different from each other that the real effect could be zero."
- **Jargon is rewritten, not linked.** Term links are for standard modes; here the plain words replace the term entirely. If a term truly cannot be avoided (a scale's name, a drug class), name it once, explain it in the same sentence in plain words, and give it the usual verified term link.
- **Honesty survives the simplification.** "We don't really know yet" instead of silently dropping uncertainty. Small studies are "too small to trust on their own", not omitted. Never round a weak finding up to a strong claim because the plain words feel less precise.
- **Citations unchanged.** Every empirical claim still carries its author–year DOI links. Place links naturally at the end of the sentence or short claim cluster they support, before terminal punctuation; do not collect them in a list-like citation dump.
- **Figure captions stay ELI5 too.** Use a short flowing paragraph of everyday sentences, explain what
  the reader sees and what remains uncertain, and keep the usual verified
  citations. Refer to the picture directly: “You can see the steps in
  `{{figure:mechanism}}`.”
- Small ELI5 uses 350–700 words spent on connected paragraphs rather than list items; medium 900–1,600; large 2,000–4,000. TL;DR, sources block, and the quality gate all apply as normal.
