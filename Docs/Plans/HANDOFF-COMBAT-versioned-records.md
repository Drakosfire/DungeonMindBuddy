# COMBAT — represent manual encounters without rewriting v1

MERGED as #3995 at `087c293812e1699e0088062484df31367343b93a`; source lease
released to HANDOFF-COMBAT-manual-profile.md. Reviewed exact head
`7a8f8bcc0bbef8287deffbf3404a2048ca11cde7` has independent code/evidence acceptance:
100 pure contract cases,16 CI guards and all1,558 classified files pass in a clean
isolated exact-SHA checkout with locked dependencies. Source/raw-copy and explicit
anchor regressions fail before and pass after repair. Evidence is retained under
records-exact-7a8f8bcc0bbef8287deffbf3404a2048ca11cde7 in the task evidence root;
the managed verification checkout is confirmed archived. No persisted/UI/DB
activation or full-goal completion is claimed by this predecessor.

Original authority: under the operator's full Combat implementation/review/accepted-merge
authority. Serial successor to #3990, merged
`1e208b20ac64bcac7682b4f8ea7ea5919fc69e79`. Fetched base
`fe8cdcc1e3ca6f463b99b1635217f37c3c9f4dc3`; branch
`codex/combat-versioned-records`, existing isolated fc67 checkout. No unmerged
parent, one open implementation PR in this workstream.

Outcome: private manual encounter/draft/participant records with explicit ordered
turn state, World/source coherence, exact profile value validation and lossless
v1/v2 record dispatch. Round-free ordered state contains no fabricated round or
anchor; rounds-enabled state retains its explicit anchor by identity. No database,
HTTP, recovery or user-facing v2 activation occurs in this slice.

Exclusive writes: this handoff; predecessor HANDOFF-COMBAT-profile-validation.md
truthful settlement; new combat_encounters/manual_encounters.py and
tests/test_combat_manual_encounters.py; one added test path in the existing
combat-profile-validation contract and its classification entry. Existing v1 DTOs,
serializers and golden fixture, profile-validator behavior, repository, HTTP,
source producers, session initialization, migrations and UI remain read-only.
#3668's adoption/minimums paths do not overlap. Historical CI drafts do not own
these additive model tests or reactivate retired verification policy.

Critique/invariants: record versions dispatch only on explicit matching profile
and draft schemas, supporting the existing alias/name preimages without rewriting
them. Unknown/mixed/ambiguous versions refuse. Actor/group/side IDs and membership
references are coherent; source identity and exact snapshot belong to the record's
World. Associated snapshots retain their exact target identity, conversation
variants cannot invent one, and manual values remain separate from source.
Only in-action participants can be active; an existing out-of-action round anchor
can remain pinned. An active rounds-enabled turn requires an explicit existing
anchor; empty/paused state may have no active actor. Profile round capability and turn-state kind must agree. Profile
digest matches its immutable snapshot. Draft size uses an explicit canonical budget,
not a claim about PostgreSQL JSONB text storage. Reading/validating never heals,
changes participation, initializes a session, maps source stats, or rewrites v1.

Validation: pure model/dispatch tests with materially different synthetic stats,
empty/active/out-of-action rosters, invalid/foreign/duplicate references, source
integrity, profile mismatch, strict state/version rejection, canonical limits and
retained v1 API/template/request/digest round trips. Run the named contract and CI
guards in an isolated exact-SHA checkout with locked Python, external scratch and
independent code/evidence review. No browser or real-database claim for private
record validation. Full persisted create/prepare/materialize/edit/recover/save and
side/spotlight behavior remain required before goal completion.
World/source coherence here is structural validation, not principal authorization
or source admission. Activation must retain the owning access/adoption guards.

Historical migration sequencing in merged #3877's PR body: Play owns0161, and
Combat owns next serial revision20261118_0162 with parent20261117_0161, subject
to confirming the sole head before committing and rehearsing0160→0161→0162 on
disposable PostgreSQL. The human authorized PRIME coordination; its prerequisite
is now merged. This lane fast-forwarded from its initial5ec base over disjoint
changes to the base above. No migration, Play/auth write ownership, shared API/UI
restart or live encounter edit is granted in this private record slice.
The one-shot explanation of why coordination is needed was answered and handled;
do not repeat it absent new information. Task evidence/designs remain under
`/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

Initial working-tree diagnostics pass98 profile/record cases plus16 CI guards. They cover
all four exact-source origins, cross-World refusal, revalidation of tampered model
instances, independent copied actors, explicit turn/profile state, reference
coherence and unchanged v1 preimages. Exact-commit evidence and formal review are
still required. The next vertical implementation must consume the settled migration
sequence and prove persistence, access, recovery and preparation/run boundaries.

Preliminary review found shared nested source data when two actors received the
same raw snapshot dictionary. The new regression fails before the repair; raw
inputs now deep-copy before source validation, alongside model-instance dumping.
A second failing-before-repair test makes the active-round anchor invariant
explicit. Retain both initial failure logs; final repaired evidence/review is
required. Existing v1 source DTOs and their serialization remain unchanged.

The consuming manual-profile integration re-anchored after main merged the Build
saved-statblock compatibility fence as0162. Its active handoff now adopts0163,
parent0162, within the explicitly assigned Combat design authority after checking
published assignments/open PRs and notifying PRIME. Original planned0162 proof is
historical diagnostics only; final qualification must prove the new forward chain
on fresh disposable PostgreSQL. See HANDOFF-COMBAT-manual-profile.md.
