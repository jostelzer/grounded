# Output production

Read only for the selected output format. Core verification requirements remain in SKILL.md and claim-verification.md.

## Output formats

### Inline chat

**Write the finished review directly in your reply.** Do not create `review.md`, attach a file, or put the review in an artifact or canvas: chat clients cannot preview a markdown file, and on the user's machine it opens in a code editor with the formatting stripped. The review is meant to be read in the conversation, where headings, tables, and bold render.

The chat review ends with its **Sources** — each entry stamped with the claims it supports and their evidence tier — and a two-line **Receipts** block carrying the audit tally and the name of the receipts file (`<review>-receipts.md`, written by the assertion audit). That receipts file is the one file an inline-chat review always produces: attach it or name its path, never paste it into the chat.

Working files (`sources.json`, `search_log.md`, `search-manifest.json`, `notes.md`, `synthesis.md`, `claims_audit.json`, the draft) are audit inputs: keep them if you have a filesystem, never present them as the output, and mention them only if the user wants to audit. If the host cannot retain the required audit artifacts, report that verified delivery is blocked. Produce other files only when asked ("save it", "give me a .md"), and then still put the review in the chat.

### Journal PDF (default)

Used when the user picks it in the format question or asks for a PDF, a printable or shareable version, or "a journal article". The journal PDF always includes generated figures: choosing the format is what triggers figure creation (step 7). `scripts/export_review.py` renders the single canonical GROUNDED design with pinned WeasyPrint — masthead with the packaged logo, linked "Agentically generated scientific review" descriptor and version on every page; metadata grid with the writing style; numbered sections; two-column Charter body with Helvetica Neue furniture; full-width tables and figures with cited captions; DOI-linked superscript citations and references in first-citation order; clickable figure references; a book-style colophon closing the document with the source count, the DOI-resolution and dated integrity-screening statement, and the claim-audit tally. The per-pair receipts never enter the PDF; they travel beside it as `<review>-receipts.md`, hashed into the release manifest. A citation that grammatically opens a sentence is a hard export error. Never substitute a browser, ReportLab, or an ad-hoc template.

```bash
python3 scripts/export_review.py --check-pdf-runtime
python3 scripts/export_review.py --in review.md --out review.pdf --pdf --style <scientific|popsci|bullets|eli5> --ledger sources.json --claims-audit claims_audit.json --claim-receipts review-receipts.md --release-manifest release-manifest.json --figure-spec figure.json --figure-prompt figure.prompt.txt --figure-inspection figure.inspection.json --figure-provenance figure.provenance.json
python3 scripts/qa_review_pdf.py review.pdf --manifest release-manifest.json --render-dir review-pdf-qa --report pdf-qa.json
```

The runtime check is a hard gate: if it fails, install the exact packages in `requirements-pdf.txt` and the native Pango runtime (on macOS, the Homebrew WeasyPrint executable), then rerun; never switch renderers. Repeat the four `--figure-*` arguments once per figure. `--claims-audit` is the checked schema-v2 assertion audit and `--claim-receipts` the receipts file it produced; the exporter refuses stale audits, changed evidence, unclassified text, and uncovered assertion elements, a review whose Receipts stamp has no matching audit, and any remote, missing, or escaping asset, writes atomically so a failed build cannot replace a good PDF, and refuses a render that is not pinned WeasyPrint with Charter and Helvetica Neue embedded. The QA command is mandatory before delivery: it rehashes every input, rebuilds the HTML, proves figure aspect ratios were preserved, rasterizes every page through Poppler, and records one authoritative render set in the manifest — use a new, case-local `--render-dir` and look at every page and contact sheet yourself. A stranded heading, an avoidably sparse spill page, a stretched figure or font, or a large preventable blank region is release-blocking; rebalance and rebuild without dropping evidence or shrinking type. Editions (the paper identity each style renders in), the pull-quote device, the exporter's automatic spill rebalance, and the layout levers (`--ref-leading`, `--figure-max-height`, `--columns 1`) are specified in `references/quality-gates.md`; QA failure messages name the lever that closes each gap. The review still goes in the chat as well.

### Slides (experimental)

The slides format runs only when the user asks for a **deck**, **slides**, a **presentation**, or a **journal club deck**; it is not offered in the format question, because the deck replaces the written review and a reader who did not ask for that should not get it. Run the complete evidence pipeline through `synthesis.md`, storyboard from those claims per `references/deck-guide.md`, and deliver in chat the sharpened question, a one-to-three-sentence plain answer, and the deck PDF — a full styled review only if the user asks for both. Every content-slide title is a full-sentence cited claim; artwork is created with `render_context: slide` and carries the evidence itself; every slide passes the guide's standalone test (claim, evidence, and firmness readable from that slide alone). Version 1 is 16:9 PDF only, and decks do not yet carry claim receipts — say so in one sentence when delivering one.

```bash
python3 scripts/export_deck.py --check-pdf-runtime
python3 scripts/export_deck.py --storyboard storyboard.json --ledger sources.json --out review-deck.pdf
python3 scripts/qa_deck_pdf.py review-deck.pdf --storyboard storyboard.json --ledger sources.json --render-dir review-deck-qa
```

The exporter enforces the style arc, slide-count limits, verified DOI coverage, 16:9 geometry, data-URI-only assets, atomic writes, canonical fonts, and pinned WeasyPrint; deck QA is mandatory, and you apply the standalone test to every rendered slide. Without a capable image-generation model the deck cannot exist: deliver the synthesis as a normal review and say in one sentence that the deck could not be generated — never fake it with text slides, SVG, or placeholders.

The evidence pipeline, verification, and citation standard are identical in every format.


### 7. Create the figures or slides

Skip for inline chat. Journal PDFs require distinct, synthesis-grounded figures: use the generated target and cap for the selected size in `budgets.md` — one whole-answer synthesis visual plus whatever mechanism, study-design, quantitative, comparison, or uncertainty views the verified synthesis genuinely earns; fewer is valid only when it holds fewer visual stories, never because producing them is inconvenient. A popsci or ELI5 review may add a sectional cutaway plate under the ceiling when it removes a genuine imagination step, shows hidden structure faithfully, adds distinct information, and stays clear at 390 px (the `cutaway` archetype and its callout contract apply).

Read `references/media-modes.md` for format coverage and embedding, then `references/figure-generation-contract.md` for the communication-first v3 workflow, which owns concept selection, evidence routing, semantic planning, annotations, non-distortion, generation, inspection, and release decisions. Build only from claims and patterns already in `synthesis.md`. Route-specific references: deterministic or composite plots — `references/quantitative-figure-guide.md` (the complete spec shape, the renderer's grammar, and the scaffold → lint → preview tools); generated or composite art — `references/image-prompt-guide.md`, `references/figure-style-system.md`; inspection and provenance records — `references/figure-inspection-contract.md`; captions and panel cross-references — `references/figure-captions.md`; feedback meant to improve unseen figures — `references/figure-feedback-generalization.md`; slides — `references/deck-guide.md`.

Every new figure uses `quality_contract_version: 3`. Non-quantitative explanations use a capable built-in image generator; verified numbers that carry the message use deterministic plotting, optionally composited with generated text-free anchors. Start every spec with `scripts/figure_spec_tools.py scaffold` and repair it with `lint`, which reports every failure at once; for a plot, `preview` writes the 390 px view and measures the primary labels before any inspection is written. Build prompts with `scripts/build_figure_prompt.py`, inspect the pixels at native and final size, and run:

```bash
python3 scripts/qa_figure.py --spec figure.json --image figure.png --inspection figure.inspection.json --provenance figure.provenance.json --geometry figure.geometry.json
```

`--geometry` (or a `geometry` path in the provenance render attempt) makes the phone gate a measurement for plots; an attested label height the raster does not contain fails.

A failed meaning, information-flow, anatomy, typography, salience, connector, quantitative, or non-distortion gate means revision and another inspection. Phone QA applies to one to three primary wayfinding labels; keep supporting labels at publication scale and simplify or split a figure rather than enlarging its whole type system. Reject a candidate whose text is poster-like or whose explanation disappears when its labels are mentally hidden. Give each passing figure a stable ID, introduce it before the artwork, refer to its A–D panels in the prose, and end its style-matched caption with verified citations. If capable image generation is unavailable or the visual gates cannot pass, deliver the verified synthesis as a normal review; record how the absence was determined in the provenance `generator_detection`, and say in one sentence when delivering that the figures are plots because no image generator was exposed.
