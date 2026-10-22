import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {testCombatLocks} from "../../combat/combatRecovery.testSupport";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { CombatMechanicsSnapshot } from "../../combat/combatTypes";
import type { ManagedWorldGraphProjectionResponse } from "../../api/types";
import type { WorldMechanicsAssociation } from "../../api/worldMechanicsTypes";
import * as combatApi from "../../combat/combatApi";
import type { CombatEncounterRecord } from "../../combat/combatTypes";
import * as selectedWorld from "../../selectedWorld/SelectedWorldContext";
import { CombatRosterModule } from "./CombatRosterModule";

const entity = {
  id: "drake-1",
  name: "Geomantic Drake",
  team: "enemy" as const,
  order: 1,
  init: 14,
  ac: 15,
  hp: 76,
  max_hp: 76,
  temp_hp: 0,
  defeated: false,
  notes: "Guards the pass",
  conditions: [],
  tags: [],
  statblock_path: null,
  statblock_artifact_id: null,
  statblock_title: null,
  corpus_fingerprint: null,
  source: "manual" as const,
  provenance: [],
};

function record(overrides: Partial<CombatEncounterRecord> = {}): CombatEncounterRecord {
  return {
    encounter_id: "3f620410-21cb-4d18-88d4-5ea5e60b0b14",
    world_id: "elderwyld",
    campaign_id: "longmont-c2",
    session: 29,
    revision: 1,
    ruleset: {
      schema: "dmb_combat_ruleset_v1",
      config_id: "generic.manual-tracking",
      system_id: "generic",
      edition_id: "manual",
      revision: "1",
      mode: "manual_tracking",
      fields: [],
      manual_defaults: {},
    },
    ruleset_digest: "a".repeat(64),
    draft: {
      schema: "dmb_combat_encounter_draft_v1",
      title: "Mireward Gate",
      round: 1,
      active_turn_entity_id: "drake-1",
      round_start_entity_id: "drake-1",
      queue_model: "circular_barrel_v1",
      entities: [entity],
      groups: [],
      provenance: [],
    },
    created_at: "2026-10-17T12:00:00Z",
    updated_at: "2026-10-17T12:00:00Z",
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("CombatRosterModule", () => {
  beforeEach(() => {localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
  afterEach(() => vi.restoreAllMocks());

  function mount() {
    let worldId = "elderwyld";
    vi.spyOn(selectedWorld, "useSelectedWorld").mockImplementation(() => ({
      kind: "managed",
      worldId,
      name: worldId === "elderwyld" ? "Elderwyld" : "Conks and Cons",
      documentId: null,
    }));
    const view = render(<CombatRosterModule />);
    return {
      ...view,
      setWorld(nextWorldId: string) {
        worldId = nextWorldId;
        view.rerender(<CombatRosterModule />);
      },
    };
  }

  it("requires an explicit open instead of guessing which encounter to load", async () => {
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([record()]);
    const getSpy = vi.spyOn(combatApi, "getWorldCombatEncounter").mockResolvedValue(record());

    mount();

    expect(await screen.findByRole("option", { name: "Mireward Gate · rev 1" })).toBeInTheDocument();
    expect(screen.queryByText("Geomantic Drake")).not.toBeInTheDocument();
    expect(getSpy).not.toHaveBeenCalled();

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), record().encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));

    expect(await screen.findAllByText("Geomantic Drake")).not.toHaveLength(0);
    expect(getSpy).toHaveBeenCalledWith("elderwyld", record().encounter_id);
    expect(screen.getByText(/generic · manual · config rev 1/i)).toBeInTheDocument();
  });

  it("locks encounter edits while opening a replacement draft", async () => {
    const current = record();
    const target = record({
      encounter_id: "76ba03ae-47ee-4b4a-b1b6-caf4822727a7",
      draft: { ...record().draft, title: "Second encounter" },
    });
    const pendingOpen = deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([current, target]);
    vi.spyOn(combatApi, "getWorldCombatEncounter")
      .mockResolvedValueOnce(current)
      .mockReturnValueOnce(pendingOpen.promise);

    mount();
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), current.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const title = await screen.findByRole("textbox", { name: "Encounter title" });

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), target.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));

    expect(title).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Notes for Geomantic Drake" })).toBeDisabled();
    await userEvent.type(title, "Edit during open");
    expect(title).toHaveValue("Mireward Gate");

    pendingOpen.resolve(target);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("Second encounter"));
    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("locks encounter edits while creating a replacement encounter", async () => {
    const current = record();
    const created = record({
      encounter_id: "aa73015d-4cc6-4d4f-845e-110bd84b7711",
      draft: { ...record().draft, title: "New encounter", entities: [] },
    });
    const pendingCreate = deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([current]);
    vi.spyOn(combatApi, "getWorldCombatEncounter").mockResolvedValue(current);
    vi.spyOn(combatApi, "createWorldCombatEncounter").mockReturnValue(pendingCreate.promise);

    mount();
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), current.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const title = await screen.findByRole("textbox", { name: "Encounter title" });
    await userEvent.clear(screen.getByRole("textbox", { name: "New encounter title" }));
    await userEvent.type(screen.getByRole("textbox", { name: "New encounter title" }), "New encounter");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(title).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Notes for Geomantic Drake" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "New encounter title" })).toBeDisabled();
    await userEvent.type(title, "Edit during create");
    expect(title).toHaveValue("Mireward Gate");

    pendingCreate.resolve(created);
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("New encounter"));
    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("creates a durable encounter, keeps edits local, then explicitly saves against its revision", async () => {
    const created = record({ draft: { ...record().draft, title: "New encounter", entities: [] } });
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([]);
    const createSpy = vi.spyOn(combatApi, "createWorldCombatEncounter").mockResolvedValue(created);
    const saveSpy = vi.spyOn(combatApi, "saveWorldCombatEncounter").mockResolvedValue(record({
      revision: 2,
      draft: { ...created.draft, title: "Night ambush" },
    }));

    mount();
    await screen.findByText(/No encounters yet/i);
    await userEvent.clear(screen.getByRole("textbox", { name: "New encounter title" }));
    await userEvent.type(screen.getByRole("textbox", { name: "New encounter title" }), "Night ambush");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("textbox", { name: "Encounter title" })).toHaveValue("New encounter");
    expect(createSpy).toHaveBeenCalledWith("elderwyld", { title: "Night ambush" });

    await userEvent.clear(screen.getByRole("textbox", { name: "Encounter title" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Encounter title" }), "Night ambush");
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    expect(saveSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(saveSpy).toHaveBeenCalledWith(
      "elderwyld",
      created.encounter_id,
      1,
      { ...created.draft, title: "Night ambush" },
    ));
    expect(await screen.findByText("Saved · rev 2")).toBeInTheDocument();
  });

  it("ignores an earlier World A create response after an A→B→A switch without clearing the newer request", async () => {
    const staleCreate = deferred<CombatEncounterRecord>();
    const currentCreate = deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([]);
    const createSpy = vi.spyOn(combatApi, "createWorldCombatEncounter")
      .mockImplementationOnce(() => staleCreate.promise)
      .mockImplementationOnce(() => currentCreate.promise);
    const view = mount();

    await screen.findByText(/No encounters yet/i);
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    view.setWorld("conks-and-cons");
    await screen.findByText(/No encounters yet/i);
    view.setWorld("elderwyld");
    await screen.findByText(/No encounters yet/i);
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(createSpy).toHaveBeenCalledTimes(2);

    staleCreate.resolve(record({ encounter_id: "stale-world-a" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Create" })).toBeDisabled());
    expect(screen.queryByRole("textbox", { name: "Encounter title" })).not.toBeInTheDocument();

    currentCreate.resolve(record({
      encounter_id: "current-world-a",
      draft: { ...record().draft, title: "Current World A" },
    }));
    expect(await screen.findByRole("textbox", { name: "Encounter title" })).toHaveValue("Current World A");
    expect(await screen.findByText("Saved · rev 1")).toBeInTheDocument();
  });

  it("ignores an earlier World A open response after an A→B→A switch without clearing the newer request", async () => {
    const staleOpen = deferred<CombatEncounterRecord>();
    const currentOpen = deferred<CombatEncounterRecord>();
    const worldARecord = record();
    const worldBRecord = record({
      world_id: "conks-and-cons",
      encounter_id: "d94ebf8a-7f0e-4ff2-a1b8-69916f6a79d1",
      draft: { ...record().draft, title: "Conks encounter" },
    });
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockImplementation(async (worldId) =>
      worldId === "elderwyld" ? [worldARecord] : [worldBRecord]);
    const openSpy = vi.spyOn(combatApi, "getWorldCombatEncounter")
      .mockImplementationOnce(() => staleOpen.promise)
      .mockImplementationOnce(() => currentOpen.promise);
    const view = mount();

    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), worldARecord.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));

    view.setWorld("conks-and-cons");
    await screen.findByRole("option", { name: "Conks encounter · rev 1" });
    view.setWorld("elderwyld");
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), worldARecord.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(openSpy).toHaveBeenCalledTimes(2);

    staleOpen.resolve(record({ draft: { ...record().draft, title: "Stale World A" } }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Open" })).toBeDisabled());
    expect(screen.queryByRole("textbox", { name: "Encounter title" })).not.toBeInTheDocument();

    currentOpen.resolve(record({ draft: { ...record().draft, title: "Current World A" } }));
    expect(await screen.findByRole("textbox", { name: "Encounter title" })).toHaveValue("Current World A");
  });

  it("keeps edits made while a save is pending after the submitted snapshot commits", async () => {
    const initial = record();
    const pendingSave = deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([initial]);
    vi.spyOn(combatApi, "getWorldCombatEncounter").mockResolvedValue(initial);
    const saveSpy = vi.spyOn(combatApi, "saveWorldCombatEncounter").mockReturnValue(pendingSave.promise);
    mount();

    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), initial.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const title = await screen.findByRole("textbox", { name: "Encounter title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Submitted title");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledWith(
      "elderwyld", initial.encounter_id, 1, { ...initial.draft, title: "Submitted title" },
    ));

    await userEvent.clear(title);
    await userEvent.type(title, "Newer edit while saving");
    pendingSave.resolve(record({
      revision: 2,
      draft: { ...initial.draft, title: "Submitted title" },
    }));

    await waitFor(() => expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("Newer edit while saving"));
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });

  it("ignores a stale World A reload after an A→B→A switch", async () => {
    const staleReload = deferred<CombatEncounterRecord>();
    const initial = record();
    const worldBRecord = record({
      world_id: "conks-and-cons",
      encounter_id: "d94ebf8a-7f0e-4ff2-a1b8-69916f6a79d1",
      draft: { ...record().draft, title: "Conks encounter" },
    });
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockImplementation(async (worldId) =>
      worldId === "elderwyld" ? [initial] : [worldBRecord]);
    vi.spyOn(combatApi, "getWorldCombatEncounter")
      .mockResolvedValueOnce(initial)
      .mockReturnValueOnce(staleReload.promise)
      .mockResolvedValueOnce(record({ draft: { ...initial.draft, title: "Current World A" } }));
    vi.spyOn(combatApi, "saveWorldCombatEncounter").mockRejectedValue(
      new Error("Combat encounter changed since it was opened; reload before saving"),
    );
    const view = mount();

    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), initial.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const title = await screen.findByRole("textbox", { name: "Encounter title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Local edit");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("button", { name: "Reload latest revision" });
    await userEvent.click(screen.getByRole("button", { name: "Reload latest revision" }));

    view.setWorld("conks-and-cons");
    await screen.findByRole("option", { name: "Conks encounter · rev 1" });
    view.setWorld("elderwyld");
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), initial.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(await screen.findByRole("textbox", { name: "Encounter title" })).toHaveValue("Current World A");

    staleReload.resolve(record({ draft: { ...initial.draft, title: "Stale reload" } }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("Current World A"));
  });

  it("preserves a stale-write conflict and offers explicit reload", async () => {
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([record()]);
    vi.spyOn(combatApi, "getWorldCombatEncounter").mockResolvedValue(record());
    vi.spyOn(combatApi, "saveWorldCombatEncounter").mockRejectedValue(new Error("Combat encounter changed since it was opened; reload before saving"));

    mount();
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), record().encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    await screen.findAllByText("Geomantic Drake");
    await userEvent.clear(screen.getByRole("textbox", { name: "Encounter title" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Encounter title" }), "Changed locally");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/changed since it was opened/i);
    expect(screen.getByRole("button", { name: "Reload latest revision" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("Changed locally");
  });

  it("locks encounter edits while reloading the latest revision", async () => {
    const initial = record();
    const pendingReload = deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([initial]);
    vi.spyOn(combatApi, "getWorldCombatEncounter")
      .mockResolvedValueOnce(initial)
      .mockReturnValueOnce(pendingReload.promise);
    vi.spyOn(combatApi, "saveWorldCombatEncounter").mockRejectedValue(
      new Error("Combat encounter changed since it was opened; reload before saving"),
    );

    mount();
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), initial.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));
    const title = await screen.findByRole("textbox", { name: "Encounter title" });
    await userEvent.clear(title);
    await userEvent.type(title, "Local edit");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "Reload latest revision" }));

    expect(title).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Notes for Geomantic Drake" })).toBeDisabled();
    await userEvent.type(title, "Late edit");
    expect(title).toHaveValue("Local edit");

    pendingReload.resolve(record({
      revision: 2,
      draft: { ...initial.draft, title: "Server latest" },
    }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Encounter title" })).toHaveValue("Server latest"));
    expect(await screen.findByText("Saved · rev 2")).toBeInTheDocument();
    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("starts the turn pointer at the first living combatant and advances the round on wrap", async () => {
    const guard = { ...entity, id: "guard-2", name: "Longbow Guard", order: 2, init: 11 };
    const fallen = { ...entity, id: "guard-3", name: "Fallen Guard", order: 3, init: 7, defeated: true };
    const initial = record({ draft: {
      ...record().draft,
      round: 1,
      active_turn_entity_id: null,
      round_start_entity_id: null,
      entities: [entity, guard, fallen],
    } });
    vi.spyOn(combatApi, "listWorldCombatEncounters").mockResolvedValue([initial]);
    vi.spyOn(combatApi, "getWorldCombatEncounter").mockResolvedValue(initial);
    const saveSpy = vi.spyOn(combatApi, "saveWorldCombatEncounter").mockResolvedValue({
      ...initial,
      revision: 2,
      draft: { ...initial.draft, round: 2, active_turn_entity_id: "drake-1", round_start_entity_id: "drake-1" },
    });

    mount();
    await screen.findByRole("option", { name: "Mireward Gate · rev 1" });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Encounter" }), initial.encounter_id);
    await userEvent.click(screen.getByRole("button", { name: "Open" }));

    const drakeRow = await screen.findByRole("row", { name: /Geomantic Drake/ });
    const guardRow = screen.getByRole("row", { name: /Longbow Guard/ });
    const fallenRow = screen.getByRole("row", { name: /Fallen Guard/ });
    const roundValue = () => screen.getByText("Round").parentElement;
    await userEvent.click(screen.getByRole("button", { name: "Next turn" }));
    expect(drakeRow).toHaveClass("combat-roster-active-row");
    expect(roundValue()).toHaveTextContent("1");

    await userEvent.click(screen.getByRole("button", { name: "Next turn" }));
    expect(guardRow).toHaveClass("combat-roster-active-row");
    expect(fallenRow).not.toHaveClass("combat-roster-active-row");

    await userEvent.click(screen.getByRole("button", { name: "Next turn" }));
    expect(drakeRow).toHaveClass("combat-roster-active-row");
    expect(roundValue()).toHaveTextContent("2");
    expect(within(fallenRow).getByRole("button", { name: "Set" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledWith(
      "elderwyld",
      initial.encounter_id,
      1,
      expect.objectContaining({
        round: 2,
        active_turn_entity_id: "drake-1",
        round_start_entity_id: "drake-1",
      }),
    ));
  });
  it("refuses a 101st actor while preserving other draft edits and a valid Save", async () => {
    const initial = record({draft:{...record().draft, active_turn_entity_id:"guard-0",round_start_entity_id:"guard-0",
      entities:Array.from({length:100},(_,index)=>({...entity,id:`guard-${index}`,name:`Guard ${index}`,order:index+1}))}});
    vi.spyOn(combatApi,"listWorldCombatEncounters").mockResolvedValue([initial]);
    vi.spyOn(combatApi,"getWorldCombatEncounter").mockResolvedValue(initial);
    const save=vi.spyOn(combatApi,"saveWorldCombatEncounter").mockImplementation(async (_world,_id,_revision,draft)=>({...initial,draft,revision:2}));
    mount();await screen.findByRole("option",{name:"Mireward Gate · rev 1"});
    await userEvent.selectOptions(screen.getByRole("combobox",{name:"Encounter"}),initial.encounter_id);
    await userEvent.click(screen.getByRole("button",{name:"Open"}));
    fireEvent.change(await screen.findByRole("textbox",{name:"Encounter title"}),{target:{value:"Keep this edit"}});
    fireEvent.click(screen.getByText("Add combatants"));
    fireEvent.change(screen.getByLabelText("Combatant name"),{target:{value:"Overflow actor"}});
    expect(screen.getByRole("button",{name:"Add to encounter draft"})).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("encounter is full");
    await userEvent.click(screen.getByRole("button",{name:"Save"}));
    expect(save).toHaveBeenCalledOnce();expect(save.mock.calls[0][3].entities).toHaveLength(100);
    expect(save.mock.calls[0][3].title).toBe("Keep this edit");
  });

  it("refuses oversized snapshot copies before append and preserves edits and assembly inputs", async () => {
    const initial = record();
    vi.spyOn(combatApi,"listWorldCombatEncounters").mockResolvedValue([initial]);
    vi.spyOn(combatApi,"getWorldCombatEncounter").mockResolvedValue(initial);
    const target={managed_world_id:'elderwyld',native_world_id:'native-world',binding_version:1,graph_revision_id:'head',node_id:'keeper',label:'Keeper',kind:'npc',role:'npc',campaign_scope:null};
    vi.spyOn(liveApi,"postManagedWorldGraphProjection").mockResolvedValue({managedWorldId:'elderwyld',nativeWorldId:'native-world',bindingVersion:1,
      projection:{snapshot:{worldId:'native-world',revisionId:'head',scopeMode:'world'},nodes:[{nodeId:'keeper',label:'Keeper',kind:'npc',role:'npc',aliases:[]}]}} as unknown as ManagedWorldGraphProjectionResponse);
    vi.spyOn(liveApi,"listWorldMechanicsAssociations").mockResolvedValue([{association_id:'one',version:1,request:{target}} as WorldMechanicsAssociation]);
    const snapshot={association_id:'one',association_version:1,target,resource:{definition:{identity:{name:'Keeper'}},provenance:{description:'x'.repeat(40000)}}} as unknown as CombatMechanicsSnapshot;
    vi.spyOn(combatApi,"previewWorldCombatMechanics").mockResolvedValue(snapshot);
    const save=vi.spyOn(combatApi,"saveWorldCombatEncounter").mockImplementation(async(_world,_id,_revision,draft)=>({...initial,revision:2,draft}));
    mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);
    await userEvent.click(screen.getByRole('button',{name:'Open'}));
    const title=await screen.findByRole('textbox',{name:'Encounter title'});
    await userEvent.clear(title);await userEvent.type(title,'Prior local edit');
    await userEvent.click(screen.getByText('Add combatants'));
    await userEvent.click(screen.getByRole('button',{name:'Find World creatures'}));
    await userEvent.click(await screen.findByRole('button',{name:'Keeper npc · World · keeper'}));
    await userEvent.click(screen.getByRole('button',{name:'Load associated mechanics'}));
    await screen.findByText('Exact saved mechanics loaded. Tracker AC and HP stay manual.');
    await userEvent.clear(screen.getByLabelText('Combatant copies'));await userEvent.type(screen.getByLabelText('Combatant copies'),'20');
    await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('700 KiB');
    expect(title).toHaveValue('Prior local edit');expect(screen.getByLabelText('Combatant name')).toHaveValue('Keeper');
    expect(screen.getByLabelText('Combatant copies')).toHaveValue(20);
    expect(screen.queryByRole('textbox',{name:'Notes for Keeper 1'})).toBeNull();
    await userEvent.click(screen.getByRole('button',{name:'Save'}));
    await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));
    expect(save.mock.calls[0][3].title).toBe('Prior local edit');expect(save.mock.calls[0][3].entities).toHaveLength(1);
    await userEvent.clear(screen.getByLabelText('Combatant copies'));await userEvent.type(screen.getByLabelText('Combatant copies'),'1');
    await userEvent.click(screen.getByRole('button',{name:'Add to encounter draft'}));
    expect(await screen.findByRole('textbox',{name:'Notes for Keeper'})).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it("keeps unsaved edits through tool unmount and explicitly recovers the same encounter",async()=>{
    const initial=record();vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([initial]);
    vi.spyOn(combatApi,'getWorldCombatEncounter').mockResolvedValue(initial);
    const save=vi.spyOn(combatApi,'saveWorldCombatEncounter').mockImplementation(async(_world,_id,_revision,draft)=>({...initial,revision:2,draft}));
    const first=mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);
    await userEvent.click(screen.getByRole('button',{name:'Open'}));
    const notes=await screen.findByLabelText('Notes for Geomantic Drake');await userEvent.clear(notes);await userEvent.type(notes,'Retained local notes');
    first.unmount();mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});
    expect(screen.getByRole('combobox',{name:'Encounter'})).toHaveValue(initial.encounter_id);
    await userEvent.click(screen.getByRole('button',{name:'Open'}));
    const recover=await screen.findByRole('button',{name:'Recover local Combat draft'});
    expect(screen.getByLabelText('Notes for Geomantic Drake')).toHaveValue('Guards the pass');expect(save).not.toHaveBeenCalled();
    await userEvent.click(recover);expect(screen.getByLabelText('Notes for Geomantic Drake')).toHaveValue('Retained local notes');
    await userEvent.click(screen.getByRole('button',{name:'Save'}));await screen.findByText('Saved · rev 2');
    expect(save.mock.calls[0][3].entities[0].notes).toBe('Retained local notes');
  });
  it("reconciles a lost Save acknowledgement without reposting or dropping later edits",async()=>{
    const initial=record();const pending=deferred<CombatEncounterRecord>();
    vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([initial]);
    const get=vi.spyOn(combatApi,'getWorldCombatEncounter').mockResolvedValue(initial);
    const save=vi.spyOn(combatApi,'saveWorldCombatEncounter').mockReturnValueOnce(pending.promise)
      .mockImplementation(async(_world,_id,revision,draft)=>({...initial,revision:revision+1,draft}));
    const first=mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);await userEvent.click(screen.getByRole('button',{name:'Open'}));
    const title=await screen.findByLabelText('Encounter title');await userEvent.clear(title);await userEvent.type(title,'Submitted');
    await userEvent.click(screen.getByRole('button',{name:'Save'}));await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));
    const submitted=save.mock.calls[0][3];await userEvent.clear(title);await userEvent.type(title,'Later edits');
    pending.reject(new Error('Connection lost'));await screen.findByRole('alert');first.unmount();
    get.mockResolvedValue({...initial,revision:2,draft:submitted});mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});
    await userEvent.click(screen.getByRole('button',{name:'Open'}));
    await screen.findByText('The submitted Save is committed. Later local edits remain available to recover.');
    expect(save).toHaveBeenCalledTimes(1);await userEvent.click(screen.getByRole('button',{name:'Recover local Combat draft'}));
    expect(screen.getByLabelText('Encounter title')).toHaveValue('Later edits');
    await userEvent.click(screen.getByRole('button',{name:'Save'}));await screen.findByText('Saved · rev 3');
    expect(save.mock.calls[1][2]).toBe(2);expect(save.mock.calls[1][3].title).toBe('Later edits');
  });
  it("refuses local changes when browser recovery storage fails",async()=>{
    const initial=record();vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([initial]);vi.spyOn(combatApi,'getWorldCombatEncounter').mockResolvedValue(initial);
    mount();await screen.findByRole('option',{name:'Mireward Gate · rev 1'});await userEvent.selectOptions(screen.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);await userEvent.click(screen.getByRole('button',{name:'Open'}));
    const title=await screen.findByLabelText('Encounter title');vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Storage quota exceeded');});
    await userEvent.type(title,'x');expect(await screen.findByRole('alert')).toHaveTextContent('Storage quota exceeded');expect(title).toHaveValue('Mireward Gate');
    expect(screen.getByRole('button',{name:'Save'})).toBeDisabled();
  });

  it("refuses a second local editor and recovers only after the first view closes",async()=>{
    const initial=record();vi.spyOn(selectedWorld,'useSelectedWorld').mockReturnValue({kind:'managed',worldId:'elderwyld',name:'Elderwyld',documentId:null});
    vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([initial]);vi.spyOn(combatApi,'getWorldCombatEncounter').mockResolvedValue(initial);
    const first=render(<CombatRosterModule/>),second=render(<CombatRosterModule/>);
    const a=within(first.container),b=within(second.container);
    await a.findByRole('option',{name:'Mireward Gate · rev 1'});await b.findByRole('option',{name:'Mireward Gate · rev 1'});
    await userEvent.selectOptions(a.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);await userEvent.click(a.getByRole('button',{name:'Open'}));
    const notes=await a.findByLabelText('Notes for Geomantic Drake');await userEvent.clear(notes);await userEvent.type(notes,'First view recovery');
    await userEvent.selectOptions(b.getByRole('combobox',{name:'Encounter'}),initial.encounter_id);await userEvent.click(b.getByRole('button',{name:'Open'}));
    expect(await b.findByRole('alert')).toHaveTextContent('another view');expect(a.getByLabelText('Notes for Geomantic Drake')).toHaveValue('First view recovery');
    first.unmount();await userEvent.click(b.getByRole('button',{name:'Open'}));
    await userEvent.click(await b.findByRole('button',{name:'Recover local Combat draft'}));
    expect(b.getByLabelText('Notes for Geomantic Drake')).toHaveValue('First view recovery');
  });

});
