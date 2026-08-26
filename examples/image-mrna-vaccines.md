## How do mRNA vaccines work?

**TL;DR** — An mRNA vaccine gives cells a short-lived recipe for one pathogen protein, not the pathogen itself. A lipid shell gets the recipe into cells and also helps alert the immune system; antigen production then recruits antibodies, memory B cells and T cells. The platform has delivered strong protection from severe respiratory disease, but protection from infection wanes, variant matching is imperfect, and myocarditis is a rare risk concentrated in young males after dose 2.

### The platform is a transient, programmable protein factory

- The payload is [messenger RNA](https://en.wikipedia.org/wiki/Messenger_RNA) (mRNA) inside a [lipid nanoparticle](https://en.wikipedia.org/wiki/Lipid_nanoparticle) (LNP): the particle protects RNA, promotes cell entry and cytoplasmic release, and [ribosomes](https://en.wikipedia.org/wiki/Ribosome) translate the sequence without the RNA entering the nucleus or becoming DNA. [Chaudhary et al. 2021](https://doi.org/10.1038/s41573-021-00283-5), [Hou et al. 2021](https://doi.org/10.1038/s41578-021-00358-0), [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y)
- Ionizable lipids bind RNA during particle formation but are closer to neutral in the body, improving delivery over permanently charged carriers. [Cullis & Felgner 2024](https://doi.org/10.1038/s41573-024-00977-6), [Hou et al. 2021](https://doi.org/10.1038/s41578-021-00358-0)
- The encoded [antigen](https://en.wikipedia.org/wiki/Antigen) is designed: COVID-19 vaccines used prefusion-stabilized spike, building on earlier coronavirus structural work, so new targets can reuse the manufacturing platform. [Corbett et al. 2020](https://doi.org/10.1038/s41586-020-2622-0), [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y)

### Modified RNA and purification made useful expression possible

- Unmodified RNA activates innate sensors: substituting modified nucleosides suppressed signalling through [Toll-like receptors](https://en.wikipedia.org/wiki/Toll-like_receptor) 3, 7 and 8 and reduced cytokine release from human [dendritic cells](https://en.wikipedia.org/wiki/Dendritic_cell). [Karikó et al. 2005](https://doi.org/10.1016/j.immuni.2005.06.008)
- Removing double-stranded RNA contaminants by high-performance liquid chromatography eliminated detectable interferon and inflammatory-cytokine induction in the tested cells and raised translation **10- to 1,000-fold**. [Karikó et al. 2011](https://doi.org/10.1093/nar/gkr695)
- Translation fidelity is a real design constraint: N1-methylpseudouridine caused +1 [ribosomal frameshifting](https://en.wikipedia.org/wiki/Ribosomal_frameshift) and immune recognition of off-target products in mice and people, although no adverse outcome was reported and synonymous recoding reduced the signal. [Mulroney et al. 2024](https://doi.org/10.1038/s41586-023-06800-3)

### The carrier is both delivery vehicle and immune alarm

- In mice, the tested LNP formulation acted as an adjuvant even without antigen-encoding RNA, driving T-follicular-helper and germinal-centre responses through its ionizable lipid and interleukin-6; the exact pathway and magnitude cannot be assumed for every LNP or for humans. [Alameh et al. 2021](https://doi.org/10.1016/j.immuni.2021.11.001), [Verbeke et al. 2022](https://doi.org/10.1016/j.immuni.2022.10.014)
- Mouse tissue profiling found vaccine mRNA chiefly in draining-node monocytes, macrophages and migratory dendritic cells at day 1; MDA5-[type I interferon](https://en.wikipedia.org/wiki/Interferon_type_I) signalling supported antigen-specific CD8 T-cell expansion, while several other proposed pathways were dispensable in that model. [Li et al. 2022](https://doi.org/10.1038/s41590-022-01163-9)

### Lymph nodes convert a brief signal into durable immune memory

- Early human trials found strong neutralizing antibodies and TH1-skewed CD4 and [CD8 T-cell](https://en.wikipedia.org/wiki/Cytotoxic_T_cell) responses, while CD8 cells expanded after the first dose before neutralizing antibodies had fully matured. [Sahin et al. 2020](https://doi.org/10.1038/s41586-020-2814-7), [Oberhardt et al. 2021](https://doi.org/10.1038/s41586-021-03841-4)
- Serial lymph-node sampling found spike-specific [germinal-centre](https://en.wikipedia.org/wiki/Germinal_center) B cells for at least **12 weeks** and T-follicular-helper cells for about **6 months**, although these intensive studies involved small, relatively young cohorts. [Turner et al. 2021](https://doi.org/10.1038/s41586-021-03738-2), [Mudd et al. 2022](https://doi.org/10.1016/j.cell.2021.12.026)
- Across 1,540 tracked B-cell clones, somatic mutation rose **3.5-fold over six months**; affinity-matured [memory B cells](https://en.wikipedia.org/wiki/Memory_B_cell) and bone-marrow plasma cells persisted even as circulating antibody declined. [Kim et al. 2022](https://doi.org/10.1038/s41586-022-04527-1)

![Mechanism map showing a lipid nanoparticle carrying modified mRNA into a cell, transient antigen production, innate immune sensing in a draining lymph node, and the branching formation of antibodies, memory B cells and T cells; dashed borders mark mainly mouse-derived mechanistic evidence.](image-mrna-vaccines-generated.png)

*Caption: the evidence-supported route from injection to memory. Delivery, transient expression and persistent human lymph-node responses are observed; detailed sensing pathways and LNP adjuvanticity rest mainly on mouse experiments. [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y), [Alameh et al. 2021](https://doi.org/10.1016/j.immuni.2021.11.001), [Li et al. 2022](https://doi.org/10.1038/s41590-022-01163-9), [Turner et al. 2021](https://doi.org/10.1038/s41586-021-03738-2), [Kim et al. 2022](https://doi.org/10.1038/s41586-022-04527-1)*

### Antibodies predict protection, but platform performance depends on pathogen and outcome

- The pivotal placebo-controlled COVID-19 trials reported **95.0%** efficacy (95% credible interval 90.3-97.6; n=43,448) for BNT162b2 and **94.1%** (95% CI 89.3-96.8; n=30,420) for mRNA-1273 against symptomatic disease before major immune-escape variants; six-month BNT162b2 efficacy was 91.3% (89.0-93.2) and 96.7% (80.3-99.9) against severe disease. [Polack et al. 2020](https://doi.org/10.1056/nejmoa2034577), [Baden et al. 2021](https://doi.org/10.1056/nejmoa2035389), [Thomas et al. 2021](https://doi.org/10.1056/nejmoa2110345)
- In mRNA-1273 recipients, estimated [vaccine efficacy](https://en.wikipedia.org/wiki/Vaccine_efficacy) rose from 78% (95% CI 54-89) at a neutralizing titre of 10 to 96% (94-98) at 1,000; a 24-study meta-analysis also linked neutralization loss to reduced protection across variants. Correlation does not mean antibodies mediate every component of protection. [Gilbert et al. 2022](https://doi.org/10.1126/science.abm3425), [Cromer et al. 2022](https://doi.org/10.1016/s2666-5247%2821%2900267-6)
- The platform generalizes but does not guarantee success: one-dose mRNA-1345 prevented RSV lower-respiratory disease by 83.7% (95.88% CI 66.0-92.2; n=35,541), whereas an influenza formulation produced stronger A but weaker B responses than licensed vaccine. [Wilson et al. 2023](https://doi.org/10.1056/nejmoa2307079), [Ma et al. 2025](https://doi.org/10.1038/s41467-025-61153-x), [Kandinov et al. 2025](https://doi.org/10.1080/21645515.2025.2484088), [Whitaker et al. 2023](https://doi.org/10.1097/qco.0000000000000948)

| Vaccine | Evidence | Main result | Important boundary |
|---|---|---|---|
| BNT162b2 | Placebo RCT, n=43,448 | 95.0% efficacy against symptomatic COVID-19 | Ancestral-virus era [Polack et al. 2020](https://doi.org/10.1056/nejmoa2034577) |
| mRNA-1273 | Placebo RCT, n=30,420 | 94.1% efficacy; 30 severe cases, all placebo | Ancestral-virus era [Baden et al. 2021](https://doi.org/10.1056/nejmoa2035389) |
| mRNA-1345 RSV | Placebo RCT, n=35,541, age at least 60 | 83.7% against lower-respiratory disease with at least 2 signs | Median follow-up 112 days [Wilson et al. 2023](https://doi.org/10.1056/nejmoa2307079) |
| ARCT-154 self-amplifying RNA | Placebo RCT, 5 micrograms | 56.6% against any and 95.3% against severe COVID-19 | Mostly Delta; short follow-up [Hồ et al. 2024](https://doi.org/10.1038/s41467-024-47905-1) |

### Protection wanes fastest where the airway and variants matter most

- Across 78 estimates, effectiveness fell **21.0 percentage points** (95% CI 13.9-29.8) against infection from month 1 to 6, versus **10.0 points** (6.1-15.4) against severe disease; only 3 of 18 included studies had low overall risk of bias. [Feikin et al. 2022](https://doi.org/10.1016/s0140-6736%2822%2900152-0)
- The anatomical pattern fits: vaccinated people had strong blood responses but lower airway neutralization and no detectable spike-specific B or T cells in bronchoalveolar lavage, unlike convalescents. This small study supports, but does not by itself prove, a mechanism for breakthrough infection. [Tang et al. 2022](https://doi.org/10.1126/sciimmunol.add4853)
- Variant matching helps incompletely. A BA.1-bivalent booster raised BA.1 titres over the ancestral booster but did not test effectiveness; later BQ.1.1 and XBB.1 escaped much BA.5-bivalent-dose neutralization. [Chalkias et al. 2022](https://doi.org/10.1056/nejmoa2208343), [Kurhade et al. 2023](https://doi.org/10.1038/s41591-022-02162-x)
- A 28-study synthesis found bivalent boosters added about **28-31% relative effectiveness** against infection and **58-62%** against severe outcomes versus earlier-dose comparators, with substantial heterogeneity. [Song et al. 2024](https://doi.org/10.1016/j.vaccine.2024.04.049)
- XBB.1.5-vaccine effectiveness in 53.4 million adults fell by month 5 to 26.7% against infection, 52.3% against hospitalization and 69.4% against death; JN.1 replacement reduced it further. Antibody responses remained biased toward epitopes shared with the ancestral strain, with limited truly XBB-specific recruitment in some people. [Ma et al. 2026](https://doi.org/10.1016/j.jmii.2025.07.002), [Johnston et al. 2024](https://doi.org/10.1016/j.immuni.2024.02.017)

![Two equal-sized evidence rows report the average 1-to-6-month decline in vaccine effectiveness against infection and severe disease with confidence intervals; a side panel explains immune memory, the airway gap and variant escape as supported but incomplete explanations.](image-mrna-vaccines-2-generated.png)

*Caption: waning is outcome-dependent. The two estimates and 95% confidence intervals come from a pre-Omicron systematic review/meta-regression; equal row sizes deliberately avoid encoding a false visual scale. Airway sampling and later variant studies explain why infection protection is more fragile, but they do not partition the decline quantitatively. [Feikin et al. 2022](https://doi.org/10.1016/s0140-6736%2822%2900152-0), [Tang et al. 2022](https://doi.org/10.1126/sciimmunol.add4853), [Kurhade et al. 2023](https://doi.org/10.1038/s41591-022-02162-x), [Ma et al. 2026](https://doi.org/10.1016/j.jmii.2025.07.002)*

### Myocarditis is rare, real, and sharply concentrated by age, sex, dose and product

- Active surveillance of 11.8 million mRNA doses found no prespecified serious-outcome signal and anaphylaxis at about **5 per million doses**; a separate matched national study found most examined adverse events were not elevated but confirmed a myocarditis excess. [Klein et al. 2021](https://doi.org/10.1001/jama.2021.15072), [Barda et al. 2021](https://doi.org/10.1056/nejmoa2110475)
- A 99-million-person multinational study reproduced the myocarditis/pericarditis signal after mRNA vaccination; its observed-versus-expected design remains sensitive to background-rate assumptions. [Faksova et al. 2024](https://doi.org/10.1016/j.vaccine.2024.01.100)
- In 39.6 million adolescent doses, pooled myopericarditis was **43.5 per million** (95% CI 30.8-61.6): **66.0** in males versus **10.1** in females, and **60.4** after dose 2 versus **16.6** after dose 1. [Guo et al. 2023](https://doi.org/10.1016/j.vaccine.2023.05.049)
- Nordic registers showed that males aged 16-24 had **55.5 excess cases per million** after BNT162b2 dose 2 and **183.9 per million** after mRNA-1273 dose 2; English data likewise found the highest relative risk after mRNA-1273 dose 2 and a smaller booster signal. [Karlstad et al. 2022](https://doi.org/10.1001/jamacardio.2022.0583), [Stowe et al. 2023](https://doi.org/10.1371/journal.pmed.1004245)
- Infection is not a uniform comparator: across all ages, infection-associated myocarditis risk was higher, but among men younger than 40 the estimated excess after mRNA-1273 dose 2 was 97 per million versus 16 per million after a positive test. [Patone et al. 2022](https://doi.org/10.1161/circulationaha.122.059970)

![Myocarditis evidence figure with two non-comparable panels: pooled adolescent cases per million doses split by sex and dose number, and Nordic excess cases per million vaccinated males aged 16 to 24 after dose 2 split by vaccine product; uncertainty intervals and denominator warnings are explicit.](image-mrna-vaccines-3-nature.svg)

*Caption: the signal is heterogeneous, not a single platform-wide rate. Panel A pools observational adolescent studies; panel B uses Nordic register-derived excess events in young men. Different populations, denominators and axes make within-panel comparisons valid but cross-panel marker positions non-comparable. [Guo et al. 2023](https://doi.org/10.1016/j.vaccine.2023.05.049), [Karlstad et al. 2022](https://doi.org/10.1001/jamacardio.2022.0583), [Patone et al. 2022](https://doi.org/10.1161/circulationaha.122.059970), [Faksova et al. 2024](https://doi.org/10.1016/j.vaccine.2024.01.100)*

### Speed and programmability remain constrained by stability, delivery and evidence gaps

- Purification, particle mixing, scale-up and cold-chain stability remain bottlenecks. [Rosa et al. 2021](https://doi.org/10.1016/j.vaccine.2021.03.038), [Hou et al. 2021](https://doi.org/10.1038/s41578-021-00358-0)
- [Freeze-drying](https://en.wikipedia.org/wiki/Freeze-drying) preserved one mRNA-LNP formulation for 12 weeks at room temperature and 24 weeks at 4 degrees C in preclinical tests, but another study found post-drying RNA retention and translation depended strongly on the ionizable lipid; thermostability is therefore formulation-specific. [Muramatsu et al. 2022](https://doi.org/10.1016/j.ymthe.2022.02.001), [Lamoot et al. 2023](https://doi.org/10.1039/d2bm02031a)
- [Self-amplifying RNA](https://en.wikipedia.org/wiki/Self-amplifying_RNA) includes replication machinery and can reduce dose: 5-microgram ARCT-154 protected against severe Delta-era COVID-19, and as a fourth-dose booster it produced non-inferior ancestral and higher BA.4/5 neutralization than BNT162b2 at day 28; neither result establishes long-term superiority. [Blakney et al. 2021](https://doi.org/10.3390/vaccines9020097), [Hồ et al. 2024](https://doi.org/10.1038/s41467-024-47905-1), [Oda et al. 2024](https://doi.org/10.1016/s1473-3099%2823%2900650-3)

**Sources**

**Alameh et al. 2021** Lipid nanoparticles enhance the efficacy of mRNA and protein subunit vaccines by inducing robust T follicular helper cell and humoral responses. *Immunity*. https://doi.org/10.1016/j.immuni.2021.11.001

**Baden et al. 2021** Efficacy and Safety of the mRNA-1273 SARS-CoV-2 Vaccine. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2035389

**Barda et al. 2021** Safety of the BNT162b2 mRNA Covid-19 Vaccine in a Nationwide Setting. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2110475

**Blakney et al. 2021** An Update on Self-Amplifying mRNA Vaccine Development. *Vaccines*. https://doi.org/10.3390/vaccines9020097

**Chalkias et al. 2022** A Bivalent Omicron-Containing Booster Vaccine against Covid-19. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2208343

**Chaudhary et al. 2021** mRNA vaccines for infectious diseases: principles, delivery and clinical translation. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-021-00283-5

**Corbett et al. 2020** SARS-CoV-2 mRNA vaccine design enabled by prototype pathogen preparedness. *Nature*. https://doi.org/10.1038/s41586-020-2622-0

**Cromer et al. 2022** Neutralising antibody titres as predictors of protection against SARS-CoV-2 variants and the impact of boosting: a meta-analysis. *The Lancet Microbe*. https://doi.org/10.1016/s2666-5247(21)00267-6

**Cullis & Felgner 2024** The 60-year evolution of lipid nanoparticles for nucleic acid delivery. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-024-00977-6

**Faksova et al. 2024** COVID-19 vaccines and adverse events of special interest: A multinational Global Vaccine Data Network (GVDN) cohort study of 99 million vaccinated individuals. *Vaccine*. https://doi.org/10.1016/j.vaccine.2024.01.100

**Feikin et al. 2022** Duration of effectiveness of vaccines against SARS-CoV-2 infection and COVID-19 disease: results of a systematic review and meta-regression. *The Lancet*. https://doi.org/10.1016/s0140-6736(22)00152-0

**Gilbert et al. 2022** Immune correlates analysis of the mRNA-1273 COVID-19 vaccine efficacy clinical trial. *Science*. https://doi.org/10.1126/science.abm3425

**Guo et al. 2023** Incidence of myopericarditis after mRNA COVID-19 vaccination: A meta-analysis with focus on adolescents aged 12–17 years. *Vaccine*. https://doi.org/10.1016/j.vaccine.2023.05.049

**Hou et al. 2021** Lipid nanoparticles for mRNA delivery. *Nature Reviews Materials*. https://doi.org/10.1038/s41578-021-00358-0

**Hồ et al. 2024** Safety, immunogenicity and efficacy of the self-amplifying mRNA ARCT-154 COVID-19 vaccine: pooled phase 1, 2, 3a and 3b randomized, controlled trials. *Nature Communications*. https://doi.org/10.1038/s41467-024-47905-1

**Johnston et al. 2024** Immunological imprinting shapes the specificity of human antibody responses against SARS-CoV-2 variants. *Immunity*. https://doi.org/10.1016/j.immuni.2024.02.017

**Kandinov et al. 2025** An mRNA-based seasonal influenza vaccine in adults: Results of two phase 3 randomized clinical trials and correlate of protection analysis of hemagglutination inhibition titers. *Human Vaccines & Immunotherapeutics*. https://doi.org/10.1080/21645515.2025.2484088

**Karikó et al. 2005** Suppression of RNA Recognition by Toll-like Receptors: The Impact of Nucleoside Modification and the Evolutionary Origin of RNA. *Immunity*. https://doi.org/10.1016/j.immuni.2005.06.008

**Karikó et al. 2011** Generating the optimal mRNA for therapy: HPLC purification eliminates immune activation and improves translation of nucleoside-modified, protein-encoding mRNA. *Nucleic Acids Research*. https://doi.org/10.1093/nar/gkr695

**Karlstad et al. 2022** SARS-CoV-2 Vaccination and Myocarditis in a Nordic Cohort Study of 23 Million Residents. *JAMA Cardiology*. https://doi.org/10.1001/jamacardio.2022.0583

**Kim et al. 2022** Germinal centre-driven maturation of B cell response to mRNA vaccination. *Nature*. https://doi.org/10.1038/s41586-022-04527-1

**Klein et al. 2021** Surveillance for Adverse Events After COVID-19 mRNA Vaccination. *JAMA*. https://doi.org/10.1001/jama.2021.15072

**Kurhade et al. 2023** Low neutralization of SARS-CoV-2 Omicron BA.2.75.2, BQ.1.1 and XBB.1 by parental mRNA vaccine or a BA.5 bivalent booster. *Nature Medicine*. https://doi.org/10.1038/s41591-022-02162-x

**Lamoot et al. 2023** Successful batch and continuous lyophilization of mRNA LNP formulations depend on cryoprotectants and ionizable lipids. *Biomaterials Science*. https://doi.org/10.1039/d2bm02031a

**Li et al. 2022** Mechanisms of innate and adaptive immunity to the Pfizer-BioNTech BNT162b2 vaccine. *Nature Immunology*. https://doi.org/10.1038/s41590-022-01163-9

**Ma et al. 2025** Immune correlates analysis of mRNA-1345 RSV vaccine efficacy clinical trial. *Nature Communications*. https://doi.org/10.1038/s41467-025-61153-x

**Ma et al. 2026** Effectiveness of the monovalent XBB.1.5 COVID-19 vaccines: A systematic review and meta-analysis. *Journal of Microbiology, Immunology and Infection*. https://doi.org/10.1016/j.jmii.2025.07.002

**Mudd et al. 2022** SARS-CoV-2 mRNA vaccination elicits a robust and persistent T follicular helper cell response in humans. *Cell*. https://doi.org/10.1016/j.cell.2021.12.026

**Mulroney et al. 2024** N1-methylpseudouridylation of mRNA causes +1 ribosomal frameshifting. *Nature*. https://doi.org/10.1038/s41586-023-06800-3

**Muramatsu et al. 2022** Lyophilization provides long-term stability for a lipid nanoparticle-formulated, nucleoside-modified mRNA vaccine. *Molecular Therapy*. https://doi.org/10.1016/j.ymthe.2022.02.001

**Oberhardt et al. 2021** Rapid and stable mobilization of CD8+ T cells by SARS-CoV-2 mRNA vaccine. *Nature*. https://doi.org/10.1038/s41586-021-03841-4

**Oda et al. 2024** Immunogenicity and safety of a booster dose of a self-amplifying RNA COVID-19 vaccine (ARCT-154) versus BNT162b2 mRNA COVID-19 vaccine: a double-blind, multicentre, randomised, controlled, phase 3, non-inferiority trial. *The Lancet Infectious Diseases*. https://doi.org/10.1016/s1473-3099(23)00650-3

**Pardi & Krammer 2024** mRNA vaccines for infectious diseases — advances, challenges and opportunities. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-024-01042-y

**Patone et al. 2022** Risk of Myocarditis After Sequential Doses of COVID-19 Vaccine and SARS-CoV-2 Infection by Age and Sex. *Circulation*. https://doi.org/10.1161/circulationaha.122.059970

**Polack et al. 2020** Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2034577

**Rosa et al. 2021** mRNA vaccines manufacturing: Challenges and bottlenecks. *Vaccine*. https://doi.org/10.1016/j.vaccine.2021.03.038

**Sahin et al. 2020** COVID-19 vaccine BNT162b1 elicits human antibody and TH1 T cell responses. *Nature*. https://doi.org/10.1038/s41586-020-2814-7

**Song et al. 2024** A systematic review and meta-analysis on the effectiveness of bivalent mRNA booster vaccines against Omicron variants. *Vaccine*. https://doi.org/10.1016/j.vaccine.2024.04.049

**Stowe et al. 2023** Risk of myocarditis and pericarditis after a COVID-19 mRNA vaccine booster and after COVID-19 in those with and without prior SARS-CoV-2 infection: A self-controlled case series analysis in England. *PLOS Medicine*. https://doi.org/10.1371/journal.pmed.1004245

**Tang et al. 2022** Respiratory mucosal immunity against SARS-CoV-2 after mRNA vaccination. *Science Immunology*. https://doi.org/10.1126/sciimmunol.add4853

**Thomas et al. 2021** Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine through 6 Months. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2110345

**Turner et al. 2021** SARS-CoV-2 mRNA vaccines induce persistent human germinal centre responses. *Nature*. https://doi.org/10.1038/s41586-021-03738-2

**Verbeke et al. 2022** Innate immune mechanisms of mRNA vaccines. *Immunity*. https://doi.org/10.1016/j.immuni.2022.10.014

**Whitaker et al. 2023** mRNA vaccines against respiratory viruses. *Current Opinion in Infectious Diseases*. https://doi.org/10.1097/qco.0000000000000948

**Wilson et al. 2023** Efficacy and Safety of an mRNA-Based RSV PreF Vaccine in Older Adults. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2307079
