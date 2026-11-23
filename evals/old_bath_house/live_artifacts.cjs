'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function confirmVariant(page, fixture, evidence) {
  const find = page.getByRole('button', { name: 'Find reviewed statblock', exact: true });
  await find.click();
  const review = page.getByRole('region', { name: 'Statblock variant review', exact: true });
  const reviewError = page.getByRole('region', { name: 'Variant approval', exact: true }).getByRole('alert');
  await review.or(reviewError).waitFor();
  if (await reviewError.isVisible()) {
    throw new Error(`Buddy did not open a statblock variant review: ${await reviewError.innerText()}`);
  }
  const confirm = review.getByRole('button', { name: 'Confirm and save as new statblock', exact: true });
  await confirm.waitFor();
  const name = (await review.getByRole('heading', { level: 3 }).first().textContent()).trim();

  const started = performance.now();
  const [response] = await Promise.all([
    page.waitForResponse(result => {
      const url = new URL(result.url());
      return url.origin === fixture.origin && url.pathname.endsWith('/confirm')
        && url.pathname.includes('/variant-reviews/') && result.request().method() === 'POST';
    }),
    confirm.click(),
  ]);
  assert.ok(response.ok(), `Statblock confirmation failed with HTTP ${response.status()}`);
  const locator = await response.json();
  assert.match(locator.definition_digest, /^sha256:[a-f0-9]{64}$/);
  assert.ok(locator.statblock_id && locator.revision_id, 'Saved variant is missing its exact identity');
  assert.notEqual(locator.statblock_id, fixture.live.originalStatblockId);
  const open = review.getByRole('link', { name: 'Open saved variant', exact: true });
  await open.waitFor();
  evidence.evidence.variant_acceptance_ms = performance.now() - started;
  const url = new URL(await open.getAttribute('href'), fixture.origin);
  assert.equal(url.origin, fixture.origin);
  assert.equal(url.pathname, '/statblock');
  assert.equal(url.searchParams.get('world'), fixture.worldId);
  for (const key of ['conversation', 'turn', 'variantReview']) {
    assert.ok(url.searchParams.get(key), `Saved variant link is missing ${key}`);
  }
  return { url: url.href, locator, name };
}

async function generatePortrait(page, fixture, variant, evidence) {
  await page.goto(variant.url);
  await page.getByRole('button', { name: 'Generate or choose portrait', exact: true }).click();
  const studio = page.getByRole('region', { name: 'Create an image', exact: true });
  const expand = studio.getByRole('button', { name: 'Expand image studio', exact: true });
  if (await expand.isVisible()) await expand.click();
  const back = studio.getByRole('button', { name: 'Back to studio', exact: true });
  if (await back.isVisible()) await back.click();
  const prompt = studio.getByRole('textbox', { name: /What would you like to see/ });
  await prompt.fill(fixture.live.portraitPrompt);
  const generate = studio.getByRole('button', { name: 'Generate image', exact: true });
  const started = performance.now();
  const [response] = await Promise.all([
    page.waitForResponse(result => {
      const url = new URL(result.url());
      return url.origin === fixture.origin && url.pathname === '/api/live/media/images/generate'
        && result.request().method() === 'POST';
    }, { timeout: 185000 }),
    generate.click(),
  ]);
  assert.ok(response.ok(), `Portrait provider failed with HTTP ${response.status()}`);
  const result = await response.json();
  const [portrait] = result.images;
  assert.ok(portrait?.asset_id, 'Generated preview is missing its media identity');
  assert.equal(portrait.state, 'staged');
  assert.ok(!portrait.delivery_url, 'Generated preview unexpectedly has public delivery');
  const image = studio.getByRole('img', { name: fixture.live.portraitPrompt, exact: true });
  await image.evaluate(async node => { await node.decode(); });
  evidence.timings_ms.portrait_generation = performance.now() - started;
  evidence.evidence.portrait_generation = { asset_id: portrait.asset_id, model: result.model, state: portrait.state };
  return portrait;
}

module.exports = { confirmVariant, generatePortrait };
