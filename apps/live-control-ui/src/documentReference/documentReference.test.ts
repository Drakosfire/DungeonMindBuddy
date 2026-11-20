import { describe, expect, it, vi } from 'vitest';
import { webcrypto } from 'node:crypto';
import { parseDocumentReference, admittedDocumentHref } from './documentReference';
import { resolveDocumentReference } from './resolveDocumentReference';
import type { DocumentReference } from './documentReference';
const ID = 'bba72416-9dfe-49bb-add0-21a346e9a421';
const href = `/build?world=elderwyld&documentId=${ID}`;
const origin = 'https://buddy.example';
const target: DocumentReference = { surface: 'build', worldId: 'elderwyld', documentId: ID };
const text = '# Saved page';
const digest = Array.from(new Uint8Array(await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(text))))
  .map(byte => byte.toString(16).padStart(2, '0')).join('');
const snapshot = { schema_version: 'dmb_workspace_document_snapshot_v1', record: {
  document_id: ID, world_id: 'elderwyld', campaign_id: 'elderwyld', kind: 'worldbuilding_source', status: 'active',
  content_status: 'committed', revision: 9, title: 'Saved page' }, markdown: text, content_sha256: digest, loaded_revision: 9 };
function reads(value: unknown = snapshot) {
  return { build: vi.fn().mockResolvedValue(value), plan: vi.fn().mockResolvedValue({
    schema_version: 'dmb_workspace_committed_revision_v2', document_id: ID, kind: 'plan', world_id: 'elderwyld',
    campaign_id: null, status: 'active', work_revision_id: 'ccdcf910-55a5-4fa6-83f4-2b7a7dfca029', object_revision: 20, revision_n: 3, markdown: text, content_sha256: digest, title: 'Old Plan',
  }) };
}

describe('document reference identity', () => {
  it('admits exact root-relative and same-origin pointers without inventing revision identity', () => {
    expect(parseDocumentReference(`${href}&revision=8`, origin)).toMatchObject({kind:'document',target:{registryRevision:8}});
    expect(parseDocumentReference(`${origin}/plan?world=elderwyld&documentId=${ID}&revision_n=3`, origin))
      .toMatchObject({kind:'document',target:{surface:'plan',revisionN:3}});
    expect(admittedDocumentHref(href)).toBe(true);
    expect(admittedDocumentHref('../source.md')).toBe(false);
  });
  it.each(['&revision=0','&revision=1&revision_n=2','&world=other','&%77orld=other','&campaign=other','&documentId=other',
    '&revision=9007199254740992','&view=bogus','&sourceArtifactId=x','&content_sha256=bad'])('rejects selectors %s', suffix => {
    expect(parseDocumentReference(href + suffix, origin).kind).toBe('invalid');
  });
  it('does not capture unrelated routes or foreign lookalikes', () => {
    expect(parseDocumentReference('https://elsewhere.example'+href, origin).kind).toBe('other');
    expect(parseDocumentReference('/play?world=elderwyld&run=one', origin).kind).toBe('other');
    expect(parseDocumentReference('/build?world=elderwyld', origin).kind).toBe('other');
    for (const value of [`${origin}/a/../build?world=elderwyld&documentId=${ID}`,`https://u:p@buddy.example${href}`,href+'\\evil']) {
      expect(parseDocumentReference(value, origin).kind).toBe('invalid');
    }
  });
});

describe('owner-backed saved document reads', () => {
  it('checks returned bytes and exact current registry revision', async () => {
    vi.stubGlobal('crypto',webcrypto);
    expect(await resolveDocumentReference({...target,registryRevision:9,digest},'elderwyld',reads())).toMatchObject({markdown:text,digest});
  });
  it('never substitutes current Build for missing historical revision', async () => {
    await expect(resolveDocumentReference({...target,registryRevision:8},'elderwyld',reads())).rejects.toThrow('has not been substituted');
  });
  it('uses exact immutable Plan reads and validates the returned revision', async () => {
    const api = reads();
    await expect(resolveDocumentReference({...target,surface:'plan',revisionN:3,digest},'elderwyld',api)).resolves.toMatchObject({revisionLabel:expect.stringContaining('historical')});
    expect(api.plan).toHaveBeenCalledWith(ID,3);
    await expect(resolveDocumentReference({...target,surface:'plan',revisionN:4},'elderwyld',api)).rejects.toThrow('does not match');
  });
  it.each([
    { record:{...snapshot.record,world_id:'foreign'} }, { record:{...snapshot.record,document_id:'foreign'} },
    { record:{...snapshot.record,status:'trashed'} }, { record:{...snapshot.record,kind:'plan'} },
    { record:{...snapshot.record,content_status:'draft'} }, { loaded_revision:8 }, {markdown:'changed'},
  ])('rejects mismatched owner or bytes %j', async changed => {
    await expect(resolveDocumentReference(target,'elderwyld',reads({...snapshot,...changed}))).rejects.toThrow();
  });
  it('rejects cross-World and unsupported revision kinds before IO', async () => {
    const api=reads();
    await expect(resolveDocumentReference(target,'foreign',api)).rejects.toThrow('another World');
    await expect(resolveDocumentReference({...target,revisionN:8},'elderwyld',api)).rejects.toThrow('not available');
    expect(api.build).not.toHaveBeenCalled(); expect(api.plan).not.toHaveBeenCalled();
  });
});
