export interface DocumentReference {
  surface: 'build' | 'plan';
  worldId: string;
  documentId: string;
  registryRevision?: number;
  revisionN?: number;
  digest?: string;
  heading?: string;
}
export type ReferenceParse = { kind: 'document'; target: DocumentReference }
  | { kind: 'invalid'; message: string } | { kind: 'other' };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const WORLD = /^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$/;
const SHA = /^[0-9a-f]{64}$/;
const selectors = new Set(['world', 'documentId', 'campaign', 'revision', 'revision_n', 'content_sha256', 'view']);

/** URL syntax is a navigation request, never proof of document ownership. */
export function parseDocumentReference(href: string, origin: string): ReferenceParse {
  const invalid: ReferenceParse = { kind: 'invalid', message: 'This document reference has unsupported or conflicting selectors.' };
  let url: URL;
  try { url = new URL(href, origin); } catch { return { kind: 'other' }; }
  if (url.origin !== origin || !['/build', '/plan'].includes(url.pathname)) return { kind: 'other' };
  // Only document references opt in; ordinary surface navigation keeps its owner.
  if (!url.searchParams.has('documentId')) return { kind: 'other' };
  const rawPath = href.startsWith('/') ? href.split(/[?#]/)[0] : /^https?:\/\/[^/]+(\/[^?#]*)?/.exec(href)?.[1];
  if (rawPath !== url.pathname) return invalid;
  if (/[\s\u0000-\u001f\u007f\\]/u.test(href) || url.username || url.password
    || /%2f|%5c/i.test(href.split('?')[0])) return invalid;
  for (const key of url.searchParams.keys()) {
    if (!selectors.has(key) || url.searchParams.getAll(key).length !== 1) return invalid;
  }
  const documentId = url.searchParams.get('documentId') ?? '';
  const worldId = url.searchParams.get('world') ?? '';
  if (!UUID.test(documentId) || !WORLD.test(worldId)) return invalid;
  const campaign = url.searchParams.get('campaign');
  if (campaign !== null && campaign !== worldId) return invalid;
  const integer = (key: string) => {
    const value = url.searchParams.get(key);
    return value === null ? undefined : /^[1-9][0-9]*$/.test(value) && Number.isSafeInteger(Number(value)) ? Number(value) : NaN;
  };
  const registryRevision = integer('revision'), revisionN = integer('revision_n');
  if (Number.isNaN(registryRevision) || Number.isNaN(revisionN)
    || (registryRevision !== undefined && revisionN !== undefined)) return invalid;
  const digest = url.searchParams.get('content_sha256') ?? undefined;
  if (digest !== undefined && !SHA.test(digest)) return invalid;
  const surface = url.pathname.slice(1) as DocumentReference['surface'];
  const view = url.searchParams.get('view');
  if (view !== null && !(surface === 'plan' ? ['document', 'cards', 'markdown'] : ['read', 'edit']).includes(view)) return invalid;
  return { kind: 'document', target: { surface, worldId, documentId, registryRevision, revisionN, digest, heading: url.hash.slice(1) || undefined } };
}

/** Narrow root-relative admission; arbitrary relative files remain unsupported. */
export function admittedDocumentHref(value: unknown): boolean {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
    && parseDocumentReference(value, 'https://surface.invalid').kind === 'document';
}

export function owningDocumentHref(target: DocumentReference): string {
  return `/${target.surface}?${new URLSearchParams({ world: target.worldId, documentId: target.documentId })}`;
}
