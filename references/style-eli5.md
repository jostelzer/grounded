# ELI5 style (explicit)

In `eli5` mode only. Write a connected explanation in short, flowing paragraphs for a smart reader with no science background at all. The evidence pipeline, citations, and verification are unchanged; only the architecture, language, and jargon treatment change. The model is not a simplified review — it is a great explainer: a patient teacher building a staircase, where every new idea stands only on ideas the reader already has. Do not use list bodies or structured bullet captions unless the user explicitly asks for bullets too; in that case use `bullets` as the structural style for validation and apply this plain-language register to it. The shared structure, citing, and quality-gate rules in `writing-guide.md` apply in full; ELI5 replaces the register rules as defined here.

**From the synthesis** (`synthesis.md`, per `synthesis-guide.md`): the staircase is the dependency order — sort the claims so each stands only on claims from earlier steps, and the ordering problem is already solved. Each step renders one claim with the one number its budget allows, chosen from that claim's `numbers` field and translated into reader units. The helper picture is chosen for the hardest claim in the ledger; the turn step is the strongest contrary line, retold as the reader's own doubt.

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

### <The turn — the reader's own doubt, in their words, e.g. "Wait — can we
trust those measurements?">
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
- **The staircase carries load downward.** No later step may undermine evidence an earlier step stated flatly: if the turn will reveal that the measurements are shaky, the earlier steps say "scientists have reported…" rather than a bare "Yes." — or the doubt moves earlier. A step that saws through the steps below it is a broken staircase. And each heading's connective must match what the reader just finished feeling: a "Why are scientists worried anyway?" is only right after reassurance, never after an alarming finding.
- **Headings are the reader's own questions.** The best ELI5 headings are the questions a curious reader would actually ask next: "So does it work?", "Why do the studies disagree?", "Is it safe to try?". A reader skimming only the headings should see the path of the explanation. Plain statements are fine too; teaser headings are not. **Template labels are never headings**: the slot names in the structure above ("the turn", "the hand-back", "step 2") and stock phrases like "But here's the thing" describe what a section does — the printed heading is always the reader's real question in the reader's words.
- **Tell the studies as little stories — one study, one story, one paragraph.** "Scientists gave 100 people the real pill and 100 people a dummy pill, and neither group knew which they got." A study told as a short story explains the method for free — the reader understands *why* the dummy pill matters without ever hearing the word "placebo". Use only real details from the paper: numbers of people, what was given, how long, what was measured. Never march through studies one sentence each — "One study found… Another found… A later study found…" is an inventory, not a story. Tell the one or two studies that matter as stories, and roll the rest up in plain words ("several other teams found the same thing"). The roll-up sentence still obeys the four-citation cap: cite the umbrella review that gathered them where one exists, otherwise the strongest three or four — never every primary at once.
- **One helper picture, chosen for the hardest idea, carried through or left out.** A single analogy is the explanation's backbone ("think of your immune system as a security team") — pick it for the hardest idea in the piece, not for a pretty opening. If the starting point plants a picture, that picture must come back in at least two later steps and be retired honestly at the hand-back — say where it breaks rather than stretching it. An analogy that appears once and vanishes is decoration; either make it carry weight or do not plant it. It must never smuggle in a claim the sources don't make.
- **Answer the question the reader is holding.** After each step, the natural next question changes. Track it. If step 2 shows the pill works a little, the reader is now wondering "then why doesn't everyone take it?" — that is step 3, whether or not a review would put it there.
- **The turn is a step, not a fine-print paragraph.** The evidence that disagrees gets its own honest step — the reader's own doubt as the heading — told with the same patience as the good news.
- **Hand the answer back.** The closing section passes the tell-a-friend test: one or two plain sentences the reader could actually say to someone else tomorrow and be right. Then what scientists still need to find out, in everyday words. If the honest summary is "nobody knows yet", hand back exactly that.

The language — unchanged rules:

- **Everyday words only.** "People in the study" not "participants"; "made-up pill" or "dummy pill" not "placebo"; "the studies disagree" not "heterogeneity". If a ten-year-old wouldn't know the word, don't use it.
- **Short sentences.** One idea per sentence. No semicolons, no nested clauses.
- **Paragraphs must flow.** Put related sentences together and use simple transitions so each section reads as an explanation, not a stack of facts. A paragraph is usually 2–4 sentences. Begin with the point, support it, then say what it means or lead into the next point.
- **Numbers stay, but say what they mean.** Not "SMD −0.34 (95% CI −0.68 to −0.00)" but "the people taking creatine improved a little more — about 2 points on a 52-point mood questionnaire, which is too small a change for most people to feel. And the studies were so different from each other that the real effect could be zero."
- **A numbers budget — the strictest of any style.** Each step carries at most one number in its prose, in reader units: fractions over percentages ("1 in 5", never "20.0%"), no decimals where a fraction or round number works, uncertainty as a plain-words range ("somewhere between twice and ten times as likely"), and a unit the reader has never held (micrograms per millilitre) translated into something they have or cut. Every other number rounds, groups, or goes. "The adjusted ratio was 4.53 (95% CI 2.00–10.27)" reworded but kept whole is not ELI5 — it is a statistic in a plain-language coat. This satisfies the intervals rule: in ELI5 the reported interval appears as the plain-words range, not as digits.
- **Jargon is rewritten, not linked.** Term links are for standard modes; here the plain words replace the term entirely. If a term truly cannot be avoided (a scale's name, a drug class), name it once, explain it in the same sentence in plain words, and give it the usual verified term link.
- **Honesty survives the simplification.** "We don't really know yet" instead of silently dropping uncertainty. Small studies are "too small to trust on their own", not omitted. Never round a weak finding up to a strong claim because the plain words feel less precise.
- **Citations unchanged.** Every empirical claim still carries its author–year DOI links. Place links naturally at the end of the sentence or short claim cluster they support, before terminal punctuation; do not collect them in a list-like citation dump.
- **Figure captions stay ELI5 too.** Use a short flowing paragraph of everyday sentences, explain what
  the reader sees and what remains uncertain, and keep the usual verified
  citations. Refer to the picture directly: “You can see the steps in
  `{{figure:mechanism}}`.”
- Small ELI5 uses 350–700 words spent on connected paragraphs rather than list items; medium 900–1,600; large 2,000–4,000. TL;DR, sources block, and the quality gate all apply as normal.

## The voice: how a good explainer actually sounds

The model is someone explaining across a kitchen table — a favorite teacher, not a narrator. The test for **every sentence, not just the terms**, is the **say-it-aloud test**: would you actually say this sentence to a friend? "The repeated findings make the link believable" fails that test even though no word in it is technical jargon — it is a researcher's sentence wearing simple words. The everyday-words rule covers the researcher's *ordinary* vocabulary too: exposure, detection, marker, identify, data, method, findings, reasonable-as-a-verdict. People across tables do not say those words; write what they do say.

**Do:**

- **Let people and things do things.** Teams found, doctors tested, the pieces showed up, the numbers went up. Never let an abstraction act: "the study's uncertainty stretched from twice to ten times" has an abstraction performing gymnastics — a person says "the true number could be anywhere from double to ten times as many."
- **Use contractions.** "It's", "don't", "can't" — this is spoken register; stiff contractions-free prose reads as a lecture.
- **Ask the reader's question out loud when it helps.** "So does that prove the pill did it? Not yet." The question-and-answer beat is native to this style and free rhythm.
- **Make the comparison the reader would make.** "Smaller than the width of a hair." "About as much as a grain of salt." Only comparisons that are faithful to the number — never decorative ones.
- **Keep the warmth in the verbs and the patience in the pacing** — never in rounding a weak finding up. "We don't really know yet" is a complete, honest, warm sentence.

**Don't — each pair shows a shape to avoid and the shape to write:**

- ✗ "The repeated findings make the link believable." → ✓ "So many teams have seen the same thing that it's hard to call it a fluke."
- ✗ "That makes the safety question reasonable." → ✓ "So it's fair to ask whether it's safe."
- ✗ "Teams used questionnaires to characterize sleep quality." → ✓ "Teams asked people how well they'd been sleeping."
- ✗ "The trial's uncertainty spanned a wide range." → ✓ "The true effect could be anywhere from tiny to quite big."
- ✗ "A systematic review judged the benefit 'probable.'" → ✓ "Scientists who gathered all the studies decided the benefit is 'probable' — likely real, but not certain."

One more spoken-voice rule: the devices stay invisible here too. Do not write "You can tell a friend:" before the hand-back — just write the sentence the reader could repeat; if it is truly plain, they will not need the label.
