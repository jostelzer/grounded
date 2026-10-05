# Popsci writing evaluation set

Use this set when changing the popular-science rules or working steps. It answers one question: do readers prefer the new articles, understand them at least as well, and are they still faithful to the sources?

## Contents

- `bp/`, `microplastics/`: frozen evidence packets (trimmed ledger, synthesis, reading notes) with a comprehension quiz written from the packet before any article existed (`quiz.json`, and `quiz-reader.json` without answers). Both were used while designing the October 2026 rules, so they are regression cases, not held-out tests.
- `popsci-feature-corpus.json`: every body paragraph of 24 published features labelled by function (scene, orientation, method, finding, explanation, context, complication, voice, practical, payoff), with word counts and whether it carries a number or a quote. It stores no article text.
- `score_comprehension.py`: validates a quiz and scores readers' answers (accuracy, points the article does not cover, over- and under-confident certainty answers).
- `paragraph_profile.py`: compares a labelled draft with the corpus.

The readability profile that ships with the skill (`skills/grounded/scripts/readability_profile.py`) needs no labels and runs on any draft.

## How to compare two versions of the rules

1. Pick topics the rule author has not looked at. Add a packet here afterwards if it should become a regression case.
2. Have the same model write each topic under each version, from the same packet.
3. **Preference (primary):** four cold readers, two personas in both reading orders, read the unlabelled articles and rank them by which they would rather read and recommend, with reasons.
4. **Comprehension:** an independent agent writes the quiz from the packet before the articles exist. Two cold readers per article answer from that article alone.
5. **Fidelity:** a blind judge checks each article against the stored source texts and lists severe, moderate and minor errors.
6. Predeclare the decision rule, report each topic separately, and keep the raw reader reports.

A version is better only if readers prefer it, comprehension does not drop and fidelity does not get worse. Results from past runs are under `output/popsci-*-eval-*/` (not in version control).

## Results so far (October 2026, gpt-6.1-sol in Codex for every condition)

Quiz columns follow the order of the comparison column.

| Topic | Comparison | Preference | Quiz | Fidelity |
|---|---|---|---|---|
| Smartphone bans (small, held out) | lean rules vs first repair vs old rules | lean first 3 of 4; old rules last 4 of 4 | 100% / 92% / 88% | negligible differences |
| Seed oils (medium, held out) | same three | first repair first 4 of 4; old rules last 4 of 4 | 92% / 100% / 100% | no severe errors; old rules weakest |
| Stopping semaglutide (medium, held out) | current rules vs first repair | current 4 of 4 | 92% vs 100% | current more faithful |
| Seed oils (recheck, not held out) | current vs first repair vs lean | first repair first 3 of 4; current second 3, first 1; lean last 4 of 4 | not run | not run |
| Infant sleep (complete run) | current vs the October original | current 4 of 4 | not run | pipeline audit passed |
| Infant sleep (two complete runs vs the original) | run A vs run B vs original | original last 4 of 4; run A first 3, run B first 1 | not run | pipeline audits passed |
| Insects (complete run, non-medical) | single article, two readers | recommend "with reservations"; counting methods 8 of 10, ease 5–6 | 5 of 5 core questions, both readers | 0 severe, 1 moderate, 9 minor |
| Cold-read step alone, infant sleep | revised vs unrevised vs run A | revised over unrevised 4 of 4; run A first 4 of 4 | not run | not run |
| Cold-read step alone, insects | revised (refined wording) vs unrevised | revised 4 of 4, each slight | not run | not run |

Four readers and one article per condition is a small sample: read the table as direction. Two complete runs of one question differed by two points on ease of reading, so a single run says little about a rule change; compare versions of a step on the same draft where possible. The current rules are the lean rules merged with the first repair's storytelling base.
