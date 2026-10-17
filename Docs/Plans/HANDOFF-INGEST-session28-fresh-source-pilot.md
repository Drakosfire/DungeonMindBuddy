# HANDOFF — INGEST: fresh Session 28 source through exact-run review

**Status: BLOCKED — proposal only.** This file proposes the next bounded Ingest capability. It grants no implementation, provider, corpus, APP-STATE, Graph, or runtime write lease. PRIME reviews and pins/activates after the operator’s Build rollout. Keep 5202 and Build unchanged.

**Re-anchor:** Buddy `main@babdf1fe78cde23f5954414a675e487a606f0a03` (observed 2026-10-17). Serial successor to merged #1287. Re-anchor again before activation; this is not an active branch/checkout contract.

## Goal and boundary

Prove one *fresh* Session 28 recap through the ordinary Ingest path: exact operator source → normal extraction → evidence/candidate review → durable, World-bound source and run → exact-run node-bearing projection after reload.

This is a real-source acceptance slice, not a new ingestion architecture and not Graph admission. Candidate extraction, source persistence, and an exact-run projection do **not** mean the four sessions are in the native World Graph. Native Graph admission/publication and readback remain a separately authorized gate.

The end goal is to support the operator’s Session 29 question/work, show Sessions 26–28 as verified native Graph knowledge, and enable Build dogfooding. This pilot proves only Session 28’s fresh-source path. Session 29 and Sessions 26–27 require their own exact-source and publication/readback evidence; the pilot must not be reported as completing them. The operator owns Build changes; no Build write set is proposed here.

## Current evidence and limits

- #1284 merged the World-scoped source identity and frozen World-binding contract. A new source ID is scoped by verified native World, campaign, session, and normalized-content digest; old worldless IDs are not silently rebound.
- #1287 merged selected-managed-World validation for exact-run projection. Its acceptance witness used a synthetic Session 22, synthetic binding, and synthetic node projection. It proves the software seam, not a real Session 28/29 source or native Graph membership.
- Session 29 has source-first handcrafted gold (#1212: 90 nodes, 155 assertions, 167 literal ranges across nine sources). The retained Session 29 candidate was reported by #1251 as blocked by ten unresolved evidence references. #1244’s legacy-reference recovery is explicitly held by PRIME; it is neither a prerequisite nor a substitute for fresh processing.
- The operator-supplied Session 28 raw artifact is available at `/home/drakosfire/C2 Session 28 — The Meat Mind.txt`. Its observed raw-file SHA-256 is `683d64889a0921db6fbfbbe448d57beac244bc00b0c169c54c55eb03f9f45b24`; the retained package records a different SHA-256 (`d19e72c07e5aa5b584f7820c4d30a00df3e7706d5ec7bf7a45b19dce2f67b6eb`). Treat these as different artifacts until the exact supplied bytes are hashed and processed. Do not register, repair, or relabel the retained package as this source.
- Current main tracks original and normalized recap files for Session 26 (`Session 26 - Thrin Pulled Underground Wall Breach.md`) and Session 27 (`Session 27 - Ironveil Warehouse Wall Collapse.md`). Their current native Graph presence has not been verified. The current tracked tree has Session 29 prep/Plan and handcrafted gold, but no Session 29 recap path; this does not rule out an operator-held original source. Session 28’s original is operator-held rather than a tracked recap. No end-to-end real recap Process → fresh APP source → exact-run projection has been accepted on current main.
- The last reported 5202 error was `ingest_context_not_configured` for `DUNGEONMIND_PUBLICATION_BASE_URL`. Whether the current main/.env launch resolved it is unverified. Verify configuration without exposing values before any Process attempt.

## Proposed workflow contract

1. **Pin source identity before Process.** Use the exact operator-supplied Session 28 bytes and calculate their SHA-256 at the execution boundary. Bind campaign `longmont-c2`, session 28, selected managed World `elderwyld`, and the server-resolved native World/binding version. Record the source revision and request/run IDs. Missing or conflicting metadata blocks before writes; never infer World from a title, campaign slug, current default, or the retained package.
2. **Use ordinary Process.** Exercise the existing `generate_recap_memory` route with the explicit managed World and fresh raw text; do not call a retained-package registration, candidate-repair, migration, or recovery path. Preserve the original bytes. A changed-source collision must require an explicit replacement decision and must not continue against stale staged text.
3. **Review the new run.** Capture the exact ExtractionRun, candidate and validation report. Verify report/run/source identity and hashes, evidence spans, unresolved-reference count, and extracted entities/relationships against source. Produce a Session 28 review/gold artifact only if the active lease names its path and the reviewer can distinguish literal evidence, derived interpretation, and unresolved claims. No candidate/model output becomes canon automatically.
4. **Prove durable exact-source reopen.** Read back the exact source and frozen managed/native/binding tuple from APP-STATE; reload that exact run in Ingest; confirm the enriched node-bearing projection is sourced by that run and the selected World. A latest-run/default-World fallback is a failure.
5. **Stop before Graph publication.** Do not claim Session 28 is “in the Graph” from a ready candidate or source projection. A later publication gate must freeze the reviewed decisions, exact source/run, target native World and current head; require an explicit user-confirmable plan and transactional stale-head protection; then prove a fresh native Graph readback at the resulting revision.

## Acceptance and failure behavior

Pass only when a fresh Process creates one new exact run and world-scoped source from the supplied raw bytes, a human-reviewed candidate has no unresolved evidence references (or each exception is explicitly dispositioned), APP-STATE readback matches the frozen World tuple, and a fresh Ingest reload shows the same exact run and node-bearing projection. Preserve any provider failure and its run receipt rather than silently retrying or resending. “Candidate ready,” “source saved,” and “projection loaded” must each remain distinct from “published to Graph.”

No paid provider request, real corpus write, APP-STATE mutation, Graph write, serving/API restart, or UI navigation is authorized by this proposal. Activation must name the provider/model/budget, exact corpus root and rollback/retention plan, APP database, native World binding, ports/proxy, and runtime ownership. Use a disposable rehearsal first if it can prove the route without the real recap. A real run must be explicitly activated with the exact target and idempotency plan.

## Scope proposal and successors

The first activation should be one serial implementation/acceptance lane. Proposed code write set, if a concrete defect is found, is limited to:
- `Docs/Plans/HANDOFF-INGEST-session28-fresh-source-pilot.md`
- the exact ordinary Process/recap route and source/run persistence files shown necessary by a read-only audit
- their owning route, source-identity, and exact-run projection tests
- Ingest’s exact-run reader tests only if rendered acceptance exposes an in-scope defect

PRIME must replace this conditional list with exact paths before marking ACTIVE. Do not expand to shared navigation, Build, schema/migration, bulk corpus tooling, legacy recovery, publication, or Graph services in this slice. Any such need returns to PRIME for a split or explicit contract amendment.

After this pilot, sequence the target data work as separate source/run/review proofs:
- Session 29: use its exact original recap; treat the retained candidate’s ten unresolved refs as diagnostics, not accepted evidence.
- Sessions 26 and 27: process the exact corpus sources and verify independent source/run identities and exact-world projections.
- Native World Graph: separately authorized reviewed publication for each exact candidate, followed by native readback proving each session’s intended nodes/edges are queryable.

Completion of the pilot is not completion of those successors or of Build dogfooding. Any report of the operator’s full target must enumerate which sessions have fresh source, exact run, review, durable source/projection, Graph publication receipt, and post-publication readback; unknown is not “done.”
