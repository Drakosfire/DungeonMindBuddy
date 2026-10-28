import { useEffect, useState } from 'react';
import { originalImageBlob } from './originalImageBlob';

type PreparedDownload = {
  dataUrl: string;
  mediaType: string;
  url?: string;
  error?: string;
};

/** The retained original is already owner-authorized; CDN delivery is unrelated. */
export function OriginalImageDownload({ dataUrl, mediaType, filename }: {
  dataUrl: string; mediaType: string; filename: string;
}) {
  const [prepared, setPrepared] = useState<PreparedDownload | null>(null);

  useEffect(() => {
    let url: string | undefined;
    try {
      url = URL.createObjectURL(originalImageBlob(dataUrl, mediaType));
      setPrepared({ dataUrl, mediaType, url });
    } catch {
      setPrepared({
        dataUrl, mediaType,
        error: 'This image could not be prepared for download. Reopen it from your library and try again.',
      });
    }
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [dataUrl, mediaType]);

  const current = prepared?.dataUrl === dataUrl && prepared.mediaType === mediaType ? prepared : null;
  if (!current) return <span role="status">Preparing download…</span>;
  if (!current.url) return <span role="alert">{current.error}</span>;
  return <a download={filename} href={current.url}>Download image</a>;
}
