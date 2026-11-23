'use strict';

const assert = require('node:assert/strict');
const { createHash, randomUUID } = require('node:crypto');
const { readFileSync, writeFileSync } = require('node:fs');
const { runPinnedAssets, runEncounter } = require('./pinned.cjs');
const { runLiveTurns } = require('./live_turns.cjs');
const { confirmVariant, generatePortrait, saveGeneratedPortrait } = require('./live_artifacts.cjs');
const { bindSavedPortrait, chooseLibraryPortrait } = require('./portrait.cjs');

async function main() {
  const [fixturePath, fixtureDigest, output] = process.argv.slice(2);
  assert.ok(fixturePath && fixtureDigest && output, 'Expected fixture path, SHA-256 and new evidence path');
  const fixtureBytes = readFileSync(fixturePath);
  assert.equal(createHash('sha256').update(fixtureBytes).digest('hex'), fixtureDigest);
  const fixture = JSON.parse(fixtureBytes);
  assert.equal(fixture.schema, 'dmb_old_bath_house_benchmark_v1');
  assert.match(fixture.sourceFixtureDigest, /^[a-f0-9]{64}$/);
  const origin = new URL(fixture.origin);
  assert.match(origin.href, /^http:\/\/127\.0\.0\.1:[0-9]+\/$/);
  assert.ok(process.env.DMB_BENCHMARK_BROWSER_TOKEN, 'The isolated runtime must supply its operator token');
  const allowedImages = new Set([fixture.boss.imageUrl, fixture.minion.imageUrl]);
  const playwright = process.env.DMB_BENCHMARK_PLAYWRIGHT;
  const { chromium } = require(playwright);
  const browser = await chromium.launch({
    executablePath: process.env.DMB_BENCHMARK_CHROMIUM,
    headless: true,
  });
  const evidence = {
    run_id: randomUUID(),
    track: fixture.live ? 'live-provider' : 'pinned-assets',
    fixture_digest: fixture.sourceFixtureDigest,
    run_manifest_digest: fixtureDigest,
    conditions: 'fresh-browser-context',
    runtime: fixture.runtime,
    chromium_version: browser.version(),
    playwright_version: require(require('node:path').join(playwright, 'package.json')).version,
    timings_ms: {},
    http_requests: [],
    checks: {},
    failures: [],
    evidence: {},
  };
  let page;
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => {
      const request = route.request();
      const target = new URL(request.url());
      if (target.origin === origin.origin) {
        return route.continue({ headers: {
          ...request.headers(), authorization: `Bearer ${process.env.DMB_BENCHMARK_BROWSER_TOKEN}`,
        } });
      }
      if (request.method() === 'GET' && request.resourceType() === 'image'
          && target.protocol === 'https:' && allowedImages.has(target.href)) {
        return route.continue();
      }
      return route.abort();
    });
    page = await context.newPage();
    page.on('requestfinished', async request => {
      const url = new URL(request.url());
      if (url.origin !== origin.origin || !url.pathname.startsWith('/api/live/')) return;
      if (!/\/(combat|world-play-runs|agent\/worlds|media)(\/|$)/.test(url.pathname)) return;
      const { requestStart, responseStart, responseEnd } = request.timing();
      const response = await request.response();
      evidence.http_requests.push({
        method: request.method(), path: url.pathname, status: response?.status(),
        response_start_ms: requestStart >= 0 && responseStart >= requestStart ? responseStart - requestStart : null,
        response_end_ms: requestStart >= 0 && responseEnd >= requestStart ? responseEnd - requestStart : null,
      });
    });
    if (fixture.live) {
      await runLiveTurns(page, fixture, evidence, checkpoint => {
        writeFileSync(output + '.checkpoint', JSON.stringify(checkpoint), { mode: 0o600 });
      });
      const variant = await confirmVariant(page, fixture, evidence);
      const generated = await generatePortrait(page, fixture, variant, evidence);
      const imageUrl = await saveGeneratedPortrait(page, fixture, generated);
      allowedImages.add(imageUrl);
      const variantUrl = new URL(variant.url);
      const liveFixture = {
        ...fixture,
        boss: {
          ...fixture.boss,
          name: variant.name,
          conversationId: variantUrl.searchParams.get('conversation'),
          turnId: variantUrl.searchParams.get('turn'),
          reviewId: variantUrl.searchParams.get('variantReview'),
          baseLocator: variant.locator,
          assetId: generated.asset_id,
          imageUrl,
          libraryLabel: fixture.live.portraitPrompt + ' · Saved',
        },
      };
      const portrait = await bindSavedPortrait(page, liveFixture, chooseLibraryPortrait);
      await runEncounter(page, liveFixture, portrait, evidence);
    } else {
      await runPinnedAssets(page, fixture, evidence);
    }
  } catch (error) {
    evidence.failures.push(String(error.message));
    if (page) {
      const states = await page.locator('details').evaluateAll(nodes => nodes.map(node => ({
        label: node.querySelector('summary')?.textContent, open: node.open,
      }))).catch(() => []);
      evidence.evidence.disclosure_states = states;
      evidence.evidence.visible_alerts = await page.getByRole('alert').allTextContents().catch(() => []);
      if (fixture.live) {
        evidence.evidence.visible_turns = await page.locator('article[data-turn-id]').evaluateAll(nodes => (
          nodes.map(node => ({
            turn_id: node.dataset.turnId,
            class_name: node.className,
            assistant_visible: Boolean(node.querySelector('.world-plan-agent-conversation__message--assistant')?.getClientRects().length),
          }))
        )).catch(() => []);
      }
    }
    process.exitCode = 1;
  } finally {
    try {
      writeFileSync(output, JSON.stringify(evidence, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
    } finally {
      await browser.close();
    }
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
