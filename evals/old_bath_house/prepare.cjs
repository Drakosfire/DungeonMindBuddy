'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function attachPreparedEncounter(page, fixture, source) {
  const { origin, worldId, documentId, sceneId, sceneTitle, planPin } = fixture;
  assert.match(origin, /^http:\/\/127\.0\.0\.1:[0-9]+$/);
  const planUrl = new URL('/plan', origin);
  planUrl.search = new URLSearchParams({ world: worldId, documentId });
  const endpoint = new URL('/api/live/combat/scene-templates', origin);
  endpoint.searchParams.set('world_id', worldId);

  await page.goto(planUrl.href);
  await page.getByRole('button', { name: `Show scene: ${sceneTitle}`, exact: true }).click();
  await page.getByRole('button', { name: 'Scene encounter', exact: true }).click();

  const observedWrites = [];
  function observe(request) {
    if (request.url() === endpoint.href && request.method() === 'POST') observedWrites.push(request);
  }
  page.on('request', observe);
  try {
    const started = performance.now();
    await page.getByRole('button', { name: 'Choose a saved encounter', exact: true }).click();
    const picker = page.getByRole('region', { name: 'Prepare from saved Combat', exact: true })
      .getByRole('combobox');
    await picker.selectOption({
      label: `${source.draft.title} · revision ${source.revision}`,
      value: source.encounter_id,
    });
    const preview = page.getByRole('region', { name: 'Saved encounter preview', exact: true });
    await preview.getByText(`Copy to ${sceneTitle} with ${source.draft.entities.length} combatants and ${source.draft.groups.length} groups.`, { exact: true }).waitFor();
    assert.equal(observedWrites.length, 0, 'Preview must not write a scene template');
    const previewMs = performance.now() - started;
    const response = page.waitForResponse(result =>
      result.url() === endpoint.href && result.request().method() === 'POST');
    const confirmed = performance.now();
    await preview.getByRole('button', { name: 'Confirm encounter copy', exact: true }).click();
    const result = await response;
    assert.ok(result.ok(), `Plan attachment failed with HTTP ${result.status()}`);
    const intent = result.request().postDataJSON();
    assert.deepEqual(intent.pin, { document_id: documentId, scene_id: sceneId, ...planPin });
    assert.deepEqual(intent.encounter, {
      schema_version: 'dmb_scene_template_copy_saved_v1',
      source_encounter_id: source.encounter_id,
      expected_revision: source.revision,
    });
    const view = await result.json();
    assert.equal(view.binding.world_id, worldId);
    assert.equal(view.binding.operation_id, intent.operation_id);
    assert.deepEqual(view.binding.origin, intent.pin);
    assert.equal(view.binding.encounter_id, view.encounter.encounter_id);
    assert.notEqual(view.encounter.encounter_id, source.encounter_id);
    assert.deepEqual(view.encounter.draft.entities, source.draft.entities);
    assert.deepEqual(view.encounter.draft.groups, source.draft.groups);
    await page.getByText(`Saved · rev ${view.encounter.revision}`, { exact: true }).waitFor();
    const version = view.versions.find(item => item.revision === view.encounter.revision);
    assert.ok(version, 'Saved Plan preparation is missing its version pin');
    return {
      planUrl: planUrl.href,
      template: { encounter_id: view.encounter.encounter_id, revision: version.revision, digest: version.digest },
      previewMs,
      commitMs: performance.now() - confirmed,
    };
  } finally {
    page.off('request', observe);
  }
}

module.exports = { attachPreparedEncounter };
