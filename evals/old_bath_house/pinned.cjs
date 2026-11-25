'use strict';

const { bindSavedPortrait, chooseLibraryPortrait } = require('./portrait.cjs');
const { assembleEncounter } = require('./assemble.cjs');
const { attachPreparedEncounter } = require('./prepare.cjs');
const { measurePlay } = require('./play.cjs');

async function runPinnedAssets(page, fixture, evidence) {
  const portrait = await bindSavedPortrait(page, fixture, chooseLibraryPortrait);
  await runEncounter(page, fixture, portrait, evidence);
}

async function runEncounter(page, fixture, portrait, evidence) {
  evidence.timings_ms.portrait_binding = portrait.elapsedMs;
  evidence.evidence.portrait_operation_id = portrait.operationId;

  const { source, elapsedMs } = await assembleEncounter(page, fixture, portrait);
  evidence.timings_ms.encounter_assembly = elapsedMs;
  evidence.evidence.source_encounter_id = source.encounter_id;

  const attachment = await attachPreparedEncounter(page, fixture, source);
  evidence.timings_ms.plan_attachment = attachment.commitMs;
  evidence.evidence.plan_attachment_preview_ms = attachment.previewMs;
  evidence.checks.confirmed_plan_attachment = true;

  const actors = source.draft.entities.map(actor => ({
    name: actor.name,
    snapshot_digest: actor.mechanics_snapshot.snapshot_digest,
  }));
  const snapshots = [...new Map(source.draft.entities.map(actor =>
    [actor.mechanics_snapshot.snapshot_digest, actor.mechanics_snapshot])).values()];
  const result = await measurePlay(page, attachment.planUrl, {
    ...fixture, actors, snapshots, template: attachment.template,
  });
  Object.assign(evidence.timings_ms, result.timings_ms);
  Object.assign(evidence.checks, result.checks);
  Object.assign(evidence.evidence, result.evidence);
}

module.exports = { runPinnedAssets, runEncounter };
