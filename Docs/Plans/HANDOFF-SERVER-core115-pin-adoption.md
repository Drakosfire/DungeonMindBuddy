# SERVER — exact Core115 dependency adoption

Status: REVIEW under PRIME's 2026-10-12 bounded dispatch. Owner: SERVER;
PRIME owns independent review/merge. Serial branch `codex/server-core115-pin`,
isolated checkout `/tmp/buddy-agent-source-targets`, fetched Buddy main base
`fa74809ea44d14a138ac652f57c5889e347e64d2`.

Primary question: does Buddy's unchanged read/reviewed-publication consumer remain
compatible when its exact Core pin advances from
`13143455b304d748c249bd7bd628134c421bf6d9` to merged Core #115
`d8798a5d5d6b46efa3e485e5b493a8fc3d4a94f7`?

Core115 preserves a source's opaque producer `source_domain_key` separately from
the generic domain during v6 publication. It uses bounded source authority and
writer-fence validation; reader admission, SourcePairs and durable wire schemas
remain unchanged. The prior candidate with Core131 is stale for writer semantics.

Exclusive tracked writes: `pyproject.toml`, `uv.lock`, and this handoff. The lock
diff must contain only the exact Core source/requirement pin; no package metadata,
timestamp, dependency-version or wheel churn. No Buddy runtime feature, consumer
relaxation, UI/dependency build, private configuration, retained authority, live
environment or operator-runtime change is leased.

Verification uses a disposable environment at
`/tmp/buddy-core115-pin-verification/.venv`, copied in isolation from the accepted
candidate's cached package set. Locked sync replaced only Core and the two local
project/source distributions, preserving the accepted candidate and live envs.
Focused source reads, producer/default-selection checks and actual reviewed
publication → native/Harness/source-read checks must pass. Real publication
tests may use only a fresh `dmb_observation_test_*` Core database and the existing
unique `dungeonbuddy_app_state_test_*` fixture at disposable loopback 55443;
retained databases at 54330/54331 are excluded. No provider call is authorized.

Before handback: check installed exact pin/module ownership, locked environment
and compatibility, inspect cumulative base→head diff, update exact evidence,
commit/push and open the focused PR. Stop for a real consumer/API failure,
unrelated lock change, unsafe test authority, or required path outside this lease.

Keep `/tmp/buddy-runtime-candidate-20261012` (Core131), the live `98f0` checkout,
rollback/continuity roots and all private configs intact. A new runtime candidate
environment is a separate funded step only after this pin PR merges. Full World,
quiet activation and operator dogfood authority remain pending.

## Implementation evidence

Pin implementation: `6713115d5bca03033a0c602c1dd109eaa0b1b772`.
The cumulative dependency diff is five insertions/deletions: two pyproject pin
locations, one accurate pin comment, and two lock source/requirement locations.
No other lock metadata or version changed. `uv sync --locked` re-used the copied
cached package set and installed only Core plus the two relocated local source
distributions. `uv pip check` (100 packages) and offline lock check passed.
Installed Core is exact `d8798a5d`; Buddy consumer modules resolve to this lane.

Nine focused cases passed: producer/default-selection checks, exact recap
descriptor/continuation and ordinary World reads, digest-bound admitted source
read, ordinary Harness observation claims, and selected-object observation
projection. Two actual owning cases also passed:
`test_actual_producer_publication_native_harness_answer_and_source_open` and
`test_actual_node_only_then_source_proven_observation_followup`. They used newly
created `dmb_observation_test_core115_c0cd11d6c1d9` on disposable 55443 with exact
Core115 migrations and unique APP fixtures. All scratch databases were cleaned
after the run. No test was skipped; the existing Pydantic field-shadow warning
remains. No retained database or provider was used.

The original candidate still reports Core131 and the live environment still
reports Core `ba6069b9`; neither was mutated. No UI install/build was repeated.
Whitespace and cumulative diff checks pass. Open #1014 has no leased-file
collision. Historical draft #826 still carries an older Core96 pin in these two
dependency files and must be restacked before future merge; it is not modified
by this main-based adoption. No acceptance token is claimed by SERVER. PRIME
reviews the exact final PR head, which includes this evidence handoff.
