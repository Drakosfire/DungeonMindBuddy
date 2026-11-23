'use strict';

const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');

async function observeTurnStream(page) {
  // Observe a clone of the real browser response. Leave the product's own stream
  // reader and durable completion untouched.
  await page.evaluate(() => {
    if (window.__oldBathHouseTurns) return;
    const records = window.__oldBathHouseTurns = [];
    const fetchTurn = window.fetch.bind(window);
    window.fetch = async (...args) => {
      const response = await fetchTurn(...args);
      const url = new URL(response.url);
      if (url.origin !== location.origin || url.pathname !== '/api/live/agent/turn') return response;
      const observed = response.clone();
      void (async () => {
        if (!observed.headers.get('content-type')?.includes('text/event-stream')) {
          const payload = await observed.json();
          records.push({
            kind: response.ok ? 'result' : 'error',
            turnId: payload.turn_id, status: response.status,
            code: payload.answer?.code ?? payload.detail?.code,
            answerStatus: payload.answer?.status,
          });
          return;
        }
        const reader = observed.body.pipeThrough(new TextDecoderStream()).getReader();
        let pending = '';
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            pending += value;
            const lines = pending.split(/\r?\n/);
            pending = lines.pop();
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              const frame = JSON.parse(line.slice(6));
              if (frame.kind === 'result' || frame.kind === 'error') {
                records.push({
                  kind: frame.kind,
                  turnId: frame.client_turn_id,
                  responseTurnId: frame.response?.turn_id,
                  status: frame.status,
                  code: frame.detail?.code ?? frame.response?.answer?.code,
                  answerStatus: frame.response?.answer?.status,
                });
                return;
              }
            }
          }
        } finally {
          void reader.cancel().catch(() => {});
        }
      })().catch(() => records.push({ kind: 'observer_error' }));
      return response;
    };
  });
}

async function selectMeatMind(page, nodeId) {
  await page.getByRole('button', { name: '@ Reference', exact: true }).click();
  const inspection = page.getByRole('region', { name: 'Reviewed Graph inspection', exact: true });
  await inspection.getByLabel('Find an object', { exact: true }).fill('Meat Mind');
  const match = inspection.getByRole('listitem').filter({
    has: page.getByRole('button', { name: `Meat Mind ${nodeId}`, exact: true }),
  });
  await match.getByRole('button', { name: 'Use Meat Mind as context', exact: true }).click();
  await page.getByRole('button', { name: 'Remove reference Meat Mind', exact: true }).waitFor();
}

async function sendTurn(page, input, { nodeId, checkpoint = {}, reportStage = () => {} } = {}) {
  const composer = page.getByLabel('Message DungeonBuddy', { exact: true });
  const send = page.getByRole('button', { name: 'Send message', exact: true });
  await observeTurnStream(page);
  await composer.fill(input);
  let firstVisible;
  const firstReply = page.waitForFunction(previous => {
    const replies = Array.from(document.querySelectorAll('article[data-turn-id] .world-plan-agent-conversation__message--assistant'));
    const reply = replies.find(node => {
      const turn = node.closest('article[data-turn-id]');
      return !previous.includes(turn.dataset.turnId) && node.getClientRects().length > 0
        && node.innerText.trim() !== 'Buddy' && turn.classList.contains('world-plan-agent-conversation__turn--complete');
    });
    return reply?.closest('article[data-turn-id]').dataset.turnId;
  }, await page.locator('article[data-turn-id]').evaluateAll(nodes => nodes.map(node => node.dataset.turnId)),
  { timeout: 180000 }).then(async handle => {
    firstVisible = performance.now();
    return handle.jsonValue();
  });
  // Attach handlers before clicking so a provider failure cannot leave a rejected waiter.
  firstReply.catch(() => {});
  const response = page.waitForResponse(result => {
    const endpoint = new URL(result.url());
    return endpoint.origin === new URL(page.url()).origin && endpoint.pathname === '/api/live/agent/turn'
      && result.request().method() === 'POST';
  }, { timeout: 180000 });
  response.catch(() => {});
  const started = performance.now();
  checkpoint.stage = 'submitting';
  reportStage(checkpoint);
  await send.click();
  const delivered = await response;
  const firstResponseMs = performance.now() - started;
  checkpoint.stage = 'response_started';
  checkpoint.first_response_ms = firstResponseMs;
  reportStage(checkpoint);
  assert.ok(delivered.ok(), `Buddy turn failed with HTTP ${delivered.status()}`);
  const request = delivered.request().postDataJSON();
  assert.ok(request.turn_id, 'Buddy request must carry the originating turn identity');
  if (nodeId) assert.ok(JSON.stringify(request).includes(nodeId), 'Meat Mind reference is missing from the request');
  const finished = page.waitForFunction(turnId => window.__oldBathHouseTurns.find(
    record => record.turnId === turnId || record.kind === 'observer_error',
  ), request.turn_id, { timeout: 180000 }).then(async handle => {
    const completeMs = performance.now() - started;
    const terminal = await handle.jsonValue();
    if (terminal.kind !== 'result' || terminal.answerStatus !== 'ok') {
      throw new Error(`Buddy turn failed: ${terminal.status ?? terminal.kind} ${terminal.code ?? ''}`.trim());
    }
    assert.equal(terminal.responseTurnId ?? terminal.turnId, request.turn_id);
    checkpoint.stage = 'terminal_reply_verified';
    checkpoint.server_response_complete_ms = completeMs;
    reportStage(checkpoint);
    return completeMs;
  });
  let deadline;
  const timeout = new Promise((_, reject) => {
    deadline = setTimeout(() => reject(new Error(`Live turn exceeded its deadline in stage ${checkpoint.stage}`)), 185000);
  });
  let visibleTurnId;
  let completeMs;
  try {
    [visibleTurnId, completeMs] = await Promise.race([Promise.all([firstReply, finished]), timeout]);
  } finally {
    clearTimeout(deadline);
  }
  return {
    clientTurnId: request.turn_id,
    turnId: visibleTurnId,
    firstVisibleMs: firstVisible - started,
    firstResponseMs,
    completeMs,
  };
}

async function runLiveTurns(page, fixture, evidence, reportStage) {
  const { origin, worldId, live } = fixture;
  assert.match(origin, /^http:\/\/127\.0\.0\.1:[0-9]+$/);
  assert.equal(live.turns.length, 6);
  const build = new URL('/build', origin);
  build.search = new URLSearchParams({ world: worldId, documentId: live.pageId });
  const readiness = page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.origin === build.origin && url.pathname === '/api/live/agent/readiness'
      && url.searchParams.get('surface') === 'build';
  });
  readiness.catch(() => {});
  await page.goto(build.href);
  const composer = page.getByLabel('Message DungeonBuddy', { exact: true });
  if (!(await composer.isVisible())) await page.locator('.conversation-dock__launcher').getByRole('button').click();
  await composer.waitFor();
  const ready = await (await readiness).json();
  assert.ok(ready.configured, `Build runtime not ready: ${ready.issues?.join(', ') ?? 'no readiness detail'}`);
  evidence.evidence.turns = [];
  for (const [index, prompt] of live.turns.entries()) {
    const nodeId = index === 0 ? live.meatMindNodeId : undefined;
    if (nodeId) await selectMeatMind(page, nodeId);
    const input = index === 0 ? prompt.replace(/\n@Meat Mind$/, '') : prompt;
    const checkpoint = { ordinal: index + 1 };
    evidence.evidence.turns.push(checkpoint);
    const result = await sendTurn(page, input, { nodeId, checkpoint, reportStage });
    Object.assign(checkpoint, result, { stage: 'visible_reply_verified' });
    reportStage(checkpoint);
    if (index === 0) {
      evidence.timings_ms.first_visible_reply = result.firstVisibleMs;
      evidence.timings_ms.reply_finished = result.completeMs;
    }
    if (index === 4) evidence.timings_ms.statblock_generation = result.completeMs;
  }
}

module.exports = { runLiveTurns, selectMeatMind, sendTurn };
