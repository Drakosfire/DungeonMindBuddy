import { SceneCard } from "./SceneCard";
import "../playSurface/playSurface.css";
import { WorldPlanCardProjection, buildWorldPlanCardProjectionModel } from "../planSurface/components/WorldPlanCardProjection";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import "../ui/tokens.css";
import "../planSurface/components/WorldPlanCardProjection.css";

const longTitle = `The ${"very long winding corridor ".repeat(8)}of Sheep`;
const markdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:sheep beat_kind=spine -->",
  "## Gather the flock",
  "The shepherd asks the party to cross before dark.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:sheep-gate -->",
  `### ${longTitle}`,
  "A narrow gate opens toward the hillside. The flock waits beyond it.",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:sheep-route scene=scene:sheep-gate -->",
  "### Which route will the party take?",
  "The path is steep and the road is exposed.",
  "<!-- dmb-playable-element:v2 kind=option id=option:hill -->",
  "- Climb the hill",
  "",
  "  Reach the high pasture before sunset.",
  "<!-- dmb-playable-element:v2 kind=option id=option:road -->",
  "- Follow the road",
  "",
  "  Keep the flock together by the wall.",
].join("\n") + "\n";
const planDoc = markdownToTiptapDoc(markdown).doc;
const model = buildWorldPlanCardProjectionModel({ document: planDoc, markdown, sourceWarnings: [] });
if (model.status !== "ready") throw new Error("Plan Scene card fixture must be ready.");

export const NarrowPlanFocus = () => (
  <main style={{ width: 320, maxWidth: "100%", marginInline: "auto", background: "#101319", minHeight: "100vh" }}>
    <WorldPlanCardProjection worldId="fixture-world" documentId="fixture-plan"
      document={planDoc} markdown={markdown} sourceWarnings={[]}
      basis={{ status: "verified", revision: 9, contentSha256: "a".repeat(64) }}
      isDirty={false} sceneId="scene:sheep-gate" onReturnToDocument={() => {}} />
  </main>
);

const encounterMarkdown = [
  "## Encounter reference",
  "### Visible terrain",
  "#### Creature abilities",
  "| STR | DEX | CON | INT | WIS | CHA |",
  "| --- | --- | --- | --- | --- | --- |",
  "| 14 (+2) | 16 (+3) | 20 (+5) | 14 (+2) | 16 (+3) | 20 (+5) |",
  "##### Counterplay",
  "| d20 | Effect |",
  "| --- | --- |",
  "| 1 | A visibly marked section of the street rises next round. Move clear or disable its supporting conduit. |",
  `| 20 | ${"UnbrokenReference".repeat(12)} |`,
  "###### Timing",
  "Announce the effect before resolving it. Original authored text remains visible.",
].join("\n");
const encounterBody = markdownToTiptapDoc(encounterMarkdown).doc.content;

export const PlaySceneReadability = () => (
  <main className="play-surface" style={{ maxWidth: 960, marginInline: "auto" }}>
    <h3>Play shell heading</h3>
    <section className="play-cockpit-center">
      <SceneCard variant="play-current" kicker="Current scene"
        identity={{ worldId: "fixture-world", documentId: "fixture-plan", sceneId: "scene:encounter",
          revision: 4, contentSha256: "b".repeat(64), sourceState: "run-pin" }}
        scene={{ id: "scene:encounter", title: "Encounter at the causeway",
          bodyText: encounterMarkdown, bodyContent: encounterBody }} choices={[]} />
    </section>
  </main>
);
