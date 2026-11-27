"use strict";

const assert = require("node:assert/strict");
const { performance } = require("node:perf_hooks");

async function generatePrivatePreview(page, origin, description) {
  const studio = page.getByRole('region', { name: 'Create an image', exact: true });
  const expand = studio.getByRole('button', { name: 'Expand image studio', exact: true });
  if (await expand.isVisible()) await expand.click();
  const back = studio.getByRole('button', { name: 'Back to studio', exact: true });
  if (await back.isVisible()) await back.click();
  const prompt = studio.getByRole('textbox', { name: /What would you like to see/ });
  await prompt.fill(description);
  const generate = studio.getByRole('button', { name: 'Generate image', exact: true });
  const started = performance.now();
  const [response] = await Promise.all([
    page.waitForResponse(result => {
      const url = new URL(result.url());
      return url.origin === origin && url.pathname === '/api/live/media/images/generate'
        && result.request().method() === 'POST';
    }, { timeout: 185000 }),
    generate.click(),
  ]);
  assert.ok(response.ok(), `Image provider failed with HTTP ${response.status()}`);
  const result = await response.json();
  assert.equal(result.images.length, 1, 'Expected exactly one generated preview');
  const [portrait] = result.images;
  assert.ok(portrait?.asset_id, 'Generated preview is missing its media identity');
  assert.equal(portrait.state, 'staged');
  assert.ok(!portrait.delivery_url, 'Generated preview unexpectedly has public delivery');
  const image = studio.getByRole('img', { name: description, exact: true });
  await image.evaluate(async node => { await node.decode(); });
  return { asset: portrait, model: result.model, elapsedMs: performance.now() - started };
}

module.exports = { generatePrivatePreview };
