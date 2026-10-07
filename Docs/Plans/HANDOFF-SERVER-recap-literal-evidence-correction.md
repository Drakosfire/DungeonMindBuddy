# SERVER: literal recap evidence correction

Status: ACTIVE. Authority: PRIME dispatch after SERVER semantic gate #973 merged at `bc0c3fe4cdf67dae12e33acfac0141a002f82a52`.

## Primary question

Can a GM correct only false anchor quotes in a frozen, exact recap candidate by creating a new reviewable child whose semantic disposition starts held?

## Lease and topology

- Base: Buddy `origin/main` at `bc0c3fe4cdf67dae12e33acfac0141a002f82a52`.
- Branch: `codex/server-recap-literal-evidence-correction`; serial, independent of open UI work.
- Write paths: this handoff; `apps/live_control_server/routes/extract_promote.py`; `apps/live_control_server/models/extract_promote.py`; `apps/live_control_server/services/exact_run_evidence_correction.py`; `tests/test_recap_literal_evidence_correction.py`. The existing worldbuilding correction test may change only for a proven regression.
- Runtime lease: disposable test roots and PostgreSQL port 54329 only. No live S27 POST, semantic decision, World write, or backend restart.

## Contract

The new route is RECAP-only and GM-gated. The existing worldbuilding route remains unchanged. The parent must be an exact REVIEWABLE recap run with a complete frozen review bundle, exact `recap_category_v1@1.0` profile, campaign/session scope, and canonical SourceArtifact/source revision/span index/candidate component pins. The request identifies the exact parent candidate SHA and quote positions. Every replacement must be a literal quote in the same frozen source paragraph; after the replacements the entire child candidate must pass typed and evidence validation. Other candidate content stays byte-equivalent at the parsed field level.

The existing immutable child creator and status transitions produce a new child. Its source and span components equal the parent's; only the candidate component changes. Its lineage records `operator_recap_literal_evidence_correction_v1`, parent run and candidate SHA, canonical corrections digest, and `{version:1,state:held,basis_sha256}` computed from the APP-STATE `RecapSemanticBasisV1` fields. Identical retries verify existing child candidate bytes, components, and lineage and return its current held/accepted/rejected decision without rewriting it; conflicting identity fails closed. The response reports run/candidate/correction digests and semantic basis/state. No automatic semantic acceptance or publication follows.

## Stop conditions and acceptance

Stop if the creator cannot preserve frozen components or source authority without an unleased migration, if profile/candidate qualification needs a new generic contract, or if a second product capability is needed. Acceptance requires tests for the HTTP GM boundary, literal correction and stale/nonliteral rejection, parent/child immutability and idempotence, held basis exactness, and no World writer. Run focused and relevant full repository gates, inspect the cumulative base-to-head diff, then push and open a draft PR for PRIME review. Do not merge.
