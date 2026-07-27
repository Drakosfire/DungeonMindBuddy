/**
 * Preloaded Build canvas starter — Mireward Reach lore draft.
 * Shows the shared markdown stack (headings, emphasis, callouts, reference chips).
 * Not durable canon; edit freely when writing real worldbuilding.
 */
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";

export const BUILD_WORLDBUILDING_STARTER_TITLE = "Mireward Reach";

export const BUILD_WORLDBUILDING_STARTER_MARKDOWN = `# Mireward Reach

[Mireward Reach](#dmb-ref:location:mireward-reach) is the last true town before the Fen begins to swallow roads, voices, and certainty.

## A town at the crossing

It grew where the east–west trade road crossed the old north route — a place of ferries, tithe barns, repair sheds, caravan yards, and stubborn people who preferred open sky to [Mirathorn](#dmb-ref:location:mirathorn)’s towers.

Retired soldiers settled beside tanners, charcoal burners, machinists, drovers, and families who wanted distance from city hierarchy without giving up civilization. The result is a town that distrusts pomp but respects usefulness:

- a working bell
- a sound wall
- a full granary
- a neighbor who shows up

Titles matter less than any of those.

## How Mireward sees itself

> [!READ-ALOUD]
> Mireward likes to think of itself as freer, tougher, and more honest than Mirathorn. Its people say the road tells you who is coming, the Fen tells you why, and the wall tells you whether you listened soon enough.

## When the old song woke up

For generations, danger from the north had become an old song rather than a living memory. The palisade still stood. Patrols still rode. The town’s warnings became ritual.

Then refugees began filling haylofts and tithe barns, carrying stories of:

- wrong music
- glassy eyes
- people walking back into the swamp after death should have stopped them

## Now

Mireward is discovering the difference between a town *built* for vigilance and a town that has actually been tested.

> [!GM-NOTE]
> Starter canvas for Build dogfood. Replace or rewrite freely — this is not committed canon until you Save and promote through review.
`;

export function buildWorldbuildingStarterContent() {
  return markdownToTiptapDoc(BUILD_WORLDBUILDING_STARTER_MARKDOWN).doc;
}
