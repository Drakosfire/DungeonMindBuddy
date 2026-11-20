import { getWorkspaceDocumentSnapshot, getWorldOwnedPlanCommittedRevision } from '../api/liveApi';
import type { DocumentReference } from './documentReference';

export interface DocumentInspection {
  title: string;
  markdown: string;
  digest: string;
  revisionLabel: string;
}
export const documentReferenceReads = {
  build: getWorkspaceDocumentSnapshot,
  plan: getWorldOwnedPlanCommittedRevision,
};
export async function resolveDocumentReference(target: DocumentReference, worldId: string,
  reads = documentReferenceReads): Promise<DocumentInspection> {
  if (target.worldId !== worldId) throw new Error('This reference belongs to another World.');
  if (target.surface === 'build' && target.revisionN !== undefined) {
    throw new Error('This Build revision type is not available for inspection.');
  }
  let result: DocumentInspection;
  if (target.surface === 'build') {
    const snapshot = await reads.build(target.documentId);
    const record = snapshot.record;
    if (record.document_id !== target.documentId || record.kind !== 'worldbuilding_source'
      || (record.world_id || record.campaign_id) !== worldId || record.status !== 'active'
      || record.content_status !== 'committed' || record.revision !== snapshot.loaded_revision
      || !Number.isSafeInteger(snapshot.loaded_revision) || snapshot.loaded_revision < 1) {
      throw new Error('The saved Build document does not match this reference.');
    }
    if (target.registryRevision !== undefined && snapshot.loaded_revision !== target.registryRevision) {
      throw new Error(`Build registry revision ${target.registryRevision} is unavailable. Current content has not been substituted.`);
    }
    result = { title: record.title, markdown: snapshot.markdown, digest: snapshot.content_sha256,
      revisionLabel: `Saved page · registry revision ${snapshot.loaded_revision}` };
  } else {
    const revision = await reads.plan(target.documentId, target.revisionN);
    if (revision.schema_version !== 'dmb_workspace_committed_revision_v2' || revision.document_id !== target.documentId
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(revision.work_revision_id)
      || !Number.isSafeInteger(revision.revision_n) || revision.revision_n < 1
      || revision.kind !== 'plan' || revision.world_id !== worldId || revision.campaign_id !== null || revision.status !== 'active'
      || (target.revisionN !== undefined && revision.revision_n !== target.revisionN)
      || (target.registryRevision !== undefined && revision.object_revision !== target.registryRevision)) {
      throw new Error('The saved Plan revision does not match this reference.');
    }
    result = { title: revision.title, markdown: revision.markdown, digest: revision.content_sha256,
      revisionLabel: `Saved Plan · ${target.revisionN !== undefined ? 'historical ' : ''}content revision ${revision.revision_n}` };
  }
  if (typeof result.title !== 'string' || typeof result.markdown !== 'string' || !/^[0-9a-f]{64}$/.test(result.digest)) throw new Error('Saved document integrity could not be checked.');
  const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(result.markdown))))
    .map(byte => byte.toString(16).padStart(2, '0')).join('');
  if (actual !== result.digest || (target.digest !== undefined && target.digest !== actual)) {
    throw new Error('The saved document digest does not match this reference.');
  }
  return result;
}
