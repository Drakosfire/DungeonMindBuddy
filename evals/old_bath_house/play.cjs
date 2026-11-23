'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function json(response) {
  assert.ok(response.ok(), `Product request failed with HTTP ${response.status()}`);
  return response.json();
}

function encounterPath(url, runId, sceneId, suffix = '') {
  return new URL(`/api/live/combat/run-encounters/${encodeURIComponent(runId)}/scenes/${encodeURIComponent(sceneId)}${suffix}`, url);
}

function responseFor(page, path, worldId, method) {
  return page.waitForResponse(response => {
    const actual = new URL(response.url());
    return actual.origin === path.origin && actual.pathname === path.pathname
      && actual.searchParams.get('world_id') === worldId
      && response.request().method() === method;
  });
}

function assertSnapshots(snapshots, expected) {
  assert.deepEqual(
    snapshots.map(snapshot => snapshot.snapshot_digest).sort(),
    expected.map(snapshot => snapshot.snapshot_digest).sort(),
  );
  for (const pinned of expected) {
    const actual = snapshots.find(snapshot => snapshot.snapshot_digest === pinned.snapshot_digest);
    assert.deepEqual(actual.locator, pinned.locator);
    assert.deepEqual(actual.resource.asset_bindings, pinned.resource.asset_bindings);
  }
}

async function openPreview(page, session, fixture) {
  const { runId, planUrl } = session;
  const { worldId, sceneId, snapshots, template } = fixture;
  const read = responseFor(page, encounterPath(planUrl, runId, sceneId), worldId, 'GET');
  const preview = responseFor(page, encounterPath(planUrl, runId, sceneId, '/preview'), worldId, 'GET');
  const started = performance.now();
  await page.getByRole('button', { name: 'Scene encounter', exact: true }).click();
  const [existing, captured] = await Promise.all([read.then(json), preview.then(json)]);
  assert.equal(existing, null, 'Combat must be unstarted when entering Play');
  assert.equal(captured.run_id, runId);
  assert.equal(captured.scene_id, sceneId);
  assert.deepEqual(captured.template, template);
  assertSnapshots(captured.saved_mechanics, snapshots);
  await page.getByRole('button', { name: 'Start this encounter', exact: true }).waitFor();
  return { captured, previewMs: performance.now() - started };
}

async function startCombat(page, session, fixture, captured) {
  const { runId, planUrl } = session;
  const { worldId, sceneId, template, snapshots, actors } = fixture;
  const applied = responseFor(page, encounterPath(planUrl, runId, sceneId), worldId, 'POST');
  const started = performance.now();
  await page.getByRole('button', { name: 'Start this encounter', exact: true }).click();
  const { receipt, encounter, state } = await json(await applied);
  assert.equal(state, 'applied');
  assert.equal(receipt.encounter_id, encounter.encounter_id);
  assert.notEqual(encounter.encounter_id, template.encounter_id);
  assert.equal(receipt.intent.run_id, runId);
  assert.equal(receipt.intent.scene_id, sceneId);
  assert.equal(receipt.intent.request.preview_digest, captured.preview_digest);
  assert.deepEqual(receipt.intent.request.template, template);
  const entities = encounter.draft.entities;
  assert.deepEqual(
    entities.map(entity => [entity.name, entity.mechanics_snapshot?.snapshot_digest]).sort(),
    actors.map(actor => [actor.name, actor.snapshot_digest]).sort(),
  );
  const unique = new Map(entities.map(entity => [entity.mechanics_snapshot.snapshot_digest, entity.mechanics_snapshot]));
  assertSnapshots([...unique.values()], snapshots);
  await page.getByRole('button', { name: 'Next turn', exact: true }).waitFor();
  return { encounterId: encounter.encounter_id, startMs: performance.now() - started };
}

async function renderPortrait(page, name, imageUrl) {
  const started = performance.now();
  await page.getByLabel(`Keep statblock open for ${name}`, { exact: true }).click();
  const image = page.getByRole('img', { name: `Portrait of ${name}`, exact: true });
  await image.waitFor();
  const rendered = await image.evaluate(async node => {
    await node.decode();
    return { url: node.currentSrc, width: node.naturalWidth };
  });
  assert.equal(rendered.url, imageUrl);
  assert.ok(rendered.width > 0, 'Saved portrait must decode in the browser');
  return performance.now() - started;
}

async function startSession(page, planUrl, sceneTitle) {
  await page.goto(planUrl);
  await page.getByRole('button', { name: 'Start Play from this Plan', exact: true }).click();
  await page.getByLabel('Begin at').selectOption({ label: sceneTitle });
  const started = performance.now();
  await Promise.all([
    page.waitForURL(url => url.pathname === '/play' && url.searchParams.has('run')),
    page.getByRole('button', { name: 'Start session from Plan', exact: true }).click(),
  ]);
  await page.getByRole('heading', { name: sceneTitle, exact: true }).waitFor();
  return {
    runId: new URL(page.url()).searchParams.get('run'),
    runUrl: page.url(),
    planUrl,
    sessionMs: performance.now() - started,
  };
}

async function capturePreparation(page, planUrl, fixture) {
  const { documentId, worldId, sceneId } = fixture;
  const path = new URL(
    `/api/live/combat/scene-templates/${encodeURIComponent(documentId)}/scenes/${encodeURIComponent(sceneId)}`,
    planUrl,
  );
  const snapshotPath = new URL(`/api/live/workspace-documents/${encodeURIComponent(documentId)}/snapshot`, planUrl);
  const document = page.waitForResponse(response => new URL(response.url()).href === snapshotPath.href
    && response.request().method() === 'GET').then(json);
  await page.goto(planUrl);
  const preparation = responseFor(page, path, worldId, 'GET');
  await page.getByRole('button', { name: 'Scene encounter', exact: true }).click();
  const view = await json(await preparation);
  assert.equal(view.binding.world_id, worldId);
  assert.equal(view.binding.origin.document_id, documentId);
  assert.equal(view.binding.origin.scene_id, sceneId);
  assert.equal(view.encounter.encounter_id, fixture.template.encounter_id);
  assert.equal(view.encounter.revision, fixture.template.revision);
  assert.ok(view.versions.some(version => version.revision === fixture.template.revision
    && version.digest === fixture.template.digest));
  return { preparation: view, plan: await document };
}

async function verifyRunningWrite(page, session, fixture, encounterId) {
  const path = encounterPath(session.planUrl, session.runId, fixture.sceneId, `/encounters/${encounterId}`);
  const damage = page.getByRole('button', { name: `Deal 1 damage to ${fixture.boss.name}`, exact: true });
  await damage.click();
  const save = responseFor(page, path, fixture.worldId, 'PUT');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  const saved = await json(await save);
  assert.equal(saved.encounter_id, encounterId);
  assert.equal(saved.draft.entities.find(actor => actor.name === fixture.boss.name).hp, fixture.boss.hp - 1);

  await page.goto(session.runUrl);
  const read = responseFor(page, encounterPath(session.planUrl, session.runId, fixture.sceneId), fixture.worldId, 'GET');
  await page.getByRole('button', { name: 'Scene encounter', exact: true }).click();
  const reopened = await json(await read);
  assert.equal(reopened.encounter.encounter_id, encounterId);
  assert.equal(reopened.encounter.draft.entities.find(actor => actor.name === fixture.boss.name).hp, fixture.boss.hp - 1);
}

async function measurePlay(page, planUrl, fixture) {
  const target = new URL(planUrl);
  assert.equal(target.protocol, 'http:');
  assert.equal(target.hostname, '127.0.0.1', 'Benchmark writes require a disposable loopback server');
  assert.equal(target.pathname, '/plan');
  assert.equal(target.searchParams.get('world'), fixture.worldId);
  assert.equal(target.searchParams.get('documentId'), fixture.documentId);
  const before = await capturePreparation(page, planUrl, fixture);
  const parley = await startSession(page, planUrl, fixture.sceneTitle);
  await openPreview(page, parley, fixture);

  const engagement = await startSession(page, planUrl, fixture.sceneTitle);
  assert.notEqual(engagement.runId, parley.runId);
  const { captured, previewMs } = await openPreview(page, engagement, fixture);
  const { encounterId, startMs } = await startCombat(page, engagement, fixture, captured);
  const renderMs = await renderPortrait(page, fixture.boss.name, fixture.boss.imageUrl);
  await verifyRunningWrite(page, engagement, fixture, encounterId);

  await page.goto(parley.runUrl);
  await openPreview(page, parley, fixture);
  const after = await capturePreparation(page, planUrl, fixture);
  assert.deepEqual(after, before, 'Running Combat changed the saved encounter preparation');
  return {
    timings_ms: {
      play_session_create: engagement.sessionMs,
      play_preview: previewMs,
      combat_start: startMs,
      statblock_render: renderMs,
    },
    checks: {
      exact_statblock_and_portrait: true,
      parley_unstarted: true,
      explicit_combat_start: true,
      distinct_running_encounter: true,
      plan_unchanged: true,
      running_edit_persisted: true,
    },
    evidence: { parley_run_id: parley.runId, engagement_run_id: engagement.runId, encounter_id: encounterId },
  };
}

module.exports = { measurePlay };
