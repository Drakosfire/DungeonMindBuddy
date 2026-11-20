import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceProjectionBinding, GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { GRAPH_REFERENCE_PROJECTION_ID } from "../../surfaceInteraction/projection/projectionCatalog";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import type { SurfaceInteractionPublication } from "../../surfaceInteraction/types";
import { useProjection } from "./projectionContext";

const innNode: GraphProjectionNodeView = {
  node_id: "location-inn", label: "Inn", kind: "location", role: "location",
  aliases: [], source_domains: ["recap"], evidence_badges: [], adjacency: [],
  anchored_to_focus_session: true, summary: "Meeting place.",
};
const resolution: GraphReferenceResolution = {
  kind: "resolved_graph", locator: `dmb-node:${innNode.node_id}`,
  reference: referenceFromGraphNode(innNode),
  graphObject: buildGraphObjectCardFromNodeView(innNode),
  graphNodeId: innNode.node_id, message: "Resolved graph node Inn.", projectionState: "ready",
};

function Probe() {
  const { active, activeGraphReference, graphReferenceProjectionState,
    openGraphReference, registerGraphReferenceBinding } = useProjection();
  const [registered, setRegistered] = useState(false);
  const binding = useMemo<GraphReferenceProjectionBinding>(() => ({
    resolverState: "ready", resolveRelationship: vi.fn(async () => resolution),
    openResolvedReference: vi.fn(), openTool: vi.fn(),
  }), []);
  useEffect(() => {
    if (registered) return registerGraphReferenceBinding(binding);
  }, [registered, binding, registerGraphReferenceBinding]);
  return <>
    <p data-testid="active-key">{active?.key ?? "none"}</p>
    <p data-testid="active-plan-ref">{activeGraphReference?.message ?? "none"}</p>
    <output data-testid="active-resolution">{JSON.stringify(activeGraphReference)}</output>
    <p data-testid="projection-state">{graphReferenceProjectionState ?? "none"}</p>
    <button onClick={() => openGraphReference({ resolution, projectionState: "ready" })}>Open graph node</button>
    <button onClick={() => setRegistered(value => !value)}>{registered ? "Retire binding" : "Register binding"}</button>
  </>;
}

function NativePublicationHost() {
  const { publishSurfaceInteractionPublication } = useAgentInteraction();
  const [declared, setDeclared] = useState(false);
  const publication = useMemo<SurfaceInteractionPublication>(() => ({
    surfaceId: "build", label: "Build",
    identity: buildSurfaceInteractionIdentity({ surfaceId: "build", instanceParts: ["projection-context-test"] }),
    canvas: null, agentContext: null, tools: [], editCommands: [],
    projections: declared ? [{ id: GRAPH_REFERENCE_PROJECTION_ID, kind: "content", preferredSize: "wide", bindingIds: [] }] : [],
    projectionBindings: [],
  }), [declared]);
  useLayoutEffect(() => publishSurfaceInteractionPublication(publication), [publication, publishSurfaceInteractionPublication]);
  return <>
    <button onClick={() => setDeclared(true)}>Declare graph reference</button>
    <Probe />
  </>;
}

describe("projectionContext", () => {
  it("requires declared capability and live binding to open reference content, then clears it on retirement", async () => {
    const user = userEvent.setup();
    render(<AgentInteractionProvider><NativePublicationHost /></AgentInteractionProvider>);
    const expectClosed = () => {
      expect(screen.getByTestId("active-key")).toHaveTextContent(/^none$/);
      expect(screen.getByTestId("active-plan-ref")).toHaveTextContent(/^none$/);
      expect(screen.getByTestId("projection-state")).toHaveTextContent(/^none$/);
      expect(JSON.parse(screen.getByTestId("active-resolution").textContent!)).toBeNull();
    };
    await user.click(screen.getByRole("button", { name: "Register binding" }));
    await user.click(screen.getByRole("button", { name: "Open graph node" }));
    expectClosed(); // A binding attempt cannot invent a declared capability.
    await user.click(screen.getByRole("button", { name: "Retire binding" }));
    await user.click(screen.getByRole("button", { name: "Declare graph reference" }));
    await user.click(screen.getByRole("button", { name: "Open graph node" }));
    expectClosed(); // Declaration without a live binding is still insufficient.
    await user.click(screen.getByRole("button", { name: "Register binding" }));
    await user.click(screen.getByRole("button", { name: "Open graph node" }));
    await waitFor(() => expect(screen.getByTestId("active-key")).toHaveTextContent(/^graph-node$/));
    expect(screen.getByTestId("active-plan-ref")).toHaveTextContent(/^Resolved graph node Inn\.$/);
    expect(screen.getByTestId("projection-state")).toHaveTextContent(/^ready$/);
    expect(JSON.parse(screen.getByTestId("active-resolution").textContent!)).toEqual(resolution);
    await user.click(screen.getByRole("button", { name: "Retire binding" }));
    await waitFor(expectClosed);
    await user.click(screen.getByRole("button", { name: "Open graph node" }));
    expectClosed();
  });
});
