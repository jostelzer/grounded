> Unedited example output. Mode: medium. Prompt: *"Use the scientific-review skill, medium mode: what's known about the gut microbiome's role in Parkinson's disease?"*

## What is known about the gut microbiome's role in Parkinson's disease?

**TL;DR** — Gut bacteria differ between people with Parkinson's and healthy people, reproducibly but by a small margin, and no organism has been shown to cause the disease. In mice, gut microbes can drive Parkinson's-like pathology; the human causal evidence is mixed. The firmest practical findings are that gut bacteria degrade levodopa and that microbiome-targeted treatment helps constipation, not movement.

### Case-control differences are real and repeatable — and small

- Re-analysing ten [16S rRNA](https://en.wikipedia.org/wiki/16S_ribosomal_RNA) datasets, Parkinson's and control communities differed significantly, but disease status explained **under 1%** of between-sample variation against 28–53% for the study of origin [Romano et al. 2021](https://doi.org/10.1038/s41531-021-00156-z).
- The largest uniformly processed cohort (490 patients, 234 controls, [shotgun metagenomics](https://en.wikipedia.org/wiki/Metagenomics)) found **84 of 257** species differently abundant — widespread but individually modest shifts [Wallen et al. 2022](https://doi.org/10.1038/s41467-022-34667-x).
- [Alpha diversity](https://en.wikipedia.org/wiki/Alpha_diversity) is not a marker: pooling seven datasets (631 patients, 436 controls), richness, evenness and Shannon index were unchanged after adjusting for age and sex [Plassais et al. 2021](https://doi.org/10.1093/braincomms/fcab113) — against the higher richness of the ten-dataset re-analysis, which tracked sequencing method [Romano et al. 2021](https://doi.org/10.1038/s41531-021-00156-z).

| Synthesis | Datasets | Participants | Core finding | |
|---|---|---|---|---|
| 16S re-analysis, harmonised | 10 | 1,211 samples (681 PD) | Disease explains <1% of variance; *Lactobacillus*, *Akkermansia*, *Bifidobacterium* up; *Lachnospiraceae*, *Faecalibacterium* down | [Romano et al. 2021](https://doi.org/10.1038/s41531-021-00156-z) |
| 16S meta-analysis, confounder-adjusted | 5 | 223 PD / 137 controls plus 4 cohorts | *Akkermansia* up; *Roseburia*, *Faecalibacterium* down across countries | [Nishiwaki et al. 2020](https://doi.org/10.1002/mds.28119) |
| Bayesian pooled analysis, patient-level | Systematic review, one pipeline | Patient-level data | Only a small taxa set survives harmonisation | [Kleine Bardenhorst et al. 2023](https://doi.org/10.1111/ene.15671) |
| Phylogenetic-placement re-analysis | 10 | 969 PD / 734 controls | Study and geography dominate; PD effect marginal | [Toh et al. 2022](https://doi.org/10.1016/j.parkreldis.2021.11.017) |
| Machine-learning meta-analysis | 22 | 4,489 samples | Within-study [AUC](https://en.wikipedia.org/wiki/Receiver_operating_characteristic) 71.9%, cross-study 61% | [Romano et al. 2025](https://doi.org/10.1038/s41467-025-56829-3) |

### The recurring signature is fewer butyrate producers and more mucin degraders

- Adjusted for body-mass index, constipation, sex, age and COMT inhibitors, [*Akkermansia*](https://en.wikipedia.org/wiki/Akkermansia) and *Catabacter* rose while [*Roseburia*](https://en.wikipedia.org/wiki/Roseburia), [*Faecalibacterium*](https://en.wikipedia.org/wiki/Faecalibacterium) and *Lachnospiraceae* fell, across five countries [Nishiwaki et al. 2020](https://doi.org/10.1002/mds.28119).
- Harmonising every step from bioinformatics to statistics leaves the same short list: *Akkermansia* and [*Bifidobacterium*](https://en.wikipedia.org/wiki/Bifidobacterium) up, *Roseburia* and *Faecalibacterium* down [Kleine Bardenhorst et al. 2023](https://doi.org/10.1111/ene.15671), [Li et al. 2023a](https://doi.org/10.1111/cns.13990).
- Those genera make [butyrate](https://en.wikipedia.org/wiki/Butyrate) or degrade mucus, so the pattern is read as a pro-inflammatory, thinner-barrier gut — an interpretation, not a demonstrated mechanism [Kleine Bardenhorst et al. 2023](https://doi.org/10.1111/ene.15671).
- In the large shotgun cohort a cluster of opportunistic pathogens (*Escherichia coli*, *Klebsiella* spp.) was elevated, fold change **2.63** (95% [CI](https://en.wikipedia.org/wiki/Confidence_interval) 1.7–4.1) [Wallen et al. 2022](https://doi.org/10.1038/s41467-022-34667-x).

### Metabolite data point to a leakier gut, not simply less fuel

- In 96 patients and 85 controls, [short-chain fatty acids](https://en.wikipedia.org/wiki/Short-chain_fatty_acid) (SCFAs) were **lower in stool but higher in plasma**, and faecal butyrate tracked motor score inversely (ρ = −0.40, p = 0.004) [Chen et al. 2022](https://doi.org/10.1212/wnl.0000000000013225).
- A second cohort (95 patients, 33 controls) reproduced the split and tied it to gut–blood barrier permeability worsened by constipation [Yang et al. 2022](https://doi.org/10.1002/mds.29063); a smaller study saw the plasma rise only after covariate adjustment (acetate 116.5 vs 108.2 µmol/L, p = 0.010) [Shin et al. 2020](https://doi.org/10.1002/mds.28016).
- Coupled metagenomics and metabolomics found greater microbial capacity to degrade mucin and host glycans, and modelled a microbial contribution to patients' folate deficiency [Rosario et al. 2021](https://doi.org/10.1016/j.celrep.2021.108807).

### Where a sample came from predicts more than whether the donor has Parkinson's

- Study and geography accounted for the largest share of compositional variation, and Caucasian and non-Caucasian cohorts differed [Toh et al. 2022](https://doi.org/10.1016/j.parkreldis.2021.11.017).
- Classifiers trained on 4,489 samples reached AUC 71.9% within a study but **61% on other studies**; pooling datasets raised leave-one-study-out AUC to 68% [Romano et al. 2025](https://doi.org/10.1038/s41467-025-56829-3).
- Single-population accuracy can look excellent — a 25-gene faecal classifier reached AUC 0.896 (95% CI 0.831–0.961) and 0.905 on independent Chinese validation [Qian et al. 2020](https://doi.org/10.1093/brain/awaa201) — which is not diagnostic readiness.
- Sixteen case-control studies reported over 100 differentially abundant taxa, the contradictions traced to sampling, extraction, sequencing and statistical choices [Boertien et al. 2019](https://doi.org/10.3233/jpd-191711); oral profiles even classified better (AUC 0.758) than gut profiles in 445 patients [Stagaman et al. 2024](https://doi.org/10.1038/s43856-024-00630-8).

### The changes precede diagnosis and are not just a drug effect

- In two cohorts of treatment-naive, newly diagnosed patients (136 and 56), composition already differed from controls, though **no single taxon replicated in both**; SCFA producers fell in each [Boertien et al. 2022](https://doi.org/10.1038/s41531-022-00395-8).
- Among 420 metagenomes nested in two US cohorts, strict anaerobes were depleted in both recent-onset and prodromal Parkinson's (classifier AUC 0.76) [Palacios et al. 2023](https://doi.org/10.1002/ana.26719).
- Butyrate-producer depletion and *Collinsella* enrichment were present in isolated [REM sleep behaviour disorder](https://en.wikipedia.org/wiki/Rapid_eye_movement_sleep_behavior_disorder) and in unaffected first-degree relatives, adjusted for antidepressants, laxatives and bowel frequency [Huang et al. 2023](https://doi.org/10.1038/s41467-023-38248-4), [Troci et al. 2025](https://doi.org/10.1177/1877718x251354931).
- In 43 non-manifesting [*GBA1*](https://en.wikipedia.org/wiki/Glucocerebrosidase) carriers, about a quarter of the microbiome was intermediate between controls and 271 patients, the direction replicating in US, Korean and Turkish cohorts [Menozzi et al. 2026](https://doi.org/10.1038/s41591-026-04318-5).
- Differences persisted on resampling 64 patients 2.25 years later, but taxa linked to *progression* were inconsistent [Aho et al. 2019](https://doi.org/10.1016/j.ebiom.2019.05.064).

### In mice, gut microbes can drive synucleinopathy — the models are strong, the extrapolation is not

- [α-synuclein](https://en.wikipedia.org/wiki/Alpha-synuclein)-overexpressing mice raised [germ-free](https://en.wikipedia.org/wiki/Germ-free_animal) had fewer motor deficits; colonising them with patient stool worsened impairment more than healthy-donor stool [Sampson et al. 2016](https://doi.org/10.1016/j.cell.2016.11.018).
- α-synuclein fibrils injected into mouse duodenum spread to the dorsal motor nucleus and later the substantia nigra with dopaminergic loss; truncal [vagotomy](https://en.wikipedia.org/wiki/Vagotomy) or α-synuclein deficiency prevented it [Kim et al. 2019](https://doi.org/10.1016/j.neuron.2019.05.035).
- Mild induced colitis in [*LRRK2*](https://en.wikipedia.org/wiki/LRRK2) G2019S mice raised colonic α-synuclein and caused dopaminergic loss, reversed by anti-TNF-α [Lin et al. 2022](https://doi.org/10.1002/mds.28890).
- Systemic endotoxin raised colonic α-synuclein and gut permeability over months **without** nigrostriatal degeneration — gut change alone was not sufficient [Kelly et al. 2014](https://doi.org/10.1002/mds.25736).
- This work underpins the body-first/brain-first framing, in which only some patients begin in the [enteric nervous system](https://en.wikipedia.org/wiki/Enteric_nervous_system) [Borghammer 2023](https://doi.org/10.1007/s00702-023-02633-6), [Park et al. 2024](https://doi.org/10.1016/j.nbd.2024.106655).

### Human evidence for the gut-first route is genuinely mixed

- Constipation is the strongest prodromal gut signal: 17 studies, 3.0 million participants, [OR](https://en.wikipedia.org/wiki/Odds_ratio) **2.36** (95% CI 1.93–2.88), with severe heterogeneity ([I²](https://en.wikipedia.org/wiki/Heterogeneity_(statistics)) = 90%) [Yao et al. 2023](https://doi.org/10.1159/000527513).
- Across 24,624 incident cases, gastroparesis (OR 4.64), dysphagia (3.58) and constipation (3.32) specifically preceded Parkinson's, but **vagotomy and inflammatory bowel disease were not associated**, and appendectomy predicted lower risk ([RR](https://en.wikipedia.org/wiki/Relative_risk) 0.48) [Konings et al. 2023](https://doi.org/10.1136/gutjnl-2023-329685).
- Vagotomy leans the Braak way without settling it: Danish truncal vagotomy beyond 20 years gave [HR](https://en.wikipedia.org/wiki/Hazard_ratio) 0.53 (95% CI 0.28–0.99) [Svensson et al. 2015](https://doi.org/10.1002/ana.24448); 9,430 Swedish vagotomised patients gave HR 0.96 (0.78–1.17) overall, 0.59 (0.37–0.93) for truncal surgery [Liu et al. 2017](https://doi.org/10.1212/wnl.0000000000003961).
- Appendectomy, proposed as an α-synuclein reservoir, shows nothing: pooled RR 1.01 (95% CI 0.90–1.12) over nine studies [Chin et al. 2025](https://doi.org/10.3389/fneur.2025.1619236) and HR 1.08 (0.94–1.23) in two prospective cohorts [Palacios et al. 2018](https://doi.org/10.1002/mds.109).
- [Inflammatory bowel disease](https://en.wikipedia.org/wiki/Inflammatory_bowel_disease) points both ways — RR 1.41 (1.19–1.66) [Zhu et al. 2019](https://doi.org/10.1016/j.dld.2018.09.017) and 1.17 (1.03–1.33) [Li et al. 2023b](https://doi.org/10.3389/fmed.2023.1137366) against OR 0.85 (0.80–0.91) in 89,790 Medicare cases [Camacho-Soto et al. 2018](https://doi.org/10.1016/j.parkreldis.2018.02.008) — while [Mendelian randomisation](https://en.wikipedia.org/wiki/Mendelian_randomization) inverts the observational story, putting genetically higher SCFA producers at *increased* risk [Jiang et al. 2023](https://doi.org/10.1111/ene.15848).

### The best-established consequence is drug handling, not neurodegeneration

- [*Enterococcus faecalis*](https://en.wikipedia.org/wiki/Enterococcus_faecalis) decarboxylates [levodopa](https://en.wikipedia.org/wiki/L-DOPA) to dopamine and *Eggerthella lenta* dehydroxylates the product; inhibiting the bacterial enzyme raised levodopa bioavailability in mice [Maini Rekdal et al. 2019](https://doi.org/10.1126/science.aau6323).
- [Small intestinal bacterial overgrowth](https://en.wikipedia.org/wiki/Small_intestinal_bacterial_overgrowth) affected 54.5% of 33 patients versus 20.0% of controls (p = 0.01); [rifaximin](https://en.wikipedia.org/wiki/Rifaximin) eradication improved motor fluctuations without changing levodopa pharmacokinetics, and 43% relapsed by six months [Fasano et al. 2013](https://doi.org/10.1002/mds.25522).
- Eradicating [*Helicobacter pylori*](https://en.wikipedia.org/wiki/Helicobacter_pylori) in 27 infected patients shortened levodopa onset by 14 minutes (p = 0.011) and lengthened ON time by 56 minutes — open-label and uncontrolled [Hashim et al. 2014](https://doi.org/10.1371/journal.pone.0112330).
- Reviews place dysbiosis alongside dysphagia, delayed gastric emptying and constipation as gut barriers to reliable levodopa response [Nyholm & Hellström 2021](https://doi.org/10.3233/jpd-202298), [Leta et al. 2023](https://doi.org/10.1111/ene.15734).

### Microbiome-targeted treatment reliably helps the bowel; motor benefit is unproven

| Trial | Design | n | Primary result | |
|---|---|---|---|---|
| Multistrain probiotic, 4 wk | RCT, placebo | 72 | Spontaneous bowel movements **+1.3/wk** (95% CI 0.8–1.8) | [Tan et al. 2021](https://doi.org/10.1212/wnl.0000000000010998) |
| Probiotics + [prebiotic](https://en.wikipedia.org/wiki/Prebiotic_(nutrition)) fibre, 4 wk | RCT, placebo | 120 | Complete bowel movements **+1.1/wk** (95% CI 0.4–1.8) | [Barichella et al. 2016](https://doi.org/10.1212/wnl.0000000000003127) |
| Nasojejunal [FMT](https://en.wikipedia.org/wiki/Fecal_microbiota_transplant), 12 mo | RCT, autologous placebo | 46 | [MDS-UPDRS](https://en.wikipedia.org/wiki/Unified_Parkinson%27s_Disease_Rating_Scale) motor −5.8 (95% CI −11.4 to −0.2) vs −2.7 (−8.3 to 2.9); p = 0.0235 | [Bruggeman et al. 2024](https://doi.org/10.1016/j.eclinm.2024.102563) |
| Colonic FMT, 6 mo | RCT, placebo | 48 | **No difference**: 0.97 points (95% CI −5.10 to 7.03, p = 0.75); GI adverse events 53% vs 7% | [Scheperjans et al. 2024](https://doi.org/10.1001/jamaneurol.2024.2305) |
| Oral FMT, 12 wk | RCT, placebo | 54 | MDS-UPDRS total group×time −6.56 (−12.98 to −0.13); baseline 9 points lower in the FMT arm | [Cheng et al. 2023](https://doi.org/10.1080/19490976.2023.2284247) |

- Pooled randomised evidence gives a small motor effect ([SMD](https://en.wikipedia.org/wiki/Standardized_mean_difference) −0.34, 95% CI −0.57 to −0.11) and a clear bowel effect (SMD 1.27, 0.35–2.2), with nothing on cognition, daily activities, quality of life or mood, at [GRADE](https://en.wikipedia.org/wiki/GRADE_approach) certainty no better than moderate [Gu et al. 2025](https://doi.org/10.3389/fcimb.2025.1627406).
- An independent synthesis of 15 trials found a comparable disease-burden effect (SMD −0.57, 95% CI −0.93 to −0.21, I² = 42%) but no pooled constipation benefit (SMD −1.01, −3.01 to 1.00, I² = 93%) [Chui et al. 2024](https://doi.org/10.1038/s41598-024-59250-w).
- Ten days of open-label prebiotic fibre in 20 patients raised SCFAs and lowered inflammatory markers and [neurofilament light chain](https://en.wikipedia.org/wiki/Neurofilament_light_polypeptide), but was uncontrolled [Hall et al. 2023](https://doi.org/10.1038/s41467-023-36497-x).
- The two rigorous FMT trials disagree on motor outcome; route, dosing, follow-up and donor selection are what an adequately powered multicentre trial would have to resolve [Bruggeman et al. 2024](https://doi.org/10.1016/j.eclinm.2024.102563), [Scheperjans et al. 2024](https://doi.org/10.1001/jamaneurol.2024.2305).

**Sources**

**Aho et al. 2019** Gut microbiota in Parkinson's disease: Temporal stability and relations to disease progression. *eBioMedicine*. https://doi.org/10.1016/j.ebiom.2019.05.064

**Barichella et al. 2016** Probiotics and prebiotic fiber for constipation associated with Parkinson disease. *Neurology*. https://doi.org/10.1212/wnl.0000000000003127

**Boertien et al. 2019** Increasing Comparability and Utility of Gut Microbiome Studies in Parkinson’s Disease: A Systematic Review. *Journal of Parkinson’s Disease*. https://doi.org/10.3233/jpd-191711

**Boertien et al. 2022** Fecal microbiome alterations in treatment-naive de novo Parkinson’s disease. *npj Parkinson's Disease*. https://doi.org/10.1038/s41531-022-00395-8

**Borghammer 2023** The brain-first vs. body-first model of Parkinson’s disease with comparison to alternative models. *Journal of Neural Transmission*. https://doi.org/10.1007/s00702-023-02633-6

**Bruggeman et al. 2024** Safety and efficacy of faecal microbiota transplantation in patients with mild to moderate Parkinson's disease (GUT-PARFECT): a double-blind, placebo-controlled, randomised, phase 2 trial. *eClinicalMedicine*. https://doi.org/10.1016/j.eclinm.2024.102563

**Camacho-Soto et al. 2018** Inflammatory bowel disease and risk of Parkinson's disease in Medicare beneficiaries. *Parkinsonism & Related Disorders*. https://doi.org/10.1016/j.parkreldis.2018.02.008

**Chen et al. 2022** Association of Fecal and Plasma Levels of Short-Chain Fatty Acids With Gut Microbiota and Clinical Severity in Patients With Parkinson Disease. *Neurology*. https://doi.org/10.1212/wnl.0000000000013225

**Cheng et al. 2023** Efficacy of fecal microbiota transplantation in patients with Parkinson’s disease: clinical trial results from a randomized, placebo-controlled design. *Gut Microbes*. https://doi.org/10.1080/19490976.2023.2284247

**Chin et al. 2025** Appendectomy and risk of Parkinson’s disease: a systematic review and meta-analysis. *Frontiers in Neurology*. https://doi.org/10.3389/fneur.2025.1619236

**Chui et al. 2024** Effects of microbiome-based interventions on neurodegenerative diseases: a systematic review and meta-analysis. *Scientific Reports*. https://doi.org/10.1038/s41598-024-59250-w

**Fasano et al. 2013** The role of small intestinal bacterial overgrowth in Parkinson's disease. *Movement Disorders*. https://doi.org/10.1002/mds.25522

**Gu et al. 2025** Efficacy of gut microbiota-targeted therapies in Parkinson’s disease: a systematic review and meta-analysis of randomized controlled trials. *Frontiers in Cellular and Infection Microbiology*. https://doi.org/10.3389/fcimb.2025.1627406

**Hall et al. 2023** An open label, non-randomized study assessing a prebiotic fiber intervention in a small cohort of Parkinson’s disease participants. *Nature Communications*. https://doi.org/10.1038/s41467-023-36497-x

**Hashim et al. 2014** Eradication of Helicobacter pylori Infection Improves Levodopa Action, Clinical Symptoms and Quality of Life in Patients with Parkinson's Disease. *PLoS ONE*. https://doi.org/10.1371/journal.pone.0112330

**Huang et al. 2023** Gut microbiome dysbiosis across early Parkinson’s disease, REM sleep behavior disorder and their first-degree relatives. *Nature Communications*. https://doi.org/10.1038/s41467-023-38248-4

**Jiang et al. 2023** Associations between gut microbiota and Parkinson disease: A bidirectional Mendelian randomization analysis. *European Journal of Neurology*. https://doi.org/10.1111/ene.15848

**Kelly et al. 2014** Progression of intestinal permeability changes and alpha‐synuclein expression in a mouse model of Parkinson's disease. *Movement Disorders*. https://doi.org/10.1002/mds.25736

**Kim et al. 2019** Transneuronal Propagation of Pathologic α-Synuclein from the Gut to the Brain Models Parkinson’s Disease. *Neuron*. https://doi.org/10.1016/j.neuron.2019.05.035

**Kleine Bardenhorst et al. 2023** Gut microbiota dysbiosis in Parkinson disease: A systematic review and pooled analysis. *European Journal of Neurology*. https://doi.org/10.1111/ene.15671

**Konings et al. 2023** Gastrointestinal syndromes preceding a diagnosis of Parkinson’s disease: testing Braak’s hypothesis using a nationwide database for comparison with Alzheimer’s disease and cerebrovascular diseases. *Gut*. https://doi.org/10.1136/gutjnl-2023-329685

**Leta et al. 2023** Gastrointestinal barriers to levodopa transport and absorption in Parkinson's disease. *European Journal of Neurology*. https://doi.org/10.1111/ene.15734

**Li et al. 2023a** Gut bacterial profiles in Parkinson's disease: A systematic review. *CNS Neuroscience & Therapeutics*. https://doi.org/10.1111/cns.13990

**Li et al. 2023b** Inflammatory bowel disease and risk of Parkinson’s disease: evidence from a meta-analysis of 14 studies involving more than 13.4 million individuals. *Frontiers in Medicine*. https://doi.org/10.3389/fmed.2023.1137366

**Lin et al. 2022** Mild Chronic Colitis Triggers Parkinsonism in LRRK2 Mutant Mice Through Activating TNF‐α Pathway. *Movement Disorders*. https://doi.org/10.1002/mds.28890

**Liu et al. 2017** Vagotomy and Parkinson disease. *Neurology*. https://doi.org/10.1212/wnl.0000000000003961

**Maini Rekdal et al. 2019** Discovery and inhibition of an interspecies gut bacterial pathway for Levodopa metabolism. *Science*. https://doi.org/10.1126/science.aau6323

**Menozzi et al. 2026** Microbiome signature of Parkinson’s disease in healthy and genetically at-risk individuals. *Nature Medicine*. https://doi.org/10.1038/s41591-026-04318-5

**Nishiwaki et al. 2020** Meta‐Analysis of Gut Dysbiosis in Parkinson's Disease. *Movement Disorders*. https://doi.org/10.1002/mds.28119

**Nyholm & Hellström 2021** Effects of Helicobacter pylori on Levodopa Pharmacokinetics. *Journal of Parkinson's Disease*. https://doi.org/10.3233/jpd-202298

**Palacios et al. 2018** Appendectomy and risk of Parkinson's disease in two large prospective cohorts of men and women. *Movement Disorders*. https://doi.org/10.1002/mds.109

**Palacios et al. 2023** Metagenomics of the Gut Microbiome in Parkinson's Disease: Prodromal Changes. *Annals of Neurology*. https://doi.org/10.1002/ana.26719

**Park et al. 2024** Difference in gut microbial dysbiotic patterns between body-first and brain-first Parkinson's disease. *Neurobiology of Disease*. https://doi.org/10.1016/j.nbd.2024.106655

**Plassais et al. 2021** Gut microbiome alpha-diversity is not a marker of Parkinson’s disease and multiple sclerosis. *Brain Communications*. https://doi.org/10.1093/braincomms/fcab113

**Qian et al. 2020** Gut metagenomics-derived genes as potential biomarkers of Parkinson’s disease. *Brain*. https://doi.org/10.1093/brain/awaa201

**Romano et al. 2021** Meta-analysis of the Parkinson’s disease gut microbiome suggests alterations linked to intestinal inflammation. *npj Parkinson's Disease*. https://doi.org/10.1038/s41531-021-00156-z

**Romano et al. 2025** Machine learning-based meta-analysis reveals gut microbiome alterations associated with Parkinson’s disease. *Nature Communications*. https://doi.org/10.1038/s41467-025-56829-3

**Rosario et al. 2021** Systematic analysis of gut microbiome reveals the role of bacterial folate and homocysteine metabolism in Parkinson’s disease. *Cell Reports*. https://doi.org/10.1016/j.celrep.2021.108807

**Sampson et al. 2016** Gut Microbiota Regulate Motor Deficits and Neuroinflammation in a Model of Parkinson’s Disease. *Cell*. https://doi.org/10.1016/j.cell.2016.11.018

**Scheperjans et al. 2024** Fecal Microbiota Transplantation for Treatment of Parkinson Disease. *JAMA Neurology*. https://doi.org/10.1001/jamaneurol.2024.2305

**Shin et al. 2020** Plasma Short‐Chain Fatty Acids in Patients With Parkinson's Disease. *Movement Disorders*. https://doi.org/10.1002/mds.28016

**Stagaman et al. 2024** Oral and gut microbiome profiles in people with early idiopathic Parkinson’s disease. *Communications Medicine*. https://doi.org/10.1038/s43856-024-00630-8

**Svensson et al. 2015** Vagotomy and subsequent risk of P arkinson's disease. *Annals of Neurology*. https://doi.org/10.1002/ana.24448

**Tan et al. 2021** Probiotics for Constipation in Parkinson Disease. *Neurology*. https://doi.org/10.1212/wnl.0000000000010998

**Toh et al. 2022** Gut microbiome in Parkinson's disease: New insights from meta-analysis. *Parkinsonism & Related Disorders*. https://doi.org/10.1016/j.parkreldis.2021.11.017

**Troci et al. 2025** Differences in intestinal microbiota in Parkinson's disease and isolated REM sleep behavior disorder. *Journal of Parkinson’s Disease*. https://doi.org/10.1177/1877718x251354931

**Wallen et al. 2022** Metagenomics of Parkinson’s disease implicates the gut microbiome in multiple disease mechanisms. *Nature Communications*. https://doi.org/10.1038/s41467-022-34667-x

**Yang et al. 2022** Parkinson's Disease Is Associated with Impaired Gut–Blood Barrier for Short‐Chain Fatty Acids. *Movement Disorders*. https://doi.org/10.1002/mds.29063

**Yao et al. 2023** Constipation in Parkinson’s Disease: A Systematic Review and Meta-Analysis. *European Neurology*. https://doi.org/10.1159/000527513

**Zhu et al. 2019** The risk of Parkinson’s disease in inflammatory bowel disease: A systematic review and meta-analysis. *Digestive and Liver Disease*. https://doi.org/10.1016/j.dld.2018.09.017
