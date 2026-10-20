import { useCallback, type ReactNode } from 'react';
import { useAgentInteraction } from '../agentInteraction/useAgentInteraction';
import { DocumentReferenceProvider } from './DocumentReferenceProvider';
import { resolveDocumentReference } from './resolveDocumentReference';

/** Subscribe to the owning publication; pushState alone is not a reactive lease. */
export function DocumentReferenceSurfaceHost({ children, worldId, surface, load = resolveDocumentReference }: {
  children: ReactNode; worldId: string | null; surface: string;
  load?: typeof resolveDocumentReference;
}) {
  const { surfaceInteractionPublication: publication } = useAgentInteraction();
  const enabled = ['build', 'plan', 'play'].includes(surface);
  const current = publication?.identity.surfaceId === surface ? publication : null;
  // Identity only: content, selection, view and callback changes do not retire inspection.
  // No URL fallback while a source publisher is loading/retired.
  const sourceIdentity = JSON.stringify([surface, current?.identity ?? null, current?.canvas?.workObject ?? null]);
  const ready = current !== null;
  const read = useCallback<typeof resolveDocumentReference>((target, selectedWorld) => {
    if (!ready) return Promise.reject(new Error('The source surface is not ready for document inspection.'));
    return load(target, selectedWorld);
  }, [ready, load]);
  return <DocumentReferenceProvider worldId={worldId} sourceIdentity={sourceIdentity} enabled={enabled} load={read}>
    {children}
  </DocumentReferenceProvider>;
}
