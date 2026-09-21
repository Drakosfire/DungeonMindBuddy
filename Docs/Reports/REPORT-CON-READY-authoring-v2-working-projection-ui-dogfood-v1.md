# CON-READY: Authoring v2 working-projection UI dogfood report

**Date:** 2026-09-20  
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / campaign memory authoring`  
**Implementation branch:** `con-ready/authoring-v2-working-projection-ui-dogfood-v1`  
**Related handoff:** [`HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md`](../Plans/HANDOFF-CON-READY-authoring-v2-working-projection-ui-dogfood-v1.md)

## Executive summary

This dogfood pass validated the direction of a published recap as a continuous working surface: the GM can keep reading the recap, open Author Node beside it, make a local identity/object/relationship decision, and immediately see that decision represented in the working projection without mutating canonical recap or World memory.

The largest lesson was that the hard part is not adding more authoring controls. It is giving each decision a clear place, sequence, and scope. The workflow became substantially easier to understand when the existing-node path, new-object path, relationship path, working projection, and final local review were separated into explicit states.

This is meaningful progress, but it is not a finished information architecture. The next iteration should reduce the remaining surface vocabulary and make duplicate resolution and search feel like first-class reusable tools.

## What the dogfood validated

### 1. Published recap and Author Node belong beside each other

The recap must remain visible while the GM works. A right-anchored Author Node drawer is a good starting composition because it keeps the source and the local decision in the same visual frame.

The drawer needs to be:

- internally scrollable;
- expandable without losing the source;
- anchored on the side it emerges from;
- closable without losing campaign/session-local staged state;
- sized for a useful initial view without taking over the entire recap.

The earlier full-page authoring presentation created context loss and made the working projection feel like a competing page. The drawer composition corrected that.

### 2. Working projection is valuable, but should not be the default authoring view

The working projection helped confirm that local adjudications are visible and useful, but showing it expanded by default made the Author Node opening state feel heavy. The better default is:

```text
published recap remains primary
→ Author Node opens with the relevant decision
→ working projection is available as a compact preview
→ preview expands when the GM needs to inspect local effects
```

The preview should float above or remain attached to Author Node while authoring so the GM does not have to choose between inspecting the local result and continuing the decision.

The projection remains a local overlay:

- canonical recap Markdown is unchanged;
- World memory is unchanged;
- campaign/session scope is preserved;
- closing and reopening the drawer retains the staged local state.

### 3. One long form is the wrong mental model

The original all-in-one authoring surface exposed too many choices at once and repeated instructions. A linear wizard is a better starting model because it gives the GM one decision at a time and makes backtracking possible.

The useful sequence is:

1. Resolve the recap phrase.
2. Add object details when a new local object is needed.
3. Optionally add a relationship.
4. Review the local draft.

The wizard header should stay compact. The step circles are status markers, not a second navigation system; the current step title and hover descriptions carry the explanation. Step 4 is the terminal review state for local staging, not a partially implemented path to a hidden Step 5. Any future publish/commit action should be a separately governed flow rather than an implied continuation of this local-only wizard.

### 4. Existing identity and new object are different authoring modes

Putting “Create a new object” above an existing-object identity decision made the surface look incoherent. The context-tab model is clearer:

- `New object` is an explicit creation context;
- the currently referenced node is its own context;
- additional selected relationship-chain nodes can become additional contexts.

This keeps new-object authoring available without making it appear to be the default answer for an existing node. It also gives the GM a stable place to return to when exploring a chain of related objects.

### 5. Identity vocabulary must follow the decision being made

The phrase “Identity check” was too abstract, and repeating “Use existing node” did not explain why a choice was recommended. The useful hierarchy is:

```text
high-confidence duplicate suggestion
→ clear sentence explaining the likely identity
→ important object details
→ one primary action
→ less likely alternatives behind “See all matches”
```

For example, a useful recommendation is closer to:

> Caelynn is probably the player character who is a member of the party.

This is easier to parse than a repeated button label and gives the GM a reason to accept the recommendation.

The distinction between identity and alias is also important:

- exact primary-label match: link/reference the existing node;
- different phrase resolving to a known node: add the phrase as an alias;
- no appropriate match: create a new local object;
- multiple same-name nodes: show ambiguity rather than silently choosing one.

The existing-node card does not need a redundant “Staged Reference” label when the object identity and local staging state are already clear from the surrounding context.

### 6. Search must work for both a few objects and hundreds of objects

The target-object control is useful only when it supports both fast narrowing and deliberate browsing. Fuzzy typed matching worked well for finding an object such as Questionable Company, but a large unbounded list was visually distant from its field and awkward to use.

The better reusable search pattern is:

- context-filtered fuzzy search by default;
- an explicit `See all`/`All` affordance for browsing the complete scoped set;
- results anchored directly to the field;
- a scrollable result region with a bounded height;
- enough type/context metadata to distinguish duplicate labels.

This should become standardized search tooling that can be reused by source, target, and identity controls rather than a one-off dropdown for this form.

### 7. Graph reference interaction should be deliberate

Hover-driven graph-node previews caused flashing and accidental orientation/open/close behavior while the GM was trying to highlight text such as StoneBridge or merchant guards. In authoring mode, first click is the safer interaction:

```text
hover → visual affordance only
first click → select/open the node context
keyboard focus → remains accessible
```

Ordinary browse previews can retain hover behavior where it is useful, but authoring mode should not compete with text selection.

This is retained as successor evidence rather than folded into this PR after review: the behavior crosses the current graph-reference and TipTap ownership boundary. The finding is still important, but it should land as a separately scoped interaction slice with its own regression coverage.

### 8. Duplicate evidence deserves a stronger moment in the flow

Karsemine demonstrated that the duplicate signal can be confident enough to lead with a suggestion rather than burying it in a long list. The suggestion should be prominent, concise, and actionable, while the full candidate set stays available behind an explicit reveal.

The current local duplicate warning is useful evidence, but duplicate handling will likely deserve its own focused walkthrough or confirmation surface in a later slice. That surface must remain recommendation-first and must not silently merge objects.

## Design principles to carry forward

1. Keep source, decision, and local result visible in the same working frame.
2. Separate presentation state from write authority; local staging is not World publication.
3. Give every control one obvious job and one obvious home.
4. Prefer adaptive sentences that explain the current decision over repeated generic instructions.
5. Hide breadth behind deliberate reveal controls when the common case is narrow.
6. Preserve root context when inspecting related objects; expansion should not feel like navigation away.
7. Make the end of a local workflow explicit instead of implying an unavailable next step.
8. Use exact graph identity and scope metadata to explain ambiguity rather than guessing.

## Remaining information-architecture questions

These are follow-up design questions, not reasons to reopen the current local-staging boundary:

- The separate `Tools` tab and `Author Tools` surface still imply an incoherent hierarchy. We need one clear taxonomy for browsing, authoring, inspection, and future publication.
- The wizard still has more explanatory copy than the final surface should carry. Step descriptions should become compact adaptive guidance or hover help after the decision model stabilizes.
- The duplicate suggestion should become a more explicit, confidence-aware mini-flow without turning into automatic merge behavior.
- Search, identity resolution, and relationship target selection should share one standardized interaction component.
- Working-projection effects should remain visible without making the projection the default opening state.
- The final local review state may eventually need a clearer “done” action, but that action should close or hand off the local workflow; it should not imply World commit.

## What this slice deliberately did not solve

This pass does not add:

- governed World publication;
- prepare/commit calls;
- automatic duplicate merge or reconciliation;
- canonical recap mutation;
- generated narrative prose;
- an Agent authoring path;
- a replacement for the existing exact-run authoring authority model.

Those boundaries are important: the dogfood proved the interaction model can become useful before we grant it durable write authority.

## Evidence and next step

The implementation was exercised against Campaign 1 and Campaign 2 recap flows, including selected existing nodes, new local objects, relationships, fuzzy target search, duplicate suggestions, close/reopen persistence, working-projection preview, and the terminal review state. Focused UI tests, TypeScript checking, and the production build pass.

The next design/code pass should focus on information architecture and reusable decision controls, especially the Tools/Author Tools hierarchy, adaptive wizard copy, duplicate walkthrough, and standardized scoped fuzzy search. It should continue to preserve the current invariant: the GM remains oriented to the same source and working projection while local adjudications stay local and reversible.

## Process follow-up

This slice also exercised the branch-first handoff model in practice: the active branch was created from the current integration head, the implementation was reviewed at its exact branch head, and the PR carried the handoff plus its state-authority updates. Current repository law still describes a steward-landed-on-`main` handoff before branch allocation. No process-law change is bundled into this product PR; before the next slice, the steward should explicitly decide whether branch-first becomes the authoritative model and update the Steward/Code-agent process documents atomically if so.
