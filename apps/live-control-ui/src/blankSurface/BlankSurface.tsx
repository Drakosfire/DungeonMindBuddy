import { useEffect, useMemo, type ReactNode } from "react";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { blankSurfacePublication, type BlankSurfaceDescriptor } from "./blankSurface";
import "./blankSurface.css";

/** Content and domain-specific Agent plugins are slots; AppChrome owns the hosts. */
export function BlankSurface({ descriptor, children }: {
  descriptor: BlankSurfaceDescriptor;
  children?: ReactNode;
}) {
  const publication = useMemo(() => blankSurfacePublication(descriptor), [descriptor]);
  const { publishSurfaceContext } = useAgentInteraction();
  usePublishSurfaceInteraction(publication);
  useEffect(() => {
    // Legacy context display is a setter, not a lease. Never clear it on teardown:
    // a newly mounted Surface may already have published its own current context.
    publishSurfaceContext({
      surfaceId: publication.surfaceId,
      label: publication.label,
      campaignId: null,
      documentId: null,
      sessionNumber: null,
      ambientSummary: descriptor.ambientSummary,
      sourceEnvelope: null,
      updatedAt: new Date().toISOString(),
    });
  }, [descriptor.ambientSummary, publication, publishSurfaceContext]);
  return (
    <main className="blank-surface" aria-label={descriptor.label}>
      {children}
      <header>
        <h1>{descriptor.label}</h1>
        <p>No active work. Open a surface from navigation to create or resume work.</p>
      </header>
      <section className="blank-surface-space" aria-label="Blank workspace" />
    </main>
  );
}
