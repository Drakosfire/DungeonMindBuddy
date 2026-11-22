# ONBOARD: show recorded creature classifications in the graph

Status: ACTIVE. The owner's onboarding goal authorizes implementation, Bugbot
review, merge and deployment. This serial slice follows merged #4467 and the
serving-line #4471. Base `f9214ad9268dd1baceb586948066056fac7f9af5`, branch
`codex/onboard-creature-label`; no live runtime, database or ports are leased.

The real signed-in Sizzek World recorded Izmati as `dnd5e:creature`, but the
read-only graph renders “object (unsupported classification)” because its
presentation map does not recognize that term. Render the exact known term as
“creature”; do not infer other classifications, change saved graph data, or
relax the fallback for unknown or mixed terms. Write set: this handoff,
`apps/live-control-ui/src/nativeGraphDemo/nativeGraphPresentation.ts` and its
existing presentation tests in `nativeGraphDemoApi.test.ts`. No other paths are
leased. Verify the exact classification, unknown and mixed fallback at the
presentation boundary, run exact-head hosted frontend verification and the
full discovered diagnostic against its base, and obtain independent Bugbot
review. Release integration/deployment must preserve the actual serving lineage
and remain separately verified. No guest publication is authorized here.
