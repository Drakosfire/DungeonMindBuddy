# INGEST: preserve disjoint reviewed description extents

Status: ACTIVE implementation. Root adopts independent design review 6f2ce85f09b122353502b6c54ec5d533250235ae655505632dae326b8d9c48b8 and explicit gate decisions recorded below.
Root designs this bounded successor under the authorized ingestion/publication goal.

## Confirmed loss and proposed outcome

S8 actual baseline run 6f132f6b-4d3d-4f2f-b3fc-5edf994d3834, candidate
eb5d30c48d920f988980b210254da0fc788326f2df30471df302d935c64a5b61,
node44 contains supported prefix [0,680), an unsafe role-assignment middle,
and supported suffix [889,3598). Source review
94da668625ec250f36aac8bdc65c5ea97f268081ba3e59785b4ea415ab2beee2
shows selecting the suffix loses actual correct Lysandra anxiety (01.Q02);
selecting only the prefix trades away the useful late linked chronology.

The current model rejects two disjoint extents as duplicate selected field.
PR2070 deliberately shipped one extent and closed its lease. This proposal
supersedes that limitation only after the new demonstrated coverage case and
owning-contract review. It does not rewrite the settled predecessor history.

Permit multiple non-overlapping proper description extents as separate existing
SelectedDescriptionExtent facts for one selected node. Each compiles to its own
existing WK CreateFact / dnd5e:summary literal and owner-derived extent metadata.
Never concatenate fragments, rewrite prose, use source-only text as model output,
change the saved candidate or add a producer/representation/fallback. Preserve
all raw quality failures and unchanged Gold; reviewed selection is a separate score.

## Prospective serial slice and expected writes

Parent #2149 exact857093a2263053b5c6ab30423262be03f1fe55bf; merge/rebase
#2145 → #2149 → successor. Rejected #2148 is not inherited. Prospective branch
codex/ingest-disjoint-description-extents, same isolated checkout after activation.
No Core/WK/dependency/migration/source/model or primary/evaluator writes in implementation.
Tests use existing disposable fixtures only. Actual publication requires a later
exact reviewed manifest and once-only confirmation, not this design.

Exclusive expected writes:
- apps/live_control_server/models/native_recap_preparation.py
- apps/live_control_server/services/native_recap_preparation.py
- tests/test_native_recap_preparation.py
- Docs/Plans/HANDOFF-INGEST-disjoint-description-extents.md

One indivisible capability: model admission and compilation/inventory/provenance
must agree. Public review packet inventory becomes one plural list of selected
description extents, including the one-extent case; no competing scalar/plural
compatibility path. Repo consumer search found only owner and tests for the old
scalar key; verify that finding before activation. Existing signed whole-field
and single-extent review selectors retain their serialized shape and actual
prepared operations; retain their normalization/confirmation regression checks.

## Invariants and failure cases

- Whole-description plus any extent is rejected. Other duplicate selected fields,
  identical/overlapping extents, malformed bounds, empty text, split UTF-8,
  full-field extent and wrong digests remain rejected at their owning boundaries.
- Do not infer each excerpt is entailed merely because literal; source/identity/
  uncertainty review remains mandatory for each retained assertion and its support.
- Each extent keeps a separate existing world-context provenance payload bound to
  actual run/revision/candidate/record/field/start/end/slice hash. Caller spoofing
  remains refused. Raw model output/candidate/source unchanged.
- Inventory lists every selected extent and computes held complement of their
  union. Whole description remains unselected when only extents were selected.
  Never overwrite an earlier extent with the last one or count held bytes as kept.
- Existing object identity, evidence, predicates and once-only prepare/confirm
  ownership remain intact. Generic shared recap/worldbuilding selector semantics
  must be tested without claiming worldbuilding corpus acceptance.
- Prove WK/Core already admit separate summary assertions for the same entity in
  this one operation; do not add Core semantics to force it. If not true, return
  to design rather than introducing an alternate representation.

## Gates before ACTIVE and validation

Independent critique of existing native contracts, duplicate/overlap rules,
scalar-inventory consumers, source scope and the real S8 loss. Inspect current
remote main/open PRs/write leases (including native writer #2151) before activation.
Root adopts exact contract and write scope only after gates resolve.

After activation: malformed/overlap/duplicate/whole-mix and UTF-8 tests; actual
prepare/confirm/fresh readback of two separate literals plus independent source
openings/provenance; held middle absent; legacy selector behavior; both recap and
worldbuilding owner tests. Use real disposable persistence where needed, no
primary or retained evaluator in tests. Inspect cumulative diff, independent
exact-head review, commit/push/open the bounded PR. No merge authority.

Then compose from accepted e841 runtime preserving donor/ID repair, independently
qualify, and reuse unchanged actual6f132 candidate. Source-only admission is already
verified at native73cf epoch25; never repeat it. Governed publication must retain
both actual safe regions with exact provenance and preserve all prior data.
Full source/Gold gaps and the overall C1S1–10 goal remain open afterward.

## Activation decisions

Fetched remote main and active PRs; #2151 head945194354bd23f1a53ffecc15d82a3fe4a41dde2 has no expected-path overlap. Branch codex/ingest-disjoint-description-extents is allocated from exact parent857093a2263053b5c6ab30423262be03f1fe55bf in this checkout. Parent write lease is consumed; no concurrent preparation-model writer was found. No ports/services or retained database write window are allocated.

Reject extents whose union covers the whole field; use existing whole-field selection. Preserve request fact ordering/field-index operation IDs; sort a separate range view only. Canonical plural packet inventory replaces scalar; per-assertion provenance stays scalar. WK already iterates separate facts and deduplicates operation IDs rather than predicates; real persistence is a completion gate, not authorization to change WK/Core if it fails. Existing disposable test fixtures may write only their isolated temporary databases; primary, dogfood and evaluator55447 remain excluded.

## Implementation validation

Owner suite: 191 passed (27 serializer warnings), including both real disposable
PostgreSQL prepare/confirm/fresh-readback cases. Log:
/tmp/disjoint-extent-full-owner-pg-v3.log. Earlier v2 run preserved two fixture
wiring failures (missing pytest request argument); corrected without changing
production behavior. Tests exercise separate summary literals/provenance,
create/reuse identity, reversed request order, three extents, all held gaps,
overlap/whole-union refusal, and recap/worldbuilding shared selectors.
Consumer search confirms plural inventory is owned only by service and tests.
No retained evaluator, primary, source or candidate writes occurred.
