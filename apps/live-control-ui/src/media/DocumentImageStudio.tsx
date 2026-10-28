import {useTourImage} from '../guidedTour/ImageObservations';
import { useEffect, useRef } from 'react';
import { authenticatedApiFetch, getNativeGraphAccessGeneration } from '../api/liveApi';
import { MediaImageWizard } from './MediaImageWizard';
import type { DocumentMediaBridge } from './documentMediaBridge';
import './DocumentImageStudio.css';

/** The existing Studio generates/retains assets; the host alone writes its document. */
export function DocumentImageStudio({ bridge, onClose, targetLabel, initialPrompt = "" }: {
  bridge: DocumentMediaBridge; onClose: () => void; targetLabel: string; initialPrompt?: string;
}) {
  const tourImage=useTourImage();
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, [bridge]);
  return <aside className="document-image-studio" aria-label={`Image Studio · ${targetLabel}`}>
    <MediaImageWizard initialPrompt={initialPrompt} onClose={onClose} chooseLabel={`Place in ${targetLabel}`} onChoose={async (image, _result, placement) => {
      const generation = getNativeGraphAccessGeneration();
      const target = await bridge.pickInsertion({ ...placement, assetId: image.asset_id });
      placement.signal.throwIfAborted();
      const { response, requestEpoch } = await authenticatedApiFetch(`/api/live/media/images/${encodeURIComponent(image.asset_id)}/metadata`, { signal: placement.signal, cache: 'no-store' });
      if (!response.ok) throw new Error('The saved image could not be verified. Try placing it again.');
      const asset = await response.json();
      placement.signal.throwIfAborted();
      if (!active.current || !asset || typeof asset !== 'object' || asset.asset_id !== image.asset_id || !['staged', 'ready'].includes(asset.state) || generation !== getNativeGraphAccessGeneration() || requestEpoch !== generation) throw new Error('The retained image or access changed. Open it again before placing it.');
      bridge.insert(target, asset.asset_id, 'Saved artwork');
      tourImage?.placed(asset.asset_id);
      onClose();
    }} />
  </aside>;
}
