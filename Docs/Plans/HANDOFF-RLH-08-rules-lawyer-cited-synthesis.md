# HANDOFF — RLH-08 Rules Lawyer cited synthesis

**Status:** DEFERRED DRAFT  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Authority:** `Drakosfire/DungeonOverMind/Docs/Plans/PLAN-rules-lawyer-graph-experiment.md`  
**Predecessor:** `RLH_07_RULES_LAWYER_TOOLHOST_ACCEPTED`  
**Primary question:** Can Buddy synthesize a useful Rules Lawyer answer from an already-bounded evidence packet without reverting to free-form model knowledge?  
**Product milestone:** first complete Rules Lawyer 2 experience

## Input boundary

Answer generation receives only:

- the user's question;
- the exact RLH-06 evidence packet;
- citation IDs/locators;
- minimal product/system instructions.

It does not receive unrestricted rulebook retrieval tools during synthesis and is not asked to use remembered rules knowledge.

Use the accepted GenerationEngine boundary for provider execution. Buddy owns prompt/product semantics.

## Output contract

Return structured synthesis:

```text
answer text
citations[] mapped to evidence IDs
support status
optional needs-more-evidence flag/reason
generation trace identity
```

Citations may reference only evidence IDs in the input packet.

Post-generation validation must reject or visibly degrade:

- citation to unknown evidence;
- answer with no support when support is required;
- provider failure;
- a packet marked insufficient unless the response clearly says evidence is insufficient.

Never silently produce a confident ruling after retrieval failure.

## UI

Extend RLH-07 with:

- concise answer;
- citation affordances;
- evidence still inspectable;
- explicit insufficient-evidence state.

Evidence remains first-class; prose does not replace it.

## Evaluation

Use a bounded fixture set and measure at minimum:

- answer supported;
- required evidence covered;
- citation fidelity;
- unsupported-claim failures.

## Suggested lease

Follow current post-E5 composition:

```text
apps/live_control_server/services/rules_lawyer_*
accepted GenerationEngine adapter seam
apps/live-control-ui/src/rulesLawyer/
focused backend/UI tests
```

## Do not

- use Jev to write prose;
- let the synthesis model initiate new retrieval;
- make graph reasoning a prerequisite;
- hide retrieval insufficiency;
- add a second provider integration beside GenerationEngine.

## Acceptance witness

Representative questions produce supported answers whose rendered citations open the exact evidence used to synthesize them.

Acceptance token:

```text
RLH_08_RULES_LAWYER_CITED_SYNTHESIS_ACCEPTED
```
