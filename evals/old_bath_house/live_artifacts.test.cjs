'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const { confirmVariant, verifyLinkedVariant } = require('./live_artifacts.cjs');

const origin = 'http://127.0.0.1:5202';
const producer = '31ff7229-cd2b-44d7-88ec-b6a48b7d0f12';
const approval = '87408caf-5d60-4f1c-a206-7b594188462b';
const reviewId = 'd006c4f1-f96a-4b64-8a48-a6115bfbbd66';
const base = '/api/live/agent/worlds/test/conversations/c1';
const target = { status: 'ready', turn_id: producer, review_id: reviewId, revision: 2 };
const reviewPath = base + '/drafts/' + producer + '/variant-reviews/' + reviewId;
const locator = { definition_digest: 'sha256:' + 'a'.repeat(64), statblock_id: 'variant', revision_id: 'v1' };

function mountedFixture({ decision = target, revision = 2 } = {}) {
  const calls = [];
  const control = {
    click: async () => calls.push('confirm'),
    waitFor: async () => {},
    isVisible: async () => false,
    getAttribute: async () => '/statblock?world=test&conversation=c1&turn=' + producer + '&variantReview=' + reviewId,
  };
  const review = {
    or: () => ({ waitFor: async () => {} }),
    isVisible: async () => false,
    getByRole: () => control,
  };
  review.getByRole = role => role === 'heading'
    ? { first: () => ({ textContent: async () => 'Variant' }) } : control;
  const page = {
    locator: selector => {
      assert.equal(selector, `article[data-turn-id="${approval}"]`);
      return { getByRole: () => ({ click: async () => calls.push('find') }) };
    },
    getByRole: () => review,
    waitForResponse: async predicate => {
      const next = calls.includes('find');
      const path = next ? reviewPath + '/confirm' : base + '/turns/' + approval + '/variant-approval';
      const response = {
        url: () => origin + path,
        request: () => ({ method: () => next ? 'POST' : 'GET' }),
        ok: () => true,
        status: () => 200,
        json: async () => next ? locator : decision,
      };
      assert.ok(predicate(response));
      return response;
    },
    evaluate: async (_read, path) => {
      assert.ok([reviewPath, reviewPath + '/saved'].includes(path));
      return { status: 200, body: path.endsWith('/saved') ? { locator } : { saved: false, revision } };
    },
  };
  const fixture = { origin, worldId: 'test', live: { originalStatblockId: 'base' } };
  const evidence = { evidence: { turns: [{ turnId: producer }, { turnId: approval }] }, checks: {} };
  return { run: () => confirmVariant(page, fixture, evidence), calls, evidence };
}

test('confirms and independently reopens the exact reviewed variant', async () => {
  const current = mountedFixture();
  assert.deepEqual((await current.run()).locator, locator);
  assert.deepEqual(current.calls, ['find', 'confirm']);
  assert.equal(current.evidence.checks.exact_variant_reopened, true);
});

test('refuses a review from another producing turn before save', async () => {
  const wrong = mountedFixture({ decision: { ...target, turn_id: approval } });
  await assert.rejects(wrong.run(), /different producing turn/);
  assert.deepEqual(wrong.calls, ['find']);
});

test('refuses a changed revision before save', async () => {
  const stale = mountedFixture({ revision: 3 });
  await assert.rejects(stale.run(), /revision changed/);
  assert.deepEqual(stale.calls, ['find']);
});

test('refuses a foreign saved variant before creating a browser tab', async () => {
  const page = { context: () => assert.fail('Opened a tab before checking variant authority') };
  const fixture = { origin, worldId: 'test', live: { pageId: 'edge' } };
  const evidence = { evidence: {}, checks: {} };
  await assert.rejects(
    verifyLinkedVariant(page, fixture, { url: 'http://127.0.0.1:5203/statblock?world=test' }, evidence),
    /strictly equal/,
  );
  assert.deepEqual(evidence.checks, {});
});
