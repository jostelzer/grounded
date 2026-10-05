# Popsci working steps

A good feature needs three things the evidence pipeline does not produce on its own: the **material** a reader's questions call for (how the thing works, how the key studies were run, what the numbers mean in daily life), a **writer with a clear desk and the sources at hand**, and **readers** who meet the article cold. These steps supply them. Use them for every popsci review, at every size. `style-popsci.md` says what the article must be.

Three roles work best as fresh agents that see only the inputs listed for them: the reader who asks questions, the writer, and the cold readers. This skill authorizes you to launch sub-agents, or separate non-interactive sessions of your own CLI, for these roles. If the host cannot do that, play each role yourself in sequence, re-reading only that role's inputs, and write "not independent" in its record.

| Step | Record in the case folder | Check |
|---|---|---|
| 1. Reader questions, before searching | `reader-questions.md` | `reader_questions.py --stage plan` |
| 2. Background search | `search-manifest.json`, lane `background` | `audit_search.py --style popsci` |
| 3. Story notes while reading | `facts.md` | `verify_claims.py synthesis-check --facts` |
| 4. Answer the questions; plan the story | `reader-questions.md`, Throughline in `synthesis.md` | `reader_questions.py --stage draft` |
| 5. Write | `review_draft.md`, `writer-notes.md` | `readability_profile.py` |
| 6. Cold read and one revision | `review_draft.v1.md`, `reader-copy.md`, `cold-read.md` | `readability_profile.py` |
| 7. Check and hand over | `popsci-audit.json` | `audit_popsci.py` |

## 1. Reader questions, before searching

Right after scoping, ask what a real reader would want to know. Launch a reader agent with only the user's request and the audience:

> You are [the reader, for example "a parent of a four-month-old with no science training"]. You have just read this question: "[request]". Write the 8 to 12 questions you would most want a good magazine article to answer, in your own words, naive ones included. Cover: what is going on; how it works; how scientists know (how the studies were done and how things were measured); how big the effects are and what they are worth compared with something you already know, such as a standard treatment or an everyday risk; why results might differ between studies or between a trial and ordinary life; what it means for someone in this situation and what people actually do about it; what nobody knows yet; and any word or unit you would need explained. Mark the most important half as core.

Save the result as `reader-questions.md`: a `Reader:` line, then entries `### Q1. …` with `- type:` (what, how-it-works, how-we-know, how-big, meaning, unknown, background, practical), `- priority:` (core, useful, optional) and `- status: open`. Merge duplicates. Always include, as core, what the key studies did and found: the answer rests on them, whatever the reader thought to ask. Keep to the sizes in `budgets.md`. The questions steer the research and the plan. They are not a checklist for the text: the article answers the core ones inside its story and leaves out those the story never reaches.

## 2. Search the background lane

The evidence lanes find studies that answer the question. They rarely find what a reader needs to understand those studies. For the how-it-works, background and practical questions, run `find_papers.py --lane background` for reviews, guidelines, consensus statements and foundational papers that define terms, explain mechanisms, give normal ranges and units, or describe standard practice. Background sources enter the ledger and pass the same citation checks as any other source. They are cited for explanation, never as evidence for the answer.

## 3. Keep story notes while reading

While reading, record in `facts.md` the small, checkable details a story needs. Each entry carries a verbatim quote from the stored text, written on one line:

```markdown
### F7. Most babies wore a movement monitor on the ankle.
- kind: method
- quote: [@Stremler2013effect] "verbatim passage from the stored text"
- answers: Q4
- supports: C3
```

Kinds: **method** (who took part, where, what was actually done and by whom, the comparison, the instrument and who recorded it, timing and duration), **definition**, **mechanism**, **scale** (normal ranges, conversions, how common something is), **background**, **context**, **detail** (a concrete particular that makes a study easy to picture), **practice** (what guidelines say, or what participants did day to day) and **voice** (the authors' own written words, when the wording adds something).

Aim the notes at the story, not at coverage: a full method card for each study the article is likely to tell as a story, and whatever the how-it-works and practical questions need. Findings about effects, associations and certainty stay in the synthesis, where strength and contrary evidence live. A yardstick taken from a background source, such as the usual effect of a standard treatment or a normal range, is a `scale` note: it sizes the answer and is never evidence for it. Then run:

```bash
python3 scripts/verify_claims.py synthesis-check --synthesis synthesis.md --ledger sources.json --evidence evidence/ --facts facts.md --size <size> --report synthesis-check.json
```

## 4. Answer the questions and plan the story

Update each question's `answered-by:` with the F and C entries that answer it and set `status:` to answered, partial or unanswerable. For the last two, give the reason on the same line after a dash: `- status: partial — no study reports absolute counts`. An open or partly answered question sends you back to step 2 or 3 first: "not in the sources I already have" is a reason to search, not a status. Only after a completed search comes up empty is a question unanswerable, and it then becomes one honest sentence in the article.

```bash
python3 scripts/reader_questions.py --questions reader-questions.md --stage draft --facts facts.md --synthesis synthesis.md --size <size>
```

In the synthesis **Throughline**, record the plan `style-popsci.md` asks for: the angle as a tension or surprise in one sentence, the yardstick that will size the key numbers, the handful of studies to tell as small stories, the line of thought from section to section, the claims the Verdict rests on (all of which must appear), and what stays out of the article.

## 5. Write

Launch the writer with a clear desk. Give it `style-popsci.md`, `writing-guide.md`, `synthesis.md`, `facts.md`, `reader-questions.md`, `notes.md`, the ledger, and read access to the stored texts (`evidence/`, `fulltexts/`). Give it no process documents: no search logs, audit contracts or figure rules. A writer holding those writes like a compliance report.

> You are the staff writer of a good science magazine. Read `style-popsci.md` and `writing-guide.md` first, then the case material. Write a [size] feature for [reader] that answers: "[question]". Body length: about [target] words (allowed range [range]).
>
> Before drafting, write a short plan in `writer-notes.md`: three possible angles in a line each, and the one you choose because it carries the most tension the evidence truly supports; the yardstick; the studies you will tell as small stories; the one design feature the reader must understand to read the numbers; the sections as one line of thought, each leading to the next; and what you are leaving out. Check the plan against the synthesis Verdict: everything it rests on must appear. Start from the Throughline and improve on it if you can.
>
> Then write `review_draft.md` as one continuous story. Write it to be enjoyed as well as trusted: something to see in the opening, a reason to read on at each turn, crossheads that say something, paragraphs that develop a point. Go to the stored text of each anchor study for the one or two details that make it vivid, give every finding the story rests on its size as a plain number, and give the reader the tools `style-popsci.md` lists: a yardstick, what a number is worth, how to read the evidence, why results differ. Cite every factual sentence in the body with the ledger key of the study it describes, `[@Key]`, right after the clause and before the punctuation; never cite a group of studies for one study's detail. The headline, standfirst and crossheads carry no citations. Use nothing from memory. If you cite a source that neither the synthesis nor `facts.md` quotes, add an entry for it to `facts.md` in the format already used there (`### F<n>. <sentence>`, `- kind:` one of method, definition, mechanism, scale, background, context, detail, practice, voice, and `- quote: [@Key] "verbatim passage"`). If the story needs something the sources do not contain, leave it out and list it under "Gaps" in your notes. Mark where a figure would teach something with a one-line note in square brackets on its own line. After the ending, add the table of exact figures the style guide describes, then the short scope and methods paragraph, headed **Scope and methods**.
>
> When the draft is complete, run `python3 scripts/readability_profile.py --review review_draft.md --report readability.json` and rewrite the passages it lists. Then read the piece once aloud in your head, as the reader, and fix whatever makes you stumble.

Keep this writer available for step 6. After it returns, re-run the step 3 check if `facts.md` changed, and treat each gap as a reason to return to step 2 or 3, or accept it as left out.

## 6. Cold read, then one revision

Keep the draft the readers will see, and make their copy, which has no citations:

```bash
cp review_draft.md review_draft.v1.md
python3 scripts/readability_profile.py --review review_draft.md --report readability.json --reader-copy reader-copy.md
```

Launch two cold readers. Each gets only `reader-copy.md`. The first is the reader named in `reader-questions.md` and also gets the core questions:

> Read this article once, as [persona]. Then report: (1) your takeaway in two sentences; (2) every sentence you had to read twice, quoted; (3) words or numbers you could not interpret; (4) what you still want to know; (5) where your attention drifted, where it felt like a list of studies, and any caveat or phrase that kept coming back; (6) sentences that sound like content but tell you nothing, quoted; (7) the one paragraph you would cut. Then answer each of these questions from the article alone, in a sentence or two, or write "not in the article": [core questions].

The second is a checker, a sceptical reader who is good with numbers. A checker's wishes make articles heavier, so the checker is asked for errors, not for wishes:

> Read this article once, as a sceptical reader who is good with numbers. Report only: (1) numbers that do not fit together, or that differ between the text and the closing table; (2) any claim that goes further than the study described could show; (3) every sentence you had to read twice, quoted; (4) sentences that sound like content but tell you nothing, quoted; (5) where it read like a list of studies or a run of caveats; (6) figures you wanted to check and could not find in the closing table. Do not list what else you would like to know.

Write `cold-read.md`: a `## Reader` section for each report, then `## Repairs` and `## Not fixing`. Decide as an editor would, for the article's main reader. The revision is an edit, not a second draft: it makes the article easier to read and never heavier.

- **Cut** what readers quoted as empty or tiring: a caveat that kept coming back, a stack of limitations after one result, notes on what was available only as a summary, a maxim that restates the point, a pointer to a figure in a sentence of its own, a check reported without its outcome, a third sentence where one explains it.
- **Rewrite** what got in the reader's way: a sentence read twice, a term or unit left unexplained, a stretch that read like a list of studies, a flat or missing ending. A sentence about method that confused a reader gets simpler; it is cut only if nothing depends on it.
- **Keep** what makes the article credible and worth reading, even when a reader did not mention it: the detail that lets a reader picture a study, the reason a method was done that way ("the traps were identical, so a change in equipment could not pass for a change in catch"), the one sentence that says how sure a result is, a concrete figure the story uses, and the plain sentence that corrects the belief the reader arrived with ("this does not mean half the world's insects have vanished"). Cutting these makes the claims read as assertions.
- **Correct** what the checker caught: a wrong or clashing number, a table row that disagrees with the text, a claim that outruns its study. Correct in about the same number of words, or cut the claim. A figure the checker could not find goes into the table only as one plain number in a row that is already there; otherwise leave it out and name it under `## Not fixing`. The table keeps one study and one result per row: never merge studies into a row to make room, and never send the reader to the table from a sentence or a caption.
- **Add** only when the main reader could not answer a core question, or was left without a yardstick, a reason for results that differ, or an account of what people in the studies actually did, and the sources answer it in one or two plain sentences. Reporting what a trial's programme consisted of is not advice. Work the answer into the paragraph where the reader would look for it, and cut as many words elsewhere. If the material is not in the case yet, go through steps 2 and 3 first; if a completed search finds nothing, the article says so in one sentence.
- **Do not add** another study, another limitation, an account of how a model adjusts for things, an explanation of what a statistic is not, or a note on what could be read only as a summary. These are the additions that readers of the finished article quote as its worst sentences. Name each declined request under `## Not fixing`, with the reason.

> ✗ Repair: "Explain that the 95% interval is uncertainty about the average effect, not a range of gains for individual babies." (The revised article said so three times.)
>
> ✓ Repair: "Readers stumbled on the interval sentence. Rewrite it as one plain sentence about how sure the result is; the exact interval is already in the table."

Send the repair list to the same writer, continuing that agent so it keeps its knowledge of the sources. If the host cannot continue an agent, launch a fresh writer with the step 5 inputs plus the draft. The writer revises once, then re-reads every changed section as a whole, so that no orphaned sentence, misfitting crosshead or pointless paragraph is left behind. The revised article is no longer than the draft (unless the draft was short of its target length), cites at most one more source and has no more sentences that limit or hedge; `audit_popsci.py` compares the two and says when a revision made the article heavier. It also stays within a tenth of the target length: when cutting takes it below, put back what readers enjoyed (a study's telling detail, a yardstick, what people actually did), never a caveat. Then re-run the profile. For a large feature, or when the revision restructured the piece, one fresh reader repeats the cold read.

## 7. Check and hand over

```bash
python3 scripts/audit_popsci.py --case . --size <size> --review review_draft.md --report popsci-audit.json
```

Then continue with the shared workflow: `format_references.py`, `validate_review.py`, the editorial read in `writing-guide.md`, figures, and the assertion audit. Pass `--facts facts.md` to `verify_claims.py extract`, so the quotes in the story notes reach the judge. Any repair the audit forces is made by the same rules: correct the sentence in plain words or cut the detail, and do not pile on. Marked rounding ("about 16 minutes"), exact unit conversions ("two hours" for 120 minutes) and plain frequencies ("about 38 in every 100" for 37.6%) are supported forms, listed in `claim-verification.md`; if the audit rejects a number, fix the number or its marking, never the readability. Run the profile once more on the final text.
