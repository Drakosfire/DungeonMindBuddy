# PROMPTS: semantic Plan reference context

Status: ACTIVE. PRIME designs and implements the operator-prioritized prompt cleanup.

## Boundary and topology

Stacked on PR2194 exact982597283208e95974b7b466cc37da3630f68d32 in the
existing buddy-context-loop checkout. Merge order:2192 policy,2194 native
navigation, then this Plan reference projection. Retarget on the merged parent;
review the final cumulative slice before merge. No new checkout or dependencies.
PR2194 code is committed and independently approved. Its immutable candidate and
recipe are separately reviewed; this slice changes neither that release nor its
pending CI/delivery gates. INGEST paths and held Play2172 remain outside scope.

Outcome: current Plan requested-work selection gets human reference labels and
source extent kind, without World/Graph/source identity, revision, hash or binding
metadata. Full selected records remain in the existing parent request, digest and
locked native-reference checks. No new provenance authority or regex scrubber.
Current emitters consolidate on V6; retained V1-V5 readers reconstruct their exact
accepted wire. The no-op reader fence prevents older readers misreading V6.

## Exclusive expected write lease

- This handoff.
- src/application_state/agent_conversation/plan_placement.py
- src/application_state/agent_conversation/plan_authoring.py
- src/application_state/agent_conversation/plan_jev_decision.py
- apps/live_control_server/services/plan_jev_dispatch.py (successor to2194's committed lease)
- src/application_state/migrations/versions/20261107_0126_plan_reference_context.py
- tests/application_state/test_plan_placement.py
- tests/test_native_plan_assertions.py

## Invariants and proof

Reference labels remain untrusted navigation context, never evidence or edit
destinations. Preserve the author's exact operation, page title, dialogue, target
availability and existing local placement selectors. Source section/full-document
choices stay distinguishable. Request/model output cannot alter reference scope,
revision, source extent or destination. Do not decode host meaning from ID strings.

Verify actual SDK wire contains semantic reference fields only, and that parent
proofs still retain the exact identity. Cover same-label references and changed
source/Graph pins, original placement and explicit operation, and historical wire.
Run native Plan decision/authoring boundary tests. Independently review, push/open
this small PR, satisfy CI, merge and deliver separately. No provider calls, runtime
write lease, DB migration or ordinary-authoring write is granted by preparation.
All other prompt roles and the full References/retrieval/authoring goal remain open.
