import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { PartyRegistrySurfaceResponse } from "../api/types";
import { PartyRegistryModule } from "./PartyRegistryModule";

const mockContext = {
  campaignId: "longmont-c2",
  liveSession: 22,
  ingestSession: 23,
  headerLabel: "Plan · C2 Session 23 Prep",
};

function makePartyRegistryResponse(
  overrides: Partial<PartyRegistrySurfaceResponse> = {},
): PartyRegistrySurfaceResponse {
  return {
    schema_version: "dmb_party_registry_surface_v1",
    campaign_id: "longmont-c2",
    session: 23,
    session_id: "session-23",
    registry_schema: "party_registry_v1",
    registry_relpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json",
    party_names: ["Questionable Company"],
    pc_slugs: [],
    companion_slugs: [],
    notable_npc_slugs: [],
    members: [],
    warnings: ["no session_pc_rosters['23'] entry"],
    registry_summary: {
      schema: "party_registry_v1",
      session_rosters: {
        "22": {
          pcs: ["stafl", "bonogo"],
          companions: ["captain_lysandra_ironveil"],
        },
      },
    },
    session_graph_context: {
      schema: "dmb_session_graph_context_v0",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      session_number: 23,
      party_names: ["Questionable Company"],
      anchor_members: [],
      anchor_nodes: [],
      warnings: ["no session_pc_rosters['23'] entry"],
    },
    available_session_keys: ["20", "22"],
    has_session_roster: false,
    known_pc_slugs: ["bonogo", "stafl"],
    known_companion_slugs: ["captain_lysandra_ironveil"],
    ...overrides,
  };
}

describe("PartyRegistryModule", () => {
  it("loads roster sessions in dropdown and shows missing-session warnings", async () => {
    vi.spyOn(liveApi, "getPartyRegistry").mockResolvedValue(makePartyRegistryResponse());

    render(<PartyRegistryModule context={mockContext} />);

    expect(await screen.findByTestId("party-registry-module")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText(/no session_pc_rosters\['23'\] entry/).length).toBeGreaterThan(0);
    });
    expect(screen.getByLabelText("Party registry session roster")).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: "Session 22" }).length).toBeGreaterThan(0);
    expect(liveApi.getPartyRegistry).toHaveBeenCalledWith("longmont-c2", 23);
  });

  it("prepares a roster save from the edit form", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "getPartyRegistry").mockResolvedValue(makePartyRegistryResponse());
    vi.spyOn(liveApi, "preparePartyRegistrySessionRosterWrite").mockResolvedValue({
      schema_version: "dmb_party_registry_session_roster_write_prepare_v1",
      campaign_id: "longmont-c2",
      session: 23,
      registry_relpath: "Longmont Campaign/Campaign 2/_party_registry.json",
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "token-123",
      writer_diff: "+ session 23",
      pc_slugs: ["stafl"],
      companion_slugs: ["captain_lysandra_ironveil"],
      warnings: [],
      diagnostics: [],
    });

    render(<PartyRegistryModule context={mockContext} />);
    await screen.findByTestId("party-registry-module");

    await user.clear(screen.getByLabelText("PC slugs"));
    await user.type(screen.getByLabelText("PC slugs"), "stafl");
    await user.click(screen.getByRole("button", { name: "Save roster" }));

    await waitFor(() => {
      expect(liveApi.preparePartyRegistrySessionRosterWrite).toHaveBeenCalledWith({
        campaign_id: "longmont-c2",
        session: 23,
        pc_slugs: ["stafl"],
        companion_slugs: [],
      });
    });
    expect(screen.getByTestId("party-registry-write-diff")).toHaveTextContent("session 23");
  });
});
