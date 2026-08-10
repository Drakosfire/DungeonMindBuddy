# HANDOFF — Eldyrwild effective conformance after first governed correction

**Created:** 2026-08-10
**Status:** IMPLEMENTATION COMPLETE — PR #542; R_current = Q_live = rev:b90646fb5b135988bd7842cde858c96e
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-effective-conformance-after-first-correction.md`
**Conversation name:** `Eldyrwild Effective Conformance After First Correction`
**Flow / agent:** `BUILD`
**Handoff direction:** `DESIGN → CODE`
**PR title:** `CONFORMANCE: re-anchor Eldyrwild after first governed correction`
**Branch:** `build/eldyrwild-effective-conformance-after-first-correction`

**Merged code predecessor:** PR #537, merge commit `9b4f02ab7b1b2fcb2a88e36f10140dd25bc0a9c9`
**Current design-observation main:** `81e7b5d71ff647e17fe806bb4ab851f6800b478c` at handoff authoring; BUILD must record fresh `origin/main` at dispatch rather than treating this SHA as frozen authority.

> **Dispatch gate:** PR #537 being merged is necessary but not sufficient. Before BUILD begins, the operator must complete and hand back the canonical Lysandra live-exit proof:
>
> * exact `P_live`;
> * integrity heal status `already_healed`;
> * Lysandra status `eligible` on `P_live`;
> * canonical apply of locked correction C with `--allow-live-world`;
> * exact `Q_live != P_live`;
> * `parent(Q_live) == P_live`;
> * old X historical / contradicted / non-current;
> * X′ current through exact C;
> * siblings unchanged;
> * source/adjudication seals unchanged;
> * parent-relative effective delta `semantic 0 / represented +1 / residual -1 / mechanics 0`;
> * pinned and unpinned rebuild equivalent at Q_live;
> * retry against Q_live returns `already_applied`;
> * no second revision and no support churn.
>
> If that proof is missing or ambiguous, do not start this PR. This slice formalizes the state produced by the governed correction. It does not perform the correction.

---

## §0 Mission

Formally re-anchor Eldyrwild's **current-descendant effective relationship conformance baseline** after the first real governed source correction, using the actual canonical live World Graph state rather than forcing the immutable historical adjudication counts onto an evolved graph.

This PR establishes that:

> the current effective-conformance fixture is an exact, reproducible observation of one explicit canonical Eldyrwild revision that contains the successfully replayable Lysandra correction, while the original adjudication anchor, historical source authority, source seals, correction authority, and conformance semantics remain unchanged.

This is a **read/re-anchor slice**.

It owns no graph mutation.

It owns no new correction semantics.

It owns no reinterpretation of DungeonMind vocabulary.

---

## §1 Why this PR exists

The Campaign Supergraph semantic-adoption sequence deliberately separated three authorities:

1. **Historical adjudication authority** — the immutable revision and source seals against which the relationship residual ledger was originally adjudicated.
2. **Current graph authority** — the actual live Eldyrwild head after governed writes.
3. **Effective-conformance interpretation** — a deterministic read of an exact graph revision against the pinned DungeonMind vocabulary, current-support semantics, adjudication continuity, and explicit adapters.

Before the first real correction, the canonical effective fixture was anchored to historical revision:

```text
rev:3413bf6f5044cf2680233f5e37c90dcf
```

with historical observation:

```text
346 semantic
294 effectively represented
52 effective residual
2 uses_statblock mechanics
```

Those values remain legitimate historical evidence.

They are **not** a universal invariant for every descendant.

The live Eldyrwild graph has evolved beyond that historical adjudication revision. PR #537 proves the Lysandra correction with a parent-relative invariant precisely so implementation does not depend on pretending the live parent is still `346 / 294 / 52 / 2`.

Once the canonical live correction succeeds, the repository needs one formal current-descendant baseline that says:

```text
This exact current revision is what effective conformance means now.
```

That is this PR.

---

## §2 Authority and shared vocabulary

| Term                            | Meaning                                                                                                                                                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A**                           | Immutable adjudication anchor `rev:3413bf6f5044cf2680233f5e37c90dcf`. Never moved by this PR.                                                                                                                         |
| **P_live**                      | Exact canonical Eldyrwild parent used for the post-merge Lysandra correction. Supplied by live-exit handback.                                                                                                         |
| **Q_live**                      | Exact canonical child created by applying correction C to P_live. Mandatory predecessor evidence.                                                                                                                     |
| **R_current**                   | Exact canonical Eldyrwild revision selected as the current effective-conformance baseline at BUILD capture. Prefer `Q_live`; if the head has advanced, R_current must be Q_live or a proven descendant satisfying §5. |
| **X**                           | Historical defective Lysandra edge `edge:npc_lysandra:threatens:node:cultists_of_longmont:is-threatened-by-cultists`.                                                                                                 |
| **X′**                          | Corrected relationship `edge:node:cultists_of_longmont:threatens:npc_lysandra`.                                                                                                                                       |
| **C**                           | Locked authored correction contribution `contribution:4c65f668dc95ef4f`.                                                                                                                                              |
| **Historical source authority** | Original Session-8 recap artifact, evidence/span, contribution/assertion, adjudication fixture, and source seals.                                                                                                     |
| **Current support**             | `support_state == supported` and nonempty `active_contribution_ids`.                                                                                                                                                  |
| **Current effective baseline**  | Exact output of the existing effective-conformance analyzer for R_current, checked in as the reproducible current fixture.                                                                                            |

Correction identity remains:

```text
C:
  contribution:4c65f668dc95ef4f

target contribution:
  contribution:86ea8a3d97dd18cc

target assertion:
  assertion:1dc0fef6561c3282

replacement assertion:
  assertion:3668ba31192a37ad

replacement edge:
  edge:node:cultists_of_longmont:threatens:npc_lysandra

locked C source-payload digest:
  78d4d7118c3ba71ed0f930157bcd2343c675ccab8544580ff0aa506aa9ec0c5d
```

This PR must not regenerate or replace any of those identities.

---

## §3 Core invariant

For one explicit R_current:

```text
R_current == Q_live
OR
R_current is a proven descendant of Q_live
```

and all of the following must hold:

```text
A remains the immutable adjudication anchor

Q_live is present in R_current ancestry

C remains exact and revision-bound

X remains durable historical material
X is not current through the corrected target support

X′ remains current through C

historical adjudication/source seals are unchanged

existing effective-conformance code, vocabulary pin,
current-support rules, and explicit adapters are unchanged

effective_conformance(R_current)
  == checked_in_current_effective_fixture

pinned rebuild(R_current) is equivalent
unpinned rebuild(R_current) is equivalent

the PR publishes no World Graph revision
the PR advances no World Graph head
```

The fixture values are whatever the existing analyzer reports for the exact R_current.

Do **not** choose numbers first and modify code/data until they appear.

---

## §4 Required pre-dispatch capture

Before the first implementation edit, BUILD must record:

```text
origin/main SHA

PR #537 merge:
  9b4f02ab7b1b2fcb2a88e36f10140dd25bc0a9c9
  proven ancestor of implementation base

canonical world root

P_live
Q_live

current canonical head

R_current
```

Also capture the completed Lysandra exit observations:

```text
integrity heal:
  already_healed

Lysandra on Q_live:
  already_applied

parent(Q_live):
  P_live

X target support

X′ support

C revision-bound digest

source/adjudication fingerprints

E(P_live)
E(Q_live)

P_live → Q_live:
  semantic unchanged
  represented +1
  residual -1
  mechanics unchanged
```

### If canonical head advanced after Q_live

Do not silently switch to "latest."

If:

```text
head == Q_live
```

then:

```text
R_current = Q_live
```

If:

```text
head != Q_live
```

then prove:

```text
Q_live is an ancestor of head
```

and inspect the exact descendant.

R_current may be the newer head only if:

```text
Q_live ancestry is proven

C is still exact/revision-bound

X remains non-current

X′ remains current through valid authority

historical source/adjudication seals still match

R_current rebuilds successfully

effective conformance can be computed without a new semantic exception
```

If any of those fail, stop and return to DESIGN.

Do not turn this PR into repair work for the intervening descendant.

---

## §5 Expected implementation scope

### Primary files expected to change

```text
tests/fixtures/dungeonmind_kernel/
  eldyrwild_relationship_effective_conformance_v1.json

tests/test_dungeonmind_relationship_effective_conformance.py

Docs/Plans/PR-TRACKER-campaign-supergraph.md

Docs/Design/STATUS-world-graph-continuity-spine.md
```

The current effective fixture is the current-baseline artifact. Re-anchor it to R_current.

The immutable adjudication/source-history fixtures remain historical authority and must not move.

### Explicitly expected to remain unchanged

Unless a concrete existing-contract defect is discovered, do not modify:

```text
apps/live_control_server/integrations/dungeonmind_kernel/
  relationship_effective_conformance_v1.py

apps/live_control_server/integrations/dungeonmind_kernel/
  relationship_adjudication_continuity_v1.py

apps/live_control_server/integrations/dungeonmind_kernel/
  whole_world_conformance_v4.py

apps/live_control_server/integrations/dungeonmind_kernel/
  relationship_explicit_adapters_v1.py

tests/fixtures/dungeonmind_kernel/
  eldyrwild_relationship_residual_adjudication_v1.json

tests/fixtures/dungeonmind_kernel/
  eldyrwild_relationship_explicit_adapter_conformance_v1.json

graph_data/approved_graph_corrections/eldyrwild/
  lysandra-threat-direction-v1.json

apps/live_control_server/services/
  eldyrwild_lysandra_threat_direction_correction.py

graph_memory Kernel correction/replay implementation
```

Also preserve the adjudication anchor revision and its payload/source seals.

If this re-anchor requires changing conformance semantics to make the new fixture pass, that is evidence of a different slice.

Stop.

---

## §6 Fixture contract

Update the current effective-conformance fixture from the existing analyzer's exact output for R_current.

At minimum the fixture must bind:

```text
world_id
campaign_id

source_revision_id = R_current

source_graph_payload_sha256 = exact R_current payload digest

DungeonMind dependency ref
world-object vocabulary revision
world-object vocabulary digest

relationship_semantic_count
relationship_effectively_represented_count
relationship_effective_residual_count
uses_statblock_mechanics_count

base relationship represented/residual counts

continuity-derived representation fields

remaining_residual_edge_ids
remaining_residual_by_predicate
remaining_residual_disposition_inventory

DungeonMind-owned remaining count
DungeonMindBuddy-owned remaining count
unadjudicated count
requires-readjudication count
```

Do not manually preserve historical totals if the exact R_current analyzer says otherwise.

### Lysandra-specific fixture observations

The fixture/current report must demonstrate:

```text
X is not in remaining_residual_edge_ids

X′ does not appear as a new Buddy residual merely because it is new history

the corrected relationship is represented under existing vocabulary

the source-correction residual inventory reflects the actual current state
```

If R_current is exactly Q_live and there are no unrelated semantic changes between the historical/current baselines, a one-residual decrease attributable to Lysandra is a useful observation.

It is not the source of truth.

The exact generated R_current report is.

---

## §7 Historical authority preservation

The following are not "stale fixture data" to be refreshed:

```text
adjudication anchor:
  rev:3413bf6f5044cf2680233f5e37c90dcf

anchor payload:
  346c1fbfb3cbbf6d0e5ded1453fdd7760264a5106022e398d6074679799ab0fa

historical defective edge X

original target contribution/assertion

Session-8 source artifact

source span / locator

source artifact SHA

excerpt SHA

adjudication disposition and ownership history
```

Those records explain why the old assertion existed and why correction was justified.

The current effective fixture answers a different question:

```text
What relationships are current/effectively represented
on this exact descendant revision?
```

Do not collapse the two authorities.

---

## §8 Required tests

### 8.1 Exact current-fixture reproduction

Against a clone containing R_current:

```text
analyze_relationship_effective_conformance_v1(
  revision_id=R_current
)
```

must serialize to the checked-in effective fixture exactly, modulo any explicitly non-semantic formatting convention already used by the suite.

No implicit "current head" selection is acceptable in the fixture proof.

The revision must be explicit.

### 8.2 Proven ancestry

Prove:

```text
A → ... → Q_live → ... → R_current
```

with the existing ancestry/continuity authority.

Do not infer ancestry from timestamps or filenames.

### 8.3 Lysandra authority still active

On the exact R_current clone:

```text
C digest == locked digest

C replay-manifest state coherent

C mutable ledger state coherent

X target support is non-current/contradicted as expected

X′ is current

no unrelated active authority has silently replaced the intended meaning
```

Using the existing Lysandra status seam against the clone is preferred where it directly proves this contract.

Do not invoke canonical apply.

### 8.4 Historical continuity unchanged

Prove the original adjudication row for X remains source-grounded and durable historical authority.

The correction must not make continuity pretend X never existed.

### 8.5 Source/adjudication seal preservation

Fingerprint the owning adjudication/source-seal artifacts before fixture regeneration.

Require byte- or semantic-equivalence afterward according to the existing fixture contract.

### 8.6 Current relationship semantics

Require the generated R_current report to reflect current support:

```text
X not current residual

X′ current and represented

contradicted historical X not double-counted as current semantics
```

### 8.7 Replay

On an isolated clone:

```text
pinned rebuild to R_current
unpinned rebuild to R_current
```

must reconstruct equivalent durable graph state under existing replay rules.

This is not a correction PR, but a "current baseline" that cannot replay is not a trustworthy baseline.

### 8.8 No mutation

Tests must prove they do not alter canonical:

```text
world head
revision inventory
contribution ledger
replay manifest
support rows
```

No `--allow-live-world` mutation is authorized in this PR.

### 8.9 Existing regressions

Run the owning effective-conformance suite and the focused Lysandra correction suite.

At minimum:

```text
uv run pytest tests/test_dungeonmind_relationship_effective_conformance.py -q

uv run pytest tests/test_eldyrwild_lysandra_threat_direction_correction.py -q
```

Also run the narrow Kernel/rebuild/continuity suites already identified by repository ownership if cumulative diff or fixture changes exercise them.

Report exact test counts.

Do not substitute "tests pass" for the actual commands/results in the review handback.

---

## §9 Meaningful state sync owned by this PR

This PR may and should carry the small state sync made true by the live transition.

### Tracker

Update `PR-TRACKER-campaign-supergraph.md` so it no longer claims the integrity heal or Lysandra correction are pending.

The merged state should record:

```text
eldyrwild-contribution-integrity-heal
  DONE

eldyrwild-lysandra-threat-direction-correction
  DONE
  #537 merged + canonical P_live → Q_live exit proven

eldyrwild-effective-conformance-after-first-correction
  DONE
  exact R_current fixture/replay baseline established
```

Then make the next bounded Buddy residual-selection step dispatchable according to the tracker:

```text
buddy-remaining-relationship-correction-slices
```

Do not choose an omnibus repair.

The next specific correction still requires bounded selection/design by correction class.

### Current-state guide

Update `STATUS-world-graph-continuity-spine.md` to say, in plain terms:

```text
the generic correction primitive has now been used on real Eldyrwild

the Lysandra correction is live and replayable

historical X remains inspectable

current truth contains X′ through authored correction C

effective relationship conformance is now formally anchored
to exact R_current

the immutable adjudication anchor remains historical authority

remaining residual work must be selected by correction class
```

Record the actual R_current counts.

Do not carry the historical `346 / 294 / 52 / 2` forward as though it were the live baseline.

### Roadmap

Do not update the roadmap merely for status ceremony.

Touch it only if a specific current sequencing statement becomes materially false and the tracker/status sync cannot truthfully express the transition.

---

## §10 Nano-commit shape

Recommended implementation sequence:

### Commit 1 — capture exact live descendant baseline

No repo semantic changes yet.

Record in handback:

```text
implementation base
P_live
Q_live
R_current
ancestry proof
Lysandra already_applied proof
source/adjudication fingerprints
R_current rebuild proof
raw effective report
```

If this fails, stop before editing fixtures.

### Commit 2 — re-anchor current effective fixture + tests

Update:

```text
eldyrwild_relationship_effective_conformance_v1.json
test_dungeonmind_relationship_effective_conformance.py
```

Prove exact explicit-revision reproduction.

No analyzer changes.

### Commit 3 — state sync

Update only the small current tracker/status state justified by the now-proven baseline.

Do not perform general documentation cleanup.

---

## §11 Failure model

This PR must fail closed on these conditions.

### Missing predecessor completion

```text
#537 merged
but no canonical P_live → Q_live proof
```

Result:

```text
BLOCKED
```

### Q_live cannot be proven in current ancestry

Result:

```text
STOP
```

Do not silently baseline a different history.

### Correction authority is no longer current

If X′ is no longer current, C is invalid/incoherent, or X has unexpectedly become current again:

```text
STOP
```

This is new semantic state, not fixture maintenance.

### R_current cannot replay

```text
STOP
```

Do not create another rebuild waiver.

### Existing analyzer cannot describe R_current without semantic changes

```text
STOP AND RETURN TO DESIGN
```

Do not change the analyzer to make expected counts appear.

### Adjudication/source seal drift

```text
STOP
```

The successor does not own source-history repair.

### DungeonMind dependency changed

If the pinned dependency or vocabulary has changed since the Lysandra live proof:

```text
STOP
```

Determine whether this is actually a dependency re-pin/conformance slice.

Do not mix that work into this PR.

### Canonical tests require mutation

```text
STOP
```

Clone the store and use explicit revisions.

---

## §12 Explicit non-goals

Do not:

```text
apply another graph correction

re-apply Lysandra C

add a generic correction manager

modify correction lifecycle semantics

modify GraphContribution correction schema

change current-support rules

change relationship conformance interpretation

add a conformance exception for Lysandra

change explicit adapter rules

change DungeonMind vocabulary

re-pin DungeonMind

rewrite historical source prose

rewrite the adjudication anchor

rewrite source seals

delete historical X

batch-fix the remaining residual ledger

pick the next 34 source corrections automatically

change Graph Review UX

implement governed correction UX

cut DungeonMind over as product authority

migrate Play

perform general docs cleanup
```

This is one formal baseline transition.

---

## §13 Review standard

Review the cumulative branch, not only the final fixture diff.

### Required evidence

Before merge, reviewer must see:

```text
exact origin/main implementation base

#537 merge ancestor proven

canonical live-exit handback:
  P_live
  Q_live
  parent relationship
  already_applied retry
  no-churn proof

exact R_current

Q_live == R_current
OR
Q_live ancestor of R_current

C remains exact/current

X historical/non-current

X′ current

adjudication anchor unchanged

source seals unchanged

effective analyzer runtime code unchanged

DungeonMind pin unchanged

exact checked-in current fixture == analyzer(R_current)

R_current pinned rebuild equivalent

R_current unpinned rebuild equivalent

canonical World Graph untouched by tests

tracker/status sync limited to state actually made true
```

### Do not block over

```text
PR prose wording

incidental formatting

historical counts not matching live counts

tracker being stale before this meaningful sync

preference-level refactors not required by the invariant
```

### Do block over

```text
implicit latest-head fixture generation

unproven ancestry

replay failure

changed source/adjudication authority

changed conformance semantics

new adapter/ontology exception

wrong or ambiguous R_current

Lysandra correction not actually current

canonical graph mutation from tests

unrelated residual mutation hidden in fixture regeneration
```

---

## §14 Acceptance criteria

The PR is merge-ready when all of the following are true:

1. The completed Lysandra live exit names exact P_live and Q_live.
2. R_current is exact and explicitly pinned.
3. Q_live is R_current or a proven ancestor.
4. R_current still contains the exact governed Lysandra correction authority.
5. Historical X remains durable and inspectable but non-current.
6. X′ remains current.
7. Historical adjudication/source seals are unchanged.
8. Existing effective-conformance semantics generate the checked-in fixture exactly for R_current.
9. The fixture records actual R_current counts and residual identities rather than imposed historical counts.
10. R_current rebuilds equivalently pinned and unpinned.
11. No canonical graph write occurs in the PR.
12. No analyzer, adapter, vocabulary, correction, or Kernel semantic change is required.
13. Tracker/status reflect the now-completed integrity-heal → Lysandra → effective-baseline chain.
14. The next Buddy residual work is left as bounded selection by correction class, not a batch-zeroing implementation.

---

## §15 Definition of done

After merge, a fresh steward can answer all of these from repository authority:

```text
What is the historical adjudication anchor?
  exact A

What revision contains the first live governed correction?
  exact Q_live

What exact revision is the current formal effective-conformance baseline?
  exact R_current

Can R_current be reconstructed?
  yes, pinned and unpinned

Is the old Lysandra relationship still historical evidence?
  yes

Is it current semantic truth?
  no

What makes the corrected relationship current?
  exact authored correction C

Did the source/adjudication history change?
  no

What are the current relationship semantic /
represented / residual / mechanics counts?
  exact checked-in R_current values

What is next?
  choose one bounded Buddy-owned residual slice
  by adjudicated correction class
```

Only then is the first governed correction sequence operationally closed.

---

## §16 Handoff to the following design slice

Do not automatically dispatch "fix the rest."

Use the newly anchored R_current residual ledger to select one bounded successor.

Selection should preserve the existing correction-class distinction:

```text
SOURCE_CORRECTION_REQUIRED
COMPOUND_ASSERTION_NOT_SINGLE_RELATIONSHIP
IDENTITY_NOT_RELATIONSHIP
INSUFFICIENT_EVIDENCE
```

The next DESIGN task should inspect the actual R_current residual inventory and choose the smallest independently useful slice with one authority model.

A likely next source-correction PR is acceptable only if:

```text
one exact adjudicated defect is selected

existing #534 correction machinery is sufficient

source/evidence identity is exact

the expected current-conformance delta is stated

unrelated support is provably preserved

replay is non-waivable
```

Do not generalize merely because the first correction worked.

---

## §17 One-sentence invariant

> Re-anchor effective conformance to the exact replayable live descendant produced by the first governed correction, while leaving historical adjudication, source evidence, correction semantics, and graph authority untouched.
</user_query>
