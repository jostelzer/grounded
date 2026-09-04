# Checking a supplied draft

## Checking a draft (the second front door)

When the user hands you text they already have — an LLM answer, a manuscript section, a press release, an essay — and asks to check, verify, or audit its claims or references, skip the size/style/format question and write no review. The draft is the review; the deliverable is a chat-ready check report:

```bash
python3 scripts/check_draft.py ingest --draft draft.md --out-dir check/
python3 scripts/verify_citations.py --ledger check/sources.json
python3 scripts/verify_claims.py extract --review check/draft-normalized.md --ledger check/sources.json --audit check/claims_audit.json
python3 scripts/verify_claims.py fetch   --audit check/claims_audit.json --evidence check/evidence/ --ledger check/sources.json --fulltext-all
python3 scripts/verify_claims.py packets --audit check/claims_audit.json --evidence check/evidence/ --blind
python3 scripts/verify_claims.py adjudicate --audit check/claims_audit.json --packet C001#1 --verdict <verdict> --quote "<verbatim passage>"
python3 scripts/verify_claims.py check   --audit check/claims_audit.json --evidence check/evidence/ --summary check/claims_summary.json
python3 scripts/check_draft.py report --resolution check/resolution.json --ledger check/sources.json --audit check/claims_audit.json --title "<draft title>" --out check/draft-check.md
```

`ingest` reads citations in whatever form they arrive (DOI links, bare DOIs, numeric markers or author–year with a reference list) and resolves each reference to a DOI, searching Crossref when the draft gives none: a reference no index can find is reported as **NOT FOUND**, an in-text citation with no list entry as **UNLISTED**. Verification and the blind claim audit then follow claim-verification.md. A check hides nothing — every verdict is shown, including `not_found` and `contradicted` (`check` exits non-zero on a contradicted pair; in a check that is a finding, not a stop, and the summary is still written) — and the report ends with the citations the author must fix. Deliver the report in chat and keep `check/` as the audit folder. A draft with no citations gets that answer; never invent references for it.


The assertion inventory now includes uncited material and headings. Use the classification workflow in claim-verification.md. Report unsupported uncited assertions; never invent references to fill them. A nonzero check result is retained as a finding. Draft checks do not require a new synthesis or outcome assessment.
