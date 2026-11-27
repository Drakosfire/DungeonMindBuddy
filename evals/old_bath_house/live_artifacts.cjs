'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const { generatePrivatePreview } = require('../buddy_benchmark/image_studio.cjs');

async function confirmVariant(page, fixture, evidence) {
  const turns = evidence.evidence.turns;
  const producer = turns.at(-2).turnId;
  const approval = turns.at(-1).turnId;
  const find = page.locator(`article[data-turn-id="${approval}"]`)
    .getByRole('button', { name: 'Find reviewed statblock', exact: true });
  const worldPath = '/api/live/agent/worlds/' + encodeURIComponent(fixture.worldId) + '/conversations/';
  const [decision] = await Promise.all([
    page.waitForResponse(result => {
      const url = new URL(result.url());
      return url.origin === fixture.origin && url.pathname.startsWith(worldPath)
        && url.pathname.endsWith('/turns/' + encodeURIComponent(approval) + '/variant-approval')
        && result.request().method() === 'GET';
    }),
    find.click(),
  ]);
  assert.ok(decision.ok(), `Variant approval failed with HTTP ${decision.status()}`);
  const target = await decision.json();
  assert.equal(target.status, 'ready');
  assert.equal(target.turn_id, producer, 'Variant approval resolved to a different producing turn');
  assert.match(target.review_id, /^[0-9a-f-]{36}$/i);
  assert.ok(Number.isSafeInteger(target.revision) && target.revision > 0);
  const conversationPath = new URL(decision.url()).pathname.split('/turns/')[0];
  const reviewPath = conversationPath + '/drafts/' + encodeURIComponent(producer)
    + '/variant-reviews/' + encodeURIComponent(target.review_id);
  const checked = await page.evaluate(async path => {
    const response = await fetch(path, { cache: 'no-store' });
    return { status: response.status, body: await response.json() };
  }, reviewPath);
  assert.equal(checked.status, 200);
  assert.equal(checked.body.revision, target.revision, 'Review revision changed before confirmation');
  assert.equal(checked.body.saved, false, 'The review already has a saved variant');
  evidence.evidence.variant_review = target;
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
      return url.origin === fixture.origin && url.pathname === reviewPath + '/confirm' && result.request().method() === 'POST';
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
  assert.equal(url.searchParams.get('conversation'), decodeURIComponent(conversationPath.split('/').at(-1)));
  assert.equal(url.searchParams.get('turn'), producer);
  assert.equal(url.searchParams.get('variantReview'), target.review_id);
  const reopened = await page.evaluate(async path => {
    const response = await fetch(path, { cache: 'no-store' });
    return { status: response.status, body: await response.json() };
  }, reviewPath + '/saved');
  assert.equal(reopened.status, 200);
  assert.deepEqual(reopened.body.locator, locator);
  evidence.checks.exact_variant_reopened = true;
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
