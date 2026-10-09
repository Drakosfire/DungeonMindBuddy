import { WorldPlanCardProjection, buildWorldPlanCardProjectionModel, worldPlanCardTargetKeys } from "../planSurface/components/WorldPlanCardProjection";
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
const selectableTargetKeys = worldPlanCardTargetKeys(model);

export const NarrowPlanFocus = () => (
  <main style={{ width: 320, maxWidth: "100%", marginInline: "auto", background: "#101319", minHeight: "100vh" }}>
    <WorldPlanCardProjection worldId="fixture-world" documentId="fixture-plan"
      document={planDoc} markdown={markdown} sourceWarnings={[]}
      basis={{ status: "verified", revision: 9, contentSha256: "a".repeat(64) }}
      isDirty={false} onReturnToDocument={() => {}} selectableTargetKeys={selectableTargetKeys}
      onSelectTarget={() => {}} />
  </main>
);
