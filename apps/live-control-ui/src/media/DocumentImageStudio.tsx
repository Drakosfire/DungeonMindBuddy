import { useEffect, useRef } from 'react';
import { authenticatedApiFetch } from '../api/liveApi';
import { MediaImageWizard } from './MediaImageWizard';
import type { DocumentMediaBridge } from './documentMediaBridge';
import './DocumentImageStudio.css';

/** The existing Studio generates/retains assets; the host alone writes its document. */
export function DocumentImageStudio({ bridge, onClose, targetLabel, initialPrompt = "" }: {
  bridge: DocumentMediaBridge; onClose: () => void; targetLabel: string; initialPrompt?: string;
}) {
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, [bridge]);
  return <aside className="document-image-studio" aria-label={`Image Studio · ${targetLabel}`}>
    <MediaImageWizard initialPrompt={initialPrompt} onClose={onClose} chooseLabel={`Place in ${targetLabel}`} onChoose={async (image, _result, placement) => {
      const target = await bridge.pickInsertion({ ...placement, assetId: image.asset_id });
      placement.signal.throwIfAborted();
      const { response } = await authenticatedApiFetch(`/api/live/media/images/${encodeURIComponent(image.asset_id)}/metadata`, { signal: placement.signal, cache: 'no-store' });
      if (!response.ok) throw new Error('The saved image could not be verified. Try placing it again.');
      const asset = await response.json();
      placement.signal.throwIfAborted();
      if (!active.current || !asset || typeof asset !== 'object' || asset.asset_id !== image.asset_id || asset.state !== 'ready') throw new Error('Save this image before placing it in the current document.');
      bridge.insert(target, asset.asset_id, 'Saved artwork');
      onClose();
    }} />
  </aside>;
}
