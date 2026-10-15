# BUILD: preserve worldbuilding source bytes for historical passage reads

**Status:** ACTIVE — PRIME implements this bounded Buddy slice; ARCHITECTURE independently reviews the exact result.

- **Base:** Buddy `main@199a7404701d6a53fa8f4a1d68b2c7874df6771a`
- **Branch:** `codex/mirathorn-worldbuilding-source-durability`
- **Checkout:** `/tmp/buddy-mirathorn-source-durability`
- **Runtime:** none; no serving ports or operator databases
- **Purpose:** make source passages from an exact reviewed worldbuilding run readable from the existing APP-STATE immutable source store, including after source edits and removal of derived local snapshot/index files.

## Outcome

When Build creates an extraction run from a registered worldbuilding source, Buddy adopts the exact committed Markdown bytes into the existing immutable `source.revision` authority using the admitted artifact ID, domain, campaign, World, and digest. An ordinary admitted worldbuilding source-anchor read can use that exact stored body to rebuild the deterministic paragraph-span index and open the requested span. It must never substitute the latest workspace text.

This strengthens historical source access using the existing storage contract. It does not make APP-STATE the authority for the Build document itself, source admission, graph facts, graph publication, or World selection.

## Invariants

- The stored text is read from the registered source artifact and rehashed before persistence; the artifact digest is an assertion, not a replacement for hashing.
- Persistence is idempotent for the same artifact and digest. Different content remains a distinct immutable revision.
- Reads match the exact artifact ID and digest and verify `source_domain`, `campaign_id`, `session_id`, and `world_id` against the registered artifact before returning source text.
- World Graph passage reads validate Build ownership from registry metadata only; they do not require the mutable current Markdown file to remain present. The Build editor and stale-source navigation keep their existing current-file checks.
- Paragraph spans are deterministically reconstructed from the exact immutable Markdown. Span identity, line range, and digest must match the requested admitted span.
- Existing file-backed reads remain available when no durable body exists. Missing or changed files never authorize a read from the current workspace revision.
- Existing WorldGraph source admission, managed-to-native binding, evidence visibility, graph revision, and publication authority remain unchanged.

## Exclusive write set

- This handoff.
- `apps/live_control_server/services/graph_run_registry.py`
- `apps/live_control_server/services/worldbuilding_source_span_read.py`
- `tests/test_worldbuilding_historical_passage.py`
- `tests/test_worldbuilding_source_body_durability.py`

No APP-STATE schema/service changes; no frontend or Agent prompt changes; no corpus, provider, retained database, World publication, runtime, or server configuration changes. If the existing immutable source service cannot store and retrieve a worldbuilding source without changing its contract, stop and return the required contract question for ARCHITECTURE.

## Owning-boundary verification

Using the existing disposable PostgreSQL fixture and synthetic Build data:

1. Create a registered World-owned Build source and an extraction run; verify exact Markdown is present in APP-STATE with the same artifact/digest/scope and that replay is idempotent.
2. Save a newer workspace revision, then remove the original source file, frozen `source.md`, and derived span-index sidecar. Open a span from the original admitted source and verify exact old passage bytes, line range, and digest in the current process and a fresh process.
3. Verify a missing durable body and missing local snapshot fail closed; never return newer workspace text.
4. Verify mismatched domain, campaign/session, World, digest, and span ID are rejected. Preserve existing wrong-native-World and corrupted-source checks.
5. Run only the focused historical-passage, source-persistence, and owning worldbuilding admission tests; preserve unrelated inherited failures with exact evidence.

Inspect the exact cumulative `main`→head diff, run lint and whitespace checks, and request independent ARCHITECTURE review before merge. No operator-facing runtime acceptance is claimed by these tests.
