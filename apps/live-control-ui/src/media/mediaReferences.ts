export const MEDIA_ASSET_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function mediaAssetId(url: string): string | null {
  const value = url.startsWith('dmb-media:') ? url.slice(10) : '';
  return MEDIA_ASSET_ID.test(value) ? value : null;
}
export function mediaMarkdown(assetId: string, alt: string): string {
  if (!MEDIA_ASSET_ID.test(assetId) || !alt.trim() || /[\r\n]/.test(alt)) throw new Error('Invalid saved image reference.');
  return `![${alt.replace(/[\\\[\]*_`<>]/g, '\\$&')}](dmb-media:${assetId})`;
}
