export const MEDIA_ASSET_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function mediaAssetId(url: string): string | null {
  const value = url.startsWith('dmb-media:') ? url.slice(10) : '';
  return MEDIA_ASSET_ID.test(value) ? value : null;
}
export function imagePresentation(title: string | null | undefined): {width: number; collapsed: boolean} | null {
  const match = /^dmb-image:v1 width=(20|[2-9][0-9]|100) collapsed=(true|false)$/.exec(title ?? '');
  return match ? {width: Number(match[1]), collapsed: match[2] === 'true'} : null;
}
export function mediaMarkdown(assetId: string, alt: string, width?: unknown, collapsed?: unknown): string {
  if (!MEDIA_ASSET_ID.test(assetId) || !alt.trim() || /[\r\n]/.test(alt)) throw new Error('Invalid saved image reference.');
  const explicit = width != null || collapsed != null;
  if (explicit && (!Number.isInteger(width) || Number(width) < 20 || Number(width) > 100 || typeof collapsed !== 'boolean')) throw new Error('Invalid image presentation.');
  const title = explicit ? ` "dmb-image:v1 width=${width} collapsed=${collapsed}"` : '';
  return `![${alt.replace(/[\\\[\]*_`<>]/g, '\\$&')}](dmb-media:${assetId}${title})`;
}
