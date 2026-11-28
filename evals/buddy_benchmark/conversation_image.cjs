"use strict";

const assert = require("node:assert/strict");
const { performance } = require("node:perf_hooks");
const { generatePrivatePreview } = require("./image_studio.cjs");

async function generatePreparedConversationImage(page, origin, fixture, preparation) {
  assert.ok(preparation?.action_id && typeof preparation.prompt === "string",
    "Buddy did not return a bound image preparation");
  const description = preparation.prompt;
  for (const detail of [fixture.page_detail, fixture.conversation_detail]) {
    assert.ok(description.toLowerCase().includes(detail.toLowerCase()),
      "Buddy's prepared description omitted: " + detail);
  }

  const studio = page.getByRole("region", { name: "Create an image", exact: true });
  const prepared = page.getByRole("article", { name: "Prepared image", exact: true });
  await prepared.waitFor({ timeout: 20000 });
  const prompt = studio.getByRole("textbox", { name: /What would you like to see/ });
  if (!await prompt.isVisible()) {
    await prepared.getByRole("button", { name: "Open Image Studio", exact: true }).click();
  }
  await prompt.waitFor({ timeout: 20000 });
  const { asset, model, elapsedMs } = await generatePrivatePreview(page, origin, description, {
    preparationId: preparation.action_id,
  });

  const started = performance.now();
  const savedPath = "/api/live/media/images/" + encodeURIComponent(asset.asset_id) + "/save";
  const saved = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === savedPath && response.request().method() === "POST";
  }, { timeout: 60000 });
  saved.catch(() => {});
  await studio.getByRole("button", { name: "Save image", exact: true }).click();
  const response = await saved;
  assert.ok(response.ok(), "Saving generated image returned HTTP " + response.status());
  const receipt = await response.json();
  assert.equal(receipt.asset_id, asset.asset_id, "Save returned a different generated asset");
  assert.equal(receipt.state, "ready", "Generated asset was not ready after Save");
  const saveMs = performance.now() - started;
  await studio.getByRole("button", { name: "Close image studio", exact: true }).click();
  return { asset_id: asset.asset_id, preparation_id: preparation.action_id, model,
    generation_ms: elapsedMs, asset_save_ms: saveMs };
}

function verifyConversationImagePlacement(before, after, fixture, assetId) {
  const text = node => node.text ?? (node.content ?? []).map(text).join("");
  const indexes = before.content.flatMap((node, index) =>
    node.type === "paragraph" && text(node) === fixture.placement_anchor ? [index] : []);
  assert.equal(indexes.length, 1, "The opening page does not have one exact placement anchor");
  const index = indexes[0] + 1;
  assert.equal(text(before.content[index]), fixture.preserved_paragraph,
    "The fixture does not have the expected neighboring paragraph");
  const block = after.content[index];
  assert.equal(block?.content?.length, 1, "Expected one image block after the anchor");
  const image = block.content[0];
  assert.equal(image.type, "mediaImage", "The placed block does not contain an image");
  assert.equal(image.attrs?.assetId, assetId, "Buddy placed a different image");
  assert.deepEqual(after.content.filter((_, i) => i !== index), before.content,
    "Placement changed or added content beyond the requested image");
  return index;
}

module.exports = { generatePreparedConversationImage, verifyConversationImagePlacement };
