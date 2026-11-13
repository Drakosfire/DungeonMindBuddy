import {
  associateWorldMechanics, confirmNativeThreat, getNativeThreat, listWorldCreatures,
  listWorldMechanicsAssociations, prepareNativeThreat,
} from "../api/liveApi";
import type { SavedMechanicsLocator } from "../api/worldMechanicsTypes";

export async function publishPdfStatblock(
  world: string, draft: string, version: number, locator: SavedMechanicsLocator,
) {
  const result = await getNativeThreat(draft, world)
    ?? await prepareNativeThreat(draft, world, version, undefined, locator);
  if (result.state === "prepared") {
    const preparedLocator = result.review.mechanics_locator;
    if (!preparedLocator || Object.entries(locator).some(
      ([key, value]) => preparedLocator[key as keyof SavedMechanicsLocator] !== value,
    )) {
      throw new Error("The prepared creature uses a different saved statblock revision.");
    }
  }
  const creature = result.state === "published" ? result : await confirmNativeThreat(result);
  const associations = await listWorldMechanicsAssociations(world);
  const previous = associations.find(({request}) => request.target.node_id === creature.node_id
    && request.target.campaign_scope === null);
  if (previous) {
    const saved = previous.proof.locator;
    if (previous.request.draft_id !== draft ||
        Object.entries(locator).some(([key, value]) => saved[key as keyof SavedMechanicsLocator] !== value)) {
      throw new Error("This creature already has different saved mechanics.");
    }
    return creature;
  }
  const catalog = await listWorldCreatures(world);
  const target = catalog.targets.find(item => item.node_id === creature.node_id && item.campaign_scope === null
    && item.native_world_id === creature.native_world_id && item.binding_version === creature.binding_version);
  if (!target) throw new Error("Creature created. Retry Publish when the Graph makes it available for association.");
  await associateWorldMechanics(world, {
    request_id: crypto.randomUUID(), draft_id: draft, expected_draft_version: version,
    target, expected_version: 0, locator,
  });
  return creature;
}
