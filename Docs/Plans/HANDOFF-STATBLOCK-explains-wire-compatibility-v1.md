---
pr_body_template: |
  ## Handoff pointer
  - Workstream: STATBLOCK / wire-and-digest compatibility
  - Direction: STEWARD → CODE → PRIME
  - Handoff: Docs/Plans/HANDOFF-STATBLOCK-explains-wire-compatibility-v1.md
  - PR topology: independent of DEMO #785/#787; source/tests/docs only, no shared runtime
  ## Review contract
  Buddy recursively omits `None` from create requests, locally rejects every non-null `RuleElement.explains` before HTTP, preserves original journal bodies, and labels unsupported-field digests Buddy-local only.
---

# HANDOFF — STATBLOCK: reconcile explains with accepted Server contract

**Created:** 2026-09-28
**Status:** ACTIVE — bounded Buddy PR #786 repair authorized; PRIME owns review and merge
**Workstream / owner:** STATBLOCK / DungeonMindBuddy consumer integration
**Direction:** STEWARD → CODE → PRIME
**Original design base:** Buddy main `132cb80bea50ef2814074a52832ab763286a1900`
**Current PR base:** Buddy main `f7ce9b99b8e9b73129c6f474989cdb30875a31c8`
**Current code head when this amendment was authorized:** `a823b45e3eb1d9e9586b97ca0376de38af6134c0`
**Server authority:** remote Server main `a5d41b2747106e862d179d4718b45ffd73577643`, a docs-only descendant of accepted runtime `1e8a6185ed16f4cb4cd3596aec7e9e22a3f74ad1`
**Owner review:** PRIME HOLD `5345032728`; PRIME authorized this exact fifth-path handoff amendment in the same PR.
**PR topology:** source/tests/docs only, independent of DEMO #785/#787; no API, UI, database, provider, or shared runtime.
**PR authorization:** update only the existing Buddy PR #786. Keep it draft and unmerged for PRIME review. No follow-on Server PR or product rehearsal is authorized.
**Title:** `STATBLOCK: preserve explains wire and digest semantics`

## §1 Accepted contract and invariant

At the current accepted Server ref above, `RuleElement.explains` is not part of `RuleElement` or the strict `RuleElement-Input` OpenAPI schema. Nested unknown fields are rejected. Therefore:

- An omitted `explains` field is accepted and retains the historical canonical definition bytes/digest.
- Explicit `null`, `[]`, and populated `explains` are all unsupported by the accepted Server contract.

Buddy behavior in this bounded repair:

1. Recursively omit `None` from the create HTTP body, including nested `rule_elements[*].explains`.
2. Reject any non-null `RuleElement.explains`, including `[]` and populated edges, locally before HTTP with typed error code `unsupported_rule_element_explains`.
3. Do not silently discard non-null authored values. Preserve the original acceptance journal/body and its local audit identity when refusing the request.
4. Buddy may retain canonical digests for local audit of explicit empty/populated values, but those values are unsupported and their digests are Buddy-local only. They must not be described as accepted Server digests or cross-owner compatible vectors.
5. Keep unrelated Server default-empty-list canonicalization unchanged.

Cross-owner absent-field vector: for `tests/fixtures/statblocks/v1/create-request.json` with `explains` absent, accepted Server `compute_definition_digest` at `1e8a6185ed16f4cb4cd3596aec7e9e22a3f74ad1` yields `sha256:265da39c72a5275bfb81315034b972ddae4aca261a683fa9ecc70a4839e91c44`. Buddy omission and null-then-omission must match this vector. This is not a vector for explicit empty or populated `explains`.

Future Server `explains` support is **unactivated**. It requires a separately authorized Server contract change defining non-null schema, edge-reference validation, historical absent-field preservation, explicit-empty/populated canonical bytes, and shared vectors. This handoff neither implements nor authorizes that work.

## §2 Scope and concurrent lanes

- DEMO #785/#787 work is independent; do not modify its paths, dependencies, PRs, runtime, or handoffs.
- The current PR is based on Buddy main `f7ce9b99b8e9b73129c6f474989cdb30875a31c8`; the implementation head above was rebased onto it with no leased-path collisions.
- Keep any existing candidate and acceptance journal untouched. No Firestore, PostgreSQL, API, browser, provider/model, credential, or product operations are permitted.
- No Server contract, generated schema, UI, persistence, migration, deployment, roadmap, or field-policy changes are in scope.

## §3 Write lease

The code/test lease remains the original four files:

- `apps/live_control_server/integrations/dungeonmind_statblocks/client.py` — recursively omit `None`; locally reject non-null `explains` before HTTP.
- `apps/live_control_server/integrations/dungeonmind_statblocks/definition_digest.py` — preserve Buddy-local audit identity and state clearly that unsupported `explains` digests do not assert Server acceptance.
- `tests/test_dungeonmind_statblocks_client.py` — prove omitted/null serialization, zero HTTP for explicit empty/populated values, and unchanged source bodies.
- `tests/test_dungeonmind_statblocks_definition_digest.py` — prove the accepted absent-field golden vector, local-only empty/populated identity, and unchanged other Server default-list behavior.

PRIME authorized this exact fifth path in the same PR:

- `Docs/Plans/HANDOFF-STATBLOCK-explains-wire-compatibility-v1.md` — reconcile this handoff’s original conflicting wire claim with the accepted Server contract; record the bounded behavior, source refs, PRIME HOLD, and this lease amendment.

Only these five paths are leased. No extra PR is authorized. No lockfile, generated contract, DEMO path/dependency, Server repo, product state, or runtime changes.

## §4 Verification and acceptance

Run source-level/unit tests only:

```bash
python -m pytest -q \
  tests/test_dungeonmind_statblocks_client.py \
  tests/test_dungeonmind_statblocks_definition_digest.py
ruff check \
  apps/live_control_server/integrations/dungeonmind_statblocks/client.py \
  apps/live_control_server/integrations/dungeonmind_statblocks/definition_digest.py \
  tests/test_dungeonmind_statblocks_client.py \
  tests/test_dungeonmind_statblocks_definition_digest.py
git diff --check
```

Acceptance requires PRIME to confirm:

1. The Server ref/model/OpenAPI are the accepted authority for omission and strict rejection of explicit null/empty/populated values.
2. Null-then-omission matches the historical absent-field golden digest above.
3. Explicit empty and populated values fail locally with `unsupported_rule_element_explains`, make zero HTTP requests, and leave input/journal bodies unchanged.
4. Buddy-only hashes for unsupported values are labeled local audit values, not Server canonical digests.
5. Unrelated Server default-list vectors remain unchanged; cumulative PR diff contains exactly the five leased paths.
6. Focused tests and scoped Ruff pass. No database, API, provider, product, or runtime operation was used.

The code portion at head `a823b45e3eb1d9e9586b97ca0376de38af6134c0` has 65 focused tests passing and a clean `git diff --check`; PRIME is running independent Ruff verification. Do not rerun the 65 tests for this documentation-only amendment unless code changes.

After PRIME review, PRIME may merge the same PR. No merge authority is granted here. Any future Server `explains` support or product rehearsal requires a separate activation and owner authorization.

## §5 Stop conditions

Stop and return to PRIME for any non-null `explains` transport enablement, Server schema/contract change, generated-contract change, reference-policy expansion, historical resealing/migration, graph binding change, path outside this five-file lease, or any runtime/database/product/provider operation. This handoff grants no merge authority; PRIME owns review and merge.
