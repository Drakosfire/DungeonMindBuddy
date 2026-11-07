# RETRIEVAL: retain keyword focus during broad source recovery

Status: DELIVERED through PR2185, merge bc405328880e2e5abed8d7bb06d6f1b26b3b10d3.
Reviewed head56cefd378226f6d15173b85d3e0588dfcbcbcd7a passed independent Bugbot
review and all seven checks. API integration51501f24feedca7fafcf96b2f528edcb902cdb41
and no-op reader fence0124 are delivered; UI unchanged, delivery lease released.
Five ordinary requests completed with inspectable native citations and conserved
retained data. The two original runs took43.3s and42.6s/four rounds, but neither
expanded broadly or exercised retained recovery focus. No causal speedup for this
change is proved. The selected-source contrast read an extra unrelated Session20
source and took14.7s/two rounds rather than11.0s/one. Source and writer pins are
unchanged, conversation hashes differ, and performance/whole-goal acceptance
remain open. The ACTIVITY successor fixes a separately observed caption gap.
Base: a273bfc9b6c1e14f55df384b2160179858935bd1 (remote main, 2026-11-07).
Branch: codex/native-keyword-recovery-focus, existing buddy-context-loop checkout.
Topology: serial after merged/delivered PR2184. Existing INGEST lanes do not own
these paths; Play2172 remains held. No new environment, checkout or runtime lease.

## Outcome and design critique

The 73-second ordinary run selected literal keywords, narrowed the first section
view, then expanded to all sources. Later decisions lost those keywords and took
seven rounds. Retain actual acknowledged keywords as soft navigation focus after
broad recovery; all source choices remain available. No planner call, read cap,
writer/model change, source authority, admission path or corpus mutation.

Adopt the existing examined-candidate metadata channel. Add distinctly typed
previously acknowledged keyword rows to that host catalog, then project them as
selected_content_keywords rather than examined/acquired source subjects. This
keeps the existing input codecs and historical digests: adding even a default
field to V1 would change old parent hashes. No keyword is presented as evidence
or answer coverage, and these rows never receive votes or read grants.

Reconstruct from the existing admitted native selection events using exact query,
World, source revision and product-attempt scope. The APP dispatch boundary checks
that supplied focus rows equal the actual acknowledged keyword catalog. The host
adds them only after existing broad expansion. Factor the existing keyword
selection reconstruction into its current APP helper; remove the duplicate host
implementation. No alternate provenance owner or persistent focus store.

Failure cases: no selected keywords or no expansion leaves the prepared wire
unchanged; unavailable/foreign/stale hints do not narrow sources; modified words,
handles or duplicate focus rows cannot pass actual dispatch admission. An old
reader cannot reconstruct the new prepared projection, so add one no-op reader
fence without rewriting retained rows. Retain actual source/claim grounding and
all mandatory selected references.

One corrected frozen comparison used the actual long-context dispatch policy.
It selected both sources that required later ordinary rounds. Thirteen votes
would produce eleven reads under the existing full-before-section deduplication.
That is a counterfactual footprint, not latency, coverage or independent quality
proof. Older acquired-body experiments omitted context selection; their rejection
is not evidence for shipping body-context input or raising limits.

## Exclusive expected writes

- This handoff and Docs/Plans/HANDOFF-RETRIEVAL-native-keyword-prioritization.md
  (truthful predecessor settlement).
- src/application_state/agent_conversation/native_source_keywords.py.
- src/application_state/agent_conversation/jev_retrieval_contract.py.
- src/application_state/agent_conversation/native_retrieval.py.
- apps/live_control_server/services/corpus_source_navigation.py.
- src/application_state/migrations/versions/20261107_0124_native_keyword_focus.py.
- tests/test_jev_retrieval_contract.py.
- tests/application_state/test_surface_native_acquisition.py.
- tests/application_state/test_surface_native_decisions.py (optional examined
  metadata hook for actual SDK admission; defaults preserve existing fixtures).

## Verification and resources

Prove SDK wire projection and question-count invariance, exact APP authorization,
source/attempt rejection, reload, broad recovery, mandatory source preservation,
untampered completion and historical no-focus wires. Use existing disposable
APP54329 and synthetic Core fixtures; never primary APP54331/Core54330 or benchmark
55447 for tests. Retain before/base/failure evidence in the established private
runtime-evidence root. Review cumulative base/head diff, obtain independent Bugbot
review and all CI, then merge/deliver under standing PRIME authority.

Ordinary original and contrast runs keep the writer and retained source pins;
record actual keyword focus, broad expansion, rounds, reads, context, latency and
native citation support. Source-only votes and counterfactual estimates never
establish full-goal completion or operator acceptance.
