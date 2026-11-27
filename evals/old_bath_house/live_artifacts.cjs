'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const { generatePrivatePreview } = require('../buddy_benchmark/image_studio.cjs');

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
  const { asset: portrait, model, elapsedMs } = await generatePrivatePreview(
    page, fixture.origin, fixture.live.portraitPrompt
  );
  evidence.timings_ms.portrait_generation = elapsedMs;
  evidence.evidence.portrait_generation = { asset_id: portrait.asset_id, model, state: portrait.state };
  return portrait;
}

module.exports = { confirmVariant, generatePortrait };
