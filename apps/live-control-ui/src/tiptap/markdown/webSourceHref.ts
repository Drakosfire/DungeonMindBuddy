import { admittedSavedConversationVariantHref } from "../../statblocks/savedStatblockLocation";
import { admittedSessionEvidenceHref } from '../../playSurface/review/sessionEvidenceHref';
import { admittedDocumentHref } from '../../documentReference/documentReference';
const nativePassagePath = /^\/api\/live\/agent\/worlds\/([A-Za-z0-9_-]+)\/conversation\/turns\/([a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12})\/native-body-excerpts\/(0|[1-9]\d{0,4})$/i;

export function nativePassageTarget(value: unknown) {
  const match = typeof value === 'string' ? nativePassagePath.exec(value) : null;
  const index = match ? Number(match[3]) : -1;
  return match && index <= 16383 ? {worldId: match[1]!, turnId: match[2]!, index} : null;
}

/** Navigation href only. Typed Buddy identities are admitted by their own nodes. */
export function webSourceHref(value: unknown): string | null {
  if (typeof value === 'string' && (admittedDocumentHref(value) || admittedSessionEvidenceHref(value) || admittedSavedConversationVariantHref(value) || nativePassageTarget(value))) return value;
  if (typeof value !== 'string' || /[\s\u0000-\u001f\u007f\\]/u.test(value) || !/^https?:\/\//i.test(value)) return null;
  try {
    const url = new URL(value);
    return url.hostname && !url.username && !url.password ? value : null;
  } catch { return null; }
}

/** Inert optional display text; never URL or evidence authority. */
export function validWebSourceTitle(value: unknown): value is string | null | undefined {
  return value == null || (typeof value === 'string' && !/[\u0000-\u001f\u007f-\u009f]/u.test(value));
}
