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

async function selectLibraryImage(page, origin, parent) {
  const studio = page.getByRole("region", { name: "Create an image", exact: true });
  const library = studio.getByRole("region", { name: "Image library", exact: true });
  const cards = library.locator(".media-image-wizard__card");
  const openLibrary = studio.getByRole("button", { name: "Image library", exact: true });
  const more = library.getByRole("button", { name: "More images", exact: true });
  const seen = new Set();
  let button = openLibrary;
  while (true) {
    const response = page.waitForResponse(result => {
      const url = new URL(result.url());
      return url.origin === origin && url.pathname === "/api/live/media/images/library" && result.ok();
    });
    const [pageResponse] = await Promise.all([response, button.click()]);
    const rows = (await pageResponse.json()).items;
    const next = rows.filter(row => !seen.has(row.asset_id));
    if (!next.length) throw new Error("Pinned parent is absent from the mounted library");
    const index = next.findIndex(row => row.asset_id === parent.asset_id);
    if (index >= 0) {
      const row = next[index];
      assert.equal(row.content_sha256, parent.content_sha256);
      await cards.nth(seen.size + index).click();
      break;
    }
    next.forEach(row => seen.add(row.asset_id));
    await cards.nth(seen.size - 1).waitFor();
    button = more;
  }
  return studio;
}

async function regeneratePrivatePreview(page, origin, parent, instructions) {
  const studio = await selectLibraryImage(page, origin, parent);
  await studio.getByRole("button", { name: "Edit image", exact: true }).click();
  const edit = page.getByRole("dialog", { name: "Edit image", exact: true });
  await edit.getByLabel("Action").selectOption("image_to_image");
  await edit.getByLabel("Instructions").fill(instructions);
  const path = "/api/live/media/images/" + parent.asset_id + "/regenerate";
  const editRoute = url => url.origin === origin && url.pathname.endsWith("/regenerate");
  const expected = { mode: "image_to_image", instructions, expected_content_sha256: parent.content_sha256 };
  let observed;
  await page.route(editRoute, async route => {
    const request = route.request();
    const body = request.postDataJSON();
    if (new URL(request.url()).pathname !== path || request.method() !== "POST"
        || !Object.keys(expected).every(key => body?.[key] === expected[key])) {
      await route.abort();
      return;
    }
    observed = body;
    await route.fallback();
  });
  const started = performance.now();
  const completion = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === origin && url.pathname === path && response.request().method() === "POST";
  }, { timeout: 185000 });
  try {
    const [response] = await Promise.all([
      completion, edit.getByRole("button", { name: "Generate", exact: true }).click(),
    ]);
    assert.ok(response.ok(), `Image edit failed with HTTP ${response.status()}`);
    const asset = await response.json();
    assert.ok(asset.asset_id && asset.asset_id !== parent.asset_id);
    assert.equal(asset.parent_asset_id, parent.asset_id);
    assert.equal(asset.state, "staged");
    assert.deepEqual(observed, expected);
    const image = edit.getByRole("img", { name: "Generated alternative", exact: true });
    const sha256 = await image.evaluate(async element => {
      await element.decode();
      const bytes = await (await fetch(element.currentSrc)).arrayBuffer();
      return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
        byte => byte.toString(16).padStart(2, "0")).join("");
    });
    return { asset: { asset_id: asset.asset_id, state: asset.state }, parent_request: observed,
      model: asset.model, sha256, elapsedMs: performance.now() - started };
  } finally {
    await page.unroute(editRoute);
  }
}

async function recoverImageSave(page, origin, studio, assetId, observation) {
  const assetUrl = origin + "/api/live/media/images/" + assetId;
  const saveUrl = assetUrl + "/save";
  const started = performance.now();
  let saveAttempts = 0;
  let committedStatus = null;
  const loseAcknowledgement = async route => {
    saveAttempts++;
    if (route.request().method() !== "POST" || saveAttempts !== 1) {
      await route.abort();
      return;
    }
    const response = await route.fetch({
      headers: { ...route.request().headers(), authorization: "Bearer " + process.env.DMB_BENCHMARK_BROWSER_TOKEN },
      maxRetries: 0, maxRedirects: 0,
    });
    committedStatus = response.status();
    await route.abort();
  };
  await page.route(saveUrl, loseAcknowledgement);
  try {
    const details = studio.locator("details.media-image-wizard__details");
    if (await details.getAttribute("open") === null)
      await details.locator("summary").filter({ hasText: /^Details$/ }).click();
    const reopened = page.waitForResponse(response => response.url() === assetUrl
      && response.request().method() === "GET" && response.ok());
    const [response] = await Promise.all([
      reopened, studio.getByRole("button", { name: "Save image", exact: true }).click(),
    ]);
    const asset = await response.json();
    await studio.getByRole("status").filter({ hasText: "Saved to CDN" }).waitFor();
    assert.equal(committedStatus, 200);
    assert.equal(saveAttempts, 1);
    assert.equal(asset.asset_id, assetId);
    assert.equal(asset.state, "ready");
    observation.recovered_state = asset.state;
  } finally {
    Object.assign(observation, { asset_id: assetId, committed_status: committedStatus,
      save_attempts: saveAttempts, elapsed_ms: performance.now() - started });
    await page.unroute(saveUrl, loseAcknowledgement);
  }
}

module.exports = { generatePrivatePreview, regeneratePrivatePreview, selectLibraryImage, recoverImageSave };
