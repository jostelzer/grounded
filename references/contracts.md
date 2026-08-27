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
   `requirements-pdf.txt` runtime, in ChatGPT, Claude Code, and any other
   shell host; the claude.ai no-network path is preserved by
   `references/no-script-fallback.md`, which must be updated in the same
   change as any behavior it mirrors.
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
  (additive only), atomic write behavior.
- `qa_review_pdf.py` / `qa_deck_pdf.py` / `qa_figure.py`: fail-closed
  behavior, report shapes (additive only).

## Fixtures

`tests/fixtures/colic/` is the recorded golden run (small popsci journal PDF,
20 verified sources, one deterministic figure). It exists so that "without
destroying what works" is checkable: the golden pipeline test must stay green
through every phase of hardening work.
