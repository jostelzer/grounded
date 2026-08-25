> Unedited example output. Mode: image (experimental). Prompt: *"Use the scientific-review skill in image mode: how do mRNA vaccines work?"*

## How do mRNA vaccines work?

**TL;DR** — The shot delivers a fatty droplet carrying genetic instructions. Your own cells read them, build one harmless viral protein, and the immune system learns to attack it. Two chemical tricks made this practical: modified letters that stop the body destroying the message, and the droplet, which both smuggles it into cells and acts as a built-in immune stimulant.

### The vaccine carries a message, not a pathogen

- It is a [lipid nanoparticle](https://en.wikipedia.org/wiki/Lipid_nanoparticle) (LNP) wrapping [messenger RNA](https://en.wikipedia.org/wiki/Messenger_RNA) (mRNA); after injection the particle enters cells, releases its cargo from the [endosome](https://en.wikipedia.org/wiki/Endosome), and the cell's own ribosomes translate it into protein [Chaudhary et al. 2021](https://doi.org/10.1038/s41573-021-00283-5), [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y).
- Both licensed COVID-19 vaccines encode the same [antigen](https://en.wikipedia.org/wiki/Antigen) — a prefusion-stabilised SARS-CoV-2 [spike protein](https://en.wikipedia.org/wiki/Coronavirus_spike_protein) — at 30 µg (BNT162b2) or 100 µg (mRNA-1273) [Polack et al. 2020](https://doi.org/10.1056/nejmoa2034577), [Baden et al. 2021](https://doi.org/10.1056/nejmoa2035389).
- The mRNA is transient and non-integrating, so a new vaccine means a new sequence rather than a new manufacturing process [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y).

### Chemically modified RNA letters were the unlock

- Modified nucleosides such as [pseudouridine](https://en.wikipedia.org/wiki/Pseudouridine) abolish RNA's ability to trigger [Toll-like receptors](https://en.wikipedia.org/wiki/Toll-like_receptor) 3, 7 and 8, so exposed [dendritic cells](https://en.wikipedia.org/wiki/Dendritic_cell) make far less cytokine [Karikó et al. 2005](https://doi.org/10.1016/j.immuni.2005.06.008).
- Stripping double-stranded RNA contaminants by chromatography raised translation a further **10- to 1,000-fold** in primary cells and removed residual interferon induction [Karikó et al. 2011](https://doi.org/10.1093/nar/gkr695).
- [N1-methylpseudouridine](https://en.wikipedia.org/wiki/N1-Methylpseudouridine) (m1Ψ), used in both licensed vaccines, beat pseudouridine by up to ~13-fold in mice [Andries et al. 2015](https://doi.org/10.1016/j.jconrel.2015.08.051); ribosome profiling shows it raises output by altering translation dynamics, not only by damping innate sensing [Rozman et al. 2026](https://doi.org/10.1038/s41586-025-09945-5).

### The lipid nanoparticle is a delivery vehicle *and* an adjuvant

- LNPs are ionizable-lipid carriers: positively charged at low pH to load RNA, near-neutral in blood, which limits toxicity [Cullis & Felgner 2024](https://doi.org/10.1038/s41573-024-00977-6), [Hou et al. 2021](https://doi.org/10.1038/s41578-021-00358-0).
- In mice the formulation is itself an [adjuvant](https://en.wikipedia.org/wiki/Immunologic_adjuvant), outperforming an MF59-like comparator and driving [T follicular helper](https://en.wikipedia.org/wiki/T_follicular_helper_cell) (Tfh) and antibody responses through the ionizable lipid and [interleukin-6](https://en.wikipedia.org/wiki/Interleukin_6) [Alameh et al. 2021](https://doi.org/10.1016/j.immuni.2021.11.001).
- The parts divide the labour: the mRNA drives [type I interferon](https://en.wikipedia.org/wiki/Interferon_type_I) that matures dendritic cells, while the LNP shapes where those cells sit in the draining lymph node [Castaño et al. 2025](https://doi.org/10.1016/j.cell.2025.11.023).

### Durable protection comes from a long germinal-centre reaction

- In mice, mRNA vaccination — unlike an adjuvanted protein vaccine — generated [germinal centre](https://en.wikipedia.org/wiki/Germinal_center) B and Tfh cells, and germinal-centre size tracked [neutralising antibody](https://en.wikipedia.org/wiki/Neutralizing_antibody) levels [Lederer et al. 2020](https://doi.org/10.1016/j.immuni.2020.11.009).
- Lymph-node sampling in vaccinated people (n=14) found spike-binding germinal-centre B cells for at least **12 weeks** after the second dose, long after plasmablasts had vanished [Turner et al. 2021](https://doi.org/10.1038/s41586-021-03738-2).
- Across 1,540 clones, [somatic hypermutation](https://en.wikipedia.org/wiki/Somatic_hypermutation) rose **3.5-fold over six months**, yielding higher-affinity [memory B cells](https://en.wikipedia.org/wiki/Memory_B_cell) and bone-marrow [plasma cells](https://en.wikipedia.org/wiki/Plasma_cell) [Kim et al. 2022](https://doi.org/10.1038/s41586-022-04527-1); spike-specific Tfh cells persisted about six months [Mudd et al. 2022](https://doi.org/10.1016/j.cell.2021.12.026).

### It works well, wanes against infection, and has real limits

| Trial | Design | n | Efficacy against symptomatic COVID-19 | Ref |
|---|---|---|---|---|
| BNT162b2 | RCT, 2 doses 21 days apart | 43,448 | **95%** (95% CrI 90.3–97.6) | [Polack et al. 2020](https://doi.org/10.1056/nejmoa2034577) |
| mRNA-1273 | RCT, 2 doses 28 days apart | 30,420 | **94.1%** (95% CI 89.3–96.8) | [Baden et al. 2021](https://doi.org/10.1056/nejmoa2035389) |

- Protection is not static: across 78 estimates, effectiveness fell **21.0 percentage points** (95% CI 13.9–29.8) against infection between 1 and 6 months, but only **10.0** (6.1–15.4) against severe disease [Feikin et al. 2022](https://doi.org/10.1016/s0140-6736(22)00152-0).
- [Myocarditis](https://en.wikipedia.org/wiki/Myocarditis) is rare but real: among ~18 million vaccinated people in England, an extra 10 cases per million followed a second mRNA-1273 dose, against 40 per million after a positive SARS-CoV-2 test; risk concentrated under 40 ([rate ratio](https://en.wikipedia.org/wiki/Rate_ratio) 3.40, 95% CI 1.91–6.04 after a second BNT162b2 dose) [Patone et al. 2022](https://doi.org/10.1038/s41591-021-01630-0).
- The chemistry has a cost: m1Ψ causes +1 [ribosomal frameshifting](https://en.wikipedia.org/wiki/Ribosomal_frameshift), and immunity to off-target frameshifted products was detected in mice and humans — no adverse outcomes reported, and fixable by synonymous recoding [Mulroney et al. 2024](https://doi.org/10.1038/s41586-023-06800-3).
- Manufacturing and cold chain, not immunology, are the practical constraint on wider use [Rosa et al. 2021](https://doi.org/10.1016/j.vaccine.2021.03.038), [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y).

### Scientific illustration

![Four-step figure: an injected lipid nanoparticle carrying mRNA; a muscle cell translating that mRNA into spike protein on its surface; the droplet and mRNA acting as an immune alarm that sends a dendritic cell to a lymph node; and a germinal centre refining antibodies over months. A results strip gives trial efficacy and waning, and a glossary band defines every term used.](image-mrna-vaccines.svg)

*Caption: the route from injection to durable antibody — droplet uptake, translation of modified-nucleoside mRNA into spike protein, and a germinal-centre reaction that keeps improving antibodies for months [Pardi & Krammer 2024](https://doi.org/10.1038/s41573-024-01042-y), [Turner et al. 2021](https://doi.org/10.1038/s41586-021-03738-2), [Kim et al. 2022](https://doi.org/10.1038/s41586-022-04527-1). The dashed amber panel marks the step resting mainly on mouse experiments [Alameh et al. 2021](https://doi.org/10.1016/j.immuni.2021.11.001), [Castaño et al. 2025](https://doi.org/10.1016/j.cell.2025.11.023); the others are observed in vaccinated people, in whom protection wanes faster against infection than against severe disease [Feikin et al. 2022](https://doi.org/10.1016/s0140-6736(22)00152-0). Schematic, not to scale.*

**Sources**

**Alameh et al. 2021** Lipid nanoparticles enhance the efficacy of mRNA and protein subunit vaccines by inducing robust T follicular helper cell and humoral responses. *Immunity*. https://doi.org/10.1016/j.immuni.2021.11.001

**Andries et al. 2015** N1-methylpseudouridine-incorporated mRNA outperforms pseudouridine-incorporated mRNA by providing enhanced protein expression and reduced immunogenicity in mammalian cell lines and mice. *Journal of Controlled Release*. https://doi.org/10.1016/j.jconrel.2015.08.051

**Baden et al. 2021** Efficacy and Safety of the mRNA-1273 SARS-CoV-2 Vaccine. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2035389

**Castaño et al. 2025** Distinct components of mRNA vaccines cooperate to instruct efficient germinal center responses. *Cell*. https://doi.org/10.1016/j.cell.2025.11.023

**Chaudhary et al. 2021** mRNA vaccines for infectious diseases: principles, delivery and clinical translation. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-021-00283-5

**Cullis & Felgner 2024** The 60-year evolution of lipid nanoparticles for nucleic acid delivery. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-024-00977-6

**Feikin et al. 2022** Duration of effectiveness of vaccines against SARS-CoV-2 infection and COVID-19 disease: results of a systematic review and meta-regression. *The Lancet*. https://doi.org/10.1016/s0140-6736(22)00152-0

**Hou et al. 2021** Lipid nanoparticles for mRNA delivery. *Nature Reviews Materials*. https://doi.org/10.1038/s41578-021-00358-0

**Karikó et al. 2005** Suppression of RNA Recognition by Toll-like Receptors: The Impact of Nucleoside Modification and the Evolutionary Origin of RNA. *Immunity*. https://doi.org/10.1016/j.immuni.2005.06.008

**Karikó et al. 2011** Generating the optimal mRNA for therapy: HPLC purification eliminates immune activation and improves translation of nucleoside-modified, protein-encoding mRNA. *Nucleic Acids Research*. https://doi.org/10.1093/nar/gkr695

**Kim et al. 2022** Germinal centre-driven maturation of B cell response to mRNA vaccination. *Nature*. https://doi.org/10.1038/s41586-022-04527-1

**Lederer et al. 2020** SARS-CoV-2 mRNA Vaccines Foster Potent Antigen-Specific Germinal Center Responses Associated with Neutralizing Antibody Generation. *Immunity*. https://doi.org/10.1016/j.immuni.2020.11.009

**Mudd et al. 2022** SARS-CoV-2 mRNA vaccination elicits a robust and persistent T follicular helper cell response in humans. *Cell*. https://doi.org/10.1016/j.cell.2021.12.026

**Mulroney et al. 2024** N1-methylpseudouridylation of mRNA causes +1 ribosomal frameshifting. *Nature*. https://doi.org/10.1038/s41586-023-06800-3

**Pardi & Krammer 2024** mRNA vaccines for infectious diseases — advances, challenges and opportunities. *Nature Reviews Drug Discovery*. https://doi.org/10.1038/s41573-024-01042-y

**Patone et al. 2022** Risks of myocarditis, pericarditis, and cardiac arrhythmias associated with COVID-19 vaccination or SARS-CoV-2 infection. *Nature Medicine*. https://doi.org/10.1038/s41591-021-01630-0

**Polack et al. 2020** Safety and Efficacy of the BNT162b2 mRNA Covid-19 Vaccine. *New England Journal of Medicine*. https://doi.org/10.1056/nejmoa2034577

**Rosa et al. 2021** mRNA vaccines manufacturing: Challenges and bottlenecks. *Vaccine*. https://doi.org/10.1016/j.vaccine.2021.03.038

**Rozman et al. 2026** N1-Methylpseudouridine directly modulates translation dynamics. *Nature*. https://doi.org/10.1038/s41586-025-09945-5

**Turner et al. 2021** SARS-CoV-2 mRNA vaccines induce persistent human germinal centre responses. *Nature*. https://doi.org/10.1038/s41586-021-03738-2

