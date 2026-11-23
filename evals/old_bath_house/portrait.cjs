'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function bindSavedPortrait(page, fixture, selectSavedImage) {
  const { origin, worldId, boss } = fixture;
  assert.match(origin, /^http:\/\/127\.0\.0\.1:[0-9]+$/);
  const target = new URL('/statblock', origin);
  for (const [key, value] of Object.entries({
    world: worldId, conversation: boss.conversationId, turn: boss.turnId, variantReview: boss.reviewId,
  })) target.searchParams.set(key, value);

  await page.goto(target.href);
  await page.getByRole('button', { name: 'Generate or choose portrait', exact: true }).click();
  await selectSavedImage(page, boss);
  const endpoint = new URL(
    `/api/live/agent/worlds/${encodeURIComponent(worldId)}/conversations/${encodeURIComponent(boss.conversationId)}/drafts/${encodeURIComponent(boss.turnId)}/variant-reviews/${encodeURIComponent(boss.reviewId)}/saved/portrait`,
    origin,
  );
  const save = page.waitForResponse(response =>
    response.url() === endpoint.href && response.request().method() === 'POST');
  const started = performance.now();
  await page.getByRole('button', { name: 'Save new portrait version', exact: true }).click();
  const response = await save;
  assert.ok(response.ok(), `Portrait binding failed with HTTP ${response.status()}`);
  const command = response.request().postDataJSON();
  const locator = await response.json();
  assert.deepEqual(command.base, boss.baseLocator);
  assert.equal(command.portrait_asset_id, boss.assetId);
  assert.equal(locator.statblock_id, boss.baseLocator.statblock_id);
  assert.equal(locator.definition_digest, boss.baseLocator.definition_digest);
  assert.notEqual(locator.revision_id, boss.baseLocator.revision_id);
  target.searchParams.set('variantPortrait', command.operation_id);
  await page.waitForURL(target.href);
  const portrait = page.getByRole('img', { name: `Portrait of ${boss.name}`, exact: true });
  const src = await portrait.evaluate(async image => {
    await image.decode();
    return image.currentSrc;
  });
  assert.equal(src, boss.imageUrl);
  return { url: target.href, locator, operationId: command.operation_id, elapsedMs: performance.now() - started };
}

async function chooseLibraryPortrait(page, boss) {
  await page.getByRole('button', { name: 'Image library', exact: true }).click();
  await page.getByRole('button', { name: boss.libraryLabel, exact: true }).click();
  await page.getByRole('button', { name: 'Use as portrait', exact: true }).click();
}

module.exports = { bindSavedPortrait, chooseLibraryPortrait };
