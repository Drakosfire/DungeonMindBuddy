# INGEST: Gazetteer submitted ownership support

Status ACTIVE; PRIME solo implementation under the Mirathorn ingestion goal.
Exact base d052e3dfcd6d5a39cfc1c4d90f7b7ed2edaaa3bb; isolated standalone
/tmp/buddy-worldbuilding-role-support clone, branch codex/gazetteer-role-support.
This avoids writes to full /home; it does not bypass rejected cleanup or provider
holds. No serving/state lease. Serial successor of accepted initial-ledger repair;
open MIND consolidation PRs remain separate held leases. This slice uses the
existing profile-owned source compilation hook, not shared consolidation edits.

Exclusive six paths:
- this handoff
- src/graph_memory/extraction/worldbuilding_gazetteer_profile.py
- src/graph_memory/extraction/worldbuilding_profile_catalog.py
- src/graph_memory/extraction/worldbuilding_role_support.py
- tests/test_worldbuilding_role_support.py
- tests/test_worldbuilding_role_support_pipeline.py

Outcome: explicitly selectable Gazetteer1.3 preserves1.2 instructions/source
retention and adds a narrow submitted-support disposition. Native v5 has no
proprietor/operator predicate; owns asserts ownership, weak association is not a
fallback. Defer an owns candidate only when every complete cited span positively
matches a named role-only proposition for its actual candidate endpoint labels.
Do not assert that the actor is not owner or that ownership is absent elsewhere.
Exact source-span identity and literal quotes are required. Separate explicit
ownership for the same endpoints disables this narrow guard; other holds remain.

Grammar: full named Markdown role heading `Actor — Proprietor of [the] Target`
(or en dash/hyphen); full `Actor owns [the] Target` or named Owner heading
recognizes independent ownership. Optional bold formatting/case/whitespace and
terminal full stop only. No pronouns, aliases, inferred identities, partial
clauses, arbitrary prose inference or changes to negation/modality/fiction time.
Unrecognized full spans/mixed support are explicitly unresolved, not recognized
role-only; no semantic deferral from empty/missing/duplicate/invalid support.
Do not repair evidence or invent a native predicate.

Preserve raw provider/candidate input, nodes/descriptions/source observations and
all exact references. Existing deferred items carry stable reason and support;
structured compiler diagnostics retain raw edge, IDs and exact profile version.
Reprocessing is idempotent. Version1.2 remains historical; do not change UI/default
profile selection or old run receipts. No new public request/schema or Core change.

Verify role-only, independent ownership, wrong endpoints, missing/mixed/duplicate
support, negated/hypothetical/quoted clauses, unparsed ownership forms, source
retention and unchanged other owns candidates. Owning production pipeline fake
provider with frozen synthetic source must show before/after profile1.2/1.3,
valid deferred preview and raw-source preservation. Real saved response replay
may provide local research evidence, no new provider request or World publication.

Finish focused tests, exact cumulative diff, commit/push/PR and independent
ARCHITECTURE review. No full Mirathorn or general entailment acceptance claimed.
