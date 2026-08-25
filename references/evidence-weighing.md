# Weighing the evidence

A review weaves a story from studies of very unequal reliability. The reader needs to know, for each claim, how much weight it can bear. This file is about reading critically and then saying what you found in calibrated language.

## The hierarchy, and its limits

For questions of effect (does X change Y):

1. Systematic reviews and meta-analyses of randomised trials — but only as good as the trials in them and the review's own methods.
2. Large, pre-registered randomised trials with low risk of bias.
3. Smaller or earlier randomised trials.
4. Large prospective cohorts with good confounder control; natural experiments; Mendelian randomisation.
5. Case-control, cross-sectional, and ecological studies.
6. Mechanistic, animal, and in vitro evidence — tells you *whether X could* affect Y, not whether it does in the population of interest.
7. Case reports, expert opinion, narrative reviews.

For other question types (prevalence, diagnosis, prognosis, mechanism, qualitative) the ordering differs: a large representative survey beats an RCT for prevalence; a well-conducted cohort is the right design for prognosis; mechanism questions need lab evidence. Match the design to the question and say when a study's design is the wrong tool for the claim it is being used to support.

## How to read an abstract critically (what to note)

- **Design and comparator.** Randomised? Cluster? Controlled? Against what — placebo, usual care, waitlist, active comparator? Waitlist controls inflate effects.
- **Sample.** Size; who; where; how recruited. Small samples give unstable, often inflated estimates.
- **Outcome.** How measured; self-report or objective; primary or secondary; at what time point. Abstracts sometimes lead with the outcome that worked.
- **Effect with uncertainty.** Point estimate *and* interval; absolute as well as relative. An abstract that gives only p-values is hiding the size of the effect.
- **Registration and pre-specification.** Registered trials with pre-specified primary outcomes are more trustworthy.
- **Funding and conflicts.** Industry-funded trials of the sponsor's product are more likely to favour it.
- **What it does not say.** Missing follow-up, attrition, harms, or the null secondary outcomes.

For load-bearing papers, read the full text and check the methods against the abstract: abstracts overstate roughly a third of the time.

## Reading a meta-analysis

- How many studies and participants; what designs were pooled.
- The pooled effect with its CI — and the **prediction interval** if reported, which tells you the range of effects to expect in a new setting. A pooled effect of d = 0.3 with a prediction interval spanning zero means "on average positive, but not reliably so".
- Heterogeneity (I², τ²) and whether it was explained by moderators.
- Risk of bias of the included studies and whether it changed the result.
- Small-study effects / publication bias assessment, and whether the authors corrected for it (trim-and-fill results are sensitivity analyses, not better estimates).
- Date of the search: a 2018 meta-analysis cannot know about a 2022 trial. When a large later trial contradicts an earlier meta-analysis, the trial usually deserves more weight, and the review should say why (size, rigour, pre-registration).
- Quality of the review itself: registered protocol, multiple databases, duplicate screening. Reviews lacking these are weaker evidence even when they pool many studies.

## Red flags that should lower the weight you give a source

- Tiny sample with a large effect; no confidence interval; "significant" without a size.
- Outcome switching (the abstract's headline outcome is not the registered primary).
- Post-hoc subgroup claims presented as findings.
- Pooled effects dominated by one study or one research group.
- A claim that has never been replicated outside its originating lab.
- Journals with known quality problems; very high self-citation; retraction or expression of concern (the verifier flags retractions).
- Mechanistic plausibility used as if it were clinical evidence.

## Handling disagreement

When sources conflict, do not pick a side silently and do not average them into mush. State the disagreement, then offer the most likely explanations, which usually come from: differences in population or setting; differences in comparator; dose, duration, or implementation quality; outcome measure or timing; study size and quality (small early studies vs large later ones); publication bias in the earlier literature; genuine effect heterogeneity. Say which explanation the evidence supports, and if you cannot tell, say that.

A large, rigorous null trial after a run of small positive studies is the single most common pattern in applied science. Describe it as such and let the reader see the history.

## Calibrated language

Tie the words to the evidence. A workable scale:

| Evidence | Say |
|---|---|
| Multiple large RCTs or a high-quality meta-analysis with consistent results | "X reduces Y", "there is strong evidence that" |
| One large RCT or several moderate ones, mostly consistent | "X probably reduces Y", "the best available evidence indicates" |
| Small trials, or consistent observational evidence | "X may reduce Y", "observational studies associate X with", "the evidence is limited but suggests" |
| Conflicting results, or only mechanistic/animal evidence | "it is unclear whether", "has been proposed", "in animal models" |
| Single small study or unreplicated finding | "one study reported", "preliminary" |

Avoid: "proven", "well known", "clearly shows", "trend toward", "marginally significant", "no effect" (say "no evidence of an effect" or "little or no difference, with an interval of …").

## Numbers

Give the number when the source gives it. Prefer absolute effects (risk from 8% to 5%) alongside relative ones (RR 0.62). Give the interval. Give the sample size for anything that matters. Convert standardised effect sizes into something interpretable when possible (a g of 0.2 is "about a fifth of a standard deviation — small"). When a source reports only a p-value, say so rather than inventing a magnitude.

## Attribution

Findings belong to studies: "In the MYRIAD trial (8,376 pupils, 84 schools), …". Consensus belongs to syntheses: "Meta-analyses up to 2020 pooled …". Your synthesis is yours: "Taken together, these results suggest …". Speculation is flagged: "One possible explanation, not yet tested, is …". The reader should never be unsure whose claim they are reading.
