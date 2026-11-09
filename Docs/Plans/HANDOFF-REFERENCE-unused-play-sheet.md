# REFERENCE: retire the unused Play reference sheet

Status: SOURCE SETTLED. PR2312 merged as
4cf63addb3925f1f9dec775f8fba843c287de566 from independently reviewed
93f8f2ac3319d969b08c1ba432b167f8c1d4a3bb. Exact-head local frontend/build and
nine CI guards passed; discovered7435/164 removes exactly ten passing cases from
qualified parent7445/164 with no new/changed failures. Full diagnostic stays red.
Source write lease released. Runtime activation remains held. Historical
allocation follows.
Status at allocation: ACTIVE source retirement. PRIME owns this serial slice from verified
remote main 7ec9bcec9beed23c71f911943062bfc9c94bda51, branch
codex/reference-retire-unused-play-sheet, existing buddy-context-loop checkout.
No unmerged parent, runtime lease, provider call or database operation. The
operator recovery hold and coordination-off instruction remain binding.

## Outcome and invariant critique

Remove the unmounted PlayGraphObjectSheet and its private
PlayThreatMechanicsSection wrapper. Exact symbol and import-path searches find
no production caller outside these two files. The historical P3C handoff records
that they were early composition wrappers, not a mounted native Play workflow.
Current native reference selection and preview remain with
SurfaceGraphReferenceInput, NativeGraphObjectPreview and SavedStatblockSession.
This removal does not claim to implement historical Runbook occurrence derivation
or Add to Combat, nor to finish current Play runtime delivery.

Retain the shared useExactThreatMechanics, ThreatMechanicsPanel, threat view-model,
ResolvedGraphObjectProjection and ThreatSheetProjection owners and their tests.
The shared host, Plan resolver/card and independently gated Plan diagnostic stay
unchanged. A wrapper with no mounted caller is not evidence that its historical
capability was delivered; retain accurate unavailable behavior in current owners.

## Exclusive expected writes and topology

Delete only these four files under apps/live-control-ui/src:
- playSurface/reference/PlayGraphObjectSheet.tsx and .test.tsx
- playSurface/reference/PlayThreatMechanicsSection.tsx and .test.tsx

Remove exactly their two test classifications in ci/test-classification.json.
HANDOFF-PLAY-shared-native-retrieval.md grants this atomic retirement partition;
CI PR2288 head657def68f68bfffca839c92549146c8ded1044e0 retains additive CI
ownership. Neither test is named in ci/contracts.json or the frozen original
command fixture. Preserve those files and their guard unchanged. No replacement
retirement registry, test shim or alternate execution path is introduced.

This handoff and HANDOFF-REFERENCE-adoption-inventory.md record the caller decision.
Settle only the source status/lease of predecessor
HANDOFF-REFERENCE-unused-opening-helpers.md (merged2310) and
HANDOFF-REFERENCE-object-diagnostic-retirement.md (merged2311). Those backward-looking
facts are now known; they do not pre-mark this slice or runtime delivery complete.
Also settle only the source status/lease of HANDOFF-CI-encounter-observation-wait.md
after prerequisite2314 merged. Also settle the source status/lease of
HANDOFF-MEDIA-image-context-first-open.md after prerequisite2315 merged.
All other source, state and authority are outside
this lease. Delivery is serial.
Open runtime/storage/CI/Surface PRs were inspected before allocation; no component
path overlaps their active work. Held server PR2104 remains untouched.

## Verification and delivery

The retained pre-integration discovered baseline at reviewed875ab18a1 contains ten passing cases
for the two exclusive test subjects (seven sheet, three mechanics wrapper).
First verify source-tree equivalence and raw baseline hashes. After deletion,
check all remaining import/export/symbol and private CSS references, the exact
classification delta and cumulative diff. Run the nine CI command/inventory
guards and exact-head local hosted frontend/build verifier, then validate its
immutable evidence. Run the discovered suite at the integrated checkpoint and
account for exactly those ten retired cases. Keep inherited failures visibly red;
new or changed failures need diagnosis rather than deletion or suppression.
Obtain independent exact-head Bugbot review, push/open the owning PR and merge
under standing PRIME authority only when the source gates pass. Runtime activation
and controlled browser verification remain pending the operator recovery hold;
source merge is not delivery to5202 or completion of the full goal.

## Integrated source checkpoint

The initial retirement head6e49c0964727babe19da0b050b931dcfa935abc5 passed
independent source review, nine CI guards, exact-head hosted sample and build.
While its discovered run completed, Surface PR2276 merged as
a22b77a406c6575eea7cc073139fb0774191cf50. Its seven changed paths do not overlap
this lease. Re-anchor this same slice on that exact merged source and repeat
exact-head qualification and independent review; retain the original run as
pre-integration evidence. Do not claim its UI tree equals the new parent tree.
Compare the retirement against the pre-integration run and inspect the Surface
case delta separately; any unexplained new failure remains a gate.

## Qualified prerequisite settlement

PR2314 merged as e2d75649b577f679af8f05e24329e4cb3f6121a6 from independently
reviewed a2b68f743eab66795641c87ba52b14db8b3b41ab. It awaits the existing exact
encounter acknowledgement assertion without changing expected proof or timeout.
Its exact-head hosted/build evidence validates. Full discovered7443/164 matches
parenta22b77a with no new/changed failure causes or case loss; the suite stays red.
Re-anchor this retirement on that merged source and verify its own exact head.
The original933f440c full-suite165-failure report and all failed/refused/focused
comparisons remain retained; the timing failure was not silently waived as inherited.

## Image-menu prerequisite settlement

The ce59f851d retirement diagnostic preserved a separate missing-Instructions
failure. A focused trace reproduced open-before-mount-reset on the same image
component. MEDIA PR2315 separately fixed that owner with a layout-phase reset;
its deterministic regression fails on the original code and passes after repair.
It merged as7ec9bcec9beed23c71f911943062bfc9c94bda51 from independently reviewed
7f64c98f5a9dc06b6bbf50128ed82e3aabfc71ab. Hosted/build evidence validates and
full7445/164 adds only its two passing cases with no new/shared-cause changes.
No original failure was waived. Re-anchor this retirement and qualify its own
head on that source; all runtime holds remain. Original retirement failure heads
are pinned under refs/codex/retained/reference-play-sheet-* as Git evidence.
