# Grounded behavioral contracts

This file freezes the invariants and public interfaces that hardening work must
not change. Every change that touches an item here must say so explicitly in
its changelog entry. Additions are fine; silent weakening or removal is not.

## Invariants (never weakened)

1. **No citation from memory.** Every cited source is discovered by a real
   index search and verified through Crossref before it may be cited.
2. **Fail-closed gates.** A failed gate never silently passes. New leniency is
   only ever *maxima → warning*; *minima* and correctness checks stay hard
   errors.
3. **Atomic artifacts.** A failed build can never overwrite an existing good
   PDF, deck, or manifest.
4. **Canonical renderer.** PDF export is pinned WeasyPrint with the Charter /
   Helvetica Neue identity and data-URI-only assets; no browser, no network at
   render time. Text size is never reduced to fix layout.
5. **Append-only records.** The ledger, search manifest, full-text manifest,
   and release manifest record what actually happened. New states (for
   example `superseded`) are additions with reasons, never rewrites of
   history.
6. **Host portability.** Every script runs on plain `python3` plus the pinned
   `requirements-pdf.txt` runtime, in Claude Code, Codex CLI, and any other
   shell host with outbound access to the literature APIs. Hosts without that
   access are unsupported: the skill stops at the Step 0 gate rather than
   degrading, so no verification-free path is maintained.
7. **CLI compatibility.** Existing flags and their defaults keep working.
   Behavior changes ship behind new flags or new output fields, never by
   repurposing existing ones.

## Public interfaces (change requires a changelog entry)

- `find_papers.py`: `--query/--openalex-query/--pubmed-query`, `--angle`,
  `--angle-id`, `--lane`, `--ledger`, `--chase*`, manifest schema version 1.
- `audit_search.py`: exit code semantics (0 pass / 1 fail), `status`,
  `errors`, `warnings`, `metrics` keys.
- `verify_citations.py`: pass criteria (DOI resolves; type acceptable; title
  and year match; no retraction signal), ledger `verification` block shape.
- `audit_fulltexts.py`: notes bullet syntax, manifest schema, `--minimum`.
- `validate_review.py`: exit codes, `status/errors/warnings/metrics` report
  shape; existing metric keys keep their meaning (new keys may be added).
- `format_references.py`: `[@key]` citation syntax, chat citation placement
  rules, Sources block shape.
- `export_review.py` / `export_deck.py`: flag set, release-manifest fields
  (additive only), atomic write behavior. Editions (`--edition`, default
  journal; popsci defaults to salon, eli5 to primer, bullets to brief) are presentation profiles only: fonts,
  furniture, and devices (drop cap, dinkus, `--pull-quote` with verbatim
  check and sentence-scoped attribution) may vary per edition; citation
  placement, reference order, and every gate may not.
- `qa_review_pdf.py` / `qa_deck_pdf.py` / `qa_figure.py`: fail-closed
  behavior, report shapes (additive only).
- `audit_production.py`: production-manifest schema 1, ordered stage names
  (`evidence`, `semantic`, `figures`, `release`), live prerequisite validation,
  exact warning acceptance, and exit-code semantics.

## Additive interface changes

- Figure quality contract v1 adds `--review-style` and `--render-route` to
  `build_figure_prompt.py`, `--provenance` to `qa_figure.py`, and repeatable
  `--figure-inspection` / `--figure-provenance` inputs to `export_review.py`.
  Existing figure specs and CLI defaults remain valid; v1 specs opt into the
  conditional-iteration, visual-quality, provenance, aspect, and PDF-matrix gates.
- Figure quality contract v2 introduced the communication-first fields. It additively
  requires a communication goal, three evaluated concepts for generated
  illustrations, a quantitative plot design for verified known numbers, an
  uppercase A–D panel/callout plan, post-generation meaning reviews, and
  explanatory-value/information-flow/intuitiveness gates, including a familiar
  starting point and caption-independent explain-back check. Contract v1 remains accepted so
  existing release manifests and fixtures stay reproducible.
- Figure quality contract v3 is the default for new figures. It adds a single
  reader-facing visual question and panel thesis; a semantic plan for specific
  entities, typed connectors, panel jobs, grouping, anatomy, salience, and
  quantitative routing; original-size anatomical-integrity checks; and hard
  gates for concept coherence, connector semantics, logical grouping,
  non-redundancy, salience, and clean typography. Contracts v1 and v2 remain
  accepted only so existing releases stay reproducible.
- Release-manifest schema 1 adds `figure_inspections` and
  `figure_provenances` lists and figure QA reports add pixel/aspect/visual-
  quality metrics. Existing fields retain their meaning.
- Journal-PDF visual planning now targets 2 figures for small reviews, 3–4 for
  medium, and 5–6 for large, with hard ceilings of 2/5/8. Falling below a
  target warns rather than failing so the policy cannot force decorative
  filler; exceeding the size ceiling remains a validation error.
- Production-manifest schema 1 additively composes the existing gates for
  multi-review journal batches. It freezes the figure height cap before pixel
  QA, binds live figure hashes and evaluated widths to release records, and
  requires diagnosed exceptions only after normal local/full-document budgets
  are exceeded. An exception records extra work and never waives a failed gate.

- Quotes before prose (v0.4.2): `synthesis.md` carries a `- quote: [@key] "…"`
  line for every key a claim cites; `verify_claims.py seed` and
  `synthesis-check` (module `synthesis_quotes.py`) gate drafting;
  `extract --synthesis` refuses a cited source the synthesis never quoted and
  carries synthesis quotes into packets; `packets --blind` and
  `adjudicate --packet` support an independent judge; `validate_review.py`
  warns at three citations on one sentence. All additive: an un-quoted
  synthesis still parses for every earlier gate.
- Claim receipts (v0.4.2) make the claim audit part of every delivered review.
  `verify_claims.py check --summary` and the `receipts` subcommand are
  additive; `claim_receipts.py` is the shared renderer. `receipts` writes
  `<review>-receipts.md` (never PDF pages) and stamps the review: Sources
  annotations plus a two-line `**Receipts**` block with the tally.
  `validate_review.py` ignores that stamp as prose, checks it carries a clean
  tally and no per-pair lines, and adds `metrics.claim_receipts`.
  `export_review.py --claims-audit` adds `inputs.claims_audit`,
  `expected.claim_pairs`, and `expected.claim_summary` (and
  `--claim-receipts` adds `inputs.claim_receipts`) to release-manifest
  schema 1, prints the colophon audit line, and refuses a Receipts stamp
  without its audit or an audit with any pair that is not `supported` or
  `partial`. `check` additionally fails templated notes (one note on three or
  more pairs), note-less `partial` verdicts, and downgrades quotes that share
  no content word or number with their claim unless a pair-specific `bridge`
  connects them; `adjudicate` records one pair at a time;
  `fetch --ledger/--fulltext-dir/--fulltext-manifest/--offline` seeds the
  store from the review's own reading. `qa_review_pdf.py` requires the
  visible colophon audit line and verifies the receipts-file hash when the
  manifest records them.
  `audit_production.py` accepts an optional `release.claims_audit` and checks
  it against the release manifest; its synthesis audit also fails a hollow
  ledger (no contrary evidence on any of eight or more claims, or boundary/
  numbers/evidence lines repeated across three or more claims). `packets`
  shows the opening of the stored text when no passage anchors on the
  sentence, so a judge can abstain honestly instead of blindly.
  `evals/claim-benchmark-creatine.json` is v2: re-adjudicated under this
  rubric (10 multi-element pairs moved to partial). Reviews without an audit still export and
  pass QA unchanged, so existing fixtures and manifests stay reproducible.

- Draft check (v0.4.3): `check_draft.py ingest|report` is a new, additive
  entry point. It reuses the verifier and the claim audit unchanged; the only
  new artifacts are `resolution.json`, `draft-normalized.md`, and
  `draft-check.md`.

- `scripts/compose_hybrid_figure.py` is kept only so quality-contract-v1
  releases stay reproducible; v3 figures never use it.

- Plot upgrade (v0.4.5): the deterministic renderer gains a primary tier —
  strings named in `layout_plan.mobile_preview.primary_labels` are drawn at the
  smallest size that clears the 390 px floor (never tick labels, never the rest
  of the type system) and recorded in the geometry manifest as
  `primary_labels_resolved`. `qa_figure.py --geometry` (or a `geometry` path in
  the provenance render attempt) measures the phone gate from those records and
  fails an attestation the raster does not contain; without a manifest the
  attested value still applies and a warning names the gap. With a manifest,
  the machine p90 label height behind the typography-dominance cap excludes
  OCR words inside rotated `y_axis_label` boxes and inside resolved primary
  labels, so the cap measures the supporting type system it was written for. Geometry QA checks
  the resolved records and the gate. Renderer sugar (`x_axis.categories` /
  `y_axis.categories`, `rows`, `annotations`) expands inside normalization and
  is mirrored in geometry QA; the manifest shape for existing constructs is
  unchanged. Opt-in `plot_design.render.auto_layout` (or `--auto-layout`)
  searches label sides and canvas widths and records `resolved_layout`; geometry
  QA honours the width only when the spec opted in. `figure_provenance.py`
  adds non-blocking `provenance_warnings` (a `generator_detection` record is
  expected when `generator_available` is false). New script
  `figure_spec_tools.py` (`scaffold`, `lint`, `preview`) wraps the unchanged
  validators. Placeholders (`<<FILL …>>`) are rejected by lint, the renderer,
  and figure QA. All additive: existing specs, manifests, and fixtures pass
  unchanged.

- Production-manifest schema 1 accepts an optional `usage` object per stage
  (`model`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`);
  `audit_production.py` reports it under `metrics.usage` with totals and
  `recorded: false` when absent. Shape errors fail; absence never does.

## Fixtures

`tests/fixtures/colic/` is the recorded golden run (small popsci journal PDF,
20 verified sources, one deterministic figure). It exists so that "without
destroying what works" is checkable: the golden pipeline test must stay green
through every phase of hardening work.

## Assertion audit v2 and evidence assessment

- Inventory headings, uncited paragraphs and summaries, captions, alt text, and table rows. Independent classification is required for uncited items; empirical claims cannot escape by losing a citation.
- Source verdicts name fully covered elements. Their union must cover the complete assertion. Partial support alone is not a release pass.
- Bind the exact assertion inventory and evidence metadata/text to a checked audit. Receipts, export and PDF QA reject stale assertions, changed judgments, missing evidence, and legacy audits. The PDF delivery CLI requires ledger, audit, and receipts even without a release manifest.
- The judge qualification benchmark is synthetic and spans five fields and all five verdicts. Gold answers are separated from judge inputs. Qualification requires complete coverage, zero false acceptance, and the configured agreement threshold; scoring verifies quoted passages and records hashes and confusion counts.
- Assess outcome certainty across five domains, and track study families and overlapping reviews separately from quotation support and text access. Synthesis and production evidence gates require the assessment.
- Completed contrary/null searches are required, disagreement is not. Source ranges are advisory. Budgets are generated from review_config.py into references/budgets.md and evaluation metadata.
- Compact scope/methods disclosures replace the prohibition on methods notes. Context/defaults resolve missing presentation choices without an automatic ask-back.
- PDF rebalancing retains the assertion tally when moving the colophon into the References heading. Raster and text QA remain mandatory.

These checks establish consistency and coverage of recorded judgments, not independent scientific truth. Offline rendering fixtures are explicitly synthetic; historical example reviews are not retroactively certified under v2.
