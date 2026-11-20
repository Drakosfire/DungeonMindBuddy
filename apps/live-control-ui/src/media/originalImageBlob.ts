/** Decode an already owner-authorized original; never a delivery URL. */
export function originalImageBlob(dataUrl: string, mediaType: string): Blob {
  const prefix = `data:${mediaType};base64,`;
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(mediaType) || !dataUrl.startsWith(prefix)) {
    throw new Error('Original image MIME mismatch');
  }
  const binary = atob(dataUrl.slice(prefix.length));
  if (!binary.length) throw new Error('Original image is empty');
  return new Blob([Uint8Array.from(binary, char => char.charCodeAt(0))], { type: mediaType });
}
