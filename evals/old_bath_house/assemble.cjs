'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function resultFor(page, url, method, action, inspectRequest) {
  const [response] = await Promise.all([
    page.waitForResponse(result => result.url() === url.href && result.request().method() === method),
    action(),
  ]);
  if (!response.ok()) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string' ? `: ${body.detail}` : '';
    throw new Error(`${method} ${url.pathname} failed with HTTP ${response.status()}${detail}`);
  }
  if (inspectRequest) inspectRequest(response.request().postDataJSON());
  return response.json();
}

async function add(page, actor, copies) {
  await page.getByLabel('Combatant name', { exact: true }).fill(actor.name);
  await page.getByLabel('Combatant team', { exact: true }).selectOption('enemy');
  await page.getByLabel('Combatant copies', { exact: true }).fill(String(copies));
  await page.getByLabel('Combatant AC', { exact: true }).fill(String(actor.ac));
  await page.getByLabel('Combatant HP', { exact: true }).fill(String(actor.hp));
  await page.getByRole('button', { name: 'Add to encounter draft', exact: true }).click();
}

async function revealSetupControl(setup, control) {
  await control.waitFor({ state: 'attached' });
  if (!(await setup.evaluate(summary => summary.parentElement.open))) await setup.click();
  await control.waitFor({ state: 'visible' });
}

async function assembleEncounter(page, fixture, portrait) {
  const { origin, worldId, boss, minion, encounterTitle } = fixture;
  assert.match(origin, /^http:\/\/127\.0\.0\.1:[0-9]+$/);
  const url = new URL(portrait.url);
  assert.equal(url.origin, origin);
  assert.equal(url.searchParams.get('world'), worldId);
  url.pathname = '/combat';
  url.searchParams.delete('variantPortrait');
  const api = suffix => {
    const target = new URL('/api/live/combat/encounters' + suffix, origin);
    target.searchParams.set('world_id', worldId);
    return target;
  };

  await page.goto(url.href);
  const started = performance.now();
  await page.getByLabel('New encounter title', { exact: true }).fill(encounterTitle);
  const created = await resultFor(page, api(''), 'POST', () =>
    page.getByRole('button', { name: 'Create', exact: true }).click());
  assert.equal(created.world_id, worldId);
  await page.getByText('Add combatants', { exact: true }).click();
  const variant = await resultFor(page, api('/conversation-variant/preview'), 'POST', () =>
    page.getByRole('button', { name: 'Load saved statblock variant', exact: true }).click());
  assert.deepEqual(variant.locator, boss.baseLocator);
  await add(page, boss, 1);

  await page.getByRole('button', { name: 'Find saved mechanics', exact: true }).click();
  const accepted = await resultFor(page, api('/accepted-mechanics/preview'), 'POST', () =>
    page.getByRole('button', { name: minion.savedMechanicsLabel, exact: true }).click());
  assert.deepEqual(accepted.locator, minion.originalLocator);
  await add(page, minion, 3);
  const saved = await resultFor(page, api('/' + created.encounter_id), 'PUT', () =>
    page.getByRole('button', { name: 'Save', exact: true }).click());
  assert.equal(saved.draft.entities.length, 4);
  assert.equal(saved.draft.groups.length, 1);
  assert.equal(saved.draft.entities.filter(actor =>
    actor.mechanics_snapshot?.snapshot_digest === accepted.snapshot_digest).length, 3);

  await page.getByText('Setup', { exact: true }).click();
  await page.getByText('Use a saved conversation portrait', { exact: true }).click();
  await page.getByLabel('Saved portrait statblock link', { exact: true }).fill(portrait.url);
  const portraitPreview = await resultFor(page, api('/saved-mechanics/preview'), 'POST', () =>
    page.getByRole('button', { name: 'Preview exact portrait', exact: true }).click(), command => {
    assert.equal(command.portrait_operation_id, portrait.operationId);
    assert.deepEqual(command.locator, portrait.locator);
  });
  const selectBoss = page.getByRole('checkbox', { name: new RegExp(`^Select ${boss.name} \\(`), includeHidden: true });
  const setup = page.locator('summary').filter({ hasText: /^Setup$/ });
  await revealSetupControl(setup, selectBoss);
  await selectBoss.check();
  const adopted = await resultFor(page, api('/' + created.encounter_id + '/mechanics-adoptions'), 'POST', () =>
    page.getByRole('button', { name: 'Use version for selected actors', exact: true }).click());
  const bossEncounter = adopted.encounter;
  assert.equal(bossEncounter.encounter_id, created.encounter_id);
  const illustrated = bossEncounter.draft.entities.find(actor => actor.name === boss.name)?.mechanics_snapshot;
  assert.deepEqual(illustrated.locator, portrait.locator);
  assert.deepEqual(illustrated, portraitPreview.snapshot);
  assert.deepEqual(adopted.receipt.source, portrait.locator);
  assert.deepEqual(
    illustrated.resource.asset_bindings.filter(binding => binding.role === 'portrait').map(binding => binding.asset.url),
    [boss.imageUrl],
  );
  assert.deepEqual(bossEncounter.draft.groups, saved.draft.groups);
  assert.deepEqual(
    bossEncounter.draft.entities.filter(actor => actor.name !== boss.name),
    saved.draft.entities.filter(actor => actor.name !== boss.name),
  );
  const reopened = new URL('/combat', origin);
  reopened.search = new URLSearchParams({ world: worldId, encounter: created.encounter_id });
  await page.goto(reopened.href);
  await page.getByText('Setup', { exact: true }).click();
  const drafts = new URL('/api/live/threat-drafts', origin);
  drafts.search = new URLSearchParams({ world_id: worldId, limit: '20', offset: '0' });
  await resultFor(page, drafts, 'GET', () =>
    page.getByRole('button', { name: 'Find saved creatures', exact: true }).click());
  const minionChoice = page.getByRole('button', { name: minion.name, exact: true, includeHidden: true });
  await revealSetupControl(setup, minionChoice);
  await minionChoice.click();
  const version = page.getByLabel('Version to use in encounter', { exact: true });
  await revealSetupControl(setup, version);
  await version.selectOption(minion.locator.revision_id);
  await resultFor(page, api('/saved-mechanics/preview'), 'POST', () =>
    page.getByRole('button', { name: 'Preview exact version', exact: true }).click());
  for (const actor of saved.draft.entities.filter(row => row.name !== boss.name)) {
    const checkbox = page.getByRole('checkbox', {
      name: new RegExp(`^Select ${actor.name} \\(`), includeHidden: true,
    });
    await revealSetupControl(setup, checkbox);
    await checkbox.check();
  }
  const updated = await resultFor(page, api('/' + created.encounter_id + '/mechanics-adoptions'), 'POST', () =>
    page.getByRole('button', { name: 'Use version for selected actors', exact: true }).click());
  const source = updated.encounter;
  assert.equal(source.encounter_id, created.encounter_id);
  assert.deepEqual(source.draft.groups, saved.draft.groups);
  for (const actor of source.draft.entities) {
    const { mechanics_snapshot: snapshot, ...tracked } = actor;
    const { mechanics_snapshot: previous, ...previousTracked } =
      bossEncounter.draft.entities.find(row => row.id === actor.id);
    assert.deepEqual(tracked, previousTracked);
    if (actor.name === boss.name) {
      assert.deepEqual(snapshot, previous);
    } else {
      assert.deepEqual(snapshot.locator, minion.locator);
      assert.equal(snapshot.revision_operation_id, minion.revisionOperation);
      assert.deepEqual(snapshot.resource.asset_bindings, minion.assetBindings);
    }
  }
  return { source, elapsedMs: performance.now() - started };
}

module.exports = { assembleEncounter };
