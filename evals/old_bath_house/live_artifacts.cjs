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

async function verifyLinkedVariant(page, fixture, variant, evidence) {
 const { worldId: world, origin } = fixture;
 const edgeId = fixture.live.pageId;
 const saved = new URL(variant.url);
 assert.equal(saved.origin, origin);
 assert.equal(saved.pathname, '/statblock');
 assert.equal(saved.searchParams.get('world'), world);
 const relative = saved.pathname + saved.search;
 const edge=new URL('/build',origin); edge.search=new URLSearchParams({world,documentId:edgeId});
 const fresh=await page.context().newPage();
 fresh.setDefaultTimeout(20000);
 const get=async path=>fresh.evaluate(async url=>{const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('GET '+response.status);return response.json()},path);
 try {
  await fresh.goto(edge.href);
  const snap='/api/live/workspace-documents/'+edgeId+'/snapshot?view=committed';
  const before=await get(snap);
  assert.equal(typeof before.markdown,'string');
  assert.equal(before.markdown.split(relative).length-1,0);
  const chat=fresh.getByLabel('Message DungeonBuddy',{exact:true});
  if(!(await chat.isVisible()))await fresh.locator('.conversation-dock__launcher').getByRole('button').click();
  const approval=evidence.evidence.turns.at(-1).turnId;
  const find=fresh.locator('article[data-turn-id="'+approval+'"]').getByRole('button',{name:'Find reviewed statblock',exact:true});
  await find.click();
  const region=fresh.getByRole('region',{name:'Statblock variant review',exact:true});
  const link=region.getByRole('link',{name:'Open saved variant',exact:true});
  await link.waitFor();
  assert.equal(new URL(await link.getAttribute('href'),origin).href,saved.href);
  const insert=region.getByRole('button',{name:'Insert at cursor and save page',exact:true});
  await insert.click();
  await region.getByText('Variant link verified on the saved page.',{exact:true}).waitFor();
  const after=await get(snap);
  assert.equal(after.markdown.split(relative).length-1,1);
  await fresh.reload();
  assert.deepEqual(await get(snap),after);
  evidence.checks.edge_link_once=true;
  const combat=new URL(saved);combat.pathname='/combat';
  await fresh.goto(combat.href);
  await fresh.getByLabel('New encounter title',{exact:true}).fill('Saved variant reopen');
  const create=fresh.waitForResponse(r=>new URL(r.url()).pathname==='/api/live/combat/encounters'&&r.request().method()==='POST');
  await fresh.getByRole('button',{name:'Create',exact:true}).click();
  const created=await create;assert.ok(created.ok());const enc=await created.json();
  await fresh.getByText('Add combatants',{exact:true}).click();
  const preview=fresh.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/conversation-variant/preview')&&r.request().method()==='POST');
  await fresh.getByRole('button',{name:'Load saved statblock variant',exact:true}).click();
  const response=await preview;assert.ok(response.ok());const value=await response.json();
  assert.deepEqual(value.locator,variant.locator);
  await fresh.getByLabel('Combatant name',{exact:true}).fill(variant.name);
  await fresh.getByLabel('Combatant team',{exact:true}).selectOption('enemy');
  await fresh.getByRole('button',{name:'Add to encounter draft',exact:true}).click();
  const path='/api/live/combat/encounters/'+enc.encounter_id;
  const commit=fresh.waitForResponse(r=>new URL(r.url()).pathname===path&&r.request().method()==='PUT');
  await fresh.getByRole('button',{name:'Save',exact:true}).click();
  assert.ok((await commit).ok());
  const reopen=new URL('/combat',origin);reopen.search=new URLSearchParams({world,encounter:enc.encounter_id});
  await fresh.goto(reopen.href);
  const reopened=await get(path+'?world_id='+encodeURIComponent(world));
  const actor=reopened.draft.entities.find(x=>x.name===variant.name);
  assert.deepEqual(actor?.mechanics_snapshot?.locator,variant.locator);
  evidence.checks.exact_variant_in_combat=true;
  evidence.evidence.linked_variant={href:relative,locator:variant.locator,encounter:enc.encounter_id,edge_revision:after.loaded_revision??after.revision??null};
 } finally {await fresh.close();}
}

module.exports = { confirmVariant, generatePortrait, verifyLinkedVariant };
