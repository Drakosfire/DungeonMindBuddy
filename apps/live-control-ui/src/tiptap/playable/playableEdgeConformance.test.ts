import fixtureData from "../../../../../tests/fixtures/playable_edge_conformance.json";
import { describe, expect, it } from "vitest";

import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { indexPlayableStructure, indexPlayableStructureV2 } from "./playableStructureIndex";
import { validatePlayableOptionItemAttrs } from "./playableElementIdentity";

// Python consumes this same checked-in synthetic fixture. It sorts v2 membership;
// document order remains a property of these exact source bytes and the UI index.
const { cases } = fixtureData;

function projection(markdown: string, grammar: number) {
  const imported = markdownToTiptapDoc(markdown);
  const result = grammar === 1 ? indexPlayableStructure(imported.doc) : indexPlayableStructureV2(imported.doc);
  return { imported, result };
}

function membership(result: ReturnType<typeof indexPlayableStructure> | ReturnType<typeof indexPlayableStructureV2>, grammar: number) {
  if (result.status !== "ready") throw new Error("expected ready structure");
  if (grammar === 1) {
    const index = (result as Extract<ReturnType<typeof indexPlayableStructure>, { status: "ready" }>).index;
    return index.elements.map((element) => ({ kind: element.kind, element_id: element.id,
      scene_id: "sceneId" in element ? element.sceneId : null,
      choice_id: "choiceId" in element ? element.choiceId : null }));
  }
  const index = (result as Extract<ReturnType<typeof indexPlayableStructureV2>, { status: "ready" }>).index;
  const sortBy = <T,>(items: T[], key: (item: T) => string) => [...items].sort((a, b) => key(a).localeCompare(key(b)));
  return {
    beats: sortBy(index.beats.map((b) => ({ beat_id: b.beatId, beat_kind: b.beatKind })), (b) => b.beat_id),
    scenes: sortBy(index.scenes.map((s) => ({ scene_id: s.sceneId, beat_id: s.beatId })), (s) => s.scene_id),
    choices: sortBy(index.choices.map((c) => ({ choice_id: c.choiceId, beat_id: c.beatId, scene_id: c.sceneId })), (c) => c.choice_id),
    options: sortBy(index.options.map((o) => ({ option_id: o.optionId, choice_id: o.choiceId })), (o) => o.option_id),
    edges: sortBy(index.options.flatMap((o) => (["activate", "suppress"] as const).flatMap((effect) =>
      (effect === "activate" ? o.activates : o.suppresses).map((target) => ({
        option_id: o.optionId, effect, target_kind: target.split(":")[0], target_id: target,
      })))), (e) => `${e.option_id}|${e.effect}|${e.target_id}`),
  };
}

describe("shared source effect target conformance", () => {
  for (const fixture of cases) {
    it(fixture.name, () => {
      const { imported, result } = projection(fixture.markdown, fixture.grammar);
      if (!fixture.valid) {
        // The owning index must reject these source identities; prose remains editable.
        expect(result.status).toBe("blocked");
        return;
      }
      expect(imported.diagnostics).toEqual([]);
      expect(membership(result, fixture.grammar)).toEqual(fixture.expected);
      if (result.status !== "ready") throw new Error("expected ready");
      expect(result.index.elements.map((e) => e.id)).toEqual(fixture.order);
      expect(result.index.elements.map((e) => e.order)).toEqual(fixture.order!.map((_, i) => i));
      const serialized = tiptapJsonToSemanticMarkdown(imported.doc);
      expect(serialized).toBe(fixture.markdown);
      const reopened = projection(serialized, fixture.grammar);
      expect(reopened.imported.diagnostics).toEqual([]);
      expect(reopened.result).toEqual(result);
      expect(membership(reopened.result, fixture.grammar)).toEqual(fixture.expected);
    });
  }

  it.each(["playableActivates", "playableSuppresses"])("rejects duplicate %s on direct editor attrs", (field) => {
    expect(validatePlayableOptionItemAttrs({ playableElementKind: "option", playableElementVersion: "v2",
      playableElementId: "option:go", [field]: ["beat:later", "beat:later"] })).toMatchObject({ status: "invalid" });
  });
});
