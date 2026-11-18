import { expect, it, vi } from "vitest";
import * as api from "../api/liveApi";
import type { SavedMechanicsLocator, WorldCreatureCatalog } from "../api/worldMechanicsTypes";
import { publishPdfStatblock } from "./publishPdfStatblock";

vi.mock("../api/liveApi", () => ({
  associateWorldMechanics: vi.fn(), confirmNativeThreat: vi.fn(),
  getNativeThreat: vi.fn(), listWorldCreatures: vi.fn(),
  listWorldMechanicsAssociations: vi.fn(), prepareNativeThreat: vi.fn(),
}));

it("resumes association without creating a second creature after interruption", async () => {
  const creature = {
    state: "published" as const, world_id: "world", draft_id: "draft",
    native_world_id: "space", binding_version: 1, node_id: "ent:tree",
    publication_id: "publication", published_revision_id: "rev:created", replayed: false,
  };
  const target = {
    managed_world_id: "world", native_world_id: "space", binding_version: 1,
    node_id: "ent:tree", graph_revision_id: "rev:current", label: "Tree",
    kind: "creature", role: "", campaign_scope: null,
  };
  const locator: SavedMechanicsLocator = {
    provider: "dungeonmind", statblock_id: "sb_tree", revision_id: "rev_tree",
    contract: "dungeonmind.dungeonbuddy-statblocks", contract_version: "1.0.0",
    definition_digest: "sha256:" + "a".repeat(64),
  };
  vi.mocked(api.getNativeThreat).mockResolvedValueOnce(null).mockResolvedValue(creature);
  vi.mocked(api.prepareNativeThreat).mockResolvedValue(creature);
  vi.mocked(api.listWorldMechanicsAssociations).mockResolvedValue([]);
  vi.mocked(api.listWorldCreatures).mockResolvedValue({ targets: [target] } as WorldCreatureCatalog);
  vi.mocked(api.associateWorldMechanics).mockRejectedValueOnce(new Error("interrupted"));
  await expect(publishPdfStatblock("world", "draft", 2, locator)).rejects.toThrow("interrupted");
  await expect(publishPdfStatblock("world", "draft", 2, locator)).resolves.toEqual(creature);
  expect(api.prepareNativeThreat).toHaveBeenCalledOnce();
  expect(api.associateWorldMechanics).toHaveBeenLastCalledWith("world", expect.objectContaining({
    draft_id: "draft", target, expected_version: 0, locator,
  }));
});
