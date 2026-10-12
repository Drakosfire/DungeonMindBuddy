# RAKE — append source support without losing existing citations

Status: ACTIVE, PRIME authorization 2026-10-12. One capability in Buddy:
append bounded, literal source evidence to a corrected recap candidate while
preserving all existing valid citations and inherited PC reference proofs.

Re-anchor remote main, active PRs and leases. Last Buddy main is
6dd0bda0dc10e65808ad536425ee3a6595d45703 with Core d8798a5d. Private motivating
proof: /tmp/session28-three-item-preparation/reviewed-diff-and-boundary-result.json.
Do not change the meanings or replay identities of old correction versions.

Exact write set:

- apps/live_control_server/models/extract_promote.py
- apps/live_control_server/services/recap_semantic_candidate_correction.py
- apps/live_control_server/routes/extract_promote.py
- tests/test_recap_semantic_candidate_correction.py
- tests/integration/test_recap_evidence_append.py
- Docs/Plans/HANDOFF-RAKE-recap-evidence-append.md

Use one versioned correction request/result following the current contracts,
with at most two append entries targeting declared node/edge IDs. Bind parent
run revision/candidate digest and source/span-index digests. Resolve literal
quotes against the frozen source span and derive locator/evidence identity on
the server. The client cannot supply replacement evidence authority. Existing
evidence entries remain byte-identical and ordered; reject duplicate appends,
unknown targets, invalid source quotes and stale preconditions atomically.

Reuse the existing immutable held-child and idempotency implementation.
Preserve all unaffected candidate fields, original parent, corrected PC
corpus_refs and inherited proofs. A correction is not semantic acceptance,
admission, publication or resolution of identity holds. No new database schema,
graph writer, provider call, runtime action, UI or semantic adjudication.

Proof at the owning boundary: actual correction service and existing route
accept append; durable child/fresh-service read preserves old citations and PC
proof; stale source/parent, forged quote, duplicate and unknown target reject
without a child; exact retry returns one identical child. Use synthetic tests
and a separately named disposable APP database. No retained writes.

Implement through cumulative diff inspection, commit/push/PR for PRIME review.
Rebrief before another path/contract/capability. Session28 actual held-child
application remains a separate exact-packet review after this implementation.


## Implementation anchor and topology

- Base: Buddy remote main `6dd0bda0dc10e65808ad536425ee3a6595d45703`;
  installed Core `d8798a5d5d6b46efa3e485e5b493a8fc3d4a94f7`.
- Isolated branch: `codex/rake-recap-evidence-append`, checkout
  `/tmp/buddy-rake-evidence-append`. Parallel independent of SERVER's procedure
  lane under PRIME's explicit collision decision; no shared runtime ownership.
- This ACTIVE handoff was dispatched from PRIME's private handoff under explicit
  authorization; its checked-in copy travels in this implementation PR.
- V10 request: at most two node/edge evidence appends and the already-established
  description replacement operation, bounded to one description. Citation-array
  preimages are SHA-pinned, append order is deterministic, and source authority
  is derived from the frozen span index. Old V1–V9 replay branches remain unchanged.
- The existing APP basis/CAS, semantic-disposition and decision-dispatch owners
  have PRIME's approved extension for this version only:
  `src/application_state/ingest/service.py`,
  `apps/live_control_server/services/recap_semantic_disposition.py`, and
  `apps/live_control_server/services/extract_promote.py`. The final lease is the
  original six paths plus these three guard paths.

The three-item Session28 application remains separately held and is not run by
this PR. Completion/review/merge facts will be recorded when known, without
pre-marking this implementation complete.


## 7. Implementation and author evidence

Status: implementation ready for PRIME exact-head review; no merge or independent
acceptance is claimed. The mutable sync set is this handoff only.

The public correction request/result and immutable manifest are V10. The internal
APP semantic basis is V11: existing basis V10 retains its V9 PC-reference meaning.
The append version participates in existing held-state, exact replay, inherited
PC proof, review projection, and decision CAS guards. No old version is redefined.

Requests contain one or two appends and optionally one preimage-pinned description
replacement. Every append binds the original ordered evidence-array digest. The
server resolves the frozen span, checks literal quote substrings and derives all
source/evidence locators. Duplicate spans/anchors, unknown targets, stale pins and
bad final operations reject before child bytes or rows are created. Ordering new
append operations canonically makes reordered exact requests one immutable child.

Author verification uses the existing Core115 Python environment against this
checkout's imports. Synthetic service/HTTP regressions include prior V1–V9 child
identities and replay. The disposable PostgreSQL test creates only a uniquely named
`dungeonbuddy_app_state_test_rake_append_*` database, upgrades to the checked-in
Alembic head (no fixed migration ID), exercises the actual correction service and
APP persistence, verifies a fresh-process child read/replay/PC proof, rejects a
forged proof at actual APP CAS, and removes only that disposable database.

```bash
PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -p no:cacheprovider tests/test_recap_semantic_candidate_correction.py
# DMB_RAKE_PG_ADMIN_DSN must be an explicitly designated disposable APP admin DSN.
PYTHONPATH="$PWD/src:$PWD" python -m pytest -q -p no:cacheprovider tests/integration/test_recap_evidence_append.py
```

Author results: 151 service/route tests and one disposable PostgreSQL test pass,
zero skips. Changed production files and the new integration test pass Ruff;
the existing service-test file has 56 lint diagnostics byte-for-byte equivalent
to main's diagnostics, with no new findings. `git diff --check` passes. Existing
Pydantic field-shadow warnings remain. No retained APP/native writes, new schema,
provider calls, corpus bytes, runtime actions or Session28 corrections occur.

The public correction route is covered with synthetic frozen source/run wiring.
The PostgreSQL proof keeps that source-path resolver seam but uses real APP source
registration, run creation/lifecycle, reads and CAS. Native PC identity is a
synthetic context: this proves inherited proof preservation, not new identity
admission or an operator semantic decision. Current publication revalidation stays
at its existing owning boundary.


## 4. Approved implementation write lease

| Path |
| --- |
| apps/live_control_server/models/extract_promote.py |
| apps/live_control_server/services/recap_semantic_candidate_correction.py |
| apps/live_control_server/routes/extract_promote.py |
| tests/test_recap_semantic_candidate_correction.py |
| tests/integration/test_recap_evidence_append.py |
| Docs/Plans/HANDOFF-RAKE-recap-evidence-append.md |
| src/application_state/ingest/service.py |
| apps/live_control_server/services/recap_semantic_disposition.py |
| apps/live_control_server/services/extract_promote.py |

## 5. Source and runtime exclusions

| Path |
| --- |
| corpus/** |
| out/** |

No private configuration, retained database, source bodies, runtime, UI or new
schema belongs in this implementation lease.

## 9. Review acceptance

- At most two literal frozen-span appends create one immutable held child.
- Parent revision/candidate/source/span pins and complete citation-array preimages
  bind every operation; duplicate, foreign, unknown, stale and forged requests
  reject before child creation.
- Existing citation entries and order, all PC references and inherited proofs,
  unaffected candidate fields, source bytes and parent remain preserved.
- Public route/service, durable APP creation/retry, fresh-process replay and APP
  CAS proof rejection have owning-boundary evidence with no skipped PG check.
- Old request, basis and immutable replay identities remain unchanged.
- Session28 application, semantic acceptance, admission and publication remain
  separate review gates after merge.


`expected_evidence_refs_sha256` hashes the complete existing array using UTF-8
JSON with sorted object keys, `ensure_ascii=False`, compact separators `,` / `:`,
and one trailing newline. Array order is preserved. This is the existing sealed
candidate canonical-byte convention; it does not use a file path or client
supplied evidence identity.
