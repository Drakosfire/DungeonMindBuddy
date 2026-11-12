import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NativeGraphNodeExplorer as GraphNodeExplorer } from "./GraphNodeExplorer";
import type { NativeGraphEntity } from "../api/nativeGraphInspection";
const inspect = vi.fn();
vi.mock("../api/liveApi", () => ({ inspectNativeGraph: (...args: unknown[]) => inspect(...args), listWorldMechanicsAssociations: vi.fn().mockResolvedValue([]) }));
vi.mock("../graphLens/NativeObjectStatblock", () => ({ NativeObjectStatblock: () => <p>Statblock lookup</p> }));
const detail: NativeGraphEntity = { schema: "dmb_native_graph_entity_v1", scope: { managed_world_id: "managed", native_world_id: "world", revision_id: "rev", binding_version: 1, scope_mode: "world", campaign_id: null }, entity: {
  found: true, completeness: { status: "complete", reason: null }, evidence: [{ evidence_ref_id: "e", evidence_role: "support" }], assertions: [{ assertion_id: "a", subject_entity_id: "lysandra", predicate: "dungeonbuddy:commands", value: { kind: "entity_ref", entity_id: "stafl" }, metadata: { scope: [], visibility: "public", epistemic_basis: "asserted", claim_mode: "dungeonbuddy.claim:fact", standing: "provisional", evidence_ref_ids: ["e"], temporal_scope: null, domain_metadata: [] } }],
} };
afterEach(() => { cleanup(); vi.clearAllMocks(); });
describe("GraphNodeExplorer", () => {
  it("separates neighbors from records and navigates without writes or automatic source reads", () => {
    const navigate = vi.fn();
    render(<GraphNodeExplorer detail={detail} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["lysandra", "Lysandra"], ["stafl", "Stafl"]])} onExplore={navigate} partial />);
    expect(screen.getByText("1 connected objects")).toBeInTheDocument();
    expect(screen.getByText(/1 relationship records/)).toBeInTheDocument();
    expect(screen.getByText("Partial view")).toBeInTheDocument();
    expect(inspect).not.toHaveBeenCalled();
    expect(screen.queryByText("Statblock lookup")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/Affiliation and command/));
    fireEvent.click(screen.getByRole("button", { name: "Explore Stafl" }));
    expect(navigate).toHaveBeenCalledWith("stafl");
  });
  it("keeps metadata in a dismissible menu and resets it on selection", () => {
    const focus = vi.fn(); const close = vi.fn();
    const props = { detail, node: { id: "lysandra", name: "Lysandra", kind: "person" as const }, revision: "rev", onFocus: focus, onClose: close, labels: new Map<string, string>(), onExplore: vi.fn() };
    const { rerender } = render(<GraphNodeExplorer {...props} />);
    const trigger = screen.getByLabelText("Node information and actions");
    const menu = trigger.closest("details")!;
    expect(screen.getByText("1 connected objects")).not.toBeVisible();
    fireEvent.click(trigger);
    expect(menu).toHaveAttribute("open");
    expect(screen.getByText("1 connected objects")).toBeVisible();
    fireEvent.keyDown(trigger, { key: "Escape" });
    expect(menu).not.toHaveAttribute("open");
    expect(trigger).toHaveFocus();
    fireEvent.click(trigger);
    rerender(<GraphNodeExplorer {...props} node={{ ...props.node, id: "stafl", name: "Stafl" }} />);
    expect(menu).not.toHaveAttribute("open");
    fireEvent.click(screen.getByRole("button", { name: "Focus" }));
    fireEvent.click(screen.getByRole("button", { name: "Close details" }));
    expect(focus).toHaveBeenCalledOnce(); expect(close).toHaveBeenCalledOnce();
  });
  it("loads exact supporting evidence only on request and rejects a newer revision", async () => {
    inspect.mockResolvedValue({ schema: "dmb_native_graph_source_v1", scope: { ...detail.scope, revision_id: "newer" }, source: { text: "Wrong newer text" } });
    render(<GraphNodeExplorer detail={detail} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["stafl", "Stafl"]])} onExplore={vi.fn()} />);
    fireEvent.click(screen.getByText(/Affiliation and command/));
    fireEvent.click(screen.getByText("Evidence and qualifications"));
    fireEvent.click(screen.getByRole("button", { name: "Read supporting source" }));
    expect(await screen.findByText(/exact cited passage is unavailable/)).toBeInTheDocument();
    expect(screen.queryByText("Wrong newer text")).not.toBeInTheDocument();
    expect(inspect).toHaveBeenCalledWith(detail.scope, { kind: "source", assertion_id: "a", evidence_ref_id: "e" });
  });
  it("starts groups collapsed with distinct counts and owns compact navigation", () => {
    render(<GraphNodeExplorer detail={detail} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["stafl", "Stafl"]])} onExplore={vi.fn()} />);
    const group = screen.getByText(/Affiliation and command/).closest("details");
    expect(group).not.toHaveAttribute("open");
    expect(group).toHaveTextContent("1 node");
    expect(screen.getByRole("button", { name: "Explore Stafl" })).not.toBeVisible();
    expect(screen.getByRole("navigation", { name: "Node explorer controls" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close details" })).toHaveTextContent("×");
  });
  it("does not turn two inverse records into two corroborating sources", () => {
    const child = { ...detail.entity.assertions[0]!, predicate: "dungeonbuddy:child_of" };
    const parent = { ...child, assertion_id: "b", subject_entity_id: "stafl", predicate: "dungeonbuddy:parent_of", value: { kind: "entity_ref" as const, entity_id: "lysandra" } };
    render(<GraphNodeExplorer detail={{ ...detail, entity: { ...detail.entity, assertions: [child, parent] } }} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["stafl", "Stafl"]])} onExplore={vi.fn()} />);
    fireEvent.click(screen.getByText(/Family/));
    fireEvent.click(screen.getByText("Evidence and qualifications · 2 records"));
    expect(screen.getByText("1 supporting source · 2 records")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Read supporting source" })).toHaveLength(1);
  });
  it("shows mixed speculative status without opening evidence", () => {
    const uncertain = { ...detail.entity.assertions[0]!, assertion_id: "b", metadata: { ...detail.entity.assertions[0]!.metadata, standing: "disputed", epistemic_basis: "speculative" } };
    render(<GraphNodeExplorer detail={{ ...detail, entity: { ...detail.entity, assertions: [...detail.entity.assertions, uncertain] } }} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["stafl", "Stafl"]])} onExplore={vi.fn()} />);
    fireEvent.click(screen.getByText(/Affiliation and command/));
    expect(screen.getAllByText("fact · speculative · disputed")[0]).toBeVisible();
  });
  it("keeps hosted limitations and pending-operation navigation guard", () => {
    const navigate = vi.fn();
    render(<GraphNodeExplorer detail={detail} node={{ id: "lysandra", name: "Lysandra", kind: "person" }} revision="rev" onFocus={vi.fn()} onClose={vi.fn()} labels={new Map([["stafl", "Stafl"]])} entityOnly navigationDisabled onExplore={navigate} />);
    expect(screen.queryByRole("button", { name: "Read supporting source" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/Affiliation and command/));
    expect(screen.getByRole("button", { name: "Explore Stafl" })).toBeDisabled();
    expect(screen.getByText(/Source excerpts and linked statblocks are not available/)).toBeInTheDocument();
    expect(inspect).not.toHaveBeenCalled();
  });
});
